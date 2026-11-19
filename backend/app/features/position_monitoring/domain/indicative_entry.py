"""Separate review observations; never qualify B58 or mutate a strict B04 episode."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal

from app.features.market_data.domain.issuer_indications import ISSUER_INDICATIONS
from app.features.market_data.domain.risk_evidence import SavedQuoteEvidence
from app.features.position_monitoring.domain.hebeltrader_original_bid import (
    assess_original_bid,
)
from app.features.position_monitoring.domain.indicative_policy import (
    V1_POLICY,
    IndicativeReviewPolicy,
)

RULE_VERSION = "indicative-entry-review-v1"
RULE_SCOPE = "INDICATIVE_ENTRY_V1"
RULE_KEY = f"{RULE_SCOPE}:{RULE_VERSION}"
type EvaluationMode = Literal["SOURCE_BID", "INDICATIVE_ISSUER", "DELAYED_SOURCE_BID"]
type SourceTimeBasis = Literal["ORIGINAL_BID_TIME", "SHARED_QUOTE_TIME", "ORIGINAL_TIME_UNKNOWN"]
type SourceFreshness = Literal["WITHIN_900_SECONDS", "WITHIN_1800_SECONDS", "UNKNOWN"]
type EpisodeKind = Literal["ENTRY_LOSS", "REVIEW_DUE", "DATA_UNAVAILABLE"]
type EntryOutcome = Literal[
    "BELOW_ENTRY", "AT_OR_ABOVE_ENTRY", "NOT_REACHED", "UNAVAILABLE", "CLOSED"
]
EPISODE_KINDS: tuple[EpisodeKind, ...] = (
    "ENTRY_LOSS",
    "REVIEW_DUE",
    "DATA_UNAVAILABLE",
)


@dataclass(frozen=True, slots=True)
class IndicativeQuote:
    bid: Decimal | None
    currency: str | None
    original_bid_at: datetime | None
    received_at: datetime | None
    evaluation_mode: EvaluationMode | None
    session_event_at: datetime
    ordering_at: datetime | None
    reasons: tuple[str, ...]
    source_quote_at: datetime | None = None
    source_time_basis: SourceTimeBasis = "ORIGINAL_TIME_UNKNOWN"
    source_freshness: SourceFreshness | None = None

    @property
    def usable(self) -> bool:
        return not self.reasons and self.bid is not None and self.evaluation_mode is not None


def qualify_review_quote(
    saved: SavedQuoteEvidence,
    *,
    now: datetime,
    selection_policy: str | None,
    policy: IndicativeReviewPolicy = V1_POLICY,
) -> IndicativeQuote:
    """Retain the existing source clocks; shared/Ask/receipt time is never BID time.

    The only original-side-time producer currently preserved by the owner is
    the Frankfurt import contract. It still does not establish a real B58
    supplier. Registered issuer indications have an unknown original clock:
    their existing 300-second receipt limit enables only a review observation.
    """
    if now.utcoffset() is None:
        raise ValueError("Indicative review requires an aware evaluation clock")
    quote, route = saved.quote, saved.route
    bid = quote.bid if quote else None
    currency = quote.currency if quote else None
    mode: EvaluationMode | None = None
    original_at = None
    source_quote_at = None
    source_time_basis: SourceTimeBasis = "ORIGINAL_TIME_UNKNOWN"
    source_freshness: SourceFreshness | None = None
    event_at = now
    ordering_at = None
    reasons: tuple[str, ...]
    if quote is None:
        reasons = (saved.reason,)
    elif route is None or saved.provenance is None or saved.identity_key != route.identity_key:
        reasons = ("REVIEW_QUOTE_BINDING_MISSING",)
    elif bid is None:
        reasons = ("REVIEW_BID_MISSING",)
    elif not bid.is_finite() or bid < 0:
        reasons = ("REVIEW_BID_INVALID",)
    elif (
        saved.retrieved_at is None
        or saved.retrieved_at.utcoffset() is None
        or saved.retrieved_at > now
    ):
        reasons = ("REVIEW_RECEIPT_TIME_INVALID",)
    elif quote.retained or quote.refresh_error:
        reasons = ("REVIEW_QUOTE_REFRESH_FAILED",)
    elif quote.observed_at is None:
        contract = ISSUER_INDICATIONS.get(saved.provider or "")
        if (
            contract is None
            or (quote.source_mode, quote.quote_time_basis) != contract[:2]
            or selection_policy != contract[2]
            or quote.provider_exchange_code != "ISSUER"
            or quote.provider_symbol != quote.isin
            or not quote.quote_time_text
            or quote.reference_price is not None
        ):
            reasons = ("REVIEW_UNKNOWN_TIME_SOURCE_UNSUPPORTED",)
        elif (now - saved.retrieved_at).total_seconds() > 300:
            reasons = ("REVIEW_ISSUER_RECEIPT_TOO_OLD",)
        else:
            mode = "INDICATIVE_ISSUER"
            source_freshness = "UNKNOWN"
            ordering_at = saved.retrieved_at
            reasons = ()
    elif policy.delayed_bid_max_age_seconds is not None and saved.provider in {
        "GETTEX_DELAYED",
        "BOERSE_STUTTGART_DELAYED",
    }:
        # These existing adapters preserve one source quote clock, not a BID
        # side clock. Their explicitly separate policy must not qualify B58.
        source_quote_at = quote.observed_at
        source_time_basis = "SHARED_QUOTE_TIME"
        allowed_venues = {"MUND", "MUNC"} if saved.provider == "GETTEX_DELAYED" else {"XSTU"}
        expected_mode = "OFFICIAL_DELAYED_PRETRADE" if saved.provider == "GETTEX_DELAYED" else None
        if (
            quote.provider_exchange_code not in allowed_venues
            or route.venue_mic != quote.provider_exchange_code
            or quote.source_mode != expected_mode
            or (quote.isin is not None and quote.provider_symbol != quote.isin)
            or quote.warrant_listing_id != route.warrant_listing_id
            or quote.currency != route.currency
            or quote.reference_price is not None
            or quote.original_evidence is not None
        ):
            reasons = ("REVIEW_DELAYED_SOURCE_BINDING_MISMATCH",)
        elif (
            source_quote_at.utcoffset() is None
            or source_quote_at > saved.retrieved_at
            or source_quote_at > now
        ):
            reasons = ("REVIEW_SOURCE_QUOTE_TIME_INVALID",)
        elif (now - source_quote_at).total_seconds() > policy.delayed_bid_max_age_seconds:
            reasons = ("REVIEW_DELAYED_BID_TOO_OLD",)
        else:
            mode = "DELAYED_SOURCE_BID"
            source_freshness = "WITHIN_1800_SECONDS"
            event_at = ordering_at = source_quote_at
            reasons = ()
    else:
        original = assess_original_bid(saved, evaluated_at=now, applicable=True)
        original_at = original.original_bid_at
        if original_at is not None:
            source_time_basis = "ORIGINAL_BID_TIME"
        if original.status != "AVAILABLE":
            reasons = original.reasons
        else:
            assert original_at is not None
            mode = "SOURCE_BID"
            source_freshness = "WITHIN_900_SECONDS"
            event_at = ordering_at = original_at
            reasons = ()
    return IndicativeQuote(
        bid,
        currency,
        original_at,
        saved.retrieved_at,
        mode,
        event_at,
        ordering_at,
        reasons,
        source_quote_at,
        source_time_basis,
        source_freshness,
    )


@dataclass(frozen=True, slots=True)
class IndicativeDecision:
    outcome: EntryOutcome
    reasons: tuple[str, ...]
    review_due: bool | None
    review_completed_sessions: int | None
    completed_sessions: int | None
    bid: Decimal | None
    gross_entry: Decimal
    remaining_quantity: int
    evaluation_mode: EvaluationMode | None
    original_bid_at: datetime | None
    received_at: datetime | None
    session_count_at: datetime
    ordering_at: datetime | None
    source_quote_at: datetime | None = None
    source_time_basis: SourceTimeBasis = "ORIGINAL_TIME_UNKNOWN"
    source_freshness: SourceFreshness | None = None


def decide_indicative_entry(
    *,
    closed: bool,
    gross_entry: Decimal,
    remaining_quantity: int,
    quote: IndicativeQuote,
    review_completed_sessions: int | None,
    completed_sessions: int | None,
    input_problems: tuple[str, ...],
) -> IndicativeDecision:
    """Three independent states: review due, price observation, unavailable data.

    Missing inputs preserve an earlier price episode. Neither an indicative
    recovery nor a sale in this scope changes a strict B04 assessment or episode.
    """
    due = review_completed_sessions >= 20 if review_completed_sessions is not None else None
    problems = tuple(dict.fromkeys((*quote.reasons, *input_problems)))
    reasons: tuple[str, ...]
    if closed or remaining_quantity <= 0:
        outcome: EntryOutcome = "CLOSED"
        reasons = ("POSITION_CLOSED_OR_CANCELLED",)
        due = False
    elif problems:
        outcome, reasons = "UNAVAILABLE", problems
    elif not gross_entry.is_finite() or gross_entry <= 0:
        outcome, reasons = "UNAVAILABLE", ("REVIEW_ENTRY_INVALID",)
    elif not quote.usable or completed_sessions is None:
        outcome, reasons = "UNAVAILABLE", ("REVIEW_REQUIRED_INPUT_MISSING",)
    elif completed_sessions < 20:
        outcome, reasons = "NOT_REACHED", ("REVIEW_TWENTIETH_SESSION_NOT_COMPLETED",)
    elif quote.bid is not None and quote.bid < gross_entry:
        outcome, reasons = "BELOW_ENTRY", ("INDICATIVE_BID_BELOW_GROSS_ENTRY",)
    else:
        outcome, reasons = "AT_OR_ABOVE_ENTRY", ("INDICATIVE_BID_AT_OR_ABOVE_GROSS_ENTRY",)
    return IndicativeDecision(
        outcome,
        reasons,
        due,
        review_completed_sessions,
        completed_sessions,
        quote.bid,
        gross_entry,
        remaining_quantity,
        quote.evaluation_mode,
        quote.original_bid_at,
        quote.received_at,
        quote.session_event_at,
        quote.ordering_at,
        quote.source_quote_at,
        quote.source_time_basis,
        quote.source_freshness,
    )
