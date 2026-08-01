"""FastAPI application bootstrap and ASGI entry point."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, TypedDict

from fastapi import Depends, FastAPI, HTTPException, status

from app.core.config import Settings, get_settings
from app.core.di import ApplicationContainer, get_database_manager
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.database import DatabaseManager

logger = logging.getLogger(__name__)


class HealthResponse(TypedDict):
    """Contract of the technical liveness endpoint."""

    status: str


def create_application(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""

    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings.log_level)
    container = ApplicationContainer.build(resolved_settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        logger.info(
            "application_started",
            extra={"environment": resolved_settings.environment.value},
        )
        yield
        await container.close()
        logger.info("application_stopped")

    documentation_url = "/docs" if resolved_settings.documentation_enabled else None
    openapi_url = "/openapi.json" if resolved_settings.documentation_enabled else None

    application = FastAPI(
        title=resolved_settings.application_name,
        debug=resolved_settings.debug,
        docs_url=documentation_url,
        redoc_url=None,
        openapi_url=openapi_url,
        lifespan=lifespan,
    )
    application.state.container = container
    application.add_middleware(RequestContextMiddleware)
    register_exception_handlers(application)

    @application.get(
        "/health",
        response_model=None,
        include_in_schema=False,
        tags=["technical"],
    )
    async def health() -> HealthResponse:
        return {"status": "ok"}

    @application.get(
        "/health/ready",
        response_model=None,
        include_in_schema=False,
        tags=["technical"],
    )
    async def readiness(
        database: Annotated[
            DatabaseManager,
            Depends(get_database_manager),
        ],
    ) -> HealthResponse:
        try:
            await database.ping()
        except Exception as error:
            logger.warning("database_readiness_failed", exc_info=error)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database is unavailable",
            ) from error
        return {"status": "ready"}

    return application


app = create_application()
