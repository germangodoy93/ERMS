"""Warranty of a delivered repair and the claims made against it."""

import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models import Base, UUIDPrimaryKeyMixin


class Warranty(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "warranties"
    __table_args__ = (CheckConstraint("days > 0", name="days_positive"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    work_order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    days: Mapped[int] = mapped_column(Integer, nullable=False)
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class WarrantyClaim(UUIDPrimaryKeyMixin, Base):
    """A claim opens a new work order (no diagnostic fee) linked to the warranty."""

    __tablename__ = "warranty_claims"
    __table_args__ = (
        CheckConstraint("status IN ('OPEN', 'ACCEPTED', 'REJECTED')", name="status_valid"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    warranty_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("warranties.id", ondelete="CASCADE"), nullable=False, index=True
    )
    claim_order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("work_orders.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    reported_issue: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
