"""Work order states, allowed transitions and reception catalogs (docs/ERMS-ERD.md)."""

from enum import StrEnum

from app.modules.roles.catalog import Perm


class Status(StrEnum):
    RECIBIDO = "RECIBIDO"
    INSPECCION = "INSPECCION"
    DIAGNOSTICO = "DIAGNOSTICO"
    COTIZACION = "COTIZACION"
    PENDIENTE_AUTORIZACION = "PENDIENTE_AUTORIZACION"
    APROBADO = "APROBADO"
    COTIZACION_RECHAZADA = "COTIZACION_RECHAZADA"
    EN_REPARACION = "EN_REPARACION"
    CONTROL_CALIDAD = "CONTROL_CALIDAD"
    LISTO_ENTREGA = "LISTO_ENTREGA"
    ENTREGADO = "ENTREGADO"
    CANCELADO = "CANCELADO"
    NO_REPARABLE = "NO_REPARABLE"


S = Status
TRANSITIONS: dict[Status, frozenset[Status]] = {
    S.RECIBIDO: frozenset({S.INSPECCION, S.CANCELADO}),
    S.INSPECCION: frozenset({S.DIAGNOSTICO, S.NO_REPARABLE, S.CANCELADO}),
    S.DIAGNOSTICO: frozenset({S.COTIZACION, S.NO_REPARABLE, S.CANCELADO}),
    S.COTIZACION: frozenset({S.PENDIENTE_AUTORIZACION, S.CANCELADO}),
    S.PENDIENTE_AUTORIZACION: frozenset({S.APROBADO, S.COTIZACION_RECHAZADA, S.CANCELADO}),
    S.APROBADO: frozenset({S.EN_REPARACION, S.CANCELADO}),
    S.EN_REPARACION: frozenset({S.CONTROL_CALIDAD, S.NO_REPARABLE}),
    # Quality control can send the device back to repair.
    S.CONTROL_CALIDAD: frozenset({S.LISTO_ENTREGA, S.EN_REPARACION}),
    # The device is always returned, repaired or not.
    S.COTIZACION_RECHAZADA: frozenset({S.LISTO_ENTREGA}),
    S.NO_REPARABLE: frozenset({S.LISTO_ENTREGA}),
    S.CANCELADO: frozenset({S.LISTO_ENTREGA}),
    S.LISTO_ENTREGA: frozenset({S.ENTREGADO}),
    S.ENTREGADO: frozenset(),
}


def targets(kind: str, source: Status) -> frozenset[Status]:
    """Allowed next states. An assembly order has no device to inspect or diagnose: it goes
    from reception straight to the quotation of the configured PC."""
    if kind == "ASSEMBLY" and source is S.RECIBIDO:
        return frozenset({S.COTIZACION, S.CANCELADO})
    return TRANSITIONS[source]


# Workshop steps are done by technicians; customer-facing steps by reception.
# Holding ANY of the listed permissions allows entering the state.
REQUIRED_PERMISSIONS: dict[Status, frozenset[Perm]] = {
    S.INSPECCION: frozenset({Perm.WORK_ORDERS_PROGRESS}),
    S.DIAGNOSTICO: frozenset({Perm.WORK_ORDERS_PROGRESS}),
    S.COTIZACION: frozenset({Perm.WORK_ORDERS_PROGRESS}),
    S.EN_REPARACION: frozenset({Perm.WORK_ORDERS_PROGRESS}),
    S.CONTROL_CALIDAD: frozenset({Perm.WORK_ORDERS_PROGRESS}),
    S.NO_REPARABLE: frozenset({Perm.WORK_ORDERS_PROGRESS}),
    S.LISTO_ENTREGA: frozenset({Perm.WORK_ORDERS_PROGRESS, Perm.WORK_ORDERS_DELIVER}),
    S.PENDIENTE_AUTORIZACION: frozenset({Perm.WORK_ORDERS_DELIVER}),
    S.APROBADO: frozenset({Perm.WORK_ORDERS_DELIVER}),
    S.COTIZACION_RECHAZADA: frozenset({Perm.WORK_ORDERS_DELIVER}),
    S.CANCELADO: frozenset({Perm.WORK_ORDERS_DELIVER}),
    S.ENTREGADO: frozenset({Perm.WORK_ORDERS_DELIVER}),
}

# Entering these states requires a written reason.
REASON_REQUIRED: frozenset[Status] = frozenset(
    {S.CANCELADO, S.NO_REPARABLE, S.COTIZACION_RECHAZADA}
)

CLOSED: frozenset[Status] = frozenset({S.ENTREGADO})


def reason_required(source: Status, target: Status) -> bool:
    # Sending a device back from quality control must explain what failed.
    return target in REASON_REQUIRED or (source is S.CONTROL_CALIDAD and target is S.EN_REPARACION)


class Priority(StrEnum):
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


class UnlockMethod(StrEnum):
    """ERMS never stores unlock passwords or patterns (project rule)."""

    NOT_REQUIRED = "NOT_REQUIRED"
    CUSTOMER_IN_PERSON = "CUSTOMER_IN_PERSON"  # given in person to the technician
    CUSTOMER_UNLOCKS = "CUSTOMER_UNLOCKS"  # the customer unlocks it when needed


class Accessory(StrEnum):
    CHARGER = "CHARGER"
    CABLE = "CABLE"
    CASE = "CASE"
    BATTERY = "BATTERY"
    SIM = "SIM"
    SD_CARD = "SD_CARD"
    CONTROLLER = "CONTROLLER"
    BOX = "BOX"
    OTHER = "OTHER"  # requires a description


ACCESSORY_LABELS: dict[Accessory, str] = {
    Accessory.CHARGER: "Cargador",
    Accessory.CABLE: "Cable",
    Accessory.CASE: "Funda o estuche",
    Accessory.BATTERY: "Batería",
    Accessory.SIM: "Tarjeta SIM",
    Accessory.SD_CARD: "Memoria SD",
    Accessory.CONTROLLER: "Control",
    Accessory.BOX: "Caja",
    Accessory.OTHER: "Otro",
}


class PaymentMethod(StrEnum):
    CASH = "CASH"
    TRANSFER = "TRANSFER"
    CARD = "CARD"
    NEQUI = "NEQUI"
    DAVIPLATA = "DAVIPLATA"


PAYMENT_METHOD_LABELS: dict[PaymentMethod, str] = {
    PaymentMethod.CASH: "Efectivo",
    PaymentMethod.TRANSFER: "Transferencia",
    PaymentMethod.CARD: "Tarjeta",
    PaymentMethod.NEQUI: "Nequi",
    PaymentMethod.DAVIPLATA: "Daviplata",
}

STATUS_LABELS: dict[Status, str] = {
    S.RECIBIDO: "Recibido",
    S.INSPECCION: "Inspección",
    S.DIAGNOSTICO: "Diagnóstico",
    S.COTIZACION: "Cotización",
    S.PENDIENTE_AUTORIZACION: "Pendiente de autorización",
    S.APROBADO: "Aprobado",
    S.COTIZACION_RECHAZADA: "Cotización rechazada",
    S.EN_REPARACION: "En reparación",
    S.CONTROL_CALIDAD: "Control de calidad",
    S.LISTO_ENTREGA: "Listo para entrega",
    S.ENTREGADO: "Entregado",
    S.CANCELADO: "Cancelado",
    S.NO_REPARABLE: "No reparable",
}

UNLOCK_LABELS: dict[UnlockMethod, str] = {
    UnlockMethod.NOT_REQUIRED: "No requiere desbloqueo",
    UnlockMethod.CUSTOMER_IN_PERSON: "El cliente dará el código en persona al técnico",
    UnlockMethod.CUSTOMER_UNLOCKS: "El cliente desbloqueará el equipo cuando se requiera",
}
