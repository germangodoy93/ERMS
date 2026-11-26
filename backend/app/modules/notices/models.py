"""Notice templates edited by the workshop and the log of notices prepared for customers."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models import Base, UUIDPrimaryKeyMixin

_KINDS = "'RECEIVED', 'QUOTE_READY', 'READY', 'NOT_REPAIRED', 'REMINDER', 'DELIVERED', 'FREE'"


class NoticeTemplate(Base):
    """Only the texts changed by the workshop; the others use the default in catalog.py."""

    __tablename__ = "notice_templates"
    __table_args__ = (CheckConstraint(f"kind IN ({_KINDS})", name="kind_valid"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True
    )
    kind: Mapped[str] = mapped_column(String(20), primary_key=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    updated_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class WorkOrderNotice(UUIDPrimaryKeyMixin, Base):
    """A message prepared for the customer. ERMS cannot know whether it was actually sent."""

    __tablename__ = "work_order_notices"
    __table_args__ = (
        CheckConstraint(f"kind IN ({_KINDS})", name="kind_valid"),
        Index("ix_work_order_notices_work_order_id_prepared_at", "work_order_id", "prepared_at"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    work_order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    prepared_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    prepared_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
