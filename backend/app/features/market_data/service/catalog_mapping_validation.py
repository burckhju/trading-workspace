"""Validate one automatic mapping against catalog evidence and unchanged master data."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.market.domain.enums import LifecycleStatus
from app.features.market.persistence.models import ListingModel, TradingVenueModel, UnderlyingModel
from app.features.market_data.domain.enums import MappingStatus, MarketDataProvider
from app.features.market_data.domain.models import ProviderInstrumentMapping
from app.features.market_data.service.types import MappingValidationResult
from app.providers.eodhd.stock_catalog import StockCatalogIdentity


class CatalogMappingResolver:
    """Use the existing administration validation contract with listing-scoped proof."""

    def __init__(
        self,
        session: AsyncSession,
        workspace_id: UUID,
        listing_id: UUID,
        identity: StockCatalogIdentity,
    ) -> None:
        self._session = session
        self._workspace_id = workspace_id
        self._listing_id = listing_id
        self._identity = identity

    async def validate_mapping(self, mapping: ProviderInstrumentMapping) -> MappingValidationResult:
        proof = self._identity
        item = proof.item
        now = datetime.now(UTC)
        valid = (
            mapping.workspace_id == self._workspace_id
            and mapping.listing_id == self._listing_id
            and mapping.provider == item.provider == MarketDataProvider.EODHD
            and mapping.provider_symbol == item.provider_symbol
            and mapping.provider_exchange_code == item.provider_exchange_code
            and all(
                timedelta(0) <= now - stamp < timedelta(hours=24)
                for stamp in (proof.catalog_retrieved_at, proof.exchanges_retrieved_at)
                + ((proof.search_retrieved_at,) if proof.search_retrieved_at is not None else ())
            )
        )
        valid = valid and (
            (proof.search_endpoint is None and proof.search_retrieved_at is None)
            or (
                proof.search_endpoint == f"/search/{item.isin}"
                and proof.search_retrieved_at is not None
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
                and underlying is not None
                and underlying.workspace_id == self._workspace_id
                and underlying.lifecycle_status == LifecycleStatus.ACTIVE
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
                (
                    _evidence_message(proof)
                    if proof.search_endpoint is not None
                    else json.dumps(
                        {
                            "source": "EODHD_OFFICIAL_STOCK_CATALOG",
                            "endpoint": proof.endpoint,
                            "isin": item.isin,
                            "currency": item.currency,
                            "mic": proof.mic,
                            "provider_identity": item.provider_symbol,
                            "provider_exchange_code": item.provider_exchange_code,
                            "catalog_retrieved_at": proof.catalog_retrieved_at.isoformat(),
                            "exchanges_retrieved_at": proof.exchanges_retrieved_at.isoformat(),
                        },
                        sort_keys=True,
                    )
                )
                if valid
                else "CATALOG_EVIDENCE_EXPIRED_OR_IDENTITY_CHANGED"
            ),
            provider_symbol=item.provider_symbol,
            provider_exchange_code=item.provider_exchange_code,
            currency=item.currency,
        )


def _evidence_message(proof: StockCatalogIdentity) -> str:
    """Compact versioned provenance fits the existing 500-character audit field."""
    item = proof.item
    return json.dumps(
        {
            "source": "EODHD_ISIN_CATALOG_V1",
            "isin": item.isin,
            "ccy": item.currency,
            "mic": proof.mic,
            "symbol": item.provider_symbol,
            "exchange": item.provider_exchange_code,
            "catalog": proof.endpoint,
            "catalog_at": proof.catalog_retrieved_at.isoformat(),
            "exchanges_at": proof.exchanges_retrieved_at.isoformat(),
            "search": proof.search_endpoint,
            "search_at": (
                proof.search_retrieved_at.isoformat() if proof.search_retrieved_at else None
            ),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
