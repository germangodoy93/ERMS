import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.modules.diagnostics.catalog import Result
from app.modules.diagnostics.schemas import ResultInput
from app.modules.workorders.schemas import MoneyOut, PersonRef
from app.shared.validators import clean_multiline


class TaskCreate(BaseModel):
    description: str = Field(min_length=3, max_length=4000)
    labor_minutes: int | None = Field(default=None, ge=0, le=10_000)

    _description = field_validator("description")(clean_multiline)


class ConsumeRequest(BaseModel):
    part_id: uuid.UUID
    quantity: int = Field(gt=0, le=1000)


class RepairPartRead(BaseModel):
    id: uuid.UUID
    part_id: uuid.UUID
    sku: str
    name: str
    quantity: int
    unit_cost: MoneyOut
    returned: bool


class TaskRead(BaseModel):
    id: uuid.UUID
    description: str
    labor_minutes: int | None
    technician: PersonRef | None
    created_at: datetime
    parts: list[RepairPartRead]


class QcCreate(BaseModel):
    results: list[ResultInput] = Field(min_length=1, max_length=60)
    notes: str | None = Field(default=None, max_length=2000)

    _notes = field_validator("notes")(clean_multiline)


class QcResultRead(BaseModel):
    test_code: str
    name: str
    result: Result
    observation: str | None


class QcRead(BaseModel):
    id: uuid.UUID
    passed: bool
    results: list[QcResultRead]
    notes: str | None
    checked_by: PersonRef | None
    checked_at: datetime


class QcTest(BaseModel):
    test_code: str
    name: str


class RepairOverview(BaseModel):
    tasks: list[TaskRead]
    quality_checks: list[QcRead] = Field(description="Del más reciente al más antiguo")
    qc_tests: list[QcTest] = Field(description="Pruebas que exige el control de calidad")
    can_repair: bool = Field(description="Orden en reparación y usuario habilitado")
    can_check: bool = Field(description="Orden en control de calidad y usuario habilitado")
