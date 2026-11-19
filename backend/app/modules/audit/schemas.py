import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditActor(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str


class AuditLogRead(BaseModel):
    id: uuid.UUID
    action: str
    entity_type: str
    entity_id: str | None
    changes: dict[str, Any] | None
    actor: AuditActor | None
    ip_address: str | None
    created_at: datetime


class AuditLogFilters(BaseModel):
    action: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    actor_user_id: uuid.UUID | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
