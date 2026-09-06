from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from app.features.position_monitoring.service.health import MonitoringHealthStatus
from app.features.position_monitoring.service.product_valuation import ProductValuationStatus
from app.features.position_monitoring.service.quote_sources import QuoteSourceAttemptStatus


class PositionMonitoringHealthResponse(BaseModel):
    trade_id: UUID
    position_id: UUID
    status: MonitoringHealthStatus
    reason: str
    symbol: str | None
    trading_date: date | None
    market_data_observed_at: datetime | None
    age_days: int | None


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
    market_value: Decimal | None
    unrealized_gross_pnl: Decimal | None
    selected_source: str | None
    source_attempts: tuple[QuoteSourceAttemptResponse, ...]
