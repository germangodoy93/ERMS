from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response

from app.modules.auth.dependencies import DbSession, require_permissions
from app.modules.organizations.models import Organization
from app.modules.reports.pdf import build_report
from app.modules.reports.schemas import Dashboard, Report
from app.modules.reports.service import ReportService, to_csv
from app.modules.roles.catalog import Perm
from app.modules.users.models import User

router = APIRouter(tags=["reports"])

Reader = Annotated[User, Depends(require_permissions(Perm.WORK_ORDERS_READ))]
Analyst = Annotated[User, Depends(require_permissions(Perm.REPORTS_READ))]
Kind = Literal["income", "orders", "inventory", "technicians"]


@router.get("/dashboard", response_model=Dashboard, summary="Indicadores del taller")
def dashboard(actor: Reader, session: DbSession) -> Dashboard:
    return ReportService(session).dashboard(actor)


@router.get(
    "/reports/{kind}",
    response_model=Report,
    responses={200: {"content": {"text/csv": {}, "application/pdf": {}}}},
    summary="Reporte por periodo (json, csv o pdf)",
)
def report(
    kind: Kind,
    actor: Analyst,
    session: DbSession,
    date_from: Annotated[date, Query(alias="from")],
    date_to: Annotated[date, Query(alias="to")],
    format: Annotated[Literal["json", "csv", "pdf"], Query()] = "json",  # noqa: A002
) -> Report | Response:
    data = ReportService(session).report(actor, kind, date_from, date_to)
    if format == "json":
        return data
    name = f"{kind}-{date_from}-{date_to}"
    if format == "csv":
        return Response(
            content=to_csv(data),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{name}.csv"'},
        )
    organization = session.get(Organization, actor.organization_id)
    assert organization is not None  # noqa: S101 - FK guarantees it
    return Response(
        content=build_report(organization, data),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{name}.pdf"'},
    )
