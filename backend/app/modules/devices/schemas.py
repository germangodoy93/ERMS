import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.shared.validators import clean_multiline, clean_text, optional_imei, optional_serial

MIN_RELEASE_YEAR = 1980
MAX_RELEASE_YEAR = 2100


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str


class ManufacturerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    is_active: bool


class ManufacturerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)

    _name = field_validator("name")(clean_text)


class ManufacturerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    is_active: bool | None = None

    _name = field_validator("name")(clean_text)


class DeviceModelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    release_year: int | None
    is_active: bool
    manufacturer: ManufacturerRead
    category: CategoryRead


class DeviceModelCreate(BaseModel):
    manufacturer_id: uuid.UUID
    category_code: str = Field(max_length=20)
    name: str = Field(min_length=1, max_length=120)
    release_year: int | None = Field(default=None, ge=MIN_RELEASE_YEAR, le=MAX_RELEASE_YEAR)

    _name = field_validator("name")(clean_text)


class DeviceModelUpdate(BaseModel):
    category_code: str | None = Field(default=None, max_length=20)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    release_year: int | None = Field(default=None, ge=MIN_RELEASE_YEAR, le=MAX_RELEASE_YEAR)
    is_active: bool | None = None

    _name = field_validator("name")(clean_text)


class _DeviceFields(BaseModel):
    _serial = field_validator("serial_number", check_fields=False)(optional_serial)
    _imei = field_validator("imei", check_fields=False)(optional_imei)
    _text = field_validator("operating_system", "storage", "color", check_fields=False)(clean_text)
    _notes = field_validator("notes", check_fields=False)(clean_multiline)


class DeviceCreate(_DeviceFields):
    model_id: uuid.UUID
    serial_number: str | None = Field(default=None, max_length=64)
    imei: str | None = Field(default=None, max_length=30)
    operating_system: str | None = Field(default=None, max_length=60)
    storage: str | None = Field(default=None, max_length=40, description="Ej. 256 GB")
    color: str | None = Field(default=None, max_length=40)
    notes: str | None = Field(default=None, max_length=2000)


class DeviceUpdate(_DeviceFields):
    """Only the fields present in the request are changed. The owner cannot be changed."""

    model_id: uuid.UUID | None = None
    serial_number: str | None = Field(default=None, max_length=64)
    imei: str | None = Field(default=None, max_length=30)
    operating_system: str | None = Field(default=None, max_length=60)
    storage: str | None = Field(default=None, max_length=40)
    color: str | None = Field(default=None, max_length=40)
    notes: str | None = Field(default=None, max_length=2000)
    is_active: bool | None = None


class DeviceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_id: uuid.UUID
    model: DeviceModelRead
    serial_number: str | None
    imei: str | None
    operating_system: str | None
    storage: str | None
    color: str | None
    notes: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class DeviceSearchItem(DeviceRead):
    customer_name: str
