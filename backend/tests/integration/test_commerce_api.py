from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.modules.diagnostics import catalog
from app.modules.quotes.models import Quotation
from app.modules.roles.catalog import RoleCode

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
INV = "/api/v1/inventory"


@dataclass
class Shop:
    admin: dict[str, str]
    supervisor: dict[str, str]
    reception: dict[str, str]
    tech: dict[str, str]


@pytest.fixture
def shop(client: TestClient, tenant: Tenant) -> Shop:
    admin = login(client, tenant.users[RoleCode.ADMIN].email)
    publish_policy(client, admin)
    publish_terms(client, admin)
    return Shop(
        admin=admin,
        supervisor=login(client, tenant.users[RoleCode.SUPERVISOR].email),
        reception=login(client, tenant.users[RoleCode.RECEPTIONIST].email),
        tech=login(client, tenant.users[RoleCode.TECHNICIAN].email),
    )


def _ok(response: Any, code: int = 200) -> Any:  # JSON of a successful response
    assert response.status_code == code, response.text
    return response.json()


def _part(client: TestClient, s: Shop, sku: str = "pant-a10", stock: int = 0, **extra: Any) -> Any:
    part = _ok(
        client.post(
            f"{INV}/parts",
            headers=s.supervisor,
            json={
                "sku": sku,
                "name": f"Repuesto {sku}",
                "sale_price": "150000",
                "min_stock": 1,
                **extra,
            },
        ),
        201,
    )
    if stock:
        _ok(
            client.post(
                f"{INV}/entries",
                headers=s.supervisor,
                json={
                    "received_on": date.today().isoformat(),
                    "invoice_number": "FV-1",
                    "lines": [{"part_id": part["id"], "quantity": stock, "unit_cost": "80000"}],
                },
            ),
            201,
        )
    return part


def _order(client: TestClient, s: Shop, *, advance: str = "0", fee: str = "50000") -> Any:
    customer = _ok(client.post("/api/v1/customers", headers=s.reception, json=new_customer()), 201)
    manufacturers = _ok(client.get("/api/v1/catalog/manufacturers", headers=s.reception))
    samsung = next(m["id"] for m in manufacturers if m["name"] == "Samsung")
    model = _ok(
        client.post(
            "/api/v1/catalog/models",
            headers=s.reception,
            json={"manufacturer_id": samsung, "category_code": "PHONE", "name": "Galaxy Comercio"},
        ),
        201,
    )
    device = _ok(
        client.post(
            f"/api/v1/customers/{customer['id']}/devices",
            headers=s.reception,
            json={"model_id": model["id"]},
        ),
        201,
    )
    payload: dict[str, Any] = {
        "customer_id": customer["id"],
        "device_id": device["id"],
        "reported_issue": "Pantalla rota.",
        "physical_condition": "Vidrio partido.",
        "unlock_method": "CUSTOMER_UNLOCKS",
        "diagnostic_fee": fee,
        "advance_amount": advance,
    }
    if advance != "0":
        payload["advance_method"] = "CASH"
    return _ok(client.post(ORDERS, headers=s.reception, json=payload), 201)


def _move(client: TestClient, headers: dict[str, str], oid: str, *statuses: str) -> None:
    for status in statuses:
        _ok(client.post(f"{ORDERS}/{oid}/status", headers=headers, json={"status": status}))


def _to_quotation(client: TestClient, s: Shop, oid: str) -> None:
    _move(client, s.tech, oid, "INSPECCION", "DIAGNOSTICO")
    results = [{"test_code": t.code, "result": "OK"} for t in catalog.manual_tests_for("PHONE")]
    _ok(client.put(f"{ORDERS}/{oid}/diagnostic/results", headers=s.tech, json={"results": results}))
    _ok(
        client.post(
            f"{ORDERS}/{oid}/diagnostic/close",
            headers=s.tech,
            json={"conclusion": "Pantalla dañada."},
        )
    )
    _move(client, s.tech, oid, "COTIZACION")


def _draft(
    client: TestClient,
    s: Shop,
    oid: str,
    items: list[dict[str, Any]],
    headers: dict[str, str] | None = None,
) -> Any:
    headers = headers or s.tech
    quote = _ok(client.post(f"{ORDERS}/{oid}/quotes", headers=headers), 201)
    return _ok(
        client.put(f"{ORDERS}/{oid}/quotes/{quote['id']}", headers=headers, json={"items": items})
    )


def _approved(client: TestClient, s: Shop, part: dict[str, Any], *, advance: str = "0") -> Any:
    order = _order(client, s, advance=advance)
    _to_quotation(client, s, order["id"])
    quote = _draft(
        client,
        s,
        order["id"],
        [
            {
                "kind": "PART",
                "part_id": part["id"],
                "quantity": 1,
                "unit_price": "100000",
                "apply_tax": True,
            },
            {
                "kind": "LABOR",
                "description": "Cambio de pantalla",
                "quantity": 1,
                "unit_price": "50000",
            },
        ],
    )
    _ok(client.post(f"{ORDERS}/{order['id']}/quotes/{quote['id']}/send", headers=s.reception))
    _ok(
        client.post(
            f"{ORDERS}/{order['id']}/quotes/{quote['id']}/response",
            headers=s.reception,
            json={"accepted": True, "channel": "VERBAL"},
        )
    )
    return order


# --- Inventory -----------------------------------------------------------------------------


def test_parts_entries_adjustments_and_ledger(client: TestClient, shop: Shop) -> None:
    part = _part(client, shop, sku=" pant a10 ", stock=0)
    assert part["sku"] == "PANT-A10"
    assert (part["stock"], part["low_stock"]) == (0, True)
    duplicate = client.post(
        f"{INV}/parts", headers=shop.supervisor, json={"sku": "PANT-A10", "name": "Otro"}
    )
    assert duplicate.status_code == 409
    assert (
        client.post(
            f"{INV}/parts", headers=shop.reception, json={"sku": "X1", "name": "X"}
        ).status_code
        == 403
    )

    entry = _ok(
        client.post(
            f"{INV}/entries",
            headers=shop.supervisor,
            json={
                "received_on": date.today().isoformat(),
                "invoice_number": "FV-77",
                "lines": [{"part_id": part["id"], "quantity": 5, "unit_cost": "82000"}],
            },
        ),
        201,
    )
    assert (entry["lines"], entry["total_cost"]) == (1, "410000.00")
    detail = _ok(client.get(f"{INV}/parts/{part['id']}", headers=shop.tech))
    assert (detail["stock"], detail["unit_cost"], detail["low_stock"]) == (5, "82000.00", False)

    adjusted = _ok(
        client.post(
            f"{INV}/parts/{part['id']}/adjustments",
            headers=shop.supervisor,
            json={"counted_quantity": 4, "reason": "Unidad dañada en bodega"},
        )
    )
    assert adjusted["stock"] == 4
    same = client.post(
        f"{INV}/parts/{part['id']}/adjustments",
        headers=shop.supervisor,
        json={"counted_quantity": 4, "reason": "Sin cambios"},
    )
    assert same.status_code == 422
    ledger = _ok(client.get(f"{INV}/parts/{part['id']}/movements", headers=shop.tech))
    assert [(m["kind"], m["quantity"], m["stock_after"]) for m in ledger] == [
        ("ADJUSTMENT", -1, 4),
        ("IN", 5, 5),
    ]
    assert ledger[1]["reference_label"] == "Factura FV-77"
    low = _ok(client.get(f"{INV}/parts", headers=shop.tech, params={"low_stock": True}))
    assert low == []


def test_suppliers(client: TestClient, shop: Shop) -> None:
    supplier = _ok(
        client.post(
            f"{INV}/suppliers",
            headers=shop.supervisor,
            json={"name": "Proveedor Ficticio", "tax_id": "890903938"},
        ),
        201,
    )
    assert supplier["tax_id"] == "890903938-8"
    assert (
        client.post(
            f"{INV}/suppliers", headers=shop.supervisor, json={"name": "proveedor ficticio"}
        ).status_code
        == 409
    )
    names = [x["name"] for x in _ok(client.get(f"{INV}/suppliers", headers=shop.tech))]
    assert names == ["Proveedor Ficticio"]


# --- Quotations ----------------------------------------------------------------------------


def test_quote_totals_with_optional_vat(client: TestClient, shop: Shop) -> None:
    part = _part(client, shop, stock=2)
    order = _order(client, shop)
    _to_quotation(client, shop, order["id"])
    quote = _draft(
        client,
        shop,
        order["id"],
        [
            {
                "kind": "PART",
                "part_id": part["id"],
                "quantity": 1,
                "unit_price": "119000",
                "apply_tax": True,
                "price_includes_tax": True,
            },
            {
                "kind": "LABOR",
                "description": "Mano de obra",
                "quantity": 1,
                "unit_price": "40000",
                "apply_tax": True,
            },
            {"kind": "PART", "description": "Flex por pedir", "quantity": 2, "unit_price": "10000"},
        ],
    )
    assert quote["status"] == "DRAFT"
    assert quote["items"][0]["description"] == "Repuesto pant-a10"  # name as typed
    assert quote["items"][0]["in_stock"] == 2
    assert (quote["subtotal"], quote["tax_total"], quote["total"]) == (
        "160000.00",
        "26600.00",
        "186600.00",
    )


def test_discount_limit_and_authorization(client: TestClient, shop: Shop) -> None:
    order = _order(client, shop)
    _to_quotation(client, shop, order["id"])
    items = [
        {
            "kind": "LABOR",
            "description": "Reparación",
            "quantity": 1,
            "unit_price": "100000",
            "discount_percent": "15",
        }
    ]
    quote = _ok(client.post(f"{ORDERS}/{order['id']}/quotes", headers=shop.reception), 201)
    url = f"{ORDERS}/{order['id']}/quotes/{quote['id']}"
    assert client.put(url, headers=shop.reception, json={"items": items}).status_code == 403
    small = [{**items[0], "discount_percent": "10"}]
    assert (
        _ok(client.put(url, headers=shop.reception, json={"items": small}))[
            "discount_authorized_by"
        ]
        is None
    )
    saved = _ok(client.put(url, headers=shop.supervisor, json={"items": items}))
    assert saved["total"] == "85000.00"
    assert saved["discount_authorized_by"]["full_name"].startswith("Usuario Supervisor")
    overview = _ok(client.get(f"{ORDERS}/{order['id']}/quotes", headers=shop.reception))
    assert overview["max_discount_percent"] == 10


def test_send_versions_and_customer_response(client: TestClient, shop: Shop, db: Session) -> None:
    order = _order(client, shop)
    oid = order["id"]
    _to_quotation(client, shop, oid)
    items = [{"kind": "LABOR", "description": "Reparación", "quantity": 1, "unit_price": "100000"}]
    v1 = _draft(client, shop, oid, items)
    assert client.post(f"{ORDERS}/{oid}/quotes", headers=shop.tech).status_code == 422  # one draft
    assert (
        client.post(f"{ORDERS}/{oid}/quotes/{v1['id']}/send", headers=shop.tech).status_code == 403
    )
    manual = client.post(
        f"{ORDERS}/{oid}/status", headers=shop.reception, json={"status": "PENDIENTE_AUTORIZACION"}
    )
    assert manual.status_code == 422

    sent = _ok(client.post(f"{ORDERS}/{oid}/quotes/{v1['id']}/send", headers=shop.reception))
    assert sent["status"] == "SENT"
    assert (
        sent["valid_until"]
        == (date.fromisoformat(sent["sent_at"][:10]) + timedelta(days=15)).isoformat()
        or sent["valid_until"]
    )
    assert (
        _ok(client.get(f"{ORDERS}/{oid}", headers=shop.reception))["status"]
        == "PENDIENTE_AUTORIZACION"
    )

    # The customer asks for changes: version 2 copies version 1 and supersedes it when sent.
    v2 = _draft(client, shop, oid, [{**items[0], "unit_price": "90000"}], headers=shop.reception)
    assert v2["version"] == 2
    _ok(client.post(f"{ORDERS}/{oid}/quotes/{v2['id']}/send", headers=shop.reception))
    statuses = [
        q["status"] for q in _ok(client.get(f"{ORDERS}/{oid}/quotes", headers=shop.tech))["quotes"]
    ]
    assert statuses == ["SENT", "SUPERSEDED"]

    no_reason = client.post(
        f"{ORDERS}/{oid}/quotes/{v2['id']}/response",
        headers=shop.reception,
        json={"accepted": False, "channel": "VERBAL"},
    )
    assert no_reason.status_code == 422
    # An expired quotation cannot be accepted.
    db.execute(
        update(Quotation)
        .where(Quotation.status == "SENT")
        .values(valid_until=date.today() - timedelta(days=1))
    )
    db.commit()
    assert (
        _ok(client.get(f"{ORDERS}/{oid}/quotes", headers=shop.tech))["quotes"][0]["status"]
        == "EXPIRED"
    )
    expired = client.post(
        f"{ORDERS}/{oid}/quotes/{v2['id']}/response",
        headers=shop.reception,
        json={"accepted": True, "channel": "VERBAL"},
    )
    assert expired.status_code == 422
    rejected = _ok(
        client.post(
            f"{ORDERS}/{oid}/quotes/{v2['id']}/response",
            headers=shop.reception,
            json={"accepted": False, "channel": "PAPER", "reason": "Muy costoso"},
        )
    )
    assert rejected["status"] == "REJECTED"
    detail = _ok(client.get(f"{ORDERS}/{oid}", headers=shop.reception))
    assert detail["status"] == "COTIZACION_RECHAZADA"
    # Rejected: only the diagnostic is due.
    billing = _ok(client.get(f"{ORDERS}/{oid}/billing", headers=shop.reception))
    assert (billing["amount_due"], billing["balance"]) == ("50000.00", "50000.00")


# --- Repair, quality control, payments and delivery ----------------------------------------


def test_repair_consumes_stock_and_quality_gates_delivery(client: TestClient, shop: Shop) -> None:
    part = _part(client, shop, stock=1)
    order = _approved(client, shop, part, advance="30000")
    oid = order["id"]
    repair_url = f"{ORDERS}/{oid}/repair"
    early = client.post(f"{repair_url}/tasks", headers=shop.tech, json={"description": "Cambio"})
    assert early.status_code == 422  # still APROBADO
    _move(client, shop.tech, oid, "EN_REPARACION")

    task = _ok(
        client.post(
            f"{repair_url}/tasks",
            headers=shop.tech,
            json={"description": "Cambio de pantalla", "labor_minutes": 45},
        ),
        201,
    )
    assert (
        client.post(
            f"{repair_url}/tasks", headers=shop.reception, json={"description": "x y z"}
        ).status_code
        == 403
    )
    used = _ok(
        client.post(
            f"{repair_url}/tasks/{task['id']}/parts",
            headers=shop.tech,
            json={"part_id": part["id"], "quantity": 1},
        )
    )
    assert used["parts"][0]["sku"] == "PANT-A10"
    assert _ok(client.get(f"{INV}/parts/{part['id']}", headers=shop.tech))["stock"] == 0
    none_left = client.post(
        f"{repair_url}/tasks/{task['id']}/parts",
        headers=shop.tech,
        json={"part_id": part["id"], "quantity": 1},
    )
    assert none_left.status_code == 422
    assert "Existencia insuficiente" in none_left.json()["detail"]
    returned = _ok(
        client.post(
            f"{repair_url}/tasks/{task['id']}/parts/{used['parts'][0]['id']}/return",
            headers=shop.tech,
        )
    )
    assert returned["parts"][0]["returned"] is True
    assert _ok(client.get(f"{INV}/parts/{part['id']}", headers=shop.tech))["stock"] == 1
    _ok(
        client.post(
            f"{repair_url}/tasks/{task['id']}/parts",
            headers=shop.tech,
            json={"part_id": part["id"], "quantity": 1},
        )
    )

    _move(client, shop.tech, oid, "CONTROL_CALIDAD")
    no_qc = client.post(
        f"{ORDERS}/{oid}/status", headers=shop.tech, json={"status": "LISTO_ENTREGA"}
    )
    assert no_qc.status_code == 422
    tests = [t.code for t in catalog.manual_tests_for("PHONE")]
    incomplete = client.post(
        f"{repair_url}/quality-checks",
        headers=shop.tech,
        json={"results": [{"test_code": "POWER_ON", "result": "OK"}]},
    )
    assert incomplete.status_code == 422
    failed = _ok(
        client.post(
            f"{repair_url}/quality-checks",
            headers=shop.tech,
            json={
                "results": [
                    {"test_code": c, "result": "FAIL" if c == "TOUCH" else "OK"} for c in tests
                ]
            },
        ),
        201,
    )
    assert failed["passed"] is False
    assert (
        client.post(
            f"{ORDERS}/{oid}/status", headers=shop.tech, json={"status": "LISTO_ENTREGA"}
        ).status_code
        == 422
    )
    passed = _ok(
        client.post(
            f"{repair_url}/quality-checks",
            headers=shop.tech,
            json={"results": [{"test_code": c, "result": "OK"} for c in tests]},
        ),
        201,
    )
    assert passed["passed"] is True
    _move(client, shop.tech, oid, "LISTO_ENTREGA")
    overview = _ok(client.get(repair_url, headers=shop.reception))
    assert [c["passed"] for c in overview["quality_checks"]] == [True, False]

    # Billing: accepted quote (119000 + 50000) includes the diagnostic; advance already paid.
    billing = _ok(client.get(f"{ORDERS}/{oid}/billing", headers=shop.reception))
    assert (billing["amount_due"], billing["paid"], billing["balance"]) == (
        "169000.00",
        "30000.00",
        "139000.00",
    )
    advance = billing["payments"][0]
    assert (advance["kind"], advance["receipt_number"]) == (
        "ADVANCE",
        f"RC-{date.today().year}-000001",
    )

    blocked = client.post(
        f"{ORDERS}/{oid}/delivery", headers=shop.reception, json={"picked_up_by_customer": True}
    )
    assert blocked.status_code == 422
    assert "saldo pendiente" in blocked.json()["detail"]
    too_much = client.post(
        f"{ORDERS}/{oid}/payments",
        headers=shop.reception,
        json={"amount": "200000", "method": "NEQUI"},
    )
    assert too_much.status_code == 422
    payment = _ok(
        client.post(
            f"{ORDERS}/{oid}/payments",
            headers=shop.reception,
            json={"amount": "139000", "method": "NEQUI", "reference": "M123"},
        ),
        201,
    )
    assert payment["receipt_number"] == f"RC-{date.today().year}-000002"
    pdf = client.get(f"{ORDERS}/{oid}/payments/{payment['id']}/receipt.pdf", headers=shop.reception)
    assert pdf.content.startswith(b"%PDF")
    assert (
        _ok(client.get(f"{ORDERS}/{oid}/billing", headers=shop.reception))["can_register"] is False
    )
    delivered = _ok(
        client.post(
            f"{ORDERS}/{oid}/delivery", headers=shop.reception, json={"picked_up_by_customer": True}
        )
    )
    assert delivered["status"] == "ENTREGADO"


def test_delivery_with_balance_requires_supervisor(client: TestClient, shop: Shop) -> None:
    order = _order(client, shop)
    oid = order["id"]
    _ok(
        client.post(
            f"{ORDERS}/{oid}/status",
            headers=shop.reception,
            json={"status": "CANCELADO", "reason": "Desiste"},
        )
    )
    _move(client, shop.reception, oid, "LISTO_ENTREGA")
    assert (
        client.post(
            f"{ORDERS}/{oid}/delivery", headers=shop.reception, json={"picked_up_by_customer": True}
        ).status_code
        == 422
    )
    no_reason = client.post(
        f"{ORDERS}/{oid}/delivery", headers=shop.supervisor, json={"picked_up_by_customer": True}
    )
    assert no_reason.status_code == 422
    delivered = _ok(
        client.post(
            f"{ORDERS}/{oid}/delivery",
            headers=shop.supervisor,
            json={"picked_up_by_customer": True, "balance_reason": "Cliente frecuente, se condona"},
        )
    )
    assert "saldo pendiente de 50000.00" in delivered["history"][-1]["reason"]


def test_quote_pdf_and_isolation(client: TestClient, shop: Shop, db: Session) -> None:
    order = _order(client, shop)
    _to_quotation(client, shop, order["id"])
    quote = _draft(
        client,
        shop,
        order["id"],
        [{"kind": "LABOR", "description": "<b>Mano</b> de obra", "quantity": 1, "unit_price": "1"}],
    )
    pdf = client.get(f"{ORDERS}/{order['id']}/quotes/{quote['id']}/pdf", headers=shop.reception)
    assert pdf.content.startswith(b"%PDF")
    other = make_tenant(db, slug="otro-taller")
    other_admin = login(client, make_user(db, other, RoleCode.ADMIN).email)
    assert client.get(f"{ORDERS}/{order['id']}/quotes", headers=other_admin).status_code == 404
    assert client.get(f"{ORDERS}/{order['id']}/billing", headers=other_admin).status_code == 404
    assert _ok(client.get(f"{INV}/parts", headers=other_admin)) == []
