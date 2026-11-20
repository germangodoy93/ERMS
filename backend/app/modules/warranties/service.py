"""Warranty claims.

- The warranty is created when a repaired order is delivered (WorkOrderService).
- A claim is opened from the ORIGINAL delivered order while its warranty is active: it creates
  a new work order for the same customer and device, without diagnostic fee, linked by
  `warranty_of_id`. The claim order may be quoted at $0.
- The claim is decided (accepted or rejected, always with a written resolution).
"""

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import BusinessRuleError, NotFoundError, PermissionDeniedError
from app.core.storage import Storage
from app.modules.audit.service import AuditService
from app.modules.roles.catalog import Perm
from app.modules.users.models import User
from app.modules.warranties.models import Warranty, WarrantyClaim
from app.modules.warranties.schemas import (
    ClaimCreate,
    ClaimDecision,
    ClaimRead,
    WarrantyOverview,
    WarrantyRead,
)
from app.modules.workorders.catalog import Status
from app.modules.workorders.models import WorkOrder
from app.modules.workorders.schemas import PersonRef, WorkOrderCreate, WorkOrderRead
from app.modules.workorders.service import WorkOrderService
from app.shared.context import BOGOTA, RequestContext, utcnow


def today() -> date:
    return utcnow().astimezone(BOGOTA).date()


class WarrantyService:
    def __init__(self, session: Session, settings: Settings, storage: Storage) -> None:
        self._session = session
        self._orders = WorkOrderService(session, settings, storage)
        self._audit = AuditService(session)

    def overview(self, actor: User, order_id: uuid.UUID) -> WarrantyOverview:
        order = self._orders.get(actor, order_id)
        original = self._orders.get(actor, order.warranty_of_id) if order.warranty_of_id else order
        warranty = self._warranty_of(original)
        claims = (
            list(
                self._session.scalars(
                    select(WarrantyClaim)
                    .where(WarrantyClaim.warranty_id == warranty.id)
                    .order_by(WarrantyClaim.created_at.desc())
                )
            )
            if warranty
            else []
        )
        perms = actor.permission_codes
        return WarrantyOverview(
            warranty=self._read(warranty, original) if warranty else None,
            claims=[self._claim_read(c) for c in claims],
            is_claim_order=order.warranty_of_id is not None,
            can_claim=bool(
                warranty
                and order.warranty_of_id is None
                and warranty.ends_on >= today()
                and Perm.WARRANTIES_MANAGE in perms
                and Perm.WORK_ORDERS_CREATE in perms
            ),
            can_decide=Perm.WARRANTIES_MANAGE in perms and any(c.status == "OPEN" for c in claims),
        )

    def open_claim(
        self, actor: User, order_id: uuid.UUID, data: ClaimCreate, context: RequestContext
    ) -> WorkOrderRead:
        self._require(actor, Perm.WARRANTIES_MANAGE)
        self._require(actor, Perm.WORK_ORDERS_CREATE)
        original = self._orders.get(actor, order_id, for_update=True)
        if original.warranty_of_id is not None:
            raise BusinessRuleError("Abra el reclamo desde la orden original.")
        if Status(original.status) is not Status.ENTREGADO:
            raise BusinessRuleError("Solo las órdenes entregadas tienen garantía.")
        warranty = self._warranty_of(original)
        if warranty is None:
            raise BusinessRuleError("Esta orden no tiene garantía (no se reparó).")
        if warranty.ends_on < today():
            raise BusinessRuleError(f"La garantía venció el {warranty.ends_on:%d/%m/%Y}.")
        claim_order = self._orders.create(
            actor,
            WorkOrderCreate(
                customer_id=original.customer_id,
                device_id=original.device_id,
                reported_issue=data.reported_issue,
                physical_condition=data.physical_condition,
                accessories=data.accessories,
                unlock_method=data.unlock_method,
                notes=f"Reclamo de garantía de la orden {original.number}.",
            ),
            context,
        )
        created = self._orders.get(actor, claim_order.id)
        created.warranty_of_id = original.id
        claim = WarrantyClaim(
            organization_id=original.organization_id,
            warranty_id=warranty.id,
            claim_order_id=created.id,
            reported_issue=data.reported_issue,
            status="OPEN",
            created_by_id=actor.id,
        )
        self._session.add(claim)
        self._session.flush()
        self._audit.record(
            "warranty.claim_opened",
            entity_type="work_order",
            entity_id=original.id,
            organization_id=actor.organization_id,
            actor_user_id=actor.id,
            context=context,
            changes={"claim_order": created.number},
        )
        return self._orders.read(actor, created.id)

    def decide(
        self,
        actor: User,
        order_id: uuid.UUID,
        claim_id: uuid.UUID,
        data: ClaimDecision,
        context: RequestContext,
    ) -> ClaimRead:
        self._require(actor, Perm.WARRANTIES_MANAGE)
        order = self._orders.get(actor, order_id)
        original_id = order.warranty_of_id or order.id
        claim = self._session.scalar(
            select(WarrantyClaim)
            .join(Warranty, Warranty.id == WarrantyClaim.warranty_id)
            .where(WarrantyClaim.id == claim_id, Warranty.work_order_id == original_id)
            .with_for_update(of=WarrantyClaim)
        )
        if claim is None:
            raise NotFoundError("El reclamo no existe.")
        if claim.status != "OPEN":
            raise BusinessRuleError("El reclamo ya fue resuelto.")
        claim.status = "ACCEPTED" if data.accepted else "REJECTED"
        claim.resolution = data.resolution
        claim.decided_by_id = actor.id
        claim.decided_at = utcnow()
        self._session.flush()
        self._audit.record(
            "warranty.claim_decided",
            entity_type="work_order",
            entity_id=original_id,
            organization_id=actor.organization_id,
            actor_user_id=actor.id,
            context=context,
            changes={"status": claim.status},
        )
        return self._claim_read(claim)

    # --- Helpers ------------------------------------------------------------------------

    def _warranty_of(self, order: WorkOrder) -> Warranty | None:
        return self._session.scalar(select(Warranty).where(Warranty.work_order_id == order.id))

    @staticmethod
    def _require(actor: User, permission: Perm) -> None:
        if permission not in actor.permission_codes:
            raise PermissionDeniedError("No tiene permisos para gestionar garantías.")

    @staticmethod
    def _read(warranty: Warranty, order: WorkOrder) -> WarrantyRead:
        return WarrantyRead(
            id=warranty.id,
            work_order_id=order.id,
            work_order_number=order.number,
            days=warranty.days,
            starts_on=warranty.starts_on,
            ends_on=warranty.ends_on,
            active=warranty.ends_on >= today(),
        )

    def _claim_read(self, claim: WarrantyClaim) -> ClaimRead:
        number = self._session.scalar(
            select(WorkOrder.number).where(WorkOrder.id == claim.claim_order_id)
        )
        decider = self._session.get(User, claim.decided_by_id) if claim.decided_by_id else None
        return ClaimRead(
            id=claim.id,
            claim_order_id=claim.claim_order_id,
            claim_order_number=number or "",
            reported_issue=claim.reported_issue,
            status=claim.status,
            resolution=claim.resolution,
            decided_by=PersonRef(id=decider.id, full_name=decider.full_name) if decider else None,
            decided_at=claim.decided_at,
            created_at=claim.created_at,
        )
