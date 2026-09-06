from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel

from app.features.position_monitoring.service.health import MonitoringHealthStatus


class PositionMonitoringHealthResponse(BaseModel):
    trade_id: UUID
    position_id: UUID
    status: MonitoringHealthStatus
    reason: str
    symbol: str | None
    trading_date: date | None
    market_data_observed_at: datetime | None
    age_days: int | None
