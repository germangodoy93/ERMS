"""Diagnostic of a work order.

Rules:
- Results are recorded while the order is in DIAGNOSTICO (technicians only on their orders).
- Every manual test of the device category must have a result before closing; NOT_TESTED is
  a valid, explicit answer (e.g. a device that does not power on).
- Agent results come only from the agent and cannot be overwritten by hand.
- Closing requires a conclusion. The order cannot go to COTIZACION until it is closed.
- Agent pairing: one-time code (30 min) → one-time token (15 min) → one report. Requires a
  computer category and the customer's DIAGNOSTIC_AGENT authorization. Codes and tokens are
  stored as SHA-256 hashes.
"""

import secrets
import uuid
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import (
    AuthenticationError,
    BusinessRuleError,
    NotFoundError,
    PermissionDeniedError,
)
from app.core.security import generate_opaque_token, hash_opaque_token
from app.modules.audit.service import AuditService
from app.modules.customers.service import CustomerService
from app.modules.diagnostics import catalog
from app.modules.diagnostics.agent_schemas import AgentReport, PairResponse
from app.modules.diagnostics.catalog import Result, Source
from app.modules.diagnostics.evaluation import evaluate
from app.modules.diagnostics.models import AgentPairing, DiagnosticResult, DiagnosticSession
from app.modules.diagnostics.schemas import (
    DiagnosticRead,
    PairingCreated,
    ResultInput,
    TestResultRead,
)
from app.modules.privacy.catalog import ConsentPurpose
from app.modules.users.models import User
from app.modules.workorders.catalog import Status
from app.modules.workorders.models import WorkOrder
from app.modules.workorders.schemas import PersonRef
from app.modules.workorders.service import may_work_on
from app.shared.context import RequestContext, utcnow

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O, 1/I: easy to type
CODE_LENGTH = 8
INVALID_CODE = "Código inválido, vencido o ya utilizado."
EDITABLE_STATUSES = frozenset({Status.DIAGNOSTICO})


def normalize_code(raw: str) -> str:
    return "".join(ch for ch in raw.upper() if ch.isalnum())


def new_code() -> str:
    code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
    return f"{code[:4]}-{code[4:]}"


@dataclass(frozen=True, slots=True)
class _Context:
    order: WorkOrder
    category: str


class DiagnosticService:
    def __init__(self, session: Session, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._customers = CustomerService(session)
        self._audit = AuditService(session)

    # --- Queries ------------------------------------------------------------------------

    def view(self, actor: User, order_id: uuid.UUID) -> DiagnosticRead:
        ctx = self._context(actor, order_id)
        session = self._session_for(ctx.order)
        results = {r.test_code: r for r in self._results(session)} if session else {}
        users = self._users(
            {r.recorded_by_id for r in results.values()}
            | {session.closed_by_id if session else None}
        )
        agent_reason = self._agent_unavailable_reason(ctx, session)
        return DiagnosticRead(
            session_id=session.id if session else None,
            state="NOT_STARTED" if session is None else "CLOSED" if session.closed_at else "OPEN",
            editable=self._can_edit(actor, ctx, session),
            agent_available=agent_reason is None,
            agent_unavailable_reason=agent_reason,
            agent_download_url=self._settings.agent_download_url,
            conclusion=session.conclusion if session else None,
            recommendation=session.recommendation if session else None,
            closed_at=session.closed_at if session else None,
            closed_by=_person(users.get(session.closed_by_id))
            if session and session.closed_by_id
            else None,
            agent_version=session.agent_version if session else None,
            agent_elevated=session.agent_elevated if session else None,
            agent_reported_at=session.agent_reported_at if session else None,
            results=[
                TestResultRead(
                    test_code=test.code,
                    name=test.name,
                    component=test.component,
                    automated=test.automated,
                    result=Result(r.result) if (r := results.get(test.code)) else None,
                    observation=r.observation if r else None,
                    evidence=r.evidence if r else None,
                    source=Source(r.source) if r else None,
                    recorded_by=_person(users.get(r.recorded_by_id))
                    if r and r.recorded_by_id
                    else None,
                    recorded_at=r.recorded_at if r else None,
                )
                for test in catalog.tests_for(ctx.category)
            ],
        )

    # --- Technician commands ------------------------------------------------------------

    def save_results(
        self,
        actor: User,
        order_id: uuid.UUID,
        inputs: list[ResultInput],
        context: RequestContext,
    ) -> DiagnosticRead:
        ctx = self._context(actor, order_id, for_update=True)
        session = self._ensure_editable(actor, ctx)
        allowed = {t.code for t in catalog.manual_tests_for(ctx.category)}
        unknown = {i.test_code for i in inputs} - allowed
        if unknown:
            raise BusinessRuleError(
                "Pruebas no válidas para este tipo de equipo: " + ", ".join(sorted(unknown)) + "."
            )
        existing = {r.test_code: r for r in self._results(session)}
        now = utcnow()
        for item in inputs:
            row = existing.get(item.test_code)
            if row is None:
                row = DiagnosticResult(session_id=session.id, test_code=item.test_code)
                self._session.add(row)
            row.result = item.result
            row.observation = item.observation
            row.source = Source.MANUAL
            row.evidence = None
            row.recorded_by_id = actor.id
            row.recorded_at = now
        self._session.flush()
        self._record(
            actor,
            context,
            "diagnostic.results_saved",
            ctx.order,
            {"tests": sorted(i.test_code for i in inputs)},
        )
        return self.view(actor, order_id)

    def close(
        self,
        actor: User,
        order_id: uuid.UUID,
        conclusion: str,
        recommendation: str | None,
        context: RequestContext,
    ) -> DiagnosticRead:
        ctx = self._context(actor, order_id, for_update=True)
        session = self._ensure_editable(actor, ctx)
        recorded = {r.test_code for r in self._results(session)}
        missing = [t.name for t in catalog.manual_tests_for(ctx.category) if t.code not in recorded]
        if missing:
            raise BusinessRuleError(
                "Registre un resultado para todas las pruebas (use 'No probado' si no aplica): "
                + ", ".join(missing)
                + "."
            )
        session.conclusion = conclusion
        session.recommendation = recommendation
        session.closed_at = utcnow()
        session.closed_by_id = actor.id
        self._invalidate_pairings(session)
        self._session.flush()
        self._record(actor, context, "diagnostic.closed", ctx.order, {})
        return self.view(actor, order_id)

    def reopen(self, actor: User, order_id: uuid.UUID, context: RequestContext) -> DiagnosticRead:
        ctx = self._context(actor, order_id, for_update=True)
        self._check_actor(actor, ctx)
        session = self._session_for(ctx.order)
        if session is None or session.closed_at is None:
            raise BusinessRuleError("El diagnóstico no está cerrado.")
        session.closed_at = None
        session.closed_by_id = None
        self._session.flush()
        self._record(actor, context, "diagnostic.reopened", ctx.order, {})
        return self.view(actor, order_id)

    def create_pairing(
        self, actor: User, order_id: uuid.UUID, context: RequestContext
    ) -> PairingCreated:
        ctx = self._context(actor, order_id, for_update=True)
        session = self._ensure_editable(actor, ctx)
        reason = self._agent_unavailable_reason(ctx, session)
        if reason:
            raise BusinessRuleError(reason)
        self._invalidate_pairings(session)
        code = new_code()
        expires_at = utcnow() + timedelta(minutes=self._settings.agent_pairing_minutes)
        self._session.add(
            AgentPairing(
                organization_id=actor.organization_id,
                session_id=session.id,
                code_hash=hash_opaque_token(normalize_code(code)),
                expires_at=expires_at,
                created_by_id=actor.id,
            )
        )
        self._session.flush()
        self._record(actor, context, "diagnostic.agent_pairing_created", ctx.order, {})
        return PairingCreated(
            code=code, expires_at=expires_at, download_url=self._settings.agent_download_url
        )

    # --- Agent commands (no user session; authenticated by code, then by token) ----------

    def agent_pair(self, raw_code: str, context: RequestContext) -> PairResponse:
        now = utcnow()
        pairing = self._session.scalar(
            select(AgentPairing)
            .where(AgentPairing.code_hash == hash_opaque_token(normalize_code(raw_code)))
            .with_for_update()
        )
        if pairing is None or pairing.paired_at is not None or pairing.expires_at <= now:
            raise AuthenticationError(INVALID_CODE)
        token = generate_opaque_token()
        pairing.paired_at = now
        pairing.token_hash = hash_opaque_token(token)
        pairing.token_expires_at = now + timedelta(minutes=self._settings.agent_token_minutes)
        order = self._order_of(pairing)
        self._session.flush()
        self._audit.record(
            "diagnostic.agent_paired",
            entity_type="work_order",
            entity_id=order.id,
            organization_id=pairing.organization_id,
            actor_user_id=None,
            context=context,
        )
        device = order.device
        return PairResponse(
            token=token,
            expires_at=pairing.token_expires_at.isoformat(),
            work_order_number=order.number,
            device=f"{device.model.manufacturer.name} {device.model.name}",
        )

    def agent_report(self, token: str, report: AgentReport, context: RequestContext) -> int:
        now = utcnow()
        pairing = self._session.scalar(
            select(AgentPairing)
            .where(AgentPairing.token_hash == hash_opaque_token(token))
            .with_for_update()
        )
        if (
            pairing is None
            or pairing.reported_at is not None
            or pairing.token_expires_at is None
            or pairing.token_expires_at <= now
        ):
            raise AuthenticationError("La sesión del agente no es válida o ya fue utilizada.")
        session = self._session.get(DiagnosticSession, pairing.session_id)
        order = self._order_of(pairing)
        if session is None or session.closed_at is not None or order.status != Status.DIAGNOSTICO:
            raise BusinessRuleError("El diagnóstico de esta orden ya no admite resultados.")

        existing = {r.test_code: r for r in self._results(session)}
        evaluations = evaluate(report)
        for ev in evaluations:
            row = existing.get(ev.code)
            if row is None:
                row = DiagnosticResult(session_id=session.id, test_code=ev.code)
                self._session.add(row)
            row.result = ev.result
            row.observation = ev.observation
            row.evidence = ev.evidence or None
            row.source = Source.AGENT
            row.recorded_by_id = pairing.created_by_id
            row.recorded_at = now
        session.agent_version = report.agent_version
        session.agent_elevated = report.elevated
        session.agent_reported_at = now
        pairing.reported_at = now
        self._session.flush()
        self._audit.record(
            "diagnostic.agent_reported",
            entity_type="work_order",
            entity_id=order.id,
            organization_id=pairing.organization_id,
            actor_user_id=None,
            context=context,
            changes={"agent_version": report.agent_version, "elevated": report.elevated},
        )
        return len(evaluations)

    # --- Helpers ------------------------------------------------------------------------

    def _context(self, actor: User, order_id: uuid.UUID, *, for_update: bool = False) -> _Context:
        query = select(WorkOrder).where(
            WorkOrder.id == order_id, WorkOrder.organization_id == actor.organization_id
        )
        if for_update:
            query = query.with_for_update(of=WorkOrder)
        order = self._session.scalar(query)
        if order is None:
            raise NotFoundError("La orden de servicio no existe.")
        return _Context(order=order, category=order.device.model.category_code)

    def _session_for(self, order: WorkOrder) -> DiagnosticSession | None:
        return self._session.scalar(
            select(DiagnosticSession).where(DiagnosticSession.work_order_id == order.id)
        )

    def _results(self, session: DiagnosticSession) -> list[DiagnosticResult]:
        return list(
            self._session.scalars(
                select(DiagnosticResult).where(DiagnosticResult.session_id == session.id)
            )
        )

    def _order_of(self, pairing: AgentPairing) -> WorkOrder:
        order = self._session.scalar(
            select(WorkOrder)
            .join(DiagnosticSession, DiagnosticSession.work_order_id == WorkOrder.id)
            .where(DiagnosticSession.id == pairing.session_id)
        )
        assert order is not None  # noqa: S101 - FK guarantees it
        return order

    def _check_actor(self, actor: User, ctx: _Context) -> None:
        if not may_work_on(actor, ctx.order):
            raise PermissionDeniedError("La orden está asignada a otro técnico.")
        if Status(ctx.order.status) not in EDITABLE_STATUSES:
            raise BusinessRuleError("El diagnóstico solo se registra con la orden en DIAGNÓSTICO.")

    def _can_edit(self, actor: User, ctx: _Context, session: DiagnosticSession | None) -> bool:
        return (
            "work_orders:progress" in actor.permission_codes
            and Status(ctx.order.status) in EDITABLE_STATUSES
            and may_work_on(actor, ctx.order)
            and (session is None or session.closed_at is None)
        )

    def _ensure_editable(self, actor: User, ctx: _Context) -> DiagnosticSession:
        self._check_actor(actor, ctx)
        session = self._session_for(ctx.order)
        if session is None:
            session = DiagnosticSession(
                organization_id=ctx.order.organization_id,
                work_order_id=ctx.order.id,
                started_by_id=actor.id,
            )
            self._session.add(session)
            self._session.flush()
        if session.closed_at is not None:
            raise BusinessRuleError("El diagnóstico está cerrado. Reábralo para modificarlo.")
        return session

    def _agent_unavailable_reason(
        self, ctx: _Context, session: DiagnosticSession | None
    ) -> str | None:
        if ctx.category not in catalog.AGENT_CATEGORIES:
            return "El agente solo funciona en computadores con Windows."
        if Status(ctx.order.status) not in EDITABLE_STATUSES:
            return "La orden debe estar en DIAGNÓSTICO."
        if session is not None and session.closed_at is not None:
            return "El diagnóstico está cerrado."
        consents = self._customers.current_consents(ctx.order.customer_id)
        if not any(c.purpose == ConsentPurpose.DIAGNOSTIC_AGENT and c.granted for c in consents):
            return (
                "El cliente no ha autorizado el agente de diagnóstico. Registre la autorización "
                "en su ficha."
            )
        return None

    def _invalidate_pairings(self, session: DiagnosticSession) -> None:
        now = utcnow()
        self._session.execute(
            update(AgentPairing)
            .where(AgentPairing.session_id == session.id, AgentPairing.reported_at.is_(None))
            .values(expires_at=now, token_expires_at=now)
        )

    def _users(self, ids: set[uuid.UUID | None]) -> dict[uuid.UUID, User]:
        wanted = {i for i in ids if i}
        if not wanted:
            return {}
        return {u.id: u for u in self._session.scalars(select(User).where(User.id.in_(wanted)))}

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
            changes=changes or None,
        )


def _person(user: User | None) -> PersonRef | None:
    return PersonRef(id=user.id, full_name=user.full_name) if user else None
