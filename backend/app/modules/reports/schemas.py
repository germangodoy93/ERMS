from typing import Any, Literal

from pydantic import BaseModel, Field

from app.modules.workorders.catalog import PaymentMethod, Status
from app.modules.workorders.schemas import MoneyOut, PersonRef


class StatusCount(BaseModel):
    status: Status
    count: int


class MethodTotal(BaseModel):
    method: PaymentMethod
    amount: MoneyOut


class TechnicianLoad(BaseModel):
    technician: PersonRef | None = Field(description="null = sin asignar")
    open_orders: int


class Dashboard(BaseModel):
    scope: Literal["WORKSHOP", "MINE"] = Field(
        description="WORKSHOP con reports:read; MINE para técnicos (solo sus órdenes)"
    )
    open_by_status: list[StatusCount]
    received_today: int
    received_week: int
    overdue: int = Field(
        description="Con trabajo pendiente del taller y fecha estimada de entrega vencida "
        "(no cuenta canceladas, no reparables, rechazadas ni listas para entrega)"
    )
    awaiting_customer: int
    expired_quotes: int
    ready_for_delivery: int
    ready_balance: MoneyOut | None
    income_month: list[MethodTotal] | None
    income_month_total: MoneyOut | None
    avg_turnaround_days: float | None = Field(description="Últimos 90 días, recepción → entrega")
    technician_load: list[TechnicianLoad] | None
    low_stock: int | None
    warranties_expiring: int | None = Field(description="Vencen en los próximos 15 días")
    open_claims: int | None


class Report(BaseModel):
    """Generic tabular report: the same data feeds JSON, CSV and PDF."""

    kind: Literal["income", "orders", "inventory", "technicians"]
    title: str
    date_from: str
    date_to: str
    columns: list[str]
    rows: list[list[Any]]
    summary: list[tuple[str, str]]
    money_columns: list[int] = Field(
        default_factory=list, description="Índices de columnas con valores en pesos"
    )
