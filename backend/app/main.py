"""ERMS API entry point (application factory)."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Settings, get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.modules.assembly.router import order_router as assembly_order_router
from app.modules.assembly.router import router as assembly_router
from app.modules.audit.router import router as audit_router
from app.modules.auth.router import router as auth_router
from app.modules.customers.router import router as customers_router
from app.modules.devices.router import catalog_router, devices_router
from app.modules.diagnostics.router import agent_router as diagnostic_agent_router
from app.modules.diagnostics.router import router as diagnostics_router
from app.modules.health.router import router as health_router
from app.modules.inventory.router import router as inventory_router
from app.modules.notices.router import order_router as notices_order_router
from app.modules.notices.router import router as notices_router
from app.modules.organizations.router import router as organization_router
from app.modules.payments.router import router as payments_router
from app.modules.privacy.router import router as privacy_router
from app.modules.quotes.router import router as quotes_router
from app.modules.repairs.router import router as repairs_router
from app.modules.reports.router import router as reports_router
from app.modules.roles.router import router as roles_router
from app.modules.users.router import router as users_router
from app.modules.warranties.router import router as warranties_router
from app.modules.workorders.router import router as work_orders_router
from app.modules.workorders.router import terms_router as reception_terms_router


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level, json_output=settings.log_json)

    # The interactive docs and the schema are not published in production: they reveal the
    # whole attack surface. The contract lives in docs/api/openapi.json.
    expose_docs = not settings.is_production
    app = FastAPI(
        title="ERMS API",
        summary=settings.app_name,
        version=settings.app_version,
        openapi_url=f"{settings.api_prefix}/openapi.json" if expose_docs else None,
        docs_url=f"{settings.api_prefix}/docs" if expose_docs else None,
        redoc_url=f"{settings.api_prefix}/redoc" if expose_docs else None,
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
    for router in (
        health_router,
        auth_router,
        users_router,
        roles_router,
        audit_router,
        organization_router,
        privacy_router,
        customers_router,
        catalog_router,
        devices_router,
        reception_terms_router,
        work_orders_router,
        diagnostics_router,
        diagnostic_agent_router,
        inventory_router,
        quotes_router,
        repairs_router,
        payments_router,
        warranties_router,
        reports_router,
        assembly_router,
        assembly_order_router,
        notices_router,
        notices_order_router,
    ):
        app.include_router(router, prefix=settings.api_prefix)
    return app


app = create_app()
