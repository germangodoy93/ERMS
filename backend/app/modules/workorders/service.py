"""Reception and work order lifecycle.

Rules:
- An order is created only for a customer who can be served and one of their active devices,
  under the reception terms in force (published version).
- Numbers are `ER-<year>-<6 digits>`, consecutive per organization and year (Bogotá time),
  generated with an atomic upsert so concurrent receptions never collide.
- Transitions follow `catalog.TRANSITIONS`; each target state requires a permission and some
  require a reason. Technicians (without `work_orders:assign`) only move orders assigned to
  them; taking an unassigned order assigns it to them.
- Delivery records who picked up the device. Status history is append-only.
- The audit trail stores states and identifiers, never free text written about the customer.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session, aliased

from app.core.config import Settings
from app.core.exceptions import (
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from app.core.storage import Storage
from app.modules.attachments.models import Attachment
from app.modules.attachments.service import AttachmentService
from app.modules.audit.service import AuditService
from app.modules.customers.models import Customer
from app.modules.customers.service import CustomerService
from app.modules.devices.models import Device, DeviceModel
from app.modules.organizations.models import Branch
from app.modules.privacy.catalog import ConsentPurpose
from app.modules.roles.catalog import Perm
from app.modules.roles.models import Permission, Role, role_permissions, user_roles
from app.modules.users.models import User
from app.modules.users.repository import escape_like
from app.modules.workorders.catalog import (
    CLOSED,
    REQUIRED_PERMISSIONS,
    TRANSITIONS,
    Status,
    reason_required,
)
from app.modules.workorders.models import (
    ReceptionTerms,
    WorkOrder,
    WorkOrderStatusHistory,
)
from app.modules.workorders.schemas import (
    AccessoryItem,
    CustomerSummary,
    DeliveryRequest,
    DeviceSummary,
    PersonRef,
    StatusHistoryItem,
    WorkOrderCreate,
    WorkOrderListItem,
    WorkOrderRead,
    WorkOrderUpdate,
)
from app.shared.context import BOGOTA, RequestContext, utcnow
from app.shared.identifiers import search_key
from app.shared.pagination import PageParams

DOC_TYPE = "WORK_ORDER"
PHOTO_ENTITY = "work_order"
NUMBER_PREFIX = "ER"
NO_TERMS_MESSAGE = (
    "El taller aún no ha publicado las condiciones del acta de recepción. Un administrador "
    "debe publicarlas en Administración → Datos del taller."
)


@dataclass(frozen=True, slots=True)
class WorkOrderFilters:
    statuses: list[Status] | None = None
    technician_id: uuid.UUID | None = None
    unassigned: bool = False
    search: str | None = None
    open_only: bool = False


class ReceptionTermsService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._audit = AuditService(session)

    def current(self, organization_id: uuid.UUID) -> ReceptionTerms | None:
        return self._session.scalar(
            select(ReceptionTerms)
            .where(ReceptionTerms.organization_id == organization_id)
            .order_by(ReceptionTerms.version.desc())
            .limit(1)
        )

    def require_current(self, organization_id: uuid.UUID) -> ReceptionTerms:
        terms = self.current(organization_id)
        if terms is None:
            raise BusinessRuleError(NO_TERMS_MESSAGE)
        return terms

    def publish(self, actor: User, content: str, context: RequestContext) -> ReceptionTerms:
        # Serialize publications of the same organization so versions never collide.
        self._session.execute(
            text("SELECT id FROM organizations WHERE id = :id FOR UPDATE"),
            {"id": actor.organization_id},
        )
        last = self._session.scalar(
            select(func.max(ReceptionTerms.version)).where(
                ReceptionTerms.organization_id == actor.organization_id
            )
        )
        terms = ReceptionTerms(
            organization_id=actor.organization_id,
            version=(last or 0) + 1,
            content=content.strip() + "\n",
            published_at=utcnow(),
            published_by_id=actor.id,
        )
        self._session.add(terms)
        self._session.flush()
        self._audit.record(
            "reception_terms.published",
            entity_type="reception_terms",
            entity_id=terms.id,
            organization_id=actor.organization_id,
            actor_user_id=actor.id,
            context=context,
            changes={"version": terms.version},
        )
        return terms


def next_number(session: Session, organization_id: uuid.UUID, year: int) -> str:
    value = session.execute(
        text(
            "INSERT INTO document_sequences (organization_id, doc_type, year, last_value) "
            "VALUES (:org, :doc, :year, 1) "
            "ON CONFLICT (organization_id, doc_type, year) "
            "DO UPDATE SET last_value = document_sequences.last_value + 1 "
            "RETURNING last_value"
        ),
        {"org": organization_id, "doc": DOC_TYPE, "year": year},
    ).scalar_one()
    return f"{NUMBER_PREFIX}-{year}-{value:06d}"


class WorkOrderService:
    def __init__(self, session: Session, settings: Settings, storage: Storage) -> None:
        self._session = session
        self._settings = settings
        self._attachments = AttachmentService(session, storage)
        self._customers = CustomerService(session)
        self._terms = ReceptionTermsService(session)
        self._audit = AuditService(session)

    # --- Queries ------------------------------------------------------------------------

    def search(
        self, actor: User, params: PageParams, filters: WorkOrderFilters
    ) -> tuple[list[WorkOrderListItem], int]:
        technician = aliased(User)
        query = (
            select(WorkOrder, Customer, technician)
            .join(Customer, Customer.id == WorkOrder.customer_id)
            .join(Device, Device.id == WorkOrder.device_id)
            .join(DeviceModel, DeviceModel.id == Device.model_id)
            .outerjoin(technician, technician.id == WorkOrder.assigned_technician_id)
            .where(WorkOrder.organization_id == actor.organization_id)
        )
        if filters.statuses:
            query = query.where(WorkOrder.status.in_([s.value for s in filters.statuses]))
        if filters.open_only:
            query = query.where(WorkOrder.status.not_in([s.value for s in CLOSED]))
        if filters.technician_id is not None:
            query = query.where(WorkOrder.assigned_technician_id == filters.technician_id)
        if filters.unassigned:
            query = query.where(WorkOrder.assigned_technician_id.is_(None))
        if filters.search and filters.search.strip():
            raw = filters.search.strip()
            compact = "".join(raw.split()).upper()
            query = query.where(
                or_(
                    WorkOrder.number.ilike(f"%{escape_like(compact)}%", escape="\\"),
                    Customer.search_name.ilike(f"%{escape_like(search_key(raw))}%", escape="\\"),
                    Device.imei.like(f"%{escape_like(compact)}%", escape="\\"),
                    Device.serial_number.like(f"%{escape_like(compact)}%", escape="\\"),
                    DeviceModel.name.ilike(f"%{escape_like(raw)}%", escape="\\"),
                )
            )
        total = self._session.scalar(select(func.count()).select_from(query.subquery())) or 0
        rows = self._session.execute(
            query.order_by(WorkOrder.received_at.desc(), WorkOrder.id)
            .offset(params.offset)
            .limit(params.size)
        ).all()
        return [_list_item(order, customer, tech) for order, customer, tech in rows], total

    def get(self, actor: User, order_id: uuid.UUID, *, for_update: bool = False) -> WorkOrder:
        query = select(WorkOrder).where(
            WorkOrder.id == order_id, WorkOrder.organization_id == actor.organization_id
        )
        if for_update:
            query = query.with_for_update(of=WorkOrder)
        order = self._session.scalar(query)
        if order is None:
            raise NotFoundError("La orden de servicio no existe.")
        return order

    def read(self, actor: User, order_id: uuid.UUID) -> WorkOrderRead:
        return self._to_read(actor, self.get(actor, order_id))

    def terms_content(self, actor: User, order_id: uuid.UUID) -> str:
        order = self.get(actor, order_id)
        terms = self._session.get(ReceptionTerms, order.terms_id)
        assert terms is not None  # noqa: S101 - FK guarantees it
        return terms.content

    def technicians(self, actor: User) -> list[User]:
        """Active users of the organization who can progress orders."""
        return list(
            self._session.scalars(
                select(User)
                .where(
                    User.organization_id == actor.organization_id,
                    User.is_active.is_(True),
                    User.id.in_(
                        select(user_roles.c.user_id)
                        .join(role_permissions, role_permissions.c.role_id == user_roles.c.role_id)
                        .join(Permission, Permission.id == role_permissions.c.permission_id)
                        .join(Role, Role.id == user_roles.c.role_id)
                        .where(
                            Permission.code == Perm.WORK_ORDERS_PROGRESS,
                            Role.organization_id == actor.organization_id,
                        )
                    ),
                )
                .order_by(User.full_name)
            )
        )

    # --- Commands -----------------------------------------------------------------------

    def create(self, actor: User, data: WorkOrderCreate, context: RequestContext) -> WorkOrderRead:
        customer = self._customers.ensure_can_be_served(actor, data.customer_id)
        device = self._session.scalar(
            select(Device).where(
                Device.id == data.device_id,
                Device.organization_id == actor.organization_id,
            )
        )
        if device is None or device.customer_id != customer.id:
            raise BusinessRuleError("El equipo no pertenece a este cliente.")
        if not device.is_active:
            raise BusinessRuleError("El equipo está inactivo.")
        open_order = self._session.scalar(
            select(WorkOrder.number).where(
                WorkOrder.device_id == device.id,
                WorkOrder.status.not_in([s.value for s in CLOSED]),
            )
        )
        if open_order is not None:
            raise ConflictError(f"El equipo ya tiene una orden abierta: {open_order}.")
        terms = self._terms.require_current(actor.organization_id)
        branch = self._session.scalar(
            select(Branch)
            .where(Branch.organization_id == actor.organization_id, Branch.is_active.is_(True))
            .order_by(Branch.created_at)
            .limit(1)
        )
        if branch is None:
            raise BusinessRuleError("El taller no tiene una sede activa.")
        technician_id = None
        if data.assigned_technician_id is not None:
            self._require(actor, Perm.WORK_ORDERS_ASSIGN)
            technician_id = self._valid_technician(actor, data.assigned_technician_id).id

        now = utcnow()
        order = WorkOrder(
            organization_id=actor.organization_id,
            branch_id=branch.id,
            number=next_number(self._session, actor.organization_id, now.astimezone(BOGOTA).year),
            customer_id=customer.id,
            device_id=device.id,
            assigned_technician_id=technician_id,
            status=Status.RECIBIDO,
            priority=data.priority,
            received_at=now,
            received_by_id=actor.id,
            reported_issue=data.reported_issue,
            physical_condition=data.physical_condition,
            accessories=[a.model_dump(mode="json") for a in data.accessories],
            unlock_method=data.unlock_method,
            estimated_delivery_date=data.estimated_delivery_date,
            diagnostic_fee=data.diagnostic_fee,
            advance_amount=data.advance_amount,
            advance_method=data.advance_method,
            notes=data.notes,
            terms_id=terms.id,
        )
        self._session.add(order)
        self._session.flush()
        self._add_history(order, None, Status.RECIBIDO, actor, None, now)
        self._record(
            actor,
            context,
            "work_order.created",
            order,
            {
                "number": order.number,
                "customer_id": str(customer.id),
                "device_id": str(device.id),
                "terms_version": terms.version,
            },
        )
        return self._to_read(actor, order)

    def update(
        self, actor: User, order_id: uuid.UUID, data: WorkOrderUpdate, context: RequestContext
    ) -> WorkOrderRead:
        order = self.get(actor, order_id, for_update=True)
        self._ensure_open(order)
        changed: list[str] = []
        for field in data.model_fields_set:
            value = getattr(data, field)
            if value is None and field in ("reported_issue", "physical_condition", "priority"):
                raise BusinessRuleError(
                    "La falla, el estado físico y la prioridad son obligatorios."
                )
            if getattr(order, field) != value:
                setattr(order, field, value)
                changed.append(field)
        if changed:
            self._session.flush()
            self._record(actor, context, "work_order.updated", order, {"fields": sorted(changed)})
        return self._to_read(actor, order)

    def assign(
        self,
        actor: User,
        order_id: uuid.UUID,
        technician_id: uuid.UUID | None,
        context: RequestContext,
    ) -> WorkOrderRead:
        order = self.get(actor, order_id, for_update=True)
        self._ensure_open(order)
        if technician_id is not None:
            self._valid_technician(actor, technician_id)
        if order.assigned_technician_id != technician_id:
            previous = order.assigned_technician_id
            order.assigned_technician_id = technician_id
            self._session.flush()
            self._record(
                actor,
                context,
                "work_order.assigned",
                order,
                {
                    "technician_id": [
                        str(previous) if previous else None,
                        str(technician_id) if technician_id else None,
                    ]
                },
            )
        return self._to_read(actor, order)

    def change_status(
        self,
        actor: User,
        order_id: uuid.UUID,
        target: Status,
        reason: str | None,
        context: RequestContext,
    ) -> WorkOrderRead:
        if target is Status.ENTREGADO:
            raise BusinessRuleError("Use la entrega del equipo para registrar quién lo retira.")
        order = self.get(actor, order_id, for_update=True)
        source = self._check_transition(actor, order, target)
        if reason_required(source, target) and not reason:
            raise BusinessRuleError("Indique el motivo de este cambio de estado.")
        self._claim_if_technician(actor, order)
        self._move(actor, order, source, target, reason, context)
        return self._to_read(actor, order)

    def deliver(
        self, actor: User, order_id: uuid.UUID, data: DeliveryRequest, context: RequestContext
    ) -> WorkOrderRead:
        order = self.get(actor, order_id, for_update=True)
        source = self._check_transition(actor, order, Status.ENTREGADO)
        if data.picked_up_by_customer:
            customer = self._session.get(Customer, order.customer_id)
            assert customer is not None  # noqa: S101 - FK guarantees it
            order.delivered_to_name = customer.full_name
            order.delivered_to_document = (
                f"{customer.id_type} {customer.id_number}" if customer.id_number else None
            )
        else:
            order.delivered_to_name = data.name
            order.delivered_to_document = data.document
        now = utcnow()
        order.delivered_at = now
        self._move(actor, order, source, Status.ENTREGADO, data.notes, context, now=now)
        return self._to_read(actor, order)

    # --- Photos (demo storage) -----------------------------------------------------------

    def photos(self, actor: User, order_id: uuid.UUID) -> tuple[list[Attachment], bool]:
        order = self.get(actor, order_id)
        items = self._attachments.list_for(actor.organization_id, PHOTO_ENTITY, order.id)
        return items, self._attachments.demo

    def add_photo(
        self,
        actor: User,
        order_id: uuid.UUID,
        data: bytes,
        file_name: str,
        context: RequestContext,
    ) -> Attachment:
        order = self.get(actor, order_id, for_update=True)
        self._ensure_open(order)
        consents = self._customers.current_consents(order.customer_id)
        if not any(c.purpose == ConsentPurpose.PHOTOS and c.granted for c in consents):
            raise BusinessRuleError(
                "El cliente no ha autorizado fotografías del equipo. Registre la autorización "
                "en su ficha antes de tomar fotos."
            )
        if len(data) > self._settings.attachment_max_bytes:
            raise BusinessRuleError("La foto supera el tamaño máximo permitido.")
        count = self._attachments.count_for(actor.organization_id, PHOTO_ENTITY, order.id)
        if count >= self._settings.attachment_max_per_order:
            raise BusinessRuleError("La orden alcanzó el máximo de fotos.")
        attachment = self._attachments.store_photo(
            organization_id=actor.organization_id,
            entity_type=PHOTO_ENTITY,
            entity_id=order.id,
            data=data,
            file_name=file_name,
            uploaded_by_id=actor.id,
        )
        self._record(
            actor, context, "work_order.photo_added", order, {"attachment_id": str(attachment.id)}
        )
        return attachment

    def photo_content(self, actor: User, order_id: uuid.UUID, attachment_id: uuid.UUID) -> bytes:
        order = self.get(actor, order_id)
        attachment = self._photo(actor, order, attachment_id)
        return self._attachments.content(attachment)

    def delete_photo(
        self,
        actor: User,
        order_id: uuid.UUID,
        attachment_id: uuid.UUID,
        context: RequestContext,
    ) -> None:
        order = self.get(actor, order_id, for_update=True)
        self._ensure_open(order)
        attachment = self._photo(actor, order, attachment_id)
        self._attachments.delete(attachment)
        self._record(
            actor, context, "work_order.photo_deleted", order, {"attachment_id": str(attachment_id)}
        )

    def _photo(self, actor: User, order: WorkOrder, attachment_id: uuid.UUID) -> Attachment:
        attachment = self._attachments.get(actor.organization_id, attachment_id)
        if attachment.entity_type != PHOTO_ENTITY or attachment.entity_id != order.id:
            raise NotFoundError("El archivo no existe.")
        return attachment

    # --- Rules --------------------------------------------------------------------------

    def allowed_transitions(self, actor: User, order: WorkOrder) -> list[Status]:
        source = Status(order.status)
        if not self._may_work_on(actor, order):
            return []
        return [
            target
            for target in sorted(TRANSITIONS[source], key=list(Status).index)
            if REQUIRED_PERMISSIONS[target] & actor.permission_codes
        ]

    def _check_transition(self, actor: User, order: WorkOrder, target: Status) -> Status:
        source = Status(order.status)
        if target not in TRANSITIONS[source]:
            raise BusinessRuleError(f"No se puede pasar de {source.value} a {target.value}.")
        if not REQUIRED_PERMISSIONS[target] & actor.permission_codes:
            raise PermissionDeniedError("No tiene permisos para llevar la orden a ese estado.")
        if not self._may_work_on(actor, order):
            raise PermissionDeniedError("La orden está asignada a otro técnico.")
        return source

    @staticmethod
    def _may_work_on(actor: User, order: WorkOrder) -> bool:
        """Technicians only move their own (or unassigned) orders; coordinators move any."""
        perms = actor.permission_codes
        if Perm.WORK_ORDERS_ASSIGN in perms or Perm.WORK_ORDERS_DELIVER in perms:
            return True
        return order.assigned_technician_id in (None, actor.id)

    @staticmethod
    def _claim_if_technician(actor: User, order: WorkOrder) -> None:
        perms = actor.permission_codes
        if (
            order.assigned_technician_id is None
            and Perm.WORK_ORDERS_PROGRESS in perms
            and Perm.WORK_ORDERS_ASSIGN not in perms
        ):
            order.assigned_technician_id = actor.id

    def _move(
        self,
        actor: User,
        order: WorkOrder,
        source: Status,
        target: Status,
        reason: str | None,
        context: RequestContext,
        *,
        now: datetime | None = None,
    ) -> None:
        order.status = target
        self._session.flush()
        self._add_history(order, source, target, actor, reason, now or utcnow())
        self._record(
            actor,
            context,
            "work_order.status_changed",
            order,
            {
                "number": order.number,
                "status": [source.value, target.value],
            },
        )

    def _add_history(
        self,
        order: WorkOrder,
        source: Status | None,
        target: Status,
        actor: User,
        reason: str | None,
        when: datetime,
    ) -> None:
        self._session.add(
            WorkOrderStatusHistory(
                work_order_id=order.id,
                from_status=source,
                to_status=target,
                changed_by_id=actor.id,
                reason=reason,
                changed_at=when,
            )
        )
        self._session.flush()

    def _valid_technician(self, actor: User, technician_id: uuid.UUID) -> User:
        technician = next((t for t in self.technicians(actor) if t.id == technician_id), None)
        if technician is None:
            raise BusinessRuleError("El usuario no es un técnico activo del taller.")
        return technician

    @staticmethod
    def _require(actor: User, permission: Perm) -> None:
        if permission not in actor.permission_codes:
            raise PermissionDeniedError("No tiene permisos para realizar esta acción.")

    @staticmethod
    def _ensure_open(order: WorkOrder) -> None:
        if Status(order.status) in CLOSED:
            raise BusinessRuleError("La orden ya fue entregada y no se puede modificar.")

    def _record(
        self,
        actor: User,
        context: RequestContext,
        action: str,
        order: WorkOrder,
        changes: dict[str, Any],
    ) -> None:
        self._audit.record(
            action,
            entity_type="work_order",
            entity_id=order.id,
            organization_id=actor.organization_id,
            actor_user_id=actor.id,
            context=context,
            changes=changes,
        )

    def _to_read(self, actor: User, order: WorkOrder) -> WorkOrderRead:
        customer = self._session.get(Customer, order.customer_id)
        assert customer is not None  # noqa: S101 - FK guarantees it
        users = {
            u.id: u
            for u in self._session.scalars(
                select(User).where(
                    User.id.in_(
                        {uid for uid in (order.assigned_technician_id, order.received_by_id) if uid}
                        | set(
                            self._session.scalars(
                                select(WorkOrderStatusHistory.changed_by_id).where(
                                    WorkOrderStatusHistory.work_order_id == order.id
                                )
                            )
                        )
                    )
                )
            )
        }
        history = self._session.scalars(
            select(WorkOrderStatusHistory)
            .where(WorkOrderStatusHistory.work_order_id == order.id)
            .order_by(WorkOrderStatusHistory.changed_at, WorkOrderStatusHistory.id)
        )
        branch = self._session.get(Branch, order.branch_id)
        terms = self._session.get(ReceptionTerms, order.terms_id)
        assert branch is not None  # noqa: S101 - FK guarantees it
        assert terms is not None  # noqa: S101 - FK guarantees it
        consents = self._customers.current_consents(customer.id)
        base = _list_item(order, customer, _lookup(users, order.assigned_technician_id))
        return WorkOrderRead(
            **base.model_dump(),
            branch=branch.name,
            reported_issue=order.reported_issue,
            physical_condition=order.physical_condition,
            accessories=[AccessoryItem.model_validate(a) for a in order.accessories],
            unlock_method=order.unlock_method,
            diagnostic_fee=order.diagnostic_fee,
            advance_amount=order.advance_amount,
            advance_method=order.advance_method,
            notes=order.notes,
            terms_version=terms.version,
            received_by=_person(_lookup(users, order.received_by_id)),
            delivered_at=order.delivered_at,
            delivered_to_name=order.delivered_to_name,
            delivered_to_document=order.delivered_to_document,
            history=[
                StatusHistoryItem(
                    from_status=h.from_status,
                    to_status=h.to_status,
                    reason=h.reason,
                    changed_by=_person(_lookup(users, h.changed_by_id)),
                    changed_at=h.changed_at,
                )
                for h in history
            ],
            allowed_transitions=self.allowed_transitions(actor, order),
            customer_allows_photos=any(
                c.purpose == ConsentPurpose.PHOTOS and c.granted for c in consents
            ),
            updated_at=order.updated_at,
        )


def _lookup(users: dict[uuid.UUID, User], user_id: uuid.UUID | None) -> User | None:
    return users.get(user_id) if user_id else None


def _person(user: User | None) -> PersonRef | None:
    return PersonRef(id=user.id, full_name=user.full_name) if user else None


def _list_item(order: WorkOrder, customer: Customer, technician: User | None) -> WorkOrderListItem:
    device = order.device
    return WorkOrderListItem(
        id=order.id,
        number=order.number,
        status=Status(order.status),
        priority=order.priority,
        received_at=order.received_at,
        estimated_delivery_date=order.estimated_delivery_date,
        customer=CustomerSummary(
            id=customer.id,
            full_name=customer.full_name,
            phone=customer.phone,
            id_type=customer.id_type,
            id_number=customer.id_number,
        ),
        device=DeviceSummary(
            id=device.id,
            category=device.model.category.name,
            manufacturer=device.model.manufacturer.name,
            model=device.model.name,
            imei=device.imei,
            serial_number=device.serial_number,
        ),
        assigned_technician=_person(technician),
    )
