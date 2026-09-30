"""Shared current route identity for retained prices and read-only diagnostics."""

import hashlib
import re
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.market.persistence.models import TradingVenueModel
from app.features.market_data.domain.enums import MappingStatus, MarketDataProvider
from app.features.market_data.domain.issuer_route_evidence import evidence_stream_id
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
    stream_id: str | None = None


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
    stream_id = None
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
        if name in {MarketDataProvider.JPMORGAN, MarketDataProvider.MORGAN_STANLEY}:
            from app.providers.jpmorgan.products import INSTRUMENTS
            from app.providers.morganstanley.products import ELIGIBLE_INSTRUMENTS, EXCLUDED_PRODUCTS

            known = INSTRUMENTS if name == MarketDataProvider.JPMORGAN else ELIGIBLE_INSTRUMENTS
            if (
                exchange != "ISSUER"
                or listing.quotation_currency_code != "EUR"
                or (warrant.wkn is not None and warrant.wkn != warrant.isin[5:11])
                or (name == MarketDataProvider.MORGAN_STANLEY and warrant.isin in EXCLUDED_PRODUCTS)
            ):
                return None
            evidence = getattr(mapping, "identity_evidence", None)
            if evidence is None and warrant.isin in known:
                # Preserve fingerprints for the previously verified fixed routes.
                stream_id = known[warrant.isin]
            else:
                stream_id = evidence_stream_id(
                    evidence,
                    provider=name.value,
                    isin=warrant.isin,
                    currency=listing.quotation_currency_code,
                    workspace_id=str(workspace_id),
                    warrant_id=str(warrant.id),
                    warrant_version=warrant.version,
                    listing_id=str(listing.id),
                    listing_version=listing.version,
                    mapping_version=mapping.version,
                )
                if stream_id is None or not isinstance(evidence, dict):
                    return None
                fingerprint.extend([stream_id, evidence["source_sha256"]])
        if name == MarketDataProvider.VONTOBEL_MARKETS and exchange != "ISSUER":
            return None
        if name == MarketDataProvider.FRANKFURT_QUOTES and (
            venue.mic != "XFRA" or exchange not in {"XSC", "XFRA"}
        ):
            return None
        if name == MarketDataProvider.GETTEX_DELAYED and (
            exchange not in {"MUND", "MUNC"} or venue.mic != exchange
        ):
            return None
        fingerprint.extend([str(mapping.id), str(mapping.version), exchange])
    return QuoteIdentity(
        hashlib.sha256("|".join(fingerprint).encode()).hexdigest(),
        warrant.isin,
        warrant.wkn,
        listing.quotation_currency_code,
        exchange,
        venue.mic,
        stream_id,
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
    if mapping is not None and mapping.identity_evidence is not None:
        # Dynamic route evidence cannot authorize prices after reference deactivation.
        from app.features.market.persistence.models import CurrencyModel, IssuerModel
        from app.providers.issuer_pages import provider_for_issuer

        issuer = await session.get(IssuerModel, warrant.issuer_id)
        currency = await session.get(CurrencyModel, listing.quotation_currency_code)
        if (
            issuer is None
            or not issuer.is_active
            or provider_for_issuer(issuer.legal_name) != name.value
            or currency is None
            or not currency.is_active
        ):
            return None
    return verified_identity(request.workspace_id, listing, warrant, venue, name, mapping)
