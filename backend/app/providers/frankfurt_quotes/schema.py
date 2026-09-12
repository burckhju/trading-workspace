"""Our vendor-neutral import contract, NOT a Deutsche Boerse wire/API schema."""

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

SCHEMA_VERSION = "frankfurt-quotes-v1"
FRANKFURT_MIC = "XFRA"
Price = Annotated[Decimal, Field(gt=0, allow_inf_nan=False)]
Size = Annotated[int, Field(strict=True, ge=0)]


class FrankfurtSourceError(RuntimeError):
    """Only stable public reason codes; never URLs, tokens or upstream response text."""


class QuoteStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    MISSING = "MISSING"
    INSUFFICIENT = "INSUFFICIENT"
    STALE = "STALE"
    UNAVAILABLE = "UNAVAILABLE"
    ERROR = "ERROR"


def _utc(value: Any) -> datetime:
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError("An explicit timezone-aware timestamp is required")
    return value.astimezone(UTC)


class FrankfurtRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    isin: Annotated[str, Field(pattern=r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")]
    wkn: Annotated[str, Field(pattern=r"^[A-Z0-9]{6}$")] | None = None
    mic: Annotated[str, Field(pattern=r"^[A-Z0-9]{4}$")]
    currency: Annotated[str, Field(pattern=r"^[A-Z]{3}$")]
    kind: Literal["BID_ASK", "LAST_TRADE", "PREVIOUS_CLOSE"]
    bid: Price | None = None
    ask: Price | None = None
    bid_size: Size | None = None
    ask_size: Size | None = None
    bid_at: datetime | None = None
    ask_at: datetime | None = None
    last_price: Price | None = None
    last_at: datetime | None = None
    close_price: Price | None = None
    close_at: datetime | None = None
    trading_status: Literal["OPEN", "CLOSED", "SUSPENDED", "UNKNOWN"] = "UNKNOWN"

    @field_validator("bid_at", "ask_at", "last_at", "close_at", mode="before")
    @classmethod
    def validate_timestamp(cls, value: Any) -> datetime | None:
        return None if value is None else _utc(value)


class FrankfurtSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["frankfurt-quotes-v1"]
    source: Annotated[str, Field(pattern=r"^[A-Za-z0-9_.-]{1,80}$")]
    generated_at: datetime
    delay_seconds: Annotated[int, Field(strict=True, ge=0)]
    # Validate only the requested instrument's fields so an unrelated corrupt
    # price does not take down every holding. Envelope/identity shape is required.
    records: Annotated[list[dict[str, Any]], Field(max_length=10000)]

    @field_validator("generated_at", mode="before")
    @classmethod
    def validate_generated_at(cls, value: Any) -> datetime:
        return _utc(value)


class FrankfurtObservation(BaseModel):
    """Read-only diagnostics; size and side timestamps are not execution approval."""

    model_config = ConfigDict(frozen=True)

    status: QuoteStatus
    reason: str
    source: str
    isin: str
    mic: str = FRANKFURT_MIC
    assessed_at: datetime
    retrieved_at: datetime
    snapshot_generated_at: datetime | None
    declared_delay_seconds: int | None
    max_quote_age_seconds: int
    observed_at: datetime | None = None
    age_seconds: float | None = None
    record: FrankfurtRecord | None = None
    provider_exchange_code: str = FRANKFURT_MIC
    source_mode: str = "NORMALIZED_SNAPSHOT"
    refresh_error: str | None = None
    execution_usable: Literal[False] = False

    @property
    def analysis_usable(self) -> bool:
        """Age/market state affect disclosure, not identity-validated analysis."""
        record = self.record
        if (
            self.status in (QuoteStatus.ERROR, QuoteStatus.MISSING, QuoteStatus.UNAVAILABLE)
            or record is None
        ):
            return False
        if record.kind == "LAST_TRADE":
            return record.last_price is not None
        if record.kind == "PREVIOUS_CLOSE":
            return record.close_price is not None
        return record.bid is not None and self.observed_at is not None


def assess_snapshot(
    snapshot: FrankfurtSnapshot,
    *,
    isin: str,
    wkn: str | None,
    currency: str,
    now: datetime,
    retrieved_at: datetime,
    max_age_seconds: int = 900,
) -> FrankfurtObservation:
    """Exact ISIN + XFRA; never synthesize bid/ask from last trades or other venues."""
    now = _utc(now)
    retrieved_at = _utc(retrieved_at)
    if not 1 <= max_age_seconds <= 900:
        raise ValueError("max_age_seconds must be in [1, 900]")
    matches = [row for row in snapshot.records if row.get("isin") == isin]
    rows = [row for row in matches if row.get("mic") == FRANKFURT_MIC]
    record = None
    if len(rows) == 1:
        try:
            record = FrankfurtRecord.model_validate(rows[0])
        except ValidationError:
            raise FrankfurtSourceError("FRANKFURT_RECORD_INVALID") from None

    status, reason = QuoteStatus.AVAILABLE, "FRANKFURT_BID_ASK_AVAILABLE"
    observed_at = None
    age = None
    if len(rows) > 1:
        status, reason = QuoteStatus.ERROR, "FRANKFURT_DUPLICATE_IDENTITY"
    elif not rows:
        status = QuoteStatus.MISSING
        reason = "FRANKFURT_VENUE_NOT_FOUND" if matches else "FRANKFURT_INSTRUMENT_NOT_FOUND"
    elif record is not None:
        if record.currency != currency:
            status, reason = QuoteStatus.ERROR, "FRANKFURT_CURRENCY_MISMATCH"
        elif wkn is not None and record.wkn != wkn:
            status, reason = QuoteStatus.ERROR, "FRANKFURT_WKN_MISMATCH"
        elif record.kind != "BID_ASK":
            status, reason = QuoteStatus.INSUFFICIENT, "FRANKFURT_POST_TRADE_ONLY"
            observed_at = record.last_at if record.kind == "LAST_TRADE" else record.close_at
            reference_price = (
                record.last_price if record.kind == "LAST_TRADE" else record.close_price
            )
            if reference_price is None:
                status, reason = (
                    QuoteStatus.MISSING,
                    "FRANKFURT_REFERENCE_PRICE_MISSING",
                )
            elif observed_at is not None:
                age = (now - observed_at).total_seconds()
                if observed_at > snapshot.generated_at:
                    status, reason = (
                        QuoteStatus.ERROR,
                        "FRANKFURT_TIMESTAMP_INCONSISTENT",
                    )
                elif age > max_age_seconds:
                    status, reason = (
                        QuoteStatus.STALE,
                        "FRANKFURT_REFERENCE_PRICE_STALE",
                    )
        elif record.bid is None or record.ask is None:
            status, reason = QuoteStatus.INSUFFICIENT, "FRANKFURT_BID_ASK_MISSING"
        elif record.bid_at is None or record.ask_at is None:
            status, reason = (
                QuoteStatus.INSUFFICIENT,
                "FRANKFURT_SIDE_TIMESTAMP_MISSING",
            )
        elif record.ask < record.bid:
            status, reason = QuoteStatus.ERROR, "FRANKFURT_CROSSED_QUOTE"
        else:
            # The older side sets freshness; do not round down before comparison.
            observed_at = min(record.bid_at, record.ask_at)
            age = (now - observed_at).total_seconds()
            if max(record.bid_at, record.ask_at) > snapshot.generated_at:
                status, reason = QuoteStatus.ERROR, "FRANKFURT_TIMESTAMP_INCONSISTENT"
            elif age > max_age_seconds:
                status, reason = QuoteStatus.STALE, "FRANKFURT_QUOTE_STALE"
            elif record.trading_status != "OPEN":
                status, reason = QuoteStatus.INSUFFICIENT, "FRANKFURT_MARKET_NOT_OPEN"

    if snapshot.generated_at > retrieved_at or retrieved_at > now:
        status, reason = QuoteStatus.ERROR, "FRANKFURT_TIMESTAMP_INCONSISTENT"
    elif status is not QuoteStatus.ERROR and snapshot.delay_seconds > max_age_seconds:
        status, reason = QuoteStatus.INSUFFICIENT, "FRANKFURT_FEED_DELAY_EXCEEDED"
    elif (
        status is not QuoteStatus.ERROR
        and (now - snapshot.generated_at).total_seconds() > max_age_seconds
    ):
        status, reason = QuoteStatus.STALE, "FRANKFURT_SNAPSHOT_STALE"

    return FrankfurtObservation(
        status=status,
        reason=reason,
        source=snapshot.source,
        isin=isin,
        assessed_at=now,
        retrieved_at=retrieved_at,
        snapshot_generated_at=snapshot.generated_at,
        declared_delay_seconds=snapshot.delay_seconds,
        max_quote_age_seconds=max_age_seconds,
        observed_at=observed_at,
        age_seconds=age,
        record=record,
    )
