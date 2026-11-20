from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.modules.diagnostics import catalog
from app.modules.diagnostics.models import AgentPairing
from app.modules.roles.catalog import RoleCode
from app.shared.context import utcnow

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
AGENT = "/api/v1/diagnostics/agent"
REPORT: dict[str, Any] = {
    "agent_version": "0.1.0",
    "elevated": False,
    "system": {"manufacturer": "Fabricante", "model": "Portátil Ficticio", "bios_serial": "ABC123"},
    "cpus": [{"name": "CPU Ficticia", "cores": 4, "logical_processors": 8}],
    "memory": {"total_bytes": 8 * 1024**3, "modules": []},
    "disks": [{"friendly_name": "SSD", "health_status": "Healthy", "size_bytes": 256 * 1024**3}],
    "volumes": [{"drive_letter": "C", "size_bytes": 200 * 1024**3, "free_bytes": 10 * 1024**3}],
    "battery": {"present": True, "design_capacity_mwh": 50000, "full_charge_capacity_mwh": 30000},
    "stability": {"unexpected_shutdowns_30d": 1, "bugchecks_30d": 0},
    "errors": {"gpus": "Sin datos"},
}


def _order(
    client: TestClient,
    headers: dict[str, str],
    category: str,
    *,
    agent_consent: bool = True,
    imei: str | None = None,
) -> dict[str, Any]:
    consents = [{"purpose": "DATA_PROCESSING", "channel": "SCREEN"}]
    if agent_consent:
        consents.append({"purpose": "DIAGNOSTIC_AGENT", "channel": "SCREEN"})
    customer = client.post(
        "/api/v1/customers",
        headers=headers,
        json=new_customer(id_type=None, id_number=None, consents=consents),
    ).json()
    manufacturers = client.get("/api/v1/catalog/manufacturers", headers=headers).json()
    lenovo = next(m["id"] for m in manufacturers if m["name"] == "Lenovo")
    model = client.post(
        "/api/v1/catalog/models",
        headers=headers,
        json={"manufacturer_id": lenovo, "category_code": category, "name": f"Modelo {category}"},
    ).json()
    device = client.post(
        f"/api/v1/customers/{customer['id']}/devices",
        headers=headers,
        json={"model_id": model["id"], "imei": imei},
    ).json()
    order = client.post(
        ORDERS,
        headers=headers,
        json={
            "customer_id": customer["id"],
            "device_id": device["id"],
            "reported_issue": "Se reinicia solo.",
            "physical_condition": "Buen estado.",
            "unlock_method": "CUSTOMER_UNLOCKS",
        },
    )
    assert order.status_code == 201, order.text
    body: dict[str, Any] = order.json()
    return body


def _to(client: TestClient, headers: dict[str, str], order_id: str, *statuses: str) -> None:
    for status in statuses:
        r = client.post(f"{ORDERS}/{order_id}/status", headers=headers, json={"status": status})
        assert r.status_code == 200, r.text


def _manual(category: str, result: str = "OK") -> list[dict[str, str]]:
    return [{"test_code": t.code, "result": result} for t in catalog.manual_tests_for(category)]


@pytest.fixture
def ready(client: TestClient, tenant: Tenant) -> tuple[dict[str, str], dict[str, str]]:
    admin = login(client, tenant.users[RoleCode.ADMIN].email)
    publish_policy(client, admin)
    publish_terms(client, admin)
    return admin, login(client, tenant.users[RoleCode.TECHNICIAN].email)


def test_manual_diagnostic_gates_the_quotation(
    client: TestClient, ready: tuple[dict[str, str], dict[str, str]]
) -> None:
    admin, tech = ready
    order = _order(client, admin, "PHONE", agent_consent=False)
    url = f"{ORDERS}/{order['id']}/diagnostic"

    view = client.get(url, headers=tech).json()
    assert view["state"] == "NOT_STARTED"
    assert view["editable"] is False  # order still RECIBIDO
    assert view["agent_available"] is False
    assert "computadores" in view["agent_unavailable_reason"]
    assert [r["test_code"] for r in view["results"]][:2] == ["POWER_ON", "SCREEN"]
    assert all(r["result"] is None for r in view["results"])
    early = client.put(f"{url}/results", headers=tech, json={"results": _manual("PHONE")[:1]})
    assert early.status_code == 422

    _to(client, tech, order["id"], "INSPECCION", "DIAGNOSTICO")
    blocked = client.post(
        f"{ORDERS}/{order['id']}/status", headers=tech, json={"status": "COTIZACION"}
    )
    assert blocked.status_code == 422
    assert "diagnóstico" in blocked.json()["detail"]

    # A device that does not power on: the rest is explicitly NOT_TESTED.
    results = [
        {
            "test_code": "POWER_ON",
            "result": "FAIL",
            "observation": "No enciende con cargador original.",
        }
    ]
    saved = client.put(f"{url}/results", headers=tech, json={"results": results}).json()
    assert saved["state"] == "OPEN"
    incomplete = client.post(f"{url}/close", headers=tech, json={"conclusion": "Falla de placa."})
    assert incomplete.status_code == 422
    assert "Pantalla" in incomplete.json()["detail"]

    rest = [{"test_code": t["test_code"], "result": "NOT_TESTED"} for t in _manual("PHONE")[1:]]
    client.put(f"{url}/results", headers=tech, json={"results": rest})
    unknown = client.put(
        f"{url}/results",
        headers=tech,
        json={"results": [{"test_code": "KEYBOARD", "result": "OK"}]},
    )
    assert unknown.status_code == 422
    agent_code = client.put(
        f"{url}/results",
        headers=tech,
        json={"results": [{"test_code": "AGENT_CPU", "result": "OK"}]},
    )
    assert agent_code.status_code == 422

    closed = client.post(
        f"{url}/close",
        headers=tech,
        json={
            "conclusion": "Falla en el circuito de carga.",
            "recommendation": "Cambiar IC de carga.",
        },
    ).json()
    assert closed["state"] == "CLOSED"
    assert closed["editable"] is False
    assert closed["closed_by"]["full_name"].startswith("Usuario Technician")
    power = next(r for r in closed["results"] if r["test_code"] == "POWER_ON")
    assert (power["result"], power["source"]) == ("FAIL", "MANUAL")

    locked = client.put(f"{url}/results", headers=tech, json={"results": _manual("PHONE")[:1]})
    assert locked.status_code == 422
    reopened = client.post(f"{url}/reopen", headers=tech).json()
    assert reopened["state"] == "OPEN"
    client.post(f"{url}/close", headers=tech, json={"conclusion": "Falla en el circuito de carga."})
    _to(client, tech, order["id"], "COTIZACION")

    pdf = client.get(f"{ORDERS}/{order['id']}/diagnostic-report.pdf", headers=admin)
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF")


def test_reception_cannot_record_and_other_technician_is_blocked(
    client: TestClient, ready: tuple[dict[str, str], dict[str, str]], tenant: Tenant, db: Session
) -> None:
    admin, tech = ready
    order = _order(client, admin, "CONSOLE", agent_consent=False)
    _to(client, tech, order["id"], "INSPECCION", "DIAGNOSTICO")  # claimed by tech
    url = f"{ORDERS}/{order['id']}/diagnostic/results"
    reception = login(client, tenant.users[RoleCode.RECEPTIONIST].email)
    assert (
        client.put(url, headers=reception, json={"results": _manual("CONSOLE")}).status_code == 403
    )
    other = login(client, make_user(db, tenant, RoleCode.TECHNICIAN).email)
    assert client.put(url, headers=other, json={"results": _manual("CONSOLE")}).status_code == 403
    assert (
        client.get(f"{ORDERS}/{order['id']}/diagnostic", headers=other).json()["editable"] is False
    )


def test_agent_flow_is_one_time_and_scoped(
    client: TestClient, ready: tuple[dict[str, str], dict[str, str]], db: Session
) -> None:
    admin, tech = ready
    order = _order(client, admin, "LAPTOP")
    url = f"{ORDERS}/{order['id']}/diagnostic"
    assert (
        client.post(f"{url}/agent-pairing", headers=tech).status_code == 422
    )  # not in DIAGNOSTICO
    _to(client, tech, order["id"], "INSPECCION", "DIAGNOSTICO")
    assert client.get(url, headers=tech).json()["agent_available"] is True

    pairing = client.post(f"{url}/agent-pairing", headers=tech)
    assert pairing.status_code == 201, pairing.text
    code = pairing.json()["code"]
    assert len(code) == 9
    assert code[4] == "-"
    assert pairing.json()["download_url"].endswith("erms-agente.exe")

    # The code can be typed in lower case and without the dash.
    paired = client.post(f"{AGENT}/pair", json={"code": code.replace("-", "").lower()})
    assert paired.status_code == 200, paired.text
    assert paired.json()["work_order_number"] == order["number"]
    assert client.post(f"{AGENT}/pair", json={"code": code}).status_code == 401  # one-time
    token = paired.json()["token"]

    assert client.post(f"{AGENT}/report", json=REPORT).status_code == 401
    bad = client.post(f"{AGENT}/report", headers={"Authorization": "Bearer otro"}, json=REPORT)
    assert bad.status_code == 401
    accepted = client.post(
        f"{AGENT}/report", headers={"Authorization": f"Bearer {token}"}, json=REPORT
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["results"] == len(catalog.AGENT_TESTS)
    again = client.post(
        f"{AGENT}/report", headers={"Authorization": f"Bearer {token}"}, json=REPORT
    )
    assert again.status_code == 401  # one report per token

    view = client.get(url, headers=tech).json()
    agent = {r["test_code"]: r for r in view["results"] if r["automated"]}
    assert view["agent_version"] == "0.1.0"
    assert view["agent_elevated"] is False
    assert agent["AGENT_BATTERY"]["result"] == "FAIL"  # 40 % wear reaches the FAIL threshold
    assert agent["AGENT_STABILITY"]["result"] == "WARNING"
    assert agent["AGENT_DISK_SMART"]["result"] == "NOT_SUPPORTED"
    assert agent["AGENT_GPU"]["result"] == "NOT_SUPPORTED"
    assert "Sin datos" in agent["AGENT_GPU"]["observation"]
    assert agent["AGENT_SYSTEM"]["evidence"]["bios_serial"] == "ABC123"
    assert {r["source"] for r in agent.values()} == {"AGENT"}


def test_agent_requires_consent_and_valid_codes(
    client: TestClient, ready: tuple[dict[str, str], dict[str, str]], db: Session
) -> None:
    admin, tech = ready
    no_consent = _order(client, admin, "DESKTOP", agent_consent=False)
    _to(client, tech, no_consent["id"], "INSPECCION", "DIAGNOSTICO")
    refused = client.post(f"{ORDERS}/{no_consent['id']}/diagnostic/agent-pairing", headers=tech)
    assert refused.status_code == 422
    assert "no ha autorizado" in refused.json()["detail"]

    order = _order(client, admin, "LAPTOP")
    _to(client, tech, order["id"], "INSPECCION", "DIAGNOSTICO")
    url = f"{ORDERS}/{order['id']}/diagnostic/agent-pairing"
    first = client.post(url, headers=tech).json()["code"]
    second = client.post(url, headers=tech).json()["code"]
    # A new code invalidates the previous one.
    assert client.post(f"{AGENT}/pair", json={"code": first}).status_code == 401
    db.execute(update(AgentPairing).values(expires_at=utcnow() - timedelta(minutes=1)))
    db.commit()
    assert client.post(f"{AGENT}/pair", json={"code": second}).status_code == 401
    assert client.post(f"{AGENT}/pair", json={"code": "ZZZZ-ZZZZ"}).status_code == 401


def test_closing_invalidates_the_agent_token(
    client: TestClient, ready: tuple[dict[str, str], dict[str, str]]
) -> None:
    admin, tech = ready
    order = _order(client, admin, "LAPTOP")
    _to(client, tech, order["id"], "INSPECCION", "DIAGNOSTICO")
    url = f"{ORDERS}/{order['id']}/diagnostic"
    code = client.post(f"{url}/agent-pairing", headers=tech).json()["code"]
    token = client.post(f"{AGENT}/pair", json={"code": code}).json()["token"]
    client.put(f"{url}/results", headers=tech, json={"results": _manual("LAPTOP")})
    client.post(f"{url}/close", headers=tech, json={"conclusion": "Sin fallas de hardware."})
    late = client.post(f"{AGENT}/report", headers={"Authorization": f"Bearer {token}"}, json=REPORT)
    assert late.status_code == 401


def test_diagnostic_is_isolated_between_organizations(
    client: TestClient, ready: tuple[dict[str, str], dict[str, str]], db: Session
) -> None:
    admin, _ = ready
    order = _order(client, admin, "PHONE")
    other = make_tenant(db, slug="otro-taller")
    other_admin = login(client, make_user(db, other, RoleCode.ADMIN).email)
    assert client.get(f"{ORDERS}/{order['id']}/diagnostic", headers=other_admin).status_code == 404
    assert (
        client.get(f"{ORDERS}/{order['id']}/diagnostic-report.pdf", headers=other_admin).status_code
        == 404
    )
