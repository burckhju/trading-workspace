"""Repository contracts and SQLAlchemy adapters for market-data persistence."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.market_data.domain.enums import MarketDataProvider, PriceType
from app.features.market_data.persistence.models import (
    DailyPriceModel,
    ProviderInstrumentMappingModel,
)


class ProviderInstrumentMappingRepository(Protocol):
    """Persistence operations for provider instrument mappings."""

    async def add(self, mapping: ProviderInstrumentMappingModel) -> None: ...
    async def get(
        self, workspace_id: UUID, mapping_id: UUID
    ) -> ProviderInstrumentMappingModel | None: ...
    async def find_for_listing(
        self, workspace_id: UUID, listing_id: UUID, provider: MarketDataProvider
    ) -> ProviderInstrumentMappingModel | None: ...
    async def list_all(
        self, workspace_id: UUID, provider: MarketDataProvider | None = None
    ) -> Sequence[ProviderInstrumentMappingModel]: ...
    async def flush(self) -> None: ...


class DailyPriceRepository(Protocol):
    """Persistence operations for completed daily prices."""

    async def add(self, price: DailyPriceModel) -> None: ...
    async def get(
        self,
        workspace_id: UUID,
        listing_id: UUID,
        trading_date: date,
        price_type: PriceType = PriceType.EOD,
    ) -> DailyPriceModel | None: ...
    async def list_range(
        self, workspace_id: UUID, listing_id: UUID, start_date: date, end_date: date
    ) -> Sequence[DailyPriceModel]: ...
    async def latest(
        self, workspace_id: UUID, listing_id: UUID, on_or_before: date | None = None
    ) -> DailyPriceModel | None: ...
    async def flush(self) -> None: ...


class SqlAlchemyProviderInstrumentMappingRepository:
    """SQLAlchemy implementation scoped by workspace and listing identity."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, mapping: ProviderInstrumentMappingModel) -> None:
        self._session.add(mapping)

    async def get(
        self, workspace_id: UUID, mapping_id: UUID
    ) -> ProviderInstrumentMappingModel | None:
        result = await self._session.scalar(
            select(ProviderInstrumentMappingModel).where(
                ProviderInstrumentMappingModel.workspace_id == workspace_id,
                ProviderInstrumentMappingModel.id == mapping_id,
            )
        )
        return result

    async def find_for_listing(
        self, workspace_id: UUID, listing_id: UUID, provider: MarketDataProvider
    ) -> ProviderInstrumentMappingModel | None:
        result = await self._session.scalar(
            select(ProviderInstrumentMappingModel).where(
                ProviderInstrumentMappingModel.workspace_id == workspace_id,
                ProviderInstrumentMappingModel.listing_id == listing_id,
                ProviderInstrumentMappingModel.provider == provider,
            )
        )
        return result

    async def list_all(
        self, workspace_id: UUID, provider: MarketDataProvider | None = None
    ) -> Sequence[ProviderInstrumentMappingModel]:
        statement = select(ProviderInstrumentMappingModel).where(
            ProviderInstrumentMappingModel.workspace_id == workspace_id
        )
        if provider is not None:
            statement = statement.where(
                ProviderInstrumentMappingModel.provider == provider
            )
        result = await self._session.scalars(
            statement.order_by(
                ProviderInstrumentMappingModel.provider,
                ProviderInstrumentMappingModel.provider_symbol,
            )
        )
        return result.all()

    async def flush(self) -> None:
        await self._session.flush()


class SqlAlchemyDailyPriceRepository:
    """SQLAlchemy implementation with deterministic chronological queries."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, price: DailyPriceModel) -> None:
        self._session.add(price)

    async def get(
        self,
        workspace_id: UUID,
        listing_id: UUID,
        trading_date: date,
        price_type: PriceType = PriceType.EOD,
    ) -> DailyPriceModel | None:
        result = await self._session.scalar(
            select(DailyPriceModel).where(
                DailyPriceModel.workspace_id == workspace_id,
                DailyPriceModel.listing_id == listing_id,
                DailyPriceModel.trading_date == trading_date,
                DailyPriceModel.price_type == price_type,
            )
        )
        return result

    async def list_range(
        self, workspace_id: UUID, listing_id: UUID, start_date: date, end_date: date
    ) -> Sequence[DailyPriceModel]:
        result = await self._session.scalars(
            select(DailyPriceModel)
            .where(
                DailyPriceModel.workspace_id == workspace_id,
                DailyPriceModel.listing_id == listing_id,
                DailyPriceModel.trading_date.between(start_date, end_date),
            )
            .order_by(DailyPriceModel.trading_date)
        )
        return result.all()

    async def latest(
        self, workspace_id: UUID, listing_id: UUID, on_or_before: date | None = None
    ) -> DailyPriceModel | None:
        statement = select(DailyPriceModel).where(
            DailyPriceModel.workspace_id == workspace_id,
            DailyPriceModel.listing_id == listing_id,
        )
        if on_or_before is not None:
            statement = statement.where(DailyPriceModel.trading_date <= on_or_before)
        result = await self._session.scalar(
            statement.order_by(DailyPriceModel.trading_date.desc()).limit(1)
        )
        return result

    async def flush(self) -> None:
        await self._session.flush()
