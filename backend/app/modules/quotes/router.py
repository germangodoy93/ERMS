import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.core.storage import Storage, get_storage
from app.modules.auth.dependencies import AppSettings, DbSession, require_permissions
from app.modules.organizations.models import Organization
from app.modules.quotes.pdf import build_quote
from app.modules.quotes.schemas import QuoteOverview, QuoteRead, QuoteSave, RespondRequest
from app.modules.quotes.service import QuoteService
from app.modules.roles.catalog import Perm
from app.modules.users.models import User
from app.modules.workorders.service import WorkOrderService
from app.shared.context import RequestContext, get_request_context

router = APIRouter(prefix="/work-orders/{order_id}/quotes", tags=["quotes"])

Reader = Annotated[User, Depends(require_permissions(Perm.WORK_ORDERS_READ))]
Editor = Annotated[User, Depends(require_permissions(Perm.QUOTES_MANAGE))]
Context = Annotated[RequestContext, Depends(get_request_context)]


def get_quote_service(
    session: DbSession, settings: AppSettings, storage: Annotated[Storage, Depends(get_storage)]
) -> QuoteService:
    return QuoteService(session, settings, storage)


Service = Annotated[QuoteService, Depends(get_quote_service)]


@router.get("", response_model=QuoteOverview, summary="Cotizaciones de la orden")
def list_quotes(order_id: uuid.UUID, actor: Reader, service: Service) -> QuoteOverview:
    return service.overview(actor, order_id)


@router.post(
    "",
    response_model=QuoteRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear borrador (copia la versión anterior)",
)
def create_quote(
    order_id: uuid.UUID, actor: Editor, service: Service, context: Context
) -> QuoteRead:
    return service.create_draft(actor, order_id, context)


@router.put("/{quote_id}", response_model=QuoteRead, summary="Guardar ítems del borrador")
def save_quote(
    order_id: uuid.UUID,
    quote_id: uuid.UUID,
    body: QuoteSave,
    actor: Editor,
    service: Service,
    context: Context,
) -> QuoteRead:
    return service.save(actor, order_id, quote_id, body, context)


@router.delete("/{quote_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Descartar borrador")
def discard_quote(
    order_id: uuid.UUID, quote_id: uuid.UUID, actor: Editor, service: Service, context: Context
) -> None:
    service.discard(actor, order_id, quote_id, context)


@router.post("/{quote_id}/send", response_model=QuoteRead, summary="Enviar al cliente")
def send_quote(
    order_id: uuid.UUID, quote_id: uuid.UUID, actor: Reader, service: Service, context: Context
) -> QuoteRead:
    return service.send(actor, order_id, quote_id, context)


@router.post(
    "/{quote_id}/response", response_model=QuoteRead, summary="Registrar respuesta del cliente"
)
def respond_quote(
    order_id: uuid.UUID,
    quote_id: uuid.UUID,
    body: RespondRequest,
    actor: Reader,
    service: Service,
    context: Context,
) -> QuoteRead:
    return service.respond(actor, order_id, quote_id, body, context)


@router.get(
    "/{quote_id}/pdf",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}}},
    summary="Cotización en PDF",
)
def quote_pdf(
    order_id: uuid.UUID,
    quote_id: uuid.UUID,
    actor: Reader,
    service: Service,
    session: DbSession,
    settings: AppSettings,
    storage: Annotated[Storage, Depends(get_storage)],
) -> Response:
    quote = service.read(actor, order_id, quote_id)
    order = WorkOrderService(session, settings, storage).read(actor, order_id)
    organization = session.get(Organization, actor.organization_id)
    assert organization is not None  # noqa: S101 - FK guarantees it
    return Response(
        content=build_quote(organization, order, quote),
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="cotizacion-{order.number}-v{quote.version}.pdf"'
            ),
            "Cache-Control": "no-store",
        },
    )
