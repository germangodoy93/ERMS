import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

PasswordField = Field(min_length=1, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = PasswordField


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105 - OAuth2 token type, not a secret
    expires_at: datetime
    must_change_password: bool


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    new_password: str = PasswordField


class ChangePasswordRequest(BaseModel):
    current_password: str = PasswordField
    new_password: str = PasswordField


class OrganizationRef(BaseModel):
    id: uuid.UUID
    name: str


class RoleRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str


class MeResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    organization: OrganizationRef
    roles: list[RoleRef]
    permissions: list[str]
    must_change_password: bool
