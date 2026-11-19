import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.modules.audit.schemas import AuditLogFilters, AuditLogRead
from app.modules.audit.service import AuditService
from app.modules.auth.dependencies import DbSession, require_permissions
from app.modules.roles.catalog import Perm
from app.modules.users.models import User
from app.shared.pagination import Page, PageParams, page_params

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("", response_model=Page[AuditLogRead], summary="Consultar auditoría")
def list_audit_logs(
    actor: Annotated[User, Depends(require_permissions(Perm.AUDIT_READ))],
    session: DbSession,
    params: Annotated[PageParams, Depends(page_params)],
    action: Annotated[str | None, Query(max_length=64)] = None,
    entity_type: Annotated[str | None, Query(max_length=64)] = None,
    entity_id: Annotated[str | None, Query(max_length=64)] = None,
    actor_user_id: uuid.UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> Page[AuditLogRead]:
    filters = AuditLogFilters(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_user_id=actor_user_id,
        date_from=date_from,
        date_to=date_to,
    )
    return AuditService(session).search(actor.organization_id, filters, params)
