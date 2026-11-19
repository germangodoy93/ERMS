from fastapi.testclient import TestClient

from app.modules.roles.catalog import RoleCode

from .conftest import Tenant, login


def test_roles_list_and_permission_catalog(client: TestClient, tenant: Tenant) -> None:
    headers = login(client, tenant.users[RoleCode.SUPERVISOR].email)
    roles = {r["code"]: r for r in client.get("/api/v1/roles", headers=headers).json()}
    assert set(roles) == {"ADMIN", "SUPERVISOR", "TECHNICIAN", "RECEPTIONIST"}
    assert roles["ADMIN"]["permissions"] == sorted(roles["ADMIN"]["permissions"])
    catalog = client.get("/api/v1/permissions", headers=headers).json()
    assert {p["code"] for p in catalog} == set(roles["ADMIN"]["permissions"])


def test_permission_changes_take_effect_immediately(client: TestClient, tenant: Tenant) -> None:
    admin_headers = login(client, tenant.users[RoleCode.ADMIN].email)
    tech_client = TestClient(client.app)
    tech_headers = login(tech_client, tenant.users[RoleCode.TECHNICIAN].email)
    assert tech_client.get("/api/v1/audit-logs", headers=tech_headers).status_code == 403

    technician_role = tenant.roles[RoleCode.TECHNICIAN].id
    response = client.put(
        f"/api/v1/roles/{technician_role}/permissions",
        headers=admin_headers,
        json={"permissions": ["audit:read"]},
    )
    assert response.status_code == 200
    # Same access token: permissions are not embedded in the JWT.
    assert tech_client.get("/api/v1/audit-logs", headers=tech_headers).status_code == 200


def test_admin_role_is_immutable_and_unknown_permissions_rejected(
    client: TestClient, tenant: Tenant
) -> None:
    headers = login(client, tenant.users[RoleCode.ADMIN].email)
    admin_role = tenant.roles[RoleCode.ADMIN].id
    assert (
        client.put(
            f"/api/v1/roles/{admin_role}/permissions", headers=headers, json={"permissions": []}
        ).status_code
        == 422
    )
    supervisor_role = tenant.roles[RoleCode.SUPERVISOR].id
    assert (
        client.put(
            f"/api/v1/roles/{supervisor_role}/permissions",
            headers=headers,
            json={"permissions": ["no:existe"]},
        ).status_code
        == 422
    )


def test_supervisor_cannot_edit_role_permissions(client: TestClient, tenant: Tenant) -> None:
    headers = login(client, tenant.users[RoleCode.SUPERVISOR].email)
    role = tenant.roles[RoleCode.SUPERVISOR].id
    response = client.put(
        f"/api/v1/roles/{role}/permissions",
        headers=headers,
        json={"permissions": ["users:read", "roles:manage"]},
    )
    assert response.status_code == 403


def test_audit_log_lists_actions_with_actor_and_filters(client: TestClient, tenant: Tenant) -> None:
    admin = tenant.users[RoleCode.ADMIN]
    headers = login(client, admin.email)
    client.post("/api/v1/auth/login", json={"email": admin.email, "password": "incorrecta"})

    page = client.get("/api/v1/audit-logs", headers=headers).json()
    actions = [item["action"] for item in page["items"]]
    assert "auth.login" in actions
    assert "auth.login_failed" in actions
    login_entry = next(i for i in page["items"] if i["action"] == "auth.login")
    assert login_entry["actor"]["email"] == admin.email

    filtered = client.get("/api/v1/audit-logs?action=auth.login_failed", headers=headers).json()
    assert {i["action"] for i in filtered["items"]} == {"auth.login_failed"}

    by_entity = client.get(
        f"/api/v1/audit-logs?entity_type=user&entity_id={admin.id}&actor_user_id={admin.id}",
        headers=headers,
    ).json()
    assert by_entity["total"] >= 1
    assert all(i["actor"]["id"] == str(admin.id) for i in by_entity["items"])

    future = client.get("/api/v1/audit-logs?date_from=2999-01-01T00:00:00Z", headers=headers).json()
    assert future["total"] == 0
    past = client.get("/api/v1/audit-logs?date_to=2000-01-01T00:00:00Z", headers=headers).json()
    assert past["total"] == 0


def test_supervisor_reads_audit_but_technician_cannot(client: TestClient, tenant: Tenant) -> None:
    supervisor = login(client, tenant.users[RoleCode.SUPERVISOR].email)
    assert client.get("/api/v1/audit-logs", headers=supervisor).status_code == 200
    technician = login(client, tenant.users[RoleCode.TECHNICIAN].email)
    assert client.get("/api/v1/audit-logs", headers=technician).status_code == 403
