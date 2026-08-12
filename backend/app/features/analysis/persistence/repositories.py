"""SQLAlchemy repositories and read adapters for market analysis."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Select, and_, asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.analysis.persistence.models import (
    MarketAnalysisCriterionModel,
    MarketAnalysisEventModel,
    MarketAnalysisModel,
    MarketAnalysisRunModel,
    MarketAnalysisSnapshotRowModel,
)
from app.features.market.persistence.models import (
    ListingModel,
    TradingVenueModel,
    UnderlyingModel,
)
from app.features.market_data.domain.models import DailyPrice
from app.features.market_data.persistence.mapping import daily_price_to_domain
from app.features.market_data.persistence.models import DailyPriceModel


@dataclass(frozen=True)
class AnalysisOverviewRow:
    analysis: MarketAnalysisModel
    underlying_name: str
    ticker: str
    trading_venue_mic: str
    trading_venue_name: str
    currency_code: str
    latest_version: int | None
    latest_status: str | None
    latest_quality_status: str | None
    latest_analysis_time: datetime | None


@dataclass(frozen=True)
class AnalysisOverviewFilter:
    underlying_id: UUID | None = None
    status: str | None = None
    quality_status: str | None = None
    analysis_time_from: datetime | None = None
    analysis_time_to: datetime | None = None
    sort_by: str = "created_at"
    sort_direction: str = "desc"


class SqlAlchemyAnalysisReferenceReader:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def validate_reference(
        self, workspace_id: UUID, underlying_id: UUID, listing_id: UUID
    ) -> bool:
        statement = (
            select(ListingModel.id)
            .join(UnderlyingModel, UnderlyingModel.id == ListingModel.underlying_id)
            .where(
                ListingModel.id == listing_id,
                ListingModel.underlying_id == underlying_id,
                ListingModel.workspace_id == workspace_id,
                UnderlyingModel.workspace_id == workspace_id,
            )
        )
        return await self._session.scalar(statement) is not None


class SqlAlchemyAnalysisMarketDataReader:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_daily_prices(
        self, workspace_id: UUID, listing_id: UUID, start_date: date, end_date: date
    ) -> tuple[DailyPrice, ...]:
        rows = (
            await self._session.scalars(
                select(DailyPriceModel)
                .where(
                    DailyPriceModel.workspace_id == workspace_id,
                    DailyPriceModel.listing_id == listing_id,
                    DailyPriceModel.trading_date.between(start_date, end_date),
                )
                .order_by(DailyPriceModel.trading_date)
            )
        ).all()
        return tuple(daily_price_to_domain(row) for row in rows)


class SqlAlchemyAnalysisRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_analysis(self, model: MarketAnalysisModel) -> None:
        self._session.add(model)

    async def add_run(self, model: MarketAnalysisRunModel) -> None:
        self._session.add(model)

    async def add_snapshot_rows(
        self, models: list[MarketAnalysisSnapshotRowModel]
    ) -> None:
        self._session.add_all(models)

    async def add_criteria(self, models: list[MarketAnalysisCriterionModel]) -> None:
        self._session.add_all(models)

    async def add_event(self, model: MarketAnalysisEventModel) -> None:
        self._session.add(model)

    async def get_analysis(
        self, workspace_id: UUID, analysis_id: UUID
    ) -> MarketAnalysisModel | None:
        result = await self._session.scalars(
            select(MarketAnalysisModel).where(
                MarketAnalysisModel.workspace_id == workspace_id,
                MarketAnalysisModel.id == analysis_id,
            )
        )
        return result.first()

    async def next_version(self, analysis_id: UUID) -> int:
        value = await self._session.scalar(
            select(func.max(MarketAnalysisRunModel.version)).where(
                MarketAnalysisRunModel.analysis_id == analysis_id
            )
        )
        return int(value or 0) + 1

    async def get_run(
        self, analysis_id: UUID, version: int
    ) -> MarketAnalysisRunModel | None:
        result = await self._session.scalars(
            select(MarketAnalysisRunModel).where(
                MarketAnalysisRunModel.analysis_id == analysis_id,
                MarketAnalysisRunModel.version == version,
            )
        )
        return result.first()

    async def get_latest_run(self, analysis_id: UUID) -> MarketAnalysisRunModel | None:
        result = await self._session.scalars(
            select(MarketAnalysisRunModel)
            .where(MarketAnalysisRunModel.analysis_id == analysis_id)
            .order_by(MarketAnalysisRunModel.version.desc())
            .limit(1)
        )
        return result.first()

    async def list_events(
        self, analysis_id: UUID
    ) -> tuple[MarketAnalysisEventModel, ...]:
        return tuple(
            (
                await self._session.scalars(
                    select(MarketAnalysisEventModel)
                    .where(MarketAnalysisEventModel.analysis_id == analysis_id)
                    .order_by(
                        MarketAnalysisEventModel.occurred_at,
                        MarketAnalysisEventModel.id,
                    )
                )
            ).all()
        )

    async def get_supersede_event(
        self, analysis_id: UUID, version: int
    ) -> MarketAnalysisEventModel | None:
        result = await self._session.scalars(
            select(MarketAnalysisEventModel).where(
                MarketAnalysisEventModel.analysis_id == analysis_id,
                MarketAnalysisEventModel.version == version,
                MarketAnalysisEventModel.event_type == "SUPERSEDED",
            )
        )
        return result.first()

    async def list_analyses(
        self, workspace_id: UUID
    ) -> tuple[MarketAnalysisModel, ...]:
        return tuple(
            (
                await self._session.scalars(
                    select(MarketAnalysisModel)
                    .where(MarketAnalysisModel.workspace_id == workspace_id)
                    .order_by(MarketAnalysisModel.created_at.desc())
                )
            ).all()
        )

    def _overview_statement(
        self, workspace_id: UUID, filters: AnalysisOverviewFilter
    ) -> tuple[Select[Any], Select[Any]]:
        latest_versions = (
            select(
                MarketAnalysisRunModel.analysis_id.label("analysis_id"),
                func.max(MarketAnalysisRunModel.version).label("latest_version"),
            )
            .group_by(MarketAnalysisRunModel.analysis_id)
            .subquery()
        )
        latest_run = MarketAnalysisRunModel
        joins = (
            MarketAnalysisModel.__table__.join(
                UnderlyingModel, UnderlyingModel.id == MarketAnalysisModel.underlying_id
            )
            .join(ListingModel, ListingModel.id == MarketAnalysisModel.listing_id)
            .join(
                TradingVenueModel, TradingVenueModel.id == ListingModel.trading_venue_id
            )
            .outerjoin(
                latest_versions, latest_versions.c.analysis_id == MarketAnalysisModel.id
            )
            .outerjoin(
                latest_run,
                and_(
                    latest_run.analysis_id == MarketAnalysisModel.id,
                    latest_run.version == latest_versions.c.latest_version,
                ),
            )
        )
        predicates = [MarketAnalysisModel.workspace_id == workspace_id]
        if filters.underlying_id is not None:
            predicates.append(
                MarketAnalysisModel.underlying_id == filters.underlying_id
            )
        if filters.status is not None:
            predicates.append(latest_run.status == filters.status)
        if filters.quality_status is not None:
            predicates.append(latest_run.quality_status == filters.quality_status)
        if filters.analysis_time_from is not None:
            predicates.append(latest_run.analysis_time >= filters.analysis_time_from)
        if filters.analysis_time_to is not None:
            predicates.append(latest_run.analysis_time <= filters.analysis_time_to)

        sort_columns = {
            "created_at": MarketAnalysisModel.created_at,
            "underlying_name": UnderlyingModel.name,
            "latest_analysis_time": latest_run.analysis_time,
            "latest_status": latest_run.status,
            "latest_quality_status": latest_run.quality_status,
        }
        sort_column = sort_columns[filters.sort_by]
        ordering = (
            asc(sort_column) if filters.sort_direction == "asc" else desc(sort_column)
        )

        statement = (
            select(
                MarketAnalysisModel,
                UnderlyingModel.name,
                ListingModel.ticker,
                TradingVenueModel.mic,
                TradingVenueModel.name,
                ListingModel.currency_code,
                latest_run.version,
                latest_run.status,
                latest_run.quality_status,
                latest_run.analysis_time,
            )
            .select_from(joins)
            .where(*predicates)
            .order_by(ordering, MarketAnalysisModel.id)
        )
        count_statement = select(func.count()).select_from(joins).where(*predicates)
        return statement, count_statement

    async def list_analysis_overview(
        self,
        workspace_id: UUID,
        offset: int,
        limit: int,
        filters: AnalysisOverviewFilter,
    ) -> tuple[AnalysisOverviewRow, ...]:
        statement, _ = self._overview_statement(workspace_id, filters)
        rows = (
            await self._session.execute(statement.offset(offset).limit(limit))
        ).all()
        return tuple(AnalysisOverviewRow(*row) for row in rows)

    async def count_analysis_overview(
        self, workspace_id: UUID, filters: AnalysisOverviewFilter
    ) -> int:
        _, statement = self._overview_statement(workspace_id, filters)
        value = await self._session.scalar(statement)
        return int(value or 0)

    async def list_runs(self, analysis_id: UUID) -> tuple[MarketAnalysisRunModel, ...]:
        return tuple(
            (
                await self._session.scalars(
                    select(MarketAnalysisRunModel)
                    .where(MarketAnalysisRunModel.analysis_id == analysis_id)
                    .order_by(MarketAnalysisRunModel.version.desc())
                )
            ).all()
        )

    async def list_snapshot(
        self, run_id: UUID, offset: int = 0, limit: int | None = None
    ) -> tuple[MarketAnalysisSnapshotRowModel, ...]:
        statement = (
            select(MarketAnalysisSnapshotRowModel)
            .where(MarketAnalysisSnapshotRowModel.run_id == run_id)
            .order_by(MarketAnalysisSnapshotRowModel.trading_date)
            .offset(offset)
        )
        if limit is not None:
            statement = statement.limit(limit)
        return tuple((await self._session.scalars(statement)).all())

    async def count_snapshot(self, run_id: UUID) -> int:
        value = await self._session.scalar(
            select(func.count())
            .select_from(MarketAnalysisSnapshotRowModel)
            .where(MarketAnalysisSnapshotRowModel.run_id == run_id)
        )
        return int(value or 0)

    async def list_criteria(
        self, run_id: UUID
    ) -> tuple[MarketAnalysisCriterionModel, ...]:
        return tuple(
            (
                await self._session.scalars(
                    select(MarketAnalysisCriterionModel)
                    .where(MarketAnalysisCriterionModel.run_id == run_id)
                    .order_by(MarketAnalysisCriterionModel.code)
                )
            ).all()
        )
