"""Translate market-data service failures into the stable application error contract."""

from fastapi import status

from app.core.exceptions import ApplicationError, ErrorDetail
from app.features.market_data.service.errors import (
    MarketDataAuthenticationError,
    MarketDataAuthorizationError,
    MarketDataBudgetExhaustedError,
    MarketDataConfigurationError,
    MarketDataCurrencyConflictError,
    MarketDataError,
    MarketDataInvalidResponseError,
    MarketDataMappingError,
    MarketDataNotFoundError,
    MarketDataRateLimitError,
    MarketDataTimeoutError,
    MarketDataUnavailableError,
)


def translate_market_data_error(error: MarketDataError) -> ApplicationError:
    """Map provider-independent failures to safe HTTP semantics."""
    status_code = status.HTTP_502_BAD_GATEWAY
    if isinstance(error, MarketDataNotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(error, (MarketDataConfigurationError, MarketDataAuthenticationError)):
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif isinstance(error, MarketDataAuthorizationError):
        status_code = status.HTTP_403_FORBIDDEN
    elif isinstance(error, (MarketDataRateLimitError, MarketDataBudgetExhaustedError)):
        status_code = status.HTTP_429_TOO_MANY_REQUESTS
    elif isinstance(error, (MarketDataTimeoutError, MarketDataUnavailableError)):
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif isinstance(
        error,
        (
            MarketDataMappingError,
            MarketDataCurrencyConflictError,
            MarketDataInvalidResponseError,
        ),
    ):
        status_code = status.HTTP_502_BAD_GATEWAY

    details: tuple[ErrorDetail, ...] = ()
    if error.retry_after is not None:
        details = (
            ErrorDetail(
                field=None,
                message="Retry may be attempted later.",
                context={"retry_after_seconds": error.retry_after.total_seconds()},
            ),
        )
    return ApplicationError(
        code=error.code,
        message=str(error),
        status_code=status_code,
        details=details,
    )
