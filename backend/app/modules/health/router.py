from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.core.config import Settings, get_settings
from app.modules.health.dependencies import get_health_service
from app.modules.health.schemas import LivenessResponse, OverallStatus, ReadinessResponse
from app.modules.health.service import HealthService

router = APIRouter(prefix="/health", tags=["health"])


@router.get(
    "/live",
    summary="Liveness: el proceso está en ejecución",
    response_model=LivenessResponse,
)
def liveness(settings: Annotated[Settings, Depends(get_settings)]) -> LivenessResponse:
    return LivenessResponse(version=settings.app_version)


@router.get(
    "/ready",
    summary="Readiness: dependencias disponibles y esquema migrado",
    response_model=ReadinessResponse,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ReadinessResponse,
            "description": "Un componente crítico no está disponible.",
        }
    },
)
def readiness(
    response: Response,
    service: Annotated[HealthService, Depends(get_health_service)],
) -> ReadinessResponse:
    result = service.readiness()
    if result.status is OverallStatus.UNAVAILABLE:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return result
