from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import exists, select

from app.database import DatabaseManager
from app.features.market.persistence.models import ListingModel, TradingVenueModel, UnderlyingModel
from app.features.market_data.domain.enums import QualityStatus
from app.features.market_data.domain.models import DailyPrice
from app.features.market_data.service.contracts import LatestCompletedDailyPriceProvider
from app.features.market_data.service.types import LatestDailyPriceRequest
from app.features.position_monitoring.service.subjects import SqlAlchemyMonitoringSubjectReader
from app.features.trade_position.persistence.models import PositionModel, TradeModel


class MonitoringHealthStatus(StrEnum):
    OK = "OK"
    MISSING = "MISSING"
    STALE = "STALE"
    ERROR = "ERROR"


@dataclass(frozen=True, slots=True)
class MonitoringBasis:
    underlying_id: UUID
    name: str
    isin: str | None
    listing_id: UUID
    venue_mic: str
    currency: str


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
    basis: MonitoringBasis | None = None
    daily_price: DailyPrice | None = None


class PositionMonitoringHealthService:
    """Read current monitoring data health without creating alerts or changing rule state."""

    def __init__(
        self,
        *,
        database: DatabaseManager,
        market_data: LatestCompletedDailyPriceProvider | None,
        max_completed_price_age_days: int,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
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
                    ~exists(
                        select(1).where(
                            TradeModel.id == PositionModel.trade_id,
                            TradeModel.cancelled_at.is_not(None),
                        )
                    ),
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
            basis_row = (
                await session.execute(
                    select(ListingModel, UnderlyingModel, TradingVenueModel)
                    .join(UnderlyingModel, UnderlyingModel.id == ListingModel.underlying_id)
                    .join(TradingVenueModel, TradingVenueModel.id == ListingModel.trading_venue_id)
                    .where(
                        ListingModel.id == subject.listing_id,
                        ListingModel.workspace_id == subject.workspace_id,
                        UnderlyingModel.workspace_id == subject.workspace_id,
                    )
                )
            ).first()
            basis = None
            if basis_row is not None:
                listing, underlying, venue = basis_row
                basis = MonitoringBasis(
                    underlying.id,
                    underlying.name,
                    underlying.isin,
                    listing.id,
                    venue.mic,
                    listing.currency_code,
                )
            base = PositionMonitoringHealth(
                trade_id=trade_id,
                position_id=position.id,
                status=MonitoringHealthStatus.ERROR,
                reason="MARKET_DATA_PROVIDER_UNAVAILABLE",
                symbol=subject.symbol,
                basis=basis,
            )
            if self._market_data is None:
                return base

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
                return replace(base, reason="MARKET_DATA_REQUEST_FAILED")

            price = result.data
            if price is None:
                return replace(
                    base,
                    status=MonitoringHealthStatus.MISSING,
                    reason="NO_COMPLETED_DAILY_PRICE",
                )
            if price.listing_id != subject.listing_id or (
                basis is not None and price.currency != basis.currency
            ):
                return replace(base, reason="MARKET_DATA_IDENTITY_MISMATCH")
            if price.trading_date > now.date():
                return replace(base, reason="DAILY_PRICE_IN_FUTURE")
            quality = result.quality_status
            if quality is QualityStatus.VALID:
                quality = price.quality_status
            if quality is not QualityStatus.VALID:
                return replace(
                    base,
                    reason=f"MARKET_DATA_QUALITY_{quality.value}",
                    trading_date=price.trading_date,
                    market_data_observed_at=price.source_updated_at or price.retrieved_at,
                )

            age_days = (now.date() - price.trading_date).days
            observed_at = price.source_updated_at or price.retrieved_at
            base = replace(
                base,
                trading_date=price.trading_date,
                market_data_observed_at=observed_at,
                age_days=age_days,
                daily_price=price,
            )
            if age_days > self._max_age_days:
                return replace(
                    base,
                    status=MonitoringHealthStatus.STALE,
                    reason="COMPLETED_DAILY_PRICE_STALE",
                )

            return replace(
                base,
                status=MonitoringHealthStatus.OK,
                reason="COMPLETED_DAILY_PRICE_CURRENT",
            )
