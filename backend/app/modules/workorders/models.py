"""Work orders, their status history, document numbering and reception terms."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.modules.devices.models import Device
from app.shared.models import Base, TimestampMixin, UUIDPrimaryKeyMixin

MONEY = Numeric(14, 2)


class DocumentSequence(Base):
    """Per organization, document type and year. Incremented with SELECT … FOR UPDATE."""

    __tablename__ = "document_sequences"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), primary_key=True
    )
    doc_type: Mapped[str] = mapped_column(String(20), primary_key=True)
    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_value: Mapped[int] = mapped_column(Integer, nullable=False)


class ReceptionTerms(UUIDPrimaryKeyMixin, Base):
    """Published versions of the conditions printed on the reception act (immutable)."""

    __tablename__ = "reception_terms"
    __table_args__ = (UniqueConstraint("organization_id", "version"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    published_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class WorkOrder(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "work_orders"
    __table_args__ = (
        UniqueConstraint("organization_id", "number"),
        CheckConstraint("diagnostic_fee >= 0", name="diagnostic_fee_positive"),
        CheckConstraint("advance_amount >= 0", name="advance_amount_positive"),
        CheckConstraint(
            "advance_amount = 0 OR advance_method IS NOT NULL", name="advance_has_method"
        ),
        Index("ix_work_orders_organization_id_status", "organization_id", "status"),
        Index("ix_work_orders_organization_id_received_at", "organization_id", "received_at"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    branch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("branches.id", ondelete="RESTRICT"), nullable=False
    )
    number: Mapped[str] = mapped_column(String(20), nullable=False)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("devices.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    assigned_technician_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    priority: Mapped[str] = mapped_column(String(10), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reported_issue: Mapped[str] = mapped_column(Text, nullable=False)
    physical_condition: Mapped[str] = mapped_column(Text, nullable=False)
    accessories: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    unlock_method: Mapped[str] = mapped_column(String(20), nullable=False)
    estimated_delivery_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    diagnostic_fee: Mapped[Decimal] = mapped_column(
        MONEY, nullable=False, default=Decimal("0"), server_default="0"
    )
    advance_amount: Mapped[Decimal] = mapped_column(
        MONEY, nullable=False, default=Decimal("0"), server_default="0"
    )
    advance_method: Mapped[str | None] = mapped_column(String(10), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    terms_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reception_terms.id", ondelete="RESTRICT"), nullable=False
    )
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_to_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    delivered_to_document: Mapped[str | None] = mapped_column(String(40), nullable=True)

    device: Mapped[Device] = relationship(lazy="joined")


class WorkOrderStatusHistory(UUIDPrimaryKeyMixin, Base):
    """Append-only trail of every status change."""

    __tablename__ = "work_order_status_history"
    __table_args__ = (
        Index("ix_work_order_status_history_order_changed", "work_order_id", "changed_at"),
    )

    work_order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False
    )
    from_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    to_status: Mapped[str] = mapped_column(String(30), nullable=False)
    changed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
