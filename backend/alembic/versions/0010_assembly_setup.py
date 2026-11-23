"""Assembly setup: desk shape and PC position of a build (setup parts are inventory parts).

Revision ID: 0010_assembly_setup
Revises: 0009_assembly_pricing
Create Date: 2026-11-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_assembly_setup"
down_revision: str | None = "0009_assembly_pricing"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "assembly_builds",
        sa.Column("desk_shape", sa.String(10), server_default="STRAIGHT", nullable=False),
    )
    op.add_column(
        "assembly_builds",
        sa.Column("pc_position", sa.String(10), server_default="AUTO", nullable=False),
    )
    op.create_check_constraint(
        "ck_assembly_builds_desk_shape_valid", "assembly_builds", "desk_shape IN ('STRAIGHT', 'L')"
    )
    op.create_check_constraint(
        "ck_assembly_builds_pc_position_valid",
        "assembly_builds",
        "pc_position IN ('AUTO', 'DESK', 'FLOOR')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_assembly_builds_pc_position_valid", "assembly_builds", type_="check")
    op.drop_constraint("ck_assembly_builds_desk_shape_valid", "assembly_builds", type_="check")
    op.drop_column("assembly_builds", "pc_position")
    op.drop_column("assembly_builds", "desk_shape")
