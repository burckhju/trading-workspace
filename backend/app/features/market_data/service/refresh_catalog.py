"""Read active workspace instruments without inferring product identity from symbols."""

from dataclasses import dataclass
from uuid import UUID, uuid5

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import DatabaseManager
from app.features.market.domain.enums import LifecycleStatus
from app.features.market.persistence.chart_watchlist import ChartWatchlistMemberModel
from app.features.market.persistence.models import (
    CurrencyModel,
    IssuerModel,
    ListingModel,
    TradingVenueModel,
    UnderlyingModel,
)
from app.features.market.persistence.top_down_models import MarketReferenceModel
from app.features.market_data.domain.enums import MappingStatus, MarketDataProvider
from app.features.market_data.persistence.instruments import MarketDataInstrumentModel
from app.features.market_data.persistence.models import (
    ProviderInstrumentMappingModel,
    WarrantProviderMappingModel,
)
from app.features.product.domain.models import WarrantLifecycle
from app.features.product.persistence.models import WarrantListingModel, WarrantModel
from app.features.trade_position.persistence.models import PositionModel, TradeModel


@dataclass(frozen=True, slots=True)
class RefreshInstrument:
    id: UUID
    name: str
    isin: str | None
    issuer: str | None = None
    listing_id: UUID | None = None
    held: bool = False
    reference_id: UUID | None = None
    setup_code: str | None = None


ISSUER_PROVIDERS = frozenset({MarketDataProvider.JPMORGAN, MarketDataProvider.MORGAN_STANLEY})


async def read_issuer_route_groups(
    database: DatabaseManager, workspace_id: UUID
) -> tuple[set[UUID], set[UUID]]:
    """Scheduling hints only; adapters revalidate each route before fetching/storing.

    Products with both kinds of mappings keep both refresh jobs. This query
    neither creates mappings nor changes the position's selected source.
    """
    async with database.session_context() as session:
        rows = (
            await session.execute(
                select(WarrantListingModel.warrant_id, WarrantProviderMappingModel.provider)
                .join(
                    WarrantProviderMappingModel,
                    WarrantProviderMappingModel.warrant_listing_id == WarrantListingModel.id,
                )
                .where(
                    WarrantListingModel.workspace_id == workspace_id,
                    WarrantListingModel.lifecycle_status == WarrantLifecycle.ACTIVE,
                    WarrantProviderMappingModel.workspace_id == workspace_id,
                    WarrantProviderMappingModel.status == MappingStatus.ACTIVE,
                    WarrantProviderMappingModel.validated_at.is_not(None),
                )
            )
        ).all()
    issuers = {warrant_id for warrant_id, provider in rows if provider in ISSUER_PROVIDERS}
    others = {warrant_id for warrant_id, provider in rows if provider not in ISSUER_PROVIDERS}
    return issuers, issuers - others


async def read_catalog(
    database: DatabaseManager,
    workspace_id: UUID,
) -> tuple[list[RefreshInstrument], list[RefreshInstrument]]:
    # Membership avoids duplicated jobs when several open trades hold the same product.
    held_products = (
        select(PositionModel.product_id)
        .join(TradeModel, TradeModel.id == PositionModel.trade_id)
        .where(
            TradeModel.workspace_id == workspace_id,
            TradeModel.cancelled_at.is_(None),
            TradeModel.product_id == PositionModel.product_id,
            PositionModel.open_quantity > 0,
            PositionModel.closed_at.is_(None),
        )
    )
    held_warrant = WarrantModel.id.in_(held_products)
    held_underlying = UnderlyingModel.id.in_(
        select(WarrantModel.underlying_id).where(
            WarrantModel.workspace_id == workspace_id,
            WarrantModel.id.in_(held_products),
        )
    )
    async with database.session_context() as session:
        warrants = (
            await session.execute(
                select(WarrantModel, IssuerModel, held_warrant)
                .join(IssuerModel, IssuerModel.id == WarrantModel.issuer_id)
                .where(
                    WarrantModel.workspace_id == workspace_id,
                    WarrantModel.lifecycle_status == WarrantLifecycle.ACTIVE,
                    IssuerModel.is_active.is_(True),
                )
                .order_by(held_warrant.desc(), WarrantModel.id)
            )
        ).all()
        underlyings = (
            await session.execute(
                select(UnderlyingModel, ListingModel, held_underlying)
                .outerjoin(
                    ListingModel,
                    (ListingModel.underlying_id == UnderlyingModel.id)
                    & (ListingModel.workspace_id == workspace_id)
                    & (ListingModel.lifecycle_status == LifecycleStatus.ACTIVE)
                    & (
                        ListingModel.trading_venue_id.in_(
                            select(TradingVenueModel.id).where(
                                TradingVenueModel.is_active.is_(True)
                            )
                        )
                    )
                    & (
                        ListingModel.currency_code.in_(
                            select(CurrencyModel.code).where(CurrencyModel.is_active.is_(True))
                        )
                    ),
                )
                .where(
                    UnderlyingModel.workspace_id == workspace_id,
                    UnderlyingModel.lifecycle_status == LifecycleStatus.ACTIVE,
                )
                .order_by(held_underlying.desc(), UnderlyingModel.id, ListingModel.id)
            )
        ).all()
        chart_items = await _read_chart_items(session, workspace_id)
        return (
            [
                RefreshInstrument(w.id, w.display_name, w.isin, issuer.legal_name, held=held)
                for w, issuer, held in warrants
            ],
            chart_items
            + [
                RefreshInstrument(
                    u.id, u.name, u.isin, listing_id=listing.id if listing else None, held=held
                )
                for u, listing, held in underlyings
            ],
        )


async def _read_chart_items(session: AsyncSession, workspace_id: UUID) -> list[RefreshInstrument]:
    """Resume only explicit chart activation; never discover arbitrary index mappings."""
    pending = list(
        await session.scalars(
            select(ChartWatchlistMemberModel)
            .where(
                ChartWatchlistMemberModel.workspace_id == workspace_id,
                ChartWatchlistMemberModel.setup_completed_at.is_(None),
            )
            .order_by(ChartWatchlistMemberModel.ordinal)
        )
    )
    references = list(
        await session.scalars(
            select(MarketReferenceModel)
            .join(
                ChartWatchlistMemberModel,
                ChartWatchlistMemberModel.market_reference_id == MarketReferenceModel.id,
            )
            .join(
                MarketDataInstrumentModel,
                MarketDataInstrumentModel.market_reference_id == MarketReferenceModel.id,
            )
            .join(
                ProviderInstrumentMappingModel,
                ProviderInstrumentMappingModel.market_data_instrument_id
                == MarketDataInstrumentModel.id,
            )
            .where(
                ChartWatchlistMemberModel.workspace_id == workspace_id,
                ChartWatchlistMemberModel.setup_completed_at.is_not(None),
                MarketReferenceModel.workspace_id == workspace_id,
                MarketReferenceModel.active.is_(True),
                MarketDataInstrumentModel.workspace_id == workspace_id,
                MarketDataInstrumentModel.kind == "MARKET_REFERENCE",
                MarketDataInstrumentModel.listing_id.is_(None),
                ProviderInstrumentMappingModel.workspace_id == workspace_id,
                ProviderInstrumentMappingModel.provider == MarketDataProvider.EODHD,
                ProviderInstrumentMappingModel.status == MappingStatus.ACTIVE,
                ProviderInstrumentMappingModel.validated_at.is_not(None),
                ProviderInstrumentMappingModel.listing_id.is_(None),
                ChartWatchlistMemberModel.verified_mapping_id == ProviderInstrumentMappingModel.id,
                ChartWatchlistMemberModel.verified_mapping_version
                == ProviderInstrumentMappingModel.version,
                ChartWatchlistMemberModel.verified_provider_symbol
                == ProviderInstrumentMappingModel.provider_symbol,
                ChartWatchlistMemberModel.verified_provider_exchange_code
                == ProviderInstrumentMappingModel.provider_exchange_code,
            )
            .order_by(MarketReferenceModel.id)
        )
    )
    return [
        RefreshInstrument(
            uuid5(workspace_id, f"chart-setup:{member.code}"),
            str(member.definition["name"]),
            member.definition.get("isin"),
            setup_code=member.code,
        )
        for member in pending
    ] + [RefreshInstrument(ref.id, ref.name, None, reference_id=ref.id) for ref in references]
