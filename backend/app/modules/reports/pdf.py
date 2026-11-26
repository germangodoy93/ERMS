"""Tabular report as a landscape PDF."""

import io
from decimal import Decimal, InvalidOperation
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER, landscape
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.modules.organizations.models import Organization
from app.modules.reports.schemas import Report
from app.modules.workorders.pdf import CENTER, LABEL, SECTION, SMALL, TITLE, _grid, _p
from app.shared.context import BOGOTA, utcnow
from app.shared.money import format_money


def money_label(value: object) -> str:
    try:
        return format_money(Decimal(str(value)))
    except InvalidOperation:
        return str(value)


def build_report(organization: Organization, report: Report) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(LETTER),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=f"{report.title} {report.date_from} a {report.date_to}",
    )
    width = doc.width
    rows: list[list[object]] = [[Paragraph(escape(c), LABEL) for c in report.columns]]
    money = set(report.money_columns)
    rows += [
        [_p(money_label(v) if i in money else str(v), SMALL) for i, v in enumerate(row)]
        for row in report.rows
    ]
    if len(rows) == 1:
        rows.append([_p("Sin datos en el periodo.", SMALL)] + [""] * (len(report.columns) - 1))
    table = Table(rows, colWidths=[width / len(report.columns)] * len(report.columns), repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
            ]
        )
    )
    generated = utcnow().astimezone(BOGOTA).strftime("%d/%m/%Y %I:%M %p")
    story: list[object] = [
        Paragraph(escape(f"{report.title} · {organization.name}"), TITLE),
        _p(f"Del {report.date_from} al {report.date_to} · generado el {generated}", CENTER),
        Spacer(1, 4 * mm),
        table,
        Paragraph("Resumen", SECTION),
        _grid(list(report.summary), (width * 0.4, width * 0.6)),
    ]
    doc.build(story)
    return buffer.getvalue()
