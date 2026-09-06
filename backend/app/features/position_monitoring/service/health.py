from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import select

from app.database import DatabaseManager
from app.features.market_data.domain.enums import QualityStatus
from app.features.market_data.service.contracts import LatestCompletedDailyPriceProvider
from app.features.market_data.service.types import LatestDailyPriceRequest
from app.features.position_monitoring.service.subjects import SqlAlchemyMonitoringSubjectReader
from app.features.trade_position.persistence.models import PositionModel


class MonitoringHealthStatus(StrEnum):
    OK = "OK"
    MISSING = "MISSING"
    STALE = "STALE"
    ERROR = "ERROR"


@dataclass(frozen=True, slots=True)
class PositionMonitoringHealth:
    trade_id: UUID
    position_id: UUID
    status: MonitoringHealthStatus
    reason: str
    symbol: str | None = None
    trading_date: date | None = None
    market_data_observed_at: datetime | None = None
    age_days: int | None = None


class PositionMonitoringHealthService:
    """Read current monitoring data health without creating alerts or changing rule state."""

    def __init__(
        self,
        *,
        database: DatabaseManager,
        market_data: LatestCompletedDailyPriceProvider | None,
        max_completed_price_age_days: int,
        now: callable = lambda: datetime.now(UTC),
    ) -> None:
        if max_completed_price_age_days < 0:
            raise ValueError("max_completed_price_age_days must not be negative")
        self._database = database
        self._market_data = market_data
        self._max_age_days = max_completed_price_age_days
        self._now = now

    async def for_trade(self, trade_id: UUID) -> PositionMonitoringHealth | None:
        async with self._database.session_context() as session:
            position = await session.scalar(
                select(PositionModel).where(
                    PositionModel.trade_id == trade_id,
                    PositionModel.open_quantity > 0,
                    PositionModel.closed_at.is_(None),
                )
            )
            if position is None:
                return None

            reader = SqlAlchemyMonitoringSubjectReader(session)
            resolutions = await reader.list_resolutions()
            resolution = next(
                (item for item in resolutions if item.position_id == position.id),
                None,
            )
            if resolution is None:
                return PositionMonitoringHealth(
                    trade_id=trade_id,
                    position_id=position.id,
                    status=MonitoringHealthStatus.ERROR,
                    reason="MONITORING_SUBJECT_NOT_RESOLVED",
                )
            if resolution.subject is None:
                return PositionMonitoringHealth(
                    trade_id=trade_id,
                    position_id=position.id,
                    status=MonitoringHealthStatus.ERROR,
                    reason=(
                        resolution.issue.value
                        if resolution.issue is not None
                        else "MONITORING_SUBJECT_NOT_RESOLVED"
                    ),
                )

            subject = resolution.subject
            if self._market_data is None:
                return PositionMonitoringHealth(
                    trade_id=trade_id,
                    position_id=position.id,
                    status=MonitoringHealthStatus.ERROR,
                    reason="MARKET_DATA_PROVIDER_UNAVAILABLE",
                    symbol=subject.symbol,
                )

            now = self._now()
            try:
                result = await self._market_data.get_latest_completed_daily_price(
                    LatestDailyPriceRequest(
                        workspace_id=subject.workspace_id,
                        listing_id=subject.listing_id,
                        mapping_id=subject.mapping_id,
                        correlation_id=uuid4(),
                        as_of_date=now.date(),
                    )
                )
            except Exception:
                return PositionMonitoringHealth(
                    trade_id=trade_id,
                    position_id=position.id,
                    status=MonitoringHealthStatus.ERROR,
                    reason="MARKET_DATA_REQUEST_FAILED",
                    symbol=subject.symbol,
                )

            price = result.data
            if price is None:
                return PositionMonitoringHealth(
                    trade_id=trade_id,
                    position_id=position.id,
                    status=MonitoringHealthStatus.MISSING,
                    reason="NO_COMPLETED_DAILY_PRICE",
                    symbol=subject.symbol,
                )
            if result.quality_status is not QualityStatus.VALID:
                return PositionMonitoringHealth(
                    trade_id=trade_id,
                    position_id=position.id,
                    status=MonitoringHealthStatus.ERROR,
                    reason=f"MARKET_DATA_QUALITY_{result.quality_status.value}",
                    symbol=subject.symbol,
                    trading_date=price.trading_date,
                    market_data_observed_at=price.source_updated_at or price.retrieved_at,
                )

            age_days = (now.date() - price.trading_date).days
            observed_at = price.source_updated_at or price.retrieved_at
            if age_days > self._max_age_days:
                return PositionMonitoringHealth(
                    trade_id=trade_id,
                    position_id=position.id,
                    status=MonitoringHealthStatus.STALE,
                    reason="COMPLETED_DAILY_PRICE_STALE",
                    symbol=subject.symbol,
                    trading_date=price.trading_date,
                    market_data_observed_at=observed_at,
                    age_days=age_days,
                )

            return PositionMonitoringHealth(
                trade_id=trade_id,
                position_id=position.id,
                status=MonitoringHealthStatus.OK,
                reason="COMPLETED_DAILY_PRICE_CURRENT",
                symbol=subject.symbol,
                trading_date=price.trading_date,
                market_data_observed_at=observed_at,
                age_days=age_days,
            )
