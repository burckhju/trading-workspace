"""Application service for provider-neutral market-data instrument identities."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.market.persistence.models import ListingModel
from app.features.market.persistence.top_down_models import MarketReferenceModel
from app.features.market_data.persistence.instruments import MarketDataInstrumentModel


class MarketDataInstrumentIdentityService:
    """Resolve or create exactly one neutral market-data identity per semantic owner."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def for_listing(
        self, *, workspace_id: UUID, listing_id: UUID
    ) -> MarketDataInstrumentModel:
        existing = await self._session.scalar(
            select(MarketDataInstrumentModel).where(
                MarketDataInstrumentModel.workspace_id == workspace_id,
                MarketDataInstrumentModel.listing_id == listing_id,
            )
        )
        if existing is not None:
            return existing

        owner = await self._session.scalar(
            select(ListingModel.id).where(
                ListingModel.workspace_id == workspace_id,
                ListingModel.id == listing_id,
            )
        )
        if owner is None:
            raise ValueError("listing not found in workspace")

        value = MarketDataInstrumentModel(
            id=uuid4(),
            workspace_id=workspace_id,
            kind="LISTING",
            listing_id=listing_id,
            market_reference_id=None,
            active=True,
            created_at=datetime.now(UTC),
        )
        self._session.add(value)
        await self._session.flush()
        return value

    async def for_market_reference(
        self, *, workspace_id: UUID, market_reference_id: UUID
    ) -> MarketDataInstrumentModel:
        existing = await self._session.scalar(
            select(MarketDataInstrumentModel).where(
                MarketDataInstrumentModel.workspace_id == workspace_id,
                MarketDataInstrumentModel.market_reference_id == market_reference_id,
            )
        )
        if existing is not None:
            return existing

        owner = await self._session.scalar(
            select(MarketReferenceModel.active).where(
                MarketReferenceModel.workspace_id == workspace_id,
                MarketReferenceModel.id == market_reference_id,
            )
        )
        if owner is None:
            raise ValueError("market reference not found in workspace")

        value = MarketDataInstrumentModel(
            id=uuid4(),
            workspace_id=workspace_id,
            kind="MARKET_REFERENCE",
            listing_id=None,
            market_reference_id=market_reference_id,
            active=bool(owner),
            created_at=datetime.now(UTC),
        )
        self._session.add(value)
        await self._session.flush()
        return value

    async def get(self, *, workspace_id: UUID, instrument_id: UUID) -> MarketDataInstrumentModel:
        value = await self._session.scalar(
            select(MarketDataInstrumentModel).where(
                MarketDataInstrumentModel.workspace_id == workspace_id,
                MarketDataInstrumentModel.id == instrument_id,
            )
        )
        if value is None:
            raise ValueError("market-data instrument not found in workspace")
        return value
