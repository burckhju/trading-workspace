"""Qualify scheduler evidence with the existing quote and session contracts."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import TypeAdapter, ValidationError

from app.features.market_data.domain.models import WarrantQuoteSnapshot
from app.features.position_monitoring.service.quote_freshness import (
    QuoteFreshness,
    TradingSessionFreshnessPolicy,
)

_QUOTE = TypeAdapter(WarrantQuoteSnapshot)
_TIME = TypeAdapter(datetime)
_FRESHNESS = TradingSessionFreshnessPolicy()


def identity_key(value: object) -> str | None:
    """Only expose the existing canonical route fingerprint, never free text."""
    return value if isinstance(value, str) and re.fullmatch(r"[a-f0-9]{64}", value) else None


def evidence_time(value: object, latest: datetime) -> datetime | None:
    """Accept only bounded UTC evidence; legacy results fall back to job completion."""
    try:
        at = _TIME.validate_python(value)
        if at.tzinfo is not None and at.utcoffset() == UTC.utcoffset(at) and at <= latest:
            return at
    except (ValueError, TypeError):
        pass
    return None


def quote_evidence(
    source: str,
    listing: UUID | None,
    attempt: dict[str, Any],
    quotes: list[dict[str, Any]],
    checked_at: datetime,
) -> dict[str, Any]:
    """Do not confuse a resolver's AVAILABLE (which permits old data) with quality.

    Reachability remains unknown: the provider contract also permits files and
    cache hits, and does not report an HTTP transport outcome. A validated result
    proves a valid response, not a new network connection.
    """
    evidence: dict[str, Any] = {
        "identity_key": identity_key(attempt.get("identity_key")),
        "provider_reachable": None,
        "response_valid": None,
        "retained_quote": bool(attempt.get("refresh_error")),
        "quote_status": "UNASSESSED",
        "quote_usable": None,
        "quote_observed_at": None,
        "quote_retrieved_at": None,
        "qualified_success": False,
    }
    matches = [
        quote
        for quote in quotes
        if quote.get("provider") == source and str(quote.get("warrant_listing_id")) == str(listing)
    ]
    if not matches:
        return {
            **evidence,
            "quote_status": "MISSING",
            "quote_usable": False,
            "quality_reason": "WARRANT_NO_QUOTE_RETURNED",
        }
    if len(matches) != 1:
        return _invalid(evidence, "WARRANT_QUOTE_AMBIGUOUS_RESULT")
    raw = matches[0]
    try:
        quote = _QUOTE.validate_python(raw)
        retrieved_at = _TIME.validate_python(raw["retrieved_at"])
        if (
            retrieved_at.tzinfo is None
            or retrieved_at.utcoffset() != UTC.utcoffset(retrieved_at)
            or retrieved_at > checked_at
            or (quote.observed_at is not None and quote.observed_at > retrieved_at)
            or (
                quote.assessed_at is not None
                and (quote.assessed_at < retrieved_at or quote.assessed_at > checked_at)
            )
        ):
            return _invalid(evidence, "WARRANT_QUOTE_TIME_INCONSISTENT")
        evidence.update(
            quote_observed_at=quote.observed_at,
            quote_retrieved_at=retrieved_at,
            retained_quote=bool(
                quote.retained or quote.refresh_error or attempt.get("refresh_error")
            ),
        )
        if (
            raw.get("quality_status", "VALID") != "VALID"
            or (
                evidence["identity_key"] is not None
                and raw.get("identity_key") != evidence["identity_key"]
            )
            or (attempt.get("currency") is not None and quote.currency != attempt["currency"])
        ):
            return _invalid(evidence, "WARRANT_QUOTE_NOT_VALIDATED")
        if attempt.get("identity_changed"):
            return _invalid(evidence, "WARRANT_QUOTE_IDENTITY_CHANGED_DURING_REFRESH")
        if attempt.get("identity_verified") is False:
            return _invalid(evidence, "WARRANT_ACTIVE_QUOTE_IDENTITY_NOT_FOUND")
        evidence["response_valid"] = True if not evidence["retained_quote"] else None
        if quote.bid is None:
            return {
                **evidence,
                "quote_status": (
                    "REFERENCE_ONLY" if quote.reference_price is not None else "MISSING"
                ),
                "quote_usable": False,
                "quality_reason": (
                    "REFERENCE_PRICE_AVAILABLE_FOR_ANALYSIS"
                    if quote.reference_price is not None
                    else "WARRANT_NO_QUOTE_RETURNED"
                ),
            }
        if quote.observed_at is None:
            return {
                **evidence,
                "quote_status": "TIMESTAMP_UNKNOWN",
                "quote_usable": False,
                "quality_reason": "WARRANT_QUOTE_TIMESTAMP_UNKNOWN",
            }
        freshness = _FRESHNESS.classify(
            observed_at=quote.observed_at,
            retrieved_at=checked_at,
            max_age_seconds=min(
                3600,
                quote.max_quote_age_seconds if quote.max_quote_age_seconds is not None else 3600,
            ),
            trading_status=quote.trading_status,
        )
        usable = freshness is not QuoteFreshness.STALE
        return {
            **evidence,
            "quote_status": freshness.value,
            "quote_usable": usable,
            "qualified_success": usable and not evidence["retained_quote"],
            "quality_reason": (
                "WARRANT_QUOTE_RETAINED"
                if evidence["retained_quote"]
                else "WARRANT_QUOTE_STALE" if not usable else None
            ),
        }
    except (ValueError, ValidationError, KeyError, TypeError):
        return _invalid(evidence, "WARRANT_QUOTE_NOT_VALIDATED")


def _invalid(evidence: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        **evidence,
        "response_valid": False,
        "quote_status": "INVALID",
        "quote_usable": False,
        "qualified_success": False,
        "quality_reason": reason,
    }
