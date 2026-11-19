from collections.abc import Callable, Sequence
from datetime import UTC, datetime

from app.modules.health.checks import HealthCheck
from app.modules.health.schemas import (
    ComponentStatus,
    OverallStatus,
    ReadinessResponse,
)


class HealthService:
    def __init__(
        self,
        checks: Sequence[HealthCheck],
        *,
        version: str,
        environment: str,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._checks = checks
        self._version = version
        self._environment = environment
        self._clock = clock

    def readiness(self) -> ReadinessResponse:
        components = [check.run() for check in self._checks]
        ready = all(c.status is not ComponentStatus.ERROR for c in components if c.critical)
        return ReadinessResponse(
            status=OverallStatus.OK if ready else OverallStatus.UNAVAILABLE,
            version=self._version,
            environment=self._environment,
            checked_at=self._clock(),
            components=components,
        )
