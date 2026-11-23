"""Fixtures for tests against a real PostgreSQL (ERMS_TEST_DATABASE_URL, disposable).

The schema is migrated once per session; each API test starts from empty business tables
(the permission catalog, inserted by migrations, is preserved).
"""

import os
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session

from app.core import database
from app.core.config import Settings, get_settings
from app.core.email import OutgoingEmail, get_mailer
from app.core.security import hash_password
from app.core.storage import LocalStorage, get_storage
from app.main import create_app
from app.modules.auth import router as auth_router
from app.modules.devices.catalog import seed_manufacturers
from app.modules.health.checks import BACKEND_ROOT
from app.modules.organizations.models import Branch, Organization
from app.modules.roles.catalog import RoleCode
from app.modules.roles.models import Role
from app.modules.roles.service import create_system_roles
from app.modules.users.models import User

TEST_DB_URL = os.environ.get("ERMS_TEST_DATABASE_URL")
PASSWORD = "Contraseña-de-prueba-123"

BUSINESS_TABLES = (
    "assembly_build_items",
    "assembly_builds",
    "warranty_claims",
    "warranties",
    "payments",
    "quality_checks",
    "repair_parts",
    "repair_tasks",
    "quotation_items",
    "quotations",
    "inventory_movements",
    "stock_entries",
    "stock_levels",
    "parts",
    "suppliers",
    "agent_pairings",
    "diagnostic_results",
    "diagnostic_sessions",
    "attachments",
    "work_order_status_history",
    "work_orders",
    "reception_terms",
    "document_sequences",
    "devices",
    "device_models",
    "manufacturers",
    "customer_consents",
    "customers",
    "privacy_policies",
    "audit_logs",
    "password_reset_tokens",
    "refresh_tokens",
    "user_roles",
    "users",
    "role_permissions",
    "roles",
    "branches",
    "organizations",
)


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if "integration" in item.path.parts:
            item.add_marker(pytest.mark.integration)
            if not TEST_DB_URL:
                item.add_marker(pytest.mark.skip(reason="ERMS_TEST_DATABASE_URL is not set"))


def _clear_caches() -> None:
    if database.get_engine.cache_info().currsize:
        database.get_engine().dispose()  # close pooled connections opened by the app
    get_settings.cache_clear()
    database.get_engine.cache_clear()
    database.get_session_factory.cache_clear()


@pytest.fixture(scope="session")
def settings() -> Iterator[Settings]:
    assert TEST_DB_URL
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = TEST_DB_URL
    _clear_caches()
    yield get_settings()
    if previous is not None:
        os.environ["DATABASE_URL"] = previous
    _clear_caches()


@pytest.fixture(scope="session")
def alembic_config(settings: Settings) -> Config:
    return Config(str(BACKEND_ROOT / "alembic.ini"))


@pytest.fixture(scope="session")
def engine(settings: Settings, alembic_config: Config) -> Iterator[Engine]:
    command.upgrade(alembic_config, "head")
    eng = create_engine(settings.database_url)
    yield eng
    eng.dispose()


@pytest.fixture
def db(engine: Engine) -> Iterator[Session]:
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {', '.join(BUSINESS_TABLES)} RESTART IDENTITY CASCADE"))
    with Session(engine, expire_on_commit=False) as session:
        yield session


class CapturingMailer:
    def __init__(self) -> None:
        self.sent: list[OutgoingEmail] = []

    def send(self, message: OutgoingEmail) -> None:
        self.sent.append(message)


@pytest.fixture
def mailer() -> CapturingMailer:
    return CapturingMailer()


@pytest.fixture
def storage(tmp_path: Path) -> LocalStorage:
    return LocalStorage(tmp_path / "attachments")


@pytest.fixture
def client(db: Session, mailer: CapturingMailer, storage: LocalStorage) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_mailer] = lambda: mailer
    auth_router._login_limiter = None  # fresh per-IP counter for each test
    app.dependency_overrides[get_storage] = lambda: storage
    with TestClient(app) as test_client:
        yield test_client


@dataclass
class Tenant:
    organization: Organization
    roles: dict[RoleCode, Role]
    users: dict[str, User] = field(default_factory=dict)


def make_tenant(db: Session, slug: str = "taller-prueba") -> Tenant:
    organization = Organization(name=f"Organización de prueba {slug}", slug=slug)
    db.add(organization)
    db.flush()
    db.add(Branch(organization_id=organization.id, name="Sede Bogotá", city="Bogotá"))
    roles = create_system_roles(db, organization.id)
    seed_manufacturers(db, organization.id)
    db.commit()
    return Tenant(organization=organization, roles=roles)


def make_user(
    db: Session,
    tenant: Tenant,
    role: RoleCode,
    *,
    email: str | None = None,
    must_change_password: bool = False,
    is_active: bool = True,
) -> User:
    user = User(
        organization_id=tenant.organization.id,
        email=email or f"{role.lower()}-{uuid.uuid4().hex[:8]}@example.com",
        full_name=f"Usuario {role.title()} de prueba",
        password_hash=hash_password(PASSWORD),
        must_change_password=must_change_password,
        is_active=is_active,
        roles=[tenant.roles[role]],
    )
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def tenant(db: Session) -> Tenant:
    tenant = make_tenant(db)
    for role in RoleCode:
        tenant.users[role] = make_user(db, tenant, role)
    return tenant


def login(client: TestClient, email: str, password: str = PASSWORD) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


# Obviously fictitious workshop data (docs/ERMS-TEST-PLAN.md, rules).
WORKSHOP_DATA = {
    "legal_name": "Taller Ficticio de Pruebas SAS",
    "tax_id": "890903938",
    "address": "Calle Ficticia 1 # 2-3",
    "city": "Bogotá",
    "phone": "601 000 0000",
    "email": "datos@example.com",
}


def publish_policy(client: TestClient, admin_headers: dict[str, str]) -> dict[str, object]:
    """Completes the workshop data and publishes the policy template as-is."""
    response = client.patch("/api/v1/organization", headers=admin_headers, json=WORKSHOP_DATA)
    assert response.status_code == 200, response.text
    draft = client.get("/api/v1/privacy-policy/draft", headers=admin_headers).json()
    assert draft["missing_fields"] == []
    response = client.post(
        "/api/v1/privacy-policy", headers=admin_headers, json={"content": draft["content"]}
    )
    assert response.status_code == 201, response.text
    body: dict[str, object] = response.json()
    return body


def new_customer(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "kind": "PERSON",
        "full_name": "  Cliente   Ficticio Pérez ",
        "id_type": "CC",
        "id_number": "1.000.000.001",
        "phone": "300 000 0001",
        "consents": [{"purpose": "DATA_PROCESSING", "channel": "SCREEN"}],
    }
    payload.update(overrides)
    return payload


def publish_terms(client: TestClient, admin_headers: dict[str, str]) -> dict[str, object]:
    template = client.get("/api/v1/reception-terms", headers=admin_headers).json()["template"]
    response = client.post(
        "/api/v1/reception-terms", headers=admin_headers, json={"content": template}
    )
    assert response.status_code == 201, response.text
    body: dict[str, object] = response.json()
    return body


@dataclass
class Shop:
    admin: dict[str, str]
    supervisor: dict[str, str]
    reception: dict[str, str]
    tech: dict[str, str]


@pytest.fixture
def shop(client: TestClient, tenant: Tenant) -> Shop:
    """Workshop ready for commerce tests: policy and terms published, one login per role."""
    admin = login(client, tenant.users[RoleCode.ADMIN].email)
    publish_policy(client, admin)
    publish_terms(client, admin)
    return Shop(
        admin=admin,
        supervisor=login(client, tenant.users[RoleCode.SUPERVISOR].email),
        reception=login(client, tenant.users[RoleCode.RECEPTIONIST].email),
        tech=login(client, tenant.users[RoleCode.TECHNICIAN].email),
    )
