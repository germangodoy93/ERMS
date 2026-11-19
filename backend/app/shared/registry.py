"""Imports every module's ORM models so `Base.metadata` is complete.

Alembic's env.py imports this module; add each new module's `models` here.
"""

from app.modules.audit import models as audit_models
from app.modules.auth import models as auth_models
from app.modules.organizations import models as organizations_models
from app.modules.roles import models as roles_models
from app.modules.users import models as users_models
from app.shared.models import Base

__all__ = [
    "Base",
    "audit_models",
    "auth_models",
    "organizations_models",
    "roles_models",
    "users_models",
]
