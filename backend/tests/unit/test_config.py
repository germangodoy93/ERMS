import pytest

from app.core.config import Environment, Settings


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("postgres://u:p@h:5432/db", "postgresql+psycopg://u:p@h:5432/db"),
        ("postgresql://u:p@h:5432/db", "postgresql+psycopg://u:p@h:5432/db"),
        ("postgresql+psycopg://u:p@h:5432/db", "postgresql+psycopg://u:p@h:5432/db"),
    ],
)
def test_database_url_always_uses_psycopg_driver(raw: str, expected: str) -> None:
    assert Settings(database_url=raw).database_url == expected


def test_cors_origins_accept_comma_separated_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173, https://erms.example.com ,")
    settings = Settings(database_url="postgresql://u:p@h/db")
    assert settings.cors_origins == ["http://localhost:5173", "https://erms.example.com"]


def test_is_production() -> None:
    settings = Settings(database_url="postgresql://u:p@h/db", environment=Environment.PRODUCTION)
    assert settings.is_production


@pytest.mark.parametrize(
    ("env", "secret", "named"),
    [
        ({"JWT_SECRET": "short-secret-value"}, "short-secret-value", "jwt_secret"),
        (
            {"S3_BUCKET": "photos", "S3_SECRET_ACCESS_KEY": "SUPERSECRETVALUE"},
            "SUPERSECRETVALUE",
            "S3_ENDPOINT",
        ),
    ],
)
def test_invalid_configuration_never_reveals_values(
    monkeypatch: pytest.MonkeyPatch, env: dict[str, str], secret: str, named: str
) -> None:
    from app.core.config import ConfigurationError, get_settings

    for name, value in env.items():
        monkeypatch.setenv(name, value)
    get_settings.cache_clear()
    try:
        with pytest.raises(ConfigurationError) as caught:
            get_settings()
    finally:
        get_settings.cache_clear()
    message = str(caught.value)
    assert named in message
    assert secret not in message
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__
