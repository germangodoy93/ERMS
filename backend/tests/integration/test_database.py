"""Migrations against a real PostgreSQL (ERMS_TEST_DATABASE_URL, disposable)."""

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import Engine, inspect, text

from app.modules.health.checks import DatabaseCheck, alembic_head_revision
from app.modules.health.schemas import ComponentStatus
from app.modules.roles.catalog import Perm
from app.shared.registry import Base


def test_migrations_upgrade_downgrade_roundtrip(alembic_config: Config, engine: Engine) -> None:
    command.downgrade(alembic_config, "base")
    assert "organizations" not in inspect(engine).get_table_names()

    command.upgrade(alembic_config, "head")
    tables = set(inspect(engine).get_table_names())
    assert {"organizations", "users", "roles", "audit_logs", "alembic_version"} <= tables


def test_permission_catalog_is_seeded(engine: Engine) -> None:
    with engine.connect() as conn:
        codes = set(conn.scalars(text("SELECT code FROM permissions")))
    assert codes == {str(p) for p in Perm}


def test_models_match_migrations(engine: Engine) -> None:
    """Autogenerate must find nothing: ORM models and migrations describe the same schema."""
    with engine.connect() as conn:
        context = MigrationContext.configure(conn, opts={"compare_type": True})
        diff = compare_metadata(context, Base.metadata)
    assert diff == [], f"Models and migrations differ: {diff}"


def test_database_check_ok_when_migrated(engine: Engine) -> None:
    result = DatabaseCheck(engine, alembic_head_revision()).run()
    assert result.status is ComponentStatus.OK, result.detail


def test_database_check_detects_pending_migration(alembic_config: Config, engine: Engine) -> None:
    command.downgrade(alembic_config, "base")
    try:
        result = DatabaseCheck(engine, alembic_head_revision()).run()
        assert result.status is ComponentStatus.ERROR
    finally:
        command.upgrade(alembic_config, "head")
