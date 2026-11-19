"""Audit trail. `record` joins the caller's transaction: if the change rolls back, so does
its audit entry; if it commits, the entry is guaranteed to exist."""

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.audit.models import AuditLog
from app.modules.audit.schemas import AuditActor, AuditLogFilters, AuditLogRead
from app.modules.users.models import User
from app.shared.context import RequestContext
from app.shared.pagination import Page, PageParams


class AuditService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def record(
        self,
        action: str,
        *,
        entity_type: str,
        entity_id: uuid.UUID | str | None,
        organization_id: uuid.UUID | None,
        actor_user_id: uuid.UUID | None,
        context: RequestContext | None = None,
        changes: dict[str, Any] | None = None,
    ) -> None:
        self._session.add(
            AuditLog(
                organization_id=organization_id,
                actor_user_id=actor_user_id,
                action=action,
                entity_type=entity_type,
                entity_id=str(entity_id) if entity_id is not None else None,
                changes=changes,
                ip_address=context.ip_address if context else None,
                user_agent=context.user_agent if context else None,
            )
        )

    def search(
        self, organization_id: uuid.UUID, filters: AuditLogFilters, params: PageParams
    ) -> Page[AuditLogRead]:
        conditions = [AuditLog.organization_id == organization_id]
        if filters.action:
            conditions.append(AuditLog.action == filters.action)
        if filters.entity_type:
            conditions.append(AuditLog.entity_type == filters.entity_type)
        if filters.entity_id:
            conditions.append(AuditLog.entity_id == filters.entity_id)
        if filters.actor_user_id:
            conditions.append(AuditLog.actor_user_id == filters.actor_user_id)
        if filters.date_from:
            conditions.append(AuditLog.created_at >= filters.date_from)
        if filters.date_to:
            conditions.append(AuditLog.created_at <= filters.date_to)

        total = self._session.scalar(select(func.count()).select_from(AuditLog).where(*conditions))
        rows = self._session.execute(
            select(AuditLog, User)
            .outerjoin(User, User.id == AuditLog.actor_user_id)
            .where(*conditions)
            .order_by(AuditLog.created_at.desc(), AuditLog.id)
            .offset(params.offset)
            .limit(params.size)
        ).all()

        items = [
            AuditLogRead(
                id=log.id,
                action=log.action,
                entity_type=log.entity_type,
                entity_id=log.entity_id,
                changes=log.changes,
                actor=AuditActor.model_validate(actor) if actor else None,
                ip_address=log.ip_address,
                created_at=log.created_at,
            )
            for log, actor in rows
        ]
        return Page(items=items, total=total or 0, page=params.page, size=params.size)
