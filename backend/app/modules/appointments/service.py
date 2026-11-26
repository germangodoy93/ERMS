"""Agenda of remote and on-site appointments (PM-04, sprint R1).

Rules:
- Appointments fall inside the remote/on-site service hours (independent of the workshop's
  opening hours), on a single day, never on a Colombian public holiday nor in the past.
- A technician with another appointment at the same time is a warning, not a block: the
  appointment is saved only with a written reason (409 `appointment_overlap` otherwise).
- On-site appointments need an address and locality; remote ones the customer's
  authorization of remote access (the session code is never stored).
- Technicians without `appointments:manage` see only their own appointments.
- The audit trail stores identifiers and times, never free text about the customer.
"""

import uuid
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.core.exceptions import (
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from app.modules.appointments.catalog import (
    DEFAULT_HOURS,
    DEFAULT_SERVICES,
    LOCALITIES,
    MAX_RANGE_DAYS,
    REMOTE_ACCESS_TEXT,
    AppointmentStatus,
    Modality,
)
from app.modules.appointments.models import Appointment, FieldService
from app.modules.appointments.schemas import (
    AgendaOptions,
    AppointmentCreate,
    AppointmentRead,
    AppointmentUpdate,
    FieldServiceRead,
    FieldServiceWrite,
    HolidayRead,
    HoursDay,
    HoursRead,
    ServiceRef,
)
from app.modules.audit.service import AuditService
from app.modules.customers.models import Customer
from app.modules.customers.service import CustomerService
from app.modules.organizations.models import Organization
from app.modules.roles.catalog import Perm
from app.modules.users.models import User
from app.modules.workorders.schemas import CustomerSummary, PersonRef
from app.modules.workorders.service import WorkOrderService
from app.shared.context import BOGOTA, RequestContext, utcnow
from app.shared.holidays import holiday_name, holidays
from app.shared.sequences import next_document_number

DOC_TYPE = "APPOINTMENT"
NUMBER_PREFIX = "CT"
# Small tolerance so an appointment booked "now" is not rejected by the clock.
PAST_TOLERANCE = timedelta(minutes=10)


class AppointmentOverlapError(ConflictError):
    code = "appointment_overlap"
    title = "El técnico ya tiene otra cita"


def seed_field_services(session: Session, organization_id: uuid.UUID) -> None:
    """Services every new workshop starts with (prices are set by the workshop)."""
    for data in DEFAULT_SERVICES:
        session.add(FieldService(organization_id=organization_id, **data))
    session.flush()


def hours_of(organization: Organization) -> list[HoursDay]:
    stored = organization.field_service_hours
    days: list[HoursDay] = []
    for weekday in range(7):
        if stored is None:
            window = DEFAULT_HOURS[weekday]
        else:
            raw = stored.get(str(weekday))
            window = (raw[0], raw[1]) if raw else None
        days.append(
            HoursDay(
                weekday=weekday,
                opens=time.fromisoformat(window[0]) if window else None,
                closes=time.fromisoformat(window[1]) if window else None,
            )
        )
    return days


def schedule_problem(hours: list[HoursDay], starts_at: datetime, ends_at: datetime) -> str | None:
    """Why the time does not fit the service hours, or None when it fits."""
    start = starts_at.astimezone(BOGOTA)
    end = ends_at.astimezone(BOGOTA)
    if end.date() != start.date():
        return "La cita debe empezar y terminar el mismo día."
    holiday = holiday_name(start.date())
    if holiday:
        return f"El {start:%d/%m/%Y} es festivo ({holiday}); no hay servicio."
    day = hours[start.weekday()]
    if day.opens is None or day.closes is None:
        return "Ese día no hay servicio remoto ni en sitio."
    if start.time() < day.opens or end.time() > day.closes:
        return f"Fuera del horario de servicio de ese día ({day.opens:%H:%M} a {day.closes:%H:%M})."
    return None


class AppointmentService:
    def __init__(self, session: Session, orders: WorkOrderService) -> None:
        self._session = session
        self._orders = orders
        self._customers = CustomerService(session)
        self._audit = AuditService(session)

    # --- Settings: hours and service catalog ------------------------------------------------

    def hours(self, actor: User) -> HoursRead:
        organization = self._organization(actor)
        return HoursRead(
            days=hours_of(organization), is_default=organization.field_service_hours is None
        )

    def save_hours(self, actor: User, days: list[HoursDay], context: RequestContext) -> HoursRead:
        organization = self._organization(actor)
        stored = {
            str(d.weekday): [f"{d.opens:%H:%M}", f"{d.closes:%H:%M}"]
            if d.opens and d.closes
            else None
            for d in sorted(days, key=lambda d: d.weekday)
        }
        if organization.field_service_hours != stored:
            organization.field_service_hours = stored
            self._session.flush()
            self._record(
                actor,
                context,
                "appointments.hours_updated",
                "organization",
                organization.id,
                {"hours": stored},
            )
        return self.hours(actor)

    def services(self, actor: User, *, active_only: bool = False) -> list[FieldServiceRead]:
        query = select(FieldService).where(FieldService.organization_id == actor.organization_id)
        if active_only:
            query = query.where(FieldService.is_active.is_(True))
        return [
            FieldServiceRead.model_validate(s)
            for s in self._session.scalars(query.order_by(FieldService.name))
        ]

    def create_service(
        self, actor: User, data: FieldServiceWrite, context: RequestContext
    ) -> FieldServiceRead:
        self._ensure_name_free(actor, data.name, None)
        service = FieldService(organization_id=actor.organization_id, **_service_values(data))
        self._session.add(service)
        self._session.flush()
        self._record(
            actor,
            context,
            "field_service.created",
            "field_service",
            service.id,
            {"name": service.name, "price": _money(service.price)},
        )
        return FieldServiceRead.model_validate(service)

    def update_service(
        self, actor: User, service_id: uuid.UUID, data: FieldServiceWrite, context: RequestContext
    ) -> FieldServiceRead:
        service = self._service(actor, service_id)
        self._ensure_name_free(actor, data.name, service.id)
        changes: dict[str, Any] = {}
        for field, value in _service_values(data).items():
            if getattr(service, field) != value:
                changes[field] = [_plain(getattr(service, field)), _plain(value)]
                setattr(service, field, value)
        if changes:
            self._session.flush()
            self._record(
                actor, context, "field_service.updated", "field_service", service.id, changes
            )
        return FieldServiceRead.model_validate(service)

    # --- Agenda ---------------------------------------------------------------------------

    def options(self, actor: User) -> AgendaOptions:
        return AgendaOptions(
            hours=hours_of(self._organization(actor)),
            services=self.services(actor, active_only=True),
            technicians=[
                PersonRef(id=t.id, full_name=t.full_name) for t in self._orders.technicians(actor)
            ],
            localities=list(LOCALITIES),
            remote_access_text=REMOTE_ACCESS_TEXT,
            can_manage=Perm.APPOINTMENTS_MANAGE in actor.permission_codes,
        )

    @staticmethod
    def holidays_between(date_from: date, date_to: date) -> list[HolidayRead]:
        _check_range(date_from, date_to)
        return [
            HolidayRead(date=day, name=name)
            for year in range(date_from.year, date_to.year + 1)
            for day, name in holidays(year).items()
            if date_from <= day <= date_to
        ]

    def search(
        self,
        actor: User,
        date_from: date,
        date_to: date,
        *,
        technician_id: uuid.UUID | None = None,
        include_cancelled: bool = False,
    ) -> list[AppointmentRead]:
        _check_range(date_from, date_to)
        start = datetime.combine(date_from, time.min, BOGOTA)
        end = datetime.combine(date_to + timedelta(days=1), time.min, BOGOTA)
        query = select(Appointment).where(
            Appointment.organization_id == actor.organization_id,
            Appointment.starts_at < end,
            Appointment.ends_at > start,
        )
        if not include_cancelled:
            query = query.where(Appointment.status == AppointmentStatus.SCHEDULED)
        if not _sees_all(actor):
            query = query.where(Appointment.technician_id == actor.id)
        elif technician_id is not None:
            query = query.where(Appointment.technician_id == technician_id)
        items = list(self._session.scalars(query.order_by(Appointment.starts_at, Appointment.id)))
        return self._to_read_many(items)

    def read(self, actor: User, appointment_id: uuid.UUID) -> AppointmentRead:
        return self._to_read_many([self._get(actor, appointment_id)])[0]

    def create(
        self, actor: User, data: AppointmentCreate, context: RequestContext
    ) -> AppointmentRead:
        customer = self._customers.ensure_can_be_served(actor, data.customer_id)
        service = self._service(actor, data.service_id)
        if not service.is_active:
            raise BusinessRuleError("El servicio está inactivo.")
        modality = Modality(service.modality)
        if modality is Modality.ON_SITE and not (data.address and data.locality):
            raise BusinessRuleError("Indique la dirección y la localidad de la visita.")
        if modality is Modality.REMOTE and data.remote_consent_channel is None:
            raise BusinessRuleError("Registre la autorización del cliente para el acceso remoto.")
        technician_id = self._technician(actor, data.technician_id)
        starts_at = data.starts_at
        ends_at = starts_at + timedelta(minutes=data.duration_minutes or service.duration_minutes)
        self._check_time(actor, starts_at, ends_at)
        overlap_reason = self._check_overlap(
            actor, technician_id, starts_at, ends_at, None, data.overlap_reason
        )
        now = utcnow()
        appointment = Appointment(
            organization_id=actor.organization_id,
            number=next_document_number(
                self._session, actor.organization_id, DOC_TYPE, NUMBER_PREFIX
            ),
            customer_id=customer.id,
            service_id=service.id,
            modality=modality,
            status=AppointmentStatus.SCHEDULED,
            starts_at=starts_at,
            ends_at=ends_at,
            technician_id=technician_id,
            reason=data.reason,
            address=data.address if modality is Modality.ON_SITE else None,
            locality=data.locality if modality is Modality.ON_SITE else None,
            notes=data.notes,
            overlap_reason=overlap_reason,
            remote_consent_channel=(
                data.remote_consent_channel if modality is Modality.REMOTE else None
            ),
            remote_consent_text=REMOTE_ACCESS_TEXT if modality is Modality.REMOTE else None,
            remote_consent_at=now if modality is Modality.REMOTE else None,
            created_by_id=actor.id,
        )
        self._session.add(appointment)
        self._session.flush()
        self._record(
            actor,
            context,
            "appointment.created",
            "appointment",
            appointment.id,
            {
                "number": appointment.number,
                "customer_id": str(customer.id),
                "service_id": str(service.id),
                "modality": modality.value,
                "starts_at": starts_at.isoformat(),
                "technician_id": str(technician_id) if technician_id else None,
                "overlap": overlap_reason is not None,
                "remote_consent_channel": appointment.remote_consent_channel,
            },
        )
        return self.read(actor, appointment.id)

    def update(
        self,
        actor: User,
        appointment_id: uuid.UUID,
        data: AppointmentUpdate,
        context: RequestContext,
    ) -> AppointmentRead:
        appointment = self._get(actor, appointment_id, for_update=True)
        self._ensure_scheduled(appointment)
        fields = data.model_fields_set
        for required in ("starts_at", "duration_minutes", "reason"):
            if required in fields and getattr(data, required) is None:
                raise BusinessRuleError("La fecha, la duración y el motivo son obligatorios.")
        on_site = appointment.modality == Modality.ON_SITE
        if on_site and (
            ("address" in fields and not data.address)
            or ("locality" in fields and not data.locality)
        ):
            raise BusinessRuleError("Indique la dirección y la localidad de la visita.")

        starts_at = (
            data.starts_at if "starts_at" in fields and data.starts_at else (appointment.starts_at)
        )
        duration = (
            data.duration_minutes
            if "duration_minutes" in fields and data.duration_minutes
            else _minutes(appointment)
        )
        ends_at = starts_at + timedelta(minutes=duration)
        technician_id = (
            self._technician(actor, data.technician_id)
            if "technician_id" in fields
            else appointment.technician_id
        )
        moved = starts_at != appointment.starts_at or ends_at != appointment.ends_at
        if moved:
            self._check_time(actor, starts_at, ends_at)
        new_overlap = appointment.overlap_reason
        if moved or technician_id != appointment.technician_id:
            new_overlap = self._check_overlap(
                actor, technician_id, starts_at, ends_at, appointment.id, data.overlap_reason
            )

        changes: dict[str, Any] = {}
        values: dict[str, Any] = {
            "starts_at": starts_at,
            "ends_at": ends_at,
            "technician_id": technician_id,
            "overlap_reason": new_overlap,
        }
        for field in ("reason", "notes", "address", "locality"):
            if field in fields and (on_site or field not in ("address", "locality")):
                values[field] = getattr(data, field)
        for field, value in values.items():
            if getattr(appointment, field) != value:
                if field in ("starts_at", "ends_at", "technician_id"):
                    changes[field] = [_plain(getattr(appointment, field)), _plain(value)]
                else:
                    changes.setdefault("fields", []).append(field)
                setattr(appointment, field, value)
        if changes:
            self._session.flush()
            self._record(
                actor,
                context,
                "appointment.updated",
                "appointment",
                appointment.id,
                {"number": appointment.number, **changes},
            )
        return self.read(actor, appointment.id)

    def cancel(
        self, actor: User, appointment_id: uuid.UUID, reason: str, context: RequestContext
    ) -> AppointmentRead:
        appointment = self._get(actor, appointment_id, for_update=True)
        self._ensure_scheduled(appointment)
        appointment.status = AppointmentStatus.CANCELLED
        appointment.cancel_reason = reason
        appointment.cancelled_at = utcnow()
        self._session.flush()
        self._record(
            actor,
            context,
            "appointment.cancelled",
            "appointment",
            appointment.id,
            {"number": appointment.number},
        )
        return self.read(actor, appointment.id)

    # --- Rules ----------------------------------------------------------------------------

    def _check_time(self, actor: User, starts_at: datetime, ends_at: datetime) -> None:
        if starts_at < utcnow() - PAST_TOLERANCE:
            raise BusinessRuleError("No se pueden agendar citas en el pasado.")
        problem = schedule_problem(hours_of(self._organization(actor)), starts_at, ends_at)
        if problem:
            raise BusinessRuleError(problem)

    def _check_overlap(
        self,
        actor: User,
        technician_id: uuid.UUID | None,
        starts_at: datetime,
        ends_at: datetime,
        exclude_id: uuid.UUID | None,
        reason: str | None,
    ) -> str | None:
        """Returns the reason to store, or raises when the technician is busy without one."""
        if technician_id is None:
            return None
        query = select(Appointment).where(
            Appointment.organization_id == actor.organization_id,
            Appointment.technician_id == technician_id,
            Appointment.status == AppointmentStatus.SCHEDULED,
            and_(Appointment.starts_at < ends_at, Appointment.ends_at > starts_at),
        )
        if exclude_id is not None:
            query = query.where(Appointment.id != exclude_id)
        clashes = list(self._session.scalars(query.order_by(Appointment.starts_at)))
        if not clashes:
            return None
        if reason:
            return reason
        first = clashes[0]
        start = first.starts_at.astimezone(BOGOTA)
        end = first.ends_at.astimezone(BOGOTA)
        raise AppointmentOverlapError(
            f"El técnico ya tiene la cita {first.number} de {start:%H:%M} a {end:%H:%M}. "
            "Elija otra hora u otro técnico, o indique por qué se agenda de todas formas.",
            errors=[
                {
                    "number": c.number,
                    "starts_at": c.starts_at.isoformat(),
                    "ends_at": c.ends_at.isoformat(),
                }
                for c in clashes
            ],
        )

    def _technician(self, actor: User, technician_id: uuid.UUID | None) -> uuid.UUID | None:
        if technician_id is None:
            return None
        if not any(t.id == technician_id for t in self._orders.technicians(actor)):
            raise BusinessRuleError("El usuario no es un técnico activo del taller.")
        return technician_id

    def _ensure_name_free(self, actor: User, name: str, current: uuid.UUID | None) -> None:
        existing = self._session.scalar(
            select(FieldService.id).where(
                FieldService.organization_id == actor.organization_id,
                FieldService.name == name,
            )
        )
        if existing is not None and existing != current:
            raise ConflictError("Ya existe un servicio con ese nombre.")

    @staticmethod
    def _ensure_scheduled(appointment: Appointment) -> None:
        if appointment.status != AppointmentStatus.SCHEDULED:
            raise BusinessRuleError("La cita está cancelada y no se puede modificar.")

    # --- Lookups --------------------------------------------------------------------------

    def _organization(self, actor: User) -> Organization:
        organization = self._session.get(Organization, actor.organization_id)
        assert organization is not None  # noqa: S101 - FK guarantees it
        return organization

    def _service(self, actor: User, service_id: uuid.UUID) -> FieldService:
        service = self._session.scalar(
            select(FieldService).where(
                FieldService.id == service_id,
                FieldService.organization_id == actor.organization_id,
            )
        )
        if service is None:
            raise NotFoundError("El servicio no existe.")
        return service

    def _get(
        self, actor: User, appointment_id: uuid.UUID, *, for_update: bool = False
    ) -> Appointment:
        query = select(Appointment).where(
            Appointment.id == appointment_id,
            Appointment.organization_id == actor.organization_id,
        )
        if for_update:
            query = query.with_for_update()
        appointment = self._session.scalar(query)
        if appointment is None:
            raise NotFoundError("La cita no existe.")
        if not _sees_all(actor) and appointment.technician_id != actor.id:
            raise PermissionDeniedError("La cita está asignada a otro técnico.")
        return appointment

    def _to_read_many(self, items: list[Appointment]) -> list[AppointmentRead]:
        if not items:
            return []
        customers = {
            c.id: c
            for c in self._session.scalars(
                select(Customer).where(Customer.id.in_({a.customer_id for a in items}))
            )
        }
        services = {
            s.id: s
            for s in self._session.scalars(
                select(FieldService).where(FieldService.id.in_({a.service_id for a in items}))
            )
        }
        user_ids = {u for a in items for u in (a.technician_id, a.created_by_id) if u}
        users = {u.id: u for u in self._session.scalars(select(User).where(User.id.in_(user_ids)))}
        return [_read(a, customers[a.customer_id], services[a.service_id], users) for a in items]

    def _record(
        self,
        actor: User,
        context: RequestContext,
        action: str,
        entity_type: str,
        entity_id: uuid.UUID,
        changes: dict[str, Any],
    ) -> None:
        self._audit.record(
            action,
            entity_type=entity_type,
            entity_id=entity_id,
            organization_id=actor.organization_id,
            actor_user_id=actor.id,
            context=context,
            changes=changes,
        )


def _sees_all(actor: User) -> bool:
    perms = actor.permission_codes
    return Perm.APPOINTMENTS_MANAGE in perms or Perm.WORK_ORDERS_ASSIGN in perms


def _check_range(date_from: date, date_to: date) -> None:
    if date_to < date_from:
        raise BusinessRuleError("La fecha final debe ser igual o posterior a la inicial.")
    if (date_to - date_from).days > MAX_RANGE_DAYS:
        raise BusinessRuleError(f"Consulte como máximo {MAX_RANGE_DAYS} días a la vez.")


def _minutes(appointment: Appointment) -> int:
    return int((appointment.ends_at - appointment.starts_at).total_seconds() // 60)


def _service_values(data: FieldServiceWrite) -> dict[str, Any]:
    return {
        "name": data.name,
        "modality": data.modality.value,
        "duration_minutes": data.duration_minutes,
        "price": data.price,
        "tax_rate": Decimal(data.tax_rate),
        "price_includes_tax": data.price_includes_tax,
        "description": data.description,
        "is_active": data.is_active,
    }


def _money(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def _plain(value: Any) -> Any:
    if isinstance(value, Decimal | uuid.UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _person(user: User | None) -> PersonRef | None:
    return PersonRef(id=user.id, full_name=user.full_name) if user else None


def _read(
    a: Appointment, customer: Customer, service: FieldService, users: dict[uuid.UUID, User]
) -> AppointmentRead:
    return AppointmentRead(
        id=a.id,
        number=a.number,
        status=AppointmentStatus(a.status),
        modality=Modality(a.modality),
        customer=CustomerSummary(
            id=customer.id,
            full_name=customer.full_name,
            phone=customer.phone,
            id_type=customer.id_type,
            id_number=customer.id_number,
        ),
        service=ServiceRef(
            id=service.id,
            name=service.name,
            price=service.price,
            tax_rate=int(service.tax_rate),
            price_includes_tax=service.price_includes_tax,
        ),
        starts_at=a.starts_at,
        ends_at=a.ends_at,
        duration_minutes=_minutes(a),
        technician=_person(users.get(a.technician_id) if a.technician_id else None),
        reason=a.reason,
        address=a.address,
        locality=a.locality,
        notes=a.notes,
        overlap_reason=a.overlap_reason,
        remote_consent_channel=a.remote_consent_channel,
        remote_consent_text=a.remote_consent_text,
        remote_consent_at=a.remote_consent_at,
        cancel_reason=a.cancel_reason,
        cancelled_at=a.cancelled_at,
        created_by=_person(users.get(a.created_by_id) if a.created_by_id else None),
        created_at=a.created_at,
    )
