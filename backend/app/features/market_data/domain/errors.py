"""Provider-independent domain errors for market data."""

from __future__ import annotations


class MarketDataDomainError(ValueError):
    """Base class for violations of internal market-data rules."""

    code = "MARKET_DATA_DOMAIN_ERROR"

    def __init__(self, message: str, *, field: str | None = None) -> None:
        super().__init__(message)
        self.field = field


class InvalidMarketDataValue(MarketDataDomainError):
    """Raised when a primitive market-data value cannot be normalized."""

    code = "MARKET_DATA_INVALID_VALUE"


class InvalidDailyPrice(MarketDataDomainError):
    """Raised when a daily price violates OHLC or value invariants."""

    code = "MARKET_DATA_INVALID_DAILY_PRICE"


class InvalidProviderInstrumentMapping(MarketDataDomainError):
    """Raised when a provider instrument mapping is internally inconsistent."""

    code = "MARKET_DATA_INVALID_PROVIDER_MAPPING"
