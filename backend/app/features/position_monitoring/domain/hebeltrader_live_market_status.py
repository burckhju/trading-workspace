"""Explain saved source status without inferring current market opening.

The existing price last-success is neither a status stream nor an account of
later refresh attempts. Even an exactly matching original status point does not
qualify B58 without a demonstrated source contract and temporal coverage.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from app.features.market_data.domain.original_market_status_evidence import (
    OriginalMarketStatusEvidence,
)
from app.features.market_data.domain.risk_evidence import SavedQuoteEvidence

PointRelation = Literal[
    "NO_EVENT_TIME",
    "NO_ORIGINAL_STATUS_TIME",
    "BEFORE_SOURCE_POINT",
    "AT_SOURCE_POINT",
    "AFTER_SOURCE_POINT",
    "NOT_APPLICABLE",
]


@dataclass(frozen=True, slots=True)
class MarketStatusPointComparison:
    event_at: datetime | None
    relation: PointRelation
    status: Literal["NOT_ASSESSABLE", "NOT_APPLICABLE"]


@dataclass(frozen=True, slots=True)
class LiveMarketStatusAssessment:
    status: Literal["MISSING", "UNSUITABLE", "NOT_APPLICABLE"]
    reasons: tuple[str, ...]
    evaluated_at: datetime
    reported_status: str | None
    original_evidence: OriginalMarketStatusEvidence | None
    at_bid: MarketStatusPointComparison
    at_read: MarketStatusPointComparison
    definition_version: Literal["hebeltrader-live-market-status-v1"] = (
        "hebeltrader-live-market-status-v1"
    )
    evidence_scope: Literal["SAVED_QUOTE_LAST_SUCCESS_ONLY"] = "SAVED_QUOTE_LAST_SUCCESS_ONLY"
    source_qualification: Literal["NOT_INDEPENDENTLY_VERIFIED"] = "NOT_INDEPENDENTLY_VERIFIED"
    newer_status_observations: Literal["NOT_OBSERVED_BY_SAVED_QUOTE_READER"] = (
        "NOT_OBSERVED_BY_SAVED_QUOTE_READER"
    )
    status_validity_interval: Literal["NOT_ESTABLISHED"] = "NOT_ESTABLISHED"


def _point(
    event_at: datetime | None,
    original: OriginalMarketStatusEvidence | None,
    *,
    applicable: bool,
) -> MarketStatusPointComparison:
    if not applicable:
        return MarketStatusPointComparison(event_at, "NOT_APPLICABLE", "NOT_APPLICABLE")
    if event_at is None:
        relation: PointRelation = "NO_EVENT_TIME"
    elif original is None:
        relation = "NO_ORIGINAL_STATUS_TIME"
    else:
        event, observed = event_at.astimezone(UTC), original.observed_at.astimezone(UTC)
        relation = (
            "BEFORE_SOURCE_POINT"
            if event < observed
            else "AFTER_SOURCE_POINT" if event > observed else "AT_SOURCE_POINT"
        )
    return MarketStatusPointComparison(event_at, relation, "NOT_ASSESSABLE")


def assess_live_market_status(
    saved: SavedQuoteEvidence,
    *,
    original_bid_at: datetime | None,
    evaluated_at: datetime,
    applicable: bool,
) -> LiveMarketStatusAssessment:
    """Retain reported facts; never turn an OPEN point into an opening interval.

    There is deliberately no price-age-derived status TTL, trusted-source flag,
    implicit continuity requirement between BID and read, or positive live state.
    A future qualified status owner needs its own evidenced temporal contract.
    """
    if evaluated_at.utcoffset() is None or (
        original_bid_at is not None and original_bid_at.utcoffset() is None
    ):
        raise ValueError("Status comparison requires aware event and server clocks")
    quote = saved.quote
    original = quote.original_market_status if quote is not None else None
    reported = quote.trading_status if quote is not None else None
    reasons: list[str] = []
    status: Literal["MISSING", "UNSUITABLE", "NOT_APPLICABLE"] = "MISSING"
    if not applicable:
        status = "NOT_APPLICABLE"
        reasons.append("POSITION_CLOSED_OR_CANCELLED")
    else:
        if quote is None:
            reasons.append("MARKET_STATUS_SAVED_QUOTE_MISSING")
        if reported is None or reported == "UNKNOWN":
            reasons.append("MARKET_STATUS_VALUE_MISSING_OR_UNKNOWN")
        elif reported != "OPEN":
            status = "UNSUITABLE"
            reasons.append(
                "MARKET_STATUS_SOURCE_REPORTED_NOT_OPEN"
                if reported in {"CLOSED", "SUSPENDED"}
                else "MARKET_STATUS_VALUE_UNSUPPORTED"
            )
        if original is None:
            reasons.append("MARKET_STATUS_ORIGINAL_TIME_MISSING")
        else:
            route = saved.route
            provenance = saved.provenance
            if (
                quote is None
                or route is None
                or provenance is None
                or original.isin != quote.provider_symbol
                or (quote.isin is not None and original.isin != quote.isin)
                or original.venue_mic != quote.venue_mic
                or original.venue_mic != route.venue_mic
                or quote.warrant_listing_id != route.warrant_listing_id
                or saved.identity_key != route.identity_key
                or original.status != reported
            ):
                status = "UNSUITABLE"
                reasons.append("MARKET_STATUS_BINDING_OR_PROVENANCE_INVALID")
            if (
                saved.retrieved_at is None
                or original.observed_at > original.generated_at
                or original.generated_at > saved.retrieved_at
                or saved.retrieved_at > evaluated_at
                or (provenance is not None and provenance.read_at != evaluated_at)
                or (provenance is not None and provenance.retrieved_at != saved.retrieved_at)
            ):
                status = "UNSUITABLE"
                reasons.append("MARKET_STATUS_SOURCE_TIME_INCONSISTENT")
            reasons.append("MARKET_STATUS_POINT_IS_NOT_VALIDITY_INTERVAL")
        # These are known limits of this producer/read path, even when a point
        # exactly equals the requested event. A later failed/status-only refresh
        # is not observed by this saved-price reader and must not imply recovery.
        reasons.extend(
            (
                "MARKET_STATUS_SOURCE_SEMANTICS_NOT_VERIFIED",
                "MARKET_STATUS_NEWER_OBSERVATIONS_NOT_COVERED",
            )
        )
    return LiveMarketStatusAssessment(
        status=status,
        reasons=tuple(reasons),
        evaluated_at=evaluated_at,
        reported_status=reported,
        original_evidence=original,
        at_bid=_point(original_bid_at, original, applicable=applicable),
        at_read=_point(evaluated_at, original, applicable=applicable),
    )
