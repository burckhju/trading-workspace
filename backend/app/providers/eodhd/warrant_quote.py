"""EODHD boundary for FT-008 warrant quotes.

EODHD's documented extended bid/ask REST quote capability is US-equity-specific.
The released FT-004 product in this repository is Warrant/WarrantListing, so wiring
that endpoint as if it were a supported warrant feed would be an invalid provider
assumption.  Keep the adapter explicit and fail closed until an entitlement/endpoint
for the actual WarrantListing universe is verified.
"""

from __future__ import annotations

from app.features.market_data.domain.enums import MarketDataCapability, MarketDataProvider
from app.features.market_data.domain.models import WarrantQuoteSnapshot
from app.features.market_data.service.errors import MarketDataConfigurationError
from app.features.market_data.service.types import MarketDataResult, WarrantQuoteRequest


class EodhdWarrantQuoteAdapter:
    """Fail-closed EODHD adapter until warrant bid/ask coverage is verified."""

    async def get_warrant_listing_quote(
        self, request: WarrantQuoteRequest
    ) -> MarketDataResult[WarrantQuoteSnapshot | None]:
        raise MarketDataConfigurationError(
            "EODHD warrant bid/ask transport is not enabled: the documented extended "
            "bid/ask REST quote capability is US-equity-specific and must not be "
            "assumed to cover FT-004 WarrantListings",
            provider=MarketDataProvider.EODHD,
            capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
            retryable=False,
        )
