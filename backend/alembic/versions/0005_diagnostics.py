"""Diagnostics: sessions, results and agent pairing codes.

Revision ID: 0005_diagnostics
Revises: 0004_work_orders
Create Date: 2026-11-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_diagnostics"
down_revision: str | None = "0004_work_orders"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _fk(table: str, column: str, target: str, ondelete: str) -> sa.ForeignKeyConstraint:
    referred = target.split(".")[0]
    return sa.ForeignKeyConstraint(
        [column], [target], name=f"fk_{table}_{column}_{referred}", ondelete=ondelete
    )


def _ts(name: str) -> sa.Column[object]:
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    op.create_table(
        "diagnostic_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("work_order_id", sa.Uuid(), nullable=False),
        sa.Column("started_by_id", sa.Uuid(), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_by_id", sa.Uuid(), nullable=True),
        sa.Column("conclusion", sa.Text(), nullable=True),
        sa.Column("recommendation", sa.Text(), nullable=True),
        sa.Column("agent_version", sa.String(length=20), nullable=True),
        sa.Column("agent_elevated", sa.Boolean(), nullable=True),
        sa.Column("agent_reported_at", sa.DateTime(timezone=True), nullable=True),
        _ts("created_at"),
        _ts("updated_at"),
        _fk("diagnostic_sessions", "organization_id", "organizations.id", "RESTRICT"),
        _fk("diagnostic_sessions", "work_order_id", "work_orders.id", "CASCADE"),
        _fk("diagnostic_sessions", "started_by_id", "users.id", "SET NULL"),
        _fk("diagnostic_sessions", "closed_by_id", "users.id", "SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_diagnostic_sessions"),
        sa.UniqueConstraint("work_order_id", name="uq_diagnostic_sessions_work_order_id"),
    )

    op.create_table(
        "diagnostic_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("test_code", sa.String(length=40), nullable=False),
        sa.Column("result", sa.String(length=20), nullable=False),
        sa.Column("observation", sa.Text(), nullable=True),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("recorded_by_id", sa.Uuid(), nullable=True),
        _ts("recorded_at"),
        sa.CheckConstraint(
            "result IN ('OK', 'WARNING', 'FAIL', 'NOT_TESTED', 'NOT_SUPPORTED')",
            name="ck_diagnostic_results_result_valid",
        ),
        sa.CheckConstraint(
            "source IN ('MANUAL', 'AGENT', 'AI_SUGGESTION')",
            name="ck_diagnostic_results_source_valid",
        ),
        _fk("diagnostic_results", "session_id", "diagnostic_sessions.id", "CASCADE"),
        _fk("diagnostic_results", "recorded_by_id", "users.id", "SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_diagnostic_results"),
        sa.UniqueConstraint(
            "session_id", "test_code", name="uq_diagnostic_results_session_id_test_code"
        ),
    )

    op.create_table(
        "agent_pairings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_id", sa.Uuid(), nullable=True),
        _ts("created_at"),
        sa.Column("paired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("token_hash", sa.String(length=64), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reported_at", sa.DateTime(timezone=True), nullable=True),
        _fk("agent_pairings", "organization_id", "organizations.id", "RESTRICT"),
        _fk("agent_pairings", "session_id", "diagnostic_sessions.id", "CASCADE"),
        _fk("agent_pairings", "created_by_id", "users.id", "SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_agent_pairings"),
        sa.UniqueConstraint("code_hash", name="uq_agent_pairings_code_hash"),
        sa.UniqueConstraint("token_hash", name="uq_agent_pairings_token_hash"),
    )
    op.create_index("ix_agent_pairings_session_id", "agent_pairings", ["session_id"])


def downgrade() -> None:
    op.drop_table("agent_pairings")
    op.drop_table("diagnostic_results")
    op.drop_table("diagnostic_sessions")
