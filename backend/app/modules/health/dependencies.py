from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.core.config import Settings, get_settings
from app.core.database import get_engine
from app.core.storage import get_storage
from app.modules.health.checks import (
    DatabaseCheck,
    RedisCheck,
    StorageCheck,
    alembic_head_revision,
)
from app.modules.health.service import HealthService


@lru_cache
def _expected_revision() -> str | None:
    return alembic_head_revision()


def get_health_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> HealthService:
    return HealthService(
        checks=[
            DatabaseCheck(get_engine(), _expected_revision()),
            RedisCheck(settings.redis_url),
            StorageCheck(get_storage()),
        ],
        version=settings.app_version,
        environment=settings.environment.value,
    )
