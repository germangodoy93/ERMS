"""Service catalog and appointments outside the workshop (remote and on-site)."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models import Base, TimestampMixin, UUIDPrimaryKeyMixin

MONEY = Numeric(14, 2)
RATE = Numeric(5, 2)


class FieldService(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A service offered remotely or on site. The price is optional: without it, the price is
    given after the diagnosis."""

    __tablename__ = "field_services"
    __table_args__ = (
        UniqueConstraint("organization_id", "name"),
        CheckConstraint("modality IN ('REMOTE', 'ON_SITE')", name="modality_valid"),
        CheckConstraint("duration_minutes BETWEEN 15 AND 480", name="duration_valid"),
        CheckConstraint("price IS NULL OR price >= 0", name="price_positive"),
        CheckConstraint("tax_rate IN (0, 19)", name="tax_rate_valid"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    modality: Mapped[str] = mapped_column(String(10), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    tax_rate: Mapped[Decimal] = mapped_column(
        RATE, nullable=False, default=Decimal("0"), server_default="0"
    )
    price_includes_tax: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )


class Appointment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A remote or on-site appointment. ERMS never stores remote session codes."""

    __tablename__ = "appointments"
    __table_args__ = (
        UniqueConstraint("organization_id", "number"),
        CheckConstraint("modality IN ('REMOTE', 'ON_SITE')", name="modality_valid"),
        CheckConstraint("status IN ('SCHEDULED', 'CANCELLED')", name="status_valid"),
        CheckConstraint("ends_at > starts_at", name="ends_after_start"),
        CheckConstraint(
            "modality <> 'ON_SITE' OR (address IS NOT NULL AND locality IS NOT NULL)",
            name="on_site_has_address",
        ),
        CheckConstraint(
            "modality <> 'REMOTE' OR remote_consent_at IS NOT NULL", name="remote_has_consent"
        ),
        CheckConstraint(
            "status <> 'CANCELLED' OR cancel_reason IS NOT NULL", name="cancel_has_reason"
        ),
        Index("ix_appointments_organization_id_starts_at", "organization_id", "starts_at"),
        Index("ix_appointments_technician_id_starts_at", "technician_id", "starts_at"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    number: Mapped[str] = mapped_column(String(20), nullable=False)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("field_services.id", ondelete="RESTRICT"), nullable=False
    )
    modality: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    technician_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    locality: Mapped[str | None] = mapped_column(String(40), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    overlap_reason: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Por qué se agendó aunque el técnico tenía otra cita"
    )
    remote_consent_channel: Mapped[str | None] = mapped_column(String(10), nullable=True)
    remote_consent_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    remote_consent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancel_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
