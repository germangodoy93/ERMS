from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.audit.models import AuditLog
from app.modules.roles.catalog import RoleCode

from .conftest import PASSWORD, Tenant, login, make_tenant, make_user

TEMP_PASSWORD = "Temporal-segura-2026"


def _new_user(
    tenant: Tenant, role: RoleCode, email: str = "nuevo@example.com"
) -> dict[str, object]:
    return {
        "email": email,
        "full_name": "  Persona   Nueva  ",
        "temporary_password": TEMP_PASSWORD,
        "role_ids": [str(tenant.roles[role].id)],
    }


def test_admin_creates_user_with_temporary_password(
    client: TestClient, tenant: Tenant, db: Session
) -> None:
    headers = login(client, tenant.users[RoleCode.ADMIN].email)
    response = client.post(
        "/api/v1/users",
        headers=headers,
        json=_new_user(tenant, RoleCode.TECHNICIAN, "Nuevo@example.com"),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["email"] == "nuevo@example.com"
    assert body["full_name"] == "Persona Nueva"
    assert body["must_change_password"] is True
    assert [r["code"] for r in body["roles"]] == ["TECHNICIAN"]

    log = db.scalar(select(AuditLog).where(AuditLog.action == "user.created"))
    assert log is not None
    assert "password" not in str(log.changes).lower()

    login_response = client.post(
        "/api/v1/auth/login", json={"email": "nuevo@example.com", "password": TEMP_PASSWORD}
    )
    assert login_response.json()["must_change_password"] is True


def test_duplicate_email_is_rejected(client: TestClient, tenant: Tenant) -> None:
    headers = login(client, tenant.users[RoleCode.ADMIN].email)
    existing = tenant.users[RoleCode.TECHNICIAN].email.upper()
    response = client.post(
        "/api/v1/users", headers=headers, json=_new_user(tenant, RoleCode.TECHNICIAN, existing)
    )
    assert response.status_code == 409


def test_weak_temporary_password_is_rejected(client: TestClient, tenant: Tenant) -> None:
    headers = login(client, tenant.users[RoleCode.ADMIN].email)
    payload = _new_user(tenant, RoleCode.TECHNICIAN) | {"temporary_password": "123"}
    assert client.post("/api/v1/users", headers=headers, json=payload).status_code == 422


def test_supervisor_manages_users_but_cannot_escalate_to_admin(
    client: TestClient, tenant: Tenant
) -> None:
    headers = login(client, tenant.users[RoleCode.SUPERVISOR].email)
    created = client.post(
        "/api/v1/users", headers=headers, json=_new_user(tenant, RoleCode.RECEPTIONIST)
    )
    assert created.status_code == 201

    as_admin = client.post(
        "/api/v1/users",
        headers=headers,
        json=_new_user(tenant, RoleCode.ADMIN, "otro@example.com"),
    )
    assert as_admin.status_code == 403

    supervisor_id = tenant.users[RoleCode.SUPERVISOR].id
    promote_self = client.put(
        f"/api/v1/users/{supervisor_id}/roles",
        headers=headers,
        json={"role_ids": [str(tenant.roles[RoleCode.ADMIN].id)]},
    )
    assert promote_self.status_code == 403

    admin_id = tenant.users[RoleCode.ADMIN].id
    assert (
        client.patch(
            f"/api/v1/users/{admin_id}", headers=headers, json={"is_active": False}
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/v1/users/{admin_id}/temporary-password",
            headers=headers,
            json={"temporary_password": TEMP_PASSWORD},
        ).status_code
        == 403
    )


def test_technician_and_receptionist_cannot_access_users(
    client: TestClient, tenant: Tenant
) -> None:
    for role in (RoleCode.TECHNICIAN, RoleCode.RECEPTIONIST):
        headers = login(client, tenant.users[role].email)
        response = client.get("/api/v1/users", headers=headers)
        assert response.status_code == 403
        assert response.json()["code"] == "permission_denied"


def test_cannot_deactivate_self_or_last_admin(client: TestClient, tenant: Tenant) -> None:
    admin = tenant.users[RoleCode.ADMIN]
    headers = login(client, admin.email)
    self_off = client.patch(f"/api/v1/users/{admin.id}", headers=headers, json={"is_active": False})
    assert self_off.status_code == 422

    demote = client.put(
        f"/api/v1/users/{admin.id}/roles",
        headers=headers,
        json={"role_ids": [str(tenant.roles[RoleCode.SUPERVISOR].id)]},
    )
    assert demote.status_code == 422
    assert "último administrador" in demote.json()["detail"]


def test_second_admin_can_demote_the_first(client: TestClient, tenant: Tenant, db: Session) -> None:
    second = make_user(db, tenant, RoleCode.ADMIN)
    headers = login(client, second.email)
    first = tenant.users[RoleCode.ADMIN]
    response = client.put(
        f"/api/v1/users/{first.id}/roles",
        headers=headers,
        json={"role_ids": [str(tenant.roles[RoleCode.SUPERVISOR].id)]},
    )
    assert response.status_code == 200
    assert [r["code"] for r in response.json()["roles"]] == ["SUPERVISOR"]


def test_deactivating_a_user_closes_their_sessions(client: TestClient, tenant: Tenant) -> None:
    technician = tenant.users[RoleCode.TECHNICIAN]
    tech_client = TestClient(client.app)
    tech_headers = login(tech_client, technician.email)

    headers = login(client, tenant.users[RoleCode.ADMIN].email)
    response = client.patch(
        f"/api/v1/users/{technician.id}", headers=headers, json={"is_active": False}
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False
    assert tech_client.get("/api/v1/auth/me", headers=tech_headers).status_code == 401


def test_update_records_field_changes_in_audit(
    client: TestClient, tenant: Tenant, db: Session
) -> None:
    technician = tenant.users[RoleCode.TECHNICIAN]
    headers = login(client, tenant.users[RoleCode.ADMIN].email)
    response = client.patch(
        f"/api/v1/users/{technician.id}",
        headers=headers,
        json={"full_name": "Nombre Corregido", "phone": "3001234567"},
    )
    assert response.status_code == 200
    log = db.scalar(select(AuditLog).where(AuditLog.action == "user.updated"))
    assert log is not None
    assert log.changes is not None
    assert log.changes["full_name"][1] == "Nombre Corregido"


def test_list_supports_search_filters_and_pagination(client: TestClient, tenant: Tenant) -> None:
    headers = login(client, tenant.users[RoleCode.ADMIN].email)
    page = client.get("/api/v1/users?size=2&page=1", headers=headers).json()
    assert page["total"] == 4
    assert len(page["items"]) == 2

    technicians = client.get("/api/v1/users?role=TECHNICIAN", headers=headers).json()
    assert [u["roles"][0]["code"] for u in technicians["items"]] == ["TECHNICIAN"]

    by_name = client.get("/api/v1/users?q=supervisor", headers=headers).json()
    assert by_name["total"] == 1

    # LIKE wildcards in the search term are treated literally.
    assert client.get("/api/v1/users?q=%25", headers=headers).json()["total"] == 0


def test_users_of_other_organizations_are_invisible(
    client: TestClient, tenant: Tenant, db: Session
) -> None:
    other = make_tenant(db, slug="otro-taller")
    stranger = make_user(db, other, RoleCode.TECHNICIAN)
    headers = login(client, tenant.users[RoleCode.ADMIN].email)

    assert client.get(f"/api/v1/users/{stranger.id}", headers=headers).status_code == 404
    emails = [u["email"] for u in client.get("/api/v1/users", headers=headers).json()["items"]]
    assert stranger.email not in emails
    foreign_role = client.post(
        "/api/v1/users",
        headers=headers,
        json=_new_user(other, RoleCode.TECHNICIAN),
    )
    assert foreign_role.status_code == 422


def test_temporary_password_forces_change(client: TestClient, tenant: Tenant) -> None:
    technician = tenant.users[RoleCode.TECHNICIAN]
    headers = login(client, tenant.users[RoleCode.ADMIN].email)
    response = client.post(
        f"/api/v1/users/{technician.id}/temporary-password",
        headers=headers,
        json={"temporary_password": TEMP_PASSWORD},
    )
    assert response.status_code == 200
    assert response.json()["must_change_password"] is True
    old = client.post("/api/v1/auth/login", json={"email": technician.email, "password": PASSWORD})
    assert old.status_code == 401
