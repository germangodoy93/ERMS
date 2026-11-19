"""Personal data policy: base template, publication of immutable versions and the
authorization texts shown at reception."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.modules.audit.service import AuditService
from app.modules.organizations.models import Organization
from app.modules.organizations.service import missing_policy_fields
from app.modules.privacy.catalog import ConsentPurpose
from app.modules.privacy.models import PrivacyPolicy
from app.modules.privacy.schemas import CurrentPrivacyPolicy, PrivacyPolicyDraft, PrivacyPolicyRead
from app.modules.privacy.template import render_authorizations, render_policy
from app.modules.users.models import User
from app.shared.context import RequestContext, utcnow

NO_POLICY_MESSAGE = (
    "El taller aún no ha publicado su política de tratamiento de datos. Un administrador debe "
    "publicarla en Administración → Datos del taller."
)
PLACEHOLDERS = {
    "legal_name": "[RAZÓN SOCIAL]",
    "tax_id": "[NIT]",
    "address": "[DIRECCIÓN]",
    "city": "[CIUDAD]",
    "phone": "[TELÉFONO]",
    "email": "[CORREO]",
}


class PrivacyService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._audit = AuditService(session)

    # --- Queries ------------------------------------------------------------------------

    def current(self, organization_id: uuid.UUID) -> PrivacyPolicy | None:
        return self._session.scalar(
            select(PrivacyPolicy)
            .where(PrivacyPolicy.organization_id == organization_id)
            .order_by(PrivacyPolicy.version.desc())
            .limit(1)
        )

    def require_current(self, organization_id: uuid.UUID) -> PrivacyPolicy:
        policy = self.current(organization_id)
        if policy is None:
            raise BusinessRuleError(NO_POLICY_MESSAGE)
        return policy

    def current_with_authorizations(self, actor: User) -> CurrentPrivacyPolicy:
        policy = self.current(actor.organization_id)
        organization = self._organization(actor)
        authorizations: dict[ConsentPurpose, str] = {}
        if policy is not None:
            authorizations = render_authorizations(
                name=organization.legal_name or organization.name, version=policy.version
            )
        return CurrentPrivacyPolicy(
            policy=PrivacyPolicyRead.model_validate(policy) if policy else None,
            authorizations=authorizations,
        )

    def versions(self, organization_id: uuid.UUID) -> list[PrivacyPolicy]:
        return list(
            self._session.scalars(
                select(PrivacyPolicy)
                .where(PrivacyPolicy.organization_id == organization_id)
                .order_by(PrivacyPolicy.version.desc())
            )
        )

    def get_version(self, organization_id: uuid.UUID, version: int) -> PrivacyPolicy:
        policy = self._session.scalar(
            select(PrivacyPolicy).where(
                PrivacyPolicy.organization_id == organization_id, PrivacyPolicy.version == version
            )
        )
        if policy is None:
            raise NotFoundError("Esa versión de la política no existe.")
        return policy

    def draft(self, actor: User) -> PrivacyPolicyDraft:
        """Template filled with the workshop data. Missing data is shown as [placeholders]."""
        organization = self._organization(actor)
        return PrivacyPolicyDraft(
            content=render_policy(
                **{
                    field: getattr(organization, field) or placeholder
                    for field, placeholder in PLACEHOLDERS.items()
                }
            ),
            missing_fields=missing_policy_fields(organization),
        )

    # --- Commands -----------------------------------------------------------------------

    def publish(self, actor: User, content: str, context: RequestContext) -> PrivacyPolicy:
        organization = self._organization(actor)
        missing = missing_policy_fields(organization)
        if missing:
            raise BusinessRuleError(
                "Complete los datos del taller antes de publicar la política: "
                + ", ".join(missing)
                + "."
            )
        content = content.strip() + "\n"
        if any(marker in content for marker in PLACEHOLDERS.values()):
            raise BusinessRuleError("La política aún tiene datos por completar entre corchetes.")

        # Serialize publications of the same organization so versions never collide.
        self._session.execute(
            select(Organization.id).where(Organization.id == organization.id).with_for_update()
        )
        last = self._session.scalar(
            select(func.max(PrivacyPolicy.version)).where(
                PrivacyPolicy.organization_id == organization.id
            )
        )
        policy = PrivacyPolicy(
            organization_id=organization.id,
            version=(last or 0) + 1,
            content=content,
            published_at=utcnow(),
            published_by_id=actor.id,
        )
        self._session.add(policy)
        self._session.flush()
        self._audit.record(
            "privacy_policy.published",
            entity_type="privacy_policy",
            entity_id=policy.id,
            organization_id=organization.id,
            actor_user_id=actor.id,
            context=context,
            changes={"version": policy.version},
        )
        return policy

    def _organization(self, actor: User) -> Organization:
        organization = self._session.get(Organization, actor.organization_id)
        assert organization is not None  # noqa: S101 - FK guarantees it
        return organization
