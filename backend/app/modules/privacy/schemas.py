import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.privacy.catalog import ConsentPurpose


class PrivacyPolicyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    version: int
    content: str
    published_at: datetime


class PrivacyPolicyVersion(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    version: int
    published_at: datetime


class CurrentPrivacyPolicy(BaseModel):
    """What reception needs: the policy in force and the authorization texts to show."""

    policy: PrivacyPolicyRead | None
    authorizations: dict[ConsentPurpose, str]


class PrivacyPolicyDraft(BaseModel):
    content: str
    missing_fields: list[str] = Field(
        description="Datos del taller que faltan para poder publicar la política"
    )


class PrivacyPolicyPublish(BaseModel):
    content: str = Field(min_length=200, max_length=50_000)
