"""Stable provider-independent application errors for market-data access."""

from __future__ import annotations

from datetime import timedelta

from app.features.market_data.domain.enums import (
    MarketDataCapability,
    MarketDataProvider,
)


class MarketDataError(RuntimeError):
    """Base error exposed by provider-independent market-data services."""

    code = "MARKET_DATA_ERROR"

    def __init__(
        self,
        message: str,
        *,
        provider: MarketDataProvider | None = None,
        capability: MarketDataCapability | None = None,
        retryable: bool = False,
        retry_after: timedelta | None = None,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.capability = capability
        self.retryable = retryable
        self.retry_after = retry_after


class MarketDataConfigurationError(MarketDataError):
    """Required provider configuration is absent or invalid."""

    code = "MARKET_DATA_CONFIGURATION_ERROR"


class MarketDataAuthenticationError(MarketDataError):
    """The provider rejected the configured credentials."""

    code = "MARKET_DATA_AUTHENTICATION_ERROR"


class MarketDataAuthorizationError(MarketDataError):
    """The provider account is not entitled to the requested capability."""

    code = "MARKET_DATA_AUTHORIZATION_ERROR"


class MarketDataRateLimitError(MarketDataError):
    """A local budget or provider rate limit prevents the request."""

    code = "MARKET_DATA_RATE_LIMIT_ERROR"


class MarketDataBudgetExhaustedError(MarketDataError):
    """The configured daily provider-call budget has been exhausted."""

    code = "MARKET_DATA_BUDGET_EXHAUSTED"


class MarketDataTimeoutError(MarketDataError):
    """The provider request exceeded its allowed duration."""

    code = "MARKET_DATA_TIMEOUT_ERROR"


class MarketDataUnavailableError(MarketDataError):
    """The provider is temporarily unavailable."""

    code = "MARKET_DATA_UNAVAILABLE_ERROR"


class MarketDataNotFoundError(MarketDataError):
    """No provider instrument or market-data record matches the request."""

    code = "MARKET_DATA_NOT_FOUND"


class MarketDataInvalidResponseError(MarketDataError):
    """The provider returned a structurally invalid or contradictory response."""

    code = "MARKET_DATA_INVALID_RESPONSE"


class MarketDataMappingError(MarketDataError):
    """Provider values cannot be mapped safely to internal models."""

    code = "MARKET_DATA_MAPPING_ERROR"


class MarketDataCurrencyConflictError(MarketDataError):
    """Provider and listing currencies do not agree."""

    code = "MARKET_DATA_CURRENCY_CONFLICT"
