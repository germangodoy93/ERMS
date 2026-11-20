"""Warranties, warranty claims and dashboard/report permissions.

Revision ID: 0007_warranties
Revises: 0006_workshop_commerce
Create Date: 2026-11-20
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_warranties"
down_revision: str | None = "0006_workshop_commerce"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_PERMISSIONS = {
    "reports:read": "Consultar el tablero del taller y los reportes",
    "warranties:manage": "Abrir y resolver reclamos de garantía",
}
GRANTS = {
    "ADMIN": set(NEW_PERMISSIONS),
    "SUPERVISOR": set(NEW_PERMISSIONS),
    "RECEPTIONIST": {"reports:read", "warranties:manage"},
}


def _fk(table: str, column: str, target: str, ondelete: str) -> sa.ForeignKeyConstraint:
    referred = target.split(".")[0]
    return sa.ForeignKeyConstraint(
        [column], [target], name=f"fk_{table}_{column}_{referred}", ondelete=ondelete
    )


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column("warranty_days", sa.Integer(), server_default="90", nullable=False),
    )
    op.add_column(
        "work_orders",
        sa.Column(
            "warranty_of_id",
            sa.Uuid(),
            nullable=True,
            comment="Orden original cuando esta orden atiende un reclamo de garantía",
        ),
    )
    op.create_foreign_key(
        "fk_work_orders_warranty_of_id_work_orders",
        "work_orders",
        "work_orders",
        ["warranty_of_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.create_table(
        "warranties",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("work_order_id", sa.Uuid(), nullable=False),
        sa.Column("days", sa.Integer(), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=False),
        sa.Column("created_by_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("days > 0", name="ck_warranties_days_positive"),
        _fk("warranties", "organization_id", "organizations.id", "RESTRICT"),
        _fk("warranties", "work_order_id", "work_orders.id", "CASCADE"),
        _fk("warranties", "created_by_id", "users.id", "SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_warranties"),
        sa.UniqueConstraint("work_order_id", name="uq_warranties_work_order_id"),
    )
    op.create_index("ix_warranties_organization_id", "warranties", ["organization_id"])
    op.create_index("ix_warranties_ends_on", "warranties", ["ends_on"])

    op.create_table(
        "warranty_claims",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("warranty_id", sa.Uuid(), nullable=False),
        sa.Column("claim_order_id", sa.Uuid(), nullable=False),
        sa.Column("reported_issue", sa.Text(), nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column("decided_by_id", sa.Uuid(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('OPEN', 'ACCEPTED', 'REJECTED')", name="ck_warranty_claims_status_valid"
        ),
        _fk("warranty_claims", "organization_id", "organizations.id", "RESTRICT"),
        _fk("warranty_claims", "warranty_id", "warranties.id", "CASCADE"),
        _fk("warranty_claims", "claim_order_id", "work_orders.id", "RESTRICT"),
        _fk("warranty_claims", "decided_by_id", "users.id", "SET NULL"),
        _fk("warranty_claims", "created_by_id", "users.id", "SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_warranty_claims"),
        sa.UniqueConstraint("claim_order_id", name="uq_warranty_claims_claim_order_id"),
    )
    op.create_index("ix_warranty_claims_warranty_id", "warranty_claims", ["warranty_id"])

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
    op.drop_table("warranty_claims")
    op.drop_table("warranties")
    op.drop_constraint(
        "fk_work_orders_warranty_of_id_work_orders", "work_orders", type_="foreignkey"
    )
    op.drop_column("work_orders", "warranty_of_id")
    op.drop_column("organizations", "warranty_days")
    codes = sorted(NEW_PERMISSIONS)
    op.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE permission_id IN "
            "(SELECT id FROM permissions WHERE code = ANY(:codes))"
        ).bindparams(codes=codes)
    )
    op.execute(sa.text("DELETE FROM permissions WHERE code = ANY(:codes)").bindparams(codes=codes))
