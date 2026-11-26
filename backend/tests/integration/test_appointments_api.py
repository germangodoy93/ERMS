"""Agenda of remote and on-site appointments (PM-04, sprint R1)."""

from datetime import date, datetime, time, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.audit.models import AuditLog
from app.modules.roles.catalog import RoleCode
from app.shared.context import BOGOTA, utcnow
from app.shared.holidays import holiday_name

from .conftest import Shop, Tenant, login, make_tenant, make_user, new_customer, publish_policy

BASE = "/api/v1/appointments"


def _workday(weeks_ahead: int = 1) -> date:
    """A Monday-to-Friday, non-holiday date at least `weeks_ahead` weeks from today."""
    day = utcnow().astimezone(BOGOTA).date() + timedelta(weeks=weeks_ahead)
    while day.weekday() > 4 or holiday_name(day):
        day += timedelta(days=1)
    return day


def _at(day: date, hour: int, minute: int = 0) -> str:
    return datetime.combine(day, time(hour, minute), BOGOTA).isoformat()


def _customer(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/api/v1/customers", headers=headers, json=new_customer())
    assert response.status_code == 201, response.text
    customer_id: str = response.json()["id"]
    return customer_id


def _service(client: TestClient, headers: dict[str, str], name: str) -> dict[str, Any]:
    services = client.get(f"{BASE}/services", headers=headers).json()
    found: dict[str, Any] = next(s for s in services if s["name"] == name)
    return found


def _remote_service(client: TestClient, admin: dict[str, str]) -> dict[str, Any]:
    response = client.post(
        f"{BASE}/services",
        headers=admin,
        json={
            "name": "Soporte remoto",
            "modality": "REMOTE",
            "duration_minutes": 30,
            "price": "50000",
            "tax_rate": 19,
            "price_includes_tax": True,
        },
    )
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


@pytest.fixture
def agenda(client: TestClient, shop: Shop, tenant: Tenant) -> dict[str, Any]:
    customer = _customer(client, shop.reception)
    visit = _service(client, shop.reception, "Visita técnica")
    tech = tenant.users[RoleCode.TECHNICIAN]
    return {"customer": customer, "visit": visit, "tech": str(tech.id)}


def _visit(agenda: dict[str, Any], starts_at: str, **extra: Any) -> dict[str, Any]:
    payload = {
        "customer_id": agenda["customer"],
        "service_id": agenda["visit"]["id"],
        "starts_at": starts_at,
        "technician_id": agenda["tech"],
        "reason": "El computador no enciende.",
        "address": "Calle Ficticia 1 # 2-3, apto 101",
        "locality": "Suba",
    }
    payload.update(extra)
    return payload


def test_new_workshop_has_the_technical_visit_and_default_hours(
    client: TestClient, shop: Shop
) -> None:
    options = client.get(f"{BASE}/options", headers=shop.reception).json()
    assert [s["name"] for s in options["services"]] == ["Visita técnica"]
    visit = options["services"][0]
    assert (visit["modality"], visit["duration_minutes"], visit["price"]) == ("ON_SITE", 60, None)
    assert options["can_manage"] is True
    assert options["hours"][0] == {"weekday": 0, "opens": "08:00:00", "closes": "18:00:00"}
    assert options["hours"][5]["closes"] == "12:00:00"
    assert options["hours"][6]["opens"] is None
    assert "Suba" in options["localities"]
    assert "no se guarda" in options["remote_access_text"]
    assert len(options["technicians"]) >= 1

    holidays = client.get(
        f"{BASE}/holidays", headers=shop.tech, params={"from": "2026-12-01", "to": "2026-12-31"}
    ).json()
    assert holidays == [
        {"date": "2026-12-08", "name": "Inmaculada Concepción"},
        {"date": "2026-12-25", "name": "Navidad"},
    ]


def test_schedule_an_on_site_visit(
    client: TestClient, shop: Shop, agenda: dict[str, Any], db: Session
) -> None:
    day = _workday()
    response = client.post(f"{BASE}", headers=shop.reception, json=_visit(agenda, _at(day, 9)))
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["number"].startswith("CT-")
    assert body["status"] == "SCHEDULED"
    assert body["modality"] == "ON_SITE"
    assert body["duration_minutes"] == 60
    assert body["technician"]["id"] == agenda["tech"]
    assert body["service"]["name"] == "Visita técnica"
    assert body["remote_consent_at"] is None
    ends = datetime.fromisoformat(body["ends_at"]).astimezone(BOGOTA)
    assert ends.time() == time(10)

    listed = client.get(
        BASE, headers=shop.reception, params={"from": day.isoformat(), "to": day.isoformat()}
    ).json()
    assert [a["number"] for a in listed] == [body["number"]]

    audit = db.scalar(select(AuditLog).where(AuditLog.action == "appointment.created"))
    assert audit is not None
    assert audit.changes is not None
    assert audit.changes["modality"] == "ON_SITE"
    assert "El computador" not in str(audit.changes)  # no free text about the customer


def test_on_site_needs_address_and_rules_of_time(
    client: TestClient, shop: Shop, agenda: dict[str, Any]
) -> None:
    day = _workday()

    def post(**extra: Any) -> str:
        response = client.post(f"{BASE}", headers=shop.reception, json=_visit(agenda, **extra))
        assert response.status_code == 422, response.text
        detail: str = response.json()["detail"]
        return detail

    assert "dirección" in post(starts_at=_at(day, 9), address=None)
    assert "Fuera del horario" in post(starts_at=_at(day, 17, 30))
    assert "Fuera del horario" in post(starts_at=_at(day, 7))
    sunday = day + timedelta(days=6 - day.weekday())
    assert "no hay servicio" in post(starts_at=_at(sunday, 9))
    assert "festivo" in post(starts_at=_at(date(2027, 12, 8), 9))
    past = utcnow().astimezone(BOGOTA).date() - timedelta(days=7)
    assert "pasado" in post(starts_at=_at(past, 9))


def test_remote_appointment_requires_the_customer_authorization(
    client: TestClient, shop: Shop, agenda: dict[str, Any]
) -> None:
    remote = _remote_service(client, shop.admin)
    assert (remote["price"], remote["tax_rate"]) == ("50000.00", 19)
    payload = _visit(agenda, _at(_workday(), 10), service_id=remote["id"])
    response = client.post(f"{BASE}", headers=shop.reception, json=payload)
    assert response.status_code == 422
    assert "acceso remoto" in response.json()["detail"]

    payload["remote_consent_channel"] = "VERBAL"
    response = client.post(f"{BASE}", headers=shop.reception, json=payload)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["modality"] == "REMOTE"
    assert body["duration_minutes"] == 30
    assert body["remote_consent_channel"] == "VERBAL"
    assert "no se guarda" in body["remote_consent_text"]
    assert body["address"] is None
    assert body["locality"] is None


def test_overlap_needs_a_reason(client: TestClient, shop: Shop, agenda: dict[str, Any]) -> None:
    day = _workday()
    first = client.post(f"{BASE}", headers=shop.reception, json=_visit(agenda, _at(day, 9)))
    assert first.status_code == 201
    clash = _visit(agenda, _at(day, 9, 30))
    response = client.post(f"{BASE}", headers=shop.reception, json=clash)
    assert response.status_code == 409
    problem = response.json()
    assert problem["code"] == "appointment_overlap"
    assert first.json()["number"] in problem["detail"]
    assert problem["errors"][0]["number"] == first.json()["number"]

    # Back to back is not an overlap.
    after = client.post(f"{BASE}", headers=shop.reception, json=_visit(agenda, _at(day, 10)))
    assert after.status_code == 201, after.text

    clash["overlap_reason"] = "El cliente solo puede a esa hora; el técnico llega en moto."
    response = client.post(f"{BASE}", headers=shop.reception, json=clash)
    assert response.status_code == 201, response.text
    assert response.json()["overlap_reason"].startswith("El cliente")

    # Without a technician there is no clash to check.
    free = client.post(
        f"{BASE}", headers=shop.reception, json=_visit(agenda, _at(day, 9), technician_id=None)
    )
    assert free.status_code == 201, free.text


def test_reschedule_reassign_and_cancel(
    client: TestClient, shop: Shop, agenda: dict[str, Any], tenant: Tenant, db: Session
) -> None:
    day = _workday()
    a = client.post(f"{BASE}", headers=shop.reception, json=_visit(agenda, _at(day, 9))).json()
    b = client.post(f"{BASE}", headers=shop.reception, json=_visit(agenda, _at(day, 14))).json()

    # Moving B onto A clashes; with a reason it is saved.
    move = client.patch(
        f"{BASE}/{b['id']}", headers=shop.reception, json={"starts_at": _at(day, 9)}
    )
    assert move.status_code == 409
    move = client.patch(
        f"{BASE}/{b['id']}",
        headers=shop.reception,
        json={"starts_at": _at(day, 11), "duration_minutes": 90, "locality": "Kennedy"},
    )
    assert move.status_code == 200, move.text
    moved = move.json()
    assert datetime.fromisoformat(moved["starts_at"]).astimezone(BOGOTA).time() == time(11)
    assert moved["duration_minutes"] == 90
    assert moved["locality"] == "Kennedy"

    other = make_user(db, tenant, RoleCode.TECHNICIAN, email="otro-tecnico@example.com")
    reassigned = client.patch(
        f"{BASE}/{b['id']}", headers=shop.supervisor, json={"technician_id": str(other.id)}
    )
    assert reassigned.status_code == 200, reassigned.text
    assert reassigned.json()["technician"]["id"] == str(other.id)

    bad = client.patch(f"{BASE}/{a['id']}", headers=shop.reception, json={"starts_at": None})
    assert bad.status_code == 422

    cancel = client.post(f"{BASE}/{a['id']}/cancel", headers=shop.reception, json={"reason": ""})
    assert cancel.status_code == 422
    cancel = client.post(
        f"{BASE}/{a['id']}/cancel",
        headers=shop.reception,
        json={"reason": "El cliente lo llevará al taller."},
    )
    assert cancel.status_code == 200, cancel.text
    assert cancel.json()["status"] == "CANCELLED"
    again = client.patch(f"{BASE}/{a['id']}", headers=shop.reception, json={"notes": "x"})
    assert again.status_code == 422

    params = {"from": day.isoformat(), "to": day.isoformat()}
    assert [x["id"] for x in client.get(BASE, headers=shop.reception, params=params).json()] == [
        b["id"]
    ]
    with_cancelled = client.get(
        BASE, headers=shop.reception, params={**params, "include_cancelled": "true"}
    ).json()
    assert len(with_cancelled) == 2
    # The cancelled slot is free again.
    assert (
        client.post(f"{BASE}", headers=shop.reception, json=_visit(agenda, _at(day, 9))).status_code
        == 201
    )


def test_technicians_see_only_their_appointments_and_cannot_schedule(
    client: TestClient, shop: Shop, agenda: dict[str, Any]
) -> None:
    day = _workday()
    mine = client.post(f"{BASE}", headers=shop.reception, json=_visit(agenda, _at(day, 9))).json()
    other = client.post(
        f"{BASE}", headers=shop.reception, json=_visit(agenda, _at(day, 11), technician_id=None)
    ).json()
    params = {"from": day.isoformat(), "to": day.isoformat()}
    seen = client.get(BASE, headers=shop.tech, params=params).json()
    assert [a["id"] for a in seen] == [mine["id"]]
    assert client.get(f"{BASE}/{other['id']}", headers=shop.tech).status_code == 403
    assert client.get(f"{BASE}/options", headers=shop.tech).json()["can_manage"] is False
    assert client.get(BASE, headers=shop.reception, params=params).json().__len__() == 2

    assert (
        client.post(f"{BASE}", headers=shop.tech, json=_visit(agenda, _at(day, 14))).status_code
        == 403
    )
    assert (
        client.post(
            f"{BASE}/{mine['id']}/cancel", headers=shop.tech, json={"reason": "No"}
        ).status_code
        == 403
    )


def test_service_catalog_and_hours_are_managed_by_the_admin(
    client: TestClient, shop: Shop, agenda: dict[str, Any]
) -> None:
    visit = agenda["visit"]
    payload = {**visit, "price": "80000", "duration_minutes": 90}
    for key in ("id", "is_active"):
        payload.pop(key)
    assert (
        client.put(
            f"{BASE}/services/{visit['id']}", headers=shop.reception, json=payload
        ).status_code
        == 403
    )
    updated = client.put(f"{BASE}/services/{visit['id']}", headers=shop.admin, json=payload)
    assert updated.status_code == 200, updated.text
    assert (updated.json()["price"], updated.json()["duration_minutes"]) == ("80000.00", 90)
    duplicate = client.post(f"{BASE}/services", headers=shop.admin, json=payload)
    assert duplicate.status_code == 409
    bad_tax = client.post(
        f"{BASE}/services", headers=shop.admin, json={**payload, "name": "Otro", "tax_rate": 5}
    )
    assert bad_tax.status_code == 422

    # Deactivated services are not offered and cannot be scheduled.
    off = client.put(
        f"{BASE}/services/{visit['id']}", headers=shop.admin, json={**payload, "is_active": False}
    )
    assert off.json()["is_active"] is False
    assert client.get(f"{BASE}/options", headers=shop.reception).json()["services"] == []
    response = client.post(
        f"{BASE}", headers=shop.reception, json=_visit(agenda, _at(_workday(), 9))
    )
    assert response.status_code == 422
    client.put(f"{BASE}/services/{visit['id']}", headers=shop.admin, json=payload)

    # Hours: only mornings on Monday-Friday, independent of the workshop.
    days = [
        {"weekday": d, "opens": "08:00", "closes": "12:00"}
        if d < 5
        else {"weekday": d, "opens": None, "closes": None}
        for d in range(7)
    ]
    assert (
        client.put(f"{BASE}/hours", headers=shop.reception, json={"days": days}).status_code == 403
    )
    saved = client.put(f"{BASE}/hours", headers=shop.admin, json={"days": days})
    assert saved.status_code == 200, saved.text
    assert saved.json()["is_default"] is False
    assert saved.json()["days"][5]["opens"] is None
    day = _workday()
    late = client.post(f"{BASE}", headers=shop.reception, json=_visit(agenda, _at(day, 14)))
    assert late.status_code == 422
    assert "08:00 a 12:00" in late.json()["detail"]
    ok = client.post(f"{BASE}", headers=shop.reception, json=_visit(agenda, _at(day, 10, 30)))
    assert ok.status_code == 201, ok.text


def test_range_limits_and_isolation(
    client: TestClient, shop: Shop, agenda: dict[str, Any], db: Session
) -> None:
    day = _workday()
    created = client.post(
        f"{BASE}", headers=shop.reception, json=_visit(agenda, _at(day, 9))
    ).json()
    wide = client.get(
        BASE, headers=shop.reception, params={"from": "2026-01-01", "to": "2026-12-31"}
    )
    assert wide.status_code == 422
    backwards = client.get(
        BASE, headers=shop.reception, params={"from": "2026-12-02", "to": "2026-12-01"}
    )
    assert backwards.status_code == 422

    other = make_tenant(db, slug="otro-taller")
    admin = make_user(db, other, RoleCode.ADMIN)
    headers = login(client, admin.email)
    publish_policy(client, headers)
    assert client.get(f"{BASE}/{created['id']}", headers=headers).status_code == 404
    params = {"from": day.isoformat(), "to": day.isoformat()}
    assert client.get(BASE, headers=headers, params=params).json() == []
    # Its own catalog: the other workshop's visit cannot be used.
    payload = _visit(agenda, _at(day, 9), technician_id=None)
    assert client.post(f"{BASE}", headers=headers, json=payload).status_code == 404
