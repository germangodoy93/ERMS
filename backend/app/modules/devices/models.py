"""Device catalog (categories, manufacturers, models) and customers' devices."""

import uuid

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.models import Base, TimestampMixin, UUIDPrimaryKeyMixin


class DeviceCategory(Base):
    """Fixed, system-wide list inserted by migrations. Later sprints attach checklists and
    diagnostic tests to these codes."""

    __tablename__ = "device_categories"

    code: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)


class Manufacturer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "manufacturers"
    __table_args__ = (UniqueConstraint("organization_id", "name"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )


class DeviceModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "device_models"
    __table_args__ = (UniqueConstraint("manufacturer_id", "name"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    manufacturer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("manufacturers.id", ondelete="RESTRICT"), nullable=False
    )
    category_code: Mapped[str] = mapped_column(
        ForeignKey("device_categories.code", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    release_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    manufacturer: Mapped[Manufacturer] = relationship(lazy="joined")
    category: Mapped[DeviceCategory] = relationship(lazy="joined")


class Device(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "devices"
    __table_args__ = (
        # NULLs are distinct: devices without IMEI or serial never collide.
        UniqueConstraint("organization_id", "imei"),
        UniqueConstraint("organization_id", "model_id", "serial_number"),
        Index("ix_devices_organization_id_serial_number", "organization_id", "serial_number"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    model_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("device_models.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    serial_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    imei: Mapped[str | None] = mapped_column(String(15), nullable=True)
    operating_system: Mapped[str | None] = mapped_column(String(60), nullable=True)
    storage: Mapped[str | None] = mapped_column(String(40), nullable=True)
    color: Mapped[str | None] = mapped_column(String(40), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    model: Mapped[DeviceModel] = relationship(lazy="joined")
