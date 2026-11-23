import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response, UploadFile, status

from app.core.exceptions import BusinessRuleError
from app.core.storage import Storage, get_storage
from app.modules.assembly.schemas import (
    AssemblyChecklist,
    BuildRead,
    BuildSummary,
    BuildWrite,
    CatalogImport,
    CatalogImportResult,
    CatalogPart,
    CostUpdateResult,
    EvaluateRequest,
    EvaluationOut,
    OrderRequest,
)
from app.modules.assembly.service import AssemblyService
from app.modules.auth.dependencies import AppSettings, DbSession, require_permissions
from app.modules.roles.catalog import Perm
from app.modules.users.models import User
from app.modules.workorders.schemas import WorkOrderRead
from app.shared.context import RequestContext, get_request_context

router = APIRouter(prefix="/assembly", tags=["assembly"])
order_router = APIRouter(prefix="/work-orders/{order_id}/assembly", tags=["assembly"])

Assembler = Annotated[User, Depends(require_permissions(Perm.ASSEMBLY_MANAGE))]
Importer = Annotated[
    User, Depends(require_permissions(Perm.ASSEMBLY_MANAGE, Perm.INVENTORY_MANAGE))
]
Reader = Annotated[User, Depends(require_permissions(Perm.WORK_ORDERS_READ))]
Context = Annotated[RequestContext, Depends(get_request_context)]


def get_assembly_service(
    session: DbSession, settings: AppSettings, storage: Annotated[Storage, Depends(get_storage)]
) -> AssemblyService:
    return AssemblyService(session, settings, storage)


Service = Annotated[AssemblyService, Depends(get_assembly_service)]


@router.get("/catalog", response_model=list[CatalogPart], summary="Piezas para ensamble")
def catalog(actor: Assembler, service: Service) -> list[CatalogPart]:
    return service.catalog(actor)


@router.post(
    "/catalog/import",
    response_model=CatalogImportResult,
    summary="Importar o actualizar el catálogo de piezas (por código)",
)
def import_catalog(
    body: CatalogImport, actor: Importer, service: Service, context: Context
) -> CatalogImportResult:
    return service.import_catalog(actor, body, context)


MAX_COST_FILE = 2 * 1024 * 1024


@router.get(
    "/catalog/costs.csv",
    response_class=Response,
    summary="Plantilla de costos para Excel (código, nombre, costo, precio de venta)",
)
def cost_template(actor: Importer, service: Service) -> Response:
    return Response(
        content=service.cost_template(actor),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="costos-ensamble.csv"'},
    )


@router.post(
    "/catalog/costs",
    response_model=CostUpdateResult,
    summary="Actualizar costos desde la plantilla guardada en Excel (CSV)",
)
async def update_costs(
    actor: Importer,
    service: Service,
    context: Context,
    file: UploadFile,
) -> CostUpdateResult:
    content = await file.read(MAX_COST_FILE + 1)
    if len(content) > MAX_COST_FILE:
        raise BusinessRuleError("El archivo supera 2 MB.")
    return service.update_costs(actor, content, context)


@router.post(
    "/evaluate", response_model=EvaluationOut, summary="Compatibilidad, consumo y rendimiento"
)
def evaluate(body: EvaluateRequest, actor: Assembler, service: Service) -> EvaluationOut:
    return service.evaluate(actor, body)


@router.get("/builds", response_model=list[BuildSummary], summary="Configuraciones guardadas")
def builds(actor: Assembler, service: Service) -> list[BuildSummary]:
    return service.builds(actor)


@router.post(
    "/builds",
    response_model=BuildRead,
    status_code=status.HTTP_201_CREATED,
    summary="Guardar una configuración",
)
def create_build(
    body: BuildWrite, actor: Assembler, service: Service, context: Context
) -> BuildRead:
    return service.save(actor, body, context)


@router.get("/builds/{build_id}", response_model=BuildRead, summary="Configuración")
def get_build(build_id: uuid.UUID, actor: Assembler, service: Service) -> BuildRead:
    return service.read(actor, build_id)


@router.put("/builds/{build_id}", response_model=BuildRead, summary="Actualizar configuración")
def update_build(
    build_id: uuid.UUID, body: BuildWrite, actor: Assembler, service: Service, context: Context
) -> BuildRead:
    return service.save(actor, body, context, build_id)


@router.delete(
    "/builds/{build_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Borrar borrador"
)
def delete_build(
    build_id: uuid.UUID, actor: Assembler, service: Service, context: Context
) -> Response:
    service.delete(actor, build_id, context)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/builds/{build_id}/order",
    response_model=WorkOrderRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear la orden de ensamble con su cotización",
)
def create_order(
    build_id: uuid.UUID, body: OrderRequest, actor: Assembler, service: Service, context: Context
) -> WorkOrderRead:
    return service.create_order(actor, build_id, body.customer_id, context)


@order_router.get("", response_model=AssemblyChecklist, summary="Lista de chequeo del ensamble")
def checklist(order_id: uuid.UUID, actor: Reader, service: Service) -> AssemblyChecklist:
    return service.checklist(actor, order_id)


@order_router.post(
    "/consume", response_model=AssemblyChecklist, summary="Descontar todas las piezas"
)
def consume(
    order_id: uuid.UUID, actor: Reader, service: Service, context: Context
) -> AssemblyChecklist:
    return service.consume_parts(actor, order_id, context)


@order_router.post(
    "/steps/{code}", response_model=AssemblyChecklist, summary="Marcar un paso como hecho"
)
def complete_step(
    order_id: uuid.UUID, code: str, actor: Reader, service: Service, context: Context
) -> AssemblyChecklist:
    return service.complete_step(actor, order_id, code, context)
