"""Quotation for the customer (PDF) with per-item IVA."""

import io
from decimal import Decimal
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.modules.organizations.models import Organization
from app.modules.quotes.schemas import QuoteRead
from app.modules.workorders.pdf import (
    BODY,
    CENTER,
    LABEL,
    SECTION,
    SMALL,
    TITLE,
    _grid,
    _p,
    money,
    phone,
)
from app.modules.workorders.schemas import WorkOrderRead


def _qty(value: Decimal) -> str:
    return f"{value.normalize():f}".replace(".", ",")


def build_quote(organization: Organization, order: WorkOrderRead, quote: QuoteRead) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=f"Cotización {order.number} v{quote.version}",
    )
    width = doc.width
    header = [
        organization.legal_name or organization.name,
        f"NIT {organization.tax_id}" if organization.tax_id else None,
        " · ".join(v for v in (organization.address, organization.city) if v) or None,
        " · ".join(v for v in (phone(organization.phone), organization.email) if v) or None,
    ]
    rows: list[list[object]] = [
        [
            Paragraph(t, LABEL)
            for t in ("Descripción", "Cant.", "Valor unit.", "Desc.", "IVA", "Total")
        ]
    ]
    for item in quote.items:
        rows.append(
            [
                _p(item.description, BODY),
                _p(_qty(item.quantity), BODY),
                _p(
                    money(item.unit_price) + (" (IVA incl.)" if item.price_includes_tax else ""),
                    SMALL,
                ),
                _p(
                    f"{item.discount_percent.normalize():f} %" if item.discount_percent else "—",
                    BODY,
                ),
                _p(f"{item.tax_rate} %" if item.tax_rate else "No aplica", SMALL),
                _p(money(item.total_amount), BODY),
            ]
        )
    items = Table(
        rows,
        colWidths=[width * w for w in (0.38, 0.08, 0.16, 0.09, 0.11, 0.18)],
        repeatRows=1,
    )
    items.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
            ]
        )
    )
    story: list[object] = [
        Paragraph(escape(organization.name), TITLE),
        _p("\n".join(line for line in header if line), CENTER),
        Spacer(1, 4 * mm),
        _grid(
            [
                ("Cotización", f"{order.number} · versión {quote.version}"),
                ("Cliente", order.customer.full_name),
                ("Equipo", f"{order.device.manufacturer} {order.device.model}"),
                (
                    "Válida hasta",
                    quote.valid_until.strftime("%d/%m/%Y") if quote.valid_until else None,
                ),
            ],
            (width * 0.3, width * 0.7),
        ),
        Paragraph("Detalle", SECTION),
        items,
        Spacer(1, 3 * mm),
        _grid(
            [
                ("Subtotal (sin IVA)", money(quote.subtotal)),
                ("Descuentos", money(quote.discount_total)),
                ("IVA", money(quote.tax_total)),
                ("Total", money(quote.total)),
            ],
            (width * 0.7, width * 0.3),
        ),
        Spacer(1, 3 * mm),
        _p(
            f"El valor del diagnóstico ({money(order.diagnostic_fee)}) está incluido en este total "
            "si el cliente aprueba la reparación. Si la rechaza, se cobra solo el diagnóstico.",
            SMALL,
        ),
    ]
    if quote.notes:
        story += [Paragraph("Observaciones", SECTION), _p(quote.notes)]
    story += [Spacer(1, 12 * mm), _p("Aprobación del cliente: ____________________________", BODY)]
    doc.build(story)
    return buffer.getvalue()
