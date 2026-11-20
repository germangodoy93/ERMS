"""Workshop dashboard and period reports (read-only queries).

Dates are interpreted in Bogotá time. Money is only shown to users with `reports:read`;
technicians get a personal dashboard limited to their own orders.
"""

import csv
import io
import uuid
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError
from app.modules.customers.models import Customer
from app.modules.devices.models import Device, DeviceModel, Manufacturer
from app.modules.inventory.models import InventoryMovement, Part, StockLevel
from app.modules.payments.models import Payment
from app.modules.payments.service import PaymentService
from app.modules.quotes.models import Quotation
from app.modules.repairs.models import RepairTask
from app.modules.reports.schemas import (
    Dashboard,
    MethodTotal,
    Report,
    StatusCount,
    TechnicianLoad,
)
from app.modules.roles.catalog import Perm
from app.modules.users.models import User
from app.modules.warranties.models import Warranty, WarrantyClaim
from app.modules.workorders.catalog import (
    PAYMENT_METHOD_LABELS,
    STATUS_LABELS,
    PaymentMethod,
    Status,
)
from app.modules.workorders.models import WorkOrder
from app.modules.workorders.schemas import PersonRef
from app.shared.context import BOGOTA, utcnow
from app.shared.money import ZERO, money

MAX_RANGE_DAYS = 366
OPEN = [s.value for s in Status if s is not Status.ENTREGADO]


def _start(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=BOGOTA)


def format_money(value: Decimal) -> str:
    integer, _, cents = f"{money(value):,.2f}".partition(".")
    text = integer.replace(",", ".")
    return f"$ {text}" if cents == "00" else f"$ {text},{cents}"


class ReportService:
    def __init__(self, session: Session) -> None:
        self._session = session

    # --- Dashboard ----------------------------------------------------------------------

    def dashboard(self, actor: User) -> Dashboard:
        org = actor.organization_id
        workshop = Perm.REPORTS_READ in actor.permission_codes
        today = utcnow().astimezone(BOGOTA).date()

        def orders() -> Select[int]:
            query = select(func.count(WorkOrder.id)).where(WorkOrder.organization_id == org)
            if not workshop:
                query = query.where(WorkOrder.assigned_technician_id == actor.id)
            return query

        by_status = self._session.execute(
            select(WorkOrder.status, func.count(WorkOrder.id))
            .where(
                WorkOrder.organization_id == org,
                WorkOrder.status.in_(OPEN),
                *([] if workshop else [WorkOrder.assigned_technician_id == actor.id]),
            )
            .group_by(WorkOrder.status)
        ).all()
        counts = {Status(s): c for s, c in by_status}
        week_start = today - timedelta(days=today.weekday())
        ready_orders = list(
            self._session.scalars(
                select(WorkOrder).where(
                    WorkOrder.organization_id == org, WorkOrder.status == Status.LISTO_ENTREGA
                )
            )
        )
        result = Dashboard(
            scope="WORKSHOP" if workshop else "MINE",
            open_by_status=[
                StatusCount(status=s, count=counts[s]) for s in Status if counts.get(s)
            ],
            received_today=self._count(orders().where(WorkOrder.received_at >= _start(today))),
            received_week=self._count(orders().where(WorkOrder.received_at >= _start(week_start))),
            overdue=self._count(
                orders().where(
                    WorkOrder.status.in_(OPEN), WorkOrder.estimated_delivery_date < today
                )
            ),
            awaiting_customer=counts.get(Status.PENDIENTE_AUTORIZACION, 0),
            expired_quotes=self._count(
                select(func.count(Quotation.id))
                .join(WorkOrder, WorkOrder.id == Quotation.work_order_id)
                .where(
                    Quotation.organization_id == org,
                    Quotation.status == "SENT",
                    Quotation.valid_until < today,
                    *([] if workshop else [WorkOrder.assigned_technician_id == actor.id]),
                )
            ),
            ready_for_delivery=counts.get(Status.LISTO_ENTREGA, 0),
            ready_balance=None,
            income_month=None,
            income_month_total=None,
            avg_turnaround_days=self._turnaround(org, today, None if workshop else actor.id),
            technician_load=None,
            low_stock=None,
            warranties_expiring=None,
            open_claims=None,
        )
        if not workshop:
            return result

        payments = PaymentService(self._session)
        result.ready_balance = sum(
            (max(payments.billing(o).balance, ZERO) for o in ready_orders), ZERO
        )
        month_start = today.replace(day=1)
        income = self._session.execute(
            select(Payment.method, func.sum(Payment.amount))
            .where(Payment.organization_id == org, Payment.paid_at >= _start(month_start))
            .group_by(Payment.method)
        ).all()
        result.income_month = [
            MethodTotal(method=PaymentMethod(m), amount=a) for m, a in sorted(income)
        ]
        result.income_month_total = sum((a for _, a in income), ZERO)
        load = self._session.execute(
            select(WorkOrder.assigned_technician_id, func.count(WorkOrder.id))
            .where(WorkOrder.organization_id == org, WorkOrder.status.in_(OPEN))
            .group_by(WorkOrder.assigned_technician_id)
        ).all()
        users = self._users({uid for uid, _ in load if uid})
        result.technician_load = sorted(
            (
                TechnicianLoad(
                    technician=PersonRef(id=users[uid].id, full_name=users[uid].full_name)
                    if uid in users
                    else None,
                    open_orders=n,
                )
                for uid, n in load
            ),
            key=lambda t: -t.open_orders,
        )
        stock = (
            select(StockLevel.part_id, func.sum(StockLevel.quantity).label("qty"))
            .group_by(StockLevel.part_id)
            .subquery()
        )
        result.low_stock = self._count(
            select(func.count(Part.id))
            .outerjoin(stock, stock.c.part_id == Part.id)
            .where(
                Part.organization_id == org,
                Part.is_active.is_(True),
                func.coalesce(stock.c.qty, 0) <= Part.min_stock,
            )
        )
        result.warranties_expiring = self._count(
            select(func.count(Warranty.id)).where(
                Warranty.organization_id == org,
                Warranty.ends_on >= today,
                Warranty.ends_on <= today + timedelta(days=15),
            )
        )
        result.open_claims = self._count(
            select(func.count(WarrantyClaim.id)).where(
                WarrantyClaim.organization_id == org, WarrantyClaim.status == "OPEN"
            )
        )
        return result

    # --- Reports ------------------------------------------------------------------------

    def report(self, actor: User, kind: str, date_from: date, date_to: date) -> Report:
        if date_to < date_from:
            raise BusinessRuleError("La fecha final es anterior a la inicial.")
        if (date_to - date_from).days > MAX_RANGE_DAYS:
            raise BusinessRuleError("El rango máximo es de un año.")
        start, end = _start(date_from), _start(date_to + timedelta(days=1))
        builders = {
            "income": self._income,
            "orders": self._orders,
            "inventory": self._inventory,
            "technicians": self._technicians,
        }
        return builders[kind](actor.organization_id, start, end, date_from, date_to)

    def _income(self, org: uuid.UUID, start: datetime, end: datetime, d1: date, d2: date) -> Report:
        rows = self._session.execute(
            select(Payment, WorkOrder.number, Customer.full_name)
            .join(WorkOrder, WorkOrder.id == Payment.work_order_id)
            .join(Customer, Customer.id == WorkOrder.customer_id)
            .where(Payment.organization_id == org, Payment.paid_at >= start, Payment.paid_at < end)
            .order_by(Payment.paid_at)
        ).all()
        totals: dict[str, Decimal] = defaultdict(lambda: ZERO)
        for payment, _, _ in rows:
            totals[payment.method] += payment.amount
        return Report(
            kind="income",
            title="Ingresos",
            date_from=d1.isoformat(),
            date_to=d2.isoformat(),
            columns=["Fecha", "Comprobante", "Orden", "Cliente", "Medio", "Valor"],
            money_columns=[5],
            rows=[
                [
                    p.paid_at.astimezone(BOGOTA).strftime("%Y-%m-%d %H:%M"),
                    p.receipt_number or "Anticipo",
                    number,
                    customer,
                    PAYMENT_METHOD_LABELS[PaymentMethod(p.method)],
                    f"{p.amount:.2f}",
                ]
                for p, number, customer in rows
            ],
            summary=[
                *(
                    (PAYMENT_METHOD_LABELS[PaymentMethod(m)], format_money(v))
                    for m, v in sorted(totals.items())
                ),
                ("Total", format_money(sum(totals.values(), ZERO))),
            ],
        )

    def _orders(self, org: uuid.UUID, start: datetime, end: datetime, d1: date, d2: date) -> Report:
        technician = User
        rows = self._session.execute(
            select(WorkOrder, Customer.full_name, Manufacturer.name, DeviceModel.name, technician)
            .join(Customer, Customer.id == WorkOrder.customer_id)
            .join(Device, Device.id == WorkOrder.device_id)
            .join(DeviceModel, DeviceModel.id == Device.model_id)
            .join(Manufacturer, Manufacturer.id == DeviceModel.manufacturer_id)
            .outerjoin(technician, technician.id == WorkOrder.assigned_technician_id)
            .where(
                WorkOrder.organization_id == org,
                WorkOrder.received_at >= start,
                WorkOrder.received_at < end,
            )
            .order_by(WorkOrder.received_at)
        ).all()
        by_status: dict[str, int] = defaultdict(int)
        durations: list[float] = []
        table = []
        for order, customer, brand, model, tech in rows:
            by_status[order.status] += 1
            days = None
            if order.delivered_at:
                days = round((order.delivered_at - order.received_at).total_seconds() / 86400, 1)
                durations.append(days)
            table.append(
                [
                    order.number,
                    order.received_at.astimezone(BOGOTA).strftime("%Y-%m-%d"),
                    STATUS_LABELS[Status(order.status)],
                    customer,
                    f"{brand} {model}",
                    tech.full_name if tech else "",
                    order.delivered_at.astimezone(BOGOTA).strftime("%Y-%m-%d")
                    if order.delivered_at
                    else "",
                    "" if days is None else f"{days}",
                ]
            )
        summary = [(STATUS_LABELS[Status(s)], str(n)) for s, n in sorted(by_status.items())]
        summary.append(("Órdenes recibidas", str(len(rows))))
        if durations:
            summary.append(
                ("Días promedio hasta la entrega", f"{sum(durations) / len(durations):.1f}")
            )
        return Report(
            kind="orders",
            title="Órdenes de servicio",
            date_from=d1.isoformat(),
            date_to=d2.isoformat(),
            columns=[
                "Orden",
                "Recibida",
                "Estado",
                "Cliente",
                "Equipo",
                "Técnico",
                "Entregada",
                "Días",
            ],
            rows=table,
            summary=summary,
        )

    def _inventory(
        self, org: uuid.UUID, start: datetime, end: datetime, d1: date, d2: date
    ) -> Report:
        stock = (
            select(StockLevel.part_id, func.sum(StockLevel.quantity).label("qty"))
            .group_by(StockLevel.part_id)
            .subquery()
        )
        moves = (
            select(
                InventoryMovement.part_id,
                func.sum(InventoryMovement.quantity)
                .filter(InventoryMovement.quantity > 0)
                .label("ins"),
                func.sum(InventoryMovement.quantity)
                .filter(InventoryMovement.quantity < 0)
                .label("outs"),
            )
            .where(
                InventoryMovement.organization_id == org,
                InventoryMovement.created_at >= start,
                InventoryMovement.created_at < end,
            )
            .group_by(InventoryMovement.part_id)
            .subquery()
        )
        rows = self._session.execute(
            select(Part, func.coalesce(stock.c.qty, 0), moves.c.ins, moves.c.outs)
            .outerjoin(stock, stock.c.part_id == Part.id)
            .outerjoin(moves, moves.c.part_id == Part.id)
            .where(Part.organization_id == org)
            .order_by(Part.name)
        ).all()
        total_value = ZERO
        table = []
        for part, qty, ins, outs in rows:
            value = money(part.unit_cost * qty)
            total_value += value
            table.append(
                [
                    part.sku,
                    part.name,
                    str(qty),
                    str(part.min_stock),
                    f"{part.unit_cost:.2f}",
                    f"{value:.2f}",
                    str(ins or 0),
                    str(-(outs or 0)),
                    "Sí" if qty <= part.min_stock else "",
                ]
            )
        return Report(
            kind="inventory",
            title="Inventario",
            date_from=d1.isoformat(),
            date_to=d2.isoformat(),
            columns=[
                "Código",
                "Repuesto",
                "Existencia",
                "Mínimo",
                "Costo",
                "Valor",
                "Entradas",
                "Salidas",
                "Stock bajo",
            ],
            money_columns=[4, 5],
            rows=table,
            summary=[
                ("Repuestos", str(len(rows))),
                ("Valor del inventario a costo", format_money(total_value)),
            ],
        )

    def _technicians(
        self, org: uuid.UUID, start: datetime, end: datetime, d1: date, d2: date
    ) -> Report:
        received = dict(
            self._session.execute(
                select(WorkOrder.assigned_technician_id, func.count(WorkOrder.id))
                .where(
                    WorkOrder.organization_id == org,
                    WorkOrder.received_at >= start,
                    WorkOrder.received_at < end,
                )
                .group_by(WorkOrder.assigned_technician_id)
            ).all()
        )
        delivered = dict(
            self._session.execute(
                select(WorkOrder.assigned_technician_id, func.count(WorkOrder.id))
                .where(
                    WorkOrder.organization_id == org,
                    WorkOrder.delivered_at >= start,
                    WorkOrder.delivered_at < end,
                )
                .group_by(WorkOrder.assigned_technician_id)
            ).all()
        )
        work = {
            uid: (n, minutes)
            for uid, n, minutes in self._session.execute(
                select(
                    RepairTask.technician_id,
                    func.count(RepairTask.id),
                    func.coalesce(func.sum(RepairTask.labor_minutes), 0),
                )
                .where(
                    RepairTask.organization_id == org,
                    RepairTask.created_at >= start,
                    RepairTask.created_at < end,
                )
                .group_by(RepairTask.technician_id)
            ).all()
        }
        ids = {uid for uid in (*received, *delivered, *work) if uid}
        users = self._users(ids)
        table = []
        for uid in sorted(ids, key=lambda u: users[u].full_name if u in users else ""):
            tasks, minutes = work.get(uid, (0, 0))
            table.append(
                [
                    users[uid].full_name if uid in users else "—",
                    str(received.get(uid, 0)),
                    str(delivered.get(uid, 0)),
                    str(tasks),
                    f"{(minutes or 0) / 60:.1f}",
                ]
            )
        if received.get(None):
            table.append(
                ["Sin asignar", str(received[None]), str(delivered.get(None, 0)), "0", "0.0"]
            )
        return Report(
            kind="technicians",
            title="Productividad por técnico",
            date_from=d1.isoformat(),
            date_to=d2.isoformat(),
            columns=["Técnico", "Órdenes recibidas", "Órdenes entregadas", "Trabajos", "Horas"],
            rows=table,
            summary=[("Técnicos con actividad", str(len(ids)))],
        )

    # --- Helpers ------------------------------------------------------------------------

    def _count(self, query: Select[int]) -> int:
        return int(self._session.scalar(query) or 0)

    def _turnaround(
        self, org: uuid.UUID, today: date, technician: uuid.UUID | None
    ) -> float | None:
        query = select(
            func.avg(func.extract("epoch", WorkOrder.delivered_at - WorkOrder.received_at))
        ).where(
            WorkOrder.organization_id == org,
            WorkOrder.delivered_at >= _start(today - timedelta(days=90)),
        )
        if technician:
            query = query.where(WorkOrder.assigned_technician_id == technician)
        seconds = self._session.scalar(query)
        return round(float(seconds) / 86400, 1) if seconds is not None else None

    def _users(self, ids: set[uuid.UUID]) -> dict[uuid.UUID, User]:
        if not ids:
            return {}
        return {u.id: u for u in self._session.scalars(select(User).where(User.id.in_(ids)))}


def to_csv(report: Report) -> bytes:
    """Excel-friendly CSV: UTF-8 with BOM and ';' separator (Spanish locale)."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow([f"{report.title} {report.date_from} a {report.date_to}"])
    writer.writerow(report.columns)
    writer.writerows([_safe_cell(v) for v in row] for row in report.rows)
    writer.writerow([])
    writer.writerows([_safe_cell(v) for v in row] for row in report.summary)
    return ("\ufeff" + buffer.getvalue()).encode("utf-8")


FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _safe_cell(value: object) -> str:
    """Prevents CSV formula injection: text that starts like a formula is quoted. Numbers
    (including negative ones) are left as they are."""
    text = "" if value is None else str(value)
    if text.startswith(FORMULA_PREFIXES):
        try:
            Decimal(text)
        except ArithmeticError:
            return "'" + text
    return text
