"""Authentication use cases: login, refresh, logout, password recovery and change."""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.email import OutgoingEmail
from app.core.exceptions import (
    AuthenticationError,
    BusinessRuleError,
    InvalidCredentialsError,
)
from app.core.security import (
    burn_password_check,
    create_access_token,
    generate_opaque_token,
    hash_opaque_token,
    hash_password,
    verify_password,
)
from app.modules.audit.service import AuditService
from app.modules.auth.models import PasswordResetToken
from app.modules.auth.schemas import MeResponse, OrganizationRef, RoleRef
from app.modules.auth.sessions import SessionManager
from app.modules.organizations.models import Organization
from app.modules.users.models import User
from app.modules.users.passwords import ensure_password_policy
from app.modules.users.repository import UserRepository
from app.shared.context import RequestContext, utcnow

logger = logging.getLogger(__name__)

INVALID_CREDENTIALS_MESSAGE = (
    "Correo o contraseña incorrectos. Tras varios intentos fallidos la cuenta se bloquea "
    "temporalmente."
)
SESSION_EXPIRED_MESSAGE = "La sesión expiró o fue cerrada. Inicie sesión nuevamente."


@dataclass(frozen=True, slots=True)
class AuthResult:
    access_token: str
    access_expires_at: datetime
    refresh_token: str
    refresh_expires_at: datetime
    must_change_password: bool


class AuthService:
    def __init__(self, session: Session, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._users = UserRepository(session)
        self._sessions = SessionManager(session, settings)
        self._audit = AuditService(session)

    # --- Login / refresh / logout -------------------------------------------------

    def login(self, email: str, password: str, context: RequestContext) -> AuthResult:
        now = utcnow()
        user = self._users.get_by_email_for_update(email)
        if user is None:
            burn_password_check(password)
            raise InvalidCredentialsError(INVALID_CREDENTIALS_MESSAGE)

        if user.locked_until is not None and user.locked_until > now:
            burn_password_check(password)
            self._audit_login_failure(user, context, reason="locked")
            raise InvalidCredentialsError(INVALID_CREDENTIALS_MESSAGE)

        valid, upgraded_hash = verify_password(password, user.password_hash)
        if not valid or not user.is_active:
            self._register_failure(user, context, reason="inactive" if valid else "password")
            raise InvalidCredentialsError(INVALID_CREDENTIALS_MESSAGE)

        if upgraded_hash:
            user.password_hash = upgraded_hash
        user.failed_login_count = 0
        user.locked_until = None
        user.last_login_at = now

        issued = self._sessions.start(user.id, context)
        self._audit.record(
            "auth.login",
            entity_type="user",
            entity_id=user.id,
            organization_id=user.organization_id,
            actor_user_id=user.id,
            context=context,
        )
        return self._result(user, issued.raw, issued.record.expires_at, issued.record.family_id)

    def refresh(self, raw_token: str | None, context: RequestContext) -> AuthResult:
        if not raw_token:
            raise AuthenticationError(SESSION_EXPIRED_MESSAGE)
        now = utcnow()
        token = self._sessions.find_for_update(raw_token)
        if token is None:
            raise AuthenticationError(SESSION_EXPIRED_MESSAGE)

        user = self._session.get(User, token.user_id)
        if token.revoked_at is not None:
            recently_rotated = token.replaced_by_id is not None and (
                now - token.revoked_at
            ) < timedelta(seconds=self._settings.refresh_reuse_grace_seconds)
            if recently_rotated:
                # Concurrent refresh from another tab: the cookie was already replaced.
                # Reject without revoking; the client retries with the new cookie.
                raise AuthenticationError(SESSION_EXPIRED_MESSAGE)
            if token.replaced_by_id is not None and user is not None:
                # A rotated token was presented again: it was probably stolen.
                self._sessions.revoke_family(token.family_id)
                self._audit.record(
                    "auth.refresh_reuse_detected",
                    entity_type="user",
                    entity_id=user.id,
                    organization_id=user.organization_id,
                    actor_user_id=user.id,
                    context=context,
                    changes={"session_id": str(token.family_id)},
                )
                self._session.commit()
            raise AuthenticationError(SESSION_EXPIRED_MESSAGE)

        if token.expires_at <= now or user is None or not user.is_active:
            raise AuthenticationError(SESSION_EXPIRED_MESSAGE)

        issued = self._sessions.issue(
            user_id=user.id,
            family_id=token.family_id,
            session_expires_at=token.session_expires_at,
            context=context,
            now=now,
        )
        token.revoked_at = now
        token.replaced_by_id = issued.record.id
        return self._result(user, issued.raw, issued.record.expires_at, token.family_id)

    def logout(self, raw_token: str | None, context: RequestContext) -> None:
        """Idempotent: works with an expired access token as long as the cookie is present."""
        if not raw_token:
            return
        token = self._sessions.find_for_update(raw_token)
        if token is None:
            return
        self._sessions.revoke_family(token.family_id)
        user = self._session.get(User, token.user_id)
        if user is not None:
            self._audit.record(
                "auth.logout",
                entity_type="user",
                entity_id=user.id,
                organization_id=user.organization_id,
                actor_user_id=user.id,
                context=context,
            )

    # --- Password recovery ----------------------------------------------------------

    def request_password_reset(self, email: str, context: RequestContext) -> OutgoingEmail | None:
        """Returns the email to send, or None. Callers must respond identically either way."""
        user = self._users.get_by_email(email)
        if user is None or not user.is_active:
            return None

        now = utcnow()
        self._session.execute(
            update(PasswordResetToken)
            .where(PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None))
            .values(used_at=now)
        )
        raw = generate_opaque_token()
        self._session.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=hash_opaque_token(raw),
                expires_at=now + timedelta(minutes=self._settings.password_reset_ttl_minutes),
            )
        )
        self._audit.record(
            "auth.password_reset_requested",
            entity_type="user",
            entity_id=user.id,
            organization_id=user.organization_id,
            actor_user_id=None,
            context=context,
        )
        link = f"{self._settings.frontend_url.rstrip('/')}/restablecer-contrasena?token={raw}"
        minutes = self._settings.password_reset_ttl_minutes
        return OutgoingEmail(
            to=user.email,
            subject="ERMS – Restablecer contraseña",
            text=(
                f"Hola {user.full_name}:\n\n"
                "Recibimos una solicitud para restablecer su contraseña de ERMS.\n"
                f"Use este enlace (válido por {minutes} minutos, un solo uso):\n\n{link}\n\n"
                "Si usted no lo solicitó, ignore este mensaje: su contraseña no cambiará.\n"
            ),
        )

    def reset_password(self, raw_token: str, new_password: str, context: RequestContext) -> None:
        now = utcnow()
        reset = self._session.scalar(
            select(PasswordResetToken)
            .where(PasswordResetToken.token_hash == hash_opaque_token(raw_token))
            .with_for_update()
        )
        if reset is None or reset.used_at is not None or reset.expires_at <= now:
            raise AuthenticationError("El enlace no es válido o ya expiró. Solicite uno nuevo.")
        user = self._session.get(User, reset.user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("El enlace no es válido o ya expiró. Solicite uno nuevo.")

        ensure_password_policy(self._settings, new_password, email=user.email)
        reset.used_at = now
        self._set_password(user, new_password, must_change=False)
        user.failed_login_count = 0
        user.locked_until = None
        self._sessions.revoke_all_for_user(user.id)
        self._audit.record(
            "auth.password_reset",
            entity_type="user",
            entity_id=user.id,
            organization_id=user.organization_id,
            actor_user_id=user.id,
            context=context,
        )

    def change_password(
        self,
        user: User,
        session_id: uuid.UUID,
        current_password: str,
        new_password: str,
        context: RequestContext,
    ) -> None:
        valid, _ = verify_password(current_password, user.password_hash)
        if not valid:
            raise InvalidCredentialsError("La contraseña actual no es correcta.")
        if current_password == new_password:
            raise BusinessRuleError("La nueva contraseña debe ser diferente a la actual.")
        ensure_password_policy(self._settings, new_password, email=user.email)
        self._set_password(user, new_password, must_change=False)
        # Other devices are signed out; the current session continues.
        self._sessions.revoke_all_for_user(user.id, except_family=session_id)
        self._audit.record(
            "auth.password_changed",
            entity_type="user",
            entity_id=user.id,
            organization_id=user.organization_id,
            actor_user_id=user.id,
            context=context,
        )

    # --- Profile ---------------------------------------------------------------------

    def me(self, user: User) -> MeResponse:
        organization = self._session.get(Organization, user.organization_id)
        assert organization is not None  # noqa: S101 - FK guarantees it
        return MeResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            organization=OrganizationRef(id=organization.id, name=organization.name),
            roles=[RoleRef(id=r.id, code=r.code, name=r.name) for r in user.roles],
            permissions=sorted(user.permission_codes),
            must_change_password=user.must_change_password,
        )

    # --- Helpers ---------------------------------------------------------------------

    def _set_password(self, user: User, password: str, *, must_change: bool) -> None:
        user.password_hash = hash_password(password)
        user.password_changed_at = utcnow()
        user.must_change_password = must_change

    def _register_failure(self, user: User, context: RequestContext, *, reason: str) -> None:
        user.failed_login_count += 1
        if user.failed_login_count >= self._settings.login_max_attempts:
            user.locked_until = utcnow() + timedelta(minutes=self._settings.login_lockout_minutes)
            user.failed_login_count = 0
            reason = f"{reason}; account locked"
        self._audit_login_failure(user, context, reason=reason)

    def _audit_login_failure(self, user: User, context: RequestContext, *, reason: str) -> None:
        self._audit.record(
            "auth.login_failed",
            entity_type="user",
            entity_id=user.id,
            organization_id=user.organization_id,
            actor_user_id=None,
            context=context,
            changes={"reason": reason},
        )
        # Persist the failure even though the request ends with an error (rolled back otherwise).
        self._session.commit()

    def _result(
        self, user: User, refresh_raw: str, refresh_expires_at: datetime, session_id: uuid.UUID
    ) -> AuthResult:
        access_token, access_expires_at = create_access_token(
            self._settings,
            user_id=user.id,
            organization_id=user.organization_id,
            session_id=session_id,
        )
        return AuthResult(
            access_token=access_token,
            access_expires_at=access_expires_at,
            refresh_token=refresh_raw,
            refresh_expires_at=refresh_expires_at,
            must_change_password=user.must_change_password,
        )
