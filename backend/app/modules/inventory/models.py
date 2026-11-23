"""Parts, suppliers, stock per branch and the append-only movement ledger."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models import Base, TimestampMixin, UUIDPrimaryKeyMixin

MONEY = Numeric(14, 2)
RATE = Numeric(5, 2)


class Supplier(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "suppliers"
    __table_args__ = (UniqueConstraint("organization_id", "name"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    tax_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    contact_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )


class Part(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "parts"
    __table_args__ = (
        UniqueConstraint("organization_id", "sku"),
        CheckConstraint(
            "kind IN ('PART', 'COMPONENT', 'ACCESSORY', 'CONSUMABLE')", name="kind_valid"
        ),
        CheckConstraint("unit_cost >= 0 AND sale_price >= 0", name="prices_positive"),
        CheckConstraint("tax_rate IN (0, 19)", name="tax_rate_valid"),
        CheckConstraint("min_stock >= 0", name="min_stock_positive"),
        CheckConstraint(
            "(assembly_category IS NULL) = (specs IS NULL)", name="assembly_specs_together"
        ),
        Index("ix_parts_organization_id_assembly_category", "organization_id", "assembly_category"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    sku: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    kind: Mapped[str] = mapped_column(String(12), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(MONEY, nullable=False, default=Decimal("0"))
    sale_price: Mapped[Decimal] = mapped_column(MONEY, nullable=False, default=Decimal("0"))
    tax_rate: Mapped[Decimal] = mapped_column(RATE, nullable=False, default=Decimal("0"))
    price_includes_tax: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    min_stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    assembly_category: Mapped[str | None] = mapped_column(
        String(10), nullable=True, comment="Categoría para el ensamble de PC (CPU, BOARD, …)"
    )
    specs: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True, comment="Especificaciones técnicas según la categoría de ensamble"
    )
    price_locked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment="Precio de venta fijado a mano: no se recalcula con el costo y el margen",
    )


class StockLevel(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "stock_levels"
    __table_args__ = (
        UniqueConstraint("part_id", "branch_id"),
        CheckConstraint("quantity >= 0", name="quantity_not_negative"),
    )

    part_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("parts.id", ondelete="RESTRICT"), nullable=False
    )
    branch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("branches.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class StockEntry(UUIDPrimaryKeyMixin, Base):
    """Purchase received from a supplier (simple entry, no purchase-order workflow)."""

    __tablename__ = "stock_entries"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    branch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("branches.id", ondelete="RESTRICT"), nullable=False
    )
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=True
    )
    invoice_number: Mapped[str | None] = mapped_column(String(40), nullable=True)
    received_on: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class InventoryMovement(UUIDPrimaryKeyMixin, Base):
    """Append-only. `quantity` is signed: IN/RETURN positive, OUT negative, ADJUSTMENT both."""

    __tablename__ = "inventory_movements"
    __table_args__ = (
        CheckConstraint("kind IN ('IN', 'OUT', 'ADJUSTMENT', 'RETURN')", name="kind_valid"),
        CheckConstraint("quantity <> 0", name="quantity_not_zero"),
        CheckConstraint("stock_after >= 0", name="stock_after_not_negative"),
        Index("ix_inventory_movements_part_created", "part_id", "created_at"),
        Index("ix_inventory_movements_reference", "reference_type", "reference_id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    part_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("parts.id", ondelete="RESTRICT"), nullable=False
    )
    branch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("branches.id", ondelete="RESTRICT"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(12), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    stock_after: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_cost: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    reference_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    reference_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
