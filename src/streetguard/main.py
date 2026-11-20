from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from streetguard.api.administration import (
    administration_router,
    authority_portal_router,
)
from streetguard.api.analytics import router as analytics_router
from streetguard.api.communications import (
    authority_router,
    notification_router,
    report_email_router,
)
from streetguard.api.detections import router as detection_router
from streetguard.api.geography import router as geography_router
from streetguard.api.health import router as health_router
from streetguard.api.locations import router as location_router
from streetguard.api.map import router as map_router
from streetguard.api.reports import router as report_router
from streetguard.config import get_settings
from streetguard.database import engine
from streetguard.logging import configure_logging


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    settings = get_settings()
    configure_logging(settings)
    structlog.get_logger().info("application_starting", environment=settings.app_env)
    yield
    await engine.dispose()
    structlog.get_logger().info("application_stopped")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url=None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_cors_origins,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
        allow_credentials=False,
    )
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(analytics_router, prefix="/api/v1")
    app.include_router(administration_router, prefix="/api/v1")
    app.include_router(authority_portal_router, prefix="/api/v1")
    app.include_router(authority_router, prefix="/api/v1")
    app.include_router(report_email_router, prefix="/api/v1")
    app.include_router(notification_router, prefix="/api/v1")
    app.include_router(detection_router, prefix="/api/v1")
    app.include_router(geography_router, prefix="/api/v1")
    app.include_router(location_router, prefix="/api/v1")
    app.include_router(map_router, prefix="/api/v1")
    app.include_router(report_router, prefix="/api/v1")
    return app


app = create_app()
