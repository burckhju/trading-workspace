"""Quote quality is distinct from a directional trading signal."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.features.market_data.domain.risk_evidence import SavedQuoteEvidence


@dataclass(frozen=True, slots=True)
class QuoteQuality:
    status: str
    reasons: tuple[str, ...]
    bid: Decimal | None = None
    ask: Decimal | None = None
    spread_mid_percent: Decimal | None = None
    observed_at: datetime | None = None
    received_at: datetime | None = None
    age_seconds: int | None = None
    bid_volume: int | None = None
    ask_volume: int | None = None
    provider: str | None = None
    currency: str | None = None
    quote_time_text: str | None = None
    quote_time_basis: str | None = None
    execution_usable: bool = False


def qualify_quote(evidence: SavedQuoteEvidence, *, as_of: datetime) -> QuoteQuality:
    quote = evidence.quote
    if quote is None:
        return QuoteQuality("NOT_EVALUABLE", (evidence.reason,))
    reasons = [evidence.refresh_status]
    age = None
    if quote.observed_at is None:
        reasons.append("SOURCE_TIME_OR_TIMEZONE_UNKNOWN")
    elif quote.observed_at > as_of:
        reasons.append("QUOTE_TIME_IN_FUTURE")
    else:
        age = int((as_of - quote.observed_at).total_seconds())
        if quote.max_quote_age_seconds is None:
            reasons.append("QUOTE_AGE_POLICY_UNKNOWN")
        elif age > quote.max_quote_age_seconds:
            reasons.append("QUOTE_STALE")
    if quote.retained or quote.refresh_error:
        reasons.append("QUOTE_RETAINED_OR_REFRESH_FAILED")
    if quote.bid is None:
        reasons.append("POSITIVE_BID_MISSING")
    if quote.ask is None:
        reasons.append("ASK_MISSING")
    for name, value in (("BID", quote.bid_volume), ("ASK", quote.ask_volume)):
        if value is None:
            reasons.append(f"{name}_VOLUME_UNKNOWN")
        elif value == 0:
            reasons.append(f"{name}_VOLUME_ZERO")
    spread = None
    if quote.bid is not None and quote.ask is not None:
        spread = (quote.ask - quote.bid) / ((quote.ask + quote.bid) / 2) * 100
    return QuoteQuality(
        "LIMITED",
        tuple(reasons),
        quote.bid,
        quote.ask,
        spread,
        quote.observed_at,
        evidence.retrieved_at,
        age,
        quote.bid_volume,
        quote.ask_volume,
        evidence.provider,
        quote.currency,
        quote.quote_time_text,
        quote.quote_time_basis,
    )
