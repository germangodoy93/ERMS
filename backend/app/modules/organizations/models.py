"""Organizations (tenant boundary) and their branches (sedes)."""

import uuid
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Organization(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    tax_id: Mapped[str | None] = mapped_column(
        String(32), nullable=True, comment="NIT de la organización"
    )
    # Data of the "Responsable del tratamiento" required by Ley 1581 de 2012 (Sprint 2).
    legal_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(80), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    warranty_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=90, server_default="90"
    )
    assembly_bottleneck_gap: Mapped[int] = mapped_column(
        Integer, nullable=False, default=25, server_default="25"
    )
    assembly_min_ram_gb: Mapped[int] = mapped_column(
        Integer, nullable=False, default=16, server_default="16"
    )
    assembly_margin_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("15"), server_default="15"
    )
    timezone: Mapped[str] = mapped_column(
        String(64), nullable=False, default="America/Bogota", server_default="America/Bogota"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )


class Branch(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "branches"
    __table_args__ = (UniqueConstraint("organization_id", "name"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    city: Mapped[str] = mapped_column(String(80), nullable=False)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
