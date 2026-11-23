"""PC assembly: configurator, saved builds and assembly orders.

- The catalog is the inventory: parts with an `assembly_category` and validated `specs`.
- `evaluate` runs the compatibility and bottleneck rules (rules.py) on a selection.
- A ready build becomes an ASSEMBLY work order for a customer: it skips inspection and
  diagnosis and starts in COTIZACION with a draft quote of the parts plus the assembly labor.
  From there it follows the normal flow (send, approve, assembly, QC, payment, delivery,
  warranty).
- During EN_REPARACION the technician ticks the assembly checklist in the real order and
  consumes all the parts from inventory in one step.
"""

import csv
import io
import unicodedata
import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import BusinessRuleError, NotFoundError, PermissionDeniedError
from app.core.storage import Storage
from app.modules.assembly.catalog import (
    CATEGORY_LABELS,
    AssemblyCategory,
    UseProfile,
    validate_specs,
)
from app.modules.assembly.models import AssemblyBuild, AssemblyBuildItem
from app.modules.assembly.pricing import apply_price, parse_pesos
from app.modules.assembly.rules import (
    Build,
    Evaluation,
    Piece,
    Thresholds,
    blocked_reason,
    evaluate,
    incompatibility,
    steps_for,
)
from app.modules.assembly.schemas import (
    AssemblyChecklist,
    BuildRead,
    BuildSummary,
    BuildWrite,
    CatalogImport,
    CatalogImportResult,
    CatalogPart,
    CostUpdateResult,
    EvaluateRequest,
    EvaluationOut,
    IssueOut,
    Selection,
    StepOut,
)
from app.modules.audit.service import AuditService
from app.modules.devices.models import Device, DeviceModel, Manufacturer
from app.modules.inventory.models import Part, StockLevel
from app.modules.organizations.models import Organization
from app.modules.quotes.schemas import QuoteItemInput, QuoteSave
from app.modules.quotes.service import QuoteService
from app.modules.repairs.models import RepairTask
from app.modules.repairs.schemas import ConsumeRequest, TaskCreate
from app.modules.repairs.service import RepairService
from app.modules.roles.catalog import Perm
from app.modules.users.models import User
from app.modules.workorders.catalog import Status, UnlockMethod
from app.modules.workorders.models import WorkOrder
from app.modules.workorders.schemas import PersonRef, WorkOrderCreate, WorkOrderRead
from app.modules.workorders.service import WorkOrderService, may_work_on
from app.shared.context import RequestContext
from app.shared.spreadsheet import safe_cell

ASSEMBLY_MANUFACTURER = "Ensamble del taller"
ASSEMBLY_MODEL = "PC armada a la medida"
ASSEMBLY_TASK = "Ensamble de PC a la medida"
BOM = chr(0xFEFF)  # Excel needs it to read UTF-8 accents
CRLF = chr(13) + chr(10)
COST_HEADER = ["Código", "Nombre", "Categoría", "Costo", "Precio de venta", "Precio fijado a mano"]
SINGLE: dict[AssemblyCategory, str] = {
    AssemblyCategory.CPU: "cpu",
    AssemblyCategory.BOARD: "board",
    AssemblyCategory.RAM: "ram",
    AssemblyCategory.GPU: "gpu",
    AssemblyCategory.PSU: "psu",
    AssemblyCategory.CASE: "case",
    AssemblyCategory.COOLER: "cooler",
}


class AssemblyService:
    def __init__(self, session: Session, settings: Settings, storage: Storage) -> None:
        self._session = session
        self._orders = WorkOrderService(session, settings, storage)
        self._quotes = QuoteService(session, settings, storage)
        self._repairs = RepairService(session, settings, storage)
        self._audit = AuditService(session)

    # --- Catalog -----------------------------------------------------------------------
    def catalog(self, actor: User) -> list[CatalogPart]:
        stock = (
            select(StockLevel.part_id, func.sum(StockLevel.quantity).label("quantity"))
            .group_by(StockLevel.part_id)
            .subquery()
        )
        rows = self._session.execute(
            select(Part, func.coalesce(stock.c.quantity, 0))
            .outerjoin(stock, stock.c.part_id == Part.id)
            .where(
                Part.organization_id == actor.organization_id,
                Part.assembly_category.is_not(None),
                Part.is_active.is_(True),
            )
            .order_by(Part.assembly_category, Part.sale_price, Part.name)
        ).all()
        return [
            CatalogPart(
                id=p.id,
                sku=p.sku,
                name=p.name,
                category=AssemblyCategory(p.assembly_category),
                sale_price=p.sale_price,
                stock=int(qty),
                specs=p.specs or {},
            )
            for p, qty in rows
        ]

    def import_catalog(
        self, actor: User, data: CatalogImport, context: RequestContext
    ) -> CatalogImportResult:
        """Creates or updates parts by SKU with the supplier cost (VAT included); the sale price
        is cost + margin unless fixed by hand. Stock is not touched."""
        existing = {
            p.sku: p
            for p in self._session.scalars(
                select(Part).where(
                    Part.organization_id == actor.organization_id,
                    Part.sku.in_([i.sku.upper() for i in data.items]),
                )
            )
        }
        created = updated = 0
        errors: list[str] = []
        margin = self._margin(actor)
        for item in data.items:
            sku = item.sku.strip().upper().replace(" ", "-")
            try:
                specs = validate_specs(item.category, item.specs)
            except ValueError as exc:
                errors.append(f"{sku}: {exc}")
                continue
            part = existing.get(sku)
            if part is None:
                part = Part(
                    organization_id=actor.organization_id,
                    sku=sku,
                    kind="COMPONENT",
                    unit_cost=Decimal("0"),
                    tax_rate=Decimal("19"),
                    price_includes_tax=True,
                    min_stock=0,
                    is_active=True,
                )
                self._session.add(part)
                existing[sku] = part
                created += 1
            else:
                updated += 1
            part.name = item.name.strip()
            part.unit_cost = item.cost
            part.assembly_category = item.category.value
            part.specs = specs
            apply_price(part, margin)
        self._session.flush()
        self._audit.record(
            "assembly.catalog_imported",
            entity_type="part",
            entity_id=None,
            organization_id=actor.organization_id,
            actor_user_id=actor.id,
            context=context,
            changes={"created": created, "updated": updated, "rejected": len(errors)},
        )
        return CatalogImportResult(created=created, updated=updated, errors=errors)

    def cost_template(self, actor: User) -> bytes:
        """CSV for Excel (UTF-8 with BOM, ";") with every assembly part and its current cost."""
        rows = self._session.scalars(
            select(Part)
            .where(
                Part.organization_id == actor.organization_id,
                Part.assembly_category.is_not(None),
            )
            .order_by(Part.assembly_category, Part.name)
        )
        out = io.StringIO()
        writer = csv.writer(out, delimiter=";", lineterminator=CRLF)
        writer.writerow(COST_HEADER)
        for p in rows:
            writer.writerow(
                [
                    safe_cell(p.sku),
                    safe_cell(p.name),
                    CATEGORY_LABELS[AssemblyCategory(str(p.assembly_category))],
                    f"{p.unit_cost:.0f}",
                    f"{p.sale_price:.0f}",
                    "Sí" if p.price_locked else "No",
                ]
            )
        return (BOM + out.getvalue()).encode("utf-8")

    def update_costs(
        self, actor: User, content: bytes, context: RequestContext
    ) -> CostUpdateResult:
        """Reads "Código" and "Costo" from a CSV saved by Excel and updates the costs; the sale
        prices follow the margin unless fixed by hand."""
        rows = _read_csv(content)
        if not rows:
            raise BusinessRuleError("El archivo está vacío.")
        header = [_norm(h) for h in rows[0]]
        try:
            code_col = next(i for i, h in enumerate(header) if h in ("codigo", "sku"))
            cost_col = next(i for i, h in enumerate(header) if h in ("costo", "cost"))
        except StopIteration:
            raise BusinessRuleError(
                "El archivo debe tener las columnas Código y Costo (use la plantilla)."
            ) from None
        parts = {
            p.sku: p
            for p in self._session.scalars(
                select(Part).where(
                    Part.organization_id == actor.organization_id,
                    Part.assembly_category.is_not(None),
                )
            )
        }
        margin = self._margin(actor)
        updated = unchanged = 0
        unknown: list[str] = []
        errors: list[str] = []
        for number, row in enumerate(rows[1:], start=2):
            if not any(cell.strip() for cell in row):
                continue
            code = row[code_col].strip().upper() if len(row) > code_col else ""
            cost = parse_pesos(row[cost_col]) if len(row) > cost_col else None
            if not code:
                errors.append(f"Fila {number}: falta el código.")
                continue
            part = parts.get(code)
            if part is None:
                unknown.append(code)
                continue
            if cost is None or cost <= 0 or cost >= Decimal("1e12"):
                errors.append(f"Fila {number} ({code}): costo inválido.")
                continue
            if part.unit_cost == cost:
                unchanged += 1
                continue
            part.unit_cost = cost
            apply_price(part, margin)
            updated += 1
        self._session.flush()
        self._audit.record(
            "assembly.costs_updated",
            entity_type="part",
            entity_id=None,
            organization_id=actor.organization_id,
            actor_user_id=actor.id,
            context=context,
            changes={"updated": updated, "unknown": len(unknown), "errors": len(errors)},
        )
        return CostUpdateResult(
            updated=updated, unchanged=unchanged, unknown=unknown, errors=errors
        )

    # --- Evaluation --------------------------------------------------------------------
    def evaluate(self, actor: User, data: EvaluateRequest) -> EvaluationOut:
        build = self._resolve(actor, data.selection)
        limits = self._limits(actor)
        result = evaluate(build, data.profile, limits)
        out = self._evaluation_out(result)
        if data.candidates_for is not None:
            for part in self._parts_of(actor, data.candidates_for):
                reason = incompatibility(build, part, data.profile, limits)
                if reason:
                    out.candidates[part.id] = reason
        return out

    # --- Builds ------------------------------------------------------------------------
    def builds(self, actor: User) -> list[BuildSummary]:
        rows = self._session.scalars(
            select(AssemblyBuild)
            .where(AssemblyBuild.organization_id == actor.organization_id)
            .order_by(AssemblyBuild.updated_at.desc())
            .limit(200)
        )
        return [self._summary(actor, b) for b in rows]

    def read(self, actor: User, build_id: uuid.UUID) -> BuildRead:
        return self._read(actor, self._get(actor, build_id))

    def save(
        self,
        actor: User,
        data: BuildWrite,
        context: RequestContext,
        build_id: uuid.UUID | None = None,
    ) -> BuildRead:
        self._resolve(actor, data.selection)  # every part must exist and fit its slot
        if build_id is None:
            build = AssemblyBuild(
                organization_id=actor.organization_id,
                status="DRAFT",
                created_by_id=actor.id,
            )
            self._session.add(build)
        else:
            build = self._get(actor, build_id, for_update=True)
            if build.status != "DRAFT":
                raise BusinessRuleError("La configuración ya tiene una orden: no se puede cambiar.")
        build.name = data.name
        build.profile = data.profile.value
        build.ram_units = data.selection.ram_units
        build.labor_price = data.labor_price
        build.notes = data.notes
        build.items = [AssemblyBuildItem(part_id=pid) for pid in _ordered_ids(data.selection)]
        self._session.flush()
        self._audit.record(
            "assembly.build_saved",
            entity_type="assembly_build",
            entity_id=build.id,
            organization_id=actor.organization_id,
            actor_user_id=actor.id,
            context=context,
            changes={"name": build.name, "parts": len(build.items)},
        )
        return self._read(actor, build)

    def delete(self, actor: User, build_id: uuid.UUID, context: RequestContext) -> None:
        build = self._get(actor, build_id, for_update=True)
        if build.status != "DRAFT":
            raise BusinessRuleError("No se puede borrar una configuración con orden.")
        self._session.delete(build)
        self._audit.record(
            "assembly.build_deleted",
            entity_type="assembly_build",
            entity_id=build_id,
            organization_id=actor.organization_id,
            actor_user_id=actor.id,
            context=context,
            changes={"name": build.name},
        )

    def create_order(
        self, actor: User, build_id: uuid.UUID, customer_id: uuid.UUID, context: RequestContext
    ) -> WorkOrderRead:
        build = self._get(actor, build_id, for_update=True)
        if build.status != "DRAFT":
            raise BusinessRuleError("Esta configuración ya tiene una orden.")
        pieces = self._build_of(actor, build)
        result = evaluate(pieces, UseProfile(build.profile), self._limits(actor))
        if result.missing:
            names = ", ".join(CATEGORY_LABELS[c] for c in result.missing)
            raise BusinessRuleError(f"Complete la configuración. Falta: {names}.")
        if result.errors:
            raise BusinessRuleError(
                f"La configuración no es compatible: {result.errors[0].message}"
            )

        device = self._new_device(actor, customer_id, build)
        created = self._orders.create(
            actor,
            WorkOrderCreate(
                customer_id=customer_id,
                device_id=device.id,
                reported_issue=f"Ensamble de PC a la medida: {build.name}.",
                physical_condition="Equipo nuevo, por ensamblar.",
                unlock_method=UnlockMethod.NOT_REQUIRED,
                diagnostic_fee=Decimal("0"),
                advance_amount=Decimal("0"),
                notes=build.notes,
            ),
            context,
        )
        order = self._orders.get(actor, created.id, for_update=True)
        order.kind = "ASSEMBLY"
        build.status = "ORDERED"
        build.work_order_id = order.id
        self._session.flush()
        self._orders.transition(actor, order, Status.COTIZACION, None, context)

        quote = self._quotes.create_draft(actor, order.id, context)
        items = [
            QuoteItemInput(
                kind="PART",
                part_id=p.id,
                description=p.name,
                quantity=Decimal(build.ram_units if p.category is AssemblyCategory.RAM else 1),
                unit_price=p.price,
                apply_tax=True,
                price_includes_tax=True,
            )
            for p in _pieces(pieces)
        ]
        items.append(
            QuoteItemInput(
                kind="LABOR",
                description="Ensamble, cableado y pruebas del equipo",
                quantity=Decimal("1"),
                unit_price=build.labor_price,
            )
        )
        self._quotes.save(
            actor,
            order.id,
            quote.id,
            QuoteSave(items=items, notes=f"PC a la medida: {build.name}."),
            context,
        )
        self._audit.record(
            "assembly.order_created",
            entity_type="assembly_build",
            entity_id=build.id,
            organization_id=actor.organization_id,
            actor_user_id=actor.id,
            context=context,
            changes={"work_order": order.number},
        )
        return self._orders.read(actor, order.id)

    # --- Checklist ---------------------------------------------------------------------
    def checklist(self, actor: User, order_id: uuid.UUID) -> AssemblyChecklist:
        order = self._orders.get(actor, order_id)
        build = self._build_for_order(actor, order)
        done = set(build.steps_done)
        steps = steps_for(self._build_of(actor, build))
        return AssemblyChecklist(
            build_id=build.id,
            build_name=build.name,
            steps=[
                StepOut(
                    code=s.code,
                    title=s.title,
                    done=s.code in done,
                    blocked_reason=None if s.code in done else blocked_reason(s, done),
                )
                for s in steps
            ],
            parts_consumed=self._consumed(order),
            can_work=self._can_work(actor, order),
        )

    def complete_step(
        self, actor: User, order_id: uuid.UUID, code: str, context: RequestContext
    ) -> AssemblyChecklist:
        order = self._orders.get(actor, order_id, for_update=True)
        self._require_work(actor, order)
        build = self._build_for_order(actor, order)
        steps = {s.code: s for s in steps_for(self._build_of(actor, build))}
        step = steps.get(code)
        if step is None:
            raise NotFoundError("Ese paso no existe en este ensamble.")
        done = set(build.steps_done)
        if code in done:
            raise BusinessRuleError("Ese paso ya está hecho.")
        reason = blocked_reason(step, done)
        if reason:
            raise BusinessRuleError(reason)
        if code == "cpu" and not self._consumed(order):
            raise BusinessRuleError("Primero descuente las piezas del inventario.")
        build.steps_done = [*build.steps_done, code]
        self._session.flush()
        self._audit.record(
            "assembly.step_done",
            entity_type="work_order",
            entity_id=order.id,
            organization_id=actor.organization_id,
            actor_user_id=actor.id,
            context=context,
            changes={"step": code},
        )
        return self.checklist(actor, order_id)

    def consume_parts(
        self, actor: User, order_id: uuid.UUID, context: RequestContext
    ) -> AssemblyChecklist:
        """Takes every part of the build out of inventory in one go (all or nothing)."""
        order = self._orders.get(actor, order_id, for_update=True)
        self._require_work(actor, order)
        if self._consumed(order):
            raise BusinessRuleError("Las piezas ya se descontaron del inventario.")
        build = self._build_for_order(actor, order)
        pieces = self._build_of(actor, build)
        task = self._repairs.add_task(
            actor, order.id, TaskCreate(description=ASSEMBLY_TASK), context
        )
        for piece in _pieces(pieces):
            qty = build.ram_units if piece.category is AssemblyCategory.RAM else 1
            self._repairs.consume(
                actor, order.id, task.id, ConsumeRequest(part_id=piece.id, quantity=qty), context
            )
        return self.checklist(actor, order_id)

    # --- Helpers -----------------------------------------------------------------------
    def _margin(self, actor: User) -> Decimal:
        org = self._session.get(Organization, actor.organization_id)
        assert org is not None  # noqa: S101 - the actor belongs to it
        return org.assembly_margin_percent

    def _limits(self, actor: User) -> Thresholds:
        org = self._session.get(Organization, actor.organization_id)
        assert org is not None  # noqa: S101 - the actor belongs to it
        return Thresholds(
            bottleneck_gap=org.assembly_bottleneck_gap, min_ram_gb=org.assembly_min_ram_gb
        )

    def _parts_of(self, actor: User, category: AssemblyCategory) -> list[Piece]:
        rows = self._session.scalars(
            select(Part).where(
                Part.organization_id == actor.organization_id,
                Part.assembly_category == category.value,
                Part.is_active.is_(True),
            )
        )
        return [_piece(p) for p in rows]

    def _resolve(self, actor: User, selection: Selection) -> Build:
        ids = selection.part_ids()
        parts = {
            p.id: p
            for p in self._session.scalars(
                select(Part).where(Part.organization_id == actor.organization_id, Part.id.in_(ids))
            )
        }
        missing = ids - parts.keys()
        if missing:
            raise NotFoundError("Una de las piezas elegidas no existe.")
        build = Build(ram_units=selection.ram_units)
        for category, attr in SINGLE.items():
            pid = getattr(selection, attr)
            if pid:
                setattr(build, attr, self._check_slot(parts[pid], category))
        build.storage = [
            self._check_slot(parts[pid], AssemblyCategory.STORAGE) for pid in selection.storage
        ]
        build.rgb = [self._check_slot(parts[pid], AssemblyCategory.RGB) for pid in selection.rgb]
        return build

    @staticmethod
    def _check_slot(part: Part, category: AssemblyCategory) -> Piece:
        if part.assembly_category != category.value:
            raise BusinessRuleError(
                f"{part.name} no es una pieza de la categoría {CATEGORY_LABELS[category]}."
            )
        return _piece(part)

    def _build_of(self, actor: User, build: AssemblyBuild) -> Build:
        return self._resolve(actor, _selection(build, self._session))

    def _get(self, actor: User, build_id: uuid.UUID, *, for_update: bool = False) -> AssemblyBuild:
        query = select(AssemblyBuild).where(
            AssemblyBuild.id == build_id, AssemblyBuild.organization_id == actor.organization_id
        )
        if for_update:
            query = query.with_for_update()
        build = self._session.scalar(query)
        if build is None:
            raise NotFoundError("La configuración no existe.")
        return build

    def _build_for_order(self, actor: User, order: WorkOrder) -> AssemblyBuild:
        build = self._session.scalar(
            select(AssemblyBuild).where(
                AssemblyBuild.work_order_id == order.id,
                AssemblyBuild.organization_id == actor.organization_id,
            )
        )
        if build is None:
            raise NotFoundError("Esta orden no es de ensamble.")
        return build

    def _consumed(self, order: WorkOrder) -> bool:
        return (
            self._session.scalar(
                select(RepairTask.id).where(
                    RepairTask.work_order_id == order.id, RepairTask.description == ASSEMBLY_TASK
                )
            )
            is not None
        )

    @staticmethod
    def _can_work(actor: User, order: WorkOrder) -> bool:
        return (
            order.status == Status.EN_REPARACION.value
            and Perm.REPAIRS_MANAGE in actor.permission_codes
            and may_work_on(actor, order)
        )

    def _require_work(self, actor: User, order: WorkOrder) -> None:
        if order.status != Status.EN_REPARACION.value:
            raise BusinessRuleError("El ensamble se registra con la orden en reparación.")
        if not self._can_work(actor, order):
            raise PermissionDeniedError("No puede trabajar en esta orden.")

    def _new_device(self, actor: User, customer_id: uuid.UUID, build: AssemblyBuild) -> Device:
        org = actor.organization_id
        maker = self._session.scalar(
            select(Manufacturer).where(
                Manufacturer.organization_id == org, Manufacturer.name == ASSEMBLY_MANUFACTURER
            )
        )
        if maker is None:
            maker = Manufacturer(organization_id=org, name=ASSEMBLY_MANUFACTURER)
            self._session.add(maker)
            self._session.flush()
        model = self._session.scalar(
            select(DeviceModel).where(
                DeviceModel.organization_id == org,
                DeviceModel.manufacturer_id == maker.id,
                DeviceModel.name == ASSEMBLY_MODEL,
            )
        )
        if model is None:
            model = DeviceModel(
                organization_id=org,
                manufacturer_id=maker.id,
                category_code="DESKTOP",
                name=ASSEMBLY_MODEL,
            )
            self._session.add(model)
            self._session.flush()
        device = Device(
            organization_id=org,
            customer_id=customer_id,
            model_id=model.id,
            notes=f"Configuración: {build.name}",
        )
        self._session.add(device)
        self._session.flush()
        return device

    def _evaluation_out(self, result: Evaluation) -> EvaluationOut:
        return EvaluationOut(
            errors=[
                IssueOut(message=i.message, categories=list(i.categories)) for i in result.errors
            ],
            warnings=[
                IssueOut(message=i.message, categories=list(i.categories)) for i in result.warnings
            ],
            missing=result.missing,
            ready=result.ready,
            watts=result.watts,
            recommended_psu_w=result.recommended_psu_w,
            price=result.price,
            gaming_index=result.gaming_index,
            work_index=result.work_index,
            ram_gb=result.ram_gb,
        )

    def _summary(self, actor: User, build: AssemblyBuild) -> BuildSummary:
        pieces = self._build_of(actor, build)
        number = (
            self._session.scalar(
                select(WorkOrder.number).where(WorkOrder.id == build.work_order_id)
            )
            if build.work_order_id
            else None
        )
        return BuildSummary(
            id=build.id,
            name=build.name,
            profile=UseProfile(build.profile),
            status=build.status,
            price=evaluate(pieces).price,
            work_order_id=build.work_order_id,
            work_order_number=number,
            updated_at=build.updated_at,
        )

    def _read(self, actor: User, build: AssemblyBuild) -> BuildRead:
        summary = self._summary(actor, build)
        pieces = self._build_of(actor, build)
        creator = self._session.get(User, build.created_by_id) if build.created_by_id else None
        return BuildRead(
            **summary.model_dump(),
            selection=_selection(build, self._session),
            labor_price=build.labor_price,
            notes=build.notes,
            created_by=PersonRef(id=creator.id, full_name=creator.full_name) if creator else None,
            evaluation=self._evaluation_out(
                evaluate(pieces, UseProfile(build.profile), self._limits(actor))
            ),
            editable=build.status == "DRAFT",
        )


def _piece(part: Part) -> Piece:
    return Piece(
        id=part.id,
        name=part.name,
        category=AssemblyCategory(str(part.assembly_category)),
        price=part.sale_price,
        specs=dict(part.specs or {}),
    )


def _pieces(build: Build) -> list[Piece]:
    singles = [getattr(build, attr) for attr in SINGLE.values()]
    return [p for p in singles if p] + build.storage + build.rgb


def _ordered_ids(selection: Selection) -> list[uuid.UUID]:
    singles = [getattr(selection, attr) for attr in SINGLE.values()]
    return [p for p in singles if p] + list(selection.storage) + list(selection.rgb)


def _selection(build: AssemblyBuild, session: Session) -> Selection:
    ids = [i.part_id for i in build.items]
    rows = session.execute(select(Part.id, Part.assembly_category).where(Part.id.in_(ids)))
    categories: dict[uuid.UUID, Any] = {row[0]: row[1] for row in rows}
    data: dict[str, Any] = {"ram_units": build.ram_units, "storage": [], "rgb": []}
    for pid in ids:
        category = AssemblyCategory(categories[pid])
        if category is AssemblyCategory.STORAGE:
            data["storage"].append(pid)
        elif category is AssemblyCategory.RGB:
            data["rgb"].append(pid)
        else:
            data[SINGLE[category]] = pid
    return Selection.model_validate(data)


def _norm(text: str) -> str:
    """Header names compared without accents, case or surrounding spaces."""
    plain = unicodedata.normalize("NFKD", text.strip().lstrip(BOM).lower())
    return "".join(ch for ch in plain if not unicodedata.combining(ch))


def _read_csv(content: bytes) -> list[list[str]]:
    """Excel in Spanish saves CSV as UTF-8 (with BOM) or Windows-1252, separated by ";" or ","."""
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("cp1252", errors="replace")
    first = text.splitlines()[0] if text else ""
    delimiter = ";" if first.count(";") >= first.count(",") else ","
    return list(csv.reader(io.StringIO(text), delimiter=delimiter))
