from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError
from app.modules.audit.service import AuditService
from app.modules.organizations.models import Organization
from app.modules.organizations.schemas import OrganizationUpdate
from app.modules.users.models import User
from app.shared.context import RequestContext

# Data of the "Responsable del tratamiento" that the privacy policy must state.
REQUIRED_FOR_POLICY: dict[str, str] = {
    "legal_name": "Razón social o nombre del responsable",
    "tax_id": "NIT",
    "address": "Dirección",
    "city": "Ciudad",
    "phone": "Teléfono",
    "email": "Correo electrónico",
}


def missing_policy_fields(organization: Organization) -> list[str]:
    return [
        label for field, label in REQUIRED_FOR_POLICY.items() if not getattr(organization, field)
    ]


class OrganizationService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._audit = AuditService(session)

    def get(self, actor: User) -> Organization:
        organization = self._session.get(Organization, actor.organization_id)
        assert organization is not None  # noqa: S101 - FK guarantees it
        return organization

    def update(
        self, actor: User, data: OrganizationUpdate, context: RequestContext
    ) -> Organization:
        organization = self.get(actor)
        changes: dict[str, Any] = {}
        for field in data.model_fields_set:
            value = getattr(data, field)
            if field == "name" and value is None:
                raise BusinessRuleError("El nombre del taller es obligatorio.")
            if getattr(organization, field) != value:
                changes[field] = [getattr(organization, field), value]
                setattr(organization, field, value)
        if changes:
            self._audit.record(
                "organization.updated",
                entity_type="organization",
                entity_id=organization.id,
                organization_id=organization.id,
                actor_user_id=actor.id,
                context=context,
                changes=changes,
            )
        return organization
