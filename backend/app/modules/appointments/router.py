import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.modules.appointments.schemas import (
    AgendaOptions,
    AppointmentCancel,
    AppointmentCreate,
    AppointmentRead,
    AppointmentUpdate,
    FieldServiceRead,
    FieldServiceWrite,
    HolidayRead,
    HoursRead,
    HoursUpdate,
)
from app.modules.appointments.service import AppointmentService
from app.modules.auth.dependencies import DbSession, require_permissions
from app.modules.roles.catalog import Perm
from app.modules.users.models import User
from app.modules.workorders.router import get_work_order_service
from app.modules.workorders.service import WorkOrderService
from app.shared.context import RequestContext, get_request_context

router = APIRouter(prefix="/appointments", tags=["appointments"])

Reader = Annotated[User, Depends(require_permissions(Perm.WORK_ORDERS_READ))]
Scheduler = Annotated[
    User, Depends(require_permissions(Perm.WORK_ORDERS_READ, Perm.APPOINTMENTS_MANAGE))
]
Manager = Annotated[User, Depends(require_permissions(Perm.ORGANIZATION_MANAGE))]
Context = Annotated[RequestContext, Depends(get_request_context)]


def get_appointment_service(
    session: DbSession, orders: Annotated[WorkOrderService, Depends(get_work_order_service)]
) -> AppointmentService:
    return AppointmentService(session, orders)


Service = Annotated[AppointmentService, Depends(get_appointment_service)]


# --- Settings (declared before /{appointment_id}) ------------------------------------------


@router.get("/options", response_model=AgendaOptions, summary="Datos para agendar")
def get_options(actor: Reader, service: Service) -> AgendaOptions:
    return service.options(actor)


@router.get("/holidays", response_model=list[HolidayRead], summary="Festivos de Colombia")
def get_holidays(
    _actor: Reader,
    date_from: Annotated[date, Query(alias="from")],
    date_to: Annotated[date, Query(alias="to")],
) -> list[HolidayRead]:
    return AppointmentService.holidays_between(date_from, date_to)


@router.get("/hours", response_model=HoursRead, summary="Horario de servicio remoto y en sitio")
def get_hours(actor: Reader, service: Service) -> HoursRead:
    return service.hours(actor)


@router.put("/hours", response_model=HoursRead, summary="Cambiar el horario de servicio")
def save_hours(body: HoursUpdate, actor: Manager, service: Service, context: Context) -> HoursRead:
    return service.save_hours(actor, body.days, context)


@router.get("/services", response_model=list[FieldServiceRead], summary="Catálogo de servicios")
def list_services(actor: Reader, service: Service) -> list[FieldServiceRead]:
    return service.services(actor)


@router.post(
    "/services",
    response_model=FieldServiceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un servicio",
)
def create_service(
    body: FieldServiceWrite, actor: Manager, service: Service, context: Context
) -> FieldServiceRead:
    return service.create_service(actor, body, context)


@router.put("/services/{service_id}", response_model=FieldServiceRead, summary="Editar un servicio")
def update_service(
    service_id: uuid.UUID,
    body: FieldServiceWrite,
    actor: Manager,
    service: Service,
    context: Context,
) -> FieldServiceRead:
    return service.update_service(actor, service_id, body, context)


# --- Appointments --------------------------------------------------------------------------


@router.get("", response_model=list[AppointmentRead], summary="Citas en un rango de fechas")
def list_appointments(
    actor: Reader,
    service: Service,
    date_from: Annotated[date, Query(alias="from")],
    date_to: Annotated[date, Query(alias="to")],
    technician_id: uuid.UUID | None = None,
    include_cancelled: bool = False,
) -> list[AppointmentRead]:
    return service.search(
        actor,
        date_from,
        date_to,
        technician_id=technician_id,
        include_cancelled=include_cancelled,
    )


@router.post(
    "",
    response_model=AppointmentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Agendar una cita remota o en sitio",
    responses={409: {"description": "El técnico ya tiene otra cita (`appointment_overlap`)"}},
)
def create_appointment(
    body: AppointmentCreate, actor: Scheduler, service: Service, context: Context
) -> AppointmentRead:
    return service.create(actor, body, context)


@router.get("/{appointment_id}", response_model=AppointmentRead, summary="Detalle de una cita")
def get_appointment(appointment_id: uuid.UUID, actor: Reader, service: Service) -> AppointmentRead:
    return service.read(actor, appointment_id)


@router.patch(
    "/{appointment_id}",
    response_model=AppointmentRead,
    summary="Mover, reasignar o corregir una cita",
    responses={409: {"description": "El técnico ya tiene otra cita (`appointment_overlap`)"}},
)
def update_appointment(
    appointment_id: uuid.UUID,
    body: AppointmentUpdate,
    actor: Scheduler,
    service: Service,
    context: Context,
) -> AppointmentRead:
    return service.update(actor, appointment_id, body, context)


@router.post(
    "/{appointment_id}/cancel", response_model=AppointmentRead, summary="Cancelar una cita"
)
def cancel_appointment(
    appointment_id: uuid.UUID,
    body: AppointmentCancel,
    actor: Scheduler,
    service: Service,
    context: Context,
) -> AppointmentRead:
    return service.cancel(actor, appointment_id, body.reason, context)
