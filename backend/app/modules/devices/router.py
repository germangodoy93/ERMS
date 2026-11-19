import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.modules.auth.dependencies import CurrentUser, DbSession, require_permissions
from app.modules.devices.models import Device, DeviceCategory, DeviceModel, Manufacturer
from app.modules.devices.schemas import (
    CategoryRead,
    DeviceCreate,
    DeviceModelCreate,
    DeviceModelRead,
    DeviceModelUpdate,
    DeviceRead,
    DeviceSearchItem,
    DeviceUpdate,
    ManufacturerCreate,
    ManufacturerRead,
    ManufacturerUpdate,
)
from app.modules.devices.service import CatalogService, DeviceService
from app.modules.roles.catalog import Perm
from app.modules.users.models import User
from app.shared.context import RequestContext, get_request_context
from app.shared.pagination import Page, PageParams, page_params

catalog_router = APIRouter(prefix="/catalog", tags=["catalog"])
devices_router = APIRouter(tags=["devices"])

CatalogManager = Annotated[User, Depends(require_permissions(Perm.CATALOG_MANAGE))]
DeviceManager = Annotated[User, Depends(require_permissions(Perm.DEVICES_MANAGE))]
Reader = Annotated[User, Depends(require_permissions(Perm.CUSTOMERS_READ))]
Context = Annotated[RequestContext, Depends(get_request_context)]


def get_catalog_service(session: DbSession) -> CatalogService:
    return CatalogService(session)


def get_device_service(session: DbSession) -> DeviceService:
    return DeviceService(session)


Catalog = Annotated[CatalogService, Depends(get_catalog_service)]
Devices = Annotated[DeviceService, Depends(get_device_service)]


# --- Catalog ----------------------------------------------------------------------------


@catalog_router.get("/categories", response_model=list[CategoryRead], summary="Categorías")
def list_categories(actor: CurrentUser, catalog: Catalog) -> list[DeviceCategory]:
    return catalog.categories()


@catalog_router.get("/manufacturers", response_model=list[ManufacturerRead], summary="Fabricantes")
def list_manufacturers(
    actor: CurrentUser, catalog: Catalog, include_inactive: bool = False
) -> list[Manufacturer]:
    return catalog.manufacturers(actor, include_inactive=include_inactive)


@catalog_router.post(
    "/manufacturers",
    response_model=ManufacturerRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear fabricante",
)
def create_manufacturer(
    body: ManufacturerCreate, actor: CatalogManager, catalog: Catalog, context: Context
) -> Manufacturer:
    return catalog.create_manufacturer(actor, body, context)


@catalog_router.patch(
    "/manufacturers/{manufacturer_id}",
    response_model=ManufacturerRead,
    summary="Renombrar, activar o desactivar fabricante",
)
def update_manufacturer(
    manufacturer_id: uuid.UUID,
    body: ManufacturerUpdate,
    actor: CatalogManager,
    catalog: Catalog,
    context: Context,
) -> Manufacturer:
    return catalog.update_manufacturer(actor, manufacturer_id, body, context)


@catalog_router.get("/models", response_model=list[DeviceModelRead], summary="Modelos")
def list_models(
    actor: CurrentUser,
    catalog: Catalog,
    manufacturer_id: uuid.UUID | None = None,
    category: Annotated[str | None, Query(max_length=20)] = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
    include_inactive: bool = False,
) -> list[DeviceModel]:
    return catalog.models(
        actor,
        manufacturer_id=manufacturer_id,
        category_code=category,
        search=q,
        include_inactive=include_inactive,
    )


@catalog_router.post(
    "/models",
    response_model=DeviceModelRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear modelo (también desde el registro de un equipo)",
)
def create_model(
    body: DeviceModelCreate, actor: DeviceManager, catalog: Catalog, context: Context
) -> DeviceModel:
    return catalog.create_model(actor, body, context)


@catalog_router.patch("/models/{model_id}", response_model=DeviceModelRead, summary="Editar modelo")
def update_model(
    model_id: uuid.UUID,
    body: DeviceModelUpdate,
    actor: CatalogManager,
    catalog: Catalog,
    context: Context,
) -> DeviceModel:
    return catalog.update_model(actor, model_id, body, context)


# --- Devices ----------------------------------------------------------------------------


@devices_router.get(
    "/customers/{customer_id}/devices",
    response_model=list[DeviceRead],
    summary="Equipos del cliente",
)
def list_customer_devices(customer_id: uuid.UUID, actor: Reader, devices: Devices) -> list[Device]:
    return devices.for_customer(actor, customer_id)


@devices_router.post(
    "/customers/{customer_id}/devices",
    response_model=DeviceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar equipo del cliente",
)
def create_device(
    customer_id: uuid.UUID,
    body: DeviceCreate,
    actor: DeviceManager,
    devices: Devices,
    context: Context,
) -> Device:
    return devices.create(actor, customer_id, body, context)


@devices_router.get(
    "/devices", response_model=Page[DeviceSearchItem], summary="Buscar por serial, IMEI o modelo"
)
def search_devices(
    actor: Reader,
    devices: Devices,
    params: Annotated[PageParams, Depends(page_params)],
    q: Annotated[str, Query(min_length=3, max_length=100)],
) -> Page[DeviceSearchItem]:
    items, total = devices.search(actor, params, search=q)
    return Page(items=items, total=total, page=params.page, size=params.size)


@devices_router.get("/devices/{device_id}", response_model=DeviceRead, summary="Detalle")
def get_device(device_id: uuid.UUID, actor: Reader, devices: Devices) -> Device:
    return devices.get(actor, device_id)


@devices_router.patch("/devices/{device_id}", response_model=DeviceRead, summary="Editar equipo")
def update_device(
    device_id: uuid.UUID,
    body: DeviceUpdate,
    actor: DeviceManager,
    devices: Devices,
    context: Context,
) -> Device:
    return devices.update(actor, device_id, body, context)
