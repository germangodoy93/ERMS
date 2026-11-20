import io
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.storage import LocalStorage
from app.modules.audit.models import AuditLog
from app.modules.diagnostics import catalog
from app.modules.roles.catalog import RoleCode
from app.modules.users.models import User

from .conftest import (
    Tenant,
    login,
    make_tenant,
    make_user,
    new_customer,
    publish_policy,
    publish_terms,
)

ORDERS = "/api/v1/work-orders"
YEAR = datetime.now(UTC).year  # Bogotá year equals UTC year except 19:00–24:00 on Dec 31


@dataclass
class Setup:
    admin: dict[str, str]
    reception: dict[str, str]
    technician: dict[str, str]
    customer_id: str
    device_id: str


def _photo_consent() -> list[dict[str, str]]:
    return [
        {"purpose": "DATA_PROCESSING", "channel": "SCREEN"},
        {"purpose": "PHOTOS", "channel": "SCREEN"},
    ]


def _device(client: TestClient, headers: dict[str, str], customer_id: str, imei: str) -> str:
    manufacturers = client.get("/api/v1/catalog/manufacturers", headers=headers).json()
    samsung = next(m["id"] for m in manufacturers if m["name"] == "Samsung")
    models = client.get(
        "/api/v1/catalog/models", headers=headers, params={"manufacturer_id": samsung}
    ).json()
    model_id = models[0]["id"] if models else None
    if model_id is None:
        model_id = client.post(
            "/api/v1/catalog/models",
            headers=headers,
            json={"manufacturer_id": samsung, "category_code": "PHONE", "name": "Galaxy Ficticio"},
        ).json()["id"]
    response = client.post(
        f"/api/v1/customers/{customer_id}/devices",
        headers=headers,
        json={"model_id": model_id, "imei": imei},
    )
    assert response.status_code == 201, response.text
    device_id: str = response.json()["id"]
    return device_id


@pytest.fixture
def setup(client: TestClient, tenant: Tenant) -> Setup:
    admin = login(client, tenant.users[RoleCode.ADMIN].email)
    publish_policy(client, admin)
    publish_terms(client, admin)
    reception = login(client, tenant.users[RoleCode.RECEPTIONIST].email)
    customer = client.post(
        "/api/v1/customers", headers=reception, json=new_customer(consents=_photo_consent())
    ).json()
    device_id = _device(client, reception, customer["id"], "490154203237518")
    technician = login(client, tenant.users[RoleCode.TECHNICIAN].email)
    return Setup(admin, reception, technician, customer["id"], device_id)


def _order_payload(s: Setup, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "customer_id": s.customer_id,
        "device_id": s.device_id,
        "reported_issue": "No enciende después de una caída.",
        "physical_condition": "Pantalla rayada, esquina superior golpeada.",
        "accessories": [{"code": "CHARGER"}, {"code": "OTHER", "detail": "Lápiz óptico"}],
        "unlock_method": "CUSTOMER_IN_PERSON",
        "diagnostic_fee": "50000",
        "advance_amount": "20000",
        "advance_method": "NEQUI",
    }
    payload.update(overrides)
    return payload


def _create(client: TestClient, s: Setup, **overrides: object) -> dict[str, Any]:
    response = client.post(ORDERS, headers=s.reception, json=_order_payload(s, **overrides))
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def _move(
    client: TestClient,
    headers: dict[str, str],
    order_id: object,
    status: str,
    reason: str | None = None,
) -> dict[str, Any]:
    response = client.post(
        f"{ORDERS}/{order_id}/status", headers=headers, json={"status": status, "reason": reason}
    )
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def _close_diagnostic(
    client: TestClient, headers: dict[str, str], order_id: object, category: str
) -> None:
    url = f"{ORDERS}/{order_id}/diagnostic"
    results = [{"test_code": t.code, "result": "OK"} for t in catalog.manual_tests_for(category)]
    assert (
        client.put(f"{url}/results", headers=headers, json={"results": results}).status_code == 200
    )
    closed = client.post(f"{url}/close", headers=headers, json={"conclusion": "Diagnóstico ok."})
    assert closed.status_code == 200, closed.text


# --- Reception terms and creation --------------------------------------------------------


def test_order_requires_published_terms(client: TestClient, tenant: Tenant) -> None:
    admin = login(client, tenant.users[RoleCode.ADMIN].email)
    publish_policy(client, admin)
    customer = client.post("/api/v1/customers", headers=admin, json=new_customer()).json()
    device_id = _device(client, admin, customer["id"], "490154203237518")
    response = client.post(
        ORDERS,
        headers=admin,
        json={
            "customer_id": customer["id"],
            "device_id": device_id,
            "reported_issue": "No carga la batería.",
            "physical_condition": "Buen estado.",
            "unlock_method": "NOT_REQUIRED",
        },
    )
    assert response.status_code == 422
    assert "condiciones del acta" in response.json()["detail"]

    current = client.get("/api/v1/reception-terms", headers=admin).json()
    assert current["terms"] is None
    assert "Ley 1480 de 2011" in current["template"]
    supervisor = login(client, tenant.users[RoleCode.SUPERVISOR].email)
    forbidden = client.post(
        "/api/v1/reception-terms", headers=supervisor, json={"content": current["template"]}
    )
    assert forbidden.status_code == 403


def test_reception_creates_numbered_orders(client: TestClient, setup: Setup, db: Session) -> None:
    first = _create(client, setup)
    assert first["number"] == f"ER-{YEAR}-000001"
    assert first["status"] == "RECIBIDO"
    assert (first["diagnostic_fee"], first["advance_amount"]) == ("50000.00", "20000.00")
    assert first["accessories"] == [
        {"code": "CHARGER", "detail": None},
        {"code": "OTHER", "detail": "Lápiz óptico"},
    ]
    assert first["terms_version"] == 1
    assert first["customer_allows_photos"] is True
    assert [h["to_status"] for h in first["history"]] == ["RECIBIDO"]
    assert first["received_by"]["full_name"].startswith("Usuario Receptionist")

    # Same device cannot have two open orders.
    duplicate = client.post(ORDERS, headers=setup.reception, json=_order_payload(setup))
    assert duplicate.status_code == 409
    assert first["number"] in duplicate.json()["detail"]

    other_device = _device(client, setup.reception, setup.customer_id, "356938035643809")
    second = _create(client, setup, device_id=other_device, advance_amount="0")
    assert second["number"] == f"ER-{YEAR}-000002"
    assert second["advance_method"] is None

    log = db.scalar(select(AuditLog).where(AuditLog.action == "work_order.created"))
    assert log is not None
    assert log.changes is not None
    assert "caída" not in json.dumps(log.changes, ensure_ascii=False)


def test_creation_validations(client: TestClient, setup: Setup, tenant: Tenant) -> None:
    cases = {
        "anticipo sin medio": _order_payload(setup, advance_method=None),
        "otro sin detalle": _order_payload(setup, accessories=[{"code": "OTHER"}]),
        "accesorio repetido": _order_payload(
            setup, accessories=[{"code": "CABLE"}, {"code": "CABLE"}]
        ),
        "valor negativo": _order_payload(setup, diagnostic_fee="-1"),
    }
    for case, payload in cases.items():
        response = client.post(ORDERS, headers=setup.reception, json=payload)
        assert response.status_code == 422, case

    other = client.post(
        "/api/v1/customers",
        headers=setup.reception,
        json=new_customer(full_name="Otro Cliente", id_number="9000000009"),
    ).json()
    wrong_owner = client.post(
        ORDERS, headers=setup.reception, json=_order_payload(setup, customer_id=other["id"])
    )
    assert wrong_owner.status_code == 422
    assert "no pertenece" in wrong_owner.json()["detail"]

    assert (
        client.post(ORDERS, headers=setup.technician, json=_order_payload(setup)).status_code == 403
    )


# --- Lifecycle ---------------------------------------------------------------------------


def test_full_lifecycle_with_roles(client: TestClient, setup: Setup, tenant: Tenant) -> None:
    order = _create(client, setup)
    oid = order["id"]
    technician: User = tenant.users[RoleCode.TECHNICIAN]

    # Reception cannot do workshop steps; the technician sees them as allowed.
    assert order["allowed_transitions"] == ["CANCELADO"]
    response = client.post(
        f"{ORDERS}/{oid}/status", headers=setup.reception, json={"status": "INSPECCION"}
    )
    assert response.status_code == 403

    order = _move(client, setup.technician, oid, "INSPECCION")
    assert order["assigned_technician"]["id"] == str(technician.id)  # claimed
    order = _move(client, setup.technician, oid, "DIAGNOSTICO")
    _close_diagnostic(client, setup.technician, oid, "PHONE")
    order = _move(client, setup.technician, oid, "COTIZACION")
    quote = client.post(f"{ORDERS}/{oid}/quotes", headers=setup.technician).json()
    item = {
        "kind": "LABOR",
        "description": "Cambio de pantalla",
        "quantity": 1,
        "unit_price": "100000",
    }
    client.put(
        f"{ORDERS}/{oid}/quotes/{quote['id']}", headers=setup.technician, json={"items": [item]}
    )
    client.post(f"{ORDERS}/{oid}/quotes/{quote['id']}/send", headers=setup.reception)
    accepted = client.post(
        f"{ORDERS}/{oid}/quotes/{quote['id']}/response",
        headers=setup.reception,
        json={"accepted": True, "channel": "VERBAL"},
    )
    assert accepted.status_code == 200, accepted.text
    order = _move(client, setup.technician, oid, "EN_REPARACION")
    order = _move(client, setup.technician, oid, "CONTROL_CALIDAD")
    no_reason = client.post(
        f"{ORDERS}/{oid}/status", headers=setup.technician, json={"status": "EN_REPARACION"}
    )
    assert no_reason.status_code == 422
    order = _move(client, setup.technician, oid, "EN_REPARACION", "El micrófono no funciona.")
    order = _move(client, setup.technician, oid, "CONTROL_CALIDAD")
    qc = [{"test_code": t.code, "result": "OK"} for t in catalog.manual_tests_for("PHONE")]
    qc_response = client.post(
        f"{ORDERS}/{oid}/repair/quality-checks", headers=setup.technician, json={"results": qc}
    )
    assert qc_response.status_code == 201, qc_response.text
    order = _move(client, setup.technician, oid, "LISTO_ENTREGA")
    paid = client.post(
        f"{ORDERS}/{oid}/payments",
        headers=setup.reception,
        json={"amount": "80000", "method": "CASH"},
    )
    assert paid.status_code == 201, paid.text

    via_status = client.post(
        f"{ORDERS}/{oid}/status", headers=setup.reception, json={"status": "ENTREGADO"}
    )
    assert via_status.status_code == 422
    third_party = client.post(
        f"{ORDERS}/{oid}/delivery", headers=setup.reception, json={"picked_up_by_customer": False}
    )
    assert third_party.status_code == 422
    delivered = client.post(
        f"{ORDERS}/{oid}/delivery",
        headers=setup.reception,
        json={"picked_up_by_customer": False, "name": "Persona Autorizada", "document": "CC 123"},
    ).json()
    assert delivered["status"] == "ENTREGADO"
    assert (delivered["delivered_to_name"], delivered["delivered_to_document"]) == (
        "Persona Autorizada",
        "CC 123",
    )
    assert delivered["allowed_transitions"] == []
    statuses = [h["to_status"] for h in delivered["history"]]
    assert statuses[0] == "RECIBIDO"
    assert statuses[-1] == "ENTREGADO"
    assert len(statuses) == 12
    qc_return = next(h for h in delivered["history"] if h["reason"])
    assert qc_return["reason"] == "El micrófono no funciona."

    closed = client.patch(f"{ORDERS}/{oid}", headers=setup.reception, json={"notes": "x"})
    assert closed.status_code == 422


def test_invalid_transitions_and_reasons(client: TestClient, setup: Setup) -> None:
    oid = _create(client, setup)["id"]
    skip = client.post(f"{ORDERS}/{oid}/status", headers=setup.admin, json={"status": "APROBADO"})
    assert skip.status_code == 422
    cancel = client.post(
        f"{ORDERS}/{oid}/status", headers=setup.reception, json={"status": "CANCELADO"}
    )
    assert cancel.status_code == 422  # reason required
    order = _move(client, setup.reception, oid, "CANCELADO", "El cliente desistió.")
    assert order["allowed_transitions"] == ["LISTO_ENTREGA"]
    order = _move(client, setup.reception, oid, "LISTO_ENTREGA")
    with_balance = client.post(
        f"{ORDERS}/{oid}/delivery", headers=setup.reception, json={"picked_up_by_customer": True}
    )
    assert with_balance.status_code == 422  # diagnostic 50000 - advance 20000 still due
    delivered = client.post(
        f"{ORDERS}/{oid}/delivery",
        headers=setup.admin,
        json={"picked_up_by_customer": True, "balance_reason": "Se condona el diagnóstico"},
    ).json()
    assert delivered["delivered_to_name"] == "Cliente Ficticio Pérez"
    assert delivered["delivered_to_document"] == "CC 1000000001"


def test_assignment_and_technician_ownership(
    client: TestClient, setup: Setup, tenant: Tenant, db: Session
) -> None:
    oid = _create(client, setup)["id"]
    other_tech = make_user(db, tenant, RoleCode.TECHNICIAN)
    technicians = client.get(f"{ORDERS}/technicians", headers=setup.reception).json()
    names = {t["id"] for t in technicians}
    assert str(other_tech.id) in names
    assert str(tenant.users[RoleCode.RECEPTIONIST].id) not in names
    assert client.get(f"{ORDERS}/technicians", headers=setup.technician).status_code == 403

    not_tech = client.put(
        f"{ORDERS}/{oid}/assignment",
        headers=setup.reception,
        json={"technician_id": str(tenant.users[RoleCode.RECEPTIONIST].id)},
    )
    assert not_tech.status_code == 422
    assigned = client.put(
        f"{ORDERS}/{oid}/assignment",
        headers=setup.reception,
        json={"technician_id": str(other_tech.id)},
    ).json()
    assert assigned["assigned_technician"]["id"] == str(other_tech.id)

    # The first technician cannot work on someone else's order.
    blocked = client.post(
        f"{ORDERS}/{oid}/status", headers=setup.technician, json={"status": "INSPECCION"}
    )
    assert blocked.status_code == 403
    assert (
        client.get(f"{ORDERS}/{oid}", headers=setup.technician).json()["allowed_transitions"] == []
    )
    other_headers = login(client, other_tech.email)
    assert _move(client, other_headers, oid, "INSPECCION")["status"] == "INSPECCION"


def test_search_and_filters(client: TestClient, setup: Setup, tenant: Tenant) -> None:
    first = _create(client, setup)
    other_device = _device(client, setup.reception, setup.customer_id, "356938035643809")
    second = _create(client, setup, device_id=other_device, advance_amount="0")
    _move(client, setup.technician, first["id"], "INSPECCION")

    def numbers(**params: object) -> list[str]:
        response = client.get(ORDERS, headers=setup.technician, params=params)
        assert response.status_code == 200, response.text
        return [o["number"] for o in response.json()["items"]]

    assert numbers() == [second["number"], first["number"]]  # newest first
    assert numbers(status="INSPECCION") == [first["number"]]
    assert numbers(status=["INSPECCION", "RECIBIDO"]) == [second["number"], first["number"]]
    assert numbers(technician_id=str(tenant.users[RoleCode.TECHNICIAN].id)) == [first["number"]]
    assert numbers(unassigned=True) == [second["number"]]
    assert numbers(q="000002") == [second["number"]]
    assert numbers(q="35693803") == [second["number"]]
    assert numbers(q="cliente ficticio perez") == [second["number"], first["number"]]
    assert numbers(open=True, q="galaxy") == [second["number"], first["number"]]


def test_customer_without_consent_cannot_open_orders(client: TestClient, setup: Setup) -> None:
    client.post(
        f"/api/v1/customers/{setup.customer_id}/consents",
        headers=setup.reception,
        json={"purpose": "DATA_PROCESSING", "granted": False, "channel": "PAPER"},
    )
    response = client.post(ORDERS, headers=setup.reception, json=_order_payload(setup))
    assert response.status_code == 422


# --- Reception act -----------------------------------------------------------------------


def test_reception_act_pdf(client: TestClient, setup: Setup) -> None:
    # Markup-looking text must be escaped, not interpreted by reportlab.
    order = _create(client, setup, physical_condition="Tapa <b>rota</b> & rayones <br/>")
    response = client.get(f"{ORDERS}/{order['id']}/reception-act.pdf", headers=setup.technician)
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/pdf"
    assert f"acta-{order['number']}.pdf" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF")
    assert len(response.content) > 2000


# --- Photos ------------------------------------------------------------------------------


def _jpeg_with_gps() -> bytes:
    image = Image.new("RGB", (4000, 3000), (200, 30, 30))
    exif = Image.Exif()
    exif[0x8825] = {2: (4.0, 36.0, 0.0)}  # GPSInfo with a latitude
    exif[0x0112] = 1  # orientation
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", exif=exif)
    return buffer.getvalue()


def test_photos_strip_metadata_and_require_consent(
    client: TestClient, setup: Setup, storage: LocalStorage
) -> None:
    order = _create(client, setup)
    url = f"{ORDERS}/{order['id']}/photos"
    original = _jpeg_with_gps()
    assert Image.open(io.BytesIO(original)).getexif().get(0x8825)

    uploaded = client.post(
        url,
        headers=setup.technician,
        files={"file": ("../../evil name.jpg", original, "image/jpeg")},
    )
    assert uploaded.status_code == 201, uploaded.text
    photo = uploaded.json()
    assert photo["file_name"] == "evil name.jpg"

    listing = client.get(url, headers=setup.reception).json()
    assert listing["demo"] is True
    assert [p["id"] for p in listing["items"]] == [photo["id"]]

    content = client.get(f"{url}/{photo['id']}", headers=setup.reception)
    assert content.headers["content-type"] == "image/jpeg"
    stored = Image.open(io.BytesIO(content.content))
    assert max(stored.size) == 2048  # resized
    assert not stored.getexif().get(0x8825)  # GPS removed

    not_image = client.post(
        url, headers=setup.technician, files={"file": ("x.jpg", b"not an image", "image/jpeg")}
    )
    assert not_image.status_code == 422
    gif = io.BytesIO()
    Image.new("RGB", (10, 10)).save(gif, format="GIF")
    assert (
        client.post(
            url, headers=setup.technician, files={"file": ("x.gif", gif.getvalue(), "image/gif")}
        ).status_code
        == 422
    )

    assert client.delete(f"{url}/{photo['id']}", headers=setup.technician).status_code == 204
    assert client.get(url, headers=setup.reception).json()["items"] == []
    assert client.get(f"{url}/{photo['id']}", headers=setup.reception).status_code == 404

    # Without the customer's photo authorization nothing is uploaded.
    client.post(
        f"/api/v1/customers/{setup.customer_id}/consents",
        headers=setup.reception,
        json={"purpose": "PHOTOS", "granted": False, "channel": "VERBAL"},
    )
    refused = client.post(
        url, headers=setup.technician, files={"file": ("a.jpg", original, "image/jpeg")}
    )
    assert refused.status_code == 422
    assert "no ha autorizado" in refused.json()["detail"]


def test_photo_limits(client: TestClient, setup: Setup, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import get_settings

    order = _create(client, setup)
    url = f"{ORDERS}/{order['id']}/photos"
    small = io.BytesIO()
    Image.new("RGB", (50, 50)).save(small, format="PNG")
    monkeypatch.setattr(get_settings(), "attachment_max_per_order", 1)
    assert (
        client.post(
            url, headers=setup.reception, files={"file": ("a.png", small.getvalue(), "image/png")}
        ).status_code
        == 201
    )
    over = client.post(
        url, headers=setup.reception, files={"file": ("b.png", small.getvalue(), "image/png")}
    )
    assert over.status_code == 422
    assert "máximo de fotos" in over.json()["detail"]
    monkeypatch.setattr(get_settings(), "attachment_max_bytes", 1024)
    big = client.post(
        url, headers=setup.reception, files={"file": ("c.jpg", _jpeg_with_gps(), "image/jpeg")}
    )
    assert big.status_code == 422


# --- Isolation ---------------------------------------------------------------------------


def test_orders_are_isolated_between_organizations(
    client: TestClient, setup: Setup, db: Session
) -> None:
    order = _create(client, setup)
    other = make_tenant(db, slug="otro-taller")
    other_admin = login(client, make_user(db, other, RoleCode.ADMIN).email)
    assert client.get(f"{ORDERS}/{order['id']}", headers=other_admin).status_code == 404
    assert (
        client.get(f"{ORDERS}/{order['id']}/reception-act.pdf", headers=other_admin).status_code
        == 404
    )
    assert client.get(ORDERS, headers=other_admin).json()["total"] == 0
    # Numbering is independent per organization.
    publish_policy(client, other_admin)
    publish_terms(client, other_admin)
    customer = client.post("/api/v1/customers", headers=other_admin, json=new_customer()).json()
    device_id = _device(client, other_admin, customer["id"], "490154203237518")
    created = client.post(
        ORDERS,
        headers=other_admin,
        json={
            "customer_id": customer["id"],
            "device_id": device_id,
            "reported_issue": "No enciende.",
            "physical_condition": "Buen estado.",
            "unlock_method": "NOT_REQUIRED",
        },
    ).json()
    assert created["number"] == f"ER-{YEAR}-000001"
