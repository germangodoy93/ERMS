from datetime import date, timedelta
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.modules.diagnostics import catalog
from app.modules.warranties.models import Warranty
from app.modules.workorders.models import WorkOrder

from .conftest import PASSWORD, Shop, Tenant, login
from .test_commerce_api import ORDERS, _approved, _move, _ok, _order, _part

TODAY = date.today()


def _deliver_repaired(client: TestClient, s: Shop, **delivery: Any) -> Any:
    part = _part(client, s, stock=1)
    order = _approved(client, s, part)
    oid = order["id"]
    _move(client, s.tech, oid, "EN_REPARACION")
    task = _ok(
        client.post(
            f"{ORDERS}/{oid}/repair/tasks",
            headers=s.tech,
            json={"description": "Cambio de pantalla"},
        ),
        201,
    )
    _ok(
        client.post(
            f"{ORDERS}/{oid}/repair/tasks/{task['id']}/parts",
            headers=s.tech,
            json={"part_id": part["id"], "quantity": 1},
        )
    )
    _move(client, s.tech, oid, "CONTROL_CALIDAD")
    results = [{"test_code": t.code, "result": "OK"} for t in catalog.manual_tests_for("PHONE")]
    _ok(
        client.post(
            f"{ORDERS}/{oid}/repair/quality-checks", headers=s.tech, json={"results": results}
        ),
        201,
    )
    _move(client, s.tech, oid, "LISTO_ENTREGA")
    balance = _ok(client.get(f"{ORDERS}/{oid}/billing", headers=s.reception))["balance"]
    _ok(
        client.post(
            f"{ORDERS}/{oid}/payments",
            headers=s.reception,
            json={"amount": balance, "method": "CASH"},
        ),
        201,
    )
    return _ok(
        client.post(
            f"{ORDERS}/{oid}/delivery",
            headers=s.reception,
            json={"picked_up_by_customer": True, **delivery},
        )
    )


def test_delivery_creates_warranty_and_claims_open_linked_orders(
    client: TestClient,
    shop: Shop,
    db: Session,
) -> None:
    _ok(client.patch("/api/v1/organization", headers=shop.admin, json={"warranty_days": 60}))
    order = _deliver_repaired(client, shop)
    overview = _ok(client.get(f"{ORDERS}/{order['id']}/warranty", headers=shop.reception))
    warranty = overview["warranty"]
    assert (warranty["days"], warranty["starts_on"], warranty["active"]) == (
        60,
        TODAY.isoformat(),
        True,
    )
    assert warranty["ends_on"] == (TODAY + timedelta(days=60)).isoformat()
    assert (overview["can_claim"], overview["is_claim_order"]) == (True, False)
    assert (
        _ok(client.get(f"{ORDERS}/{order['id']}/warranty", headers=shop.tech))["can_claim"] is False
    )

    claim_body = {
        "reported_issue": "La pantalla volvió a fallar.",
        "physical_condition": "Sin golpes.",
        "unlock_method": "NOT_REQUIRED",
    }
    claim_order = _ok(
        client.post(
            f"{ORDERS}/{order['id']}/warranty/claims", headers=shop.reception, json=claim_body
        ),
        201,
    )
    assert claim_order["diagnostic_fee"] == "0.00"
    assert claim_order["notes"] == f"Reclamo de garantía de la orden {order['number']}."
    from_claim = _ok(client.get(f"{ORDERS}/{claim_order['id']}/warranty", headers=shop.reception))
    assert from_claim["is_claim_order"] is True
    assert from_claim["warranty"]["work_order_number"] == order["number"]
    assert from_claim["can_claim"] is False
    claim = from_claim["claims"][0]
    assert (claim["status"], claim["claim_order_number"]) == ("OPEN", claim_order["number"])
    # The device already has an open (claim) order.
    assert (
        client.post(
            f"{ORDERS}/{order['id']}/warranty/claims", headers=shop.reception, json=claim_body
        ).status_code
        == 409
    )

    decided = _ok(
        client.post(
            f"{ORDERS}/{claim_order['id']}/warranty/claims/{claim['id']}/decision",
            headers=shop.supervisor,
            json={"accepted": True, "resolution": "Defecto del repuesto; se cambia sin costo."},
        )
    )
    assert (decided["status"], decided["decided_by"]["full_name"][:16]) == (
        "ACCEPTED",
        "Usuario Supervis",
    )
    again = client.post(
        f"{ORDERS}/{order['id']}/warranty/claims/{claim['id']}/decision",
        headers=shop.supervisor,
        json={"accepted": False, "resolution": "Otra decisión"},
    )
    assert again.status_code == 422

    # Claims are quoted at $0 and do not create a new warranty when delivered.
    oid = claim_order["id"]
    _move(client, shop.tech, oid, "INSPECCION", "DIAGNOSTICO")
    results = [{"test_code": t.code, "result": "OK"} for t in catalog.manual_tests_for("PHONE")]
    _ok(
        client.put(
            f"{ORDERS}/{oid}/diagnostic/results", headers=shop.tech, json={"results": results}
        )
    )
    _ok(
        client.post(
            f"{ORDERS}/{oid}/diagnostic/close",
            headers=shop.tech,
            json={"conclusion": "Repuesto defectuoso."},
        )
    )
    _move(client, shop.tech, oid, "COTIZACION")
    quote = _ok(client.post(f"{ORDERS}/{oid}/quotes", headers=shop.tech), 201)
    item = {"kind": "LABOR", "description": "Cambio en garantía", "quantity": 1, "unit_price": "0"}
    _ok(
        client.put(
            f"{ORDERS}/{oid}/quotes/{quote['id']}", headers=shop.tech, json={"items": [item]}
        )
    )
    _ok(client.post(f"{ORDERS}/{oid}/quotes/{quote['id']}/send", headers=shop.reception))


def test_expired_and_missing_warranties(client: TestClient, shop: Shop, db: Session) -> None:
    order = _deliver_repaired(client, shop, warranty_days=5)
    assert (
        _ok(client.get(f"{ORDERS}/{order['id']}/warranty", headers=shop.reception))["warranty"][
            "days"
        ]
        == 5
    )
    db.execute(update(Warranty).values(ends_on=TODAY - timedelta(days=1)))
    db.commit()
    view = _ok(client.get(f"{ORDERS}/{order['id']}/warranty", headers=shop.reception))
    assert (view["warranty"]["active"], view["can_claim"]) == (False, False)
    body = {
        "reported_issue": "Falla de nuevo.",
        "physical_condition": "Igual.",
        "unlock_method": "NOT_REQUIRED",
    }
    expired = client.post(
        f"{ORDERS}/{order['id']}/warranty/claims", headers=shop.reception, json=body
    )
    assert expired.status_code == 422
    assert "venció" in expired.json()["detail"]

    cancelled = _order(client, shop)
    _ok(
        client.post(
            f"{ORDERS}/{cancelled['id']}/status",
            headers=shop.reception,
            json={"status": "CANCELADO", "reason": "Desiste"},
        )
    )
    _move(client, shop.reception, cancelled["id"], "LISTO_ENTREGA")
    _ok(
        client.post(
            f"{ORDERS}/{cancelled['id']}/delivery",
            headers=shop.supervisor,
            json={"picked_up_by_customer": True, "balance_reason": "Sin cobro"},
        )
    )
    assert (
        _ok(client.get(f"{ORDERS}/{cancelled['id']}/warranty", headers=shop.reception))["warranty"]
        is None
    )


def test_dashboard_scopes(client: TestClient, shop: Shop, tenant: Tenant) -> None:
    _deliver_repaired(client, shop)
    pending = _order(client, shop, advance="10000")
    _move(client, shop.tech, pending["id"], "INSPECCION")
    _part(client, shop, sku="LOW-1")  # stock 0 <= min 1

    workshop = _ok(client.get("/api/v1/dashboard", headers=shop.reception))
    assert workshop["scope"] == "WORKSHOP"
    assert workshop["received_today"] == 2
    assert {s["status"]: s["count"] for s in workshop["open_by_status"]} == {"INSPECCION": 1}
    assert workshop["income_month_total"] == "179000.00"  # 169000 delivered + 10000 advance
    assert workshop["low_stock"] == 2
    assert workshop["warranties_expiring"] == 0
    assert workshop["avg_turnaround_days"] is not None
    load = {
        (t["technician"] or {}).get("full_name"): t["open_orders"]
        for t in workshop["technician_load"]
    }
    assert load == {tenant.users["TECHNICIAN"].full_name: 1}

    mine = _ok(client.get("/api/v1/dashboard", headers=shop.tech))
    assert mine["scope"] == "MINE"
    assert mine["income_month"] is None
    assert mine["technician_load"] is None
    assert mine["received_today"] == 2  # both orders were taken by this technician


def test_overdue_counts_only_pending_work(client: TestClient, shop: Shop, db: Session) -> None:
    late = _order(client, shop)
    cancelled = _order(client, shop)
    db.execute(
        update(WorkOrder)
        .where(WorkOrder.id.in_([late["id"], cancelled["id"]]))
        .values(estimated_delivery_date=TODAY - timedelta(days=2))
    )
    db.commit()
    assert _ok(client.get("/api/v1/dashboard", headers=shop.reception))["overdue"] == 2
    _ok(
        client.post(
            f"{ORDERS}/{cancelled['id']}/status",
            headers=shop.reception,
            json={"status": "CANCELADO", "reason": "El cliente desistió."},
        )
    )
    # A cancelled order only waits for the device to be returned: it is not late work.
    assert _ok(client.get("/api/v1/dashboard", headers=shop.reception))["overdue"] == 1


def test_reports_formats_and_permissions(client: TestClient, shop: Shop) -> None:
    _deliver_repaired(client, shop)
    params = {"from": (TODAY - timedelta(days=1)).isoformat(), "to": TODAY.isoformat()}
    income = _ok(client.get("/api/v1/reports/income", headers=shop.reception, params=params))
    assert income["columns"][:2] == ["Fecha", "Comprobante"]
    assert income["money_columns"] == [5]
    assert len(income["rows"]) == 1
    assert income["summary"][-1] == ["Total", "$ 169.000"]

    orders = _ok(client.get("/api/v1/reports/orders", headers=shop.reception, params=params))
    assert orders["rows"][0][2] == "Entregado"
    inventory = _ok(client.get("/api/v1/reports/inventory", headers=shop.reception, params=params))
    assert inventory["rows"][0][6:8] == ["1", "1"]  # one in, one out
    technicians = _ok(
        client.get("/api/v1/reports/technicians", headers=shop.reception, params=params)
    )
    assert technicians["rows"][0][2] == "1"

    csv = client.get(
        "/api/v1/reports/income", headers=shop.reception, params={**params, "format": "csv"}
    )
    assert csv.headers["content-type"].startswith("text/csv")
    text = csv.content.decode("utf-8")
    assert text.startswith("﻿")
    assert "Fecha;Comprobante;Orden;Cliente;Medio;Valor" in text
    pdf = client.get(
        "/api/v1/reports/orders", headers=shop.reception, params={**params, "format": "pdf"}
    )
    assert pdf.content.startswith(b"%PDF")
    income_pdf = client.get(
        "/api/v1/reports/income", headers=shop.reception, params={**params, "format": "pdf"}
    )
    assert income_pdf.content.startswith(b"%PDF")

    assert client.get("/api/v1/reports/income", headers=shop.tech, params=params).status_code == 403
    backwards = {"from": TODAY.isoformat(), "to": (TODAY - timedelta(days=3)).isoformat()}
    assert (
        client.get("/api/v1/reports/income", headers=shop.reception, params=backwards).status_code
        == 422
    )
    too_long = {"from": (TODAY - timedelta(days=400)).isoformat(), "to": TODAY.isoformat()}
    assert (
        client.get("/api/v1/reports/income", headers=shop.reception, params=too_long).status_code
        == 422
    )


def test_csv_neutralizes_formulas(client: TestClient, shop: Shop) -> None:
    from .conftest import new_customer

    _ok(
        client.post(
            "/api/v1/customers",
            headers=shop.reception,
            json=new_customer(full_name="=HYPERLINK(1)", id_number="7000000007"),
        ),
        201,
    )
    customers = _ok(
        client.get("/api/v1/customers", headers=shop.reception, params={"q": "hyperlink"})
    )
    assert customers["total"] == 1
    from app.shared.spreadsheet import safe_cell as _safe_cell

    assert _safe_cell("=HYPERLINK(1)") == "'=HYPERLINK(1)"
    assert _safe_cell("-5.00") == "-5.00"
    assert _safe_cell("+57 300") == "'+57 300"


def test_login_is_rate_limited_per_ip(client: TestClient, tenant: Tenant) -> None:
    for attempt in range(20):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": f"nadie{attempt}@example.com", "password": "Clave-incorrecta-1"},
        )
        assert response.status_code == 401
    blocked = client.post(
        "/api/v1/auth/login",
        json={"email": tenant.users["ADMIN"].email, "password": PASSWORD},
    )
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) > 0
    assert blocked.json()["code"] == "rate_limited"


def test_successful_logins_do_not_count(client: TestClient, tenant: Tenant) -> None:
    for _ in range(25):
        login(client, tenant.users["ADMIN"].email)
