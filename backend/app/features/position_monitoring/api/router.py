from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.di import ApplicationContainer, get_container
from app.features.position_monitoring.api.dtos import (
    PositionMonitoringHealthResponse,
    ProductPositionValuationResponse,
    QuoteSourceAttemptResponse,
)
from app.features.position_monitoring.service.health import PositionMonitoringHealthService
from app.features.position_monitoring.service.product_valuation import (
    ProductPositionValuationService,
)
from app.features.position_monitoring.service.quote_sources import (
    MultiSourceWarrantQuoteResolver,
    NamedWarrantQuoteSource,
)
from app.providers.eodhd.warrant_quote import EodhdWarrantQuoteAdapter
from app.providers.stuttgart_delayed import StuttgartDelayedWarrantQuoteAdapter

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


def _warrant_quote_resolver(container: ApplicationContainer) -> MultiSourceWarrantQuoteResolver:
    stuttgart_settings = container.settings.market_data.stuttgart_delayed
    stuttgart_provider = (
        StuttgartDelayedWarrantQuoteAdapter(
            database=container.database,
            settings=stuttgart_settings,
        )
        if stuttgart_settings.enabled and stuttgart_settings.has_verified_schema
        else None
    )
    stuttgart_reason = (
        "STUTTGART_DELAYED_DISABLED"
        if not stuttgart_settings.enabled
        else "STUTTGART_DELAYED_SCHEMA_NOT_VERIFIED"
    )
    return MultiSourceWarrantQuoteResolver(
        (
            NamedWarrantQuoteSource("EODHD", EodhdWarrantQuoteAdapter()),
            NamedWarrantQuoteSource(
                "BOERSE_STUTTGART_DELAYED",
                stuttgart_provider,
                delayed=True,
                unavailable_reason=stuttgart_reason,
            ),
            NamedWarrantQuoteSource(
                "GETTEX_DELAYED",
                None,
                delayed=True,
                unavailable_reason=(
                    "Official MUND/MUNC delayed pre-trade source is reserved but not enabled until "
                    "payload schema, usage terms, and listing identity are verified"
                ),
            ),
        )
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
        quote_resolver=_warrant_quote_resolver(container),
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
        selected_source=value.selected_source,
        source_attempts=tuple(
            QuoteSourceAttemptResponse(
                source=attempt.source,
                status=attempt.status,
                reason=attempt.reason,
                delayed=attempt.delayed,
                observed_at=attempt.observed_at,
                bid_available=attempt.bid_available,
                ask_available=attempt.ask_available,
            )
            for attempt in value.source_attempts
        ),
    )
