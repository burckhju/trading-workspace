"""Stable application-service errors for FT-001."""

from __future__ import annotations


class ServiceError(RuntimeError):
    code = "SERVICE_ERROR"

    def __init__(self, message: str, *, field: str | None = None) -> None:
        super().__init__(message)
        self.field = field


class WorkspaceNotFound(ServiceError):
    code = "WORKSPACE_NOT_FOUND"


class UnderlyingNotFound(ServiceError):
    code = "UNDERLYING_NOT_FOUND"


class ListingNotFound(ServiceError):
    code = "LISTING_NOT_FOUND"


class TradingVenueNotFound(ServiceError):
    code = "TRADING_VENUE_NOT_FOUND"


class CurrencyNotFound(ServiceError):
    code = "CURRENCY_NOT_FOUND"


class InactiveReferenceData(ServiceError):
    code = "REFERENCE_DATA_INACTIVE"


class DuplicateIsin(ServiceError):
    code = "UNDERLYING_DUPLICATE_ISIN"


class DuplicateWkn(ServiceError):
    code = "UNDERLYING_DUPLICATE_WKN"


class DuplicateMarketTicker(ServiceError):
    code = "LISTING_DUPLICATE_MARKET_TICKER"


class UnderlyingDeleteReferenced(ServiceError):
    code = "UNDERLYING_DELETE_REFERENCED"

    def __init__(self, message: str, *, references: tuple[UsageReference, ...]) -> None:
        super().__init__(message)
        self.references = references


from app.features.market.service.types import UsageReference  # noqa: E402
