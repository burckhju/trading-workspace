from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.di import ApplicationContainer, get_container
from app.features.position_monitoring.api.dtos import (
    DynamicStopResponse,
    PositionAlertProjectionResponse,
    PositionAnalyticsResponse,
    PositionMonitoringHealthResponse,
    PositionPhaseResponse,
    PositionScoreResponse,
    ProductPositionValuationResponse,
    QuoteSourceAttemptResponse,
    StuttgartDelayedSourceHealthResponse,
)
from app.features.position_monitoring.service.alert_projection import (
    PositionAlertProjectionService,
)
from app.features.position_monitoring.service.dynamic_stop import DynamicStopService
from app.features.position_monitoring.service.health import PositionMonitoringHealthService
from app.features.position_monitoring.service.phase_engine import PositionPhaseService
from app.features.position_monitoring.service.position_analytics import (
    PositionAwareAnalyticsService,
)
from app.features.position_monitoring.service.product_valuation import (
    ProductPositionValuationService,
)
from app.features.position_monitoring.service.quote_runtime import build_warrant_quote_resolver
from app.features.position_monitoring.service.score_engine import PositionScoreService
from app.features.position_monitoring.service.source_diagnostics import (
    get_stuttgart_delayed_source_health,
)

router = APIRouter(prefix="/api/v1/position-monitoring", tags=["position-monitoring"])


def _health_service(container: ApplicationContainer) -> PositionMonitoringHealthService:
    return PositionMonitoringHealthService(
        database=container.database,
        market_data=container.eodhd.adapter if container.eodhd is not None else None,
        max_completed_price_age_days=(
            container.settings.position_monitoring.max_completed_price_age_days
        ),
    )


def _analytics_service(container: ApplicationContainer) -> PositionAwareAnalyticsService:
    return PositionAwareAnalyticsService(
        database=container.database,
        monitoring_health=_health_service(container),
    )


def _dynamic_stop_service(container: ApplicationContainer) -> DynamicStopService:
    analytics = _analytics_service(container)
    return DynamicStopService(
        database=container.database,
        position_analytics=analytics,
        phase_service=PositionPhaseService(
            database=container.database,
            position_analytics=analytics,
        ),
        score_service=PositionScoreService(
            database=container.database,
            position_analytics=analytics,
        ),
    )


@router.get(
    "/quote-sources/stuttgart-delayed/health",
    response_model=StuttgartDelayedSourceHealthResponse,
)
async def get_stuttgart_delayed_health(
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> StuttgartDelayedSourceHealthResponse:
    value = get_stuttgart_delayed_source_health(container.settings.market_data.stuttgart_delayed)
    return StuttgartDelayedSourceHealthResponse(
        status=value.status,
        reason=value.reason,
        enabled=value.enabled,
        source_mode=value.source_mode,
        schema_version=value.schema_version,
        local_directory=value.local_directory,
        latest_file=value.latest_file,
        latest_file_timestamp=value.latest_file_timestamp,
        file_count=value.file_count,
    )


@router.get(
    "/trades/{trade_id}/health",
    response_model=PositionMonitoringHealthResponse,
)
async def get_trade_monitoring_health(
    trade_id: UUID,
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> PositionMonitoringHealthResponse:
    """Return provider-neutral monitoring data health without mutating alert state."""

    value = await _health_service(container).for_trade(trade_id)
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
    "/trades/{trade_id}/analytics",
    response_model=PositionAnalyticsResponse,
)
async def get_trade_position_analytics(
    trade_id: UUID,
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> PositionAnalyticsResponse:
    """Return deterministic analysis-backed analytics projected into position context."""

    value = await _analytics_service(container).for_trade(trade_id)
    if value is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No open position is available for position analytics",
        )
    return PositionAnalyticsResponse(
        trade_id=value.trade_id,
        position_id=value.position_id,
        entry_executed_at=value.entry_executed_at,
        highest_high_since_entry=value.highest_high_since_entry,
        analysis_run_id=value.analysis_run_id,
        market_data_observed_at=value.market_data_observed_at,
        quality_status=value.quality_status,
        reason=value.reason,
        sessions_since_entry=value.sessions_since_entry,
    )


@router.get(
    "/trades/{trade_id}/phase",
    response_model=PositionPhaseResponse,
)
async def get_trade_position_phase(
    trade_id: UUID,
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> PositionPhaseResponse:
    """Return the deterministic read-only position phase projection."""

    service = PositionPhaseService(
        database=container.database,
        position_analytics=_analytics_service(container),
    )
    value = await service.for_trade(trade_id)
    if value is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No open position is available for phase classification",
        )
    return PositionPhaseResponse(
        trade_id=value.trade_id,
        position_id=value.position_id,
        phase=value.phase,
        quality_status=value.quality_status,
        reason=value.reason,
        policy_version=value.policy_version,
        analysis_run_id=value.analysis_run_id,
        sessions_since_entry=value.sessions_since_entry,
    )


@router.get(
    "/trades/{trade_id}/scores",
    response_model=PositionScoreResponse,
)
async def get_trade_position_scores(
    trade_id: UUID,
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> PositionScoreResponse:
    """Return deterministic explainable TrendScore and PeakScore projections."""

    service = PositionScoreService(
        database=container.database,
        position_analytics=_analytics_service(container),
    )
    value = await service.for_trade(trade_id)
    if value is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No open position is available for score projection",
        )
    return PositionScoreResponse(
        trade_id=value.trade_id,
        position_id=value.position_id,
        trend_score=value.trend_score,
        peak_score=value.peak_score,
        trend_components=value.trend_components,
        peak_components=value.peak_components,
        quality_status=value.quality_status,
        reason=value.reason,
        policy_version=value.policy_version,
        analysis_run_id=value.analysis_run_id,
        sessions_since_entry=value.sessions_since_entry,
    )


@router.get(
    "/trades/{trade_id}/dynamic-stop",
    response_model=DynamicStopResponse,
)
async def get_trade_dynamic_stop(
    trade_id: UUID,
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> DynamicStopResponse:
    """Return an indicative read-only dynamic stop projection."""

    value = await _dynamic_stop_service(container).for_trade(trade_id)
    if value is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No open position is available for dynamic stop projection",
        )
    return DynamicStopResponse(
        trade_id=value.trade_id,
        position_id=value.position_id,
        candidate_stop=value.candidate_stop,
        atr_multiple=value.atr_multiple,
        latest_price=value.latest_price,
        atr_14=value.atr_14,
        highest_high_since_entry=value.highest_high_since_entry,
        breached=value.breached,
        distance_to_stop=value.distance_to_stop,
        phase=value.phase,
        trend_score=value.trend_score,
        peak_score=value.peak_score,
        quality_status=value.quality_status,
        reason=value.reason,
        policy_version=value.policy_version,
        phase_policy_version=value.phase_policy_version,
        score_policy_version=value.score_policy_version,
        analysis_run_id=value.analysis_run_id,
    )


@router.get(
    "/trades/{trade_id}/alert-projection",
    response_model=PositionAlertProjectionResponse,
)
async def get_trade_alert_projection(
    trade_id: UUID,
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> PositionAlertProjectionResponse:
    """Return read-only operational attention without creating persisted alerts."""

    value = await PositionAlertProjectionService(
        dynamic_stop=_dynamic_stop_service(container)
    ).for_trade(trade_id)
    if value is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No open position is available for alert projection",
        )
    return PositionAlertProjectionResponse(
        trade_id=value.trade_id,
        position_id=value.position_id,
        alert_level=value.alert_level,
        attention_required=value.attention_required,
        quality_status=value.quality_status,
        reason=value.reason,
        candidate_stop=value.candidate_stop,
        latest_price=value.latest_price,
        phase=value.phase,
        policy_version=value.policy_version,
        dynamic_stop_policy_version=value.dynamic_stop_policy_version,
        analysis_run_id=value.analysis_run_id,
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
        quote_resolver=build_warrant_quote_resolver(container),
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
        quote_age_seconds=value.quote_age_seconds,
        max_quote_age_seconds=value.max_quote_age_seconds,
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
