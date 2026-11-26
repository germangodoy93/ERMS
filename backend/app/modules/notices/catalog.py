"""Customer notices by WhatsApp (post-MVP sprint 3, phase A).

ERMS prepares the message and a `wa.me` link; the advisor sends it from the workshop's
WhatsApp Business. Only service notices: never advertising (it would need another consent
under Ley 1581).
"""

from enum import StrEnum
from string import Formatter

from app.modules.workorders.catalog import Status

#: Days a ready device can wait before the "not picked up" reminder (owner's decision).
REMINDER_DAYS = 7
MAX_BODY = 1500


class NoticeKind(StrEnum):
    RECEIVED = "RECEIVED"
    QUOTE_READY = "QUOTE_READY"
    READY = "READY"
    NOT_REPAIRED = "NOT_REPAIRED"
    REMINDER = "REMINDER"
    DELIVERED = "DELIVERED"
    FREE = "FREE"


NOTICE_LABELS: dict[NoticeKind, str] = {
    NoticeKind.RECEIVED: "Orden recibida",
    NoticeKind.QUOTE_READY: "Cotización lista",
    NoticeKind.READY: "Equipo listo",
    NoticeKind.NOT_REPAIRED: "No reparado o cancelado",
    NoticeKind.REMINDER: "Recordatorio: equipo sin retirar",
    NoticeKind.DELIVERED: "Entregado y garantía",
    NoticeKind.FREE: "Mensaje libre",
}

#: States in which a pending notice is shown on the dashboard ("Por avisar"). Reception and
#: delivery happen with the customer present, so they are suggested but never pending.
NOT_REPAIRED_STATES = frozenset(
    {Status.NO_REPARABLE, Status.CANCELADO, Status.COTIZACION_RECHAZADA}
)
PENDING_KINDS = frozenset(
    {NoticeKind.QUOTE_READY, NoticeKind.READY, NoticeKind.NOT_REPAIRED, NoticeKind.REMINDER}
)
#: A READY / NOT_REPAIRED / REMINDER notice counts as "the customer knows it is ready".
PICKUP_KINDS = frozenset({NoticeKind.READY, NoticeKind.NOT_REPAIRED, NoticeKind.REMINDER})

PLACEHOLDERS: dict[str, str] = {
    "cliente": "Nombre del cliente (solo el primer nombre si es persona)",
    "orden": "Número de la orden",
    "equipo": "Marca y modelo del equipo",
    "taller": "Nombre del taller",
    "telefono_taller": "Teléfono del taller",
    "direccion_taller": "Dirección y ciudad del taller",
    "falla": "Conclusión del diagnóstico (o la falla reportada)",
    "total": "Valor de la cotización",
    "saldo": "Saldo pendiente",
    "diagnostico": "Valor del diagnóstico",
    "fecha_estimada": "Fecha estimada de entrega",
    "motivo": "Motivo de no reparar o cancelar",
    "dias_listo": "Días que lleva el equipo listo",
    "garantia_dias": "Días de garantía",
    "garantia_hasta": "Fecha final de la garantía",
}

DEFAULT_TEMPLATES: dict[NoticeKind, str] = {
    NoticeKind.RECEIVED: (
        "Hola {cliente}, le saluda {taller}. Recibimos su {equipo} con la orden {orden}. "
        "Le avisaremos por este medio cuando tengamos el diagnóstico."
    ),
    NoticeKind.QUOTE_READY: (
        "Hola {cliente}, ya revisamos su {equipo} (orden {orden}).\n"
        "Diagnóstico: {falla}\n"
        "Valor de la reparación: {total}\n"
        "Fecha estimada de entrega: {fecha_estimada}\n"
        "¿Autoriza la reparación? Responda SÍ para continuar o NO si prefiere retirarlo."
    ),
    NoticeKind.READY: (
        "Hola {cliente}, su {equipo} (orden {orden}) ya está reparado y listo para "
        "entrega. Saldo pendiente: {saldo}. Lo esperamos en {direccion_taller}. {taller}"
    ),
    NoticeKind.NOT_REPAIRED: (
        "Hola {cliente}, sobre su {equipo} (orden {orden}): {motivo}. Puede pasar a "
        "retirarlo en {direccion_taller}. Valor a pagar: {saldo}. {taller}"
    ),
    NoticeKind.REMINDER: (
        "Hola {cliente}, le recordamos que su {equipo} (orden {orden}) está listo para "
        "retirar desde hace {dias_listo} días. Saldo pendiente: {saldo}. Lo esperamos en "
        "{direccion_taller}. {taller}"
    ),
    NoticeKind.DELIVERED: (
        "Hola {cliente}, gracias por confiar en {taller}. Su {equipo} (orden {orden}) "
        "tiene garantía de {garantia_dias} días, hasta el {garantia_hasta}. Si tiene "
        "alguna novedad, escríbanos por este medio."
    ),
    NoticeKind.FREE: (
        "Hola {cliente}, le escribimos de {taller} sobre su {equipo} (orden {orden}). "
    ),
}


def template_errors(body: str) -> list[str]:
    """Problems of a template written by the administrator (empty list = valid)."""
    try:
        fields = [parsed for parsed in Formatter().parse(body) if parsed[1] is not None]
    except ValueError:
        return ["Revise las llaves { }: cada campo se escribe así: {cliente}."]
    errors: list[str] = []
    for _, name, spec, conversion in fields:
        if name not in PLACEHOLDERS:
            errors.append(f"El campo {{{name}}} no existe.")
        elif spec or conversion:
            errors.append(f"Escriba el campo sin formato adicional: {{{name}}}.")
    return errors


def render(body: str, values: dict[str, str]) -> str:
    """Fills a validated template. Values are plain strings, never formatted again."""
    return body.format_map(values)
