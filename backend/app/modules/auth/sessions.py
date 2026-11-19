"""Session lifecycle shared by the auth and users modules.

A session is a family of refresh tokens:
- absolute lifetime: `session_max_hours` from login (never extended);
- idle lifetime: each refresh token expires `session_idle_minutes` after issuance;
- rotation: every refresh revokes the presented token and issues a new one.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import exists, select, update
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import generate_opaque_token, hash_opaque_token
from app.modules.auth.models import RefreshToken
from app.shared.context import RequestContext, utcnow


@dataclass(frozen=True, slots=True)
class IssuedRefreshToken:
    raw: str
    record: RefreshToken


class SessionManager:
    def __init__(self, session: Session, settings: Settings) -> None:
        self._session = session
        self._settings = settings

    def issue(
        self,
        *,
        user_id: uuid.UUID,
        family_id: uuid.UUID,
        session_expires_at: datetime,
        context: RequestContext | None,
        now: datetime | None = None,
    ) -> IssuedRefreshToken:
        now = now or utcnow()
        raw = generate_opaque_token()
        record = RefreshToken(
            id=uuid.uuid4(),
            user_id=user_id,
            family_id=family_id,
            token_hash=hash_opaque_token(raw),
            expires_at=min(
                now + timedelta(minutes=self._settings.session_idle_minutes), session_expires_at
            ),
            session_expires_at=session_expires_at,
            ip_address=context.ip_address if context else None,
            user_agent=context.user_agent if context else None,
        )
        self._session.add(record)
        self._session.flush()
        return IssuedRefreshToken(raw=raw, record=record)

    def start(self, user_id: uuid.UUID, context: RequestContext | None) -> IssuedRefreshToken:
        now = utcnow()
        return self.issue(
            user_id=user_id,
            family_id=uuid.uuid4(),
            session_expires_at=now + timedelta(hours=self._settings.session_max_hours),
            context=context,
            now=now,
        )

    def find_for_update(self, raw_token: str) -> RefreshToken | None:
        return self._session.scalar(
            select(RefreshToken)
            .where(RefreshToken.token_hash == hash_opaque_token(raw_token))
            .with_for_update()
        )

    def revoke_family(self, family_id: uuid.UUID) -> None:
        self._session.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=utcnow())
        )

    def revoke_all_for_user(
        self, user_id: uuid.UUID, *, except_family: uuid.UUID | None = None
    ) -> None:
        statement = update(RefreshToken).where(
            RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None)
        )
        if except_family is not None:
            statement = statement.where(RefreshToken.family_id != except_family)
        self._session.execute(statement.values(revoked_at=utcnow()))

    def is_active(self, family_id: uuid.UUID) -> bool:
        """True while the session has a usable token (not logged out, not expired)."""
        now = utcnow()
        return bool(
            self._session.scalar(
                select(
                    exists().where(
                        RefreshToken.family_id == family_id,
                        RefreshToken.revoked_at.is_(None),
                        RefreshToken.expires_at > now,
                    )
                )
            )
        )
