"""Bounded SELECT-only adapter for the public EOD time-series contract."""

from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.market_data.domain.enums import PriceType
from app.features.market_data.persistence.models import DailyPriceModel
from app.features.market_data.service.time_series import (
    MAX_SERIES_POINTS,
    SeriesCoverage,
    SeriesObservation,
)


class SqlAlchemyTimeSeriesReader:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def observations(
        self, workspace_id: UUID, instrument_id: UUID, start: date, end: date
    ) -> tuple[SeriesObservation, ...]:
        rows = await self._session.scalars(
            select(DailyPriceModel)
            .where(
                DailyPriceModel.workspace_id == workspace_id,
                DailyPriceModel.market_data_instrument_id == instrument_id,
                DailyPriceModel.price_type == PriceType.EOD,
                DailyPriceModel.trading_date.between(start, end),
            )
            .order_by(DailyPriceModel.trading_date)
            .limit(MAX_SERIES_POINTS + 1)
        )
        return tuple(
            SeriesObservation(
                row.trading_date,
                row.close,
                row.adjusted_close,
                row.currency,
                row.provider.value,
                row.provider_symbol,
                row.retrieved_at,
                row.source_updated_at,
                row.quality_status.value,
                tuple(filter(None, row.warnings.split("\n"))),
            )
            for row in rows
        )

    async def coverage(
        self, workspace_id: UUID, instrument_ids: tuple[UUID, ...], end: date
    ) -> dict[UUID, SeriesCoverage]:
        if not instrument_ids:
            return {}
        rows = await self._session.execute(
            select(
                DailyPriceModel.market_data_instrument_id,
                func.count(DailyPriceModel.id),
                func.min(DailyPriceModel.trading_date),
                func.max(DailyPriceModel.trading_date),
            )
            .where(
                DailyPriceModel.workspace_id == workspace_id,
                DailyPriceModel.market_data_instrument_id.in_(instrument_ids),
                DailyPriceModel.price_type == PriceType.EOD,
                DailyPriceModel.trading_date <= end,
            )
            .group_by(DailyPriceModel.market_data_instrument_id)
        )
        return {key: SeriesCoverage(count, first, last) for key, count, first, last in rows}
