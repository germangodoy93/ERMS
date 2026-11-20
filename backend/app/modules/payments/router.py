import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.core.storage import Storage, get_storage
from app.modules.auth.dependencies import AppSettings, DbSession, require_permissions
from app.modules.organizations.models import Organization
from app.modules.payments.models import Payment
from app.modules.payments.pdf import build_receipt
from app.modules.payments.schemas import BillingRead, PaymentCreate, PaymentRead
from app.modules.payments.service import PaymentService
from app.modules.roles.catalog import Perm
from app.modules.users.models import User
from app.modules.workorders.schemas import PersonRef
from app.modules.workorders.service import WorkOrderService
from app.shared.context import RequestContext, get_request_context

router = APIRouter(prefix="/work-orders/{order_id}", tags=["payments"])

Reader = Annotated[User, Depends(require_permissions(Perm.WORK_ORDERS_READ))]
Cashier = Annotated[User, Depends(require_permissions(Perm.PAYMENTS_MANAGE))]
Context = Annotated[RequestContext, Depends(get_request_context)]


def get_orders(
    session: DbSession, settings: AppSettings, storage: Annotated[Storage, Depends(get_storage)]
) -> WorkOrderService:
    return WorkOrderService(session, settings, storage)


Orders = Annotated[WorkOrderService, Depends(get_orders)]


def _payment_read(session: DbSession, payment: Payment) -> PaymentRead:
    user = session.get(User, payment.received_by_id) if payment.received_by_id else None
    return PaymentRead(
        id=payment.id,
        receipt_number=payment.receipt_number,
        kind=payment.kind,
        amount=payment.amount,
        method=payment.method,
        reference=payment.reference,
        notes=payment.notes,
        received_by=PersonRef(id=user.id, full_name=user.full_name) if user else None,
        paid_at=payment.paid_at,
    )


@router.get("/billing", response_model=BillingRead, summary="Saldo y pagos de la orden")
def get_billing(
    order_id: uuid.UUID, actor: Reader, orders: Orders, session: DbSession
) -> BillingRead:
    order = orders.get(actor, order_id)
    service = PaymentService(session)
    billing = service.billing(order)
    return BillingRead(
        diagnostic_fee=billing.diagnostic_fee,
        accepted_quote_total=billing.accepted_quote_total,
        amount_due=billing.amount_due,
        paid=billing.paid,
        balance=billing.balance,
        payments=[_payment_read(session, p) for p in service.payments(order)],
        can_register=Perm.PAYMENTS_MANAGE in actor.permission_codes and billing.balance > 0,
    )


@router.post(
    "/payments",
    response_model=PaymentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un pago",
)
def register_payment(
    order_id: uuid.UUID,
    body: PaymentCreate,
    actor: Cashier,
    orders: Orders,
    session: DbSession,
    context: Context,
) -> PaymentRead:
    order = orders.get(actor, order_id, for_update=True)
    service = PaymentService(session)
    balance = service.billing(order).balance
    if balance <= 0:
        raise BusinessRuleError("La orden no tiene saldo pendiente.")
    if body.amount > balance:
        raise BusinessRuleError(f"El pago supera el saldo pendiente ({balance}).")
    payment = service.register(
        actor,
        order,
        amount=body.amount,
        method=body.method,
        reference=body.reference,
        notes=body.notes,
        context=context,
    )
    return _payment_read(session, payment)


@router.get(
    "/payments/{payment_id}/receipt.pdf",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}}},
    summary="Comprobante de pago (no es factura electrónica)",
)
def receipt(
    order_id: uuid.UUID,
    payment_id: uuid.UUID,
    actor: Reader,
    orders: Orders,
    session: DbSession,
) -> Response:
    order = orders.get(actor, order_id)
    service = PaymentService(session)
    payment = session.scalar(
        select(Payment).where(Payment.id == payment_id, Payment.work_order_id == order.id)
    )
    if payment is None:
        raise NotFoundError("El pago no existe.")
    organization = session.get(Organization, actor.organization_id)
    assert organization is not None  # noqa: S101 - FK guarantees it
    pdf = build_receipt(
        organization,
        orders.read(actor, order.id),
        _payment_read(session, payment),
        service.billing(order),
    )
    name = payment.receipt_number or f"anticipo-{order.number}"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{name}.pdf"',
            "Cache-Control": "no-store",
        },
    )
