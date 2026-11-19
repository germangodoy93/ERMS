"""Customers and their data processing consents (Ley 1581 de 2012)."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Customer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "customers"
    __table_args__ = (
        # The document is optional, but unique inside the organization when present
        # (PostgreSQL treats NULLs as distinct).
        UniqueConstraint("organization_id", "id_type", "id_number"),
        CheckConstraint("(id_type IS NULL) = (id_number IS NULL)", name="id_type_with_number"),
        CheckConstraint("kind IN ('PERSON', 'COMPANY')", name="kind_valid"),
        CheckConstraint("email = lower(email)", name="email_lowercase"),
        Index(
            "ix_customers_search_name_trgm",
            "search_name",
            postgresql_using="gin",
            postgresql_ops={"search_name": "gin_trgm_ops"},
        ),
        Index("ix_customers_organization_id_phone", "organization_id", "phone"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(10), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    search_name: Mapped[str] = mapped_column(String(200), nullable=False)
    id_type: Mapped[str | None] = mapped_column(String(5), nullable=True)
    id_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    anonymized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class CustomerConsent(UUIDPrimaryKeyMixin, Base):
    """Append-only: granting or revoking always inserts a new row.

    The current state of a purpose is the most recent row for (customer, purpose).
    """

    __tablename__ = "customer_consents"
    __table_args__ = (
        CheckConstraint(
            "purpose IN ('DATA_PROCESSING', 'PHOTOS', 'DIAGNOSTIC_AGENT')", name="purpose_valid"
        ),
        CheckConstraint("channel IN ('SCREEN', 'PAPER', 'VERBAL')", name="channel_valid"),
        Index("ix_customer_consents_customer_purpose", "customer_id", "purpose", "recorded_at"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    purpose: Mapped[str] = mapped_column(String(20), nullable=False)
    granted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    channel: Mapped[str] = mapped_column(String(10), nullable=False)
    policy_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("privacy_policies.id", ondelete="RESTRICT"), nullable=False
    )
    recorded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
