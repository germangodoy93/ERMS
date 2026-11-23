"""PC builds configured by the workshop and the parts chosen for them."""

import uuid
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.models import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AssemblyBuild(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assembly_builds"
    __table_args__ = (
        CheckConstraint("status IN ('DRAFT', 'ORDERED')", name="status_valid"),
        CheckConstraint("profile IN ('OFFICE', 'DESIGN', 'GAMING')", name="profile_valid"),
        CheckConstraint("ram_units BETWEEN 1 AND 4", name="ram_units_valid"),
        CheckConstraint("labor_price >= 0", name="labor_price_positive"),
        CheckConstraint(
            "(status = 'ORDERED') = (work_order_id IS NOT NULL)", name="ordered_has_order"
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    profile: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="DRAFT")
    ram_units: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    labor_price: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0")
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    work_order_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("work_orders.id", ondelete="RESTRICT"), nullable=True, unique=True
    )
    steps_done: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    items: Mapped[list["AssemblyBuildItem"]] = relationship(
        back_populates="build", cascade="all, delete-orphan", lazy="selectin"
    )


class AssemblyBuildItem(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "assembly_build_items"

    build_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assembly_builds.id", ondelete="CASCADE"), nullable=False, index=True
    )
    part_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("parts.id", ondelete="RESTRICT"), nullable=False
    )

    build: Mapped[AssemblyBuild] = relationship(back_populates="items")
