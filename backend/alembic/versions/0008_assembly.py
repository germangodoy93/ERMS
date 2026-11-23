"""PC assembly: component specs on parts, builds, assembly orders and bottleneck settings.

Revision ID: 0008_assembly
Revises: 0007_warranties
Create Date: 2026-11-23
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_assembly"
down_revision: str | None = "0007_warranties"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_PERMISSIONS = {"assembly:manage": "Configurar y vender PC armadas a la medida"}
# The owner asked for the module to be used only by technicians and administrators.
GRANTS = {"ADMIN": set(NEW_PERMISSIONS), "TECHNICIAN": set(NEW_PERMISSIONS)}


def _fk(table: str, column: str, target: str, ondelete: str) -> sa.ForeignKeyConstraint:
    referred = target.split(".")[0]
    return sa.ForeignKeyConstraint(
        [column], [target], name=f"fk_{table}_{column}_{referred}", ondelete=ondelete
    )


def upgrade() -> None:
    op.add_column(
        "parts",
        sa.Column(
            "assembly_category",
            sa.String(10),
            nullable=True,
            comment="Categoría para el ensamble de PC (CPU, BOARD, …)",
        ),
    )
    op.add_column(
        "parts",
        sa.Column(
            "specs",
            postgresql.JSONB(),
            nullable=True,
            comment="Especificaciones técnicas según la categoría de ensamble",
        ),
    )
    op.create_check_constraint(
        "ck_parts_assembly_specs_together",
        "parts",
        "(assembly_category IS NULL) = (specs IS NULL)",
    )
    op.create_index(
        "ix_parts_organization_id_assembly_category",
        "parts",
        ["organization_id", "assembly_category"],
    )
    op.add_column(
        "work_orders",
        sa.Column("kind", sa.String(10), server_default="SERVICE", nullable=False),
    )
    op.create_check_constraint(
        "ck_work_orders_kind_valid", "work_orders", "kind IN ('SERVICE', 'ASSEMBLY')"
    )
    op.add_column(
        "organizations",
        sa.Column("assembly_bottleneck_gap", sa.Integer(), server_default="25", nullable=False),
    )
    op.add_column(
        "organizations",
        sa.Column("assembly_min_ram_gb", sa.Integer(), server_default="16", nullable=False),
    )

    op.create_table(
        "assembly_builds",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("profile", sa.String(10), nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("ram_units", sa.Integer(), nullable=False),
        sa.Column("labor_price", sa.Numeric(14, 2), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("work_order_id", sa.Uuid(), nullable=True),
        sa.Column("steps_done", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("created_by_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'ORDERED')", name="ck_assembly_builds_status_valid"
        ),
        sa.CheckConstraint(
            "profile IN ('OFFICE', 'DESIGN', 'GAMING')", name="ck_assembly_builds_profile_valid"
        ),
        sa.CheckConstraint("ram_units BETWEEN 1 AND 4", name="ck_assembly_builds_ram_units_valid"),
        sa.CheckConstraint("labor_price >= 0", name="ck_assembly_builds_labor_price_positive"),
        sa.CheckConstraint(
            "(status = 'ORDERED') = (work_order_id IS NOT NULL)",
            name="ck_assembly_builds_ordered_has_order",
        ),
        _fk("assembly_builds", "organization_id", "organizations.id", "RESTRICT"),
        _fk("assembly_builds", "work_order_id", "work_orders.id", "RESTRICT"),
        _fk("assembly_builds", "created_by_id", "users.id", "SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_assembly_builds"),
        sa.UniqueConstraint("work_order_id", name="uq_assembly_builds_work_order_id"),
    )
    op.create_index("ix_assembly_builds_organization_id", "assembly_builds", ["organization_id"])
    op.create_table(
        "assembly_build_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("build_id", sa.Uuid(), nullable=False),
        sa.Column("part_id", sa.Uuid(), nullable=False),
        _fk("assembly_build_items", "build_id", "assembly_builds.id", "CASCADE"),
        _fk("assembly_build_items", "part_id", "parts.id", "RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_assembly_build_items"),
    )
    op.create_index("ix_assembly_build_items_build_id", "assembly_build_items", ["build_id"])

    conn = op.get_bind()
    permissions = sa.table(
        "permissions",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
        sa.column("description", sa.String()),
    )
    op.bulk_insert(
        permissions,
        [{"id": uuid.uuid4(), "code": c, "description": d} for c, d in NEW_PERMISSIONS.items()],
    )
    for role_code, codes in GRANTS.items():
        conn.execute(
            sa.text(
                "INSERT INTO role_permissions (role_id, permission_id) "
                "SELECT r.id, p.id FROM roles r JOIN permissions p ON p.code = ANY(:codes) "
                "WHERE r.code = :role AND r.is_system"
            ),
            {"codes": sorted(codes), "role": role_code},
        )


def downgrade() -> None:
    op.drop_table("assembly_build_items")
    op.drop_table("assembly_builds")
    op.drop_column("organizations", "assembly_min_ram_gb")
    op.drop_column("organizations", "assembly_bottleneck_gap")
    op.drop_constraint("ck_work_orders_kind_valid", "work_orders", type_="check")
    op.drop_column("work_orders", "kind")
    op.drop_index("ix_parts_organization_id_assembly_category", table_name="parts")
    op.drop_constraint("ck_parts_assembly_specs_together", "parts", type_="check")
    op.drop_column("parts", "specs")
    op.drop_column("parts", "assembly_category")
    codes = sorted(NEW_PERMISSIONS)
    op.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE permission_id IN "
            "(SELECT id FROM permissions WHERE code = ANY(:codes))"
        ).bindparams(codes=codes)
    )
    op.execute(sa.text("DELETE FROM permissions WHERE code = ANY(:codes)").bindparams(codes=codes))
