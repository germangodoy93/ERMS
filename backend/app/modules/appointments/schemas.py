import uuid
from datetime import date, datetime, time
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.appointments.catalog import (
    LOCALITIES,
    MAX_DURATION,
    MIN_DURATION,
    AppointmentStatus,
    ConsentChannel,
    Modality,
)
from app.modules.workorders.schemas import CustomerSummary, MoneyOut, PersonRef
from app.shared.validators import clean_multiline, clean_text

Duration = Field(ge=MIN_DURATION, le=MAX_DURATION, multiple_of=5)


def _aware(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        raise ValueError("Indique la fecha y hora con zona horaria.")
    return value


def _locality(value: str | None) -> str | None:
    value = clean_text(value)
    if value is not None and value not in LOCALITIES:
        raise ValueError("Elija una localidad de la lista.")
    return value


# --- Service hours -----------------------------------------------------------------------


class HoursDay(BaseModel):
    weekday: int = Field(ge=0, le=6, description="0 = lunes … 6 = domingo")
    opens: time | None = Field(description="Vacío: no hay servicio ese día")
    closes: time | None

    @model_validator(mode="after")
    def _valid(self) -> Self:
        if (self.opens is None) != (self.closes is None):
            raise ValueError("Indique la hora de inicio y la de fin, o deje el día sin servicio.")
        if self.opens is not None and self.closes is not None and self.opens >= self.closes:
            raise ValueError("La hora de fin debe ser posterior a la de inicio.")
        return self


class HoursRead(BaseModel):
    days: list[HoursDay]
    is_default: bool = Field(description="True mientras el taller no ha cambiado el horario")


class HoursUpdate(BaseModel):
    days: list[HoursDay] = Field(min_length=7, max_length=7)

    @model_validator(mode="after")
    def _all_days(self) -> Self:
        if sorted(d.weekday for d in self.days) != list(range(7)):
            raise ValueError("Envíe los siete días de la semana, una vez cada uno.")
        return self


# --- Service catalog ---------------------------------------------------------------------


class FieldServiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    modality: Modality
    duration_minutes: int
    price: MoneyOut | None = Field(description="Vacío: el precio se da tras el diagnóstico")
    tax_rate: int
    price_includes_tax: bool
    description: str | None
    is_active: bool


class FieldServiceWrite(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    modality: Modality
    duration_minutes: int = Duration
    price: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    tax_rate: int = Field(default=0, description="0 o 19 (IVA)")
    price_includes_tax: bool = False
    description: str | None = Field(default=None, max_length=1000)
    is_active: bool = True

    _name = field_validator("name")(clean_text)
    _description = field_validator("description")(clean_multiline)

    @field_validator("tax_rate")
    @classmethod
    def _rate(cls, value: int) -> int:
        if value not in (0, 19):
            raise ValueError("El IVA debe ser 0 % o 19 %.")
        return value


# --- Appointments ------------------------------------------------------------------------


class AppointmentCreate(BaseModel):
    customer_id: uuid.UUID
    service_id: uuid.UUID
    starts_at: datetime
    duration_minutes: int | None = Field(
        default=None,
        ge=MIN_DURATION,
        le=MAX_DURATION,
        multiple_of=5,
        description="Por defecto, la duración del servicio",
    )
    technician_id: uuid.UUID | None = None
    reason: str = Field(min_length=5, max_length=2000, description="Qué necesita el cliente")
    address: str | None = Field(default=None, max_length=255)
    locality: str | None = Field(default=None, max_length=40)
    notes: str | None = Field(default=None, max_length=2000)
    overlap_reason: str | None = Field(
        default=None, max_length=500, description="Obligatorio si el técnico ya tiene otra cita"
    )
    remote_consent_channel: ConsentChannel | None = Field(
        default=None, description="Obligatorio en las citas remotas"
    )

    _texts = field_validator("reason", "notes", "overlap_reason")(clean_multiline)
    _address = field_validator("address")(clean_text)
    _locality = field_validator("locality")(_locality)
    _starts = field_validator("starts_at")(_aware)


class AppointmentUpdate(BaseModel):
    """Only the fields present are changed (reschedule, reassign, correct the data)."""

    starts_at: datetime | None = None
    duration_minutes: int | None = Field(
        default=None, ge=MIN_DURATION, le=MAX_DURATION, multiple_of=5
    )
    technician_id: uuid.UUID | None = None
    reason: str | None = Field(default=None, min_length=5, max_length=2000)
    address: str | None = Field(default=None, max_length=255)
    locality: str | None = Field(default=None, max_length=40)
    notes: str | None = Field(default=None, max_length=2000)
    overlap_reason: str | None = Field(default=None, max_length=500)

    _texts = field_validator("reason", "notes", "overlap_reason")(clean_multiline)
    _address = field_validator("address")(clean_text)
    _locality = field_validator("locality")(_locality)
    _starts = field_validator("starts_at")(_aware)


class AppointmentCancel(BaseModel):
    reason: str = Field(min_length=3, max_length=500)

    _reason = field_validator("reason")(clean_multiline)


class ServiceRef(BaseModel):
    id: uuid.UUID
    name: str
    price: MoneyOut | None
    tax_rate: int
    price_includes_tax: bool


class AppointmentRead(BaseModel):
    id: uuid.UUID
    number: str
    status: AppointmentStatus
    modality: Modality
    customer: CustomerSummary
    service: ServiceRef
    starts_at: datetime
    ends_at: datetime
    duration_minutes: int
    technician: PersonRef | None
    reason: str
    address: str | None
    locality: str | None
    notes: str | None
    overlap_reason: str | None
    remote_consent_channel: ConsentChannel | None
    remote_consent_text: str | None
    remote_consent_at: datetime | None
    cancel_reason: str | None
    cancelled_at: datetime | None
    created_by: PersonRef | None
    created_at: datetime


class HolidayRead(BaseModel):
    date: date
    name: str


class AgendaOptions(BaseModel):
    hours: list[HoursDay]
    services: list[FieldServiceRead] = Field(description="Servicios activos")
    technicians: list[PersonRef]
    localities: list[str]
    remote_access_text: str
    can_manage: bool = Field(description="El usuario puede agendar, mover y cancelar citas")
