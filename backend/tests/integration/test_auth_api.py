from datetime import timedelta
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.modules.audit.models import AuditLog
from app.modules.auth.models import RefreshToken
from app.modules.roles.catalog import RoleCode
from app.shared.context import utcnow

from .conftest import PASSWORD, CapturingMailer, Tenant, login, make_user

NEW_PASSWORD = "Otra-contraseña-segura-456"


def _login_raw(client: TestClient, email: str, password: str = PASSWORD):  # type: ignore[no-untyped-def]
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def test_login_returns_access_token_and_secure_refresh_cookie(
    client: TestClient, tenant: Tenant
) -> None:
    admin = tenant.users[RoleCode.ADMIN]
    response = _login_raw(client, admin.email.upper())  # email is case-insensitive

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["must_change_password"] is False
    cookie = response.headers["set-cookie"]
    assert "erms_refresh=" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=strict" in cookie
    assert "Path=/api/v1/auth" in cookie


def test_me_returns_roles_and_effective_permissions(client: TestClient, tenant: Tenant) -> None:
    headers = login(client, tenant.users[RoleCode.SUPERVISOR].email)
    me = client.get("/api/v1/auth/me", headers=headers).json()
    assert [r["code"] for r in me["roles"]] == ["SUPERVISOR"]
    assert me["permissions"] == [
        "audit:read",
        "catalog:manage",
        "customers:manage",
        "customers:read",
        "devices:manage",
        "users:manage",
        "users:read",
        "work_orders:assign",
        "work_orders:create",
        "work_orders:deliver",
        "work_orders:progress",
        "work_orders:read",
    ]
    assert me["organization"]["name"] == tenant.organization.name


def test_wrong_password_and_unknown_email_get_the_same_answer(
    client: TestClient, tenant: Tenant
) -> None:
    wrong = _login_raw(client, tenant.users[RoleCode.ADMIN].email, "incorrecta")
    unknown = _login_raw(client, "nadie@example.com", "incorrecta")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["detail"] == unknown.json()["detail"]
    assert wrong.json()["code"] == "invalid_credentials"


def test_account_locks_after_max_failed_attempts(
    client: TestClient, tenant: Tenant, db: Session
) -> None:
    user = tenant.users[RoleCode.TECHNICIAN]
    for _ in range(5):
        assert _login_raw(client, user.email, "incorrecta").status_code == 401

    # Even the right password is rejected while locked.
    assert _login_raw(client, user.email).status_code == 401

    db.expire_all()
    failures = db.scalars(
        select(AuditLog).where(
            AuditLog.action == "auth.login_failed", AuditLog.entity_id == str(user.id)
        )
    ).all()
    assert len(failures) == 6
    assert any("locked" in (f.changes or {}).get("reason", "") for f in failures)

    # Once the lock expires the user can log in again.
    db.execute(update(type(user)).where(type(user).id == user.id).values(locked_until=utcnow()))
    db.commit()
    assert _login_raw(client, user.email).status_code == 200


def test_inactive_user_cannot_login(client: TestClient, tenant: Tenant, db: Session) -> None:
    user = make_user(db, tenant, RoleCode.TECHNICIAN, is_active=False)
    assert _login_raw(client, user.email).status_code == 401


def test_refresh_rotates_token_and_detects_reuse(
    client: TestClient, tenant: Tenant, db: Session
) -> None:
    _login_raw(client, tenant.users[RoleCode.ADMIN].email)
    original = client.cookies.get("erms_refresh")
    assert original

    rotated = client.post("/api/v1/auth/refresh")
    assert rotated.status_code == 200
    new_cookie = client.cookies.get("erms_refresh")
    assert new_cookie
    assert new_cookie != original

    def refresh_with(token: str) -> Response:
        client.cookies.clear()
        client.cookies.set("erms_refresh", token)
        response: Response = client.post("/api/v1/auth/refresh")
        return response

    # Within the grace window (concurrent tabs) the old token is rejected but the session lives.
    assert refresh_with(original).status_code == 401
    renewed = refresh_with(new_cookie)
    assert renewed.status_code == 200
    latest = renewed.cookies["erms_refresh"]

    # After the grace window, replaying an old token (theft) kills the whole session.
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.revoked_at.is_not(None))
        .values(revoked_at=utcnow() - timedelta(minutes=5))
    )
    db.commit()
    assert refresh_with(original).status_code == 401
    assert refresh_with(latest).status_code == 401


def test_refresh_without_cookie_is_rejected(client: TestClient) -> None:
    response = client.post("/api/v1/auth/refresh")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_session_expires_after_absolute_lifetime(
    client: TestClient, tenant: Tenant, db: Session
) -> None:
    _login_raw(client, tenant.users[RoleCode.ADMIN].email)
    past = utcnow() - timedelta(seconds=1)
    db.execute(update(RefreshToken).values(expires_at=past, session_expires_at=past))
    db.commit()
    assert client.post("/api/v1/auth/refresh").status_code == 401


def test_logout_revokes_session_and_access_token(client: TestClient, tenant: Tenant) -> None:
    headers = login(client, tenant.users[RoleCode.ADMIN].email)
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200

    assert client.post("/api/v1/auth/logout").status_code == 204
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
    assert client.post("/api/v1/auth/refresh").status_code == 401


def test_protected_endpoints_require_a_valid_token(client: TestClient, tenant: Tenant) -> None:
    assert client.get("/api/v1/users").status_code == 401
    bad = {"Authorization": "Bearer not-a-jwt"}
    assert client.get("/api/v1/users", headers=bad).status_code == 401


def test_temporary_password_must_be_changed_before_using_the_app(
    client: TestClient, tenant: Tenant, db: Session
) -> None:
    user = make_user(db, tenant, RoleCode.ADMIN, must_change_password=True)
    response = _login_raw(client, user.email)
    assert response.json()["must_change_password"] is True
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}

    blocked = client.get("/api/v1/users", headers=headers)
    assert blocked.status_code == 403
    assert blocked.json()["code"] == "password_change_required"
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200

    weak = client.post(
        "/api/v1/auth/password/change",
        headers=headers,
        json={"current_password": PASSWORD, "new_password": "corta"},
    )
    assert weak.status_code == 422
    assert weak.json()["errors"][0]["type"] == "password_policy"

    changed = client.post(
        "/api/v1/auth/password/change",
        headers=headers,
        json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
    )
    assert changed.status_code == 204
    assert client.get("/api/v1/users", headers=headers).status_code == 200


def test_change_password_rejects_wrong_current_password(client: TestClient, tenant: Tenant) -> None:
    headers = login(client, tenant.users[RoleCode.ADMIN].email)
    response = client.post(
        "/api/v1/auth/password/change",
        headers=headers,
        json={"current_password": "incorrecta", "new_password": NEW_PASSWORD},
    )
    assert response.status_code == 401


def test_password_reset_flow(client: TestClient, tenant: Tenant, mailer: CapturingMailer) -> None:
    user = tenant.users[RoleCode.RECEPTIONIST]
    other_session = TestClient(client.app)
    login(other_session, user.email)

    unknown = client.post("/api/v1/auth/password/forgot", json={"email": "nadie@example.com"})
    known = client.post("/api/v1/auth/password/forgot", json={"email": user.email})
    assert unknown.status_code == known.status_code == 202
    assert unknown.json() == known.json()
    assert len(mailer.sent) == 1
    assert mailer.sent[0].to == user.email

    link = next(line for line in mailer.sent[0].text.splitlines() if "token=" in line)
    token = parse_qs(urlparse(link.strip()).query)["token"][0]

    reset = client.post(
        "/api/v1/auth/password/reset", json={"token": token, "new_password": NEW_PASSWORD}
    )
    assert reset.status_code == 204
    assert _login_raw(client, user.email).status_code == 401
    assert _login_raw(client, user.email, NEW_PASSWORD).status_code == 200
    # Existing sessions were closed and the link cannot be reused.
    assert other_session.post("/api/v1/auth/refresh").status_code == 401
    again = client.post(
        "/api/v1/auth/password/reset", json={"token": token, "new_password": NEW_PASSWORD + "x"}
    )
    assert again.status_code == 401
