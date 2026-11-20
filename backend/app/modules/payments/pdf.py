"""Payment receipt (comprobante de pago). It is NOT an electronic invoice (DIAN)."""

import io
from decimal import Decimal
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from app.modules.organizations.models import Organization
from app.modules.payments.schemas import PaymentRead
from app.modules.payments.service import Billing
from app.modules.workorders.catalog import PAYMENT_METHOD_LABELS
from app.modules.workorders.pdf import CENTER, SECTION, SMALL, TITLE, _grid, _p, money, phone
from app.modules.workorders.schemas import WorkOrderRead
from app.shared.context import BOGOTA


def build_receipt(
    organization: Organization, order: WorkOrderRead, payment: PaymentRead, billing: Billing
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=f"Comprobante {payment.receipt_number or ''}",
    )
    width = doc.width
    header = [
        organization.legal_name or organization.name,
        f"NIT {organization.tax_id}" if organization.tax_id else None,
        " · ".join(v for v in (organization.address, organization.city) if v) or None,
        " · ".join(v for v in (phone(organization.phone), organization.email) if v) or None,
    ]
    story: list[object] = [
        Paragraph(escape(organization.name), TITLE),
        _p("\n".join(line for line in header if line), CENTER),
        Spacer(1, 4 * mm),
        _grid(
            [
                ("Comprobante de pago", payment.receipt_number or "Anticipo de recepción"),
                ("Fecha", payment.paid_at.astimezone(BOGOTA).strftime("%d/%m/%Y %I:%M %p")),
                ("Orden de servicio", order.number),
                ("Cliente", order.customer.full_name),
                ("Equipo", f"{order.device.manufacturer} {order.device.model}"),
            ],
            (width * 0.35, width * 0.65),
        ),
        Paragraph("Pago recibido", SECTION),
        _grid(
            [
                ("Valor", money(payment.amount)),
                ("Medio de pago", PAYMENT_METHOD_LABELS[payment.method]),
                ("Referencia", payment.reference),
                ("Recibió", payment.received_by.full_name if payment.received_by else None),
            ],
            (width * 0.35, width * 0.65),
        ),
        Paragraph("Estado de cuenta de la orden", SECTION),
        _grid(
            [
                ("Valor del servicio", money(billing.amount_due)),
                ("Total pagado", money(billing.paid)),
                ("Saldo pendiente", money(max(billing.balance, Decimal(0)))),
            ],
            (width * 0.35, width * 0.65),
        ),
        Spacer(1, 6 * mm),
        _p(
            "Este documento es un comprobante de pago interno y no reemplaza la factura "
            "electrónica de venta.",
            SMALL,
        ),
    ]
    doc.build(story)
    return buffer.getvalue()
