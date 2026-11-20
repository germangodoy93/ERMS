import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.modules.auth.dependencies import DbSession, require_permissions
from app.modules.inventory.models import Supplier
from app.modules.inventory.schemas import (
    AdjustmentCreate,
    MovementRead,
    PartRead,
    PartWrite,
    StockEntryCreate,
    StockEntryRead,
    SupplierRead,
    SupplierWrite,
)
from app.modules.inventory.service import InventoryService
from app.modules.roles.catalog import Perm
from app.modules.users.models import User
from app.shared.context import RequestContext, get_request_context

router = APIRouter(prefix="/inventory", tags=["inventory"])

Reader = Annotated[User, Depends(require_permissions(Perm.INVENTORY_READ))]
Manager = Annotated[User, Depends(require_permissions(Perm.INVENTORY_MANAGE))]
Context = Annotated[RequestContext, Depends(get_request_context)]


def get_inventory_service(session: DbSession) -> InventoryService:
    return InventoryService(session)


Service = Annotated[InventoryService, Depends(get_inventory_service)]


@router.get("/parts", response_model=list[PartRead], summary="Repuestos con existencia")
def list_parts(
    actor: Reader,
    service: Service,
    q: Annotated[str | None, Query(max_length=100, description="Código o nombre")] = None,
    low_stock: bool = False,
    include_inactive: bool = False,
) -> list[PartRead]:
    return service.search(actor, search=q, low_stock=low_stock, include_inactive=include_inactive)


@router.post(
    "/parts", response_model=PartRead, status_code=status.HTTP_201_CREATED, summary="Nuevo repuesto"
)
def create_part(body: PartWrite, actor: Manager, service: Service, context: Context) -> PartRead:
    return service.save_part(actor, body, context)


@router.get("/parts/{part_id}", response_model=PartRead, summary="Detalle del repuesto")
def get_part(part_id: uuid.UUID, actor: Reader, service: Service) -> PartRead:
    return service.read_part(actor, part_id)


@router.put("/parts/{part_id}", response_model=PartRead, summary="Editar repuesto")
def update_part(
    part_id: uuid.UUID, body: PartWrite, actor: Manager, service: Service, context: Context
) -> PartRead:
    return service.save_part(actor, body, context, part_id)


@router.get("/parts/{part_id}/movements", response_model=list[MovementRead], summary="Movimientos")
def part_movements(part_id: uuid.UUID, actor: Reader, service: Service) -> list[MovementRead]:
    return service.movements(actor, part_id)


@router.post(
    "/parts/{part_id}/adjustments",
    response_model=PartRead,
    summary="Ajuste por conteo físico",
)
def adjust(
    part_id: uuid.UUID, body: AdjustmentCreate, actor: Manager, service: Service, context: Context
) -> PartRead:
    return service.adjust(actor, part_id, body, context)


@router.post(
    "/entries",
    response_model=StockEntryRead,
    status_code=status.HTTP_201_CREATED,
    summary="Entrada de inventario (compra)",
)
def receive(
    body: StockEntryCreate, actor: Manager, service: Service, context: Context
) -> StockEntryRead:
    return service.receive(actor, body, context)


@router.get("/suppliers", response_model=list[SupplierRead], summary="Proveedores")
def list_suppliers(
    actor: Reader, service: Service, include_inactive: bool = False
) -> list[Supplier]:
    return service.suppliers(actor, include_inactive=include_inactive)


@router.post(
    "/suppliers",
    response_model=SupplierRead,
    status_code=status.HTTP_201_CREATED,
    summary="Nuevo proveedor",
)
def create_supplier(
    body: SupplierWrite, actor: Manager, service: Service, context: Context
) -> Supplier:
    return service.save_supplier(actor, body, context)


@router.put("/suppliers/{supplier_id}", response_model=SupplierRead, summary="Editar proveedor")
def update_supplier(
    supplier_id: uuid.UUID,
    body: SupplierWrite,
    actor: Manager,
    service: Service,
    context: Context,
) -> Supplier:
    return service.save_supplier(actor, body, context, supplier_id)
