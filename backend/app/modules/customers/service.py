"""Customers and Habeas Data rules (Ley 1581 de 2012):

- A customer is only registered with the data processing authorization (DATA_PROCESSING),
  tied to the policy version in force. Without a published policy no customer is created.
- Consents are append-only: revoking inserts a new record.
- The audit trail stores WHICH fields changed, never their personal values, so anonymizing
  a customer leaves no personal data behind in `audit_logs`.
- Anonymization (right of suppression) removes personal data and keeps the technical
  history. Only `customers:anonymize` (Administrador) can do it, and it is irreversible.
"""

import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.modules.audit.service import AuditService
from app.modules.customers.models import Customer, CustomerConsent
from app.modules.customers.repository import CustomerRepository
from app.modules.customers.schemas import (
    ConsentChange,
    ConsentRecordRead,
    ConsentStatus,
    CustomerCreate,
    CustomerRead,
    CustomerUpdate,
)
from app.modules.privacy.catalog import ConsentChannel, ConsentPurpose
from app.modules.privacy.service import PrivacyService
from app.modules.users.models import User
from app.shared.context import RequestContext, utcnow
from app.shared.identifiers import search_key
from app.shared.pagination import PageParams

ANONYMIZED_NAME = "Cliente anonimizado"
_EDITABLE = ("kind", "full_name", "id_type", "id_number", "phone", "email", "address", "notes")


class CustomerService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._customers = CustomerRepository(session)
        self._privacy = PrivacyService(session)
        self._audit = AuditService(session)

    # --- Queries ------------------------------------------------------------------------

    def search(
        self, actor: User, params: PageParams, *, search: str | None, is_active: bool | None
    ) -> tuple[list[Customer], int]:
        return self._customers.search(
            actor.organization_id, params, search=search, is_active=is_active
        )

    def get(self, actor: User, customer_id: uuid.UUID) -> Customer:
        customer = self._customers.get(actor.organization_id, customer_id)
        if customer is None:
            raise NotFoundError("El cliente no existe.")
        return customer

    def read(self, actor: User, customer_id: uuid.UUID) -> CustomerRead:
        return self._to_read(self.get(actor, customer_id))

    def consent_history(self, actor: User, customer_id: uuid.UUID) -> list[ConsentRecordRead]:
        customer = self.get(actor, customer_id)
        return [
            ConsentRecordRead(
                id=consent.id,
                purpose=ConsentPurpose(consent.purpose),
                granted=consent.granted,
                channel=ConsentChannel(consent.channel),
                policy_version=version,
                recorded_at=consent.recorded_at,
                recorded_by=recorded_by,
            )
            for consent, version, recorded_by in self._customers.consent_history(customer.id)
        ]

    def current_consents(self, customer_id: uuid.UUID) -> list[ConsentStatus]:
        return [
            ConsentStatus(
                purpose=ConsentPurpose(consent.purpose),
                granted=consent.granted,
                channel=ConsentChannel(consent.channel),
                policy_version=version,
                recorded_at=consent.recorded_at,
            )
            for consent, version in self._customers.current_consents(customer_id)
        ]

    def ensure_can_be_served(self, actor: User, customer_id: uuid.UUID) -> Customer:
        """Used by other modules (devices now, work orders in Sprint 3)."""
        customer = self.get(actor, customer_id)
        if customer.anonymized_at is not None:
            raise BusinessRuleError("El cliente fue anonimizado y no puede recibir servicios.")
        if not customer.is_active:
            raise BusinessRuleError("El cliente está inactivo. Actívelo para continuar.")
        if not self._has_data_processing(customer.id):
            raise BusinessRuleError(
                "El cliente revocó la autorización de tratamiento de datos. Registre una nueva "
                "autorización para continuar."
            )
        return customer

    # --- Commands -----------------------------------------------------------------------

    def create(self, actor: User, data: CustomerCreate, context: RequestContext) -> CustomerRead:
        policy = self._privacy.require_current(actor.organization_id)
        if data.id_type and data.id_number:
            self._ensure_document_free(actor, data.id_type, data.id_number)

        customer = Customer(
            organization_id=actor.organization_id,
            kind=data.kind,
            full_name=data.full_name,
            search_name=search_key(data.full_name),
            id_type=data.id_type,
            id_number=data.id_number,
            phone=data.phone,
            email=data.email,
            address=data.address,
            notes=data.notes,
            created_by_id=actor.id,
        )
        self._customers.add(customer)
        now = utcnow()
        for grant in data.consents:
            self._customers.add_consent(
                CustomerConsent(
                    organization_id=actor.organization_id,
                    customer_id=customer.id,
                    purpose=grant.purpose,
                    granted=True,
                    channel=grant.channel,
                    policy_id=policy.id,
                    recorded_by_id=actor.id,
                    recorded_at=now,
                )
            )
        self._audit.record(
            "customer.created",
            entity_type="customer",
            entity_id=customer.id,
            organization_id=actor.organization_id,
            actor_user_id=actor.id,
            context=context,
            changes={
                "fields": sorted(f for f in _EDITABLE if getattr(customer, f) is not None),
                "consents": sorted(g.purpose for g in data.consents),
                "policy_version": policy.version,
            },
        )
        return self._to_read(customer)

    def update(
        self, actor: User, customer_id: uuid.UUID, data: CustomerUpdate, context: RequestContext
    ) -> CustomerRead:
        customer = self._get_for_update(actor, customer_id)
        self._ensure_not_anonymized(customer)
        fields = data.model_fields_set
        changed: list[str] = []

        if (
            data.id_type
            and data.id_number
            and (data.id_type != customer.id_type or data.id_number != customer.id_number)
        ):
            self._ensure_document_free(actor, data.id_type, data.id_number, exclude_id=customer.id)
        for field in _EDITABLE:
            if field not in fields:
                continue
            value = getattr(data, field)
            if field in ("kind", "full_name") and value is None:
                raise BusinessRuleError("El tipo de cliente y el nombre son obligatorios.")
            if getattr(customer, field) != value:
                setattr(customer, field, value)
                changed.append(field)
        if "full_name" in changed:
            customer.search_name = search_key(customer.full_name)
        if not customer.phone and not customer.email:
            raise BusinessRuleError("Registre al menos un teléfono o un correo electrónico.")
        if data.is_active is not None and data.is_active != customer.is_active:
            customer.is_active = data.is_active
            changed.append("is_active")

        if changed:
            self._session.flush()
            self._audit.record(
                "customer.updated",
                entity_type="customer",
                entity_id=customer.id,
                organization_id=actor.organization_id,
                actor_user_id=actor.id,
                context=context,
                changes={"fields": sorted(changed), "is_active": customer.is_active}
                if "is_active" in changed
                else {"fields": sorted(changed)},
            )
        return self._to_read(customer)

    def change_consent(
        self, actor: User, customer_id: uuid.UUID, change: ConsentChange, context: RequestContext
    ) -> CustomerRead:
        customer = self._get_for_update(actor, customer_id)
        self._ensure_not_anonymized(customer)
        current = {c.purpose: c for c in self.current_consents(customer.id)}
        state = current.get(change.purpose)
        if state is not None and state.granted == change.granted:
            raise ConflictError(
                "La autorización ya está otorgada."
                if change.granted
                else "La autorización ya está revocada."
            )
        if state is None and not change.granted:
            raise BusinessRuleError("No hay una autorización para revocar.")
        policy = self._privacy.require_current(actor.organization_id)
        self._customers.add_consent(
            CustomerConsent(
                organization_id=actor.organization_id,
                customer_id=customer.id,
                purpose=change.purpose,
                granted=change.granted,
                channel=change.channel,
                policy_id=policy.id,
                recorded_by_id=actor.id,
                recorded_at=utcnow(),
            )
        )
        self._audit.record(
            "customer.consent_granted" if change.granted else "customer.consent_revoked",
            entity_type="customer",
            entity_id=customer.id,
            organization_id=actor.organization_id,
            actor_user_id=actor.id,
            context=context,
            changes={
                "purpose": change.purpose,
                "channel": change.channel,
                "policy_version": policy.version,
            },
        )
        return self._to_read(customer)

    def anonymize(
        self,
        actor: User,
        customer_id: uuid.UUID,
        channel: ConsentChannel,
        context: RequestContext,
    ) -> CustomerRead:
        customer = self._get_for_update(actor, customer_id)
        if customer.anonymized_at is not None:
            raise ConflictError("El cliente ya fue anonimizado.")

        # Every authorization still granted is revoked, tied to the policy it was given under.
        now = utcnow()
        for status in self.current_consents(customer.id):
            if status.granted:
                policy = self._privacy.get_version(actor.organization_id, status.policy_version)
                self._customers.add_consent(
                    CustomerConsent(
                        organization_id=actor.organization_id,
                        customer_id=customer.id,
                        purpose=status.purpose,
                        granted=False,
                        channel=channel,
                        policy_id=policy.id,
                        recorded_by_id=actor.id,
                        recorded_at=now,
                    )
                )

        customer.full_name = ANONYMIZED_NAME
        customer.search_name = search_key(ANONYMIZED_NAME)
        customer.id_type = None
        customer.id_number = None
        customer.phone = None
        customer.email = None
        customer.address = None
        customer.notes = None
        customer.is_active = False
        customer.anonymized_at = now
        # Imported here: the devices module depends on this one.
        from app.modules.devices.service import DeviceService

        DeviceService(self._session).clear_personal_notes(actor.organization_id, customer.id)
        self._session.flush()
        self._audit.record(
            "customer.anonymized",
            entity_type="customer",
            entity_id=customer.id,
            organization_id=actor.organization_id,
            actor_user_id=actor.id,
            context=context,
            changes={"channel": channel},
        )
        return self._to_read(customer)

    # --- Helpers ------------------------------------------------------------------------

    def _get_for_update(self, actor: User, customer_id: uuid.UUID) -> Customer:
        customer = self._customers.get_for_update(actor.organization_id, customer_id)
        if customer is None:
            raise NotFoundError("El cliente no existe.")
        return customer

    def _ensure_document_free(
        self,
        actor: User,
        id_type: str,
        id_number: str,
        *,
        exclude_id: uuid.UUID | None = None,
    ) -> None:
        existing = self._customers.find_by_document(
            actor.organization_id, id_type, id_number, exclude_id=exclude_id
        )
        if existing is not None:
            raise ConflictError(
                f"Ya existe un cliente con {id_type} {id_number}: {existing.full_name}."
            )

    @staticmethod
    def _ensure_not_anonymized(customer: Customer) -> None:
        if customer.anonymized_at is not None:
            raise BusinessRuleError("El cliente fue anonimizado y sus datos no se pueden editar.")

    def _has_data_processing(self, customer_id: uuid.UUID) -> bool:
        return any(
            c.purpose == ConsentPurpose.DATA_PROCESSING and c.granted
            for c in self.current_consents(customer_id)
        )

    def _to_read(self, customer: Customer) -> CustomerRead:
        consents = self.current_consents(customer.id)
        data_processing = any(
            c.purpose == ConsentPurpose.DATA_PROCESSING and c.granted for c in consents
        )
        return CustomerRead.model_validate(
            {
                **{
                    field: getattr(customer, field)
                    for field in (
                        "id",
                        "kind",
                        "full_name",
                        "id_type",
                        "id_number",
                        "phone",
                        "email",
                        "address",
                        "notes",
                        "is_active",
                        "anonymized_at",
                        "created_at",
                        "updated_at",
                    )
                },
                "consents": consents,
                "can_be_served": customer.is_active
                and customer.anonymized_at is None
                and data_processing,
            }
        )
