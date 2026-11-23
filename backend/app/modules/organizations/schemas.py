import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.shared.validators import clean_text, optional_email, optional_nit, optional_phone


class OrganizationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    legal_name: str | None
    tax_id: str | None
    address: str | None
    city: str | None
    phone: str | None
    email: str | None
    warranty_days: int
    assembly_bottleneck_gap: int
    assembly_min_ram_gb: int


class OrganizationUpdate(BaseModel):
    """Only the fields present in the request are changed. The slug is immutable."""

    name: str | None = Field(default=None, min_length=2, max_length=200)
    legal_name: str | None = Field(default=None, max_length=200)
    tax_id: str | None = Field(default=None, max_length=32, description="NIT, con o sin DV")
    address: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=80)
    phone: str | None = Field(default=None, max_length=30)
    email: EmailStr | None = None
    warranty_days: int | None = Field(default=None, ge=1, le=3650)
    assembly_bottleneck_gap: int | None = Field(
        default=None,
        ge=5,
        le=100,
        description="Diferencia de índices que se avisa como cuello de botella",
    )
    assembly_min_ram_gb: int | None = Field(
        default=None, ge=4, le=256, description="RAM mínima recomendada para diseño y gaming"
    )

    _text = field_validator("name", "legal_name", "address", "city")(clean_text)
    _nit = field_validator("tax_id")(optional_nit)
    _phone = field_validator("phone")(optional_phone)
    _email = field_validator("email", mode="after")(optional_email)
