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
