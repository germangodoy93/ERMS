"""Imports every module's ORM models so `Base.metadata` is complete.

Alembic's env.py imports this module; add each new module's `models` here.
"""

from app.modules.organizations import models as organizations_models
from app.shared.models import Base

__all__ = ["Base", "organizations_models"]
