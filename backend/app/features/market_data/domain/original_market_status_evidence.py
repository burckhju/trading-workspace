"""Original instrument-status points, never current-market or continuity approval."""

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from app.features.market_data.domain.errors import InvalidMarketDataValue

MarketStatus = Literal["OPEN", "CLOSED", "SUSPENDED", "UNKNOWN"]
_STATUSES = {"OPEN", "CLOSED", "SUSPENDED", "UNKNOWN"}
_ORIGINAL_TIME = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]{1,6})?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])"
)


def original_market_status_time(value: object) -> datetime:
    """Require source text with a known offset; never coerce numbers or dates."""
    if (
        not isinstance(value, str)
        or _ORIGINAL_TIME.fullmatch(value) is None
        or value.endswith("-00:00")
    ):
        raise InvalidMarketDataValue("Original status time requires an explicit ISO offset")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise InvalidMarketDataValue("Original status time is invalid") from exc
    return parsed.astimezone(UTC)


def _utc(value: datetime, field: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.utcoffset() is None
        or value.utcoffset() != UTC.utcoffset(value)
    ):
        raise InvalidMarketDataValue(f"{field} must use an explicit UTC timestamp", field=field)


def _text(value: str, field: str, limit: int) -> None:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise InvalidMarketDataValue(f"{field} must contain bounded source text", field=field)


@dataclass(frozen=True, slots=True)
class OriginalMarketStatusEvidence:
    version: Literal["original-market-status-evidence-v1"]
    source_contract: str
    source_reference: str
    generated_at: datetime
    isin: str
    venue_mic: str
    status: MarketStatus
    original_status_text: str
    source_status_field: str
    observed_at: datetime
    original_time_text: str
    source_time_field: str
    time_basis: Literal["SEPARATE_STATUS_TIMESTAMP"] = "SEPARATE_STATUS_TIMESTAMP"
    temporal_meaning: Literal["OBSERVED_AT_INSTANT"] = "OBSERVED_AT_INSTANT"

    def __post_init__(self) -> None:
        if self.version != "original-market-status-evidence-v1":
            raise InvalidMarketDataValue("Unsupported original market status evidence version")
        for field, limit in (
            ("source_contract", 100),
            ("source_reference", 200),
            ("source_status_field", 100),
            ("source_time_field", 100),
        ):
            _text(getattr(self, field), field, limit)
        for field, pattern in (
            ("isin", r"[A-Z]{2}[A-Z0-9]{9}[0-9]"),
            ("venue_mic", r"[A-Z0-9]{4}"),
        ):
            if re.fullmatch(pattern, getattr(self, field)) is None:
                raise InvalidMarketDataValue(f"Invalid original market status {field}", field=field)
        if self.status not in _STATUSES or self.original_status_text != self.status:
            raise InvalidMarketDataValue("Original status text must match the recorded status")
        _utc(self.generated_at, "generated_at")
        _utc(self.observed_at, "observed_at")
        if original_market_status_time(self.original_time_text) != self.observed_at:
            raise InvalidMarketDataValue("Original status text does not match its UTC instant")
        if self.observed_at > self.generated_at:
            raise InvalidMarketDataValue("Original status time exceeds source generation time")
        if self.time_basis != "SEPARATE_STATUS_TIMESTAMP":
            raise InvalidMarketDataValue("Original market status requires a separate status clock")
        if self.temporal_meaning != "OBSERVED_AT_INSTANT":
            raise InvalidMarketDataValue("A status point establishes no interval or current state")
