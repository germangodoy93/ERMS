import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.modules.assembly.catalog import (
    MULTI_LIMITS,
    AssemblyCategory,
    DeskShape,
    PcPosition,
    UseProfile,
)
from app.modules.workorders.schemas import MoneyOut, PersonRef
from app.shared.validators import clean_multiline, clean_text

C = AssemblyCategory


def _many(category: AssemblyCategory) -> Any:
    return Field(default_factory=list, max_length=MULTI_LIMITS[category])


class CatalogPart(BaseModel):
    id: uuid.UUID
    sku: str
    name: str
    category: AssemblyCategory
    sale_price: MoneyOut
    stock: int
    specs: dict[str, Any]


class Selection(BaseModel):
    cpu: uuid.UUID | None = None
    board: uuid.UUID | None = None
    ram: uuid.UUID | None = None
    ram_units: int = Field(default=2, ge=1, le=4, description="Unidades del kit de RAM")
    gpu: uuid.UUID | None = None
    psu: uuid.UUID | None = None
    case: uuid.UUID | None = None
    cooler: uuid.UUID | None = None
    storage: list[uuid.UUID] = _many(C.STORAGE)
    rgb: list[uuid.UUID] = _many(C.RGB)
    # Setup
    monitor: list[uuid.UUID] = _many(C.MONITOR)
    keyboard: uuid.UUID | None = None
    mouse: uuid.UUID | None = None
    pad: uuid.UUID | None = None
    headset: uuid.UUID | None = None
    mic: list[uuid.UUID] = _many(C.MIC)
    speaker: uuid.UUID | None = None
    camera: uuid.UUID | None = None
    stream: list[uuid.UUID] = _many(C.STREAM)
    chair: uuid.UUID | None = None
    desk: uuid.UUID | None = None
    light: list[uuid.UUID] = _many(C.LIGHT)
    desk_shape: DeskShape = DeskShape.STRAIGHT
    pc_position: PcPosition = PcPosition.AUTO

    def ids_of(self, category: AssemblyCategory) -> list[uuid.UUID]:
        value = getattr(self, category.value.lower())
        if isinstance(value, list):
            return list(value)
        return [value] if value else []

    def part_ids(self) -> set[uuid.UUID]:
        return {pid for category in AssemblyCategory for pid in self.ids_of(category)}


class EvaluateRequest(BaseModel):
    selection: Selection
    profile: UseProfile = UseProfile.GAMING
    candidates_for: AssemblyCategory | None = Field(
        default=None, description="Devuelve por qué no encaja cada pieza de esta categoría"
    )


class IssueOut(BaseModel):
    message: str
    categories: list[AssemblyCategory]


class EvaluationOut(BaseModel):
    errors: list[IssueOut]
    warnings: list[IssueOut]
    missing: list[AssemblyCategory]
    ready: bool = Field(description="Completa y sin incompatibilidades")
    watts: int
    recommended_psu_w: int
    price: MoneyOut = Field(description="Piezas del PC, IVA incluido")
    setup_price: MoneyOut = Field(description="Monitores, periféricos y mobiliario del setup")
    gaming_index: int
    work_index: int
    ram_gb: int
    candidates: dict[uuid.UUID, str] = Field(
        default_factory=dict, description="Pieza → motivo por el que no es compatible"
    )


class BuildWrite(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    profile: UseProfile = UseProfile.GAMING
    selection: Selection
    labor_price: Decimal = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=2)
    notes: str | None = Field(default=None, max_length=2000)

    _name = field_validator("name")(clean_text)
    _notes = field_validator("notes")(clean_multiline)


class BuildSummary(BaseModel):
    id: uuid.UUID
    name: str
    profile: UseProfile
    status: str
    price: MoneyOut
    work_order_id: uuid.UUID | None
    work_order_number: str | None
    updated_at: datetime


class BuildRead(BuildSummary):
    selection: Selection
    labor_price: MoneyOut
    notes: str | None
    created_by: PersonRef | None
    evaluation: EvaluationOut
    editable: bool


class OrderRequest(BaseModel):
    customer_id: uuid.UUID


class StepOut(BaseModel):
    code: str
    title: str
    done: bool
    blocked_reason: str | None


class AssemblyChecklist(BaseModel):
    build_id: uuid.UUID
    build_name: str
    steps: list[StepOut]
    parts_consumed: bool = Field(description="Las piezas ya se descontaron del inventario")
    can_work: bool = Field(description="La orden está en ensamble y el usuario puede avanzar")


class CatalogImportItem(BaseModel):
    sku: str = Field(min_length=2, max_length=40)
    name: str = Field(min_length=2, max_length=200)
    category: AssemblyCategory
    cost: Decimal = Field(
        ge=0, max_digits=14, decimal_places=2, description="Precio del proveedor, IVA incluido"
    )
    specs: dict[str, Any]


class CatalogImport(BaseModel):
    items: list[CatalogImportItem] = Field(min_length=1, max_length=2000)


class CatalogImportResult(BaseModel):
    created: int
    updated: int
    errors: list[str] = Field(description="Piezas rechazadas con su motivo")


class CostUpdateResult(BaseModel):
    updated: int
    unchanged: int
    unknown: list[str] = Field(description="Códigos que no están en el catálogo de ensamble")
    errors: list[str] = Field(description="Filas que no se pudieron leer")
