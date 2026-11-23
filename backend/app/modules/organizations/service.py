from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError
from app.modules.assembly.pricing import reprice_all
from app.modules.audit.service import AuditService
from app.modules.organizations.models import Organization
from app.modules.organizations.schemas import OrganizationUpdate
from app.modules.users.models import User
from app.shared.context import RequestContext

NOT_NULL = frozenset(
    {
        "name",
        "warranty_days",
        "assembly_bottleneck_gap",
        "assembly_min_ram_gb",
        "assembly_margin_percent",
    }
)

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
            if field in NOT_NULL and value is None:
                raise BusinessRuleError(
                    "El nombre del taller, los días de garantía y los valores del ensamble "
                    "son obligatorios."
                )
            if getattr(organization, field) != value:
                changes[field] = [_plain(getattr(organization, field)), _plain(value)]
                setattr(organization, field, value)
        if "assembly_margin_percent" in changes:
            changes["repriced_parts"] = reprice_all(
                self._session, organization.id, organization.assembly_margin_percent
            )
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


def _plain(value: Any) -> Any:
    """Audit diffs are JSON: decimals become strings."""
    return str(value) if isinstance(value, Decimal) else value
