"""Bounded, non-mutating market chart API; no provider is constructed here."""

from datetime import UTC, date, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_database_session
from app.features.analysis.domain.enums import PriceField
from app.features.analysis.domain.time_series import ChartComparison
from app.features.analysis.service.charts import ChartCatalog, ChartService
from app.features.market.persistence.chart_context import SqlAlchemyChartContextReader
from app.features.market.service.chart_contracts import UnderlyingChartContext
from app.features.market_data.persistence.time_series import SqlAlchemyTimeSeriesReader

router = APIRouter(prefix="/api/v1/market-charts", tags=["market-charts"])
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")


async def get_chart_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> ChartService:
    return ChartService(SqlAlchemyChartContextReader(session), SqlAlchemyTimeSeriesReader(session))


def _end(value: date | None) -> date:
    return value or datetime.now(UTC).date()


def _error(error: ValueError) -> HTTPException:
    return HTTPException(status_code=404 if "not found" in str(error) else 422, detail=str(error))


@router.get("/series", response_model=ChartComparison)
async def chart_series(
    response: Response,
    service: Annotated[ChartService, Depends(get_chart_service)],
    target: Annotated[list[str], Query(min_length=1, max_length=4)],
    start_date: date | None = None,
    end_date: date | None = None,
    price_field: PriceField = PriceField.CLOSE,
) -> ChartComparison:
    response.headers["Cache-Control"] = "private, max-age=30"
    try:
        return await service.series(
            WORKSPACE_ID, tuple(target), start_date, _end(end_date), price_field
        )
    except ValueError as error:
        raise _error(error) from error


@router.get("/catalog", response_model=ChartCatalog)
async def chart_catalog(
    service: Annotated[ChartService, Depends(get_chart_service)],
    as_of: date | None = None,
) -> ChartCatalog:
    try:
        return await service.catalog(WORKSPACE_ID, _end(as_of))
    except ValueError as error:
        raise _error(error) from error


@router.get("/underlyings/{underlying_id}", response_model=UnderlyingChartContext)
async def underlying_chart_context(
    underlying_id: UUID,
    service: Annotated[ChartService, Depends(get_chart_service)],
    as_of: date | None = None,
) -> UnderlyingChartContext:
    try:
        return await service.underlying(WORKSPACE_ID, underlying_id, _end(as_of))
    except ValueError as error:
        raise _error(error) from error
