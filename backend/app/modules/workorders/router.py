import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.core.storage import Storage, get_storage
from app.modules.auth.dependencies import (
    AppSettings,
    CurrentUser,
    DbSession,
    require_any_permission,
    require_permissions,
)
from app.modules.organizations.models import Organization
from app.modules.roles.catalog import Perm
from app.modules.users.models import User
from app.modules.workorders.catalog import Status
from app.modules.workorders.models import ReceptionTerms
from app.modules.workorders.pdf import build_reception_act
from app.modules.workorders.schemas import (
    Assignment,
    CurrentReceptionTerms,
    DeliveryRequest,
    PersonRef,
    PhotoList,
    PhotoRead,
    ReceptionTermsPublish,
    ReceptionTermsRead,
    StatusChange,
    WorkOrderCreate,
    WorkOrderListItem,
    WorkOrderRead,
    WorkOrderUpdate,
)
from app.modules.workorders.service import (
    ReceptionTermsService,
    WorkOrderFilters,
    WorkOrderService,
)
from app.modules.workorders.terms_template import RECEPTION_TERMS_TEMPLATE
from app.shared.context import RequestContext, get_request_context
from app.shared.pagination import Page, PageParams, page_params

terms_router = APIRouter(prefix="/reception-terms", tags=["work-orders"])
router = APIRouter(prefix="/work-orders", tags=["work-orders"])

Reader = Annotated[User, Depends(require_permissions(Perm.WORK_ORDERS_READ))]
Creator = Annotated[User, Depends(require_permissions(Perm.WORK_ORDERS_CREATE))]
Assigner = Annotated[User, Depends(require_permissions(Perm.WORK_ORDERS_ASSIGN))]
Deliverer = Annotated[User, Depends(require_permissions(Perm.WORK_ORDERS_DELIVER))]
Mover = Annotated[
    User,
    Depends(require_any_permission(Perm.WORK_ORDERS_PROGRESS, Perm.WORK_ORDERS_DELIVER)),
]
PhotoTaker = Annotated[
    User,
    Depends(require_any_permission(Perm.WORK_ORDERS_CREATE, Perm.WORK_ORDERS_PROGRESS)),
]
OrgManager = Annotated[User, Depends(require_permissions(Perm.ORGANIZATION_MANAGE))]
Context = Annotated[RequestContext, Depends(get_request_context)]


def get_work_order_service(
    session: DbSession, settings: AppSettings, storage: Annotated[Storage, Depends(get_storage)]
) -> WorkOrderService:
    return WorkOrderService(session, settings, storage)


def get_terms_service(session: DbSession) -> ReceptionTermsService:
    return ReceptionTermsService(session)


Service = Annotated[WorkOrderService, Depends(get_work_order_service)]
Terms = Annotated[ReceptionTermsService, Depends(get_terms_service)]


# --- Reception terms ---------------------------------------------------------------------


@terms_router.get("", response_model=CurrentReceptionTerms, summary="Condiciones vigentes")
def get_terms(actor: CurrentUser, terms: Terms) -> CurrentReceptionTerms:
    current = terms.current(actor.organization_id)
    return CurrentReceptionTerms(
        terms=ReceptionTermsRead.model_validate(current) if current else None,
        template=RECEPTION_TERMS_TEMPLATE,
    )


@terms_router.post(
    "",
    response_model=ReceptionTermsRead,
    status_code=status.HTTP_201_CREATED,
    summary="Publicar una nueva versión de las condiciones",
)
def publish_terms(
    body: ReceptionTermsPublish, actor: OrgManager, terms: Terms, context: Context
) -> ReceptionTerms:
    return terms.publish(actor, body.content, context)


# --- Work orders -------------------------------------------------------------------------


@router.get("", response_model=Page[WorkOrderListItem], summary="Buscar órdenes")
def list_work_orders(
    actor: Reader,
    service: Service,
    params: Annotated[PageParams, Depends(page_params)],
    status_in: Annotated[list[Status] | None, Query(alias="status")] = None,
    technician_id: uuid.UUID | None = None,
    unassigned: bool = False,
    open_only: Annotated[bool, Query(alias="open")] = False,
    q: Annotated[
        str | None, Query(max_length=100, description="Número, cliente, IMEI, serial o modelo")
    ] = None,
) -> Page[WorkOrderListItem]:
    filters = WorkOrderFilters(
        statuses=status_in,
        technician_id=technician_id,
        unassigned=unassigned,
        open_only=open_only,
        search=q,
    )
    items, total = service.search(actor, params, filters)
    return Page(items=items, total=total, page=params.page, size=params.size)


@router.post(
    "",
    response_model=WorkOrderRead,
    status_code=status.HTTP_201_CREATED,
    summary="Recibir un equipo (crear orden)",
)
def create_work_order(
    body: WorkOrderCreate, actor: Creator, service: Service, context: Context
) -> WorkOrderRead:
    return service.create(actor, body, context)


@router.get(
    "/technicians", response_model=list[PersonRef], summary="Técnicos que se pueden asignar"
)
def list_technicians(actor: Assigner, service: Service) -> list[PersonRef]:
    return [PersonRef(id=u.id, full_name=u.full_name) for u in service.technicians(actor)]


@router.get("/{order_id}", response_model=WorkOrderRead, summary="Detalle de la orden")
def get_work_order(order_id: uuid.UUID, actor: Reader, service: Service) -> WorkOrderRead:
    return service.read(actor, order_id)


@router.patch("/{order_id}", response_model=WorkOrderRead, summary="Corregir datos de recepción")
def update_work_order(
    order_id: uuid.UUID, body: WorkOrderUpdate, actor: Creator, service: Service, context: Context
) -> WorkOrderRead:
    return service.update(actor, order_id, body, context)


@router.put("/{order_id}/assignment", response_model=WorkOrderRead, summary="Asignar técnico")
def assign_work_order(
    order_id: uuid.UUID, body: Assignment, actor: Assigner, service: Service, context: Context
) -> WorkOrderRead:
    return service.assign(actor, order_id, body.technician_id, context)


@router.post("/{order_id}/status", response_model=WorkOrderRead, summary="Cambiar de estado")
def change_status(
    order_id: uuid.UUID, body: StatusChange, actor: Mover, service: Service, context: Context
) -> WorkOrderRead:
    return service.change_status(actor, order_id, body.status, body.reason, context)


@router.post("/{order_id}/delivery", response_model=WorkOrderRead, summary="Entregar el equipo")
def deliver(
    order_id: uuid.UUID, body: DeliveryRequest, actor: Deliverer, service: Service, context: Context
) -> WorkOrderRead:
    return service.deliver(actor, order_id, body, context)


@router.get(
    "/{order_id}/reception-act.pdf",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}}},
    summary="Acta de recepción en PDF",
)
def reception_act(
    order_id: uuid.UUID, actor: Reader, service: Service, session: DbSession
) -> Response:
    order = service.read(actor, order_id)
    organization = _organization(session, actor)
    terms = service.terms_content(actor, order_id)
    pdf = build_reception_act(order, organization, terms)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="acta-{order.number}.pdf"',
            "Cache-Control": "no-store",
        },
    )


@router.get("/{order_id}/photos", response_model=PhotoList, summary="Fotos del equipo")
def list_photos(
    order_id: uuid.UUID, actor: Reader, service: Service, settings: AppSettings
) -> PhotoList:
    items, demo = service.photos(actor, order_id)
    return PhotoList(
        demo=demo,
        max_photos=settings.attachment_max_per_order,
        items=[PhotoRead.model_validate(a) for a in items],
    )


@router.post(
    "/{order_id}/photos",
    response_model=PhotoRead,
    status_code=status.HTTP_201_CREATED,
    summary="Subir foto (requiere autorización de fotos del cliente)",
)
def upload_photo(
    order_id: uuid.UUID,
    file: UploadFile,
    actor: PhotoTaker,
    service: Service,
    settings: AppSettings,
    context: Context,
) -> PhotoRead:
    # Sync handler (runs in the threadpool, like the DB calls). Reading one byte more than
    # the limit detects oversized files without loading them whole.
    data = file.file.read(settings.attachment_max_bytes + 1)
    attachment = service.add_photo(actor, order_id, data, file.filename or "foto", context)
    return PhotoRead.model_validate(attachment)


@router.get(
    "/{order_id}/photos/{attachment_id}",
    response_class=Response,
    responses={200: {"content": {"image/jpeg": {}}}},
    summary="Contenido de una foto",
)
def photo_content(
    order_id: uuid.UUID, attachment_id: uuid.UUID, actor: Reader, service: Service
) -> Response:
    data = service.photo_content(actor, order_id, attachment_id)
    return Response(
        content=data, media_type="image/jpeg", headers={"Cache-Control": "private, no-store"}
    )


@router.delete(
    "/{order_id}/photos/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar foto",
)
def delete_photo(
    order_id: uuid.UUID,
    attachment_id: uuid.UUID,
    actor: PhotoTaker,
    service: Service,
    context: Context,
) -> None:
    service.delete_photo(actor, order_id, attachment_id, context)


def _organization(session: Session, actor: User) -> Organization:
    organization = session.get(Organization, actor.organization_id)
    assert organization is not None  # noqa: S101 - FK guarantees it
    return organization
