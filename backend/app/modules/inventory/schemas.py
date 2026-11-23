import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.modules.assembly.catalog import AssemblyCategory, validate_specs
from app.modules.workorders.schemas import MoneyOut, PersonRef
from app.shared.validators import (
    clean_multiline,
    clean_text,
    optional_email,
    optional_nit,
    optional_phone,
)

PartKind = Literal["PART", "COMPONENT", "ACCESSORY", "CONSUMABLE"]
TaxRate = Literal[0, 19]
Money = Field(ge=0, max_digits=14, decimal_places=2)
OptionalMoney = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=2)


def _sku(value: str | None) -> str | None:
    value = clean_text(value)
    return value.upper().replace(" ", "-") if value else None


class SupplierRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    tax_id: str | None
    contact_name: str | None
    phone: str | None
    email: str | None
    is_active: bool


class SupplierWrite(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    tax_id: str | None = Field(default=None, max_length=32)
    contact_name: str | None = Field(default=None, max_length=160)
    phone: str | None = Field(default=None, max_length=30)
    email: EmailStr | None = None
    is_active: bool = True

    _text = field_validator("name", "contact_name")(clean_text)
    _nit = field_validator("tax_id")(optional_nit)
    _phone = field_validator("phone")(optional_phone)
    _email = field_validator("email", mode="after")(optional_email)


class PartRead(BaseModel):
    id: uuid.UUID
    sku: str
    name: str
    kind: PartKind
    unit_cost: MoneyOut | None = Field(
        description="Solo para quien administra el inventario; null para los demás"
    )
    sale_price: MoneyOut
    tax_rate: int
    price_includes_tax: bool
    min_stock: int
    notes: str | None
    is_active: bool
    stock: int
    low_stock: bool
    assembly_category: AssemblyCategory | None = None
    specs: dict[str, Any] | None = None
    price_locked: bool = False


class PartWrite(BaseModel):
    sku: str = Field(min_length=2, max_length=40)
    name: str = Field(min_length=2, max_length=200)
    kind: PartKind = "PART"
    unit_cost: Decimal = OptionalMoney
    sale_price: Decimal = OptionalMoney
    tax_rate: TaxRate = 0
    price_includes_tax: bool = False
    min_stock: int = Field(default=0, ge=0, le=100_000)
    notes: str | None = Field(default=None, max_length=2000)
    is_active: bool = True
    assembly_category: AssemblyCategory | None = Field(
        default=None, description="Para el ensamble de PC; si se omite, no se cambia"
    )
    specs: dict[str, Any] | None = Field(
        default=None, description="Especificaciones técnicas de la categoría de ensamble"
    )
    price_locked: bool | None = Field(
        default=None,
        description="Piezas de ensamble: precio fijado a mano (si no, costo + margen); "
        "si se omite, no se cambia",
    )

    _sku = field_validator("sku")(_sku)
    _name = field_validator("name")(clean_text)
    _notes = field_validator("notes")(clean_multiline)

    @model_validator(mode="after")
    def _assembly(self) -> Self:
        if self.assembly_category is None:
            if self.specs is not None:
                raise ValueError("Las especificaciones requieren una categoría de ensamble.")
            return self
        if self.specs is None:
            raise ValueError("Indique las especificaciones técnicas de la pieza.")
        self.specs = validate_specs(self.assembly_category, self.specs)
        return self


class StockEntryLine(BaseModel):
    part_id: uuid.UUID
    quantity: int = Field(gt=0, le=100_000)
    unit_cost: Decimal = Money


class StockEntryCreate(BaseModel):
    supplier_id: uuid.UUID | None = None
    invoice_number: str | None = Field(default=None, max_length=40)
    received_on: date
    notes: str | None = Field(default=None, max_length=2000)
    lines: list[StockEntryLine] = Field(min_length=1, max_length=200)

    _invoice = field_validator("invoice_number")(clean_text)
    _notes = field_validator("notes")(clean_multiline)


class StockEntryRead(BaseModel):
    id: uuid.UUID
    supplier: str | None
    invoice_number: str | None
    received_on: date
    lines: int
    total_cost: MoneyOut


class AdjustmentCreate(BaseModel):
    """Physical count: the new quantity on the shelf, with the reason of the difference."""

    counted_quantity: int = Field(ge=0, le=1_000_000)
    reason: str = Field(min_length=3, max_length=500)

    _reason = field_validator("reason")(clean_multiline)


class MovementRead(BaseModel):
    id: uuid.UUID
    kind: Literal["IN", "OUT", "ADJUSTMENT", "RETURN"]
    quantity: int
    stock_after: int
    unit_cost: MoneyOut | None
    reference_type: str | None
    reference_id: uuid.UUID | None
    reference_label: str | None
    reason: str | None
    created_by: PersonRef | None
    created_at: datetime
