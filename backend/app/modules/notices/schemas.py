import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.modules.notices.catalog import MAX_BODY, NoticeKind
from app.modules.workorders.catalog import Status
from app.modules.workorders.schemas import PersonRef


def _text(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("Escriba el mensaje.")
    return value


class NoticeDraft(BaseModel):
    kind: NoticeKind
    label: str
    body: str


class NoticeRead(BaseModel):
    id: uuid.UUID
    kind: NoticeKind
    label: str
    phone: str
    body: str
    prepared_by: PersonRef | None
    prepared_at: datetime


class NoticePanel(BaseModel):
    phone: str | None = Field(description="Teléfono del cliente (E.164)")
    can_whatsapp: bool
    blocked_reason: str | None = Field(description="Por qué no se puede avisar por WhatsApp")
    can_prepare: bool = Field(description="El usuario tiene permiso para preparar avisos")
    suggested: NoticeKind
    pending: bool = Field(description="El aviso sugerido todavía no se ha preparado")
    drafts: list[NoticeDraft]
    history: list[NoticeRead]


class NoticeCreate(BaseModel):
    kind: NoticeKind
    body: str = Field(min_length=1, max_length=MAX_BODY)

    _body = field_validator("body")(_text)


class PreparedNotice(BaseModel):
    notice: NoticeRead
    url: str = Field(description="Enlace wa.me con el mensaje (abrir o mostrar como QR)")


class PendingNotice(BaseModel):
    work_order_id: uuid.UUID
    number: str
    customer_name: str
    status: Status
    kind: NoticeKind
    label: str
    since: datetime = Field(description="Desde cuándo está pendiente el aviso")
    can_whatsapp: bool


class TemplateRead(BaseModel):
    kind: NoticeKind
    label: str
    body: str
    default_body: str
    is_default: bool


class PlaceholderRead(BaseModel):
    name: str
    description: str


class TemplatesRead(BaseModel):
    templates: list[TemplateRead]
    placeholders: list[PlaceholderRead]
    reminder_days: int


class TemplateUpdate(BaseModel):
    body: str = Field(min_length=1, max_length=MAX_BODY)

    _body = field_validator("body")(_text)
