"""Quotations per work order (versioned) with per-item IVA."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.models import Base, TimestampMixin, UUIDPrimaryKeyMixin

MONEY = Numeric(14, 2)
RATE = Numeric(5, 2)


class Quotation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "quotations"
    __table_args__ = (
        UniqueConstraint("work_order_id", "version"),
        CheckConstraint(
            "status IN ('DRAFT', 'SENT', 'ACCEPTED', 'REJECTED', 'SUPERSEDED')",
            name="status_valid",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    work_order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(12), nullable=False)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    subtotal: Mapped[Decimal] = mapped_column(MONEY, nullable=False, default=Decimal("0"))
    discount_total: Mapped[Decimal] = mapped_column(MONEY, nullable=False, default=Decimal("0"))
    tax_total: Mapped[Decimal] = mapped_column(MONEY, nullable=False, default=Decimal("0"))
    total: Mapped[Decimal] = mapped_column(MONEY, nullable=False, default=Decimal("0"))
    discount_authorized_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    responded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    response_channel: Mapped[str | None] = mapped_column(String(10), nullable=True)

    items: Mapped[list["QuotationItem"]] = relationship(
        lazy="selectin", order_by="QuotationItem.position", cascade="all, delete-orphan"
    )


class QuotationItem(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "quotation_items"
    __table_args__ = (
        CheckConstraint("kind IN ('LABOR', 'PART')", name="kind_valid"),
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("unit_price >= 0", name="unit_price_positive"),
        CheckConstraint("discount_percent >= 0 AND discount_percent <= 100", name="discount_valid"),
        CheckConstraint("tax_rate IN (0, 19)", name="tax_rate_valid"),
    )

    quotation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("quotations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(10), nullable=False)
    part_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("parts.id", ondelete="RESTRICT"), nullable=True
    )
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    discount_percent: Mapped[Decimal] = mapped_column(RATE, nullable=False, default=Decimal("0"))
    tax_rate: Mapped[Decimal] = mapped_column(RATE, nullable=False, default=Decimal("0"))
    price_includes_tax: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    discount_amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    base_amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
