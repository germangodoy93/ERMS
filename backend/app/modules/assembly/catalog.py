"""PC assembly catalog: component categories, their technical specs and the assembly steps.

The specs replace the name-based guesses of the original HTML simulator: every rule reads an
explicit field that the workshop can edit in the inventory.
"""

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class AssemblyCategory(StrEnum):
    CPU = "CPU"
    BOARD = "BOARD"
    RAM = "RAM"
    GPU = "GPU"
    STORAGE = "STORAGE"
    PSU = "PSU"
    CASE = "CASE"
    COOLER = "COOLER"
    RGB = "RGB"
    # Setup (sold with the PC in the same order)
    MONITOR = "MONITOR"
    KEYBOARD = "KEYBOARD"
    MOUSE = "MOUSE"
    PAD = "PAD"
    HEADSET = "HEADSET"
    MIC = "MIC"
    SPEAKER = "SPEAKER"
    CAMERA = "CAMERA"
    STREAM = "STREAM"
    CHAIR = "CHAIR"
    DESK = "DESK"
    LIGHT = "LIGHT"


CATEGORY_LABELS: dict[AssemblyCategory, str] = {
    AssemblyCategory.CPU: "Procesador",
    AssemblyCategory.BOARD: "Placa base",
    AssemblyCategory.RAM: "Memoria",
    AssemblyCategory.GPU: "Gráfica",
    AssemblyCategory.STORAGE: "Almacenamiento",
    AssemblyCategory.PSU: "Fuente",
    AssemblyCategory.CASE: "Gabinete",
    AssemblyCategory.COOLER: "Refrigeración",
    AssemblyCategory.RGB: "RGB",
    AssemblyCategory.MONITOR: "Monitores",
    AssemblyCategory.KEYBOARD: "Teclado",
    AssemblyCategory.MOUSE: "Mouse",
    AssemblyCategory.PAD: "Pad",
    AssemblyCategory.HEADSET: "Audífonos",
    AssemblyCategory.MIC: "Micrófono",
    AssemblyCategory.SPEAKER: "Parlantes",
    AssemblyCategory.CAMERA: "Cámara",
    AssemblyCategory.STREAM: "Streaming",
    AssemblyCategory.CHAIR: "Silla",
    AssemblyCategory.DESK: "Escritorio",
    AssemblyCategory.LIGHT: "Luces",
}
SETUP: frozenset["AssemblyCategory"] = frozenset(
    {
        AssemblyCategory.MONITOR,
        AssemblyCategory.KEYBOARD,
        AssemblyCategory.MOUSE,
        AssemblyCategory.PAD,
        AssemblyCategory.HEADSET,
        AssemblyCategory.MIC,
        AssemblyCategory.SPEAKER,
        AssemblyCategory.CAMERA,
        AssemblyCategory.STREAM,
        AssemblyCategory.CHAIR,
        AssemblyCategory.DESK,
        AssemblyCategory.LIGHT,
    }
)

# Categories a build cannot do without (the GPU is optional with integrated graphics).
REQUIRED: tuple[AssemblyCategory, ...] = (
    AssemblyCategory.CPU,
    AssemblyCategory.BOARD,
    AssemblyCategory.RAM,
    AssemblyCategory.STORAGE,
    AssemblyCategory.PSU,
    AssemblyCategory.CASE,
    AssemblyCategory.COOLER,
)
# Categories where several parts can be chosen, with their limit (as in the simulator).
MULTI_LIMITS: dict[AssemblyCategory, int] = {
    AssemblyCategory.STORAGE: 4,
    AssemblyCategory.RGB: 8,
    AssemblyCategory.MONITOR: 3,
    AssemblyCategory.MIC: 2,
    AssemblyCategory.STREAM: 3,
    AssemblyCategory.LIGHT: 2,
}
MULTI: frozenset[AssemblyCategory] = frozenset(MULTI_LIMITS)
MAX_STORAGE = MULTI_LIMITS[AssemblyCategory.STORAGE]
MAX_RGB = MULTI_LIMITS[AssemblyCategory.RGB]


class DeskShape(StrEnum):
    STRAIGHT = "STRAIGHT"
    L = "L"


class PcPosition(StrEnum):
    AUTO = "AUTO"
    DESK = "DESK"
    FLOOR = "FLOOR"


class UseProfile(StrEnum):
    OFFICE = "OFFICE"
    DESIGN = "DESIGN"
    GAMING = "GAMING"


PROFILE_LABELS: dict[UseProfile, str] = {
    UseProfile.OFFICE: "Oficina",
    UseProfile.DESIGN: "Diseño y edición",
    UseProfile.GAMING: "Gaming",
}

Socket = Annotated[str, Field(min_length=2, max_length=20)]
RamType = Literal["DDR4", "DDR5"]
BoardForm = Literal["EATX", "ATX", "mATX", "ITX"]
PsuForm = Literal["ATX", "SFX"]
Index = Annotated[int, Field(ge=0, le=100)]


StyleValue = str | int | float | bool


class _Spec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    style: dict[str, StyleValue] | None = Field(
        default=None,
        description="Detalles visuales para el 3D (color, RGB, ventiladores…); no afectan reglas",
    )


class CpuSpec(_Spec):
    socket: Socket
    cores: int = Field(ge=1, le=256)
    tdp_w: int = Field(ge=1, le=1000, description="Consumo máximo en vatios")
    integrated_graphics: bool
    gaming_index: Index = Field(description="Índice orientativo para juegos (0-100)")
    work_index: Index = Field(description="Índice orientativo para trabajo pesado (0-100)")


class BoardSpec(_Spec):
    socket: Socket
    ram_type: RamType
    form_factor: BoardForm
    ram_slots: int = Field(ge=1, le=8)
    m2_slots: int = Field(ge=0, le=8)
    max_ram_mhz: int | None = Field(default=None, ge=1000, le=12000)


class RamSpec(_Spec):
    ram_type: RamType
    modules: int = Field(ge=1, le=8, description="Módulos por unidad (kit)")
    capacity_gb: int = Field(ge=1, le=1024, description="Capacidad total de la unidad")
    mhz: int | None = Field(default=None, ge=1000, le=12000)


class GpuSpec(_Spec):
    tdp_w: int = Field(ge=1, le=1500)
    length_mm: int = Field(ge=50, le=500)
    gaming_index: Index
    power_connector: Literal["NONE", "8PIN", "16PIN"]


class StorageSpec(_Spec):
    interface: Literal["M.2", "SATA"]


class PsuSpec(_Spec):
    watts: int = Field(ge=100, le=3000)
    form_factor: PsuForm


class CaseSpec(_Spec):
    size: Literal["ITX", "MATX", "ATX", "XL"]
    board_form_factors: list[BoardForm] = Field(min_length=1)
    max_gpu_mm: int = Field(ge=50, le=600)
    max_cooler_mm: int = Field(ge=20, le=250)
    max_radiator_mm: int = Field(ge=0, le=480)
    psu_form_factors: list[PsuForm] = Field(min_length=1)
    fan_slots: int = Field(ge=0, le=20)


class CoolerSpec(_Spec):
    type: Literal["AIR", "AIO"]
    tdp_w: int = Field(ge=1, le=1000, description="Calor que puede disipar")
    height_mm: int | None = Field(default=None, ge=10, le=250)
    radiator_mm: int | None = Field(default=None, ge=120, le=480)
    sockets: list[Socket] | None = Field(default=None, description="Vacío = anclaje universal")
    dual_tower: bool = False
    includes_fans: bool = True


class RgbSpec(_Spec):
    kind: Literal["FAN_KIT", "STRIMER_24", "STRIMER_16", "STRIMER_8", "GPU_SUPPORT"]
    fan_count: int = Field(default=0, ge=0, le=12)
    infinity: bool = False
    lcd: bool = False


class MonitorSpec(_Spec):
    inches: float = Field(ge=10, le=65)
    resolution: Literal["FHD", "QHD", "4K", "5K", "UWQHD", "DQHD"] | None = None
    hz: int | None = Field(default=None, ge=30, le=1000)
    oled: bool = False
    curved: bool = False
    ultrawide: Literal[0, 1, 2] = Field(default=0, description="0 = 16:9, 1 = 21:9, 2 = 32:9")
    pro: bool = Field(default=False, description="Monitor para diseño")


class KeyboardSpec(_Spec):
    size: Literal["60%", "75%", "TKL", "100%", "PAD"]
    low_profile: bool = False
    hall_effect: bool = False
    wireless: bool = False


class MouseSpec(_Spec):
    wireless: bool = False


class PadSpec(_Spec):
    size: Literal["M", "L", "XL", "XXL"]


class HeadsetSpec(_Spec):
    earbuds: bool = False
    wireless: bool = False
    rgb: bool = False


class MicSpec(_Spec):
    arm: bool = Field(default=False, description="Es un brazo, no un micrófono")
    xlr: bool = Field(default=False, description="Necesita interfaz de audio")
    rgb: bool = False


class SpeakerSpec(_Spec):
    kind: Literal["BAR", "PAIR", "ROBOT"]
    rgb: bool = False


class CameraSpec(_Spec):
    resolution: str | None = Field(default=None, max_length=10)


class StreamSpec(_Spec):
    kind: Literal["DECK", "LIGHT"]
    key_columns: int = Field(default=0, ge=0, le=10)
    key_rows: int = Field(default=0, ge=0, le=6)
    dials: bool = False


class ChairSpec(_Spec):
    pass


class DeskSpec(_Spec):
    width_cm: int = Field(ge=60, le=300)
    integrated_case: bool = Field(default=False, description="Escritorio con gabinete integrado")


class LightSpec(_Spec):
    kind: Literal["LINES", "SQUARES"]
    pieces: int = Field(ge=1, le=50)


SPEC_MODELS: dict[AssemblyCategory, type[_Spec]] = {
    AssemblyCategory.CPU: CpuSpec,
    AssemblyCategory.BOARD: BoardSpec,
    AssemblyCategory.RAM: RamSpec,
    AssemblyCategory.GPU: GpuSpec,
    AssemblyCategory.STORAGE: StorageSpec,
    AssemblyCategory.PSU: PsuSpec,
    AssemblyCategory.CASE: CaseSpec,
    AssemblyCategory.COOLER: CoolerSpec,
    AssemblyCategory.RGB: RgbSpec,
    AssemblyCategory.MONITOR: MonitorSpec,
    AssemblyCategory.KEYBOARD: KeyboardSpec,
    AssemblyCategory.MOUSE: MouseSpec,
    AssemblyCategory.PAD: PadSpec,
    AssemblyCategory.HEADSET: HeadsetSpec,
    AssemblyCategory.MIC: MicSpec,
    AssemblyCategory.SPEAKER: SpeakerSpec,
    AssemblyCategory.CAMERA: CameraSpec,
    AssemblyCategory.STREAM: StreamSpec,
    AssemblyCategory.CHAIR: ChairSpec,
    AssemblyCategory.DESK: DeskSpec,
    AssemblyCategory.LIGHT: LightSpec,
}


def validate_specs(category: AssemblyCategory, specs: dict[str, object]) -> dict[str, object]:
    """Returns the normalized specs or raises ValueError naming the wrong fields."""
    try:
        model = SPEC_MODELS[category].model_validate(specs)
    except ValidationError as exc:
        fields = sorted({".".join(str(p) for p in e["loc"]) or "specs" for e in exc.errors()})
        raise ValueError(
            f"Especificaciones inválidas para {CATEGORY_LABELS[category]}: "
            f"revise {', '.join(fields)}."
        ) from None
    if isinstance(model, CoolerSpec):
        if model.type == "AIR" and model.height_mm is None:
            raise ValueError("Indique la altura del disipador de aire.")
        if model.type == "AIO" and model.radiator_mm is None:
            raise ValueError("Indique el tamaño del radiador.")
    return model.model_dump(mode="json")


# --- Assembly steps (real order, from the simulator) -----------------------------------
class Step(BaseModel):
    code: str
    title: str
    requires: tuple[str, ...] = ()


# Why a step cannot be done yet, keyed by the missing prerequisite.
BLOCKED_REASON: dict[str, str] = {
    "cpu": "primero la CPU debe estar en su socket.",
    "paste": "sin pasta térmica entre CPU y disipador, la CPU se sobrecalienta en segundos.",
    "ram": "la RAM se instala con la placa fuera del gabinete: dentro el acceso es incómodo.",
    "m2": "el SSD M.2 va antes de montar la placa: después la ranura suele quedar tapada.",
    "board": "esta pieza se fija a la placa ya atornillada dentro del gabinete.",
    "psu": "sin la fuente instalada no hay cables que conectar.",
    "gpu": "la gráfica también necesita su cable PCIe: instálela antes de cablear.",
    "sata": "monte los discos SATA en sus bahías antes de cablear.",
    "rgb": "instale primero los ventiladores y accesorios RGB: luego los cables estorban.",
    "cool": "el ventilador o la bomba del disipador también se conecta a la placa.",
    "cables": "sin cables conectados no llega corriente a nada.",
}
