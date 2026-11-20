import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.modules.workorders.catalog import PaymentMethod
from app.modules.workorders.schemas import MoneyOut, PersonRef
from app.shared.validators import clean_multiline, clean_text


class PaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    method: PaymentMethod
    reference: str | None = Field(default=None, max_length=80, description="Nº de transacción")
    notes: str | None = Field(default=None, max_length=1000)

    _reference = field_validator("reference")(clean_text)
    _notes = field_validator("notes")(clean_multiline)


class PaymentRead(BaseModel):
    id: uuid.UUID
    receipt_number: str | None
    kind: Literal["ADVANCE", "PAYMENT"]
    amount: MoneyOut
    method: PaymentMethod
    reference: str | None
    notes: str | None
    received_by: PersonRef | None
    paid_at: datetime


class BillingRead(BaseModel):
    diagnostic_fee: MoneyOut
    accepted_quote_total: MoneyOut | None
    amount_due: MoneyOut = Field(
        description="Total de la cotización aceptada (incluye el diagnóstico) o el diagnóstico"
    )
    paid: MoneyOut
    balance: MoneyOut = Field(description="Positivo: debe el cliente; negativo: saldo a favor")
    payments: list[PaymentRead]
    can_register: bool
