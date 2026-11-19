"""Integration tests against a real PostgreSQL.

Set ERMS_TEST_DATABASE_URL to a DISPOSABLE database: these tests downgrade it to an
empty schema and migrate it back to head.
"""

import os
from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, inspect

from app.core.config import Settings, get_settings
from app.modules.health.checks import BACKEND_ROOT, DatabaseCheck, alembic_head_revision
from app.modules.health.schemas import ComponentStatus

TEST_DB_URL = os.environ.get("ERMS_TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not TEST_DB_URL, reason="ERMS_TEST_DATABASE_URL is not set"),
]


@pytest.fixture(scope="module")
def db_url() -> Iterator[str]:
    assert TEST_DB_URL
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = TEST_DB_URL
    get_settings.cache_clear()
    yield Settings().database_url
    if previous is not None:
        os.environ["DATABASE_URL"] = previous
    get_settings.cache_clear()


@pytest.fixture(scope="module")
def alembic_config(db_url: str) -> Config:
    return Config(str(BACKEND_ROOT / "alembic.ini"))


@pytest.fixture(scope="module")
def engine(db_url: str) -> Iterator[Engine]:
    eng = create_engine(db_url)
    yield eng
    eng.dispose()


def test_migrations_upgrade_downgrade_roundtrip(alembic_config: Config, engine: Engine) -> None:
    command.downgrade(alembic_config, "base")
    assert "organizations" not in inspect(engine).get_table_names()

    command.upgrade(alembic_config, "head")
    tables = inspect(engine).get_table_names()
    assert "organizations" in tables
    assert "alembic_version" in tables


def test_database_check_ok_when_migrated(alembic_config: Config, engine: Engine) -> None:
    command.upgrade(alembic_config, "head")
    result = DatabaseCheck(engine, alembic_head_revision()).run()
    assert result.status is ComponentStatus.OK, result.detail


def test_database_check_detects_pending_migration(alembic_config: Config, engine: Engine) -> None:
    command.downgrade(alembic_config, "base")
    try:
        result = DatabaseCheck(engine, alembic_head_revision()).run()
        assert result.status is ComponentStatus.ERROR
    finally:
        command.upgrade(alembic_config, "head")
