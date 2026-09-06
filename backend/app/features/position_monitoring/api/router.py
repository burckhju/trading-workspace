from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.di import ApplicationContainer, get_container
from app.features.position_monitoring.api.dtos import (
    PositionMonitoringHealthResponse,
    PositionValuationResponse,
)
from app.features.position_monitoring.service.health import PositionMonitoringHealthService
from app.features.position_monitoring.service.valuation import PositionValuationService

router = APIRouter(prefix="/api/v1/position-monitoring", tags=["position-monitoring"])


@router.get(
    "/trades/{trade_id}/health",
    response_model=PositionMonitoringHealthResponse,
)
async def get_trade_monitoring_health(
    trade_id: UUID,
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> PositionMonitoringHealthResponse:
    """Return provider-neutral monitoring data health without mutating alert state."""

    service = PositionMonitoringHealthService(
        database=container.database,
        market_data=container.eodhd.adapter if container.eodhd is not None else None,
        max_completed_price_age_days=(
            container.settings.position_monitoring.max_completed_price_age_days
        ),
    )
    value = await service.for_trade(trade_id)
    if value is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No open position is available for monitoring",
        )
    return PositionMonitoringHealthResponse(
        trade_id=value.trade_id,
        position_id=value.position_id,
        status=value.status,
        reason=value.reason,
        symbol=value.symbol,
        trading_date=value.trading_date,
        market_data_observed_at=value.market_data_observed_at,
        age_days=value.age_days,
    )


@router.get(
    "/trades/{trade_id}/valuation",
    response_model=PositionValuationResponse,
)
async def get_trade_position_valuation(
    trade_id: UUID,
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> PositionValuationResponse:
    """Return indicative WarrantListing valuation without changing position state."""

    service = PositionValuationService(
        database=container.database,
        market_data=container.eodhd.adapter if container.eodhd is not None else None,
    )
    value = await service.for_trade(trade_id)
    if value is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No open position is available for valuation",
        )
    return PositionValuationResponse(
        trade_id=value.trade_id,
        position_id=value.position_id,
        status=value.status,
        reason=value.reason,
        warrant_listing_id=value.warrant_listing_id,
        bid=value.bid,
        ask=value.ask,
        currency=value.currency,
        observed_at=value.observed_at,
        mark_price=value.mark_price,
        mark_price_type=value.mark_price_type,
        market_value=value.market_value,
        unrealized_gross_pnl=value.unrealized_gross_pnl,
    )
