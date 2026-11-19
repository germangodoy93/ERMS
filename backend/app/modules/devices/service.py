"""Device catalog and customers' devices.

- Categories are fixed. Manufacturers and models belong to each organization.
- Reception can create a model while registering a device (`devices:manage`); editing or
  deactivating catalog entries requires `catalog:manage`.
- A device is registered only for a customer who can be served (active, not anonymized and
  with the data processing authorization in force).
- IMEI (validated with Luhn) is unique per organization; the serial is unique per model.
"""

import uuid
from typing import Any

from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.modules.audit.service import AuditService
from app.modules.customers.models import Customer
from app.modules.customers.service import CustomerService
from app.modules.devices.models import Device, DeviceCategory, DeviceModel, Manufacturer
from app.modules.devices.schemas import (
    DeviceCreate,
    DeviceModelCreate,
    DeviceModelUpdate,
    DeviceSearchItem,
    DeviceUpdate,
    ManufacturerCreate,
    ManufacturerUpdate,
)
from app.modules.users.models import User
from app.modules.users.repository import escape_like
from app.shared.context import RequestContext
from app.shared.pagination import PageParams


class CatalogService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._audit = AuditService(session)

    # --- Categories ---------------------------------------------------------------------

    def categories(self) -> list[DeviceCategory]:
        return list(
            self._session.scalars(select(DeviceCategory).order_by(DeviceCategory.sort_order))
        )

    def _category(self, code: str) -> DeviceCategory:
        category = self._session.get(DeviceCategory, code)
        if category is None:
            raise BusinessRuleError("La categoría no existe.")
        return category

    # --- Manufacturers ------------------------------------------------------------------

    def manufacturers(self, actor: User, *, include_inactive: bool) -> list[Manufacturer]:
        query = select(Manufacturer).where(Manufacturer.organization_id == actor.organization_id)
        if not include_inactive:
            query = query.where(Manufacturer.is_active.is_(True))
        return list(self._session.scalars(query.order_by(func.lower(Manufacturer.name))))

    def get_manufacturer(self, actor: User, manufacturer_id: uuid.UUID) -> Manufacturer:
        manufacturer = self._session.scalar(
            select(Manufacturer).where(
                Manufacturer.id == manufacturer_id,
                Manufacturer.organization_id == actor.organization_id,
            )
        )
        if manufacturer is None:
            raise NotFoundError("El fabricante no existe.")
        return manufacturer

    def create_manufacturer(
        self, actor: User, data: ManufacturerCreate, context: RequestContext
    ) -> Manufacturer:
        self._ensure_manufacturer_name_free(actor, data.name)
        manufacturer = Manufacturer(organization_id=actor.organization_id, name=data.name)
        self._session.add(manufacturer)
        self._session.flush()
        self._record(actor, context, "catalog.manufacturer_created", manufacturer.id, data.name)
        return manufacturer

    def update_manufacturer(
        self,
        actor: User,
        manufacturer_id: uuid.UUID,
        data: ManufacturerUpdate,
        context: RequestContext,
    ) -> Manufacturer:
        manufacturer = self.get_manufacturer(actor, manufacturer_id)
        changes: dict[str, Any] = {}
        if data.name is not None and data.name != manufacturer.name:
            self._ensure_manufacturer_name_free(actor, data.name, exclude_id=manufacturer.id)
            changes["name"] = [manufacturer.name, data.name]
            manufacturer.name = data.name
        if data.is_active is not None and data.is_active != manufacturer.is_active:
            changes["is_active"] = [manufacturer.is_active, data.is_active]
            manufacturer.is_active = data.is_active
        if changes:
            self._session.flush()
            self._audit.record(
                "catalog.manufacturer_updated",
                entity_type="manufacturer",
                entity_id=manufacturer.id,
                organization_id=actor.organization_id,
                actor_user_id=actor.id,
                context=context,
                changes=changes,
            )
        return manufacturer

    def _ensure_manufacturer_name_free(
        self, actor: User, name: str, *, exclude_id: uuid.UUID | None = None
    ) -> None:
        query = select(Manufacturer.id).where(
            Manufacturer.organization_id == actor.organization_id,
            func.lower(Manufacturer.name) == name.lower(),
        )
        if exclude_id is not None:
            query = query.where(Manufacturer.id != exclude_id)
        if self._session.scalar(query) is not None:
            raise ConflictError(f"El fabricante {name} ya existe.")

    # --- Models -------------------------------------------------------------------------

    def models(
        self,
        actor: User,
        *,
        manufacturer_id: uuid.UUID | None,
        category_code: str | None,
        search: str | None,
        include_inactive: bool,
    ) -> list[DeviceModel]:
        query = select(DeviceModel).where(DeviceModel.organization_id == actor.organization_id)
        if manufacturer_id is not None:
            query = query.where(DeviceModel.manufacturer_id == manufacturer_id)
        if category_code:
            query = query.where(DeviceModel.category_code == category_code)
        if search and search.strip():
            query = query.where(
                DeviceModel.name.ilike(f"%{escape_like(search.strip())}%", escape="\\")
            )
        if not include_inactive:
            query = query.where(DeviceModel.is_active.is_(True))
        return list(self._session.scalars(query.order_by(func.lower(DeviceModel.name)).limit(200)))

    def get_model(self, actor: User, model_id: uuid.UUID) -> DeviceModel:
        model = self._session.scalar(
            select(DeviceModel).where(
                DeviceModel.id == model_id, DeviceModel.organization_id == actor.organization_id
            )
        )
        if model is None:
            raise NotFoundError("El modelo no existe.")
        return model

    def create_model(
        self, actor: User, data: DeviceModelCreate, context: RequestContext
    ) -> DeviceModel:
        manufacturer = self.get_manufacturer(actor, data.manufacturer_id)
        if not manufacturer.is_active:
            raise BusinessRuleError("El fabricante está inactivo.")
        self._category(data.category_code)
        self._ensure_model_name_free(manufacturer.id, data.name)
        model = DeviceModel(
            organization_id=actor.organization_id,
            manufacturer_id=manufacturer.id,
            category_code=data.category_code,
            name=data.name,
            release_year=data.release_year,
        )
        self._session.add(model)
        self._session.flush()
        self._record(
            actor, context, "catalog.model_created", model.id, f"{manufacturer.name} {data.name}"
        )
        return model

    def update_model(
        self, actor: User, model_id: uuid.UUID, data: DeviceModelUpdate, context: RequestContext
    ) -> DeviceModel:
        model = self.get_model(actor, model_id)
        changes: dict[str, Any] = {}
        fields = data.model_fields_set
        if data.name is not None and data.name != model.name:
            self._ensure_model_name_free(model.manufacturer_id, data.name, exclude_id=model.id)
            changes["name"] = [model.name, data.name]
            model.name = data.name
        if data.category_code is not None and data.category_code != model.category_code:
            self._category(data.category_code)
            changes["category_code"] = [model.category_code, data.category_code]
            model.category_code = data.category_code
        if "release_year" in fields and data.release_year != model.release_year:
            changes["release_year"] = [model.release_year, data.release_year]
            model.release_year = data.release_year
        if data.is_active is not None and data.is_active != model.is_active:
            changes["is_active"] = [model.is_active, data.is_active]
            model.is_active = data.is_active
        if changes:
            self._session.flush()
            self._session.refresh(model)
            self._audit.record(
                "catalog.model_updated",
                entity_type="device_model",
                entity_id=model.id,
                organization_id=actor.organization_id,
                actor_user_id=actor.id,
                context=context,
                changes=changes,
            )
        return model

    def _ensure_model_name_free(
        self, manufacturer_id: uuid.UUID, name: str, *, exclude_id: uuid.UUID | None = None
    ) -> None:
        query = select(DeviceModel.id).where(
            DeviceModel.manufacturer_id == manufacturer_id,
            func.lower(DeviceModel.name) == name.lower(),
        )
        if exclude_id is not None:
            query = query.where(DeviceModel.id != exclude_id)
        if self._session.scalar(query) is not None:
            raise ConflictError(f"El modelo {name} ya existe para ese fabricante.")

    def _record(
        self, actor: User, context: RequestContext, action: str, entity_id: uuid.UUID, name: str
    ) -> None:
        self._audit.record(
            action,
            entity_type="manufacturer" if "manufacturer" in action else "device_model",
            entity_id=entity_id,
            organization_id=actor.organization_id,
            actor_user_id=actor.id,
            context=context,
            changes={"name": name},
        )


class DeviceService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._customers = CustomerService(session)
        self._catalog = CatalogService(session)
        self._audit = AuditService(session)

    def for_customer(self, actor: User, customer_id: uuid.UUID) -> list[Device]:
        customer = self._customers.get(actor, customer_id)
        return list(
            self._session.scalars(
                select(Device)
                .where(
                    Device.customer_id == customer.id,
                    Device.organization_id == actor.organization_id,
                )
                .order_by(Device.created_at.desc())
            )
        )

    def get(self, actor: User, device_id: uuid.UUID) -> Device:
        device = self._session.scalar(
            select(Device).where(
                Device.id == device_id, Device.organization_id == actor.organization_id
            )
        )
        if device is None:
            raise NotFoundError("El equipo no existe.")
        return device

    def search(
        self, actor: User, params: PageParams, *, search: str
    ) -> tuple[list[DeviceSearchItem], int]:
        text = search.strip()
        compact = "".join(text.split()).upper()
        pattern = f"%{escape_like(compact)}%"
        query = (
            select(Device, Customer.full_name)
            .join(Customer, Customer.id == Device.customer_id)
            .join(DeviceModel, DeviceModel.id == Device.model_id)
            .where(
                Device.organization_id == actor.organization_id,
                or_(
                    Device.serial_number.like(pattern, escape="\\"),
                    Device.imei.like(pattern, escape="\\"),
                    DeviceModel.name.ilike(f"%{escape_like(text)}%", escape="\\"),
                ),
            )
        )
        total = self._session.scalar(select(func.count()).select_from(query.subquery())) or 0
        rows = self._session.execute(
            query.order_by(Device.created_at.desc(), Device.id)
            .offset(params.offset)
            .limit(params.size)
        ).all()
        items = [
            DeviceSearchItem.model_validate(
                {**_device_dict(device), "customer_name": customer_name}
            )
            for device, customer_name in rows
        ]
        return items, total

    def create(
        self, actor: User, customer_id: uuid.UUID, data: DeviceCreate, context: RequestContext
    ) -> Device:
        customer = self._customers.ensure_can_be_served(actor, customer_id)
        model = self._catalog.get_model(actor, data.model_id)
        if not model.is_active:
            raise BusinessRuleError("El modelo está inactivo.")
        self._ensure_identifiers_free(actor, model.id, data.serial_number, data.imei)
        device = Device(
            organization_id=actor.organization_id,
            customer_id=customer.id,
            model_id=model.id,
            serial_number=data.serial_number,
            imei=data.imei,
            operating_system=data.operating_system,
            storage=data.storage,
            color=data.color,
            notes=data.notes,
        )
        self._session.add(device)
        self._session.flush()
        self._audit.record(
            "device.created",
            entity_type="device",
            entity_id=device.id,
            organization_id=actor.organization_id,
            actor_user_id=actor.id,
            context=context,
            changes={"customer_id": str(customer.id), "model": model.name},
        )
        return device

    def update(
        self, actor: User, device_id: uuid.UUID, data: DeviceUpdate, context: RequestContext
    ) -> Device:
        device = self.get(actor, device_id)
        fields = data.model_fields_set
        if "model_id" in fields and data.model_id is None:
            raise BusinessRuleError("El modelo es obligatorio.")
        model_id = data.model_id or device.model_id
        if model_id != device.model_id:
            model = self._catalog.get_model(actor, model_id)
            if not model.is_active:
                raise BusinessRuleError("El modelo está inactivo.")
        serial = data.serial_number if "serial_number" in fields else device.serial_number
        imei = data.imei if "imei" in fields else device.imei
        self._ensure_identifiers_free(actor, model_id, serial, imei, exclude_id=device.id)

        changed: list[str] = []
        for field in (
            "model_id",
            "serial_number",
            "imei",
            "operating_system",
            "storage",
            "color",
            "notes",
            "is_active",
        ):
            if field not in fields:
                continue
            value = getattr(data, field)
            if field == "is_active" and value is None:
                continue
            if getattr(device, field) != value:
                setattr(device, field, value)
                changed.append(field)
        if changed:
            self._session.flush()
            self._session.refresh(device)
            self._audit.record(
                "device.updated",
                entity_type="device",
                entity_id=device.id,
                organization_id=actor.organization_id,
                actor_user_id=actor.id,
                context=context,
                changes={"fields": sorted(changed)},
            )
        return device

    def clear_personal_notes(self, organization_id: uuid.UUID, customer_id: uuid.UUID) -> None:
        """Used when a customer is anonymized: free-text notes may hold personal data."""
        self._session.execute(
            update(Device)
            .where(Device.organization_id == organization_id, Device.customer_id == customer_id)
            .values(notes=None)
        )

    def _ensure_identifiers_free(
        self,
        actor: User,
        model_id: uuid.UUID,
        serial: str | None,
        imei: str | None,
        *,
        exclude_id: uuid.UUID | None = None,
    ) -> None:
        conditions = []
        if imei:
            conditions.append(("IMEI", Device.imei == imei))
        if serial:
            conditions.append(
                ("serial", (Device.serial_number == serial) & (Device.model_id == model_id))
            )
        for label, condition in conditions:
            query = (
                select(Customer.full_name)
                .join(Device, Device.customer_id == Customer.id)
                .where(Device.organization_id == actor.organization_id, condition)
            )
            if exclude_id is not None:
                query = query.where(Device.id != exclude_id)
            owner = self._session.scalar(query)
            if owner is not None:
                raise ConflictError(f"Ya hay un equipo registrado con ese {label} ({owner}).")


def _device_dict(device: Device) -> dict[str, Any]:
    return {
        "id": device.id,
        "customer_id": device.customer_id,
        "model": device.model,
        "serial_number": device.serial_number,
        "imei": device.imei,
        "operating_system": device.operating_system,
        "storage": device.storage,
        "color": device.color,
        "notes": device.notes,
        "is_active": device.is_active,
        "created_at": device.created_at,
        "updated_at": device.updated_at,
    }
