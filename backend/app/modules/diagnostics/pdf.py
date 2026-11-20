"""Diagnostic report for the customer (PDF). Agent results are labelled as automatic and
untested items are shown as such: nothing is presented as checked when it was not."""

import io
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.modules.diagnostics.catalog import Result, Source
from app.modules.diagnostics.schemas import DiagnosticRead
from app.modules.organizations.models import Organization
from app.modules.workorders.pdf import BODY, CENTER, LABEL, SECTION, SMALL, TITLE, _grid, _p, phone
from app.modules.workorders.schemas import WorkOrderRead
from app.shared.context import BOGOTA

RESULT_LABELS: dict[Result, str] = {
    Result.OK: "Bien",
    Result.WARNING: "Advertencia",
    Result.FAIL: "Falla",
    Result.NOT_TESTED: "No probado",
    Result.NOT_SUPPORTED: "No soportado",
}
RESULT_COLORS: dict[Result, colors.Color] = {
    Result.OK: colors.HexColor("#1f7a4d"),
    Result.WARNING: colors.HexColor("#9a6700"),
    Result.FAIL: colors.HexColor("#b42318"),
    Result.NOT_TESTED: colors.grey,
    Result.NOT_SUPPORTED: colors.grey,
}


def build_diagnostic_report(
    order: WorkOrderRead, diagnostic: DiagnosticRead, organization: Organization
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=f"Diagnóstico {order.number}",
        author=organization.legal_name or organization.name,
    )
    width = doc.width
    header = [
        organization.legal_name or organization.name,
        f"NIT {organization.tax_id}" if organization.tax_id else None,
        " · ".join(v for v in (phone(organization.phone), organization.email) if v) or None,
    ]
    closed = (
        diagnostic.closed_at.astimezone(BOGOTA).strftime("%d/%m/%Y %I:%M %p")
        if diagnostic.closed_at
        else "En curso (no cerrado)"
    )
    story: list[object] = [
        Paragraph(escape(organization.name), TITLE),
        _p("\n".join(line for line in header if line), CENTER),
        Spacer(1, 4 * mm),
        _grid(
            [
                ("Informe de diagnóstico", order.number),
                ("Cliente", order.customer.full_name),
                ("Equipo", f"{order.device.manufacturer} {order.device.model}"),
                ("IMEI / Serial", order.device.imei or order.device.serial_number),
                ("Fecha del diagnóstico", closed),
                ("Técnico", diagnostic.closed_by.full_name if diagnostic.closed_by else None),
            ],
            (width * 0.3, width * 0.7),
        ),
        Paragraph("Falla reportada", SECTION),
        _p(order.reported_issue),
        Paragraph("Resultados", SECTION),
        _results_table(diagnostic, width),
    ]
    if diagnostic.agent_reported_at:
        story.append(Spacer(1, 2 * mm))
        story.append(
            _p(
                "Los resultados marcados como (automático) fueron recolectados por el agente de "
                f"diagnóstico ERMS {diagnostic.agent_version or ''} con autorización del cliente, "
                "en modo solo lectura"
                + (" con permisos de administrador." if diagnostic.agent_elevated else "."),
                SMALL,
            )
        )
    story += [
        Paragraph("Conclusión del técnico", SECTION),
        _p(diagnostic.conclusion),
        Paragraph("Reparación recomendada", SECTION),
        _p(diagnostic.recommendation),
        Spacer(1, 6 * mm),
        _p(
            "Este informe describe el estado del equipo al momento del diagnóstico. Los valores de "
            "la reparación se informan por separado en la cotización.",
            SMALL,
        ),
    ]
    doc.build(story)
    return buffer.getvalue()


def _results_table(diagnostic: DiagnosticRead, width: float) -> Table:
    rows: list[list[object]] = [
        [Paragraph("Prueba", LABEL), Paragraph("Resultado", LABEL), Paragraph("Detalle", LABEL)]
    ]
    styles: list[tuple[object, ...]] = []
    for index, item in enumerate(diagnostic.results, start=1):
        result = item.result or Result.NOT_TESTED
        name = item.name + (" (automático)" if item.source is Source.AGENT else "")
        rows.append(
            [
                _p(name, BODY),
                _p(RESULT_LABELS[result], BODY),
                _p(item.observation or "", SMALL),
            ]
        )
        styles.append(("TEXTCOLOR", (1, index), (1, index), RESULT_COLORS[result]))
    table = Table(rows, colWidths=[width * 0.3, width * 0.17, width * 0.53], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                *styles,
            ]
        )
    )
    return table
