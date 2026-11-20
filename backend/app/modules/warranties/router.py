import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.storage import Storage, get_storage
from app.modules.auth.dependencies import AppSettings, DbSession, require_permissions
from app.modules.roles.catalog import Perm
from app.modules.users.models import User
from app.modules.warranties.schemas import ClaimCreate, ClaimDecision, ClaimRead, WarrantyOverview
from app.modules.warranties.service import WarrantyService
from app.modules.workorders.schemas import WorkOrderRead
from app.shared.context import RequestContext, get_request_context

router = APIRouter(prefix="/work-orders/{order_id}/warranty", tags=["warranties"])

Reader = Annotated[User, Depends(require_permissions(Perm.WORK_ORDERS_READ))]
Manager = Annotated[User, Depends(require_permissions(Perm.WARRANTIES_MANAGE))]
Context = Annotated[RequestContext, Depends(get_request_context)]


def get_warranty_service(
    session: DbSession, settings: AppSettings, storage: Annotated[Storage, Depends(get_storage)]
) -> WarrantyService:
    return WarrantyService(session, settings, storage)


Service = Annotated[WarrantyService, Depends(get_warranty_service)]


@router.get("", response_model=WarrantyOverview, summary="Garantía y reclamos")
def get_warranty(order_id: uuid.UUID, actor: Reader, service: Service) -> WarrantyOverview:
    return service.overview(actor, order_id)


@router.post(
    "/claims",
    response_model=WorkOrderRead,
    status_code=status.HTTP_201_CREATED,
    summary="Abrir reclamo (crea una orden vinculada, sin diagnóstico)",
)
def open_claim(
    order_id: uuid.UUID, body: ClaimCreate, actor: Manager, service: Service, context: Context
) -> WorkOrderRead:
    return service.open_claim(actor, order_id, body, context)


@router.post("/claims/{claim_id}/decision", response_model=ClaimRead, summary="Resolver reclamo")
def decide_claim(
    order_id: uuid.UUID,
    claim_id: uuid.UUID,
    body: ClaimDecision,
    actor: Manager,
    service: Service,
    context: Context,
) -> ClaimRead:
    return service.decide(actor, order_id, claim_id, body, context)
