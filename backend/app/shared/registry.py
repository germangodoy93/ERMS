"""Imports every module's ORM models so `Base.metadata` is complete.

Alembic's env.py imports this module; add each new module's `models` here.
"""

from app.modules.attachments import models as attachments_models
from app.modules.audit import models as audit_models
from app.modules.auth import models as auth_models
from app.modules.customers import models as customers_models
from app.modules.devices import models as devices_models
from app.modules.diagnostics import models as diagnostics_models
from app.modules.organizations import models as organizations_models
from app.modules.privacy import models as privacy_models
from app.modules.roles import models as roles_models
from app.modules.users import models as users_models
from app.modules.workorders import models as workorders_models
from app.shared.models import Base

__all__ = [
    "Base",
    "attachments_models",
    "audit_models",
    "auth_models",
    "customers_models",
    "devices_models",
    "diagnostics_models",
    "organizations_models",
    "privacy_models",
    "roles_models",
    "users_models",
    "workorders_models",
]
