"""Passive original-BID prerequisites, never a B04 comparison or live-market proof."""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Literal

from app.features.market_data.domain.risk_evidence import SavedQuoteEvidence
from app.features.market_data.domain.session_evidence import SessionDay, SessionWindow


@dataclass(frozen=True, slots=True)
class OriginalBidAssessment:
    status: Literal["AVAILABLE", "MISSING", "UNSUITABLE", "NOT_APPLICABLE"]
    price: Decimal | None
    currency: str | None
    original_bid_at: datetime | None
    age_seconds: Decimal | None
    evaluated_at: datetime
    reasons: tuple[str, ...]
    maximum_age_seconds: Literal[900] = 900
    price_axis: Literal["WARRANT_BID"] = "WARRANT_BID"


@dataclass(frozen=True, slots=True)
class DocumentedSessionMatch:
    status: Literal["IN_DOCUMENTED_INTERVAL", "OUTSIDE_DOCUMENTED_INTERVAL", "NOT_ASSESSABLE"]
    event_at: datetime | None
    session_date: date | None
    interval: SessionWindow | None
    reasons: tuple[str, ...]


def assess_original_bid(
    saved: SavedQuoteEvidence, *, evaluated_at: datetime, applicable: bool
) -> OriginalBidAssessment:
    if evaluated_at.utcoffset() is None:
        raise ValueError("The server read requires a timezone-aware clock")
    quote = saved.quote
    original = quote.original_evidence if quote else None
    side = original.bid if original else None
    price = quote.bid if quote else None
    currency = quote.currency if quote else None
    bid_at = side.observed_at if side else None
    age = None
    if bid_at is not None:
        delta = evaluated_at.astimezone(UTC) - bid_at.astimezone(UTC)
        age = Decimal(delta.days * 86400 + delta.seconds) + Decimal(delta.microseconds) / 1000000
    status: Literal["AVAILABLE", "MISSING", "UNSUITABLE", "NOT_APPLICABLE"]
    reasons: tuple[str, ...]
    if not applicable:
        status, reasons = "NOT_APPLICABLE", ("POSITION_CLOSED_OR_CANCELLED",)
    elif quote is None:
        status = (
            "MISSING"
            if saved.reason
            in {"NO_CONFIRMED_SAVED_QUOTE_SOURCE", "NO_SAVED_QUOTE_FOR_CURRENT_ROUTE"}
            else "UNSUITABLE"
        )
        reasons = (saved.reason,)
    elif saved.route is None or saved.provenance is None:
        status, reasons = "UNSUITABLE", ("SAVED_QUOTE_BINDING_OR_PROVENANCE_MISSING",)
    elif price is None:
        status, reasons = "MISSING", ("ORIGINAL_BID_PRICE_MISSING",)
    elif side is None:
        status, reasons = "MISSING", ("ORIGINAL_BID_SIDE_TIME_MISSING",)
    elif (
        saved.provider != "FRANKFURT_QUOTES"
        or original is None
        or original.version != "original-quote-evidence-v1"
        or original.source_contract != "frankfurt-quotes-v1"
        or side.source_field != "bid_at"
        or side.time_basis != "SEPARATE_SIDE_TIMESTAMP"
        or quote.provider_exchange_code != "XFRA"
        or quote.venue_mic != "XFRA"
        or saved.route.venue_mic != "XFRA"
        or original.venue_mic != "XFRA"
        or quote.source_mode
        not in {"FRANKFURT_REALTIME_MONITORING", "FRANKFURT_DELAYED_MONITORING"}
    ):
        # Only this existing producer contract preserves a demonstrated BID
        # field. A structurally valid future source is not silently qualified.
        status, reasons = "UNSUITABLE", ("ORIGINAL_BID_SOURCE_CONTRACT_UNSUPPORTED",)
    elif (
        saved.retrieved_at is None
        or original is None
        or original.generated_at > saved.retrieved_at
        or side.observed_at > saved.retrieved_at
    ):
        status, reasons = "UNSUITABLE", ("ORIGINAL_BID_AFTER_RETRIEVAL",)
    elif age is not None and age < 0:
        status, reasons = "UNSUITABLE", ("ORIGINAL_BID_AFTER_READ",)
    elif age is not None and age > 900:
        status, reasons = "UNSUITABLE", ("ORIGINAL_BID_TOO_OLD",)
    else:
        status, reasons = "AVAILABLE", ()
    return OriginalBidAssessment(status, price, currency, bid_at, age, evaluated_at, reasons)


def documented_session_at(
    *, days: tuple[SessionDay, ...], event_at: datetime
) -> DocumentedSessionMatch:
    """Inspect complete, owner-qualified rows; opening included, closing excluded.

    This establishes a documented interval only. It makes no statement about a
    trading halt or a currently open instrument. Callers must include the prior
    local day to cover documented overnight sessions, with no invented holidays.
    """
    if event_at.utcoffset() is None:
        raise ValueError("A documented interval needs an aware event clock")
    if any(day.status == "UNKNOWN" for day in days):
        return DocumentedSessionMatch(
            "NOT_ASSESSABLE", event_at, None, None, ("SESSION_DAYS_UNKNOWN",)
        )
    matches = [
        (day.session_date, interval)
        for day in days
        for interval in day.intervals
        if interval.opens_at.astimezone(UTC)
        <= event_at.astimezone(UTC)
        < interval.closes_at.astimezone(UTC)
    ]
    if len(matches) > 1:
        return DocumentedSessionMatch(
            "NOT_ASSESSABLE", event_at, None, None, ("SESSION_DAYS_CONFLICT",)
        )
    if not matches:
        return DocumentedSessionMatch(
            "OUTSIDE_DOCUMENTED_INTERVAL",
            event_at,
            None,
            None,
            ("OUTSIDE_DOCUMENTED_PRODUCT_SESSION",),
        )
    day, interval = matches[0]
    return DocumentedSessionMatch("IN_DOCUMENTED_INTERVAL", event_at, day, interval, ())
