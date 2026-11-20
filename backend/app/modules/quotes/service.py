"""Quotations of a work order.

Rules (Sprint 5):
- Drafts are edited with the order in COTIZACION or PENDIENTE_AUTORIZACION (a new version when
  the customer asks for changes). One draft at a time; a new draft copies the last version.
- IVA per item: 19 % or none; the price may be entered with or without IVA.
- Discounts above 10 % per item require `quotes:discount`; who authorized is recorded.
- Sending (customer-facing, `work_orders:deliver`) moves the order to PENDIENTE_AUTORIZACION,
  sets validity to 15 days and supersedes the previously sent version.
- The customer's answer moves the order to APROBADO or COTIZACION_RECHAZADA (reason required).
  An expired quotation cannot be accepted: send a new version.
- If accepted, the diagnostic fee is included in the repair price (it is not added).
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import BusinessRuleError, NotFoundError, PermissionDeniedError
from app.core.storage import Storage
from app.modules.audit.service import AuditService
from app.modules.inventory.models import Part
from app.modules.inventory.service import InventoryService
from app.modules.quotes.models import Quotation, QuotationItem
from app.modules.quotes.schemas import (
    QuoteItemRead,
    QuoteOverview,
    QuoteRead,
    QuoteSave,
    RespondRequest,
)
from app.modules.roles.catalog import Perm
from app.modules.users.models import User
from app.modules.workorders.catalog import Status
from app.modules.workorders.models import WorkOrder
from app.modules.workorders.schemas import PersonRef
from app.modules.workorders.service import WorkOrderService
from app.shared.context import BOGOTA, RequestContext, utcnow
from app.shared.money import ZERO, line_amounts

VALIDITY_DAYS = 15
DISCOUNT_LIMIT = Decimal("10")
EDITABLE_ORDER_STATES = frozenset({Status.COTIZACION, Status.PENDIENTE_AUTORIZACION})


def today_bogota() -> date:
    return utcnow().astimezone(BOGOTA).date()


class QuoteService:
    def __init__(self, session: Session, settings: Settings, storage: Storage) -> None:
        self._session = session
        self._orders = WorkOrderService(session, settings, storage)
        self._inventory = InventoryService(session)
        self._audit = AuditService(session)

    # --- Queries ------------------------------------------------------------------------

    def overview(self, actor: User, order_id: uuid.UUID) -> QuoteOverview:
        order = self._orders.get(actor, order_id)
        quotes = list(
            self._session.scalars(
                select(Quotation)
                .where(Quotation.work_order_id == order.id)
                .order_by(Quotation.version.desc())
            )
        )
        perms = actor.permission_codes
        open_state = Status(order.status) in EDITABLE_ORDER_STATES
        return QuoteOverview(
            diagnostic_fee=order.diagnostic_fee,
            quotes=[self._read(actor, q) for q in quotes],
            can_edit=open_state and Perm.QUOTES_MANAGE in perms,
            can_send=open_state and Perm.WORK_ORDERS_DELIVER in perms,
            can_respond=Status(order.status) is Status.PENDIENTE_AUTORIZACION
            and Perm.WORK_ORDERS_DELIVER in perms,
            max_discount_percent=100 if Perm.QUOTES_DISCOUNT in perms else int(DISCOUNT_LIMIT),
        )

    def get(self, actor: User, order_id: uuid.UUID, quote_id: uuid.UUID) -> Quotation:
        quote = self._session.scalar(
            select(Quotation).where(
                Quotation.id == quote_id,
                Quotation.work_order_id == order_id,
                Quotation.organization_id == actor.organization_id,
            )
        )
        if quote is None:
            raise NotFoundError("La cotización no existe.")
        return quote

    def read(self, actor: User, order_id: uuid.UUID, quote_id: uuid.UUID) -> QuoteRead:
        return self._read(actor, self.get(actor, order_id, quote_id))

    # --- Commands -----------------------------------------------------------------------

    def create_draft(self, actor: User, order_id: uuid.UUID, context: RequestContext) -> QuoteRead:
        order = self._orders.get(actor, order_id, for_update=True)
        self._ensure_editable(order)
        existing = list(
            self._session.scalars(
                select(Quotation)
                .where(Quotation.work_order_id == order.id)
                .order_by(Quotation.version.desc())
            )
        )
        if any(q.status == "DRAFT" for q in existing):
            raise BusinessRuleError("Ya hay un borrador de cotización para esta orden.")
        if any(q.status == "ACCEPTED" for q in existing):
            raise BusinessRuleError("La orden ya tiene una cotización aceptada.")
        previous = existing[0] if existing else None
        quote = Quotation(
            organization_id=order.organization_id,
            work_order_id=order.id,
            version=(previous.version if previous else 0) + 1,
            status="DRAFT",
            notes=previous.notes if previous else None,
            created_by_id=actor.id,
            subtotal=ZERO,
            discount_total=ZERO,
            tax_total=ZERO,
            total=ZERO,
        )
        if previous:
            quote.items = [
                QuotationItem(
                    position=i.position,
                    kind=i.kind,
                    part_id=i.part_id,
                    description=i.description,
                    quantity=i.quantity,
                    unit_price=i.unit_price,
                    discount_percent=i.discount_percent,
                    tax_rate=i.tax_rate,
                    price_includes_tax=i.price_includes_tax,
                    discount_amount=i.discount_amount,
                    base_amount=i.base_amount,
                    tax_amount=i.tax_amount,
                    total_amount=i.total_amount,
                )
                for i in previous.items
            ]
            self._totals(quote)
            quote.discount_authorized_by_id = previous.discount_authorized_by_id
        self._session.add(quote)
        self._session.flush()
        self._record(actor, context, "quote.created", order, {"version": quote.version})
        return self._read(actor, quote)

    def save(
        self,
        actor: User,
        order_id: uuid.UUID,
        quote_id: uuid.UUID,
        data: QuoteSave,
        context: RequestContext,
    ) -> QuoteRead:
        order = self._orders.get(actor, order_id, for_update=True)
        self._ensure_editable(order)
        quote = self.get(actor, order.id, quote_id)
        if quote.status != "DRAFT":
            raise BusinessRuleError("Solo se edita una cotización en borrador.")
        over_limit = any(i.discount_percent > DISCOUNT_LIMIT for i in data.items)
        if over_limit and Perm.QUOTES_DISCOUNT not in actor.permission_codes:
            raise PermissionDeniedError(
                "Los descuentos mayores al 10 % los autoriza un supervisor o administrador."
            )
        items: list[QuotationItem] = []
        for position, item in enumerate(data.items, start=1):
            part: Part | None = None
            if item.part_id is not None:
                part = self._inventory.get_part(actor, item.part_id)
            rate = Decimal("19") if item.apply_tax else Decimal("0")
            amounts = line_amounts(
                item.quantity,
                item.unit_price,
                item.discount_percent,
                rate,
                price_includes_tax=item.price_includes_tax,
            )
            items.append(
                QuotationItem(
                    position=position,
                    kind=item.kind,
                    part_id=part.id if part else None,
                    description=item.description or (part.name if part else ""),
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    discount_percent=item.discount_percent,
                    tax_rate=rate,
                    price_includes_tax=item.price_includes_tax,
                    discount_amount=amounts.discount,
                    base_amount=amounts.base,
                    tax_amount=amounts.tax,
                    total_amount=amounts.total,
                )
            )
        quote.items = items
        quote.notes = data.notes
        quote.discount_authorized_by_id = actor.id if over_limit else None
        self._totals(quote)
        self._session.flush()
        self._record(
            actor,
            context,
            "quote.saved",
            order,
            {
                "version": quote.version,
                "total": str(quote.total),
                "items": len(items),
            },
        )
        return self._read(actor, quote)

    def discard(
        self, actor: User, order_id: uuid.UUID, quote_id: uuid.UUID, context: RequestContext
    ) -> None:
        order = self._orders.get(actor, order_id, for_update=True)
        quote = self.get(actor, order.id, quote_id)
        if quote.status != "DRAFT":
            raise BusinessRuleError("Solo se descarta una cotización en borrador.")
        self._session.delete(quote)
        self._session.flush()
        self._record(actor, context, "quote.discarded", order, {"version": quote.version})

    def send(
        self, actor: User, order_id: uuid.UUID, quote_id: uuid.UUID, context: RequestContext
    ) -> QuoteRead:
        self._require(actor, Perm.WORK_ORDERS_DELIVER, "enviar cotizaciones al cliente")
        order = self._orders.get(actor, order_id, for_update=True)
        self._ensure_editable(order)
        quote = self.get(actor, order.id, quote_id)
        if quote.status != "DRAFT":
            raise BusinessRuleError("Solo se envía una cotización en borrador.")
        if not quote.items or quote.total <= 0:
            raise BusinessRuleError("La cotización no tiene ítems con valor.")
        for previous in self._session.scalars(
            select(Quotation).where(Quotation.work_order_id == order.id, Quotation.status == "SENT")
        ):
            previous.status = "SUPERSEDED"
        quote.status = "SENT"
        quote.sent_at = utcnow()
        quote.sent_by_id = actor.id
        quote.valid_until = today_bogota() + timedelta(days=VALIDITY_DAYS)
        if Status(order.status) is Status.COTIZACION:
            self._orders.transition(actor, order, Status.PENDIENTE_AUTORIZACION, None, context)
        self._session.flush()
        self._record(
            actor,
            context,
            "quote.sent",
            order,
            {
                "version": quote.version,
                "total": str(quote.total),
            },
        )
        return self._read(actor, quote)

    def respond(
        self,
        actor: User,
        order_id: uuid.UUID,
        quote_id: uuid.UUID,
        data: RespondRequest,
        context: RequestContext,
    ) -> QuoteRead:
        self._require(actor, Perm.WORK_ORDERS_DELIVER, "registrar la respuesta del cliente")
        order = self._orders.get(actor, order_id, for_update=True)
        quote = self.get(actor, order.id, quote_id)
        if quote.status != "SENT":
            raise BusinessRuleError("Solo se responde la cotización enviada vigente.")
        if data.accepted and quote.valid_until and quote.valid_until < today_bogota():
            raise BusinessRuleError("La cotización está vencida. Cree y envíe una nueva versión.")
        if not data.accepted and not data.reason:
            raise BusinessRuleError("Indique por qué el cliente rechazó la cotización.")
        quote.status = "ACCEPTED" if data.accepted else "REJECTED"
        quote.responded_at = utcnow()
        quote.responded_by_id = actor.id
        quote.response_channel = data.channel
        target = Status.APROBADO if data.accepted else Status.COTIZACION_RECHAZADA
        self._orders.transition(actor, order, target, data.reason, context)
        self._session.flush()
        self._record(
            actor,
            context,
            "quote.accepted" if data.accepted else "quote.rejected",
            order,
            {
                "version": quote.version,
                "channel": data.channel,
            },
        )
        return self._read(actor, quote)

    # --- Helpers ------------------------------------------------------------------------

    @staticmethod
    def _totals(quote: Quotation) -> None:
        quote.discount_total = sum((i.discount_amount for i in quote.items), ZERO)
        quote.subtotal = sum((i.base_amount for i in quote.items), ZERO)
        quote.tax_total = sum((i.tax_amount for i in quote.items), ZERO)
        quote.total = sum((i.total_amount for i in quote.items), ZERO)

    @staticmethod
    def _ensure_editable(order: WorkOrder) -> None:
        if Status(order.status) not in EDITABLE_ORDER_STATES:
            raise BusinessRuleError(
                "La cotización se elabora con la orden en Cotización o Pendiente de autorización."
            )

    @staticmethod
    def _require(actor: User, permission: Perm, action: str) -> None:
        if permission not in actor.permission_codes:
            raise PermissionDeniedError(f"No tiene permisos para {action}.")

    def _read(self, actor: User, quote: Quotation) -> QuoteRead:
        user_ids = {uid for uid in (quote.created_by_id, quote.discount_authorized_by_id) if uid}
        users = (
            {u.id: u for u in self._session.scalars(select(User).where(User.id.in_(user_ids)))}
            if user_ids
            else {}
        )
        part_ids = {i.part_id for i in quote.items if i.part_id}
        parts = (
            {p.id: p for p in self._session.scalars(select(Part).where(Part.id.in_(part_ids)))}
            if part_ids
            else {}
        )
        status = quote.status
        if status == "SENT" and quote.valid_until and quote.valid_until < today_bogota():
            status = "EXPIRED"

        def person(uid: uuid.UUID | None) -> PersonRef | None:
            user = users.get(uid) if uid else None
            return PersonRef(id=user.id, full_name=user.full_name) if user else None

        return QuoteRead(
            id=quote.id,
            version=quote.version,
            status=status,
            valid_until=quote.valid_until,
            notes=quote.notes,
            subtotal=quote.subtotal,
            discount_total=quote.discount_total,
            tax_total=quote.tax_total,
            total=quote.total,
            discount_authorized_by=person(quote.discount_authorized_by_id),
            created_by=person(quote.created_by_id),
            created_at=quote.created_at,
            sent_at=quote.sent_at,
            responded_at=quote.responded_at,
            response_channel=quote.response_channel,
            items=[
                QuoteItemRead(
                    id=i.id,
                    position=i.position,
                    kind=i.kind,
                    part_id=i.part_id,
                    sku=parts[i.part_id].sku if i.part_id in parts else None,
                    in_stock=self._inventory.stock_of(actor, i.part_id) if i.part_id else None,
                    description=i.description,
                    quantity=i.quantity,
                    unit_price=i.unit_price,
                    discount_percent=i.discount_percent,
                    tax_rate=int(i.tax_rate),
                    price_includes_tax=i.price_includes_tax,
                    discount_amount=i.discount_amount,
                    base_amount=i.base_amount,
                    tax_amount=i.tax_amount,
                    total_amount=i.total_amount,
                )
                for i in quote.items
            ],
        )

    def _record(
        self,
        actor: User,
        context: RequestContext,
        action: str,
        order: WorkOrder,
        changes: dict[str, object],
    ) -> None:
        self._audit.record(
            action,
            entity_type="work_order",
            entity_id=order.id,
            organization_id=actor.organization_id,
            actor_user_id=actor.id,
            context=context,
            changes=changes,
        )
