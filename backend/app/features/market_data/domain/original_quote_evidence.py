"""Original side clocks and price bindings; never a rule or execution approval."""

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Literal

from app.features.market_data.domain.errors import InvalidMarketDataValue


def _utc(value: datetime, field: str) -> None:
    if value.utcoffset() is None or value.utcoffset() != UTC.utcoffset(value):
        raise InvalidMarketDataValue(f"{field} must use an explicit UTC timestamp", field=field)


def _text(value: str, field: str, limit: int) -> None:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise InvalidMarketDataValue(f"{field} must contain bounded source text", field=field)


@dataclass(frozen=True, slots=True)
class OriginalQuoteSideEvidence:
    price: Decimal
    observed_at: datetime
    original_time_text: str
    source_field: str
    time_basis: Literal["SEPARATE_SIDE_TIMESTAMP"] = "SEPARATE_SIDE_TIMESTAMP"

    def __post_init__(self) -> None:
        try:
            if isinstance(self.price, (bool, float)):
                raise ValueError("Price must not use binary floating-point")
            price = Decimal(self.price)
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise InvalidMarketDataValue("Original side price must be decimal") from exc
        if not price.is_finite() or price <= 0:
            raise InvalidMarketDataValue("Original side price must be finite and positive")
        object.__setattr__(self, "price", price)
        _utc(self.observed_at, "observed_at")
        _text(self.original_time_text, "original_time_text", 100)
        _text(self.source_field, "source_field", 100)
        if self.time_basis != "SEPARATE_SIDE_TIMESTAMP":
            raise InvalidMarketDataValue("Original side evidence requires a separate side clock")
        try:
            original = datetime.fromisoformat(self.original_time_text.replace("Z", "+00:00"))
        except ValueError as exc:
            raise InvalidMarketDataValue("Original side time text is not an ISO timestamp") from exc
        if original.utcoffset() is None or original.astimezone(UTC) != self.observed_at:
            raise InvalidMarketDataValue("Original side time text does not match its UTC instant")


@dataclass(frozen=True, slots=True)
class OriginalQuoteEvidence:
    version: Literal["original-quote-evidence-v1"]
    source_contract: str
    source_reference: str
    generated_at: datetime
    isin: str
    currency: str
    venue_mic: str
    bid: OriginalQuoteSideEvidence | None
    ask: OriginalQuoteSideEvidence | None

    def __post_init__(self) -> None:
        if self.version != "original-quote-evidence-v1":
            raise InvalidMarketDataValue("Unsupported original quote evidence version")
        _text(self.source_contract, "source_contract", 100)
        _text(self.source_reference, "source_reference", 200)
        _utc(self.generated_at, "generated_at")
        for field, pattern in (
            ("isin", r"[A-Z]{2}[A-Z0-9]{9}[0-9]"),
            ("currency", r"[A-Z]{3}"),
            ("venue_mic", r"[A-Z0-9]{4}"),
        ):
            if re.fullmatch(pattern, getattr(self, field)) is None:
                raise InvalidMarketDataValue(f"Invalid original quote {field}", field=field)
        if self.bid is None and self.ask is None:
            raise InvalidMarketDataValue("Original quote evidence requires a price side")
        for side in (self.bid, self.ask):
            if side is not None and side.observed_at > self.generated_at:
                raise InvalidMarketDataValue("Original side time exceeds source generation time")
        if self.bid is not None and self.ask is not None and self.ask.price < self.bid.price:
            raise InvalidMarketDataValue("Original quote evidence must not be crossed")
