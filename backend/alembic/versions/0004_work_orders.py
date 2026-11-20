"""Work orders, status history, document sequences, reception terms and attachments.

Revision ID: 0004_work_orders
Revises: 0003_customers_devices
Create Date: 2026-11-20
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_work_orders"
down_revision: str | None = "0003_customers_devices"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Frozen copies of the catalog at this revision.
NEW_PERMISSIONS = {
    "work_orders:read": "Consultar órdenes de servicio",
    "work_orders:create": "Recibir equipos y crear órdenes de servicio",
    "work_orders:assign": "Asignar técnicos a las órdenes",
    "work_orders:progress": "Avanzar las etapas técnicas de las órdenes",
    "work_orders:deliver": "Registrar decisiones del cliente, cancelar y entregar equipos",
}
GRANTS = {
    "ADMIN": set(NEW_PERMISSIONS),
    "SUPERVISOR": set(NEW_PERMISSIONS),
    "RECEPTIONIST": {
        "work_orders:read",
        "work_orders:create",
        "work_orders:assign",
        "work_orders:deliver",
    },
    "TECHNICIAN": {"work_orders:read", "work_orders:progress"},
}


def _fk(table: str, column: str, target: str, ondelete: str) -> sa.ForeignKeyConstraint:
    referred = target.split(".")[0]
    return sa.ForeignKeyConstraint(
        [column], [target], name=f"fk_{table}_{column}_{referred}", ondelete=ondelete
    )


def upgrade() -> None:
    op.create_table(
        "document_sequences",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("doc_type", sa.String(length=20), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("last_value", sa.Integer(), nullable=False),
        _fk("document_sequences", "organization_id", "organizations.id", "RESTRICT"),
        sa.PrimaryKeyConstraint(
            "organization_id", "doc_type", "year", name="pk_document_sequences"
        ),
    )

    op.create_table(
        "reception_terms",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_by_id", sa.Uuid(), nullable=True),
        _fk("reception_terms", "organization_id", "organizations.id", "RESTRICT"),
        _fk("reception_terms", "published_by_id", "users.id", "SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_reception_terms"),
        sa.UniqueConstraint(
            "organization_id", "version", name="uq_reception_terms_organization_id_version"
        ),
    )
    op.create_index("ix_reception_terms_organization_id", "reception_terms", ["organization_id"])

    op.create_table(
        "work_orders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("branch_id", sa.Uuid(), nullable=False),
        sa.Column("number", sa.String(length=20), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.Uuid(), nullable=False),
        sa.Column("assigned_technician_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("priority", sa.String(length=10), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_by_id", sa.Uuid(), nullable=True),
        sa.Column("reported_issue", sa.Text(), nullable=False),
        sa.Column("physical_condition", sa.Text(), nullable=False),
        sa.Column(
            "accessories",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column("unlock_method", sa.String(length=20), nullable=False),
        sa.Column("estimated_delivery_date", sa.Date(), nullable=True),
        sa.Column("diagnostic_fee", sa.Numeric(14, 2), server_default="0", nullable=False),
        sa.Column("advance_amount", sa.Numeric(14, 2), server_default="0", nullable=False),
        sa.Column("advance_method", sa.String(length=10), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("terms_id", sa.Uuid(), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_to_name", sa.String(length=200), nullable=True),
        sa.Column("delivered_to_document", sa.String(length=40), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("diagnostic_fee >= 0", name="ck_work_orders_diagnostic_fee_positive"),
        sa.CheckConstraint("advance_amount >= 0", name="ck_work_orders_advance_amount_positive"),
        sa.CheckConstraint(
            "advance_amount = 0 OR advance_method IS NOT NULL",
            name="ck_work_orders_advance_has_method",
        ),
        _fk("work_orders", "organization_id", "organizations.id", "RESTRICT"),
        _fk("work_orders", "branch_id", "branches.id", "RESTRICT"),
        _fk("work_orders", "customer_id", "customers.id", "RESTRICT"),
        _fk("work_orders", "device_id", "devices.id", "RESTRICT"),
        _fk("work_orders", "assigned_technician_id", "users.id", "RESTRICT"),
        _fk("work_orders", "received_by_id", "users.id", "SET NULL"),
        _fk("work_orders", "terms_id", "reception_terms.id", "RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_work_orders"),
        sa.UniqueConstraint(
            "organization_id", "number", name="uq_work_orders_organization_id_number"
        ),
    )
    op.create_index("ix_work_orders_customer_id", "work_orders", ["customer_id"])
    op.create_index("ix_work_orders_device_id", "work_orders", ["device_id"])
    op.create_index(
        "ix_work_orders_assigned_technician_id", "work_orders", ["assigned_technician_id"]
    )
    op.create_index(
        "ix_work_orders_organization_id_status", "work_orders", ["organization_id", "status"]
    )
    op.create_index(
        "ix_work_orders_organization_id_received_at",
        "work_orders",
        ["organization_id", "received_at"],
    )

    op.create_table(
        "work_order_status_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("work_order_id", sa.Uuid(), nullable=False),
        sa.Column("from_status", sa.String(length=30), nullable=True),
        sa.Column("to_status", sa.String(length=30), nullable=False),
        sa.Column("changed_by_id", sa.Uuid(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "changed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        _fk("work_order_status_history", "work_order_id", "work_orders.id", "CASCADE"),
        _fk("work_order_status_history", "changed_by_id", "users.id", "SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_work_order_status_history"),
    )
    op.create_index(
        "ix_work_order_status_history_order_changed",
        "work_order_status_history",
        ["work_order_id", "changed_at"],
    )

    op.create_table(
        "attachments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(length=30), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("storage_key", sa.String(length=255), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("uploaded_by_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        _fk("attachments", "organization_id", "organizations.id", "RESTRICT"),
        _fk("attachments", "uploaded_by_id", "users.id", "SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_attachments"),
        sa.UniqueConstraint("storage_key", name="uq_attachments_storage_key"),
    )
    op.create_index("ix_attachments_entity", "attachments", ["entity_type", "entity_id"])

    _seed_permissions()


def _seed_permissions() -> None:
    conn = op.get_bind()
    permissions = sa.table(
        "permissions",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
        sa.column("description", sa.String()),
    )
    op.bulk_insert(
        permissions,
        [
            {"id": uuid.uuid4(), "code": code, "description": description}
            for code, description in NEW_PERMISSIONS.items()
        ],
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
    op.drop_table("attachments")
    op.drop_table("work_order_status_history")
    op.drop_table("work_orders")
    op.drop_table("reception_terms")
    op.drop_table("document_sequences")
    codes = sorted(NEW_PERMISSIONS)
    op.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE permission_id IN "
            "(SELECT id FROM permissions WHERE code = ANY(:codes))"
        ).bindparams(codes=codes)
    )
    op.execute(sa.text("DELETE FROM permissions WHERE code = ANY(:codes)").bindparams(codes=codes))
