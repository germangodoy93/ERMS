"""Customer notices by WhatsApp (ADR-054): ERMS writes the message, the advisor sends it.

The suggested notice depends on the order's status and on the notices already prepared:

- Quote sent to the customer -> "Cotización lista" until one is prepared.
- Ready for delivery after quality control -> "Equipo listo"; after a cancellation, a
  rejected quote or "no reparable" -> "No reparado o cancelado" (prepared in that state or
  once ready). If the customer was told and the device is still there after REMINDER_DAYS,
  a reminder is due, and again every REMINDER_DAYS.
- Reception and delivery happen in person: suggested, never pending.
"""

import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from urllib.parse import quote

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.modules.audit.service import AuditService
from app.modules.customers.models import Customer
from app.modules.diagnostics.models import DiagnosticSession
from app.modules.notices.catalog import (
    DEFAULT_TEMPLATES,
    NOT_REPAIRED_STATES,
    NOTICE_LABELS,
    PENDING_KINDS,
    PICKUP_KINDS,
    PLACEHOLDERS,
    REMINDER_DAYS,
    NoticeKind,
    render,
    template_errors,
)
from app.modules.notices.models import NoticeTemplate, WorkOrderNotice
from app.modules.notices.schemas import (
    NoticeCreate,
    NoticeDraft,
    NoticePanel,
    NoticeRead,
    PendingNotice,
    PlaceholderRead,
    PreparedNotice,
    TemplateRead,
    TemplatesRead,
)
from app.modules.organizations.models import Organization
from app.modules.payments.service import PaymentService
from app.modules.quotes.models import Quotation
from app.modules.roles.catalog import Perm
from app.modules.users.models import User
from app.modules.warranties.models import Warranty
from app.modules.workorders.catalog import Status
from app.modules.workorders.models import WorkOrder, WorkOrderStatusHistory
from app.modules.workorders.schemas import PersonRef
from app.shared.context import BOGOTA, RequestContext, utcnow
from app.shared.money import ZERO, format_money

WATCHED = frozenset({Status.PENDIENTE_AUTORIZACION, Status.LISTO_ENTREGA, *NOT_REPAIRED_STATES})
STATUS_KIND: dict[Status, NoticeKind] = {
    Status.RECIBIDO: NoticeKind.RECEIVED,
    Status.PENDIENTE_AUTORIZACION: NoticeKind.QUOTE_READY,
    Status.ENTREGADO: NoticeKind.DELIVERED,
    **dict.fromkeys(NOT_REPAIRED_STATES, NoticeKind.NOT_REPAIRED),
}


@dataclass(frozen=True, slots=True)
class Suggestion:
    kind: NoticeKind
    pending: bool
    since: datetime


def whatsapp_number(phone: str | None) -> tuple[str | None, str | None]:
    """(digits for wa.me, reason it cannot be used). Phones are stored in E.164."""
    if not phone:
        return None, "El cliente no tiene teléfono registrado."
    if phone.startswith("+5760"):
        return None, "El teléfono del cliente es fijo; WhatsApp necesita un celular."
    return phone.removeprefix("+"), None


def whatsapp_url(digits: str, body: str) -> str:
    return f"https://wa.me/{digits}?text={quote(body, safe='')}"


def suggest(
    order: WorkOrder,
    history: list[WorkOrderStatusHistory],
    notices: list[WorkOrderNotice],
    now: datetime,
) -> Suggestion:
    """`history` and `notices` belong to the order, oldest first."""
    status = Status(order.status)

    def entered(states: Iterable[Status]) -> tuple[datetime, WorkOrderStatusHistory | None]:
        targets = {s.value for s in states}
        for entry in reversed(history):
            if entry.to_status in targets:
                return entry.changed_at, entry
        return order.received_at, None

    def told(kinds: Iterable[NoticeKind], since: datetime) -> WorkOrderNotice | None:
        wanted = {k.value for k in kinds}
        found = [n for n in notices if n.kind in wanted and n.prepared_at >= since]
        return found[-1] if found else None

    if status is Status.LISTO_ENTREGA:
        ready_at, entry = entered([Status.LISTO_ENTREGA])
        repaired = entry is not None and entry.from_status == Status.CONTROL_CALIDAD
        base = NoticeKind.READY if repaired else NoticeKind.NOT_REPAIRED
        # Not repaired: telling the customer while cancelled/rejected also counts.
        since = ready_at if repaired else entered(NOT_REPAIRED_STATES)[0]
        last = told(PICKUP_KINDS, since)
        if last is None:
            return Suggestion(base, pending=True, since=ready_at)
        due = last.prepared_at + timedelta(days=REMINDER_DAYS)
        if now >= due:
            return Suggestion(NoticeKind.REMINDER, pending=True, since=due)
        return Suggestion(base, pending=False, since=ready_at)

    kind = STATUS_KIND.get(status, NoticeKind.FREE)
    since, _ = entered([status])
    if kind in PENDING_KINDS:
        return Suggestion(kind, pending=told([kind], since) is None, since=since)
    return Suggestion(kind, pending=False, since=since)


class NoticeService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._audit = AuditService(session)

    # --- Order panel ---------------------------------------------------------------------

    def panel(self, actor: User, order_id: uuid.UUID) -> NoticePanel:
        order = self._order(actor, order_id)
        customer = self._customer(order)
        _, blocked = whatsapp_number(customer.phone)
        notices = self._notices([order.id]).get(order.id, [])
        suggestion = suggest(order, self._history([order.id]).get(order.id, []), notices, utcnow())
        values = self._values(order, customer)
        templates = self._templates(actor.organization_id)
        return NoticePanel(
            phone=customer.phone,
            can_whatsapp=blocked is None,
            blocked_reason=blocked,
            can_prepare=Perm.CUSTOMERS_NOTIFY in actor.permission_codes,
            suggested=suggestion.kind,
            pending=suggestion.pending,
            drafts=[
                NoticeDraft(kind=kind, label=NOTICE_LABELS[kind], body=render(body, values))
                for kind, body in templates.items()
            ],
            history=[self._read(n) for n in reversed(notices)],
        )

    def prepare(
        self, actor: User, order_id: uuid.UUID, data: NoticeCreate, context: RequestContext
    ) -> PreparedNotice:
        order = self._order(actor, order_id)
        customer = self._customer(order)
        digits, blocked = whatsapp_number(customer.phone)
        if digits is None or customer.phone is None:
            raise BusinessRuleError(blocked or "El cliente no tiene celular.")
        notice = WorkOrderNotice(
            organization_id=actor.organization_id,
            work_order_id=order.id,
            kind=data.kind.value,
            phone=customer.phone,
            body=data.body,
            prepared_by_id=actor.id,
            prepared_at=utcnow(),
        )
        self._session.add(notice)
        self._session.flush()
        # The message itself stays in the order's log; the audit only records the fact.
        self._audit.record(
            "work_order.notice_prepared",
            entity_type="work_order",
            entity_id=order.id,
            organization_id=actor.organization_id,
            actor_user_id=actor.id,
            context=context,
            changes={"kind": data.kind.value, "channel": "WHATSAPP"},
        )
        return PreparedNotice(notice=self._read(notice), url=whatsapp_url(digits, data.body))

    # --- Dashboard -----------------------------------------------------------------------

    def pending(self, actor: User) -> list[PendingNotice]:
        orders = list(
            self._session.scalars(
                select(WorkOrder).where(
                    WorkOrder.organization_id == actor.organization_id,
                    WorkOrder.status.in_([s.value for s in WATCHED]),
                )
            )
        )
        if not orders:
            return []
        ids = [o.id for o in orders]
        history = self._history(ids)
        notices = self._notices(ids)
        customers = {
            c.id: c
            for c in self._session.scalars(
                select(Customer).where(Customer.id.in_({o.customer_id for o in orders}))
            )
        }
        now = utcnow()
        result: list[PendingNotice] = []
        for order in orders:
            suggestion = suggest(order, history.get(order.id, []), notices.get(order.id, []), now)
            if not suggestion.pending:
                continue
            customer = customers[order.customer_id]
            result.append(
                PendingNotice(
                    work_order_id=order.id,
                    number=order.number,
                    customer_name=customer.full_name,
                    status=Status(order.status),
                    kind=suggestion.kind,
                    label=NOTICE_LABELS[suggestion.kind],
                    since=suggestion.since,
                    can_whatsapp=whatsapp_number(customer.phone)[1] is None,
                )
            )
        return sorted(result, key=lambda p: p.since)

    # --- Templates -----------------------------------------------------------------------

    def templates(self, actor: User) -> TemplatesRead:
        custom = self._custom_templates(actor.organization_id)
        return TemplatesRead(
            templates=[
                TemplateRead(
                    kind=kind,
                    label=NOTICE_LABELS[kind],
                    body=custom.get(kind, default),
                    default_body=default,
                    is_default=kind not in custom,
                )
                for kind, default in DEFAULT_TEMPLATES.items()
            ],
            placeholders=[
                PlaceholderRead(name=name, description=text) for name, text in PLACEHOLDERS.items()
            ],
            reminder_days=REMINDER_DAYS,
        )

    def save_template(
        self, actor: User, kind: NoticeKind, body: str, context: RequestContext
    ) -> TemplatesRead:
        errors = template_errors(body)
        if errors:
            raise BusinessRuleError(" ".join(errors))
        row = self._session.get(NoticeTemplate, (actor.organization_id, kind.value))
        if body == DEFAULT_TEMPLATES[kind]:
            if row is not None:
                self._session.delete(row)
        elif row is None:
            self._session.add(
                NoticeTemplate(
                    organization_id=actor.organization_id,
                    kind=kind.value,
                    body=body,
                    updated_by_id=actor.id,
                    updated_at=utcnow(),
                )
            )
        else:
            row.body = body
            row.updated_by_id = actor.id
            row.updated_at = utcnow()
        self._session.flush()
        self._record_template(actor, kind, "notice_template.updated", context)
        return self.templates(actor)

    def reset_template(
        self, actor: User, kind: NoticeKind, context: RequestContext
    ) -> TemplatesRead:
        self._session.execute(
            delete(NoticeTemplate).where(
                NoticeTemplate.organization_id == actor.organization_id,
                NoticeTemplate.kind == kind.value,
            )
        )
        self._record_template(actor, kind, "notice_template.reset", context)
        return self.templates(actor)

    # --- Helpers -------------------------------------------------------------------------

    def _record_template(
        self, actor: User, kind: NoticeKind, action: str, context: RequestContext
    ) -> None:
        self._audit.record(
            action,
            entity_type="notice_template",
            entity_id=kind.value,
            organization_id=actor.organization_id,
            actor_user_id=actor.id,
            context=context,
            changes={"kind": kind.value},
        )

    def _order(self, actor: User, order_id: uuid.UUID) -> WorkOrder:
        order = self._session.scalar(
            select(WorkOrder).where(
                WorkOrder.id == order_id, WorkOrder.organization_id == actor.organization_id
            )
        )
        if order is None:
            raise NotFoundError("La orden de servicio no existe.")
        return order

    def _customer(self, order: WorkOrder) -> Customer:
        customer = self._session.get(Customer, order.customer_id)
        if customer is None:  # pragma: no cover - guaranteed by the foreign key
            raise NotFoundError("El cliente no existe.")
        return customer

    def _history(self, ids: list[uuid.UUID]) -> dict[uuid.UUID, list[WorkOrderStatusHistory]]:
        grouped: dict[uuid.UUID, list[WorkOrderStatusHistory]] = {}
        for entry in self._session.scalars(
            select(WorkOrderStatusHistory)
            .where(WorkOrderStatusHistory.work_order_id.in_(ids))
            .order_by(WorkOrderStatusHistory.changed_at, WorkOrderStatusHistory.id)
        ):
            grouped.setdefault(entry.work_order_id, []).append(entry)
        return grouped

    def _notices(self, ids: list[uuid.UUID]) -> dict[uuid.UUID, list[WorkOrderNotice]]:
        grouped: dict[uuid.UUID, list[WorkOrderNotice]] = {}
        for notice in self._session.scalars(
            select(WorkOrderNotice)
            .where(WorkOrderNotice.work_order_id.in_(ids))
            .order_by(WorkOrderNotice.prepared_at, WorkOrderNotice.id)
        ):
            grouped.setdefault(notice.work_order_id, []).append(notice)
        return grouped

    def _custom_templates(self, organization_id: uuid.UUID) -> dict[NoticeKind, str]:
        rows = self._session.scalars(
            select(NoticeTemplate).where(NoticeTemplate.organization_id == organization_id)
        )
        return {NoticeKind(r.kind): r.body for r in rows}

    def _templates(self, organization_id: uuid.UUID) -> dict[NoticeKind, str]:
        custom = self._custom_templates(organization_id)
        return {kind: custom.get(kind, body) for kind, body in DEFAULT_TEMPLATES.items()}

    def _read(self, notice: WorkOrderNotice) -> NoticeRead:
        user = self._session.get(User, notice.prepared_by_id) if notice.prepared_by_id else None
        return NoticeRead(
            id=notice.id,
            kind=NoticeKind(notice.kind),
            label=NOTICE_LABELS[NoticeKind(notice.kind)],
            phone=notice.phone,
            body=notice.body,
            prepared_by=PersonRef(id=user.id, full_name=user.full_name) if user else None,
            prepared_at=notice.prepared_at,
        )

    def _values(self, order: WorkOrder, customer: Customer) -> dict[str, str]:
        organization = self._session.get(Organization, order.organization_id)
        assert organization is not None  # noqa: S101 - guaranteed by the foreign key
        billing = PaymentService(self._session).billing(order)
        quote_total = self._session.scalar(
            select(Quotation.total)
            .where(Quotation.work_order_id == order.id, Quotation.status.in_(["SENT", "ACCEPTED"]))
            .order_by(Quotation.version.desc())
            .limit(1)
        )
        conclusion = self._session.scalar(
            select(DiagnosticSession.conclusion).where(DiagnosticSession.work_order_id == order.id)
        )
        warranty = self._session.scalar(select(Warranty).where(Warranty.work_order_id == order.id))
        history = self._history([order.id]).get(order.id, [])
        reason = next(
            (
                h.reason
                for h in reversed(history)
                if h.to_status in {s.value for s in NOT_REPAIRED_STATES} and h.reason
            ),
            None,
        )
        ready_at = next(
            (h.changed_at for h in reversed(history) if h.to_status == Status.LISTO_ENTREGA),
            None,
        )
        today = utcnow().astimezone(BOGOTA).date()
        device = order.device
        address = ", ".join(p for p in (organization.address, organization.city) if p)
        return {
            "cliente": _first_name(customer),
            "orden": order.number,
            "equipo": "PC armada a la medida"
            if order.kind == "ASSEMBLY"
            else f"{device.model.manufacturer.name} {device.model.name}",
            "taller": organization.name,
            "telefono_taller": _readable_phone(organization.phone),
            "direccion_taller": address or "nuestro taller",
            "falla": (conclusion or order.reported_issue).strip().rstrip("."),
            "total": format_money(quote_total if quote_total is not None else billing.amount_due),
            "saldo": format_money(max(billing.balance, ZERO)),
            "diagnostico": format_money(order.diagnostic_fee or Decimal(0)),
            "fecha_estimada": order.estimated_delivery_date.strftime("%d/%m/%Y")
            if order.estimated_delivery_date
            else "por confirmar",
            "motivo": (reason or "no fue posible repararlo").strip().rstrip("."),
            "dias_listo": str((today - ready_at.astimezone(BOGOTA).date()).days)
            if ready_at
            else "0",
            "garantia_dias": str(warranty.days if warranty else organization.warranty_days),
            "garantia_hasta": warranty.ends_on.strftime("%d/%m/%Y")
            if warranty
            else "la fecha de entrega más los días de garantía",
        }


def _first_name(customer: Customer) -> str:
    if customer.kind == "PERSON":
        return customer.full_name.split()[0] if customer.full_name.split() else "cliente"
    return customer.full_name


def _readable_phone(phone: str | None) -> str:
    if not phone:
        return ""
    if phone.startswith("+57") and len(phone) == 13:
        digits = phone[3:]
        return f"{digits[:3]} {digits[3:6]} {digits[6:]}"
    return phone
