"""Assembly rules with parts taken from the owner's simulator (fictitious IDs, real specs)."""

from decimal import Decimal
from typing import Any

import pytest

from app.modules.assembly.catalog import AssemblyCategory as C
from app.modules.assembly.catalog import UseProfile, validate_specs
from app.modules.assembly.rules import (
    Build,
    Piece,
    Thresholds,
    blocked_reason,
    evaluate,
    incompatibility,
    steps_for,
)


def piece(category: C, name: str, price: int, **specs: Any) -> Piece:
    return Piece(
        id=name,
        name=name,
        category=category,
        price=Decimal(price),
        specs=validate_specs(category, specs),
    )


CPU_9800X3D = piece(
    C.CPU, "Ryzen 7 9800X3D", 1999000, socket="AM5", cores=8, tdp_w=162,
    integrated_graphics=True, gaming_index=98, work_index=66,
)  # fmt: skip
CPU_265KF = piece(
    C.CPU, "Core Ultra 7 265KF", 1490000, socket="LGA1851", cores=20, tdp_w=250,
    integrated_graphics=False, gaming_index=78, work_index=85,
)  # fmt: skip
CPU_8600G = piece(
    C.CPU, "Ryzen 5 8600G", 846000, socket="AM5", cores=6, tdp_w=88,
    integrated_graphics=True, gaming_index=56, work_index=42,
)  # fmt: skip
BOARD_B850S = piece(
    C.BOARD, "MSI Pro B850-S", 789000, socket="AM5", ram_type="DDR5", form_factor="ATX",
    ram_slots=4, m2_slots=3,
)  # fmt: skip
BOARD_B850M = piece(
    C.BOARD, "B850M Rock", 447000, socket="AM5", ram_type="DDR5", form_factor="mATX",
    ram_slots=4, m2_slots=2, max_ram_mhz=5600,
)  # fmt: skip
RAM_16_DDR5 = piece(
    C.RAM, "16 GB DDR5 6000", 839000, ram_type="DDR5", modules=1, capacity_gb=16, mhz=6000
)
RAM_32_DDR4 = piece(
    C.RAM, "32 GB DDR4 3200", 859000, ram_type="DDR4", modules=1, capacity_gb=32, mhz=3200
)
GPU_5070 = piece(
    C.GPU, "RTX 5070 Shadow 3X", 3399000, tdp_w=250, length_mm=297, gaming_index=75,
    power_connector="16PIN",
)  # fmt: skip
GPU_5090 = piece(
    C.GPU, "RTX 5090", 17390000, tdp_w=575, length_mm=348, gaming_index=100,
    power_connector="16PIN",
)  # fmt: skip
GPU_RX = piece(
    C.GPU, "RX 9060 XT", 2550000, tdp_w=170, length_mm=250, gaming_index=63,
    power_connector="8PIN",
)  # fmt: skip
SSD = piece(C.STORAGE, "SSD 1 TB", 639000, interface="M.2")
PSU_850 = piece(C.PSU, "850 W Gold", 407000, watts=850, form_factor="ATX")
PSU_600 = piece(C.PSU, "600 W Bronze", 179000, watts=600, form_factor="ATX")
CASE_216 = piece(
    C.CASE, "Lancool 216", 393000, size="ATX", board_form_factors=["ATX", "mATX", "ITX"],
    max_gpu_mm=392, max_cooler_mm=180, max_radiator_mm=360, psu_form_factors=["ATX"],
    fan_slots=7,
)  # fmt: skip
CASE_A4 = piece(
    C.CASE, "A4-H2O ITX", 642000, size="ITX", board_form_factors=["ITX"], max_gpu_mm=322,
    max_cooler_mm=55, max_radiator_mm=240, psu_form_factors=["SFX"], fan_slots=3,
)  # fmt: skip
COOLER_U12S = piece(C.COOLER, "NH-U12S", 415000, type="AIR", height_mm=158, tdp_w=180)
COOLER_D15 = piece(
    C.COOLER, "NH-D15", 529000, type="AIR", height_mm=165, tdp_w=250, dual_tower=True
)
COOLER_L9A = piece(
    C.COOLER, "NH-L9a-AM5", 279000, type="AIR", height_mm=37, tdp_w=65, sockets=["AM4", "AM5"]
)
AIO_360 = piece(C.COOLER, "AIO 360", 520000, type="AIO", radiator_mm=360, tdp_w=320)
STRIMER_16 = piece(C.RGB, "Strimer 16-12", 264000, kind="STRIMER_16")
FAN_KIT = piece(C.RGB, "Kit x3", 379000, kind="FAN_KIT", fan_count=3, infinity=True)


def gamer() -> Build:
    """The simulator's "Gamer 1440p" preset."""
    return Build(
        cpu=CPU_9800X3D,
        board=BOARD_B850S,
        ram=RAM_16_DDR5,
        ram_units=2,
        gpu=GPU_5070,
        storage=[SSD],
        psu=PSU_850,
        case=CASE_216,
        cooler=COOLER_U12S,
    )


def messages(issues: list[Any]) -> str:
    return " | ".join(i.message for i in issues)


def test_gamer_preset_is_ready_and_priced() -> None:
    result = evaluate(gamer())
    assert result.errors == []
    assert result.ready
    assert result.watts == 162 + 250 + 50 + 2 * 5 + 7 + 5
    assert result.recommended_psu_w == 650
    # CPU + board + 2 RAM units + GPU + SSD + PSU + case + cooler
    assert result.price == Decimal(
        1999000 + 789000 + 839000 * 2 + 3399000 + 639000 + 407000 + 393000 + 415000
    )
    assert result.gaming_index == round(75 * 0.75 + 98 * 0.25)
    assert result.ram_gb == 32


def test_trap_preset_reports_every_incompatibility() -> None:
    """The simulator's "Con errores para practicar" preset."""
    trap = Build(
        cpu=CPU_265KF,
        board=BOARD_B850M,
        ram=RAM_32_DDR4,
        ram_units=1,
        storage=[SSD],
        psu=PSU_600,
        case=CASE_A4,
        cooler=COOLER_D15,
    )
    text = messages(evaluate(trap).errors)
    assert "Socket incompatible: la CPU es LGA1851 y la placa AM5" in text
    assert "La placa usa DDR5 y la memoria es DDR4" in text
    assert "Una placa mATX no cabe en este gabinete" in text
    assert "El disipador mide 165 mm de alto y el gabinete admite 55 mm" in text
    assert "acepta fuentes SFX, no ATX" in text
    assert "sin tarjeta gráfica no habrá imagen" in text
    assert "canal sencillo" in messages(evaluate(trap).warnings)


def test_power_supply_too_small_and_low_margin() -> None:
    weak = gamer()
    weak.gpu, weak.psu = GPU_5090, PSU_600
    assert "no alcanza el consumo estimado" in messages(evaluate(weak).errors)
    tight = gamer()
    tight.psu = piece(C.PSU, "620 W", 1, watts=620, form_factor="ATX")
    assert "Poco margen en la fuente" in messages(evaluate(tight).warnings)


def test_cooler_socket_gpu_length_and_ram_speed() -> None:
    b = gamer()
    b.cpu, b.board, b.cooler = CPU_265KF, None, COOLER_L9A
    assert "solo trae anclaje para AM4/AM5" in messages(evaluate(b).errors)
    long_gpu = gamer()
    long_gpu.case = piece(
        C.CASE, "Mini", 1, size="MATX", board_form_factors=["mATX", "ITX"], max_gpu_mm=250,
        max_cooler_mm=165, max_radiator_mm=240, psu_form_factors=["ATX"], fan_slots=6,
    )  # fmt: skip
    errors = messages(evaluate(long_gpu).errors)
    assert "La gráfica mide 297 mm y el gabinete admite hasta 250 mm" in errors
    assert "Una placa ATX no cabe" in errors
    fast_ram = gamer()
    fast_ram.board = BOARD_B850M
    assert "funcionará a 5600 MHz" in messages(evaluate(fast_ram).warnings)


def test_radiator_and_fan_room() -> None:
    b = gamer()
    b.case, b.cooler = CASE_A4, AIO_360
    assert "El radiador de 360 mm no cabe" in messages(evaluate(b).errors)
    crowded = gamer()
    crowded.cooler, crowded.rgb = AIO_360, [FAN_KIT, FAN_KIT]
    assert "Hay 6 ventiladores en kits y el gabinete tiene espacio para unos 4" in messages(
        evaluate(crowded).warnings
    )


def test_strimer_needs_a_16_pin_gpu() -> None:
    b = gamer()
    b.gpu, b.rgb = GPU_RX, [STRIMER_16]
    assert "conector de 16 pines" in messages(evaluate(b).errors)
    b.gpu = None
    assert "El Strimer 16-12 necesita una tarjeta gráfica" in messages(evaluate(b).errors)


@pytest.mark.parametrize(
    ("cpu", "gpu", "expected"),
    [
        (CPU_8600G, GPU_5090, "el procesador limita a la gráfica"),
        (CPU_9800X3D, GPU_RX, "la gráfica limita al procesador"),
    ],
)
def test_gaming_bottlenecks(cpu: Piece, gpu: Piece, expected: str) -> None:
    b = gamer()
    b.cpu, b.gpu = cpu, gpu
    assert expected in messages(evaluate(b, UseProfile.GAMING).warnings)


def test_bottleneck_threshold_and_profiles() -> None:
    b = gamer()
    b.cpu, b.gpu = CPU_9800X3D, GPU_RX  # gap of 35 points
    assert "Cuello de botella" not in messages(evaluate(b, limits=Thresholds(40, 16)).warnings)
    office = gamer()
    assert "Para oficina esta gráfica es más de lo necesario" in messages(
        evaluate(office, UseProfile.OFFICE).warnings
    )
    small_ram = gamer()
    small_ram.ram_units = 1
    warnings = messages(evaluate(small_ram, UseProfile.DESIGN).warnings)
    assert "al menos 16 GB de RAM (hay 16 GB)" not in warnings
    assert "al menos 32 GB" in messages(
        evaluate(small_ram, UseProfile.DESIGN, Thresholds(25, 32)).warnings
    )


def test_missing_parts_and_candidate_reasons() -> None:
    partial = Build(cpu=CPU_9800X3D)
    result = evaluate(partial)
    assert result.missing == [C.BOARD, C.RAM, C.STORAGE, C.PSU, C.CASE, C.COOLER]
    assert not result.ready
    reason = incompatibility(partial, BOARD_B850M, UseProfile.GAMING, Thresholds())
    assert reason is None
    lga = piece(
        C.BOARD, "Z890", 1, socket="LGA1851", ram_type="DDR5", form_factor="ATX", ram_slots=4,
        m2_slots=3,
    )  # fmt: skip
    assert "Socket incompatible" in (
        incompatibility(partial, lga, UseProfile.GAMING, Thresholds()) or ""
    )


def test_assembly_steps_follow_the_real_order() -> None:
    steps = steps_for(gamer())
    codes = [s.code for s in steps]
    assert codes == ["cpu", "paste", "cool", "ram", "m2", "board", "psu", "gpu", "cables", "boot"]
    by_code = {s.code: s for s in steps}
    assert blocked_reason(by_code["board"], {"cpu"}) == (
        "Aún no: la RAM se instala con la placa fuera del gabinete: dentro el acceso es incómodo."
    )
    assert blocked_reason(by_code["paste"], {"cpu"}) is None
    aio = gamer()
    aio.cooler, aio.rgb = AIO_360, [FAN_KIT]
    aio_codes = [s.code for s in steps_for(aio)]
    assert aio_codes.index("cool") > aio_codes.index("board")
    assert "rgb" in aio_codes


def test_specs_are_validated_with_spanish_message() -> None:
    with pytest.raises(ValueError, match="Especificaciones inválidas para Procesador"):
        validate_specs(C.CPU, {"socket": "AM5"})
    with pytest.raises(ValueError, match="altura del disipador"):
        validate_specs(C.COOLER, {"type": "AIR", "tdp_w": 100})
