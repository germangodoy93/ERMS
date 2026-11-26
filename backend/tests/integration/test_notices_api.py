"""Customer notices by WhatsApp (post-MVP sprint 3, ADR-054)."""

import uuid
from datetime import timedelta
from typing import Any
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.modules.audit.models import AuditLog
from app.modules.notices.models import WorkOrderNotice
from app.modules.roles.catalog import RoleCode
from app.modules.workorders.models import WorkOrder, WorkOrderStatusHistory
from app.shared.context import utcnow

from .conftest import Tenant, login, make_tenant, make_user, new_customer
from .test_work_orders_api import (
    ORDERS,
    Setup,
    _create,
    _device,
    setup,  # noqa: F401 (fixture)
)

PENDING = "/api/v1/notices/pending"
TEMPLATES = "/api/v1/notices/templates"


def _panel(client: TestClient, headers: dict[str, str], order_id: str) -> dict[str, Any]:
    response = client.get(f"{ORDERS}/{order_id}/notices", headers=headers)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def _draft(panel: dict[str, Any], kind: str) -> str:
    body: str = next(d["body"] for d in panel["drafts"] if d["kind"] == kind)
    return body


def _force_status(db: Session, order_id: str, source: str, target: str, days_ago: float) -> None:
    """Moves the order without the whole workshop flow (covered by other tests)."""
    oid = uuid.UUID(order_id)
    db.execute(update(WorkOrder).where(WorkOrder.id == oid).values(status=target))
    db.add(
        WorkOrderStatusHistory(
            work_order_id=oid,
            from_status=source,
            to_status=target,
            changed_at=utcnow() - timedelta(days=days_ago),
            reason="El repuesto ya no se fabrica." if target == "NO_REPARABLE" else None,
        )
    )
    db.commit()


def test_prepare_notice_builds_the_whatsapp_link_and_logs_it(
    client: TestClient,
    setup: Setup,  # noqa: F811
    db: Session,
) -> None:
    order = _create(client, setup)
    panel = _panel(client, setup.reception, order["id"])
    assert panel["phone"] == "+573000000001"
    assert panel["can_whatsapp"] is True
    assert panel["can_prepare"] is True
    assert panel["suggested"] == "RECEIVED"
    assert panel["pending"] is False
    received = _draft(panel, "RECEIVED")
    assert received.startswith("Hola Cliente, le saluda Organización de prueba")
    assert order["number"] in received
    assert "{" not in received

    edited = received + "\nGracias por elegirnos 😊 & ¿algo más?"
    prepared = client.post(
        f"{ORDERS}/{order['id']}/notices",
        headers=setup.reception,
        json={"kind": "RECEIVED", "body": f"  {edited}  "},
    )
    assert prepared.status_code == 201, prepared.text
    url = urlparse(prepared.json()["url"])
    assert (url.netloc, url.path) == ("wa.me", "/573000000001")
    assert parse_qs(url.query)["text"] == [edited]
    notice = prepared.json()["notice"]
    assert notice["label"] == "Orden recibida"
    assert notice["prepared_by"]["full_name"]

    history = _panel(client, setup.reception, order["id"])["history"]
    assert [h["id"] for h in history] == [notice["id"]]
    assert history[0]["body"] == edited
    audit = db.scalars(select(AuditLog).where(AuditLog.action == "work_order.notice_prepared"))
    [entry] = list(audit)
    assert entry.changes == {"kind": "RECEIVED", "channel": "WHATSAPP"}

    blank = client.post(
        f"{ORDERS}/{order['id']}/notices",
        headers=setup.reception,
        json={"kind": "FREE", "body": "   "},
    )
    assert blank.status_code == 422


def test_landline_customers_cannot_get_whatsapp_notices(
    client: TestClient,
    setup: Setup,  # noqa: F811
) -> None:
    customer = client.post(
        "/api/v1/customers",
        headers=setup.reception,
        json=new_customer(id_number="1.000.000.777", phone="601 555 1234"),
    ).json()
    device = _device(client, setup.reception, customer["id"], "356938035643809")
    order = _create(client, setup, customer_id=customer["id"], device_id=device)
    panel = _panel(client, setup.reception, order["id"])
    assert panel["can_whatsapp"] is False
    assert "fijo" in panel["blocked_reason"]
    refused = client.post(
        f"{ORDERS}/{order['id']}/notices",
        headers=setup.reception,
        json={"kind": "FREE", "body": "Hola"},
    )
    assert refused.status_code == 422
    assert "fijo" in refused.json()["detail"]


def test_pending_notices_ready_and_reminder(
    client: TestClient,
    setup: Setup,  # noqa: F811
    db: Session,
) -> None:
    order = _create(client, setup)
    assert client.get(PENDING, headers=setup.reception).json() == []

    _force_status(db, order["id"], "CONTROL_CALIDAD", "LISTO_ENTREGA", days_ago=9)
    [pending] = client.get(PENDING, headers=setup.reception).json()
    assert (pending["work_order_id"], pending["kind"]) == (order["id"], "READY")
    assert pending["can_whatsapp"] is True
    panel = _panel(client, setup.reception, order["id"])
    assert (panel["suggested"], panel["pending"]) == ("READY", True)
    ready = _draft(panel, "READY")
    assert "Saldo pendiente: $ 30.000" in ready  # diagnostic 50.000 - advance 20.000

    client.post(
        f"{ORDERS}/{order['id']}/notices",
        headers=setup.reception,
        json={"kind": "READY", "body": ready},
    )
    assert client.get(PENDING, headers=setup.reception).json() == []

    # The notice was prepared 8 days ago (the device has been ready for 9) and the device is
    # still there: a reminder is due.
    db.execute(
        update(WorkOrderNotice).values(prepared_at=WorkOrderNotice.prepared_at - timedelta(days=8))
    )
    db.commit()
    [reminder] = client.get(PENDING, headers=setup.reception).json()
    assert reminder["kind"] == "REMINDER"
    assert reminder["label"] == "Recordatorio: equipo sin retirar"


def test_not_repaired_notice_uses_the_reason(
    client: TestClient,
    setup: Setup,  # noqa: F811
    db: Session,
) -> None:
    order = _create(client, setup)
    _force_status(db, order["id"], "DIAGNOSTICO", "NO_REPARABLE", days_ago=2)
    panel = _panel(client, setup.reception, order["id"])
    assert (panel["suggested"], panel["pending"]) == ("NOT_REPAIRED", True)
    draft = _draft(panel, "NOT_REPAIRED")
    assert f"(orden {order['number']}): El repuesto ya no se fabrica. Puede pasar" in draft
    [pending] = client.get(PENDING, headers=setup.reception).json()
    assert pending["kind"] == "NOT_REPAIRED"


def test_templates_are_editable_by_the_administrator(
    client: TestClient,
    setup: Setup,  # noqa: F811
) -> None:
    assert client.get(TEMPLATES, headers=setup.reception).status_code == 403
    templates = client.get(TEMPLATES, headers=setup.admin).json()
    assert templates["reminder_days"] == 7
    assert {p["name"] for p in templates["placeholders"]} >= {"cliente", "orden", "saldo"}
    assert all(t["is_default"] for t in templates["templates"])

    bad = client.put(
        f"{TEMPLATES}/RECEIVED", headers=setup.admin, json={"body": "Hola {nombre} {total:>5}"}
    )
    assert bad.status_code == 422
    assert "{nombre} no existe" in bad.json()["detail"]

    saved = client.put(
        f"{TEMPLATES}/RECEIVED",
        headers=setup.admin,
        json={"body": "Buen día {cliente}, su orden es {orden}."},
    )
    assert saved.status_code == 200, saved.text
    received = next(t for t in saved.json()["templates"] if t["kind"] == "RECEIVED")
    assert received["is_default"] is False

    order = _create(client, setup)
    draft = _draft(_panel(client, setup.reception, order["id"]), "RECEIVED")
    assert draft == f"Buen día Cliente, su orden es {order['number']}."

    reset = client.delete(f"{TEMPLATES}/RECEIVED", headers=setup.admin).json()
    received = next(t for t in reset["templates"] if t["kind"] == "RECEIVED")
    assert received["is_default"] is True
    assert received["body"] == received["default_body"]


def test_permissions_and_isolation(
    client: TestClient,
    setup: Setup,  # noqa: F811
    db: Session,
    tenant: Tenant,
) -> None:
    order = _create(client, setup)
    panel = _panel(client, setup.technician, order["id"])
    assert panel["can_prepare"] is False
    denied = client.post(
        f"{ORDERS}/{order['id']}/notices",
        headers=setup.technician,
        json={"kind": "FREE", "body": "Hola"},
    )
    assert denied.status_code == 403
    assert client.get(PENDING, headers=setup.technician).status_code == 403

    other = make_tenant(db, slug="otro-taller")
    outsider = make_user(db, other, RoleCode.ADMIN, email="admin@otro.example.com")
    db.commit()
    headers = login(client, outsider.email)
    assert client.get(f"{ORDERS}/{order['id']}/notices", headers=headers).status_code == 404
    assert (
        client.post(
            f"{ORDERS}/{order['id']}/notices", headers=headers, json={"kind": "FREE", "body": "x"}
        ).status_code
        == 404
    )
    assert client.get(PENDING, headers=headers).json() == []
