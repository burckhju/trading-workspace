"""Shared current route identity for retained prices and read-only diagnostics."""

import hashlib
import re
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.market.persistence.models import TradingVenueModel
from app.features.market_data.domain.enums import MappingStatus, MarketDataProvider
from app.features.market_data.persistence.models import WarrantProviderMappingModel
from app.features.market_data.service.types import WarrantQuoteRequest
from app.features.product.domain.models import WarrantLifecycle
from app.features.product.persistence.models import WarrantListingModel, WarrantModel


@dataclass(frozen=True)
class QuoteIdentity:
    key: str
    isin: str
    wkn: str | None
    currency: str
    exchange: str
    mic: str


def verified_identity(
    workspace_id: UUID,
    listing: WarrantListingModel,
    warrant: WarrantModel,
    venue: TradingVenueModel,
    name: MarketDataProvider,
    mapping: WarrantProviderMappingModel | None,
) -> QuoteIdentity | None:
    """No network, SQL or mutation; preserve the existing fingerprint contract."""
    if (
        listing.workspace_id != workspace_id
        or warrant.workspace_id != workspace_id
        or listing.warrant_id != warrant.id
        or listing.trading_venue_id != venue.id
        or listing.lifecycle_status != WarrantLifecycle.ACTIVE
        or warrant.lifecycle_status != WarrantLifecycle.ACTIVE
        or not venue.is_active
        or not warrant.isin
        or not re.fullmatch(r"[A-Z0-9]{12}", warrant.isin)
    ):
        return None
    fingerprint = [
        str(workspace_id),
        str(warrant.id),
        str(warrant.version),
        str(listing.id),
        str(listing.version),
        venue.mic,
        warrant.isin,
        warrant.wkn or "",
        listing.quotation_currency_code,
        name.value,
    ]
    if name == MarketDataProvider.BOERSE_STUTTGART_DELAYED:
        if venue.mic != "XSTU":
            return None
        exchange = "XSTU"
    else:
        if (
            mapping is None
            or mapping.workspace_id != workspace_id
            or mapping.warrant_listing_id != listing.id
            or mapping.provider != name
            or mapping.status != MappingStatus.ACTIVE
            or mapping.validated_at is None
            or mapping.provider_symbol != warrant.isin
        ):
            return None
        exchange = mapping.provider_exchange_code
        if name == MarketDataProvider.VONTOBEL_MARKETS and exchange != "ISSUER":
            return None
        if name == MarketDataProvider.FRANKFURT_QUOTES and (
            venue.mic != "XFRA" or exchange not in {"XSC", "XFRA"}
        ):
            return None
        if name == MarketDataProvider.GETTEX_DELAYED and exchange not in {"MUND", "MUNC"}:
            return None
        fingerprint.extend([str(mapping.id), str(mapping.version), exchange])
    return QuoteIdentity(
        hashlib.sha256("|".join(fingerprint).encode()).hexdigest(),
        warrant.isin,
        warrant.wkn,
        listing.quotation_currency_code,
        exchange,
        venue.mic,
    )


async def read_quote_identity(
    session: AsyncSession, request: WarrantQuoteRequest, name: MarketDataProvider
) -> QuoteIdentity | None:
    row = (
        await session.execute(
            select(WarrantListingModel, WarrantModel, TradingVenueModel)
            .join(WarrantModel, WarrantModel.id == WarrantListingModel.warrant_id)
            .join(TradingVenueModel, TradingVenueModel.id == WarrantListingModel.trading_venue_id)
            .where(
                WarrantListingModel.id == request.warrant_listing_id,
                WarrantListingModel.workspace_id == request.workspace_id,
                WarrantModel.workspace_id == request.workspace_id,
                WarrantListingModel.lifecycle_status == WarrantLifecycle.ACTIVE,
                WarrantModel.lifecycle_status == WarrantLifecycle.ACTIVE,
                TradingVenueModel.is_active.is_(True),
            )
        )
    ).one_or_none()
    if row is None:
        return None
    listing, warrant, venue = row
    mapping = None
    if name != MarketDataProvider.BOERSE_STUTTGART_DELAYED:
        mapping = await session.scalar(
            select(WarrantProviderMappingModel).where(
                WarrantProviderMappingModel.workspace_id == request.workspace_id,
                WarrantProviderMappingModel.warrant_listing_id == listing.id,
                WarrantProviderMappingModel.provider == name,
                WarrantProviderMappingModel.status == MappingStatus.ACTIVE,
                WarrantProviderMappingModel.validated_at.is_not(None),
            )
        )
    return verified_identity(request.workspace_id, listing, warrant, venue, name, mapping)
