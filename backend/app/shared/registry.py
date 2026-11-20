"""Imports every module's ORM models so `Base.metadata` is complete.

Alembic's env.py imports this module; add each new module's `models` here.
"""

from app.modules.attachments import models as attachments_models
from app.modules.audit import models as audit_models
from app.modules.auth import models as auth_models
from app.modules.customers import models as customers_models
from app.modules.devices import models as devices_models
from app.modules.diagnostics import models as diagnostics_models
from app.modules.inventory import models as inventory_models
from app.modules.organizations import models as organizations_models
from app.modules.payments import models as payments_models
from app.modules.privacy import models as privacy_models
from app.modules.quotes import models as quotes_models
from app.modules.repairs import models as repairs_models
from app.modules.roles import models as roles_models
from app.modules.users import models as users_models
from app.modules.warranties import models as warranties_models
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
    "inventory_models",
    "organizations_models",
    "payments_models",
    "privacy_models",
    "quotes_models",
    "repairs_models",
    "roles_models",
    "users_models",
    "warranties_models",
    "workorders_models",
]
