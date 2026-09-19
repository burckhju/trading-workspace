"""A diagnostic GET never calls providers, schedules jobs, or changes mappings."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.core.di import ApplicationContainer, get_container
from app.features.market_data.persistence.position_quote_coverage import (
    PositionQuoteCoverageRepository,
)
from app.features.market_data.persistence.quote_coverage import QuoteCoverageRepository
from app.features.market_data.service.position_quote_coverage import (
    PositionQuoteCoverageReport,
    PositionQuoteCoverageService,
)
from app.features.market_data.service.quote_coverage import CoverageReport, QuoteCoverageService
from app.features.market_data.service.refresh import MarketDataRefreshRuntime
from app.features.position_monitoring.service.quote_runtime import build_warrant_quote_resolver

router = APIRouter()


def get_quote_coverage_service(
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> QuoteCoverageService:
    return QuoteCoverageService(
        QuoteCoverageRepository(container.database),
        build_warrant_quote_resolver(container).source_configuration(),
    )


def get_position_quote_coverage_service(
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> PositionQuoteCoverageService:
    product_coverage = get_quote_coverage_service(container)
    return PositionQuoteCoverageService(
        PositionQuoteCoverageRepository(container.database),
        product_coverage,
    )


@router.get("/warrants/quote-coverage", response_model=CoverageReport)
async def warrant_quote_coverage(
    request: Request,
    service: Annotated[QuoteCoverageService, Depends(get_quote_coverage_service)],
) -> CoverageReport:
    runtime: MarketDataRefreshRuntime = request.app.state.market_data_refresh
    return await service.report(runtime.workspace_id, runtime.status())


@router.get("/positions/quote-coverage", response_model=PositionQuoteCoverageReport)
async def position_quote_coverage(
    request: Request,
    service: Annotated[
        PositionQuoteCoverageService, Depends(get_position_quote_coverage_service)
    ],
) -> PositionQuoteCoverageReport:
    """Project persisted position source decisions from stored evidence only."""

    runtime: MarketDataRefreshRuntime = request.app.state.market_data_refresh
    return await service.report(runtime.workspace_id, runtime.status())
