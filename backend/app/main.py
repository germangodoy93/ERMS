"""ERMS API entry point (application factory)."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Settings, get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.modules.audit.router import router as audit_router
from app.modules.auth.router import router as auth_router
from app.modules.health.router import router as health_router
from app.modules.roles.router import router as roles_router
from app.modules.users.router import router as users_router


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level, json_output=settings.log_json)

    app = FastAPI(
        title="ERMS API",
        summary=settings.app_name,
        version=settings.app_version,
        openapi_url=f"{settings.api_prefix}/openapi.json",
        docs_url=f"{settings.api_prefix}/docs",
        redoc_url=f"{settings.api_prefix}/redoc",
    )

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        )

    register_exception_handlers(app)
    for router in (health_router, auth_router, users_router, roles_router, audit_router):
        app.include_router(router, prefix=settings.api_prefix)
    return app


app = create_app()
