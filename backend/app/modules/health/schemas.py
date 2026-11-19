from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ComponentStatus(StrEnum):
    OK = "ok"
    ERROR = "error"
    NOT_CONFIGURED = "not_configured"


class OverallStatus(StrEnum):
    OK = "ok"
    UNAVAILABLE = "unavailable"


class ComponentHealth(BaseModel):
    name: str = Field(examples=["database"])
    status: ComponentStatus
    critical: bool = Field(description="If true, an error makes the service not ready.")
    latency_ms: float | None = Field(default=None, ge=0)
    detail: str | None = Field(default=None, examples=["revision 0001_initial (head)"])


class LivenessResponse(BaseModel):
    status: OverallStatus = OverallStatus.OK
    version: str


class ReadinessResponse(BaseModel):
    status: OverallStatus
    version: str
    environment: str
    checked_at: datetime
    components: list[ComponentHealth]
