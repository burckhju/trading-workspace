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
from app.features.analysis.api import router as analysis_router
from app.features.candidate.api import router as candidate_router
from app.features.learning.api import router as learning_router
from app.features.market.api import reference_data_router, underlying_router
from app.features.market.api.reference_market_data_router import (
    router as reference_market_data_router,
)
from app.features.market.api.top_down_router import router as top_down_reference_router
from app.features.market_data.api import router as market_data_router
from app.features.model.api import router as model_governance_router
from app.features.post_trade.api import router as post_trade_router
from app.features.product.api import router as product_router
from app.features.product_selection.api import router as product_selection_router
from app.features.trade_plan.api import router as trade_plan_router
from app.features.trade_position.api import router as trade_position_router
from app.features.user_preferences.api.router import router as user_preferences_router

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
    application.include_router(underlying_router)
    application.include_router(reference_data_router)
    application.include_router(top_down_reference_router)
    application.include_router(reference_market_data_router)
    application.include_router(market_data_router)
    application.include_router(product_router)
    application.include_router(product_selection_router)
    application.include_router(analysis_router)
    application.include_router(candidate_router)
    application.include_router(trade_plan_router)
    application.include_router(trade_position_router)
    application.include_router(post_trade_router)
    application.include_router(learning_router)
    application.include_router(model_governance_router)
    application.include_router(user_preferences_router)

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
