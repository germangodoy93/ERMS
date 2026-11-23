import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    field_validator,
    model_validator,
)

from app.modules.workorders.catalog import Accessory, PaymentMethod, Priority, Status, UnlockMethod
from app.shared.validators import clean_multiline, clean_text

Money = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=2)
# API contract: money travels as a decimal string with two places ("150000.00").
MoneyOut = Annotated[
    Decimal, PlainSerializer(lambda v: f"{v.quantize(Decimal('0.01'))}", return_type=str)
]


# --- Reception terms ---------------------------------------------------------------------


class ReceptionTermsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    version: int
    content: str
    published_at: datetime


class CurrentReceptionTerms(BaseModel):
    terms: ReceptionTermsRead | None
    template: str = Field(description="Texto base sugerido para la primera versión")


class ReceptionTermsPublish(BaseModel):
    content: str = Field(min_length=100, max_length=20_000)


# --- Work orders -------------------------------------------------------------------------


class AccessoryItem(BaseModel):
    code: Accessory
    detail: str | None = Field(default=None, max_length=120)

    _detail = field_validator("detail")(clean_text)

    @model_validator(mode="after")
    def _other_needs_detail(self) -> Self:
        if self.code is Accessory.OTHER and not self.detail:
            raise ValueError("Describa el accesorio marcado como 'Otro'.")
        return self


class WorkOrderCreate(BaseModel):
    customer_id: uuid.UUID
    device_id: uuid.UUID
    reported_issue: str = Field(min_length=5, max_length=4000)
    physical_condition: str = Field(min_length=3, max_length=4000)
    accessories: list[AccessoryItem] = Field(default_factory=list, max_length=20)
    unlock_method: UnlockMethod
    priority: Priority = Priority.NORMAL
    estimated_delivery_date: date | None = None
    diagnostic_fee: Decimal = Money
    advance_amount: Decimal = Money
    advance_method: PaymentMethod | None = None
    notes: str | None = Field(default=None, max_length=4000)
    assigned_technician_id: uuid.UUID | None = None

    _texts = field_validator("reported_issue", "physical_condition", "notes")(clean_multiline)

    @model_validator(mode="after")
    def _rules(self) -> Self:
        if self.advance_amount > 0 and self.advance_method is None:
            raise ValueError("Indique el medio de pago del anticipo.")
        if self.advance_amount == 0:
            self.advance_method = None
        codes = [a.code for a in self.accessories if a.code is not Accessory.OTHER]
        if len(codes) != len(set(codes)):
            raise ValueError("Cada accesorio debe aparecer una sola vez.")
        return self


class WorkOrderUpdate(BaseModel):
    """Reception data that can be corrected while the order is open. Amounts are fixed once
    the act is printed: corrections go in the notes."""

    reported_issue: str | None = Field(default=None, min_length=5, max_length=4000)
    physical_condition: str | None = Field(default=None, min_length=3, max_length=4000)
    priority: Priority | None = None
    estimated_delivery_date: date | None = None
    notes: str | None = Field(default=None, max_length=4000)

    _texts = field_validator("reported_issue", "physical_condition", "notes")(clean_multiline)


class StatusChange(BaseModel):
    status: Status
    reason: str | None = Field(default=None, max_length=2000)

    _reason = field_validator("reason")(clean_multiline)


class DeliveryRequest(BaseModel):
    """Who picked up the device. When it is not the customer, name and document are required."""

    picked_up_by_customer: bool
    name: str | None = Field(default=None, max_length=200)
    document: str | None = Field(default=None, max_length=40)
    notes: str | None = Field(default=None, max_length=2000)
    balance_reason: str | None = Field(
        default=None,
        max_length=500,
        description="Obligatorio con saldo pendiente (requiere work_orders:deliver_with_balance)",
    )
    warranty_days: int | None = Field(
        default=None, ge=1, le=3650, description="Días de garantía; por defecto, los del taller"
    )

    _texts = field_validator("name", "document")(clean_text)
    _notes = field_validator("notes", "balance_reason")(clean_multiline)

    @model_validator(mode="after")
    def _third_party(self) -> Self:
        if not self.picked_up_by_customer and not (self.name and self.document):
            raise ValueError("Registre el nombre y el documento de quien retira el equipo.")
        return self


class Assignment(BaseModel):
    technician_id: uuid.UUID | None


class PersonRef(BaseModel):
    id: uuid.UUID
    full_name: str


class CustomerSummary(BaseModel):
    id: uuid.UUID
    full_name: str
    phone: str | None
    id_type: str | None
    id_number: str | None


class DeviceSummary(BaseModel):
    id: uuid.UUID
    category: str
    manufacturer: str
    model: str
    imei: str | None
    serial_number: str | None


OrderKind = Literal["SERVICE", "ASSEMBLY"]


class WorkOrderListItem(BaseModel):
    id: uuid.UUID
    number: str
    status: Status
    priority: Priority
    received_at: datetime
    estimated_delivery_date: date | None
    customer: CustomerSummary
    device: DeviceSummary
    assigned_technician: PersonRef | None
    kind: OrderKind = Field(
        default="SERVICE", description="SERVICE = reparación; ASSEMBLY = PC a la medida"
    )


class StatusHistoryItem(BaseModel):
    from_status: Status | None
    to_status: Status
    reason: str | None
    changed_by: PersonRef | None
    changed_at: datetime


class WorkOrderRead(WorkOrderListItem):
    branch: str
    reported_issue: str
    physical_condition: str
    accessories: list[AccessoryItem]
    unlock_method: UnlockMethod
    diagnostic_fee: MoneyOut
    advance_amount: MoneyOut
    advance_method: PaymentMethod | None
    notes: str | None
    terms_version: int
    received_by: PersonRef | None
    delivered_at: datetime | None
    delivered_to_name: str | None
    delivered_to_document: str | None
    history: list[StatusHistoryItem]
    allowed_transitions: list[Status] = Field(
        description="Estados a los que el usuario actual puede llevar la orden"
    )
    customer_allows_photos: bool
    updated_at: datetime


class PhotoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    file_name: str
    size_bytes: int
    created_at: datetime


class PhotoList(BaseModel):
    demo: bool = Field(
        description="True mientras las fotos se guardan en almacenamiento de demostración"
    )
    max_photos: int
    items: list[PhotoRead]
