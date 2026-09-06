from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.di import ApplicationContainer, get_container
from app.features.position_monitoring.api.dtos import (
    PositionMonitoringHealthResponse,
    ProductPositionValuationResponse,
)
from app.features.position_monitoring.service.health import PositionMonitoringHealthService
from app.features.position_monitoring.service.product_valuation import (
    ProductPositionValuationService,
)
from app.providers.eodhd.warrant_quote import EodhdWarrantQuoteAdapter

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
    "/trades/{trade_id}/product-valuation",
    response_model=ProductPositionValuationResponse,
)
async def get_trade_product_valuation(
    trade_id: UUID,
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> ProductPositionValuationResponse:
    """Return fail-closed held-product quote health and BID-based indicative valuation."""

    service = ProductPositionValuationService(
        database=container.database,
        quote_provider=EodhdWarrantQuoteAdapter(),
    )
    value = await service.for_trade(trade_id)
    if value is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No open position is available for product valuation",
        )
    return ProductPositionValuationResponse(
        trade_id=value.trade_id,
        position_id=value.position_id,
        status=value.status,
        reason=value.reason,
        warrant_listing_id=value.warrant_listing_id,
        symbol=value.symbol,
        bid=value.bid,
        ask=value.ask,
        currency=value.currency,
        quote_observed_at=value.quote_observed_at,
        market_value=value.market_value,
        unrealized_gross_pnl=value.unrealized_gross_pnl,
    )
