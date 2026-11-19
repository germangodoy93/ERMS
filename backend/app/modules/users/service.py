"""User management with the protection rules agreed for Sprint 1:

- Only holders of `roles:manage` (Administrador) can grant/revoke the ADMIN role or manage
  a user who is an administrator. A Supervisor can never escalate to Administrador.
- Nobody can deactivate themselves.
- The organization always keeps at least one active administrator.
- New users get a temporary password and must change it on first login.
"""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import (
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from app.core.security import hash_password
from app.modules.audit.service import AuditService
from app.modules.auth.sessions import SessionManager
from app.modules.roles.catalog import Perm, RoleCode
from app.modules.roles.models import Role
from app.modules.users.models import User
from app.modules.users.passwords import ensure_password_policy
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import UserCreate, UserUpdate
from app.shared.context import RequestContext, utcnow
from app.shared.pagination import PageParams


class UserService:
    def __init__(self, session: Session, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._users = UserRepository(session)
        self._sessions = SessionManager(session, settings)
        self._audit = AuditService(session)

    # --- Queries ----------------------------------------------------------------

    def search(
        self,
        actor: User,
        params: PageParams,
        *,
        search: str | None,
        is_active: bool | None,
        role_code: str | None,
    ) -> tuple[list[User], int]:
        return self._users.search(
            actor.organization_id, params, search=search, is_active=is_active, role_code=role_code
        )

    def get(self, actor: User, user_id: uuid.UUID) -> User:
        user = self._users.get(actor.organization_id, user_id)
        if user is None:
            raise NotFoundError("El usuario no existe.")
        return user

    # --- Commands ---------------------------------------------------------------

    def create(self, actor: User, data: UserCreate, context: RequestContext) -> User:
        email = data.email.lower()
        if self._users.email_exists(email):
            raise ConflictError("Ya existe un usuario con ese correo electrónico.")
        roles = self._resolve_roles(actor, data.role_ids)
        if RoleCode.ADMIN in {r.code for r in roles}:
            self._require_admin_privileges(actor)
        ensure_password_policy(self._settings, data.temporary_password, email=email)

        user = User(
            organization_id=actor.organization_id,
            email=email,
            full_name=data.full_name,
            phone=data.phone,
            password_hash=hash_password(data.temporary_password),
            password_changed_at=utcnow(),
            must_change_password=True,
            roles=roles,
        )
        self._users.add(user)
        self._audit.record(
            "user.created",
            entity_type="user",
            entity_id=user.id,
            organization_id=actor.organization_id,
            actor_user_id=actor.id,
            context=context,
            changes={
                "email": email,
                "full_name": user.full_name,
                "phone": user.phone,
                "roles": sorted(r.code for r in roles),
            },
        )
        return user

    def update(
        self, actor: User, user_id: uuid.UUID, data: UserUpdate, context: RequestContext
    ) -> User:
        user = self.get(actor, user_id)
        self._guard_target(actor, user)
        fields = data.model_fields_set
        changes: dict[str, Any] = {}

        if "email" in fields and data.email is not None:
            email = data.email.lower()
            if email != user.email:
                if self._users.email_exists(email, exclude_id=user.id):
                    raise ConflictError("Ya existe un usuario con ese correo electrónico.")
                changes["email"] = [user.email, email]
                user.email = email
        if (
            "full_name" in fields
            and data.full_name is not None
            and data.full_name != user.full_name
        ):
            changes["full_name"] = [user.full_name, data.full_name]
            user.full_name = data.full_name
        if "phone" in fields and data.phone != user.phone:
            changes["phone"] = [user.phone, data.phone]
            user.phone = data.phone
        if (
            "is_active" in fields
            and data.is_active is not None
            and data.is_active != user.is_active
        ):
            if not data.is_active:
                self._ensure_can_deactivate(actor, user)
                self._sessions.revoke_all_for_user(user.id)
            else:
                user.failed_login_count = 0
                user.locked_until = None
            changes["is_active"] = [user.is_active, data.is_active]
            user.is_active = data.is_active

        if changes:
            self._audit.record(
                "user.updated",
                entity_type="user",
                entity_id=user.id,
                organization_id=actor.organization_id,
                actor_user_id=actor.id,
                context=context,
                changes=changes,
            )
        return user

    def set_roles(
        self, actor: User, user_id: uuid.UUID, role_ids: list[uuid.UUID], context: RequestContext
    ) -> User:
        user = self.get(actor, user_id)
        new_roles = self._resolve_roles(actor, role_ids)
        old_codes = user.role_codes
        new_codes = {r.code for r in new_roles}

        admin_changed = (RoleCode.ADMIN in old_codes) != (RoleCode.ADMIN in new_codes)
        if admin_changed or RoleCode.ADMIN in old_codes:
            self._require_admin_privileges(actor)
        if (
            RoleCode.ADMIN in old_codes
            and RoleCode.ADMIN not in new_codes
            and user.is_active
            and self._users.count_active_admins(actor.organization_id) <= 1
        ):
            raise BusinessRuleError(
                "No se puede quitar el rol Administrador al último administrador activo."
            )

        if old_codes != new_codes:
            user.roles = new_roles
            self._audit.record(
                "user.roles_changed",
                entity_type="user",
                entity_id=user.id,
                organization_id=actor.organization_id,
                actor_user_id=actor.id,
                context=context,
                changes={"roles": [sorted(old_codes), sorted(new_codes)]},
            )
        return user

    def set_temporary_password(
        self, actor: User, user_id: uuid.UUID, password: str, context: RequestContext
    ) -> User:
        user = self.get(actor, user_id)
        self._guard_target(actor, user)
        if user.id == actor.id:
            raise BusinessRuleError("Para su propia cuenta use 'Cambiar contraseña'.")
        ensure_password_policy(self._settings, password, email=user.email)
        user.password_hash = hash_password(password)
        user.password_changed_at = utcnow()
        user.must_change_password = True
        user.failed_login_count = 0
        user.locked_until = None
        self._sessions.revoke_all_for_user(user.id)
        self._audit.record(
            "user.temporary_password_set",
            entity_type="user",
            entity_id=user.id,
            organization_id=actor.organization_id,
            actor_user_id=actor.id,
            context=context,
        )
        return user

    # --- Rules ------------------------------------------------------------------

    def _resolve_roles(self, actor: User, role_ids: list[uuid.UUID]) -> list[Role]:
        unique_ids = set(role_ids)
        roles = list(
            self._session.scalars(
                select(Role).where(
                    Role.id.in_(unique_ids), Role.organization_id == actor.organization_id
                )
            )
        )
        if len(roles) != len(unique_ids):
            raise BusinessRuleError("Uno o más roles no existen.")
        return roles

    @staticmethod
    def _require_admin_privileges(actor: User) -> None:
        if Perm.ROLES_MANAGE not in actor.permission_codes:
            raise PermissionDeniedError(
                "Solo un Administrador puede asignar, quitar o gestionar el rol Administrador."
            )

    def _guard_target(self, actor: User, target: User) -> None:
        if RoleCode.ADMIN in target.role_codes and target.id != actor.id:
            self._require_admin_privileges(actor)

    def _ensure_can_deactivate(self, actor: User, user: User) -> None:
        if user.id == actor.id:
            raise BusinessRuleError("No puede desactivar su propia cuenta.")
        if (
            RoleCode.ADMIN in user.role_codes
            and self._users.count_active_admins(actor.organization_id) <= 1
        ):
            raise BusinessRuleError("No se puede desactivar al último administrador activo.")
