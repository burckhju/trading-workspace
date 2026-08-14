"""Repository contracts and SQLAlchemy adapters for FT-001.

Repositories provide persistence primitives only. They never commit transactions and
contain no business decisions; transaction boundaries and invariants belong to the
later service/domain steps.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, cast
from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.features.market.persistence.enums import AggregateType, LifecycleStatus
from app.features.market.persistence.models import (
    AuditEventModel,
    CurrencyModel,
    ListingModel,
    TradingVenueModel,
    UnderlyingModel,
    WorkspaceModel,
)


class WorkspaceRepository(Protocol):
    async def get(self, workspace_id: UUID) -> WorkspaceModel | None: ...


class ReferenceDataRepository(Protocol):
    async def add_trading_venue(self, venue: TradingVenueModel) -> None: ...
    async def find_trading_venue_by_mic(self, mic: str) -> TradingVenueModel | None: ...
    async def flush(self) -> None: ...
    async def list_active_trading_venues(self) -> Sequence[TradingVenueModel]: ...
    async def list_trading_venues(self) -> Sequence[TradingVenueModel]: ...
    async def get_trading_venue(self, venue_id: UUID) -> TradingVenueModel | None: ...
    async def list_active_currencies(self) -> Sequence[CurrencyModel]: ...
    async def get_currency(self, code: str) -> CurrencyModel | None: ...


class UnderlyingRepository(Protocol):
    async def add(self, underlying: UnderlyingModel) -> None: ...
    async def get(self, workspace_id: UUID, underlying_id: UUID) -> UnderlyingModel | None: ...
    async def get_with_listings(
        self, workspace_id: UUID, underlying_id: UUID
    ) -> UnderlyingModel | None: ...
    async def find_by_isin(self, workspace_id: UUID, isin: str) -> UnderlyingModel | None: ...
    async def find_by_wkn(self, workspace_id: UUID, wkn: str) -> UnderlyingModel | None: ...
    async def search(
        self,
        workspace_id: UUID,
        query: str | None,
        lifecycle_status: LifecycleStatus | None,
        trading_venue_id: UUID | None,
        currency_code: str | None,
        *,
        offset: int,
        limit: int,
    ) -> Sequence[UnderlyingModel]: ...
    async def count_search(
        self,
        workspace_id: UUID,
        query: str | None,
        lifecycle_status: LifecycleStatus | None,
        trading_venue_id: UUID | None,
        currency_code: str | None,
    ) -> int: ...
    async def delete(self, underlying: UnderlyingModel) -> None: ...
    async def flush(self) -> None: ...


class ListingRepository(Protocol):
    async def add(self, listing: ListingModel) -> None: ...
    async def get(self, workspace_id: UUID, listing_id: UUID) -> ListingModel | None: ...
    async def find_by_venue_ticker(
        self, workspace_id: UUID, venue_id: UUID, ticker: str
    ) -> ListingModel | None: ...
    async def list_for_underlying(
        self, workspace_id: UUID, underlying_id: UUID
    ) -> Sequence[ListingModel]: ...
    async def delete(self, listing: ListingModel) -> None: ...
    async def flush(self) -> None: ...


class AuditEventRepository(Protocol):
    async def append(self, event: AuditEventModel) -> None: ...
    async def list_for_aggregate(
        self,
        workspace_id: UUID,
        aggregate_type: AggregateType,
        aggregate_id: UUID,
        *,
        offset: int,
        limit: int,
    ) -> Sequence[AuditEventModel]: ...
    async def list_for_underlying_history(
        self,
        workspace_id: UUID,
        underlying_id: UUID,
        listing_ids: Sequence[UUID],
        *,
        offset: int,
        limit: int,
    ) -> Sequence[AuditEventModel]: ...
    async def count_for_underlying_history(
        self, workspace_id: UUID, underlying_id: UUID, listing_ids: Sequence[UUID]
    ) -> int: ...
    async def flush(self) -> None: ...


class SqlAlchemyWorkspaceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, workspace_id: UUID) -> WorkspaceModel | None:
        return await self._session.get(WorkspaceModel, workspace_id)


class SqlAlchemyReferenceDataRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_trading_venue(self, venue: TradingVenueModel) -> None:
        self._session.add(venue)

    async def find_trading_venue_by_mic(self, mic: str) -> TradingVenueModel | None:
        return cast(
            TradingVenueModel | None,
            await self._session.scalar(
                select(TradingVenueModel).where(TradingVenueModel.mic == mic.strip().upper())
            ),
        )

    async def flush(self) -> None:
        await self._session.flush()

    async def list_active_trading_venues(self) -> Sequence[TradingVenueModel]:
        result = await self._session.scalars(
            select(TradingVenueModel)
            .where(TradingVenueModel.is_active.is_(True))
            .order_by(TradingVenueModel.name, TradingVenueModel.mic)
        )
        return result.all()

    async def list_trading_venues(self) -> Sequence[TradingVenueModel]:
        result = await self._session.scalars(
            select(TradingVenueModel).order_by(TradingVenueModel.name, TradingVenueModel.mic)
        )
        return result.all()

    async def get_trading_venue(self, venue_id: UUID) -> TradingVenueModel | None:
        return await self._session.get(TradingVenueModel, venue_id)

    async def list_active_currencies(self) -> Sequence[CurrencyModel]:
        result = await self._session.scalars(
            select(CurrencyModel)
            .where(CurrencyModel.is_active.is_(True))
            .order_by(CurrencyModel.code)
        )
        return result.all()

    async def get_currency(self, code: str) -> CurrencyModel | None:
        return await self._session.get(CurrencyModel, code)


class SqlAlchemyUnderlyingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, underlying: UnderlyingModel) -> None:
        self._session.add(underlying)

    async def get(self, workspace_id: UUID, underlying_id: UUID) -> UnderlyingModel | None:
        result = await self._session.scalar(
            select(UnderlyingModel).where(
                UnderlyingModel.workspace_id == workspace_id,
                UnderlyingModel.id == underlying_id,
            )
        )
        return result

    async def get_with_listings(
        self, workspace_id: UUID, underlying_id: UUID
    ) -> UnderlyingModel | None:
        result = await self._session.scalar(
            select(UnderlyingModel)
            .options(
                selectinload(UnderlyingModel.listings).selectinload(ListingModel.trading_venue),
                selectinload(UnderlyingModel.listings).selectinload(ListingModel.currency),
            )
            .where(
                UnderlyingModel.workspace_id == workspace_id,
                UnderlyingModel.id == underlying_id,
            )
        )
        return result

    async def find_by_isin(self, workspace_id: UUID, isin: str) -> UnderlyingModel | None:
        result = await self._session.scalar(
            select(UnderlyingModel).where(
                UnderlyingModel.workspace_id == workspace_id,
                UnderlyingModel.isin == isin,
            )
        )
        return result

    async def find_by_wkn(self, workspace_id: UUID, wkn: str) -> UnderlyingModel | None:
        result = await self._session.scalar(
            select(UnderlyingModel).where(
                UnderlyingModel.workspace_id == workspace_id,
                UnderlyingModel.wkn == wkn,
            )
        )
        return result

    @staticmethod
    def _search_statement(
        workspace_id: UUID,
        query: str | None,
        lifecycle_status: LifecycleStatus | None,
        trading_venue_id: UUID | None = None,
        currency_code: str | None = None,
    ) -> Select[tuple[UnderlyingModel]]:
        statement = select(UnderlyingModel).where(UnderlyingModel.workspace_id == workspace_id)
        if lifecycle_status is not None:
            statement = statement.where(UnderlyingModel.lifecycle_status == lifecycle_status)
        if trading_venue_id is not None:
            statement = statement.where(
                UnderlyingModel.listings.any(
                    (ListingModel.trading_venue_id == trading_venue_id)
                    & (ListingModel.lifecycle_status == LifecycleStatus.ACTIVE)
                )
            )
        if currency_code is not None:
            statement = statement.where(
                UnderlyingModel.listings.any(
                    (ListingModel.currency_code == currency_code)
                    & (ListingModel.lifecycle_status == LifecycleStatus.ACTIVE)
                )
            )
        if query:
            pattern = f"%{query}%"
            statement = statement.where(
                or_(
                    UnderlyingModel.name.ilike(pattern),
                    UnderlyingModel.isin.ilike(pattern),
                    UnderlyingModel.wkn.ilike(pattern),
                    UnderlyingModel.listings.any(ListingModel.ticker.ilike(pattern)),
                )
            )
        return statement

    async def search(
        self,
        workspace_id: UUID,
        query: str | None,
        lifecycle_status: LifecycleStatus | None,
        trading_venue_id: UUID | None,
        currency_code: str | None,
        *,
        offset: int,
        limit: int,
    ) -> Sequence[UnderlyingModel]:
        statement = self._search_statement(
            workspace_id,
            query,
            lifecycle_status,
            trading_venue_id,
            currency_code,
        )
        statement = statement.options(
            selectinload(UnderlyingModel.listings).selectinload(ListingModel.trading_venue),
            selectinload(UnderlyingModel.listings).selectinload(ListingModel.currency),
        )
        result = await self._session.scalars(
            statement.order_by(UnderlyingModel.name, UnderlyingModel.id).offset(offset).limit(limit)
        )
        return result.all()

    async def count_search(
        self,
        workspace_id: UUID,
        query: str | None,
        lifecycle_status: LifecycleStatus | None,
        trading_venue_id: UUID | None,
        currency_code: str | None,
    ) -> int:
        statement = self._search_statement(
            workspace_id,
            query,
            lifecycle_status,
            trading_venue_id,
            currency_code,
        )
        count = await self._session.scalar(select(func.count()).select_from(statement.subquery()))
        return int(count or 0)

    async def delete(self, underlying: UnderlyingModel) -> None:
        await self._session.delete(underlying)

    async def flush(self) -> None:
        await self._session.flush()


class SqlAlchemyListingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, listing: ListingModel) -> None:
        self._session.add(listing)

    async def get(self, workspace_id: UUID, listing_id: UUID) -> ListingModel | None:
        result = await self._session.scalar(
            select(ListingModel).where(
                ListingModel.workspace_id == workspace_id,
                ListingModel.id == listing_id,
            )
        )
        return result

    async def find_by_venue_ticker(
        self, workspace_id: UUID, venue_id: UUID, ticker: str
    ) -> ListingModel | None:
        result = await self._session.scalar(
            select(ListingModel).where(
                ListingModel.workspace_id == workspace_id,
                ListingModel.trading_venue_id == venue_id,
                ListingModel.ticker == ticker,
            )
        )
        return result

    async def list_for_underlying(
        self, workspace_id: UUID, underlying_id: UUID
    ) -> Sequence[ListingModel]:
        result = await self._session.scalars(
            select(ListingModel)
            .where(
                ListingModel.workspace_id == workspace_id,
                ListingModel.underlying_id == underlying_id,
            )
            .order_by(ListingModel.is_primary.desc(), ListingModel.ticker, ListingModel.id)
        )
        return result.all()

    async def delete(self, listing: ListingModel) -> None:
        await self._session.delete(listing)

    async def flush(self) -> None:
        await self._session.flush()


class SqlAlchemyAuditEventRepository:
    """Append-only audit repository; update and delete operations are intentionally absent."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(self, event: AuditEventModel) -> None:
        self._session.add(event)

    async def list_for_aggregate(
        self,
        workspace_id: UUID,
        aggregate_type: AggregateType,
        aggregate_id: UUID,
        *,
        offset: int,
        limit: int,
    ) -> Sequence[AuditEventModel]:
        result = await self._session.scalars(
            select(AuditEventModel)
            .where(
                AuditEventModel.workspace_id == workspace_id,
                AuditEventModel.aggregate_type == aggregate_type,
                AuditEventModel.aggregate_id == aggregate_id,
            )
            .order_by(AuditEventModel.occurred_at.desc(), AuditEventModel.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return result.all()

    async def list_for_underlying_history(
        self,
        workspace_id: UUID,
        underlying_id: UUID,
        listing_ids: Sequence[UUID],
        *,
        offset: int,
        limit: int,
    ) -> Sequence[AuditEventModel]:
        aggregate_filter = (
            (AuditEventModel.aggregate_type == AggregateType.UNDERLYING)
            & (AuditEventModel.aggregate_id == underlying_id)
        ) | (
            (AuditEventModel.aggregate_type == AggregateType.LISTING)
            & AuditEventModel.aggregate_id.in_(listing_ids)
        )
        result = await self._session.scalars(
            select(AuditEventModel)
            .where(
                AuditEventModel.workspace_id == workspace_id,
                aggregate_filter,
            )
            .order_by(AuditEventModel.occurred_at.desc(), AuditEventModel.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return result.all()

    async def count_for_underlying_history(
        self, workspace_id: UUID, underlying_id: UUID, listing_ids: Sequence[UUID]
    ) -> int:
        aggregate_filter = (
            (AuditEventModel.aggregate_type == AggregateType.UNDERLYING)
            & (AuditEventModel.aggregate_id == underlying_id)
        ) | (
            (AuditEventModel.aggregate_type == AggregateType.LISTING)
            & AuditEventModel.aggregate_id.in_(listing_ids)
        )
        count = await self._session.scalar(
            select(func.count())
            .select_from(AuditEventModel)
            .where(AuditEventModel.workspace_id == workspace_id, aggregate_filter)
        )
        return int(count or 0)

    async def flush(self) -> None:
        await self._session.flush()
