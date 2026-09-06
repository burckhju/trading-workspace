from __future__ import annotations

from app.features.market_data.domain.enums import MarketDataCapability, MarketDataProvider
from app.features.market_data.domain.models import WarrantQuoteSnapshot
from app.features.market_data.service.errors import MarketDataConfigurationError
from app.features.market_data.service.types import MarketDataResult, WarrantQuoteRequest


class UnavailableWarrantQuoteAdapter:
    """Named provider slot that fails closed until a transport/schema is verified."""

    def __init__(self, *, reason: str) -> None:
        self._reason = reason

    async def get_warrant_listing_quote(
        self, request: WarrantQuoteRequest
    ) -> MarketDataResult[WarrantQuoteSnapshot | None]:
        del request
        raise MarketDataConfigurationError(
            self._reason,
            provider=MarketDataProvider.EODHD,
            capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
            retryable=False,
        )
