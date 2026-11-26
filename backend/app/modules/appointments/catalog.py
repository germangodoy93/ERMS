"""Appointments outside the workshop (remote and on-site): catalogs and defaults (PM-04, R1)."""

from enum import StrEnum


class Modality(StrEnum):
    REMOTE = "REMOTE"
    ON_SITE = "ON_SITE"


MODALITY_LABELS: dict[Modality, str] = {
    Modality.REMOTE: "Remota",
    Modality.ON_SITE: "En sitio",
}


class AppointmentStatus(StrEnum):
    SCHEDULED = "SCHEDULED"
    CANCELLED = "CANCELLED"


STATUS_LABELS: dict[AppointmentStatus, str] = {
    AppointmentStatus.SCHEDULED: "Agendada",
    AppointmentStatus.CANCELLED: "Cancelada",
}


class ConsentChannel(StrEnum):
    SCREEN = "SCREEN"
    PAPER = "PAPER"
    VERBAL = "VERBAL"


# Localities of Bogotá (Acuerdo 2 de 1992 and Acuerdo 117 de 2003), plus municipalities nearby.
LOCALITIES: tuple[str, ...] = (
    "Usaquén",
    "Chapinero",
    "Santa Fe",
    "San Cristóbal",
    "Usme",
    "Tunjuelito",
    "Bosa",
    "Kennedy",
    "Fontibón",
    "Engativá",
    "Suba",
    "Barrios Unidos",
    "Teusaquillo",
    "Los Mártires",
    "Antonio Nariño",
    "Puente Aranda",
    "La Candelaria",
    "Rafael Uribe Uribe",
    "Ciudad Bolívar",
    "Sumapaz",
    "Otro municipio",
)

WEEKDAY_LABELS = ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo")

# Service hours for remote and on-site attention, independent of the workshop's opening
# hours. Key: weekday (0 = Monday); value: ("HH:MM", "HH:MM") or None when there is no service.
DEFAULT_HOURS: dict[int, tuple[str, str] | None] = {
    0: ("08:00", "18:00"),
    1: ("08:00", "18:00"),
    2: ("08:00", "18:00"),
    3: ("08:00", "18:00"),
    4: ("08:00", "18:00"),
    5: ("08:00", "12:00"),
    6: None,
}

# Services every workshop starts with; prices are set by the workshop (never invented).
DEFAULT_SERVICES: tuple[dict[str, object], ...] = (
    {
        "name": "Visita técnica",
        "modality": Modality.ON_SITE,
        "duration_minutes": 60,
        "description": (
            "El técnico va al sitio, hace el diagnóstico y sigue el proceso normal de la orden "
            "(cotización, autorización, reparación y entrega)."
        ),
    },
)

REMOTE_ACCESS_TEXT = (
    "El cliente autoriza al técnico del taller a conectarse a su equipo de forma remota "
    "(Asistencia rápida de Windows u otra herramienta que el cliente inicia) para el servicio "
    "agendado. La sesión la abre y la puede cerrar el cliente en cualquier momento; el código "
    "de conexión no se guarda en ERMS. El técnico no abrirá documentos, fotos ni cuentas "
    "personales que no sean necesarios para el servicio, y no hará cambios irreversibles "
    "(formateos, borrados, firmware) sin una confirmación expresa del cliente en ese momento."
)

MIN_DURATION = 15
MAX_DURATION = 480
MAX_RANGE_DAYS = 62
