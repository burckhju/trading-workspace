"""Bind live ETF evidence and reviewed segment identity to one unchanged listing."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.market.domain.enums import LifecycleStatus, UnderlyingType
from app.features.market.persistence.models import ListingModel, TradingVenueModel, UnderlyingModel
from app.features.market_data.domain.enums import MappingStatus, MarketDataProvider
from app.features.market_data.domain.models import ProviderInstrumentMapping
from app.features.market_data.service.types import MappingValidationResult
from app.providers.eodhd.etf_catalog import EtfCatalogIdentity


class EtfCatalogMappingResolver:
    def __init__(
        self,
        session: AsyncSession,
        workspace_id: UUID,
        listing_id: UUID,
        identity: EtfCatalogIdentity,
    ) -> None:
        self._session = session
        self._workspace_id = workspace_id
        self._listing_id = listing_id
        self._identity = identity

    async def validate_mapping(self, mapping: ProviderInstrumentMapping) -> MappingValidationResult:
        proof = self._identity
        item = proof.item
        now = datetime.now(UTC)
        stamps = (proof.catalog_retrieved_at, proof.exchanges_retrieved_at) + (
            (proof.search_retrieved_at,) if proof.search_retrieved_at is not None else ()
        )
        valid = (
            mapping.workspace_id == self._workspace_id
            and mapping.listing_id == self._listing_id
            and mapping.provider == item.provider == MarketDataProvider.EODHD
            and mapping.provider_symbol == item.provider_symbol == proof.listing_ticker
            and mapping.provider_exchange_code == item.provider_exchange_code == "US"
            and (item.instrument_type or "").upper() == "ETF"
            and proof.endpoint == "/exchange-symbol-list/US"
            and (proof.mic, proof.provider_venue) in {("ARCX", "NYSE ARCA"), ("XNMS", "NASDAQ")}
            and proof.listing_reviewed_on <= now.date()
            and all(timedelta(0) <= now - stamp < timedelta(hours=24) for stamp in stamps)
            and (
                (proof.search_endpoint is None and proof.search_retrieved_at is None)
                or (
                    proof.search_endpoint == f"/search/{item.isin}"
                    and proof.search_retrieved_at is not None
                )
            )
        )
        listing = await self._session.get(ListingModel, self._listing_id, populate_existing=True)
        if listing is None:
            valid = False
        else:
            underlying = await self._session.get(
                UnderlyingModel, listing.underlying_id, populate_existing=True
            )
            venue = await self._session.get(
                TradingVenueModel, listing.trading_venue_id, populate_existing=True
            )
            valid = valid and (
                listing.workspace_id == self._workspace_id
                and listing.lifecycle_status == LifecycleStatus.ACTIVE
                and listing.currency_code == item.currency
                and listing.ticker == proof.listing_ticker
                and underlying is not None
                and underlying.workspace_id == self._workspace_id
                and underlying.lifecycle_status == LifecycleStatus.ACTIVE
                and underlying.type == UnderlyingType.ETF
                and underlying.isin == item.isin
                and venue is not None
                and venue.is_active
                and venue.mic == proof.mic
            )
        return MappingValidationResult(
            mapping.id,
            MarketDataProvider.EODHD,
            MappingStatus.ACTIVE if valid else MappingStatus.INVALID,
            now,
            message=(
                _evidence_message(proof)
                if valid
                else "ETF_EVIDENCE_EXPIRED_OR_LISTING_IDENTITY_CHANGED"
            ),
            provider_symbol=item.provider_symbol,
            provider_exchange_code=item.provider_exchange_code,
            currency=item.currency,
        )


def _evidence_message(proof: EtfCatalogIdentity) -> str:
    # Full URLs remain in the immutable membership definition. Link that exact
    # listing evidence without exceeding the owner's existing 500-char field.
    listing_evidence = "\n".join(
        (
            proof.listing_source_url,
            proof.venue_source_url,
            proof.listing_reviewed_on.isoformat(),
            proof.listing_ticker,
            proof.mic,
        )
    )
    return json.dumps(
        {
            "source": "EODHD_ETF_AND_REVIEWED_LISTING_V1",
            "isin": proof.item.isin,
            "ccy": proof.item.currency,
            "mic": proof.mic,
            "venue": proof.provider_venue,
            "symbol": proof.item.provider_symbol,
            "exchange": proof.item.provider_exchange_code,
            "catalog_at": proof.catalog_retrieved_at.isoformat(),
            "exchanges_at": proof.exchanges_retrieved_at.isoformat(),
            "search_at": (
                proof.search_retrieved_at.isoformat() if proof.search_retrieved_at else None
            ),
            "listing_sha256": hashlib.sha256(listing_evidence.encode()).hexdigest(),
        },
        separators=(",", ":"),
        sort_keys=True,
    )
