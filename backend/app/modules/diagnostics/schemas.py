import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.modules.diagnostics.catalog import Result, Source
from app.modules.workorders.schemas import PersonRef
from app.shared.validators import clean_multiline

ManualResult = Literal["OK", "WARNING", "FAIL", "NOT_TESTED", "NOT_SUPPORTED"]


class TestResultRead(BaseModel):
    test_code: str
    name: str
    component: str
    automated: bool
    result: Result | None = Field(description="null mientras no se ha registrado")
    observation: str | None
    evidence: dict[str, Any] | None
    source: Source | None
    recorded_by: PersonRef | None
    recorded_at: datetime | None


class DiagnosticRead(BaseModel):
    session_id: uuid.UUID | None
    state: Literal["NOT_STARTED", "OPEN", "CLOSED"]
    editable: bool = Field(description="El usuario puede registrar resultados ahora")
    agent_available: bool = Field(
        description="Computador, orden en diagnóstico y autorización DIAGNOSTIC_AGENT vigente"
    )
    agent_unavailable_reason: str | None
    agent_download_url: str
    conclusion: str | None
    recommendation: str | None
    closed_at: datetime | None
    closed_by: PersonRef | None
    agent_version: str | None
    agent_elevated: bool | None
    agent_reported_at: datetime | None
    results: list[TestResultRead]


class ResultInput(BaseModel):
    test_code: str = Field(max_length=40)
    result: ManualResult
    observation: str | None = Field(default=None, max_length=2000)

    _observation = field_validator("observation")(clean_multiline)


class ResultsUpdate(BaseModel):
    results: list[ResultInput] = Field(min_length=1, max_length=60)


class CloseRequest(BaseModel):
    conclusion: str = Field(min_length=5, max_length=4000)
    recommendation: str | None = Field(default=None, max_length=4000)

    _texts = field_validator("conclusion", "recommendation")(clean_multiline)


class PairingCreated(BaseModel):
    code: str = Field(description="Código de un solo uso que se escribe en el agente")
    expires_at: datetime
    download_url: str
