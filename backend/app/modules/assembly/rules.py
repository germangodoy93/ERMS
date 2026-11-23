"""Compatibility and bottleneck rules for a PC build. Pure functions: no database access.

Ported from the owner's HTML simulator (`check()` and `startAsm()`), reading explicit specs
instead of guessing from product names, plus RAM speed and per-profile bottleneck checks.
"""

import math
from dataclasses import dataclass, field, replace
from decimal import Decimal
from typing import Any

from app.modules.assembly.catalog import (
    BLOCKED_REASON,
    CATEGORY_LABELS,
    REQUIRED,
    SETUP,
    AssemblyCategory,
    Step,
    UseProfile,
)

C = AssemblyCategory


@dataclass(frozen=True)
class Piece:
    id: Any
    name: str
    category: AssemblyCategory
    price: Decimal
    specs: dict[str, Any]

    def __getitem__(self, key: str) -> Any:
        return self.specs.get(key)


@dataclass
class Build:
    cpu: Piece | None = None
    board: Piece | None = None
    ram: Piece | None = None
    ram_units: int = 2
    gpu: Piece | None = None
    psu: Piece | None = None
    case: Piece | None = None
    cooler: Piece | None = None
    storage: list[Piece] = field(default_factory=list)
    rgb: list[Piece] = field(default_factory=list)
    # Setup
    monitor: list[Piece] = field(default_factory=list)
    keyboard: Piece | None = None
    mouse: Piece | None = None
    pad: Piece | None = None
    headset: Piece | None = None
    mic: list[Piece] = field(default_factory=list)
    speaker: Piece | None = None
    camera: Piece | None = None
    stream: list[Piece] = field(default_factory=list)
    chair: Piece | None = None
    desk: Piece | None = None
    light: list[Piece] = field(default_factory=list)

    def setup_pieces(self) -> list[Piece]:
        out: list[Piece] = []
        for category in SETUP:
            value = self.get(category)
            if isinstance(value, list):
                out.extend(value)
            elif value is not None:
                out.append(value)
        return out

    def get(self, category: AssemblyCategory) -> Piece | list[Piece] | None:
        value: Piece | list[Piece] | None = getattr(self, category.value.lower())
        return value

    def with_piece(self, piece: Piece) -> "Build":
        """A copy of the build with `piece` chosen (added for multi-choice categories)."""
        copy = replace(self)
        for key, value in vars(copy).items():
            if isinstance(value, list):  # lists are copied so the original stays untouched
                setattr(copy, key, list(value))
        name = piece.category.value.lower()
        current = getattr(copy, name)
        if isinstance(current, list):
            if piece not in current:
                current.append(piece)
        else:
            setattr(copy, name, piece)
        return copy


@dataclass(frozen=True)
class Thresholds:
    bottleneck_gap: int = 25
    min_ram_gb: int = 16


@dataclass(frozen=True)
class Issue:
    message: str
    categories: tuple[AssemblyCategory, ...]


@dataclass
class Evaluation:
    errors: list[Issue]
    warnings: list[Issue]
    missing: list[AssemblyCategory]
    watts: int
    recommended_psu_w: int
    price: Decimal
    setup_price: Decimal
    gaming_index: int
    work_index: int
    modules: int
    ram_gb: int

    @property
    def ready(self) -> bool:
        return not self.errors and not self.missing


def evaluate(
    b: Build, profile: UseProfile = UseProfile.GAMING, limits: Thresholds | None = None
) -> Evaluation:
    limits = limits or Thresholds()
    errors: list[Issue] = []
    warnings: list[Issue] = []

    def err(message: str, *cats: AssemblyCategory) -> None:
        errors.append(Issue(message, cats))

    def warn(message: str, *cats: AssemblyCategory) -> None:
        warnings.append(Issue(message, cats))

    cpu, board, ram, gpu, psu, case, cooler = (
        b.cpu,
        b.board,
        b.ram,
        b.gpu,
        b.psu,
        b.case,
        b.cooler,
    )
    units = max(1, b.ram_units)
    modules = ram["modules"] * units if ram else 0
    ram_gb = ram["capacity_gb"] * units if ram else 0
    kit_fans = sum(x["fan_count"] or 0 for x in b.rgb)

    if cpu and board and cpu["socket"] != board["socket"]:
        err(
            f"Socket incompatible: la CPU es {cpu['socket']} y la placa {board['socket']}.",
            C.CPU,
            C.BOARD,
        )
    if ram and board and ram["ram_type"] != board["ram_type"]:
        err(
            f"La placa usa {board['ram_type']} y la memoria es {ram['ram_type']}: "
            "las muescas no coinciden.",
            C.RAM,
            C.BOARD,
        )
    if ram and board and modules > board["ram_slots"]:
        err(
            f"Hay {modules} módulos de RAM y la placa solo tiene {board['ram_slots']} ranuras.",
            C.RAM,
            C.BOARD,
        )
    if ram and modules == 1:
        warn(
            "Con un solo módulo la RAM trabaja en canal sencillo: la mitad del ancho de banda. "
            "Lo ideal son 2 módulos.",
            C.RAM,
        )
    if ram and modules == 3:
        warn("Con 3 módulos se pierde el doble canal simétrico: use 2 o 4.", C.RAM)
    if ram and modules == 4 and ram["ram_type"] == "DDR5":
        warn("Con 4 módulos DDR5 la memoria suele bajar de frecuencia para ser estable.", C.RAM)
    if ram and board and ram["mhz"] and board["max_ram_mhz"] and ram["mhz"] > board["max_ram_mhz"]:
        warn(
            f"La memoria es de {ram['mhz']} MHz y la placa soporta hasta {board['max_ram_mhz']} "
            f"MHz: funcionará a {board['max_ram_mhz']} MHz.",
            C.RAM,
            C.BOARD,
        )
    if cooler and cpu and cooler["sockets"] and cpu["socket"] not in cooler["sockets"]:
        err(
            f"El disipador solo trae anclaje para {'/'.join(cooler['sockets'])} "
            f"y la CPU es {cpu['socket']}.",
            C.COOLER,
            C.CPU,
        )
    if cooler and not cooler["includes_fans"]:
        warn("Esta refrigeración no incluye ventiladores: hay que comprarlos aparte.", C.COOLER)
    if board and case and board["form_factor"] not in case["board_form_factors"]:
        err(
            f"Una placa {board['form_factor']} no cabe en este gabinete "
            f"(admite {', '.join(case['board_form_factors'])}).",
            C.BOARD,
            C.CASE,
        )
    if gpu and case and gpu["length_mm"] > case["max_gpu_mm"]:
        err(
            f"La gráfica mide {gpu['length_mm']} mm y el gabinete admite hasta "
            f"{case['max_gpu_mm']} mm.",
            C.GPU,
            C.CASE,
        )
    if cooler and case and cooler["type"] == "AIR" and cooler["height_mm"] > case["max_cooler_mm"]:
        err(
            f"El disipador mide {cooler['height_mm']} mm de alto y el gabinete admite "
            f"{case['max_cooler_mm']} mm: la tapa no cierra.",
            C.COOLER,
            C.CASE,
        )
    if (
        cooler
        and case
        and cooler["type"] == "AIO"
        and cooler["radiator_mm"] > case["max_radiator_mm"]
    ):
        err(
            f"El radiador de {cooler['radiator_mm']} mm no cabe: el gabinete admite hasta "
            f"{case['max_radiator_mm']} mm.",
            C.COOLER,
            C.CASE,
        )
    if cooler and cpu and cooler["tdp_w"] < cpu["tdp_w"]:
        warn(
            f"El disipador maneja ~{cooler['tdp_w']} W y la CPU puede consumir {cpu['tdp_w']} W: "
            "bajará su frecuencia por temperatura.",
            C.COOLER,
            C.CPU,
        )
    if psu and case and psu["form_factor"] not in case["psu_form_factors"]:
        err(
            f"El gabinete acepta fuentes {'/'.join(case['psu_form_factors'])}, "
            f"no {psu['form_factor']}.",
            C.PSU,
            C.CASE,
        )
    m2 = sum(1 for d in b.storage if d["interface"] == "M.2")
    if board and m2 > board["m2_slots"]:
        err(
            f"Hay {m2} SSD M.2 y la placa tiene {board['m2_slots']} ranuras M.2.",
            C.STORAGE,
            C.BOARD,
        )
    if cpu and not cpu["integrated_graphics"] and not gpu:
        err(
            "La CPU no tiene gráficos integrados: sin tarjeta gráfica no habrá imagen.",
            C.GPU,
            C.CPU,
        )
    kinds = [x["kind"] for x in b.rgb]
    if kinds.count("STRIMER_24") > 1:
        err(
            "La placa tiene un solo conector de 24 pines: elija un único Strimer de 24 pines.",
            C.RGB,
        )
    if "STRIMER_16" in kinds:
        if not gpu:
            err("El Strimer 16-12 necesita una tarjeta gráfica.", C.RGB, C.GPU)
        elif gpu["power_connector"] != "16PIN":
            err(
                "El Strimer 16-12 es para gráficas con conector de 16 pines; "
                "esta gráfica no lo tiene.",
                C.RGB,
                C.GPU,
            )
    if "GPU_SUPPORT" in kinds and not gpu:
        err("El soporte ARGB para GPU necesita una tarjeta gráfica.", C.RGB, C.GPU)
    if case:
        radiator_fans = cooler["radiator_mm"] // 120 if cooler and cooler["type"] == "AIO" else 0
        room = case["fan_slots"] - radiator_fans
        if kit_fans > room:
            warn(
                f"Hay {kit_fans} ventiladores en kits y el gabinete tiene espacio "
                f"para unos {room}.",
                C.RGB,
                C.CASE,
            )

    watts = (
        (cpu["tdp_w"] if cpu else 0)
        + (gpu["tdp_w"] if gpu else 0)
        + (50 if board else 0)
        + modules * 5
        + len(b.storage) * 7
        + ((15 if cooler["type"] == "AIO" else 5) if cooler else 0)
        + len(b.rgb) * 4
        + kit_fans * 3
    )
    recommended = math.ceil(watts * 1.3 / 50) * 50
    if psu and watts:
        if psu["watts"] < watts:
            err(
                f"La fuente ({psu['watts']} W) no alcanza el consumo estimado ({watts} W): "
                "se apagará por protección.",
                C.PSU,
            )
        elif psu["watts"] < recommended:
            warn(
                f"Poco margen en la fuente: se recomiendan {recommended} W para los picos.",
                C.PSU,
            )

    _bottlenecks(b, profile, limits, ram_gb, warn)

    missing = [c for c in REQUIRED if not b.get(c)]
    price = sum((p.price for p in (cpu, board, gpu, psu, case, cooler) if p), Decimal("0"))
    price += sum((p.price for p in [*b.storage, *b.rgb]), Decimal("0"))
    if ram:
        price += ram.price * units
    setup_price = sum((p.price for p in b.setup_pieces()), Decimal("0"))
    if cpu:
        gaming = (
            round(gpu["gaming_index"] * 0.75 + cpu["gaming_index"] * 0.25)
            if gpu
            else (8 if cpu["integrated_graphics"] else 0)
        )
        work = min(100, round(cpu["work_index"] * 0.8 + min(20.0, ram_gb / 64 * 20)))
    else:
        gaming = work = 0
    return Evaluation(
        errors=errors,
        warnings=warnings,
        missing=missing,
        watts=watts,
        recommended_psu_w=recommended,
        price=price,
        setup_price=setup_price,
        gaming_index=gaming,
        work_index=work,
        modules=modules,
        ram_gb=ram_gb,
    )


def _bottlenecks(b: Build, profile: UseProfile, limits: Thresholds, ram_gb: int, warn: Any) -> None:
    cpu, gpu, ram = b.cpu, b.gpu, b.ram
    gap = limits.bottleneck_gap
    if profile is UseProfile.GAMING and cpu:
        if not gpu:
            if cpu["integrated_graphics"]:
                warn(
                    "Para gaming los gráficos integrados se quedan cortos: agregue una "
                    "tarjeta gráfica.",
                    C.GPU,
                )
        else:
            diff = cpu["gaming_index"] - gpu["gaming_index"]
            if diff > gap:
                warn(
                    "Cuello de botella: la gráfica limita al procesador. Para gaming conviene "
                    "una gráfica más potente o un procesador más económico.",
                    C.GPU,
                    C.CPU,
                )
            elif -diff > gap:
                warn(
                    "Cuello de botella: el procesador limita a la gráfica. La gráfica no "
                    "rendirá todo lo que cuesta.",
                    C.CPU,
                    C.GPU,
                )
    if (
        profile is UseProfile.DESIGN
        and cpu
        and gpu
        and gpu["gaming_index"] - cpu["work_index"] > gap
    ):
        warn(
            "Para diseño y edición el procesador pesa más que la gráfica: considere un "
            "procesador más potente.",
            C.CPU,
            C.GPU,
        )
    if profile in (UseProfile.GAMING, UseProfile.DESIGN) and ram and ram_gb < limits.min_ram_gb:
        warn(
            f"Para este uso se recomiendan al menos {limits.min_ram_gb} GB de RAM "
            f"(hay {ram_gb} GB).",
            C.RAM,
        )
    if profile is UseProfile.OFFICE and gpu and gpu["gaming_index"] >= 60:
        warn("Para oficina esta gráfica es más de lo necesario: puede bajar el costo.", C.GPU)


def incompatibility(
    b: Build, candidate: Piece, profile: UseProfile, limits: Thresholds
) -> str | None:
    """The first error that choosing `candidate` would cause in its own category."""
    if candidate.category in SETUP:
        return None  # setup advice depends on the 3D layout and never blocks the sale
    result = evaluate(b.with_piece(candidate), profile, limits)
    return next((e.message for e in result.errors if candidate.category in e.categories), None)


def missing_label(categories: list[AssemblyCategory]) -> list[str]:
    return [CATEGORY_LABELS[c] for c in categories]


# --- Assembly checklist ----------------------------------------------------------------
def steps_for(b: Build) -> list[Step]:
    aio = bool(b.cooler and b.cooler["type"] == "AIO")
    m2 = any(d["interface"] == "M.2" for d in b.storage)
    sata = any(d["interface"] == "SATA" for d in b.storage)
    strimers = any(str(x["kind"]).startswith("STRIMER") for x in b.rgb)
    support = any(x["kind"] == "GPU_SUPPORT" for x in b.rgb)
    two = b.ram and b.ram["modules"] * max(1, b.ram_units) == 2
    cool = Step(
        code="cool",
        title="Montar el bloque y el radiador de la AIO"
        if aio
        else "Montar el disipador sobre la CPU",
        requires=("paste", "board") if aio else ("paste",),
    )
    steps = [
        Step(code="cpu", title="Colocar la CPU en el socket (alinear el triángulo)"),
        Step(code="paste", title="Aplicar pasta térmica sobre la CPU", requires=("cpu",)),
    ]
    if not aio:  # an air cooler goes on with the board still on the bench
        steps.append(cool)
    steps.append(
        Step(code="ram", title="Insertar la RAM" + (" en las ranuras A2 y B2" if two else ""))
    )
    if m2:
        steps.append(Step(code="m2", title="Instalar el SSD M.2 y su tornillo"))
    steps.append(
        Step(
            code="board",
            title="Atornillar la placa al gabinete sobre los separadores",
            requires=("cpu", "ram", *(("m2",) if m2 else ())),
        )
    )
    if aio:
        steps.append(cool)
    steps.append(Step(code="psu", title="Instalar la fuente en su compartimento"))
    if sata:
        steps.append(Step(code="sata", title="Montar los discos SATA en las bahías"))
    if b.gpu:
        steps.append(
            Step(code="gpu", title="Insertar la gráfica en la ranura PCIe x16", requires=("board",))
        )
    if b.rgb:
        steps.append(
            Step(
                code="rgb",
                title="Instalar ventiladores y accesorios RGB",
                requires=("board", *(("gpu",) if support and b.gpu else ())),
            )
        )
    cables = ["board", "psu", "cool"]
    cables += ["gpu"] if b.gpu else []
    cables += ["sata"] if sata else []
    cables += ["rgb"] if b.rgb else []
    steps.append(
        Step(
            code="cables",
            title="Conectar cables: 24 pines, EPS de CPU, PCIe, SATA y panel frontal"
            + (" (con los Strimer RGB)" if strimers else ""),
            requires=tuple(cables),
        )
    )
    steps.append(Step(code="boot", title="Encender y verificar el POST", requires=("cables",)))
    return steps


def blocked_reason(step: Step, done: set[str]) -> str | None:
    pending = [r for r in step.requires if r not in done]
    return f"Aún no: {BLOCKED_REASON[pending[0]]}" if pending else None
