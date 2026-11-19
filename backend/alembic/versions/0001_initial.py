"""Initial schema: organizations (tenant boundary).

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("tax_id", sa.String(length=32), nullable=True, comment="NIT de la organización"),
        sa.Column(
            "timezone", sa.String(length=64), server_default="America/Bogota", nullable=False
        ),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organizations")),
        sa.UniqueConstraint("slug", name=op.f("uq_organizations_slug")),
    )


def downgrade() -> None:
    op.drop_table("organizations")
