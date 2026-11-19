import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cli import main
from app.modules.organizations.models import Branch, Organization
from app.modules.users.models import User

ADMIN_PASSWORD = "Contraseña-inicial-2026"
ARGS = [
    "bootstrap",
    "--org-name",
    "Taller de prueba SAS",
    "--org-slug",
    "taller-cli",
    "--admin-email",
    "Admin@Example.com",
    "--admin-name",
    "Administrador de prueba",
]


def test_bootstrap_creates_org_branch_roles_and_admin(
    db: Session, client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ERMS_ADMIN_PASSWORD", ADMIN_PASSWORD)
    main(ARGS)

    org = db.scalar(select(Organization).where(Organization.slug == "taller-cli"))
    assert org is not None
    branch = db.scalar(select(Branch).where(Branch.organization_id == org.id))
    assert branch is not None
    assert branch.city == "Bogotá"
    admin = db.scalar(select(User).where(User.email == "admin@example.com"))
    assert admin is not None
    assert admin.must_change_password is True
    assert admin.role_codes == {"ADMIN"}

    response = client.post(
        "/api/v1/auth/login", json={"email": "admin@example.com", "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 200
    assert response.json()["must_change_password"] is True


def test_bootstrap_refuses_to_run_twice(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ERMS_ADMIN_PASSWORD", ADMIN_PASSWORD)
    main(ARGS)
    with pytest.raises(SystemExit, match="ya existe"):
        main(ARGS)


def test_bootstrap_enforces_password_policy(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ERMS_ADMIN_PASSWORD", "debil")
    with pytest.raises(Exception, match="política"):
        main(ARGS)
    assert db.scalar(select(Organization)) is None
