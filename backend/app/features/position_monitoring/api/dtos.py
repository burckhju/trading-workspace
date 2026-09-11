from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from app.core.config.settings import StuttgartDelayedSourceMode
from app.features.position_monitoring.service.health import MonitoringHealthStatus
from app.features.position_monitoring.service.phase_engine import PositionPhase
from app.features.position_monitoring.service.position_analytics import PositionAnalyticsStatus
from app.features.position_monitoring.service.product_valuation import ProductValuationStatus
from app.features.position_monitoring.service.quote_sources import QuoteSourceAttemptStatus
from app.features.position_monitoring.service.source_diagnostics import StuttgartDelayedSourceStatus


class PositionMonitoringHealthResponse(BaseModel):
    trade_id: UUID
    position_id: UUID
    status: MonitoringHealthStatus
    reason: str
    symbol: str | None
    trading_date: date | None
    market_data_observed_at: datetime | None
    age_days: int | None


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


class QuoteSourceAttemptResponse(BaseModel):
    source: str
    status: QuoteSourceAttemptStatus
    reason: str
    delayed: bool
    observed_at: datetime | None
    bid_available: bool
    ask_available: bool


class ProductPositionValuationResponse(BaseModel):
    trade_id: UUID
    position_id: UUID
    status: ProductValuationStatus
    reason: str
    warrant_listing_id: UUID | None
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
