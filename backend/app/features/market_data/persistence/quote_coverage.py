"""Batched, workspace-scoped projection of held products and their existing routes."""

from uuid import UUID

from sqlalchemy import select

from app.database.manager import DatabaseManager
from app.features.market.persistence.models import CurrencyModel, IssuerModel, TradingVenueModel
from app.features.market_data.domain.enums import MarketDataProvider
from app.features.market_data.persistence.models import (
    WarrantProviderMappingModel,
    WarrantQuoteObservationModel,
)
from app.features.market_data.persistence.quote_identity import verified_identity
from app.features.market_data.service.quote_coverage import ProductRecord, RouteRecord
from app.features.product.persistence.models import WarrantListingModel, WarrantModel
from app.features.trade_position.persistence.models import PositionModel, TradeModel
from app.providers.vontobel_markets.issuer import supports_issuer_probe


class QuoteCoverageRepository:
    def __init__(self, database: DatabaseManager) -> None:
        self.database = database

    async def held_products(self, workspace_id: UUID) -> tuple[ProductRecord, ...]:
        held = (
            select(PositionModel.product_id)
            .join(TradeModel, TradeModel.id == PositionModel.trade_id)
            .where(
                TradeModel.workspace_id == workspace_id,
                TradeModel.product_id == PositionModel.product_id,
                TradeModel.cancelled_at.is_(None),
                PositionModel.open_quantity > 0,
                PositionModel.closed_at.is_(None),
            )
        )
        async with self.database.session_context() as session:
            products = (
                await session.execute(
                    select(WarrantModel, IssuerModel)
                    .join(IssuerModel, IssuerModel.id == WarrantModel.issuer_id)
                    .where(WarrantModel.workspace_id == workspace_id, WarrantModel.id.in_(held))
                    .order_by(IssuerModel.legal_name, WarrantModel.display_name, WarrantModel.id)
                )
            ).all()
            if not products:
                return ()
            listings = (
                await session.execute(
                    select(WarrantListingModel, TradingVenueModel, CurrencyModel.is_active)
                    .outerjoin(
                        TradingVenueModel,
                        TradingVenueModel.id == WarrantListingModel.trading_venue_id,
                    )
                    .outerjoin(
                        CurrencyModel,
                        CurrencyModel.code == WarrantListingModel.quotation_currency_code,
                    )
                    .where(
                        WarrantListingModel.workspace_id == workspace_id,
                        WarrantListingModel.warrant_id.in_([w.id for w, _ in products]),
                    )
                    .order_by(WarrantListingModel.id)
                )
            ).all()
            ids = [listing.id for listing, _, _ in listings]
            mappings = (
                (
                    await session.execute(
                        select(WarrantProviderMappingModel).where(
                            WarrantProviderMappingModel.workspace_id == workspace_id,
                            WarrantProviderMappingModel.warrant_listing_id.in_(ids),
                        )
                    )
                )
                .scalars()
                .all()
            )
            observations = (
                (
                    await session.execute(
                        select(WarrantQuoteObservationModel).where(
                            WarrantQuoteObservationModel.workspace_id == workspace_id,
                            WarrantQuoteObservationModel.warrant_listing_id.in_(ids),
                        )
                    )
                )
                .scalars()
                .all()
            )
            mapping_index = {(m.warrant_listing_id, m.provider.value): m for m in mappings}
            observation_index = {(o.warrant_listing_id, o.provider): o for o in observations}
            listing_index: dict[
                UUID, list[tuple[WarrantListingModel, TradingVenueModel | None, bool | None]]
            ] = {}
            providers_by_listing: dict[UUID, set[MarketDataProvider]] = {}
            for listing, venue, currency_active in listings:
                listing_index.setdefault(listing.warrant_id, []).append(
                    (listing, venue, currency_active)
                )
            for known_mapping in mappings:
                providers_by_listing.setdefault(known_mapping.warrant_listing_id, set()).add(
                    known_mapping.provider
                )
            result = []
            for warrant, issuer in products:
                routes = []
                for listing, venue, currency_active in listing_index.get(warrant.id, []):
                    names = set(providers_by_listing.get(listing.id, set()))
                    if venue is not None and venue.mic == "XFRA":
                        names.add(MarketDataProvider.FRANKFURT_QUOTES)
                    if venue is not None and venue.mic == "XSTU":
                        names.add(MarketDataProvider.BOERSE_STUTTGART_DELAYED)
                    if supports_issuer_probe(issuer.legal_name):
                        names.add(MarketDataProvider.VONTOBEL_MARKETS)
                    for provider in sorted(names):
                        mapping = mapping_index.get((listing.id, provider.value))
                        observation = observation_index.get((listing.id, provider.value))
                        identity = (
                            verified_identity(
                                workspace_id, listing, warrant, venue, provider, mapping
                            )
                            if venue is not None
                            else None
                        )
                        reason = (
                            "ROUTE_IDENTITY_VERIFIED" if identity else "VALIDATED_MAPPING_REQUIRED"
                        )
                        if (
                            listing.lifecycle_status != "ACTIVE"
                            or venue is None
                            or not venue.is_active
                        ):
                            reason = "LISTING_OR_VENUE_INACTIVE"
                        elif not currency_active:
                            reason = "QUOTE_CURRENCY_INACTIVE"
                        elif not warrant.isin:
                            reason = "ISIN_REQUIRED"
                        elif mapping is not None and mapping.status != "ACTIVE":
                            reason = "MAPPING_" + mapping.status.value
                        elif identity is None and mapping is not None:
                            reason = "MAPPING_IDENTITY_UNVERIFIED"
                        if reason != "ROUTE_IDENTITY_VERIFIED":
                            identity = None
                        routes.append(
                            RouteRecord(
                                provider.value,
                                listing.id,
                                venue.mic if venue else "UNKNOWN",
                                listing.quotation_currency_code,
                                mapping.id if mapping else None,
                                mapping.status.value if mapping else None,
                                (
                                    mapping.provider_symbol
                                    if mapping
                                    else warrant.isin if identity else None
                                ),
                                (
                                    mapping.provider_exchange_code
                                    if mapping
                                    else identity.exchange if identity else None
                                ),
                                mapping.validated_at if mapping else None,
                                reason,
                                identity.key if identity else None,
                                observation.identity_key if observation else None,
                                observation.payload if observation else None,
                            )
                        )
                result.append(
                    ProductRecord(
                        warrant.id,
                        warrant.display_name,
                        warrant.isin,
                        warrant.wkn,
                        issuer.legal_name,
                        warrant.lifecycle_status == "ACTIVE" and issuer.is_active,
                        supports_issuer_probe(issuer.legal_name),
                        tuple(routes),
                    )
                )
            return tuple(result)
