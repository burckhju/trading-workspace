from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from app.features.position_monitoring.service.health import MonitoringHealthStatus
from app.features.position_monitoring.service.valuation import PositionValuationStatus


class PositionMonitoringHealthResponse(BaseModel):
    trade_id: UUID
    position_id: UUID
    status: MonitoringHealthStatus
    reason: str
    symbol: str | None
    trading_date: date | None
    market_data_observed_at: datetime | None
    age_days: int | None


class PositionValuationResponse(BaseModel):
    trade_id: UUID
    position_id: UUID
    status: PositionValuationStatus
    reason: str
    warrant_listing_id: UUID | None
    bid: Decimal | None
    ask: Decimal | None
    currency: str | None
    observed_at: datetime | None
    mark_price: Decimal | None
    mark_price_type: str | None
    market_value: Decimal | None
    unrealized_gross_pnl: Decimal | None
