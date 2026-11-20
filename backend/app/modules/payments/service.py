"""Payments and balance of a work order.

Amount due (Sprint 5 decision): the total of the ACCEPTED quotation, which already includes
the diagnostic; without an accepted quotation, the diagnostic fee. Balance = due - paid.
A negative balance is money in favour of the customer.
"""

import uuid
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.audit.service import AuditService
from app.modules.payments.models import Payment
from app.modules.quotes.models import Quotation
from app.modules.users.models import User
from app.modules.workorders.catalog import PaymentMethod
from app.modules.workorders.models import WorkOrder
from app.shared.context import RequestContext, utcnow
from app.shared.money import ZERO, money
from app.shared.sequences import next_document_number

RECEIPT_DOC = "RECEIPT"
RECEIPT_PREFIX = "RC"


@dataclass(frozen=True, slots=True)
class Billing:
    diagnostic_fee: Decimal
    accepted_quote_total: Decimal | None
    amount_due: Decimal
    paid: Decimal
    balance: Decimal


class PaymentService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._audit = AuditService(session)

    def payments(self, order: WorkOrder) -> list[Payment]:
        return list(
            self._session.scalars(
                select(Payment)
                .where(Payment.work_order_id == order.id)
                .order_by(Payment.paid_at, Payment.id)
            )
        )

    def billing(self, order: WorkOrder) -> Billing:
        accepted = self._session.scalar(
            select(Quotation.total).where(
                Quotation.work_order_id == order.id, Quotation.status == "ACCEPTED"
            )
        )
        paid = self._session.scalar(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(
                Payment.work_order_id == order.id
            )
        )
        due = accepted if accepted is not None else order.diagnostic_fee
        paid_amount = money(paid or ZERO)
        return Billing(
            diagnostic_fee=money(order.diagnostic_fee),
            accepted_quote_total=money(accepted) if accepted is not None else None,
            amount_due=money(due),
            paid=paid_amount,
            balance=money(due) - paid_amount,
        )

    def register(
        self,
        actor: User,
        order: WorkOrder,
        *,
        amount: Decimal,
        method: PaymentMethod,
        reference: str | None,
        notes: str | None,
        kind: str = "PAYMENT",
        context: RequestContext | None = None,
    ) -> Payment:
        payment = Payment(
            organization_id=order.organization_id,
            work_order_id=order.id,
            receipt_number=next_document_number(
                self._session, order.organization_id, RECEIPT_DOC, RECEIPT_PREFIX
            ),
            kind=kind,
            amount=money(amount),
            method=method,
            reference=reference,
            notes=notes,
            received_by_id=actor.id,
            paid_at=utcnow(),
        )
        self._session.add(payment)
        self._session.flush()
        self._audit.record(
            "payment.registered",
            entity_type="work_order",
            entity_id=order.id,
            organization_id=order.organization_id,
            actor_user_id=actor.id,
            context=context,
            changes={
                "receipt_number": payment.receipt_number,
                "amount": str(payment.amount),
                "method": method,
                "kind": kind,
            },
        )
        return payment

    def get(self, order: WorkOrder, payment_id: uuid.UUID) -> Payment | None:
        return self._session.scalar(
            select(Payment).where(Payment.id == payment_id, Payment.work_order_id == order.id)
        )
