import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.storage import Storage, get_storage
from app.modules.auth.dependencies import AppSettings, DbSession, require_permissions
from app.modules.repairs.schemas import (
    ConsumeRequest,
    QcCreate,
    QcRead,
    RepairOverview,
    TaskCreate,
    TaskRead,
)
from app.modules.repairs.service import RepairService
from app.modules.roles.catalog import Perm
from app.modules.users.models import User
from app.shared.context import RequestContext, get_request_context

router = APIRouter(prefix="/work-orders/{order_id}/repair", tags=["repairs"])

Reader = Annotated[User, Depends(require_permissions(Perm.WORK_ORDERS_READ))]
Repairer = Annotated[User, Depends(require_permissions(Perm.REPAIRS_MANAGE))]
Context = Annotated[RequestContext, Depends(get_request_context)]


def get_repair_service(
    session: DbSession, settings: AppSettings, storage: Annotated[Storage, Depends(get_storage)]
) -> RepairService:
    return RepairService(session, settings, storage)


Service = Annotated[RepairService, Depends(get_repair_service)]


@router.get("", response_model=RepairOverview, summary="Reparación y control de calidad")
def get_repair(order_id: uuid.UUID, actor: Reader, service: Service) -> RepairOverview:
    return service.overview(actor, order_id)


@router.post(
    "/tasks", response_model=TaskRead, status_code=status.HTTP_201_CREATED, summary="Nueva tarea"
)
def add_task(
    order_id: uuid.UUID, body: TaskCreate, actor: Repairer, service: Service, context: Context
) -> TaskRead:
    return service.add_task(actor, order_id, body, context)


@router.post(
    "/tasks/{task_id}/parts", response_model=TaskRead, summary="Consumir repuesto del inventario"
)
def consume_part(
    order_id: uuid.UUID,
    task_id: uuid.UUID,
    body: ConsumeRequest,
    actor: Repairer,
    service: Service,
    context: Context,
) -> TaskRead:
    return service.consume(actor, order_id, task_id, body, context)


@router.post(
    "/tasks/{task_id}/parts/{repair_part_id}/return",
    response_model=TaskRead,
    summary="Devolver repuesto al inventario",
)
def return_part(
    order_id: uuid.UUID,
    task_id: uuid.UUID,
    repair_part_id: uuid.UUID,
    actor: Repairer,
    service: Service,
    context: Context,
) -> TaskRead:
    return service.return_part(actor, order_id, task_id, repair_part_id, context)


@router.post(
    "/quality-checks",
    response_model=QcRead,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar control de calidad",
)
def quality_check(
    order_id: uuid.UUID, body: QcCreate, actor: Repairer, service: Service, context: Context
) -> QcRead:
    return service.quality_check(actor, order_id, body, context)
