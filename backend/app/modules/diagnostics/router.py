import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.exceptions import AuthenticationError
from app.core.storage import Storage, get_storage
from app.modules.auth.dependencies import AppSettings, DbSession, require_permissions
from app.modules.diagnostics.agent_schemas import (
    AgentReport,
    PairRequest,
    PairResponse,
    ReportAccepted,
)
from app.modules.diagnostics.pdf import build_diagnostic_report
from app.modules.diagnostics.schemas import (
    CloseRequest,
    DiagnosticRead,
    PairingCreated,
    ResultsUpdate,
)
from app.modules.diagnostics.service import DiagnosticService
from app.modules.organizations.models import Organization
from app.modules.roles.catalog import Perm
from app.modules.users.models import User
from app.modules.workorders.service import WorkOrderService
from app.shared.context import RequestContext, get_request_context

router = APIRouter(prefix="/work-orders/{order_id}", tags=["diagnostics"])
agent_router = APIRouter(prefix="/diagnostics/agent", tags=["diagnostic-agent"])

Reader = Annotated[User, Depends(require_permissions(Perm.WORK_ORDERS_READ))]
Technician = Annotated[User, Depends(require_permissions(Perm.WORK_ORDERS_PROGRESS))]
Context = Annotated[RequestContext, Depends(get_request_context)]
_agent_bearer = HTTPBearer(auto_error=False, description="Token entregado por /pair")


def get_diagnostic_service(session: DbSession, settings: AppSettings) -> DiagnosticService:
    return DiagnosticService(session, settings)


Service = Annotated[DiagnosticService, Depends(get_diagnostic_service)]


@router.get("/diagnostic", response_model=DiagnosticRead, summary="Diagnóstico de la orden")
def get_diagnostic(order_id: uuid.UUID, actor: Reader, service: Service) -> DiagnosticRead:
    return service.view(actor, order_id)


@router.put(
    "/diagnostic/results", response_model=DiagnosticRead, summary="Registrar resultados manuales"
)
def save_results(
    order_id: uuid.UUID, body: ResultsUpdate, actor: Technician, service: Service, context: Context
) -> DiagnosticRead:
    return service.save_results(actor, order_id, body.results, context)


@router.post("/diagnostic/close", response_model=DiagnosticRead, summary="Cerrar el diagnóstico")
def close_diagnostic(
    order_id: uuid.UUID, body: CloseRequest, actor: Technician, service: Service, context: Context
) -> DiagnosticRead:
    return service.close(actor, order_id, body.conclusion, body.recommendation, context)


@router.post("/diagnostic/reopen", response_model=DiagnosticRead, summary="Reabrir el diagnóstico")
def reopen_diagnostic(
    order_id: uuid.UUID, actor: Technician, service: Service, context: Context
) -> DiagnosticRead:
    return service.reopen(actor, order_id, context)


@router.post(
    "/diagnostic/agent-pairing",
    response_model=PairingCreated,
    status_code=status.HTTP_201_CREATED,
    summary="Generar código de un solo uso para el agente",
)
def create_pairing(
    order_id: uuid.UUID, actor: Technician, service: Service, context: Context
) -> PairingCreated:
    return service.create_pairing(actor, order_id, context)


@router.get(
    "/diagnostic-report.pdf",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}}},
    summary="Informe de diagnóstico en PDF",
)
def diagnostic_report(
    order_id: uuid.UUID,
    actor: Reader,
    service: Service,
    session: DbSession,
    settings: AppSettings,
    storage: Annotated[Storage, Depends(get_storage)],
) -> Response:
    diagnostic = service.view(actor, order_id)
    order = WorkOrderService(session, settings, storage).read(actor, order_id)
    organization = session.get(Organization, actor.organization_id)
    assert organization is not None  # noqa: S101 - FK guarantees it
    pdf = build_diagnostic_report(order, diagnostic, organization)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="diagnostico-{order.number}.pdf"',
            "Cache-Control": "no-store",
        },
    )


# --- Agent endpoints (no user session) ---------------------------------------------------


@agent_router.post("/pair", response_model=PairResponse, summary="Canjear el código del técnico")
def agent_pair(body: PairRequest, service: Service, context: Context) -> PairResponse:
    return service.agent_pair(body.code, context)


@agent_router.post(
    "/report", response_model=ReportAccepted, summary="Enviar los datos recolectados (una vez)"
)
def agent_report(
    body: AgentReport,
    service: Service,
    context: Context,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_agent_bearer)],
) -> ReportAccepted:
    if credentials is None:
        raise AuthenticationError("Falta el token del agente.")
    return ReportAccepted(results=service.agent_report(credentials.credentials, body, context))
