"""Repair tasks, parts consumption and quality control.

- Tasks and parts are recorded with the order EN_REPARACION by whoever may work on it.
- Consuming a part creates an OUT movement (stock never negative); returning it creates a
  RETURN movement. The ledger keeps both.
- Quality control repeats the manual checklist of the device category. It passes when no
  test FAILs; LISTO_ENTREGA requires the latest check to pass (enforced by work orders).
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import BusinessRuleError, NotFoundError, PermissionDeniedError
from app.core.storage import Storage
from app.modules.audit.service import AuditService
from app.modules.diagnostics import catalog as tests_catalog
from app.modules.diagnostics.catalog import Result
from app.modules.inventory.models import Part
from app.modules.inventory.service import InventoryService
from app.modules.repairs.models import QualityCheck, RepairPart, RepairTask
from app.modules.repairs.schemas import (
    ConsumeRequest,
    QcCreate,
    QcRead,
    QcResultRead,
    QcTest,
    RepairOverview,
    RepairPartRead,
    TaskCreate,
    TaskRead,
)
from app.modules.roles.catalog import Perm
from app.modules.users.models import User
from app.modules.workorders.catalog import Status
from app.modules.workorders.models import WorkOrder
from app.modules.workorders.schemas import PersonRef
from app.modules.workorders.service import WorkOrderService, may_work_on
from app.shared.context import RequestContext


class RepairService:
    def __init__(self, session: Session, settings: Settings, storage: Storage) -> None:
        self._session = session
        self._orders = WorkOrderService(session, settings, storage)
        self._inventory = InventoryService(session)
        self._audit = AuditService(session)

    # --- Queries ------------------------------------------------------------------------

    def overview(self, actor: User, order_id: uuid.UUID) -> RepairOverview:
        order = self._orders.get(actor, order_id)
        category = order.device.model.category_code
        tasks = list(
            self._session.scalars(
                select(RepairTask)
                .where(RepairTask.work_order_id == order.id)
                .order_by(RepairTask.created_at, RepairTask.id)
            )
        )
        checks = list(
            self._session.scalars(
                select(QualityCheck)
                .where(QualityCheck.work_order_id == order.id)
                .order_by(QualityCheck.checked_at.desc(), QualityCheck.id.desc())
            )
        )
        allowed = Perm.REPAIRS_MANAGE in actor.permission_codes and may_work_on(actor, order)
        return RepairOverview(
            tasks=[self._task_read(t) for t in tasks],
            quality_checks=[self._qc_read(c) for c in checks],
            qc_tests=[
                QcTest(test_code=t.code, name=t.name)
                for t in tests_catalog.manual_tests_for(category)
            ],
            can_repair=allowed and Status(order.status) is Status.EN_REPARACION,
            can_check=allowed and Status(order.status) is Status.CONTROL_CALIDAD,
        )

    # --- Commands -----------------------------------------------------------------------

    def add_task(
        self, actor: User, order_id: uuid.UUID, data: TaskCreate, context: RequestContext
    ) -> TaskRead:
        order = self._repairable(actor, order_id)
        task = RepairTask(
            organization_id=order.organization_id,
            work_order_id=order.id,
            technician_id=actor.id,
            description=data.description,
            labor_minutes=data.labor_minutes,
        )
        self._session.add(task)
        self._session.flush()
        self._record(actor, context, "repair.task_added", order, {"task_id": str(task.id)})
        return self._task_read(task)

    def consume(
        self,
        actor: User,
        order_id: uuid.UUID,
        task_id: uuid.UUID,
        data: ConsumeRequest,
        context: RequestContext,
    ) -> TaskRead:
        order = self._repairable(actor, order_id)
        task = self._task(order, task_id)
        part = self._inventory.get_part(actor, data.part_id)
        if not part.is_active:
            raise BusinessRuleError("El repuesto está inactivo.")
        movement = self._inventory.consume(actor, part, data.quantity, ("repair_task", task.id))
        self._session.add(
            RepairPart(
                task_id=task.id,
                part_id=part.id,
                quantity=data.quantity,
                unit_cost=part.unit_cost,
                movement_id=movement.id,
            )
        )
        self._session.flush()
        self._record(
            actor,
            context,
            "repair.part_consumed",
            order,
            {
                "sku": part.sku,
                "quantity": data.quantity,
            },
        )
        return self._task_read(task)

    def return_part(
        self,
        actor: User,
        order_id: uuid.UUID,
        task_id: uuid.UUID,
        repair_part_id: uuid.UUID,
        context: RequestContext,
    ) -> TaskRead:
        order = self._repairable(actor, order_id)
        task = self._task(order, task_id)
        used = self._session.scalar(
            select(RepairPart).where(RepairPart.id == repair_part_id, RepairPart.task_id == task.id)
        )
        if used is None:
            raise NotFoundError("El repuesto no está en esta tarea.")
        if used.returned_movement_id is not None:
            raise BusinessRuleError("El repuesto ya fue devuelto al inventario.")
        part = self._inventory.get_part(actor, used.part_id)
        movement = self._inventory.give_back(actor, part, used.quantity, ("repair_task", task.id))
        used.returned_movement_id = movement.id
        self._session.flush()
        self._record(
            actor,
            context,
            "repair.part_returned",
            order,
            {
                "sku": part.sku,
                "quantity": used.quantity,
            },
        )
        return self._task_read(task)

    def quality_check(
        self, actor: User, order_id: uuid.UUID, data: QcCreate, context: RequestContext
    ) -> QcRead:
        order = self._orders.get(actor, order_id, for_update=True)
        self._check_actor(actor, order)
        if Status(order.status) is not Status.CONTROL_CALIDAD:
            raise BusinessRuleError("El control de calidad se registra en Control de calidad.")
        expected = {
            t.code for t in tests_catalog.manual_tests_for(order.device.model.category_code)
        }
        given = {r.test_code for r in data.results}
        if given != expected:
            missing = expected - given
            unknown = given - expected
            detail = []
            if missing:
                detail.append("faltan " + ", ".join(sorted(missing)))
            if unknown:
                detail.append("no aplican " + ", ".join(sorted(unknown)))
            raise BusinessRuleError(
                "Registre todas las pruebas del control de calidad (" + "; ".join(detail) + ")."
            )
        passed = not any(r.result == Result.FAIL for r in data.results)
        check = QualityCheck(
            organization_id=order.organization_id,
            work_order_id=order.id,
            passed=passed,
            results=[r.model_dump(mode="json") for r in data.results],
            notes=data.notes,
            checked_by_id=actor.id,
        )
        self._session.add(check)
        self._session.flush()
        self._record(actor, context, "repair.quality_checked", order, {"passed": passed})
        return self._qc_read(check)

    # --- Helpers ------------------------------------------------------------------------

    def _repairable(self, actor: User, order_id: uuid.UUID) -> WorkOrder:
        order = self._orders.get(actor, order_id, for_update=True)
        self._check_actor(actor, order)
        if Status(order.status) is not Status.EN_REPARACION:
            raise BusinessRuleError("Las reparaciones se registran con la orden En reparación.")
        return order

    @staticmethod
    def _check_actor(actor: User, order: WorkOrder) -> None:
        if Perm.REPAIRS_MANAGE not in actor.permission_codes:
            raise PermissionDeniedError("No tiene permisos para registrar reparaciones.")
        if not may_work_on(actor, order):
            raise PermissionDeniedError("La orden está asignada a otro técnico.")

    def _task(self, order: WorkOrder, task_id: uuid.UUID) -> RepairTask:
        task = self._session.scalar(
            select(RepairTask).where(RepairTask.id == task_id, RepairTask.work_order_id == order.id)
        )
        if task is None:
            raise NotFoundError("La tarea no existe.")
        return task

    def _person(self, user_id: uuid.UUID | None) -> PersonRef | None:
        user = self._session.get(User, user_id) if user_id else None
        return PersonRef(id=user.id, full_name=user.full_name) if user else None

    def _task_read(self, task: RepairTask) -> TaskRead:
        rows = self._session.execute(
            select(RepairPart, Part)
            .join(Part, Part.id == RepairPart.part_id)
            .where(RepairPart.task_id == task.id)
            .order_by(RepairPart.id)
        ).all()
        return TaskRead(
            id=task.id,
            description=task.description,
            labor_minutes=task.labor_minutes,
            technician=self._person(task.technician_id),
            created_at=task.created_at,
            parts=[
                RepairPartRead(
                    id=used.id,
                    part_id=part.id,
                    sku=part.sku,
                    name=part.name,
                    quantity=used.quantity,
                    unit_cost=used.unit_cost,
                    returned=used.returned_movement_id is not None,
                )
                for used, part in rows
            ],
        )

    def _qc_read(self, check: QualityCheck) -> QcRead:
        return QcRead(
            id=check.id,
            passed=check.passed,
            results=[
                QcResultRead(
                    test_code=r["test_code"],
                    name=tests_catalog.ALL_TESTS[r["test_code"]].name
                    if r["test_code"] in tests_catalog.ALL_TESTS
                    else r["test_code"],
                    result=r["result"],
                    observation=r.get("observation"),
                )
                for r in check.results
            ],
            notes=check.notes,
            checked_by=self._person(check.checked_by_id),
            checked_at=check.checked_at,
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
