"""Reception act (acta de recepción) as a PDF, generated on request with reportlab.

All user-provided text is XML-escaped before entering reportlab Paragraphs, which interpret
a small markup language.
"""

import io
from datetime import date, datetime
from decimal import Decimal
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.modules.organizations.models import Organization
from app.modules.workorders.catalog import (
    ACCESSORY_LABELS,
    PAYMENT_METHOD_LABELS,
    UNLOCK_LABELS,
    Accessory,
    PaymentMethod,
    UnlockMethod,
)
from app.modules.workorders.schemas import WorkOrderRead
from app.shared.context import BOGOTA

_styles = getSampleStyleSheet()
BODY = ParagraphStyle("body", parent=_styles["Normal"], fontSize=9, leading=12)
SMALL = ParagraphStyle("small", parent=BODY, fontSize=7.5, leading=10)
LABEL = ParagraphStyle("label", parent=BODY, fontName="Helvetica-Bold")
TITLE = ParagraphStyle("title", parent=_styles["Title"], fontSize=15, spaceAfter=2)
SECTION = ParagraphStyle(
    "section", parent=BODY, fontName="Helvetica-Bold", fontSize=10, spaceBefore=8, spaceAfter=3
)
CENTER = ParagraphStyle("center", parent=SMALL, alignment=TA_CENTER)


def money(value: Decimal) -> str:
    """Colombian pesos: $ 1.250.000 (no cents when they are zero)."""
    rounded = value.quantize(Decimal("0.01"))
    integer, _, cents = f"{rounded:,.2f}".partition(".")
    text = integer.replace(",", ".")
    return f"$ {text}" if cents == "00" else f"$ {text},{cents}"


def phone(value: str | None) -> str | None:
    """+573001234567 → 300 123 4567; other numbers unchanged."""
    if value and value.startswith("+57") and len(value) == 13:
        digits = value[3:]
        return f"{digits[:3]} {digits[3:6]} {digits[6:]}"
    return value


def _p(value: str | None, style: ParagraphStyle = BODY) -> Paragraph:
    text = escape(value or "—").replace("\n", "<br/>")
    return Paragraph(text, style)


def _date(value: date | None) -> str:
    return value.strftime("%d/%m/%Y") if value else "—"


def _datetime(value: datetime) -> str:
    return value.astimezone(BOGOTA).strftime("%d/%m/%Y %I:%M %p")


def _grid(rows: list[tuple[str, str | None]], widths: tuple[float, float]) -> Table:
    table = Table([[_p(label, LABEL), _p(value)] for label, value in rows], colWidths=list(widths))
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
                ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def build_reception_act(
    order: WorkOrderRead, organization: Organization, terms_content: str
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=f"Acta de recepción {order.number}",
        author=organization.legal_name or organization.name,
    )
    width = doc.width
    header_lines = [
        organization.legal_name or organization.name,
        f"NIT {organization.tax_id}" if organization.tax_id else None,
        " · ".join(v for v in (organization.address, organization.city) if v) or None,
        " · ".join(v for v in (phone(organization.phone), organization.email) if v) or None,
    ]
    story: list[object] = [
        Paragraph(escape(organization.name), TITLE),
        _p("\n".join(line for line in header_lines if line), CENTER),
        Spacer(1, 4 * mm),
        _grid(
            [
                ("Acta de recepción", order.number),
                ("Fecha de recepción", _datetime(order.received_at)),
                ("Sede", order.branch),
                ("Recibió", order.received_by.full_name if order.received_by else None),
            ],
            (width * 0.3, width * 0.7),
        ),
        Paragraph("Cliente", SECTION),
        _grid(
            [
                ("Nombre", order.customer.full_name),
                (
                    "Documento",
                    f"{order.customer.id_type} {order.customer.id_number}"
                    if order.customer.id_number
                    else None,
                ),
                ("Teléfono", phone(order.customer.phone)),
            ],
            (width * 0.3, width * 0.7),
        ),
        Paragraph("Equipo", SECTION),
        _grid(
            [
                ("Tipo", order.device.category),
                ("Marca y modelo", f"{order.device.manufacturer} {order.device.model}"),
                ("IMEI", order.device.imei),
                ("Serial", order.device.serial_number),
                ("Desbloqueo", UNLOCK_LABELS[UnlockMethod(order.unlock_method)]),
            ],
            (width * 0.3, width * 0.7),
        ),
        Paragraph("Recepción", SECTION),
        _grid(
            [
                ("Falla reportada", order.reported_issue),
                ("Estado físico", order.physical_condition),
                ("Accesorios", _accessories(order)),
                ("Observaciones", order.notes),
                ("Entrega estimada", _date(order.estimated_delivery_date)),
            ],
            (width * 0.3, width * 0.7),
        ),
        Paragraph("Valores", SECTION),
        _grid(
            [
                ("Valor del diagnóstico", money(order.diagnostic_fee)),
                ("Anticipo recibido", _advance(order)),
            ],
            (width * 0.3, width * 0.7),
        ),
        Paragraph(f"Condiciones del servicio (versión {order.terms_version})", SECTION),
        _p(terms_content.strip(), SMALL),
        Spacer(1, 4 * mm),
        _p(
            "El cliente declara que la información de esta acta es correcta y que recibió copia "
            "de las condiciones del servicio.",
            SMALL,
        ),
        Spacer(1, 14 * mm),
        KeepTogether([_signatures(width)]),
    ]
    doc.build(story)
    return buffer.getvalue()


def _accessories(order: WorkOrderRead) -> str:
    if not order.accessories:
        return "Ninguno"
    items = []
    for item in order.accessories:
        label = ACCESSORY_LABELS[Accessory(item.code)]
        items.append(f"{label}: {item.detail}" if item.detail else label)
    return ", ".join(items)


def _advance(order: WorkOrderRead) -> str:
    if order.advance_amount <= 0:
        return "Sin anticipo"
    method = (
        PAYMENT_METHOD_LABELS[PaymentMethod(order.advance_method)] if order.advance_method else ""
    )
    return f"{money(order.advance_amount)} ({method})"


def _signatures(width: float) -> Table:
    line = "_" * 38
    table = Table(
        [
            [_p(line, CENTER), _p(line, CENTER)],
            [_p("Firma del cliente", CENTER), _p("Firma de quien recibe", CENTER)],
            [_p("Nombre y documento:", SMALL), _p("Nombre:", SMALL)],
        ],
        colWidths=[width / 2, width / 2],
    )
    table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    return table
