"""Diagnostic test catalog (fixed, in code) and agent evaluation thresholds.

Manual tests are recorded by the technician. Agent tests are filled ONLY from data the
Windows agent actually collected; anything it could not read is NOT_SUPPORTED, never guessed.
"""

from dataclasses import dataclass
from enum import StrEnum

from app.modules.devices.catalog import CategoryCode


class Result(StrEnum):
    OK = "OK"
    WARNING = "WARNING"
    FAIL = "FAIL"
    NOT_TESTED = "NOT_TESTED"
    NOT_SUPPORTED = "NOT_SUPPORTED"


class Source(StrEnum):
    MANUAL = "MANUAL"
    AGENT = "AGENT"
    # Reserved for a future AI layer: never shown as a verified result.
    AI_SUGGESTION = "AI_SUGGESTION"


@dataclass(frozen=True, slots=True)
class DiagnosticTest:
    code: str
    name: str
    component: str
    automated: bool = False


C = CategoryCode
PHONE_TABLET = (C.PHONE, C.TABLET)
COMPUTERS = (C.LAPTOP, C.DESKTOP)

_MANUAL: list[tuple[DiagnosticTest, tuple[CategoryCode, ...]]] = [
    (DiagnosticTest("POWER_ON", "Encendido", "Alimentación"), tuple(C)),
    (DiagnosticTest("SCREEN", "Pantalla", "Pantalla"), (*PHONE_TABLET, C.LAPTOP)),
    (DiagnosticTest("TOUCH", "Táctil", "Pantalla"), PHONE_TABLET),
    (DiagnosticTest("CAMERAS", "Cámaras", "Cámara"), PHONE_TABLET),
    (DiagnosticTest("MICROPHONE", "Micrófono", "Audio"), PHONE_TABLET),
    (DiagnosticTest("SPEAKER", "Parlante", "Audio"), PHONE_TABLET),
    (DiagnosticTest("EARPIECE", "Auricular de llamada", "Audio"), (C.PHONE,)),
    (DiagnosticTest("CHARGING_PORT", "Puerto de carga", "Alimentación"), PHONE_TABLET),
    (DiagnosticTest("BUTTONS", "Botones", "Controles"), PHONE_TABLET),
    (DiagnosticTest("WIFI", "Wi-Fi", "Conectividad"), (*PHONE_TABLET, *COMPUTERS, C.CONSOLE)),
    (DiagnosticTest("BLUETOOTH", "Bluetooth", "Conectividad"), PHONE_TABLET),
    (DiagnosticTest("CELL_SIGNAL", "Señal celular", "Conectividad"), (C.PHONE,)),
    (DiagnosticTest("BATTERY_HEALTH", "Salud de batería", "Batería"), (*PHONE_TABLET, C.LAPTOP)),
    (DiagnosticTest("BIOMETRICS", "Biometría (huella o rostro)", "Seguridad"), PHONE_TABLET),
    (DiagnosticTest("KEYBOARD", "Teclado", "Entrada"), COMPUTERS),
    (DiagnosticTest("TOUCHPAD", "Touchpad", "Entrada"), (C.LAPTOP,)),
    (DiagnosticTest("USB_PORTS", "Puertos USB", "Puertos"), COMPUTERS),
    (DiagnosticTest("VIDEO_OUTPUT", "Salida de video", "Video"), (C.DESKTOP, C.CONSOLE)),
    (DiagnosticTest("AUDIO", "Audio", "Audio"), COMPUTERS),
    (DiagnosticTest("WEBCAM", "Cámara web", "Cámara"), (C.LAPTOP,)),
    (DiagnosticTest("HINGES", "Bisagras", "Chasis"), (C.LAPTOP,)),
    (
        DiagnosticTest("FANS_THERMAL", "Ventiladores y temperatura", "Térmico"),
        (*COMPUTERS, C.CONSOLE),
    ),
    (DiagnosticTest("CONTROLLERS", "Controles", "Entrada"), (C.CONSOLE,)),
    (DiagnosticTest("DISC_DRIVE", "Lector de discos", "Almacenamiento"), (C.CONSOLE,)),
    (DiagnosticTest("STORAGE", "Almacenamiento", "Almacenamiento"), (C.CONSOLE,)),
    (DiagnosticTest("GENERAL", "Revisión general", "General"), (C.OTHER,)),
]

AGENT_TESTS: list[DiagnosticTest] = [
    DiagnosticTest("AGENT_SYSTEM", "Sistema y equipo", "Sistema", automated=True),
    DiagnosticTest("AGENT_CPU", "Procesador", "Procesador", automated=True),
    DiagnosticTest("AGENT_MEMORY", "Memoria RAM", "Memoria", automated=True),
    DiagnosticTest("AGENT_GPU", "Tarjeta de video", "Video", automated=True),
    DiagnosticTest("AGENT_DISK_HEALTH", "Salud de discos", "Almacenamiento", automated=True),
    DiagnosticTest("AGENT_DISK_SPACE", "Espacio en disco", "Almacenamiento", automated=True),
    DiagnosticTest("AGENT_DISK_SMART", "SMART de discos", "Almacenamiento", automated=True),
    DiagnosticTest("AGENT_BATTERY", "Desgaste de batería", "Batería", automated=True),
    DiagnosticTest("AGENT_STABILITY", "Estabilidad (30 días)", "Sistema", automated=True),
]

AGENT_CATEGORIES: frozenset[CategoryCode] = frozenset(COMPUTERS)

ALL_TESTS: dict[str, DiagnosticTest] = {
    **{test.code: test for test, _ in _MANUAL},
    **{test.code: test for test in AGENT_TESTS},
}


def manual_tests_for(category: str) -> list[DiagnosticTest]:
    return [test for test, categories in _MANUAL if category in categories]


def tests_for(category: str) -> list[DiagnosticTest]:
    tests = manual_tests_for(category)
    if category in AGENT_CATEGORIES:
        tests += AGENT_TESTS
    return tests


# --- Thresholds used to evaluate agent data (documented in docs/ERMS-API.md) -------------
BATTERY_WEAR_WARNING = 20.0  # % of design capacity lost
BATTERY_WEAR_FAIL = 40.0
DISK_FREE_WARNING = 10.0  # % free on any volume
SMART_WEAR_WARNING = 80  # % of rated life used (StorageReliabilityCounter.Wear)
SMART_TEMP_WARNING = 60  # °C
UNEXPECTED_SHUTDOWNS_WARNING = 1  # Kernel-Power 41 in 30 days
BUGCHECKS_WARNING = 1  # blue screens in 30 days
BUGCHECKS_FAIL = 5
