import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.modules.auth.schemas import RoleRef


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = " ".join(value.split())
    return value or None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    phone: str | None
    is_active: bool
    must_change_password: bool
    roles: list[RoleRef]
    last_login_at: datetime | None
    locked_until: datetime | None
    created_at: datetime
    updated_at: datetime


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=160)
    phone: str | None = Field(default=None, max_length=30)
    temporary_password: str = Field(min_length=1, max_length=128)
    role_ids: list[uuid.UUID] = Field(min_length=1)

    _clean_name = field_validator("full_name", "phone")(_clean)


class UserUpdate(BaseModel):
    """Only the fields present in the request are changed."""

    email: EmailStr | None = None
    full_name: str | None = Field(default=None, min_length=2, max_length=160)
    phone: str | None = Field(default=None, max_length=30)
    is_active: bool | None = None

    _clean_name = field_validator("full_name", "phone")(_clean)


class UserRolesUpdate(BaseModel):
    role_ids: list[uuid.UUID] = Field(min_length=1)


class TemporaryPasswordSet(BaseModel):
    temporary_password: str = Field(min_length=1, max_length=128)
