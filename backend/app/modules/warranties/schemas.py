import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.modules.workorders.catalog import UnlockMethod
from app.modules.workorders.schemas import AccessoryItem, PersonRef
from app.shared.validators import clean_multiline


class WarrantyRead(BaseModel):
    id: uuid.UUID
    work_order_id: uuid.UUID
    work_order_number: str
    days: int
    starts_on: date
    ends_on: date
    active: bool


class ClaimRead(BaseModel):
    id: uuid.UUID
    claim_order_id: uuid.UUID
    claim_order_number: str
    reported_issue: str
    status: Literal["OPEN", "ACCEPTED", "REJECTED"]
    resolution: str | None
    decided_by: PersonRef | None
    decided_at: datetime | None
    created_at: datetime


class WarrantyOverview(BaseModel):
    warranty: WarrantyRead | None = Field(
        description="Garantía de esta orden, o la original si esta orden es un reclamo"
    )
    claims: list[ClaimRead]
    is_claim_order: bool
    can_claim: bool
    can_decide: bool


class ClaimCreate(BaseModel):
    reported_issue: str = Field(min_length=5, max_length=4000)
    physical_condition: str = Field(min_length=3, max_length=4000)
    accessories: list[AccessoryItem] = Field(default_factory=list, max_length=20)
    unlock_method: UnlockMethod

    _texts = field_validator("reported_issue", "physical_condition")(clean_multiline)


class ClaimDecision(BaseModel):
    accepted: bool
    resolution: str = Field(min_length=5, max_length=4000)

    _resolution = field_validator("resolution")(clean_multiline)
