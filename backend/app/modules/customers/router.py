import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.modules.auth.dependencies import DbSession, require_permissions
from app.modules.customers.models import Customer
from app.modules.customers.schemas import (
    AnonymizeRequest,
    ConsentChange,
    ConsentRecordRead,
    CustomerCreate,
    CustomerListItem,
    CustomerRead,
    CustomerUpdate,
)
from app.modules.customers.service import CustomerService
from app.modules.roles.catalog import Perm
from app.modules.users.models import User
from app.shared.context import RequestContext, get_request_context
from app.shared.pagination import Page, PageParams, page_params

router = APIRouter(prefix="/customers", tags=["customers"])

Reader = Annotated[User, Depends(require_permissions(Perm.CUSTOMERS_READ))]
Manager = Annotated[User, Depends(require_permissions(Perm.CUSTOMERS_MANAGE))]
Anonymizer = Annotated[User, Depends(require_permissions(Perm.CUSTOMERS_ANONYMIZE))]
Context = Annotated[RequestContext, Depends(get_request_context)]


def get_customer_service(session: DbSession) -> CustomerService:
    return CustomerService(session)


Service = Annotated[CustomerService, Depends(get_customer_service)]


@router.get("", response_model=Page[CustomerListItem], summary="Buscar clientes")
def list_customers(
    actor: Reader,
    service: Service,
    params: Annotated[PageParams, Depends(page_params)],
    q: Annotated[
        str | None, Query(max_length=100, description="Nombre, documento o teléfono")
    ] = None,
    is_active: bool | None = None,
) -> Page[CustomerListItem]:
    items: list[Customer]
    items, total = service.search(actor, params, search=q, is_active=is_active)
    return Page(
        items=[CustomerListItem.model_validate(c) for c in items],
        total=total,
        page=params.page,
        size=params.size,
    )


@router.post(
    "",
    response_model=CustomerRead,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar cliente con su autorización de datos",
)
def create_customer(
    body: CustomerCreate, actor: Manager, service: Service, context: Context
) -> CustomerRead:
    return service.create(actor, body, context)


@router.get("/{customer_id}", response_model=CustomerRead, summary="Ficha del cliente")
def get_customer(customer_id: uuid.UUID, actor: Reader, service: Service) -> CustomerRead:
    return service.read(actor, customer_id)


@router.patch("/{customer_id}", response_model=CustomerRead, summary="Editar, activar o desactivar")
def update_customer(
    customer_id: uuid.UUID, body: CustomerUpdate, actor: Manager, service: Service, context: Context
) -> CustomerRead:
    return service.update(actor, customer_id, body, context)


@router.get(
    "/{customer_id}/consents",
    response_model=list[ConsentRecordRead],
    summary="Historial de autorizaciones",
)
def list_consents(
    customer_id: uuid.UUID, actor: Reader, service: Service
) -> list[ConsentRecordRead]:
    return service.consent_history(actor, customer_id)


@router.post(
    "/{customer_id}/consents",
    response_model=CustomerRead,
    summary="Otorgar o revocar una autorización",
)
def change_consent(
    customer_id: uuid.UUID, body: ConsentChange, actor: Manager, service: Service, context: Context
) -> CustomerRead:
    return service.change_consent(actor, customer_id, body, context)


@router.post(
    "/{customer_id}/anonymize",
    response_model=CustomerRead,
    summary="Anonimizar (derecho de supresión, irreversible)",
)
def anonymize_customer(
    customer_id: uuid.UUID,
    body: AnonymizeRequest,
    actor: Anonymizer,
    service: Service,
    context: Context,
) -> CustomerRead:
    return service.anonymize(actor, customer_id, body.channel, context)
