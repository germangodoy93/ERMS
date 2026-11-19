import uuid
from datetime import datetime
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.modules.privacy.catalog import ConsentChannel, ConsentPurpose
from app.shared.identifiers import IdType, normalize_id_number
from app.shared.validators import clean_multiline, clean_text, optional_email, optional_phone


class CustomerKind(StrEnum):
    PERSON = "PERSON"
    COMPANY = "COMPANY"


class ConsentGrant(BaseModel):
    purpose: ConsentPurpose
    channel: ConsentChannel


class _CustomerFields(BaseModel):
    """Shared validation: the document type and number go together and are normalized."""

    id_type: IdType | None = None
    id_number: str | None = Field(default=None, max_length=32)

    @model_validator(mode="after")
    def _normalize_document(self) -> Self:
        if "id_type" in self.model_fields_set or "id_number" in self.model_fields_set:
            if (self.id_type is None) != (self.id_number is None):
                raise ValueError("Indique el tipo y el número de documento, o ninguno de los dos.")
            if self.id_type is not None and self.id_number is not None:
                self.id_number = normalize_id_number(self.id_type, self.id_number)
        return self


class CustomerCreate(_CustomerFields):
    kind: CustomerKind = CustomerKind.PERSON
    full_name: str = Field(min_length=2, max_length=200)
    phone: str | None = Field(default=None, max_length=30)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=2000)
    consents: list[ConsentGrant] = Field(
        min_length=1,
        description="Debe incluir DATA_PROCESSING. Las demás finalidades son opcionales.",
    )

    _text = field_validator("full_name", "address", "id_number")(clean_text)
    _notes = field_validator("notes")(clean_multiline)
    _phone = field_validator("phone")(optional_phone)
    _email = field_validator("email", mode="after")(optional_email)

    @model_validator(mode="after")
    def _rules(self) -> Self:
        if not self.phone and not self.email:
            raise ValueError("Registre al menos un teléfono o un correo electrónico.")
        purposes = [c.purpose for c in self.consents]
        if len(purposes) != len(set(purposes)):
            raise ValueError("Cada finalidad de consentimiento debe aparecer una sola vez.")
        if ConsentPurpose.DATA_PROCESSING not in purposes:
            raise ValueError(
                "Sin la autorización de tratamiento de datos no se puede registrar al cliente."
            )
        return self


class CustomerUpdate(_CustomerFields):
    """Only the fields present in the request are changed."""

    kind: CustomerKind | None = None
    full_name: str | None = Field(default=None, min_length=2, max_length=200)
    phone: str | None = Field(default=None, max_length=30)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=2000)
    is_active: bool | None = None

    _text = field_validator("full_name", "address", "id_number")(clean_text)
    _notes = field_validator("notes")(clean_multiline)
    _phone = field_validator("phone")(optional_phone)
    _email = field_validator("email", mode="after")(optional_email)


class ConsentChange(BaseModel):
    purpose: ConsentPurpose
    granted: bool
    channel: ConsentChannel


class AnonymizeRequest(BaseModel):
    channel: ConsentChannel = Field(description="Medio por el que el titular pidió la supresión")


class ConsentStatus(BaseModel):
    """Current state of one purpose (most recent record)."""

    purpose: ConsentPurpose
    granted: bool
    channel: ConsentChannel
    policy_version: int
    recorded_at: datetime


class ConsentRecordRead(ConsentStatus):
    id: uuid.UUID
    recorded_by: str | None


class CustomerListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: CustomerKind
    full_name: str
    id_type: IdType | None
    id_number: str | None
    phone: str | None
    email: str | None
    is_active: bool
    anonymized_at: datetime | None
    created_at: datetime


class CustomerRead(CustomerListItem):
    address: str | None
    notes: str | None
    updated_at: datetime
    consents: list[ConsentStatus]
    can_be_served: bool = Field(
        description="Activo, no anonimizado y con autorización de tratamiento de datos vigente"
    )
