from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.core.config.settings import StuttgartDelayedSourceMode
from app.features.market_data.domain.enums import MarketDataProvider
from app.features.position_monitoring.service.alert_projection import PositionAlertLevel
from app.features.position_monitoring.service.health import MonitoringHealthStatus
from app.features.position_monitoring.service.phase_engine import PositionPhase
from app.features.position_monitoring.service.position_analytics import (
    PositionAnalyticsStatus,
)
from app.features.position_monitoring.service.product_valuation import (
    ProductValuationStatus,
)
from app.features.position_monitoring.service.quote_sources import (
    QuoteSourceAttemptStatus,
)
from app.features.position_monitoring.service.source_diagnostics import (
    StuttgartDelayedSourceStatus,
)


class MonitoringBasisResponse(BaseModel):
    underlying_id: UUID
    name: str
    isin: str | None
    listing_id: UUID
    venue_mic: str
    currency: str


class MonitoringDailyPriceResponse(BaseModel):
    listing_id: UUID
    trading_date: date
    close: Decimal
    low: Decimal
    high: Decimal
    currency: str
    provider: MarketDataProvider
    provider_symbol: str
    source_updated_at: datetime | None
    retrieved_at: datetime


class MonitoringRuntimeStatusResponse(BaseModel):
    enabled: bool
    running: bool = False
    cycle_running: bool = False
    interval_seconds: int
    scope: Literal["PROCESS_LOCAL_ALL_WORKSPACES"] = "PROCESS_LOCAL_ALL_WORKSPACES"
    price_basis: Literal["EXPLICIT_INSTRUMENT_AND_CURRENCY"] = "EXPLICIT_INSTRUMENT_AND_CURRENCY"
    last_cycle_started_at: datetime | None = None
    last_cycle_completed_at: datetime | None = None
    next_run_at: datetime | None = None
    last_error: str | None = None
    last_error_at: datetime | None = None
    last_result: dict[str, int] | None = None
    last_rule_checks: tuple[dict[str, str | None], ...] = ()


class PositionMonitoringHealthResponse(BaseModel):
    trade_id: UUID
    position_id: UUID
    status: MonitoringHealthStatus
    reason: str
    symbol: str | None
    trading_date: date | None
    market_data_observed_at: datetime | None
    age_days: int | None
    basis: MonitoringBasisResponse | None = None
    daily_price: MonitoringDailyPriceResponse | None = None


class PositionAnalyticsResponse(BaseModel):
    trade_id: UUID
    position_id: UUID
    entry_executed_at: datetime | None
    highest_high_since_entry: Decimal | None
    analysis_run_id: UUID | None
    market_data_observed_at: datetime | None
    quality_status: PositionAnalyticsStatus
    reason: str
    sessions_since_entry: int | None


class PositionPhaseResponse(BaseModel):
    trade_id: UUID
    position_id: UUID
    phase: PositionPhase | None
    quality_status: PositionAnalyticsStatus
    reason: str
    policy_version: str
    analysis_run_id: UUID | None
    sessions_since_entry: int | None


class PositionScoreResponse(BaseModel):
    trade_id: UUID
    position_id: UUID
    trend_score: int | None
    peak_score: int | None
    trend_components: dict[str, int]
    peak_components: dict[str, int]
    quality_status: PositionAnalyticsStatus
    reason: str
    policy_version: str
    analysis_run_id: UUID | None
    sessions_since_entry: int | None


class DynamicStopResponse(BaseModel):
    trade_id: UUID
    position_id: UUID
    candidate_stop: Decimal | None
    atr_multiple: Decimal | None
    latest_price: Decimal | None
    atr_14: Decimal | None
    highest_high_since_entry: Decimal | None
    breached: bool | None
    distance_to_stop: Decimal | None
    phase: PositionPhase | None
    trend_score: int | None
    peak_score: int | None
    quality_status: PositionAnalyticsStatus
    reason: str
    policy_version: str
    phase_policy_version: str
    score_policy_version: str
    analysis_run_id: UUID | None


class PositionAlertProjectionResponse(BaseModel):
    trade_id: UUID
    position_id: UUID
    alert_level: PositionAlertLevel | None
    attention_required: bool
    quality_status: PositionAnalyticsStatus
    reason: str
    candidate_stop: Decimal | None
    latest_price: Decimal | None
    phase: PositionPhase | None
    policy_version: str
    dynamic_stop_policy_version: str
    analysis_run_id: UUID | None


class QuoteSourceAttemptResponse(BaseModel):
    source: str
    status: QuoteSourceAttemptStatus
    reason: str
    delayed: bool
    observed_at: datetime | None
    bid_available: bool
    ask_available: bool
    warrant_listing_id: UUID | None = None
    reference_price: Decimal | None = None
    reference_price_type: str | None = None
    currency: str | None = None
    refresh_error: str | None = None


class ProductPositionValuationResponse(BaseModel):
    trade_id: UUID
    position_id: UUID
    status: ProductValuationStatus
    reason: str
    warrant_listing_id: UUID | None
    provenance_listing_id: UUID | None = None
    quote_listing_id: UUID | None = None
    symbol: str | None
    bid: Decimal | None
    ask: Decimal | None
    currency: str | None
    quote_observed_at: datetime | None
    quote_age_seconds: int | None
    max_quote_age_seconds: int | None
    market_value: Decimal | None
    unrealized_gross_pnl: Decimal | None
    selected_source: str | None
    quote_provider: MarketDataProvider | None
    provider_identity: str | None
    provider_exchange_code: str | None
    isin: str | None
    wkn: str | None
    source_mode: str | None
    trading_status: str | None
    valuation_usable: bool
    execution_usable: bool
    analysis_usable: bool
    analysis_warning: str | None
    analysis_market_value: Decimal | None
    analysis_unrealized_gross_pnl: Decimal | None
    monitoring_usable: bool = False
    reference_price: Decimal | None = None
    reference_price_type: str | None = None
    quote_retrieved_at: datetime | None = None
    quote_refresh_error: str | None = None
    quote_assessed_at: datetime | None = None
    quote_delay_seconds: int | None = None
    quote_venue_mic: str | None = None
    quote_age_limit_exceeded: bool | None = None
    spread_absolute: Decimal | None = None
    spread_percent: Decimal | None = None
    freshness_policy: str | None
    source_attempts: tuple[QuoteSourceAttemptResponse, ...]


class StuttgartDelayedSourceHealthResponse(BaseModel):
    status: StuttgartDelayedSourceStatus
    reason: str
    enabled: bool
    source_mode: StuttgartDelayedSourceMode
    schema_version: str | None
    local_directory: str | None
    latest_file: str | None
    latest_file_timestamp: datetime | None
    file_count: int | None


class VontobelMarketsSourceHealthResponse(BaseModel):
    status: str
    reason: str
    enabled: bool
    base_url: str
    culture: str
