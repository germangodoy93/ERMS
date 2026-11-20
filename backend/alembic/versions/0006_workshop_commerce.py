"""Inventory, quotations, repairs, quality control and payments.

Revision ID: 0006_workshop_commerce
Revises: 0005_diagnostics
Create Date: 2026-11-20
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_workshop_commerce"
down_revision: str | None = "0005_diagnostics"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_PERMISSIONS = {
    "work_orders:deliver_with_balance": "Autorizar la entrega de equipos con saldo pendiente",
    "inventory:read": "Consultar repuestos y existencias",
    "inventory:manage": "Administrar repuestos, proveedores, entradas y ajustes de inventario",
    "quotes:manage": "Elaborar y enviar cotizaciones",
    "quotes:discount": "Autorizar descuentos mayores al 10 %",
    "repairs:manage": "Registrar reparaciones, consumir repuestos y hacer control de calidad",
    "payments:manage": "Registrar pagos y emitir comprobantes",
}
GRANTS = {
    "ADMIN": set(NEW_PERMISSIONS),
    "SUPERVISOR": set(NEW_PERMISSIONS),
    "TECHNICIAN": {"inventory:read", "quotes:manage", "repairs:manage"},
    "RECEPTIONIST": {"inventory:read", "quotes:manage", "payments:manage"},
}
MONEY = sa.Numeric(14, 2)
RATE = sa.Numeric(5, 2)


def _fk(table: str, column: str, target: str, ondelete: str) -> sa.ForeignKeyConstraint:
    referred = target.split(".")[0]
    return sa.ForeignKeyConstraint(
        [column], [target], name=f"fk_{table}_{column}_{referred}", ondelete=ondelete
    )


def _now(name: str) -> sa.Column[object]:
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    op.create_table(
        "suppliers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("tax_id", sa.String(32), nullable=True),
        sa.Column("contact_name", sa.String(160), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("email", sa.String(254), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        _now("created_at"),
        _now("updated_at"),
        _fk("suppliers", "organization_id", "organizations.id", "RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_suppliers"),
        sa.UniqueConstraint("organization_id", "name", name="uq_suppliers_organization_id_name"),
    )
    op.create_index("ix_suppliers_organization_id", "suppliers", ["organization_id"])

    op.create_table(
        "parts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("sku", sa.String(40), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("kind", sa.String(12), nullable=False),
        sa.Column("unit_cost", MONEY, nullable=False),
        sa.Column("sale_price", MONEY, nullable=False),
        sa.Column("tax_rate", RATE, nullable=False),
        sa.Column("price_includes_tax", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("min_stock", sa.Integer(), server_default="0", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        _now("created_at"),
        _now("updated_at"),
        sa.CheckConstraint(
            "kind IN ('PART', 'COMPONENT', 'ACCESSORY', 'CONSUMABLE')", name="ck_parts_kind_valid"
        ),
        sa.CheckConstraint("unit_cost >= 0 AND sale_price >= 0", name="ck_parts_prices_positive"),
        sa.CheckConstraint("tax_rate IN (0, 19)", name="ck_parts_tax_rate_valid"),
        sa.CheckConstraint("min_stock >= 0", name="ck_parts_min_stock_positive"),
        _fk("parts", "organization_id", "organizations.id", "RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_parts"),
        sa.UniqueConstraint("organization_id", "sku", name="uq_parts_organization_id_sku"),
    )
    op.create_index("ix_parts_organization_id", "parts", ["organization_id"])

    op.create_table(
        "stock_levels",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("part_id", sa.Uuid(), nullable=False),
        sa.Column("branch_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.CheckConstraint("quantity >= 0", name="ck_stock_levels_quantity_not_negative"),
        _fk("stock_levels", "part_id", "parts.id", "RESTRICT"),
        _fk("stock_levels", "branch_id", "branches.id", "RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_stock_levels"),
        sa.UniqueConstraint("part_id", "branch_id", name="uq_stock_levels_part_id_branch_id"),
    )
    op.create_index("ix_stock_levels_branch_id", "stock_levels", ["branch_id"])

    op.create_table(
        "stock_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("branch_id", sa.Uuid(), nullable=False),
        sa.Column("supplier_id", sa.Uuid(), nullable=True),
        sa.Column("invoice_number", sa.String(40), nullable=True),
        sa.Column("received_on", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=True),
        _now("created_at"),
        _fk("stock_entries", "organization_id", "organizations.id", "RESTRICT"),
        _fk("stock_entries", "branch_id", "branches.id", "RESTRICT"),
        _fk("stock_entries", "supplier_id", "suppliers.id", "RESTRICT"),
        _fk("stock_entries", "created_by_id", "users.id", "SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_stock_entries"),
    )
    op.create_index("ix_stock_entries_organization_id", "stock_entries", ["organization_id"])

    op.create_table(
        "inventory_movements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("part_id", sa.Uuid(), nullable=False),
        sa.Column("branch_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(12), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("stock_after", sa.Integer(), nullable=False),
        sa.Column("unit_cost", MONEY, nullable=True),
        sa.Column("reference_type", sa.String(30), nullable=True),
        sa.Column("reference_id", sa.Uuid(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=True),
        _now("created_at"),
        sa.CheckConstraint(
            "kind IN ('IN', 'OUT', 'ADJUSTMENT', 'RETURN')",
            name="ck_inventory_movements_kind_valid",
        ),
        sa.CheckConstraint("quantity <> 0", name="ck_inventory_movements_quantity_not_zero"),
        sa.CheckConstraint(
            "stock_after >= 0", name="ck_inventory_movements_stock_after_not_negative"
        ),
        _fk("inventory_movements", "organization_id", "organizations.id", "RESTRICT"),
        _fk("inventory_movements", "part_id", "parts.id", "RESTRICT"),
        _fk("inventory_movements", "branch_id", "branches.id", "RESTRICT"),
        _fk("inventory_movements", "created_by_id", "users.id", "SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_inventory_movements"),
    )
    op.create_index(
        "ix_inventory_movements_organization_id", "inventory_movements", ["organization_id"]
    )
    op.create_index(
        "ix_inventory_movements_part_created", "inventory_movements", ["part_id", "created_at"]
    )
    op.create_index(
        "ix_inventory_movements_reference",
        "inventory_movements",
        ["reference_type", "reference_id"],
    )

    op.create_table(
        "quotations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("work_order_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("subtotal", MONEY, nullable=False),
        sa.Column("discount_total", MONEY, nullable=False),
        sa.Column("tax_total", MONEY, nullable=False),
        sa.Column("total", MONEY, nullable=False),
        sa.Column("discount_authorized_by_id", sa.Uuid(), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_by_id", sa.Uuid(), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("responded_by_id", sa.Uuid(), nullable=True),
        sa.Column("response_channel", sa.String(10), nullable=True),
        _now("created_at"),
        _now("updated_at"),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'SENT', 'ACCEPTED', 'REJECTED', 'SUPERSEDED')",
            name="ck_quotations_status_valid",
        ),
        _fk("quotations", "organization_id", "organizations.id", "RESTRICT"),
        _fk("quotations", "work_order_id", "work_orders.id", "CASCADE"),
        _fk("quotations", "discount_authorized_by_id", "users.id", "SET NULL"),
        _fk("quotations", "created_by_id", "users.id", "SET NULL"),
        _fk("quotations", "sent_by_id", "users.id", "SET NULL"),
        _fk("quotations", "responded_by_id", "users.id", "SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_quotations"),
        sa.UniqueConstraint("work_order_id", "version", name="uq_quotations_work_order_id_version"),
    )
    op.create_index("ix_quotations_work_order_id", "quotations", ["work_order_id"])

    op.create_table(
        "quotation_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("quotation_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("part_id", sa.Uuid(), nullable=True),
        sa.Column("description", sa.String(300), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 2), nullable=False),
        sa.Column("unit_price", MONEY, nullable=False),
        sa.Column("discount_percent", RATE, nullable=False),
        sa.Column("tax_rate", RATE, nullable=False),
        sa.Column("price_includes_tax", sa.Boolean(), nullable=False),
        sa.Column("discount_amount", MONEY, nullable=False),
        sa.Column("base_amount", MONEY, nullable=False),
        sa.Column("tax_amount", MONEY, nullable=False),
        sa.Column("total_amount", MONEY, nullable=False),
        sa.CheckConstraint("kind IN ('LABOR', 'PART')", name="ck_quotation_items_kind_valid"),
        sa.CheckConstraint("quantity > 0", name="ck_quotation_items_quantity_positive"),
        sa.CheckConstraint("unit_price >= 0", name="ck_quotation_items_unit_price_positive"),
        sa.CheckConstraint(
            "discount_percent >= 0 AND discount_percent <= 100",
            name="ck_quotation_items_discount_valid",
        ),
        sa.CheckConstraint("tax_rate IN (0, 19)", name="ck_quotation_items_tax_rate_valid"),
        _fk("quotation_items", "quotation_id", "quotations.id", "CASCADE"),
        _fk("quotation_items", "part_id", "parts.id", "RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_quotation_items"),
    )
    op.create_index("ix_quotation_items_quotation_id", "quotation_items", ["quotation_id"])

    op.create_table(
        "repair_tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("work_order_id", sa.Uuid(), nullable=False),
        sa.Column("technician_id", sa.Uuid(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("labor_minutes", sa.Integer(), nullable=True),
        _now("created_at"),
        sa.CheckConstraint(
            "labor_minutes IS NULL OR labor_minutes >= 0", name="ck_repair_tasks_labor_positive"
        ),
        _fk("repair_tasks", "organization_id", "organizations.id", "RESTRICT"),
        _fk("repair_tasks", "work_order_id", "work_orders.id", "CASCADE"),
        _fk("repair_tasks", "technician_id", "users.id", "SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_repair_tasks"),
    )
    op.create_index("ix_repair_tasks_work_order_id", "repair_tasks", ["work_order_id"])

    op.create_table(
        "repair_parts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("part_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_cost", MONEY, nullable=False),
        sa.Column("movement_id", sa.Uuid(), nullable=False),
        sa.Column("returned_movement_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint("quantity > 0", name="ck_repair_parts_quantity_positive"),
        _fk("repair_parts", "task_id", "repair_tasks.id", "CASCADE"),
        _fk("repair_parts", "part_id", "parts.id", "RESTRICT"),
        _fk("repair_parts", "movement_id", "inventory_movements.id", "RESTRICT"),
        _fk("repair_parts", "returned_movement_id", "inventory_movements.id", "RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_repair_parts"),
    )
    op.create_index("ix_repair_parts_task_id", "repair_parts", ["task_id"])

    op.create_table(
        "quality_checks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("work_order_id", sa.Uuid(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("results", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("checked_by_id", sa.Uuid(), nullable=True),
        _now("checked_at"),
        _fk("quality_checks", "organization_id", "organizations.id", "RESTRICT"),
        _fk("quality_checks", "work_order_id", "work_orders.id", "CASCADE"),
        _fk("quality_checks", "checked_by_id", "users.id", "SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_quality_checks"),
    )
    op.create_index("ix_quality_checks_work_order_id", "quality_checks", ["work_order_id"])

    op.create_table(
        "payments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("work_order_id", sa.Uuid(), nullable=False),
        sa.Column("receipt_number", sa.String(20), nullable=True),
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("amount", MONEY, nullable=False),
        sa.Column("method", sa.String(10), nullable=False),
        sa.Column("reference", sa.String(80), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("received_by_id", sa.Uuid(), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_payments_amount_positive"),
        sa.CheckConstraint("kind IN ('ADVANCE', 'PAYMENT')", name="ck_payments_kind_valid"),
        sa.CheckConstraint(
            "method IN ('CASH', 'TRANSFER', 'CARD', 'NEQUI', 'DAVIPLATA')",
            name="ck_payments_method_valid",
        ),
        _fk("payments", "organization_id", "organizations.id", "RESTRICT"),
        _fk("payments", "work_order_id", "work_orders.id", "RESTRICT"),
        _fk("payments", "received_by_id", "users.id", "SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_payments"),
        sa.UniqueConstraint(
            "organization_id", "receipt_number", name="uq_payments_organization_id_receipt_number"
        ),
    )
    op.create_index("ix_payments_work_order_id", "payments", ["work_order_id"])

    _seed()


def _seed() -> None:
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
    # Advances recorded at reception (Sprint 3) become payments. No receipt number: they were
    # documented on the reception act.
    conn.execute(
        sa.text(
            "INSERT INTO payments (id, organization_id, work_order_id, kind, amount, method, "
            "notes, received_by_id, paid_at) "
            "SELECT gen_random_uuid(), organization_id, id, 'ADVANCE', advance_amount, "
            "advance_method, 'Anticipo registrado en la recepción', received_by_id, received_at "
            "FROM work_orders WHERE advance_amount > 0"
        )
    )


def downgrade() -> None:
    for table in (
        "payments",
        "quality_checks",
        "repair_parts",
        "repair_tasks",
        "quotation_items",
        "quotations",
        "inventory_movements",
        "stock_entries",
        "stock_levels",
        "parts",
        "suppliers",
    ):
        op.drop_table(table)
    codes = sorted(NEW_PERMISSIONS)
    op.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE permission_id IN "
            "(SELECT id FROM permissions WHERE code = ANY(:codes))"
        ).bindparams(codes=codes)
    )
    op.execute(sa.text("DELETE FROM permissions WHERE code = ANY(:codes)").bindparams(codes=codes))
