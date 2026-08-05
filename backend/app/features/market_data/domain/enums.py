"""Stable provider-independent enum values for market data."""

from enum import StrEnum


class MarketDataProvider(StrEnum):
    """Supported external market-data providers."""

    EODHD = "EODHD"


class MarketDataCapability(StrEnum):
    """Independently implementable provider capabilities."""

    HISTORICAL_DAILY_PRICES = "HISTORICAL_DAILY_PRICES"
    LATEST_COMPLETED_DAILY_PRICE = "LATEST_COMPLETED_DAILY_PRICE"
    INSTRUMENT_MAPPING_VALIDATION = "INSTRUMENT_MAPPING_VALIDATION"


class MappingStatus(StrEnum):
    """Lifecycle state of a provider instrument mapping."""

    ACTIVE = "ACTIVE"
    INVALID = "INVALID"
    DISABLED = "DISABLED"


class QualityStatus(StrEnum):
    """Explicit quality assessment of returned market data."""

    VALID = "VALID"
    INCOMPLETE = "INCOMPLETE"
    SUSPICIOUS = "SUSPICIOUS"


class CacheStatus(StrEnum):
    """Technical cache outcome attached to a market-data result."""

    HIT = "HIT"
    MISS = "MISS"
    BYPASS = "BYPASS"
    STALE_REJECTED = "STALE_REJECTED"


class PriceType(StrEnum):
    """Market-data price granularity persisted by the application."""

    EOD = "EOD"
