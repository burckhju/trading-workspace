"""Provider-independent requests and results for market-data capabilities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import UUID

from app.features.market_data.domain.enums import (
    CacheStatus,
    MappingStatus,
    MarketDataCapability,
    MarketDataProvider,
    QualityStatus,
)
from app.features.market_data.domain.errors import InvalidMarketDataValue


def _require_utc(value: datetime, *, field: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise InvalidMarketDataValue(f"{field} must be timezone-aware", field=field)
    if value.utcoffset() != UTC.utcoffset(value):
        raise InvalidMarketDataValue(f"{field} must use UTC", field=field)


@dataclass(frozen=True, slots=True)
class DailyPriceRequest:
    """Request historical EOD prices for one approved provider mapping."""

    workspace_id: UUID
    listing_id: UUID
    mapping_id: UUID
    start_date: date
    end_date: date
    correlation_id: UUID

    def __post_init__(self) -> None:
        if self.end_date < self.start_date:
            raise InvalidMarketDataValue("end_date must not be before start_date", field="end_date")


@dataclass(frozen=True, slots=True)
class WarrantQuoteRequest:
    """Request the best available quote snapshot for one FT-004 WarrantListing."""

    workspace_id: UUID
    warrant_listing_id: UUID
    correlation_id: UUID
    as_of: datetime

    def __post_init__(self) -> None:
        _require_utc(self.as_of, field="as_of")


@dataclass(frozen=True, slots=True)
class LatestDailyPriceRequest:
    """Request the most recent completed EOD price for one provider mapping."""

    workspace_id: UUID
    listing_id: UUID
    mapping_id: UUID
    correlation_id: UUID
    as_of_date: date | None = None


@dataclass(frozen=True, slots=True)
class MarketDataResult[T]:
    """Data plus explicit provenance, cache and provider-consumption metadata."""

    data: T
    provider: MarketDataProvider
    capability: MarketDataCapability
    correlation_id: UUID
    retrieved_at: datetime
    cache_status: CacheStatus
    quality_status: QualityStatus
    warnings: tuple[str, ...]
    retry_count: int
    provider_call_cost: int | None

    def __post_init__(self) -> None:
        _require_utc(self.retrieved_at, field="retrieved_at")
        if self.retry_count < 0:
            raise InvalidMarketDataValue("retry_count must not be negative", field="retry_count")
        if self.provider_call_cost is not None and self.provider_call_cost < 0:
            raise InvalidMarketDataValue(
                "provider_call_cost must not be negative", field="provider_call_cost"
            )
        object.__setattr__(
            self,
            "warnings",
            tuple(message for warning in self.warnings if (message := warning.strip())),
        )


@dataclass(frozen=True, slots=True)
class MappingValidationResult:
    """Provider-independent result of validating an instrument mapping."""

    mapping_id: UUID
    provider: MarketDataProvider
    status: MappingStatus
    validated_at: datetime
    message: str | None = None
    provider_symbol: str | None = None
    provider_exchange_code: str | None = None
    currency: str | None = None

    def __post_init__(self) -> None:
        _require_utc(self.validated_at, field="validated_at")
        if self.message is not None:
            object.__setattr__(self, "message", self.message.strip() or None)
        for field_name in ("provider_symbol", "provider_exchange_code", "currency"):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(self, field_name, value.strip().upper() or None)
