"""Persistence reader/writer for position quote-source decisions."""

from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.market.persistence.models import TradingVenueModel
from app.features.market_data.domain.enums import MappingStatus, MarketDataProvider
from app.features.market_data.domain.position_quote_source import PositionQuoteSourceCandidate
from app.features.market_data.persistence.models import (
    PositionQuoteSourceSelectionModel,
    WarrantProviderMappingModel,
)
from app.features.market_data.persistence.quote_identity import verified_identity
from app.features.product.domain.models import WarrantLifecycle
from app.features.product.persistence.models import WarrantListingModel, WarrantModel
from app.features.trade_position.persistence.models import PositionModel, TradeModel


class PositionQuoteSourceSelectionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def lock_open_position(
        self, workspace_id: UUID, position_id: UUID, warrant_id: UUID
    ) -> bool:
        row = await self.session.scalar(
            select(PositionModel.id)
            .join(TradeModel, TradeModel.id == PositionModel.trade_id)
            .where(
                PositionModel.id == position_id,
                PositionModel.product_id == warrant_id,
                PositionModel.open_quantity > 0,
                PositionModel.closed_at.is_(None),
                TradeModel.workspace_id == workspace_id,
                TradeModel.product_id == warrant_id,
                TradeModel.cancelled_at.is_(None),
            )
            .with_for_update()
        )
        return row is not None

    async def active_for_position(
        self, workspace_id: UUID, position_id: UUID
    ) -> PositionQuoteSourceSelectionModel | None:
        return await self.session.scalar(
            select(PositionQuoteSourceSelectionModel)
            .where(
                PositionQuoteSourceSelectionModel.workspace_id == workspace_id,
                PositionQuoteSourceSelectionModel.position_id == position_id,
                PositionQuoteSourceSelectionModel.superseded_at.is_(None),
            )
            .with_for_update()
        )

    async def verified_candidates(
        self,
        workspace_id: UUID,
        warrant_id: UUID,
        allowed_providers: Iterable[MarketDataProvider],
    ) -> tuple[PositionQuoteSourceCandidate, ...]:
        providers = tuple(sorted(set(allowed_providers), key=lambda item: item.value))
        if not providers:
            return ()

        rows = (
            await self.session.execute(
                select(WarrantListingModel, WarrantModel, TradingVenueModel)
                .join(WarrantModel, WarrantModel.id == WarrantListingModel.warrant_id)
                .join(
                    TradingVenueModel,
                    TradingVenueModel.id == WarrantListingModel.trading_venue_id,
                )
                .where(
                    WarrantListingModel.workspace_id == workspace_id,
                    WarrantListingModel.warrant_id == warrant_id,
                    WarrantListingModel.lifecycle_status == WarrantLifecycle.ACTIVE,
                    WarrantModel.workspace_id == workspace_id,
                    WarrantModel.id == warrant_id,
                    WarrantModel.lifecycle_status == WarrantLifecycle.ACTIVE,
                    TradingVenueModel.is_active.is_(True),
                )
                .order_by(WarrantListingModel.id)
            )
        ).all()
        if not rows:
            return ()

        listing_ids = [listing.id for listing, _warrant, _venue in rows]
        mappings = list(
            await self.session.scalars(
                select(WarrantProviderMappingModel).where(
                    WarrantProviderMappingModel.workspace_id == workspace_id,
                    WarrantProviderMappingModel.warrant_listing_id.in_(listing_ids),
                    WarrantProviderMappingModel.provider.in_(providers),
                    WarrantProviderMappingModel.status == MappingStatus.ACTIVE,
                    WarrantProviderMappingModel.validated_at.is_not(None),
                )
            )
        )
        mapping_index = {
            (mapping.warrant_listing_id, mapping.provider): mapping for mapping in mappings
        }

        candidates: list[PositionQuoteSourceCandidate] = []
        for listing, warrant, venue in rows:
            for provider in providers:
                mapping = mapping_index.get((listing.id, provider))
                identity = verified_identity(
                    workspace_id, listing, warrant, venue, provider, mapping
                )
                if identity is None:
                    continue
                candidates.append(
                    PositionQuoteSourceCandidate(
                        provider=provider,
                        listing_id=listing.id,
                        mapping_id=mapping.id if mapping is not None else None,
                        mapping_version=mapping.version if mapping is not None else None,
                        identity_key=identity.key,
                        currency=identity.currency,
                        mic=identity.mic,
                        provider_exchange_code=identity.exchange,
                    )
                )
        return tuple(candidates)

    async def add(self, selection: PositionQuoteSourceSelectionModel) -> None:
        self.session.add(selection)
        await self.session.flush()
