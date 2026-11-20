import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Self

from pydantic import BaseModel, Field, field_validator, model_validator

from app.modules.privacy.catalog import ConsentChannel
from app.modules.workorders.schemas import MoneyOut, PersonRef
from app.shared.validators import clean_multiline, clean_text

QuoteStatus = Literal["DRAFT", "SENT", "ACCEPTED", "REJECTED", "SUPERSEDED", "EXPIRED"]


class QuoteItemInput(BaseModel):
    kind: Literal["LABOR", "PART"]
    part_id: uuid.UUID | None = Field(
        default=None, description="Repuesto del inventario; vacío = repuesto por pedir"
    )
    description: str | None = Field(default=None, max_length=300)
    quantity: Decimal = Field(gt=0, le=9999, max_digits=10, decimal_places=2)
    unit_price: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    discount_percent: Decimal = Field(default=Decimal("0"), ge=0, le=100, decimal_places=2)
    apply_tax: bool = Field(default=False, description="Aplica IVA del 19 %")
    price_includes_tax: bool = Field(
        default=False, description="El precio escrito ya incluye el IVA"
    )

    _description = field_validator("description")(clean_text)

    @model_validator(mode="after")
    def _rules(self) -> Self:
        if self.kind == "LABOR" and self.part_id is not None:
            raise ValueError("La mano de obra no lleva repuesto del inventario.")
        if self.part_id is None and not self.description:
            raise ValueError("Describa el ítem.")
        if not self.apply_tax:
            self.price_includes_tax = False
        return self


class QuoteSave(BaseModel):
    items: list[QuoteItemInput] = Field(min_length=1, max_length=100)
    notes: str | None = Field(default=None, max_length=4000)

    _notes = field_validator("notes")(clean_multiline)


class QuoteItemRead(BaseModel):
    id: uuid.UUID
    position: int
    kind: Literal["LABOR", "PART"]
    part_id: uuid.UUID | None
    sku: str | None
    in_stock: int | None
    description: str
    quantity: Decimal
    unit_price: MoneyOut
    discount_percent: Decimal
    tax_rate: int
    price_includes_tax: bool
    discount_amount: MoneyOut
    base_amount: MoneyOut
    tax_amount: MoneyOut
    total_amount: MoneyOut


class QuoteRead(BaseModel):
    id: uuid.UUID
    version: int
    status: QuoteStatus = Field(description="EXPIRED se calcula: enviada y vencida")
    valid_until: date | None
    notes: str | None
    subtotal: MoneyOut
    discount_total: MoneyOut
    tax_total: MoneyOut
    total: MoneyOut
    discount_authorized_by: PersonRef | None
    created_by: PersonRef | None
    created_at: datetime
    sent_at: datetime | None
    responded_at: datetime | None
    response_channel: ConsentChannel | None
    items: list[QuoteItemRead]


class QuoteOverview(BaseModel):
    diagnostic_fee: MoneyOut
    quotes: list[QuoteRead] = Field(description="De la versión más reciente a la más antigua")
    can_edit: bool
    can_send: bool
    can_respond: bool
    max_discount_percent: int = Field(description="Descuento máximo por ítem para este usuario")


class RespondRequest(BaseModel):
    accepted: bool
    channel: ConsentChannel
    reason: str | None = Field(default=None, max_length=2000)

    _reason = field_validator("reason")(clean_multiline)
