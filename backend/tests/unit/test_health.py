from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from app.core.config import Environment, Settings
from app.main import create_app
from app.modules.health.checks import DatabaseCheck, RedisCheck, alembic_head_revision
from app.modules.health.dependencies import get_health_service
from app.modules.health.schemas import ComponentHealth, ComponentStatus, OverallStatus
from app.modules.health.service import HealthService

FIXED_NOW = datetime(2026, 11, 19, 12, 0, tzinfo=UTC)


class StubCheck:
    def __init__(self, name: str, status: ComponentStatus, *, critical: bool) -> None:
        self.name = name
        self.critical = critical
        self._status = status

    def run(self) -> ComponentHealth:
        return ComponentHealth(name=self.name, status=self._status, critical=self.critical)


def make_service(*checks: StubCheck) -> HealthService:
    return HealthService(checks, version="0.1.0", environment="test", clock=lambda: FIXED_NOW)


def test_ready_when_all_critical_checks_pass() -> None:
    service = make_service(
        StubCheck("database", ComponentStatus.OK, critical=True),
        StubCheck("redis", ComponentStatus.ERROR, critical=False),
    )
    result = service.readiness()
    assert result.status is OverallStatus.OK
    assert result.checked_at == FIXED_NOW


def test_unavailable_when_a_critical_check_fails() -> None:
    service = make_service(StubCheck("database", ComponentStatus.ERROR, critical=True))
    assert service.readiness().status is OverallStatus.UNAVAILABLE


def test_redis_check_reports_not_configured_without_url() -> None:
    assert RedisCheck(None).run().status is ComponentStatus.NOT_CONFIGURED


def test_redis_check_reports_unreachable_server() -> None:
    result = RedisCheck("redis://127.0.0.1:1/0").run()
    assert result.status is ComponentStatus.ERROR
    assert result.critical is False


def test_database_check_reports_unreachable_server() -> None:
    unreachable = create_engine(
        "postgresql+psycopg://x:x@127.0.0.1:1/x", connect_args={"connect_timeout": 1}
    )
    result = DatabaseCheck(unreachable, "0001_initial").run()
    assert result.status is ComponentStatus.ERROR
    assert "base de datos" in (result.detail or "")


def test_alembic_has_a_single_head() -> None:
    # get_current_head raises if migrations branch into several heads.
    assert alembic_head_revision() is not None


@pytest.fixture
def app() -> FastAPI:
    application = create_app(
        Settings(database_url="postgresql://u:p@127.0.0.1:1/db", log_json=False)
    )

    @application.get("/boom", include_in_schema=False)
    def boom() -> None:
        raise RuntimeError("unexpected")

    application.state.stub_service = make_service(
        StubCheck("database", ComponentStatus.OK, critical=True)
    )
    application.dependency_overrides[get_health_service] = lambda: application.state.stub_service
    return application


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def test_liveness_endpoint(client: TestClient) -> None:
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0"}


def test_readiness_endpoint_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["components"][0]["name"] == "database"


def test_readiness_endpoint_returns_503_when_unavailable(app: FastAPI, client: TestClient) -> None:
    app.state.stub_service = make_service(
        StubCheck("database", ComponentStatus.ERROR, critical=True)
    )
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 503
    assert response.json()["status"] == "unavailable"


def test_not_found_uses_problem_details(client: TestClient) -> None:
    response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["code"] == "not_found"


def test_unhandled_errors_do_not_leak_details(client: TestClient) -> None:
    response = client.get("/boom")
    assert response.status_code == 500
    body = response.json()
    assert body["code"] == "internal_error"
    assert "unexpected" not in body["detail"]


def test_openapi_and_swagger_are_exposed(client: TestClient) -> None:
    assert client.get("/api/v1/openapi.json").status_code == 200
    assert client.get("/api/v1/docs").status_code == 200


def test_openapi_and_swagger_are_hidden_in_production() -> None:
    settings = Settings(environment=Environment.PRODUCTION)
    with TestClient(create_app(settings)) as prod_client:
        for path in ("/api/v1/openapi.json", "/api/v1/docs", "/api/v1/redoc"):
            assert prod_client.get(path).status_code == 404, path
        assert prod_client.get("/api/v1/health/live").status_code == 200
