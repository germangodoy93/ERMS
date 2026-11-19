"""Organizations: the tenant boundary. Every business table will reference this one."""

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Organization(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    tax_id: Mapped[str | None] = mapped_column(
        String(32), nullable=True, comment="NIT de la organización"
    )
    timezone: Mapped[str] = mapped_column(
        String(64), nullable=False, default="America/Bogota", server_default="America/Bogota"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
