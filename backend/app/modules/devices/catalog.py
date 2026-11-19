"""Initial device catalog.

Categories are fixed system-wide (inserted by migration 0003). The manufacturers below are
pre-loaded for each new organization and can be edited or deactivated afterwards; models
are created by each workshop as devices arrive.
"""

import uuid
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.devices.models import Manufacturer


class CategoryCode(StrEnum):
    LAPTOP = "LAPTOP"
    DESKTOP = "DESKTOP"
    PHONE = "PHONE"
    TABLET = "TABLET"
    CONSOLE = "CONSOLE"
    OTHER = "OTHER"


DEFAULT_MANUFACTURERS: tuple[str, ...] = (
    "Acer",
    "Apple",
    "Asus",
    "Dell",
    "HP",
    "Huawei",
    "Lenovo",
    "Microsoft",
    "Motorola",
    "Nintendo",
    "Samsung",
    "Sony",
    "Xiaomi",
)


def seed_manufacturers(session: Session, organization_id: uuid.UUID) -> None:
    """Adds the default manufacturers that the organization does not have yet."""
    existing = set(
        session.scalars(
            select(Manufacturer.name).where(Manufacturer.organization_id == organization_id)
        )
    )
    for name in DEFAULT_MANUFACTURERS:
        if name not in existing:
            session.add(Manufacturer(organization_id=organization_id, name=name))
    session.flush()
