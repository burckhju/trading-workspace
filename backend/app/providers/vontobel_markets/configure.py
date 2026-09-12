"""Idempotent issuer mapping from verified product evidence and existing listings."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.market.persistence.models import IssuerModel, TradingVenueModel
from app.features.market_data.domain.enums import MappingStatus, MarketDataProvider
from app.features.market_data.persistence.models import WarrantProviderMappingModel
from app.features.product.domain.models import WarrantLifecycle
from app.features.product.persistence.models import WarrantListingModel, WarrantModel
from app.providers.vontobel_markets.adapter import (
    VontobelIdentity,
    VontobelMarketsWarrantQuoteAdapter,
)


async def configure_warrant(
    session: AsyncSession,
    adapter: VontobelMarketsWarrantQuoteAdapter,
    *,
    workspace_id: UUID,
    warrant_id: UUID,
) -> UUID:
    """Issuer name selects a probe; only matching ISIN/WKN/currency validates it."""
    warrant = await session.scalar(
        select(WarrantModel)
        .where(WarrantModel.id == warrant_id, WarrantModel.workspace_id == workspace_id)
        .with_for_update()
    )
    if warrant is None or warrant.lifecycle_status != WarrantLifecycle.ACTIVE or not warrant.isin:
        raise ValueError("ACTIVE_WARRANT_ISIN_REQUIRED")
    issuer = await session.get(IssuerModel, warrant.issuer_id)
    if issuer is None or not issuer.is_active or "vontobel" not in issuer.legal_name.lower():
        raise ValueError("ISSUER_NOT_SUPPORTED_BY_VONTOBEL")
    listings = list(
        await session.scalars(
            select(WarrantListingModel)
            .join(TradingVenueModel, TradingVenueModel.id == WarrantListingModel.trading_venue_id)
            .where(
                WarrantListingModel.workspace_id == workspace_id,
                WarrantListingModel.warrant_id == warrant_id,
                WarrantListingModel.lifecycle_status == WarrantLifecycle.ACTIVE,
                TradingVenueModel.is_active.is_(True),
            )
            .order_by(WarrantListingModel.id)
        )
    )
    if not listings or len({row.quotation_currency_code for row in listings}) != 1:
        raise ValueError("ACTIVE_UNAMBIGUOUS_QUOTE_CURRENCY_REQUIRED")
    mappings = list(
        await session.scalars(
            select(WarrantProviderMappingModel).where(
                WarrantProviderMappingModel.provider == MarketDataProvider.VONTOBEL_MARKETS,
                or_(
                    WarrantProviderMappingModel.warrant_listing_id.in_(
                        [row.id for row in listings]
                    ),
                    WarrantProviderMappingModel.provider_symbol == warrant.isin,
                ),
            )
        )
    )
    if mappings:
        if len(mappings) != 1:
            raise ValueError("VONTOBEL_MAPPING_CONFLICT")
        existing = mappings[0]
        if (
            existing.workspace_id != workspace_id
            or existing.warrant_listing_id not in {row.id for row in listings}
            or existing.provider_symbol != warrant.isin
            or existing.provider_exchange_code != "ISSUER"
            or existing.status != MappingStatus.ACTIVE
            or existing.validated_at is None
        ):
            raise ValueError("VONTOBEL_MAPPING_CONFLICT")
        return existing.warrant_listing_id
    listing = listings[0]
    quote, retrieved_at, _ = await adapter.probe(
        VontobelIdentity(
            listing.id,
            warrant.isin,
            warrant.wkn,
            listing.quotation_currency_code,
            warrant.isin,
            "ISSUER",
        )
    )
    if (
        quote is None
        or quote.bid is None
        or quote.observed_at is None
        or quote.observed_at > datetime.now(UTC)
    ):
        raise ValueError("VONTOBEL_VERIFIED_BID_REQUIRED")
    session.add(
        WarrantProviderMappingModel(
            id=uuid4(),
            workspace_id=workspace_id,
            warrant_listing_id=listing.id,
            provider=MarketDataProvider.VONTOBEL_MARKETS,
            provider_symbol=warrant.isin,
            provider_exchange_code="ISSUER",
            status=MappingStatus.ACTIVE,
            validated_at=retrieved_at,
            validation_message=(
                "Automatic exact ISIN/WKN/currency verification against "
                "official issuer payload; indicative only"
            ),
            version=1,
            created_at=retrieved_at,
            updated_at=retrieved_at,
        )
    )
    await session.flush()
    await session.commit()
    return listing.id
