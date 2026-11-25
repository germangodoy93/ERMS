"""Individual readiness checks.

Each check implements the `HealthCheck` protocol, so new infrastructure (object
storage, Celery workers) is added by writing a new check, not by editing the service.
"""

import logging
import time
from pathlib import Path
from typing import Protocol

from alembic.config import Config
from alembic.script import ScriptDirectory
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.core.storage import S3Storage, Storage, StorageError
from app.modules.health.schemas import ComponentHealth, ComponentStatus

logger = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).resolve().parents[3]


class HealthCheck(Protocol):
    name: str
    critical: bool

    def run(self) -> ComponentHealth: ...


def _elapsed_ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 2)


def alembic_head_revision(alembic_ini: Path = BACKEND_ROOT / "alembic.ini") -> str | None:
    config = Config(str(alembic_ini))
    config.set_main_option("script_location", str(alembic_ini.parent / "alembic"))
    return ScriptDirectory.from_config(config).get_current_head()


class DatabaseCheck:
    """Verifies connectivity and that the schema is migrated to the latest revision."""

    name = "database"
    critical = True

    def __init__(self, engine: Engine, expected_revision: str | None) -> None:
        self._engine = engine
        self._expected_revision = expected_revision

    def run(self) -> ComponentHealth:
        start = time.perf_counter()
        try:
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                current = conn.execute(
                    text("SELECT version_num FROM alembic_version")
                ).scalar_one_or_none()
        except SQLAlchemyError as exc:
            logger.warning("Database health check failed", extra={"error": type(exc).__name__})
            return ComponentHealth(
                name=self.name,
                status=ComponentStatus.ERROR,
                critical=self.critical,
                latency_ms=_elapsed_ms(start),
                detail="No fue posible consultar la base de datos o no tiene migraciones.",
            )

        latency = _elapsed_ms(start)
        if current != self._expected_revision:
            return ComponentHealth(
                name=self.name,
                status=ComponentStatus.ERROR,
                critical=self.critical,
                latency_ms=latency,
                detail=(
                    f"Migración pendiente: actual={current}, esperada={self._expected_revision}"
                ),
            )
        return ComponentHealth(
            name=self.name,
            status=ComponentStatus.OK,
            critical=self.critical,
            latency_ms=latency,
            detail=f"PostgreSQL disponible, migración {current} (head)",
        )


class RedisCheck:
    """Redis is not critical until Celery tasks are introduced (Sprint 3)."""

    name = "redis"
    critical = False

    def __init__(self, redis_url: str | None) -> None:
        self._redis_url = redis_url

    def run(self) -> ComponentHealth:
        if not self._redis_url:
            return ComponentHealth(
                name=self.name,
                status=ComponentStatus.NOT_CONFIGURED,
                critical=self.critical,
                detail="REDIS_URL no está configurado.",
            )
        start = time.perf_counter()
        try:
            client = Redis.from_url(self._redis_url, socket_connect_timeout=2, socket_timeout=2)
            try:
                client.ping()
            finally:
                client.close()
        except RedisError as exc:
            logger.warning("Redis health check failed", extra={"error": type(exc).__name__})
            return ComponentHealth(
                name=self.name,
                status=ComponentStatus.ERROR,
                critical=self.critical,
                latency_ms=_elapsed_ms(start),
                detail="No fue posible conectar con Redis.",
            )
        return ComponentHealth(
            name=self.name,
            status=ComponentStatus.OK,
            critical=self.critical,
            latency_ms=_elapsed_ms(start),
            detail="Redis disponible",
        )


class StorageCheck:
    """File storage for photos. Not critical: the rest of the workshop keeps working."""

    name = "storage"
    critical = False

    def __init__(self, storage: Storage) -> None:
        self._storage = storage

    def run(self) -> ComponentHealth:
        if not isinstance(self._storage, S3Storage):
            return ComponentHealth(
                name=self.name,
                status=ComponentStatus.NOT_CONFIGURED,
                critical=self.critical,
                detail="Fotos en modo demostración (disco del servidor; S3_* no configurado).",
            )
        start = time.perf_counter()
        try:
            self._storage.ping()
        except StorageError:
            logger.warning("Storage health check failed")
            return ComponentHealth(
                name=self.name,
                status=ComponentStatus.ERROR,
                critical=self.critical,
                latency_ms=_elapsed_ms(start),
                detail="No fue posible conectar con el bucket de fotos.",
            )
        return ComponentHealth(
            name=self.name,
            status=ComponentStatus.OK,
            critical=self.critical,
            latency_ms=_elapsed_ms(start),
            detail="Bucket de fotos disponible",
        )
