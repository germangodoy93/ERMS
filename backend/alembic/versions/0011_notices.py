"""Customer notices by WhatsApp: editable templates, log of prepared notices, permission.

Revision ID: 0011_notices
Revises: 0010_assembly_setup
Create Date: 2026-11-26
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_notices"
down_revision: str | None = "0010_assembly_setup"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_PERMISSIONS = {"customers:notify": "Preparar avisos al cliente por WhatsApp"}
# Customer-facing roles; technicians can be granted it from the roles screen.
GRANTS = {
    "ADMIN": set(NEW_PERMISSIONS),
    "SUPERVISOR": set(NEW_PERMISSIONS),
    "RECEPTIONIST": set(NEW_PERMISSIONS),
}
KINDS = "'RECEIVED', 'QUOTE_READY', 'READY', 'NOT_REPAIRED', 'REMINDER', 'DELIVERED', 'FREE'"


def upgrade() -> None:
    op.create_table(
        "notice_templates",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("updated_by_id", sa.Uuid(), nullable=True),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(f"kind IN ({KINDS})", name="ck_notice_templates_kind_valid"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_notice_templates_organization_id_organizations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_id"],
            ["users.id"],
            name="fk_notice_templates_updated_by_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("organization_id", "kind", name="pk_notice_templates"),
    )
    op.create_table(
        "work_order_notices",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("work_order_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("prepared_by_id", sa.Uuid(), nullable=True),
        sa.Column(
            "prepared_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(f"kind IN ({KINDS})", name="ck_work_order_notices_kind_valid"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_work_order_notices_organization_id_organizations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["work_order_id"],
            ["work_orders.id"],
            name="fk_work_order_notices_work_order_id_work_orders",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["prepared_by_id"],
            ["users.id"],
            name="fk_work_order_notices_prepared_by_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_work_order_notices"),
    )
    op.create_index(
        "ix_work_order_notices_organization_id", "work_order_notices", ["organization_id"]
    )
    op.create_index(
        "ix_work_order_notices_work_order_id_prepared_at",
        "work_order_notices",
        ["work_order_id", "prepared_at"],
    )

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
    op.drop_table("work_order_notices")
    op.drop_table("notice_templates")
    codes = sorted(NEW_PERMISSIONS)
    op.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE permission_id IN "
            "(SELECT id FROM permissions WHERE code = ANY(:codes))"
        ).bindparams(codes=codes)
    )
    op.execute(sa.text("DELETE FROM permissions WHERE code = ANY(:codes)").bindparams(codes=codes))
