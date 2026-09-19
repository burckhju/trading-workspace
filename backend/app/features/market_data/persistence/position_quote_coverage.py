"""Batched read model for open positions and their persisted quote-source selections."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, select

from app.database.manager import DatabaseManager
from app.features.market.persistence.models import TradingVenueModel
from app.features.market_data.domain.enums import MarketDataProvider
from app.features.market_data.persistence.models import (
    PositionQuoteSourceSelectionModel,
    WarrantProviderMappingModel,
)
from app.features.market_data.persistence.quote_identity import verified_identity
from app.features.product.persistence.models import WarrantListingModel, WarrantModel
from app.features.trade_position.persistence.models import PositionModel, TradeModel


@dataclass(frozen=True)
class PositionQuoteCoverageRecord:
    position_id: UUID
    trade_id: UUID
    warrant_id: UUID
    name: str
    isin: str | None
    wkn: str | None
    selection_id: UUID | None
    selection_status: str | None
    selection_reason: str | None
    policy_version: str | None
    selected_at: datetime | None
    provider: str | None
    listing_id: UUID | None
    mapping_id: UUID | None
    persisted_identity_key: str | None
    persisted_mapping_version: int | None
    current_identity_key: str | None
    current_mapping_status: str | None
    current_mapping_version: int | None
    provider_exchange_code: str | None
    mic: str | None
    currency: str | None


class PositionQuoteCoverageRepository:
    def __init__(self, database: DatabaseManager) -> None:
        self.database = database

    async def open_positions(
        self, workspace_id: UUID
    ) -> tuple[PositionQuoteCoverageRecord, ...]:
        async with self.database.session_context() as session:
            rows = (
                await session.execute(
                    select(
                        PositionModel,
                        TradeModel,
                        WarrantModel,
                        PositionQuoteSourceSelectionModel,
                        WarrantListingModel,
                        TradingVenueModel,
                        WarrantProviderMappingModel,
                    )
                    .join(TradeModel, TradeModel.id == PositionModel.trade_id)
                    .join(WarrantModel, WarrantModel.id == PositionModel.product_id)
                    .outerjoin(
                        PositionQuoteSourceSelectionModel,
                        and_(
                            PositionQuoteSourceSelectionModel.workspace_id
                            == TradeModel.workspace_id,
                            PositionQuoteSourceSelectionModel.position_id == PositionModel.id,
                            PositionQuoteSourceSelectionModel.superseded_at.is_(None),
                        ),
                    )
                    .outerjoin(
                        WarrantListingModel,
                        and_(
                            WarrantListingModel.id
                            == PositionQuoteSourceSelectionModel.warrant_listing_id,
                            WarrantListingModel.workspace_id == TradeModel.workspace_id,
                        ),
                    )
                    .outerjoin(
                        TradingVenueModel,
                        TradingVenueModel.id == WarrantListingModel.trading_venue_id,
                    )
                    .outerjoin(
                        WarrantProviderMappingModel,
                        and_(
                            WarrantProviderMappingModel.id
                            == PositionQuoteSourceSelectionModel.warrant_provider_mapping_id,
                            WarrantProviderMappingModel.workspace_id == TradeModel.workspace_id,
                        ),
                    )
                    .where(
                        TradeModel.workspace_id == workspace_id,
                        TradeModel.product_id == PositionModel.product_id,
                        TradeModel.cancelled_at.is_(None),
                        PositionModel.open_quantity > 0,
                        PositionModel.closed_at.is_(None),
                    )
                    .order_by(WarrantModel.isin, PositionModel.id)
                )
            ).all()

        result = []
        for position, trade, warrant, selection, listing, venue, mapping in rows:
            current_identity_key = None
            if (
                selection is not None
                and selection.selection_status == "SELECTED"
                and selection.provider is not None
                and listing is not None
                and venue is not None
            ):
                try:
                    provider = MarketDataProvider(selection.provider)
                except ValueError:
                    provider = None
                if provider is not None:
                    identity = verified_identity(
                        workspace_id, listing, warrant, venue, provider, mapping
                    )
                    current_identity_key = identity.key if identity is not None else None

            result.append(
                PositionQuoteCoverageRecord(
                    position_id=position.id,
                    trade_id=trade.id,
                    warrant_id=warrant.id,
                    name=warrant.display_name,
                    isin=warrant.isin,
                    wkn=warrant.wkn,
                    selection_id=selection.id if selection is not None else None,
                    selection_status=(
                        selection.selection_status if selection is not None else None
                    ),
                    selection_reason=(
                        selection.selection_reason if selection is not None else None
                    ),
                    policy_version=selection.policy_version if selection is not None else None,
                    selected_at=selection.selected_at if selection is not None else None,
                    provider=selection.provider if selection is not None else None,
                    listing_id=(
                        selection.warrant_listing_id if selection is not None else None
                    ),
                    mapping_id=(
                        selection.warrant_provider_mapping_id
                        if selection is not None
                        else None
                    ),
                    persisted_identity_key=(
                        selection.identity_key if selection is not None else None
                    ),
                    persisted_mapping_version=(
                        selection.mapping_version if selection is not None else None
                    ),
                    current_identity_key=current_identity_key,
                    current_mapping_status=(
                        mapping.status.value if mapping is not None else None
                    ),
                    current_mapping_version=mapping.version if mapping is not None else None,
                    provider_exchange_code=(
                        mapping.provider_exchange_code if mapping is not None else None
                    ),
                    mic=venue.mic if venue is not None else None,
                    currency=(
                        listing.quotation_currency_code if listing is not None else None
                    ),
                )
            )
        return tuple(result)
