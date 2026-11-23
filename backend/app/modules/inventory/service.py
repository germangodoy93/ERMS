"""Parts catalog and stock.

Every stock change goes through `_move`: it locks the part's stock row, refuses to go below
zero and writes an append-only movement with the resulting stock. Two technicians can never
consume the same last unit.
"""

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.modules.audit.service import AuditService
from app.modules.inventory.models import (
    InventoryMovement,
    Part,
    StockEntry,
    StockLevel,
    Supplier,
)
from app.modules.inventory.schemas import (
    AdjustmentCreate,
    MovementRead,
    PartRead,
    PartWrite,
    StockEntryCreate,
    StockEntryRead,
    SupplierWrite,
)
from app.modules.users.models import User
from app.modules.users.repository import escape_like
from app.modules.workorders.schemas import PersonRef
from app.shared.context import RequestContext
from app.shared.sequences import default_branch


class InventoryService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._audit = AuditService(session)

    # --- Suppliers ----------------------------------------------------------------------

    def suppliers(self, actor: User, *, include_inactive: bool) -> list[Supplier]:
        query = select(Supplier).where(Supplier.organization_id == actor.organization_id)
        if not include_inactive:
            query = query.where(Supplier.is_active.is_(True))
        return list(self._session.scalars(query.order_by(func.lower(Supplier.name))))

    def save_supplier(
        self,
        actor: User,
        data: SupplierWrite,
        context: RequestContext,
        supplier_id: uuid.UUID | None = None,
    ) -> Supplier:
        duplicate = select(Supplier.id).where(
            Supplier.organization_id == actor.organization_id,
            func.lower(Supplier.name) == data.name.lower(),
        )
        if supplier_id:
            duplicate = duplicate.where(Supplier.id != supplier_id)
        if self._session.scalar(duplicate):
            raise ConflictError(f"El proveedor {data.name} ya existe.")
        if supplier_id:
            supplier = self._get_supplier(actor, supplier_id)
        else:
            supplier = Supplier(organization_id=actor.organization_id)
            self._session.add(supplier)
        for field, value in data.model_dump().items():
            setattr(supplier, field, value)
        self._session.flush()
        self._record(
            actor,
            context,
            "inventory.supplier_saved",
            "supplier",
            supplier.id,
            {"name": supplier.name},
        )
        return supplier

    def _get_supplier(self, actor: User, supplier_id: uuid.UUID) -> Supplier:
        supplier = self._session.scalar(
            select(Supplier).where(
                Supplier.id == supplier_id, Supplier.organization_id == actor.organization_id
            )
        )
        if supplier is None:
            raise NotFoundError("El proveedor no existe.")
        return supplier

    # --- Parts --------------------------------------------------------------------------

    def search(
        self,
        actor: User,
        *,
        search: str | None,
        low_stock: bool,
        include_inactive: bool,
    ) -> list[PartRead]:
        stock = self._stock_subquery(actor)
        query = (
            select(Part, func.coalesce(stock.c.quantity, 0))
            .outerjoin(stock, stock.c.part_id == Part.id)
            .where(Part.organization_id == actor.organization_id)
        )
        if search and search.strip():
            pattern = f"%{escape_like(search.strip())}%"
            query = query.where(
                or_(Part.sku.ilike(pattern, escape="\\"), Part.name.ilike(pattern, escape="\\"))
            )
        if not include_inactive:
            query = query.where(Part.is_active.is_(True))
        if low_stock:
            query = query.where(func.coalesce(stock.c.quantity, 0) <= Part.min_stock)
        rows = self._session.execute(query.order_by(func.lower(Part.name)).limit(500)).all()
        return [_part_read(part, quantity) for part, quantity in rows]

    def get_part(self, actor: User, part_id: uuid.UUID) -> Part:
        part = self._session.scalar(
            select(Part).where(Part.id == part_id, Part.organization_id == actor.organization_id)
        )
        if part is None:
            raise NotFoundError("El repuesto no existe.")
        return part

    def read_part(self, actor: User, part_id: uuid.UUID) -> PartRead:
        part = self.get_part(actor, part_id)
        return _part_read(part, self.stock_of(actor, part.id))

    def save_part(
        self,
        actor: User,
        data: PartWrite,
        context: RequestContext,
        part_id: uuid.UUID | None = None,
    ) -> PartRead:
        duplicate = select(Part.id).where(
            Part.organization_id == actor.organization_id, Part.sku == data.sku
        )
        if part_id:
            duplicate = duplicate.where(Part.id != part_id)
        if self._session.scalar(duplicate):
            raise ConflictError(f"Ya existe un repuesto con el código {data.sku}.")
        if part_id:
            part = self.get_part(actor, part_id)
        else:
            part = Part(organization_id=actor.organization_id)
            self._session.add(part)
        # The assembly fields are only touched when sent, so older clients keep the specs.
        keep = {"assembly_category", "specs"} - data.model_fields_set
        for field, value in data.model_dump(exclude=keep).items():
            setattr(part, field, Decimal(value) if field == "tax_rate" else value)
        self._session.flush()
        self._record(actor, context, "inventory.part_saved", "part", part.id, {"sku": part.sku})
        return _part_read(part, self.stock_of(actor, part.id))

    def stock_of(self, actor: User, part_id: uuid.UUID) -> int:
        branch = self._branch(actor)
        return (
            self._session.scalar(
                select(StockLevel.quantity).where(
                    StockLevel.part_id == part_id, StockLevel.branch_id == branch
                )
            )
            or 0
        )

    # --- Movements ----------------------------------------------------------------------

    def receive(
        self, actor: User, data: StockEntryCreate, context: RequestContext
    ) -> StockEntryRead:
        supplier = self._get_supplier(actor, data.supplier_id) if data.supplier_id else None
        branch = self._branch(actor)
        entry = StockEntry(
            organization_id=actor.organization_id,
            branch_id=branch,
            supplier_id=supplier.id if supplier else None,
            invoice_number=data.invoice_number,
            received_on=data.received_on,
            notes=data.notes,
            created_by_id=actor.id,
        )
        self._session.add(entry)
        self._session.flush()
        total = Decimal("0")
        for line in data.lines:
            part = self.get_part(actor, line.part_id)
            self._move(
                actor,
                part,
                "IN",
                line.quantity,
                unit_cost=line.unit_cost,
                reference=("stock_entry", entry.id),
            )
            part.unit_cost = line.unit_cost  # last purchase cost
            total += line.unit_cost * line.quantity
        self._record(
            actor,
            context,
            "inventory.stock_received",
            "stock_entry",
            entry.id,
            {
                "lines": len(data.lines),
                "invoice_number": data.invoice_number,
            },
        )
        return StockEntryRead(
            id=entry.id,
            supplier=supplier.name if supplier else None,
            invoice_number=entry.invoice_number,
            received_on=entry.received_on,
            lines=len(data.lines),
            total_cost=total,
        )

    def adjust(
        self, actor: User, part_id: uuid.UUID, data: AdjustmentCreate, context: RequestContext
    ) -> PartRead:
        part = self.get_part(actor, part_id)
        current = self._lock_stock(actor, part).quantity
        delta = data.counted_quantity - current
        if delta == 0:
            raise BusinessRuleError("La cantidad contada es igual a la existencia actual.")
        self._move(actor, part, "ADJUSTMENT", delta, reason=data.reason)
        self._record(
            actor,
            context,
            "inventory.adjusted",
            "part",
            part.id,
            {
                "from": current,
                "to": data.counted_quantity,
            },
        )
        return _part_read(part, data.counted_quantity)

    def consume(
        self, actor: User, part: Part, quantity: int, reference: tuple[str, uuid.UUID]
    ) -> InventoryMovement:
        return self._move(
            actor, part, "OUT", -quantity, unit_cost=part.unit_cost, reference=reference
        )

    def give_back(
        self, actor: User, part: Part, quantity: int, reference: tuple[str, uuid.UUID]
    ) -> InventoryMovement:
        return self._move(
            actor, part, "RETURN", quantity, unit_cost=part.unit_cost, reference=reference
        )

    def movements(self, actor: User, part_id: uuid.UUID) -> list[MovementRead]:
        part = self.get_part(actor, part_id)
        rows = self._session.execute(
            select(InventoryMovement, User)
            .outerjoin(User, User.id == InventoryMovement.created_by_id)
            .where(InventoryMovement.part_id == part.id)
            .order_by(InventoryMovement.created_at.desc(), InventoryMovement.id.desc())
            .limit(200)
        ).all()
        return [
            MovementRead(
                id=m.id,
                kind=m.kind,
                quantity=m.quantity,
                stock_after=m.stock_after,
                unit_cost=m.unit_cost,
                reference_type=m.reference_type,
                reference_id=m.reference_id,
                reference_label=self._reference_label(m),
                reason=m.reason,
                created_by=PersonRef(id=u.id, full_name=u.full_name) if u else None,
                created_at=m.created_at,
            )
            for m, u in rows
        ]

    # --- Internals ----------------------------------------------------------------------

    def _branch(self, actor: User) -> uuid.UUID:
        branch = default_branch(self._session, actor.organization_id)
        if branch is None:
            raise BusinessRuleError("El taller no tiene una sede activa.")
        return branch.id

    def _lock_stock(self, actor: User, part: Part) -> StockLevel:
        branch = self._branch(actor)
        self._session.execute(
            text(
                "INSERT INTO stock_levels (id, part_id, branch_id, quantity) "
                "VALUES (:id, :part, :branch, 0) ON CONFLICT (part_id, branch_id) DO NOTHING"
            ),
            {"id": uuid.uuid4(), "part": part.id, "branch": branch},
        )
        level = self._session.scalar(
            select(StockLevel)
            .where(StockLevel.part_id == part.id, StockLevel.branch_id == branch)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        assert level is not None  # noqa: S101 - inserted above
        return level

    def _move(
        self,
        actor: User,
        part: Part,
        kind: str,
        quantity: int,
        *,
        unit_cost: Decimal | None = None,
        reference: tuple[str, uuid.UUID] | None = None,
        reason: str | None = None,
    ) -> InventoryMovement:
        level = self._lock_stock(actor, part)
        new_quantity = level.quantity + quantity
        if new_quantity < 0:
            raise BusinessRuleError(
                f"Existencia insuficiente de {part.name}: hay {level.quantity}, "
                f"se necesitan {-quantity}."
            )
        level.quantity = new_quantity
        movement = InventoryMovement(
            organization_id=actor.organization_id,
            part_id=part.id,
            branch_id=level.branch_id,
            kind=kind,
            quantity=quantity,
            stock_after=new_quantity,
            unit_cost=unit_cost,
            reference_type=reference[0] if reference else None,
            reference_id=reference[1] if reference else None,
            reason=reason,
            created_by_id=actor.id,
        )
        self._session.add(movement)
        self._session.flush()
        return movement

    def _stock_subquery(self, actor: User) -> Any:
        branch = self._branch(actor)
        return (
            select(StockLevel.part_id, StockLevel.quantity)
            .where(StockLevel.branch_id == branch)
            .subquery()
        )

    def _reference_label(self, movement: InventoryMovement) -> str | None:
        if movement.reference_type == "stock_entry" and movement.reference_id:
            entry = self._session.get(StockEntry, movement.reference_id)
            return (
                f"Factura {entry.invoice_number}" if entry and entry.invoice_number else "Entrada"
            )
        if movement.reference_type == "repair_task" and movement.reference_id:
            from app.modules.repairs.models import RepairTask
            from app.modules.workorders.models import WorkOrder

            number = self._session.scalar(
                select(WorkOrder.number)
                .join(RepairTask, RepairTask.work_order_id == WorkOrder.id)
                .where(RepairTask.id == movement.reference_id)
            )
            return f"Orden {number}" if number else None
        return None

    def _record(
        self,
        actor: User,
        context: RequestContext,
        action: str,
        entity_type: str,
        entity_id: uuid.UUID,
        changes: dict[str, Any],
    ) -> None:
        self._audit.record(
            action,
            entity_type=entity_type,
            entity_id=entity_id,
            organization_id=actor.organization_id,
            actor_user_id=actor.id,
            context=context,
            changes=changes,
        )


def _part_read(part: Part, stock: int) -> PartRead:
    return PartRead(
        id=part.id,
        sku=part.sku,
        name=part.name,
        kind=part.kind,
        unit_cost=part.unit_cost,
        sale_price=part.sale_price,
        tax_rate=int(part.tax_rate),
        price_includes_tax=part.price_includes_tax,
        min_stock=part.min_stock,
        notes=part.notes,
        is_active=part.is_active,
        stock=stock,
        low_stock=stock <= part.min_stock,
        assembly_category=part.assembly_category,
        specs=part.specs,
    )
