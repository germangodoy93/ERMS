import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.config import Settings
from app.core.security import (
    InvalidAccessTokenError,
    create_access_token,
    decode_access_token,
    hash_opaque_token,
    hash_password,
    password_policy_errors,
    verify_password,
)


@pytest.fixture
def settings() -> Settings:
    return Settings(database_url="postgresql://u:p@h/db")


def test_password_hash_is_argon2_and_verifies() -> None:
    hashed = hash_password("Una-clave-larga-123")
    assert hashed.startswith("$argon2id$")
    assert verify_password("Una-clave-larga-123", hashed)[0] is True
    assert verify_password("otra", hashed)[0] is False


def test_verify_without_hash_never_succeeds() -> None:
    assert verify_password("cualquiera", None) == (False, None)


def test_opaque_token_hash_is_deterministic_sha256() -> None:
    assert hash_opaque_token("abc") == hash_opaque_token("abc")
    assert len(hash_opaque_token("abc")) == 64


def test_access_token_roundtrip(settings: Settings) -> None:
    ids = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    token, expires_at = create_access_token(
        settings, user_id=ids[0], organization_id=ids[1], session_id=ids[2]
    )
    claims = decode_access_token(settings, token)
    assert (claims.user_id, claims.organization_id, claims.session_id) == ids
    assert claims.expires_at == expires_at.replace(microsecond=0)


def test_expired_access_token_is_rejected(settings: Settings) -> None:
    long_ago = datetime.now(UTC) - timedelta(hours=1)
    token, _ = create_access_token(
        settings,
        user_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        session_id=uuid.uuid4(),
        now=long_ago,
    )
    with pytest.raises(InvalidAccessTokenError):
        decode_access_token(settings, token)


def test_token_signed_with_another_key_is_rejected(settings: Settings) -> None:
    other = settings.model_copy(update={"jwt_secret": settings.jwt_secret.__class__("x" * 40)})
    token, _ = create_access_token(
        other, user_id=uuid.uuid4(), organization_id=uuid.uuid4(), session_id=uuid.uuid4()
    )
    with pytest.raises(InvalidAccessTokenError):
        decode_access_token(settings, token)


def test_token_of_another_type_is_rejected(settings: Settings) -> None:
    now = int(datetime.now(UTC).timestamp())
    payload = {
        "sub": str(uuid.uuid4()),
        "org": str(uuid.uuid4()),
        "sid": str(uuid.uuid4()),
        "typ": "refresh",
        "iat": now,
        "exp": now + 60,
    }
    token = jwt.encode(payload, settings.jwt_secret.get_secret_value(), algorithm="HS256")
    with pytest.raises(InvalidAccessTokenError):
        decode_access_token(settings, token)


def test_unsigned_token_is_rejected(settings: Settings) -> None:
    token = jwt.encode({"sub": "x"}, key="", algorithm="none")
    with pytest.raises(InvalidAccessTokenError):
        decode_access_token(settings, token)


@pytest.mark.parametrize(
    ("password", "expected_errors"),
    [
        ("Una-clave-muy-segura", 0),
        ("corta", 1),
        ("juan.perez-2026-clave", 1),  # contains the email's user part
        (" con-espacios-al-inicio", 1),
    ],
)
def test_password_policy(password: str, expected_errors: int) -> None:
    errors = password_policy_errors(password, email="juan.perez@example.com", min_length=12)
    assert len(errors) == expected_errors, errors


def test_short_jwt_secret_is_rejected() -> None:
    with pytest.raises(ValueError, match="JWT_SECRET"):
        Settings(database_url="postgresql://u:p@h/db", jwt_secret="corto")


def test_cookie_secure_defaults_to_production_only() -> None:
    dev = Settings(database_url="postgresql://u:p@h/db")
    prod = Settings(database_url="postgresql://u:p@h/db", environment="production")
    assert dev.cookie_secure is False
    assert prod.cookie_secure is True
