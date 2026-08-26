"""Immutable internal market-data models independent of every provider."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID

from app.features.market_data.domain.enums import (
    MappingStatus,
    MarketDataProvider,
    PriceType,
    QualityStatus,
)
from app.features.market_data.domain.errors import (
    InvalidDailyPrice,
    InvalidMarketDataValue,
    InvalidProviderInstrumentMapping,
)


def _require_utc(value: datetime, *, field: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise InvalidMarketDataValue(f"{field} must be timezone-aware", field=field)
    if value.utcoffset() != UTC.utcoffset(value):
        raise InvalidMarketDataValue(f"{field} must use UTC", field=field)
    return value


def _normalize_code(value: str, *, field: str) -> str:
    normalized = value.strip().upper()
    if not normalized:
        raise InvalidMarketDataValue(f"{field} must not be blank", field=field)
    return normalized


def _normalize_message(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _decimal(value: Decimal | str | int, *, field: str) -> Decimal:
    if isinstance(value, float):
        raise InvalidMarketDataValue(f"{field} must not use binary floating-point", field=field)
    try:
        normalized = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise InvalidMarketDataValue(f"{field} must be a decimal value", field=field) from exc
    if not normalized.is_finite():
        raise InvalidMarketDataValue(f"{field} must be finite", field=field)
    return normalized


@dataclass(frozen=True, slots=True)
class ProviderInstrumentMapping:
    """Approved association between one internal market-data owner and a provider symbol."""

    id: UUID
    workspace_id: UUID
    listing_id: UUID | None
    provider: MarketDataProvider
    provider_symbol: str
    provider_exchange_code: str
    status: MappingStatus
    validated_at: datetime | None
    validation_message: str | None
    created_at: datetime
    updated_at: datetime
    version: int
    market_data_instrument_id: UUID | None = None

    def __post_init__(self) -> None:
        if self.listing_id is None and self.market_data_instrument_id is None:
            raise InvalidProviderInstrumentMapping(
                "mapping requires a listing or market-data instrument owner",
                field="listing_id",
            )
        object.__setattr__(
            self,
            "provider_symbol",
            _normalize_code(self.provider_symbol, field="provider_symbol"),
        )
        object.__setattr__(
            self,
            "provider_exchange_code",
            _normalize_code(self.provider_exchange_code, field="provider_exchange_code"),
        )
        object.__setattr__(self, "validation_message", _normalize_message(self.validation_message))
        _require_utc(self.created_at, field="created_at")
        _require_utc(self.updated_at, field="updated_at")
        if self.validated_at is not None:
            _require_utc(self.validated_at, field="validated_at")
        if self.version < 1:
            raise InvalidProviderInstrumentMapping("version must be at least 1", field="version")
        if self.updated_at < self.created_at:
            raise InvalidProviderInstrumentMapping(
                "updated_at must not be before created_at", field="updated_at"
            )
        if self.validated_at is not None and self.validated_at < self.created_at:
            raise InvalidProviderInstrumentMapping(
                "validated_at must not be before created_at", field="validated_at"
            )
        if self.status is MappingStatus.ACTIVE and self.validated_at is None:
            raise InvalidProviderInstrumentMapping(
                "active mappings require validated_at", field="validated_at"
            )


@dataclass(frozen=True, slots=True)
class WarrantProviderMapping:
    """Approved provider association for one FT-004 WarrantListing.

    This is intentionally separate from ProviderInstrumentMapping, whose listing_id
    belongs to the released FT-001 Listing aggregate.
    """

    id: UUID
    workspace_id: UUID
    warrant_listing_id: UUID
    provider: MarketDataProvider
    provider_symbol: str
    provider_exchange_code: str
    status: MappingStatus
    validated_at: datetime | None
    validation_message: str | None
    created_at: datetime
    updated_at: datetime
    version: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "provider_symbol", _normalize_code(self.provider_symbol, field="provider_symbol")
        )
        object.__setattr__(
            self,
            "provider_exchange_code",
            _normalize_code(self.provider_exchange_code, field="provider_exchange_code"),
        )
        object.__setattr__(self, "validation_message", _normalize_message(self.validation_message))
        _require_utc(self.created_at, field="created_at")
        _require_utc(self.updated_at, field="updated_at")
        if self.validated_at is not None:
            _require_utc(self.validated_at, field="validated_at")
        if self.version < 1:
            raise InvalidProviderInstrumentMapping("version must be at least 1", field="version")
        if self.updated_at < self.created_at:
            raise InvalidProviderInstrumentMapping(
                "updated_at must not be before created_at", field="updated_at"
            )
        if self.status is MappingStatus.ACTIVE and self.validated_at is None:
            raise InvalidProviderInstrumentMapping(
                "active mappings require validated_at", field="validated_at"
            )


@dataclass(frozen=True, slots=True)
class DailyPrice:
    """Validated provider-independent EOD price for one FT-001 Listing."""

    listing_id: UUID
    trading_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    adjusted_close: Decimal | None
    volume: Decimal | None
    currency: str
    provider: MarketDataProvider
    provider_symbol: str
    retrieved_at: datetime
    source_updated_at: datetime | None
    quality_status: QualityStatus
    warnings: tuple[str, ...] = ()
    price_type: PriceType = PriceType.EOD
    market_data_instrument_id: UUID | None = None

    def __post_init__(self) -> None:
        for field in ("open", "high", "low", "close"):
            object.__setattr__(self, field, _decimal(getattr(self, field), field=field))
        if self.adjusted_close is not None:
            object.__setattr__(
                self,
                "adjusted_close",
                _decimal(self.adjusted_close, field="adjusted_close"),
            )
        if self.volume is not None:
            object.__setattr__(self, "volume", _decimal(self.volume, field="volume"))
        object.__setattr__(self, "currency", _normalize_code(self.currency, field="currency"))
        object.__setattr__(
            self,
            "provider_symbol",
            _normalize_code(self.provider_symbol, field="provider_symbol"),
        )
        object.__setattr__(
            self,
            "warnings",
            tuple(message for warning in self.warnings if (message := warning.strip())),
        )
        _require_utc(self.retrieved_at, field="retrieved_at")
        if self.source_updated_at is not None:
            _require_utc(self.source_updated_at, field="source_updated_at")
        self._validate_values()

    def _validate_values(self) -> None:
        for field in ("open", "high", "low", "close"):
            if getattr(self, field) <= 0:
                raise InvalidDailyPrice(f"{field} must be positive", field=field)
        if self.adjusted_close is not None and self.adjusted_close <= 0:
            raise InvalidDailyPrice("adjusted_close must be positive", field="adjusted_close")
        if self.volume is not None and self.volume < 0:
            raise InvalidDailyPrice("volume must not be negative", field="volume")
        if self.low > self.high:
            raise InvalidDailyPrice("low must not exceed high", field="low")
        if not self.low <= self.open <= self.high:
            raise InvalidDailyPrice("open must be between low and high", field="open")
        if not self.low <= self.close <= self.high:
            raise InvalidDailyPrice("close must be between low and high", field="close")


@dataclass(frozen=True, slots=True)
class WarrantQuoteSnapshot:
    """Provider-neutral bid/ask observation for one concrete FT-004 WarrantListing.

    Provider identity remains provenance only; it never becomes Warrant/WarrantListing
    master data.  Partial quotes are allowed and carry explicit quality through the
    surrounding MarketDataResult.
    """

    warrant_listing_id: UUID
    bid: Decimal | None
    ask: Decimal | None
    currency: str
    provider_symbol: str
    provider_exchange_code: str
    observed_at: datetime

    def __post_init__(self) -> None:
        if self.bid is not None:
            object.__setattr__(self, "bid", _decimal(self.bid, field="bid"))
            if self.bid <= 0:
                raise InvalidMarketDataValue("bid must be positive", field="bid")
        if self.ask is not None:
            object.__setattr__(self, "ask", _decimal(self.ask, field="ask"))
            if self.ask <= 0:
                raise InvalidMarketDataValue("ask must be positive", field="ask")
        if self.bid is not None and self.ask is not None and self.ask < self.bid:
            raise InvalidMarketDataValue("ask must not be below bid", field="ask")
        object.__setattr__(self, "currency", _normalize_code(self.currency, field="currency"))
        object.__setattr__(
            self, "provider_symbol", _normalize_code(self.provider_symbol, field="provider_symbol")
        )
        object.__setattr__(
            self,
            "provider_exchange_code",
            _normalize_code(self.provider_exchange_code, field="provider_exchange_code"),
        )
        _require_utc(self.observed_at, field="observed_at")
