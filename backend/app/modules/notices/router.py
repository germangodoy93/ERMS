import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.modules.auth.dependencies import DbSession, require_permissions
from app.modules.notices.catalog import NoticeKind
from app.modules.notices.schemas import (
    NoticeCreate,
    NoticePanel,
    PendingNotice,
    PreparedNotice,
    TemplatesRead,
    TemplateUpdate,
)
from app.modules.notices.service import NoticeService
from app.modules.roles.catalog import Perm
from app.modules.users.models import User
from app.shared.context import RequestContext, get_request_context

router = APIRouter(prefix="/notices", tags=["notices"])
order_router = APIRouter(prefix="/work-orders/{order_id}/notices", tags=["notices"])

Reader = Annotated[User, Depends(require_permissions(Perm.WORK_ORDERS_READ))]
Notifier = Annotated[
    User, Depends(require_permissions(Perm.WORK_ORDERS_READ, Perm.CUSTOMERS_NOTIFY))
]
Manager = Annotated[User, Depends(require_permissions(Perm.ORGANIZATION_MANAGE))]
Context = Annotated[RequestContext, Depends(get_request_context)]


def get_notice_service(session: DbSession) -> NoticeService:
    return NoticeService(session)


Service = Annotated[NoticeService, Depends(get_notice_service)]


@order_router.get("", response_model=NoticePanel, summary="Avisos al cliente de la orden")
def get_panel(order_id: uuid.UUID, actor: Reader, service: Service) -> NoticePanel:
    return service.panel(actor, order_id)


@order_router.post(
    "",
    response_model=PreparedNotice,
    status_code=status.HTTP_201_CREATED,
    summary="Preparar un aviso por WhatsApp (devuelve el enlace wa.me)",
)
def prepare_notice(
    order_id: uuid.UUID, body: NoticeCreate, actor: Notifier, service: Service, context: Context
) -> PreparedNotice:
    return service.prepare(actor, order_id, body, context)


@router.get("/pending", response_model=list[PendingNotice], summary="Órdenes por avisar")
def pending_notices(actor: Notifier, service: Service) -> list[PendingNotice]:
    return service.pending(actor)


@router.get("/templates", response_model=TemplatesRead, summary="Textos de los avisos")
def get_templates(actor: Manager, service: Service) -> TemplatesRead:
    return service.templates(actor)


@router.put("/templates/{kind}", response_model=TemplatesRead, summary="Editar un texto")
def save_template(
    kind: NoticeKind, body: TemplateUpdate, actor: Manager, service: Service, context: Context
) -> TemplatesRead:
    return service.save_template(actor, kind, body.body, context)


@router.delete(
    "/templates/{kind}", response_model=TemplatesRead, summary="Restaurar el texto original"
)
def reset_template(
    kind: NoticeKind, actor: Manager, service: Service, context: Context
) -> TemplatesRead:
    return service.reset_template(actor, kind, context)
