"""Cryptographic primitives: password hashing, access tokens and opaque tokens.

- Passwords: Argon2id via pwdlib (ADR-002).
- Access tokens: short-lived JWT (HS256) carrying identity only, never permissions.
- Refresh / reset tokens: random opaque values; only their SHA-256 hash is stored.
"""

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.core.config import Settings

_password_hash = PasswordHash((Argon2Hasher(),))

# Verifying against a fixed hash when the user does not exist keeps response times
# similar for existing and non-existing accounts (prevents user enumeration).
_DUMMY_HASH = _password_hash.hash(secrets.token_urlsafe(16))

ACCESS_TOKEN_TYPE = "access"  # noqa: S105 - token type label, not a secret


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str | None) -> tuple[bool, str | None]:
    """Returns (valid, new_hash). `new_hash` is set when parameters were upgraded."""
    if password_hash is None:
        _password_hash.verify(password, _DUMMY_HASH)
        return False, None
    return _password_hash.verify_and_update(password, password_hash)


def burn_password_check(password: str) -> None:
    """Spend the same time as a real verification (unknown user)."""
    _password_hash.verify(password, _DUMMY_HASH)


def generate_opaque_token() -> str:
    return secrets.token_urlsafe(32)


def hash_opaque_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class AccessTokenClaims:
    user_id: uuid.UUID
    organization_id: uuid.UUID
    session_id: uuid.UUID
    expires_at: datetime


class InvalidAccessTokenError(Exception):
    pass


def create_access_token(
    settings: Settings,
    *,
    user_id: uuid.UUID,
    organization_id: uuid.UUID,
    session_id: uuid.UUID,
    now: datetime | None = None,
) -> tuple[str, datetime]:
    issued_at = now or datetime.now(UTC)
    expires_at = issued_at + timedelta(minutes=settings.access_token_ttl_minutes)
    payload = {
        "sub": str(user_id),
        "org": str(organization_id),
        "sid": str(session_id),
        "typ": ACCESS_TOKEN_TYPE,
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
        "jti": uuid.uuid4().hex,
    }
    token = jwt.encode(
        payload, settings.jwt_secret.get_secret_value(), algorithm=settings.jwt_algorithm
    )
    return token, expires_at


def decode_access_token(settings: Settings, token: str) -> AccessTokenClaims:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "org", "sid", "exp", "iat", "typ"]},
        )
        if payload["typ"] != ACCESS_TOKEN_TYPE:
            raise InvalidAccessTokenError("wrong token type")
        return AccessTokenClaims(
            user_id=uuid.UUID(payload["sub"]),
            organization_id=uuid.UUID(payload["org"]),
            session_id=uuid.UUID(payload["sid"]),
            expires_at=datetime.fromtimestamp(payload["exp"], tz=UTC),
        )
    except (jwt.PyJWTError, ValueError, KeyError) as exc:
        raise InvalidAccessTokenError(str(exc)) from exc


def password_policy_errors(password: str, *, email: str, min_length: int) -> list[str]:
    """Returns human-readable reasons why a password is not acceptable (empty = valid)."""
    errors: list[str] = []
    if len(password) < min_length:
        errors.append(f"Debe tener al menos {min_length} caracteres.")
    if len(password) > 128:
        errors.append("Debe tener como máximo 128 caracteres.")
    local_part = email.split("@", 1)[0].lower()
    if len(local_part) >= 3 and local_part in password.lower():
        errors.append("No puede contener el usuario de su correo electrónico.")
    if password.strip() != password:
        errors.append("No puede empezar ni terminar con espacios.")
    return errors
