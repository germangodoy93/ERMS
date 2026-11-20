"""Authentication and authorization dependencies used by every protected endpoint.

@router.get(..., dependencies=[Depends(require_permissions(Perm.USERS_READ))])
def handler(user: CurrentUser): ...
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.core.exceptions import (
    AuthenticationError,
    PasswordChangeRequiredError,
    PermissionDeniedError,
)
from app.core.security import InvalidAccessTokenError, decode_access_token
from app.modules.auth.service import SESSION_EXPIRED_MESSAGE, AuthService
from app.modules.auth.sessions import SessionManager
from app.modules.roles.catalog import Perm
from app.modules.users.models import User

_bearer = HTTPBearer(auto_error=False, description="Access token obtenido en /auth/login")

DbSession = Annotated[Session, Depends(get_db_session)]
AppSettings = Annotated[Settings, Depends(get_settings)]


@dataclass(frozen=True, slots=True)
class Principal:
    user: User
    session_id: uuid.UUID


def get_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    session: DbSession,
    settings: AppSettings,
) -> Principal:
    """Authenticated user, even if they still must change a temporary password."""
    if credentials is None:
        raise AuthenticationError("Debe iniciar sesión.")
    try:
        claims = decode_access_token(settings, credentials.credentials)
    except InvalidAccessTokenError as exc:
        raise AuthenticationError(SESSION_EXPIRED_MESSAGE) from exc

    user = session.get(User, claims.user_id)
    if (
        user is None
        or not user.is_active
        or user.organization_id != claims.organization_id
        or not SessionManager(session, settings).is_active(claims.session_id)
    ):
        raise AuthenticationError(SESSION_EXPIRED_MESSAGE)
    return Principal(user=user, session_id=claims.session_id)


def get_current_user(principal: Annotated[Principal, Depends(get_principal)]) -> User:
    """Authenticated user who is allowed to use the application."""
    if principal.user.must_change_password:
        raise PasswordChangeRequiredError("Debe cambiar su contraseña temporal antes de continuar.")
    return principal.user


CurrentPrincipal = Annotated[Principal, Depends(get_principal)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def require_permissions(*required: Perm) -> Callable[[User], User]:
    def dependency(user: CurrentUser) -> User:
        missing = set(required) - user.permission_codes
        if missing:
            raise PermissionDeniedError("No tiene permisos para realizar esta acción.")
        return user

    return dependency


def require_any_permission(*options: Perm) -> Callable[[User], User]:
    def dependency(user: CurrentUser) -> User:
        if not set(options) & user.permission_codes:
            raise PermissionDeniedError("No tiene permisos para realizar esta acción.")
        return user

    return dependency


def get_auth_service(session: DbSession, settings: AppSettings) -> AuthService:
    return AuthService(session, settings)
