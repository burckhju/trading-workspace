from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import exists, select

from app.database import DatabaseManager
from app.features.analysis.domain.enums import AnalysisQualityStatus, AnalysisStatus
from app.features.analysis.persistence.models import (
    MarketAnalysisModel,
    MarketAnalysisRunModel,
    MarketAnalysisSnapshotRowModel,
)
from app.features.market.persistence.models import ListingModel
from app.features.position_monitoring.service.health import PositionMonitoringHealthService
from app.features.product.persistence.models import WarrantModel
from app.features.trade_position.persistence.models import (
    ExecutionRecordModel,
    PositionModel,
    TradeModel,
)


class PositionAnalyticsStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    INSUFFICIENT = "INSUFFICIENT"
    MISSING = "MISSING"
    STALE = "STALE"
    ERROR = "ERROR"


@dataclass(frozen=True, slots=True)
class PositionAnalytics:
    trade_id: UUID
    position_id: UUID
    entry_executed_at: datetime | None
    highest_high_since_entry: Decimal | None
    analysis_run_id: UUID | None
    market_data_observed_at: datetime | None
    quality_status: PositionAnalyticsStatus
    reason: str
    sessions_since_entry: int | None = None


def highest_high_since_entry(
    *,
    entry_executed_at: datetime,
    evaluation_time: datetime,
    rows: tuple[MarketAnalysisSnapshotRowModel, ...],
    entry_on: date | None = None,
) -> tuple[Decimal | None, int]:
    """Project the peak from completed daily snapshot rows without look-ahead.

    Daily rows carry a trading date, not a session-close timestamp. V1 therefore
    uses the conservative rule that the entry trading date and evaluation date
    are excluded. Only sessions strictly after the entry date and strictly
    before the evaluation date are eligible. This prevents an intraday entry
    from inheriting a pre-entry high and prevents an evaluation-day candle from
    being treated as completed without an explicit close timestamp.
    """
    if entry_executed_at.tzinfo is None or evaluation_time.tzinfo is None:
        raise ValueError("entry and evaluation timestamps must be timezone-aware")
    entry_date = entry_on or entry_executed_at.astimezone(UTC).date()
    evaluation_date = evaluation_time.astimezone(UTC).date()
    eligible = tuple(row for row in rows if entry_date < row.trading_date < evaluation_date)
    if not eligible:
        return None, 0
    return max(row.high for row in eligible), len(eligible)


class PositionAwareAnalyticsService:
    """Computed position projection over execution truth and analysis snapshots."""

    def __init__(
        self,
        *,
        database: DatabaseManager,
        monitoring_health: PositionMonitoringHealthService,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._database = database
        self._monitoring_health = monitoring_health
        self._now = now

    async def for_trade(self, trade_id: UUID) -> PositionAnalytics | None:
        evaluation_time = self._now()
        async with self._database.session_context() as session:
            row = (
                await session.execute(
                    select(PositionModel, TradeModel, WarrantModel)
                    .join(TradeModel, TradeModel.id == PositionModel.trade_id)
                    .join(WarrantModel, WarrantModel.id == TradeModel.product_id)
                    .where(
                        TradeModel.id == trade_id,
                        TradeModel.cancelled_at.is_(None),
                        PositionModel.open_quantity > 0,
                        PositionModel.closed_at.is_(None),
                    )
                )
            ).first()
            if row is None:
                return None
            position, trade, warrant = row

            replacement = ExecutionRecordModel.__table__.alias("replacement")
            entry = await session.scalar(
                select(ExecutionRecordModel)
                .where(
                    ExecutionRecordModel.trade_id == trade.id,
                    ExecutionRecordModel.side == "BUY",
                    ~exists(
                        select(1)
                        .select_from(replacement)
                        .where(replacement.c.supersedes_execution_id == ExecutionRecordModel.id)
                    ),
                )
                .order_by(
                    ExecutionRecordModel.executed_at,
                    ExecutionRecordModel.recorded_at,
                    ExecutionRecordModel.id,
                )
                .limit(1)
            )
            if entry is None:
                return PositionAnalytics(
                    trade_id=trade.id,
                    position_id=position.id,
                    entry_executed_at=None,
                    highest_high_since_entry=None,
                    analysis_run_id=None,
                    market_data_observed_at=None,
                    quality_status=PositionAnalyticsStatus.ERROR,
                    reason="INVALID_POSITION_PROVENANCE_NO_BUY_EXECUTION",
                )

            listing_id = await session.scalar(
                select(ListingModel.id).where(
                    ListingModel.workspace_id == trade.workspace_id,
                    ListingModel.underlying_id == warrant.underlying_id,
                    ListingModel.is_primary.is_(True),
                )
            )
            if listing_id is None:
                return self._unavailable(
                    trade.id,
                    position.id,
                    entry.executed_at,
                    PositionAnalyticsStatus.MISSING,
                    "NO_PRIMARY_LISTING",
                )

            analysis = await session.scalar(
                select(MarketAnalysisModel)
                .where(
                    MarketAnalysisModel.workspace_id == trade.workspace_id,
                    MarketAnalysisModel.listing_id == listing_id,
                )
                .order_by(MarketAnalysisModel.created_at.desc())
                .limit(1)
            )
            if analysis is None:
                return self._unavailable(
                    trade.id,
                    position.id,
                    entry.executed_at,
                    PositionAnalyticsStatus.MISSING,
                    "NO_FT006_ANALYSIS",
                )

            eligible_statuses = (
                AnalysisStatus.COMPLETED.value,
                AnalysisStatus.COMPLETED_WITH_WARNINGS.value,
                AnalysisStatus.NOT_EVALUABLE.value,
            )
            run = await session.scalar(
                select(MarketAnalysisRunModel)
                .where(
                    MarketAnalysisRunModel.analysis_id == analysis.id,
                    MarketAnalysisRunModel.status.in_(eligible_statuses),
                )
                .order_by(MarketAnalysisRunModel.version.desc())
                .limit(1)
            )
            if run is None:
                return self._unavailable(
                    trade.id,
                    position.id,
                    entry.executed_at,
                    PositionAnalyticsStatus.MISSING,
                    "NO_TERMINAL_FT006_RUN",
                )
            if run.quality_status == AnalysisQualityStatus.INSUFFICIENT.value:
                return PositionAnalytics(
                    trade_id=trade.id,
                    position_id=position.id,
                    entry_executed_at=entry.executed_at,
                    highest_high_since_entry=None,
                    analysis_run_id=run.id,
                    market_data_observed_at=run.analysis_time,
                    quality_status=PositionAnalyticsStatus.INSUFFICIENT,
                    reason="FT006_HISTORY_INSUFFICIENT",
                )

            snapshot_rows = tuple(
                (
                    await session.scalars(
                        select(MarketAnalysisSnapshotRowModel)
                        .where(MarketAnalysisSnapshotRowModel.run_id == run.id)
                        .order_by(MarketAnalysisSnapshotRowModel.trading_date)
                    )
                ).all()
            )
            peak, sessions = highest_high_since_entry(
                entry_executed_at=entry.executed_at,
                evaluation_time=evaluation_time,
                rows=snapshot_rows,
                entry_on=entry.executed_on,
            )
            if peak is None:
                return PositionAnalytics(
                    trade_id=trade.id,
                    position_id=position.id,
                    entry_executed_at=entry.executed_at,
                    highest_high_since_entry=None,
                    analysis_run_id=run.id,
                    market_data_observed_at=run.analysis_time,
                    quality_status=PositionAnalyticsStatus.INSUFFICIENT,
                    reason="NO_COMPLETED_SESSION_SINCE_ENTRY",
                    sessions_since_entry=0,
                )

        health = await self._monitoring_health.for_trade(trade_id)
        if health is None:
            return None
        if health.status.value == "STALE":
            status = PositionAnalyticsStatus.STALE
            reason = health.reason
            peak = None
        elif health.status.value != "OK":
            status = (
                PositionAnalyticsStatus.MISSING
                if health.status.value == "MISSING"
                else PositionAnalyticsStatus.ERROR
            )
            reason = health.reason
            peak = None
        else:
            status = PositionAnalyticsStatus.AVAILABLE
            reason = "POSITION_ANALYTICS_AVAILABLE"

        return PositionAnalytics(
            trade_id=trade.id,
            position_id=position.id,
            entry_executed_at=entry.executed_at,
            highest_high_since_entry=peak,
            analysis_run_id=run.id,
            market_data_observed_at=health.market_data_observed_at or run.analysis_time,
            quality_status=status,
            reason=reason,
            sessions_since_entry=sessions,
        )

    @staticmethod
    def _unavailable(
        trade_id: UUID,
        position_id: UUID,
        entry_executed_at: datetime,
        status: PositionAnalyticsStatus,
        reason: str,
    ) -> PositionAnalytics:
        return PositionAnalytics(
            trade_id=trade_id,
            position_id=position_id,
            entry_executed_at=entry_executed_at,
            highest_high_since_entry=None,
            analysis_run_id=None,
            market_data_observed_at=None,
            quality_status=status,
            reason=reason,
        )
