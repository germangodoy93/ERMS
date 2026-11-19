import uuid

from pydantic import BaseModel, Field


class PermissionRead(BaseModel):
    code: str
    description: str


class RoleRead(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    is_system: bool
    permissions: list[str]


class RolePermissionsUpdate(BaseModel):
    permissions: list[str] = Field(description="Códigos de permiso, p. ej. 'users:read'")
