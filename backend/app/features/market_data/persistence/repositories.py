"""Repository contracts and SQLAlchemy adapters for market-data persistence."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Protocol, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.market.persistence.models import ListingModel
from app.features.market_data.domain.enums import MappingStatus, MarketDataProvider, PriceType
from app.features.market_data.persistence.instruments import MarketDataInstrumentModel
from app.features.market_data.persistence.models import (
    DailyPriceModel,
    ProviderInstrumentMappingModel,
    WarrantProviderMappingModel,
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
    async def find_for_instrument(
        self, workspace_id: UUID, instrument_id: UUID, provider: MarketDataProvider
    ) -> ProviderInstrumentMappingModel | None: ...
    async def list_all(
        self, workspace_id: UUID, provider: MarketDataProvider | None = None
    ) -> Sequence[ProviderInstrumentMappingModel]: ...
    async def get_listing_venue_id(self, workspace_id: UUID, listing_id: UUID) -> UUID | None: ...
    async def list_active_venue_ids_for_exchange(
        self,
        workspace_id: UUID,
        provider: MarketDataProvider,
        provider_exchange_code: str,
    ) -> Sequence[UUID]: ...
    async def flush(self) -> None: ...


class WarrantProviderMappingRepository(Protocol):
    async def add(self, mapping: WarrantProviderMappingModel) -> None: ...
    async def get(
        self, workspace_id: UUID, mapping_id: UUID
    ) -> WarrantProviderMappingModel | None: ...
    async def find_for_warrant_listing(
        self, workspace_id: UUID, warrant_listing_id: UUID, provider: MarketDataProvider
    ) -> WarrantProviderMappingModel | None: ...
    async def flush(self) -> None: ...


class SqlAlchemyWarrantProviderMappingRepository:
    """SQLAlchemy adapter for the separate FT-004 WarrantListing provider mapping."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, mapping: WarrantProviderMappingModel) -> None:
        self._session.add(mapping)

    async def get(self, workspace_id: UUID, mapping_id: UUID) -> WarrantProviderMappingModel | None:
        return cast(
            WarrantProviderMappingModel | None,
            await self._session.scalar(
                select(WarrantProviderMappingModel).where(
                    WarrantProviderMappingModel.workspace_id == workspace_id,
                    WarrantProviderMappingModel.id == mapping_id,
                )
            ),
        )

    async def find_for_warrant_listing(
        self, workspace_id: UUID, warrant_listing_id: UUID, provider: MarketDataProvider
    ) -> WarrantProviderMappingModel | None:
        return cast(
            WarrantProviderMappingModel | None,
            await self._session.scalar(
                select(WarrantProviderMappingModel).where(
                    WarrantProviderMappingModel.workspace_id == workspace_id,
                    WarrantProviderMappingModel.warrant_listing_id == warrant_listing_id,
                    WarrantProviderMappingModel.provider == provider,
                )
            ),
        )

    async def flush(self) -> None:
        await self._session.flush()


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
    async def get_for_instrument(
        self,
        workspace_id: UUID,
        instrument_id: UUID,
        trading_date: date,
        price_type: PriceType = PriceType.EOD,
    ) -> DailyPriceModel | None: ...
    async def list_range(
        self, workspace_id: UUID, listing_id: UUID, start_date: date, end_date: date
    ) -> Sequence[DailyPriceModel]: ...
    async def list_range_for_instrument(
        self, workspace_id: UUID, instrument_id: UUID, start_date: date, end_date: date
    ) -> Sequence[DailyPriceModel]: ...
    async def latest(
        self, workspace_id: UUID, listing_id: UUID, on_or_before: date | None = None
    ) -> DailyPriceModel | None: ...
    async def flush(self) -> None: ...


class SqlAlchemyProviderInstrumentMappingRepository:
    """SQLAlchemy implementation scoped by workspace and neutral instrument identity."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _instrument_for_listing(self, workspace_id: UUID, listing_id: UUID) -> UUID:
        value = await self._session.scalar(
            select(MarketDataInstrumentModel.id).where(
                MarketDataInstrumentModel.workspace_id == workspace_id,
                MarketDataInstrumentModel.kind == "LISTING",
                MarketDataInstrumentModel.listing_id == listing_id,
                MarketDataInstrumentModel.active.is_(True),
            )
        )
        if value is None:
            raise ValueError("market-data instrument for listing is missing")
        return cast(UUID, value)

    async def add(self, mapping: ProviderInstrumentMappingModel) -> None:
        if mapping.market_data_instrument_id is None:
            if mapping.listing_id is None:
                raise ValueError("provider mapping requires market-data instrument identity")
            mapping.market_data_instrument_id = await self._instrument_for_listing(
                mapping.workspace_id, mapping.listing_id
            )
        self._session.add(mapping)

    async def get(
        self, workspace_id: UUID, mapping_id: UUID
    ) -> ProviderInstrumentMappingModel | None:
        return await self._session.scalar(
            select(ProviderInstrumentMappingModel).where(
                ProviderInstrumentMappingModel.workspace_id == workspace_id,
                ProviderInstrumentMappingModel.id == mapping_id,
            )
        )

    async def find_for_listing(
        self, workspace_id: UUID, listing_id: UUID, provider: MarketDataProvider
    ) -> ProviderInstrumentMappingModel | None:
        return await self._session.scalar(
            select(ProviderInstrumentMappingModel).where(
                ProviderInstrumentMappingModel.workspace_id == workspace_id,
                ProviderInstrumentMappingModel.listing_id == listing_id,
                ProviderInstrumentMappingModel.provider == provider,
            )
        )

    async def find_for_instrument(
        self, workspace_id: UUID, instrument_id: UUID, provider: MarketDataProvider
    ) -> ProviderInstrumentMappingModel | None:
        return await self._session.scalar(
            select(ProviderInstrumentMappingModel).where(
                ProviderInstrumentMappingModel.workspace_id == workspace_id,
                ProviderInstrumentMappingModel.market_data_instrument_id == instrument_id,
                ProviderInstrumentMappingModel.provider == provider,
            )
        )

    async def list_all(
        self, workspace_id: UUID, provider: MarketDataProvider | None = None
    ) -> Sequence[ProviderInstrumentMappingModel]:
        statement = select(ProviderInstrumentMappingModel).where(
            ProviderInstrumentMappingModel.workspace_id == workspace_id
        )
        if provider is not None:
            statement = statement.where(ProviderInstrumentMappingModel.provider == provider)
        result = await self._session.scalars(
            statement.order_by(
                ProviderInstrumentMappingModel.provider,
                ProviderInstrumentMappingModel.provider_symbol,
            )
        )
        return result.all()

    async def get_listing_venue_id(self, workspace_id: UUID, listing_id: UUID) -> UUID | None:
        return cast(
            UUID | None,
            await self._session.scalar(
                select(ListingModel.trading_venue_id).where(
                    ListingModel.workspace_id == workspace_id,
                    ListingModel.id == listing_id,
                )
            ),
        )

    async def list_active_venue_ids_for_exchange(
        self,
        workspace_id: UUID,
        provider: MarketDataProvider,
        provider_exchange_code: str,
    ) -> Sequence[UUID]:
        result = await self._session.scalars(
            select(ListingModel.trading_venue_id)
            .join(
                ProviderInstrumentMappingModel,
                ProviderInstrumentMappingModel.listing_id == ListingModel.id,
            )
            .where(
                ProviderInstrumentMappingModel.workspace_id == workspace_id,
                ProviderInstrumentMappingModel.provider == provider,
                ProviderInstrumentMappingModel.provider_exchange_code
                == provider_exchange_code.strip().upper(),
                ProviderInstrumentMappingModel.status == MappingStatus.ACTIVE,
                ListingModel.workspace_id == workspace_id,
            )
            .distinct()
        )
        return result.all()

    async def flush(self) -> None:
        await self._session.flush()


class SqlAlchemyDailyPriceRepository:
    """SQLAlchemy implementation with deterministic chronological queries."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _instrument_for_listing(self, workspace_id: UUID, listing_id: UUID) -> UUID:
        value = await self._session.scalar(
            select(MarketDataInstrumentModel.id).where(
                MarketDataInstrumentModel.workspace_id == workspace_id,
                MarketDataInstrumentModel.kind == "LISTING",
                MarketDataInstrumentModel.listing_id == listing_id,
                MarketDataInstrumentModel.active.is_(True),
            )
        )
        if value is None:
            raise ValueError("market-data instrument for listing is missing")
        return cast(UUID, value)

    async def add(self, price: DailyPriceModel) -> None:
        if price.market_data_instrument_id is None:
            if price.listing_id is None:
                raise ValueError("daily price requires market-data instrument identity")
            price.market_data_instrument_id = await self._instrument_for_listing(
                price.workspace_id, price.listing_id
            )
        self._session.add(price)

    async def get(
        self,
        workspace_id: UUID,
        listing_id: UUID,
        trading_date: date,
        price_type: PriceType = PriceType.EOD,
    ) -> DailyPriceModel | None:
        return await self._session.scalar(
            select(DailyPriceModel).where(
                DailyPriceModel.workspace_id == workspace_id,
                DailyPriceModel.listing_id == listing_id,
                DailyPriceModel.trading_date == trading_date,
                DailyPriceModel.price_type == price_type,
            )
        )

    async def get_for_instrument(
        self,
        workspace_id: UUID,
        instrument_id: UUID,
        trading_date: date,
        price_type: PriceType = PriceType.EOD,
    ) -> DailyPriceModel | None:
        return await self._session.scalar(
            select(DailyPriceModel).where(
                DailyPriceModel.workspace_id == workspace_id,
                DailyPriceModel.market_data_instrument_id == instrument_id,
                DailyPriceModel.trading_date == trading_date,
                DailyPriceModel.price_type == price_type,
            )
        )

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

    async def list_range_for_instrument(
        self, workspace_id: UUID, instrument_id: UUID, start_date: date, end_date: date
    ) -> Sequence[DailyPriceModel]:
        result = await self._session.scalars(
            select(DailyPriceModel)
            .where(
                DailyPriceModel.workspace_id == workspace_id,
                DailyPriceModel.market_data_instrument_id == instrument_id,
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
        return await self._session.scalar(
            statement.order_by(DailyPriceModel.trading_date.desc()).limit(1)
        )

    async def flush(self) -> None:
        await self._session.flush()
