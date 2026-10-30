"""Process-local check state; no alerts, age policy, persistence or retry decisions."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from uuid import UUID

from app.features.market_data.service import errors
from app.features.market_data.service.refresh_quality import evidence_time, quote_evidence
from app.providers.frankfurt_quotes.schema import FrankfurtSourceError

_CODE = re.compile(r"(?:[A-Z][A-Z0-9_]{0,139}|[A-Z][A-Za-z0-9]{0,134}Error)")
_ERROR_CATEGORIES = {
    errors.MarketDataError: "PROVIDER_ERROR",
    errors.MarketDataConfigurationError: "CONFIGURATION",
    errors.MarketDataAuthenticationError: "CONFIGURATION",
    errors.MarketDataAuthorizationError: "CONFIGURATION",
    errors.MarketDataRateLimitError: "PROVIDER_ERROR",
    errors.MarketDataBudgetExhaustedError: "PROVIDER_ERROR",
    errors.MarketDataTimeoutError: "PROVIDER_ERROR",
    errors.MarketDataUnavailableError: "PROVIDER_ERROR",
    errors.MarketDataNotFoundError: "NO_QUOTE",
    errors.MarketDataInvalidResponseError: "DATA_QUALITY",
    errors.MarketDataMappingError: "CONFIGURATION",
    errors.MarketDataCurrencyConflictError: "DATA_QUALITY",
}
_ERROR_CODES = {error.__name__: error.code for error in _ERROR_CATEGORIES}
_REASON_CATEGORIES = {
    name: category
    for error, category in _ERROR_CATEGORIES.items()
    for name in (error.code, error.__name__)
} | {
    "WARRANT_LISTING_MISMATCH": "DATA_QUALITY",
    "WARRANT_QUOTE_TIME_INCONSISTENT": "DATA_QUALITY",
    "WARRANT_QUOTE_CURRENCY_MISMATCH": "DATA_QUALITY",
    "WARRANT_QUOTE_IDENTITY_MISMATCH": "DATA_QUALITY",
    "WARRANT_QUOTE_NOT_VALIDATED": "DATA_QUALITY",
    "WARRANT_NO_QUOTE_RETURNED": "NO_QUOTE",
    "WARRANT_QUOTE_IDENTITY_CHANGED_DURING_REFRESH": "CONFIGURATION",
    "WARRANT_ACTIVE_QUOTE_IDENTITY_NOT_FOUND": "CONFIGURATION",
    "ISIN_REQUIRED": "CONFIGURATION",
    "NO_ACTIVE_MAPPING": "CONFIGURATION",
    "JPMORGAN_VERIFIED_MAPPING_REQUIRED": "CONFIGURATION",
    "MORGAN_STANLEY_VERIFIED_MAPPING_REQUIRED": "CONFIGURATION",
    "FRANKFURT_ACTIVE_MAPPING_NOT_FOUND": "CONFIGURATION",
    "FRANKFURT_MAPPING_IDENTITY_INVALID": "CONFIGURATION",
    "FRANKFURT_HTTP_401": "CONFIGURATION",
    "FRANKFURT_HTTP_403": "CONFIGURATION",
    "FRANKFURT_TRANSPORT_TIMEOUT": "PROVIDER_ERROR",
    "FRANKFURT_TRANSPORT_ERROR": "PROVIDER_ERROR",
    "FRANKFURT_LOCAL_FILE_UNAVAILABLE": "PROVIDER_ERROR",
    "FRANKFURT_ISIN_INVALID": "CONFIGURATION",
    "FRANKFURT_ISIN_REQUIRED": "CONFIGURATION",
    "FRANKFURT_PUBLIC_MODE_REQUIRED": "CONFIGURATION",
    "VONTOBEL_MAPPING_CONFLICT": "CONFIGURATION",
    "ACTIVE_WARRANT_ISIN_REQUIRED": "CONFIGURATION",
    "ACTIVE_UNAMBIGUOUS_QUOTE_CURRENCY_REQUIRED": "CONFIGURATION",
    "ISSUER_NOT_SUPPORTED_BY_VONTOBEL": "CONFIGURATION",
    "VONTOBEL_VERIFIED_BID_REQUIRED": "DATA_QUALITY",
    "ISSUER_RENDERER_UNAVAILABLE": "PROVIDER_ERROR",
    "ISSUER_RENDER_TIMEOUT": "PROVIDER_ERROR",
    "ISSUER_PAGE_TRANSPORT_ERROR": "PROVIDER_ERROR",
    "ISSUER_PAGE_ACCESS_OR_RATE_LIMIT": "PROVIDER_ERROR",
    "ISSUER_PAGE_TERMS_REQUIRED": "CONFIGURATION",
    "ISSUER_RENDER_TERMS_REQUIRED": "CONFIGURATION",
    "ISSUER_PAGE_ACCESS_BLOCKED": "CONFIGURATION",
    "ISSUER_RENDER_ACCESS_BLOCKED": "CONFIGURATION",
    "ISSUER_RENDER_RESPONSE_INVALID": "DATA_QUALITY",
    "ISSUER_PRODUCT_IDENTITY_CONFLICT": "DATA_QUALITY",
    "ISSUER_PRODUCT_METADATA_AMBIGUOUS": "DATA_QUALITY",
    "ISSUER_QUOTE_CURRENCY_UNVERIFIED": "DATA_QUALITY",
}
_WAITING = {"PENDING", "DEFERRED"}
_LOCAL_DEFERRALS = {"FRANKFURT_REQUEST_THROTTLED", "ISSUER_DISCOVERY_DEFERRED"}


def safe_reason(value: object, fallback: str | None = None) -> str | None:
    """Retain bounded application codes/class names, never arbitrary exception text."""
    if isinstance(value, str) and _CODE.fullmatch(value):
        return _ERROR_CODES.get(value, value)
    return (
        _ERROR_CODES.get(fallback, fallback)
        if fallback is not None and _CODE.fullmatch(fallback)
        else None
    )


def exception_reason(exc: Exception) -> str:
    """Preserve specific provider codes or their existing provider-neutral error code."""
    if isinstance(exc, errors.MarketDataError):
        return safe_reason(str(exc), exc.code) or errors.MarketDataError.code
    fallback = safe_reason(type(exc).__name__, "UNCLASSIFIED_JOB_ERROR")
    if isinstance(exc, (ValueError, FrankfurtSourceError)):
        return safe_reason(str(exc), fallback) or "UNCLASSIFIED_JOB_ERROR"
    return fallback or "UNCLASSIFIED_JOB_ERROR"


def _category(kind: str, status: str, reason: str | None, refresh_failed: bool) -> str | None:
    if status in _WAITING:
        return None
    if status == "AVAILABLE" and not refresh_failed:
        return None
    if reason is not None and reason in _REASON_CATEGORIES:
        return _REASON_CATEGORIES[reason]
    # These existing adapters emit status-specific codes, never raw HTTP bodies.
    if reason and (http := re.fullmatch(r"(?:FRANKFURT|ISSUER_PAGE)_HTTP_([0-9]{3})", reason)):
        if http[1] in {"401", "403"}:
            return "CONFIGURATION"
        return "NO_QUOTE" if http[1] == "404" else "PROVIDER_ERROR"
    if refresh_failed:
        return "PROVIDER_ERROR"
    if status in {"UNAVAILABLE", "BLOCKED", "NEEDS_MASTER_DATA"}:
        return "CONFIGURATION"
    if status == "MISSING":
        return "NO_QUOTE"
    if status in {"INSUFFICIENT", "STALE"}:
        return "DATA_QUALITY"
    return "JOB_ERROR" if kind == "JOB" else "PROVIDER_ERROR"


def _observation(
    kind: str,
    source: str | None,
    listing_id: UUID | None,
    status: str,
    details: dict[str, Any],
    *,
    quotes: list[dict[str, Any]] | None = None,
    checked_at: datetime | None = None,
) -> dict[str, Any]:
    refresh_failed = kind == "SOURCE" and bool(details.get("refresh_error"))
    reason = (
        safe_reason(details["refresh_error"], "UNCLASSIFIED_PROVIDER_ERROR")
        if refresh_failed
        else safe_reason(details.get("reason"))
    )
    observation: dict[str, Any] = {
        "kind": kind,
        "source": source,
        "listing_id": listing_id,
        "status": safe_reason(status, "ERROR"),
        "category": _category(kind, status, reason, refresh_failed),
        "reason": reason,
        "waiting": status in _WAITING or reason in _LOCAL_DEFERRALS,
        "qualified_success": status == "AVAILABLE" and not refresh_failed,
    }
    if kind == "SOURCE":
        assert source is not None and checked_at is not None
        evidence = quote_evidence(source, listing_id, details, quotes or [], checked_at)
        quality_reason = evidence.pop("quality_reason", None)
        observation.update(evidence)
        if status != "AVAILABLE" or refresh_failed:
            observation["qualified_success"] = False
        elif quality_reason:
            observation["reason"] = quality_reason
            observation["category"] = _REASON_CATEGORIES.get(
                quality_reason,
                "NO_QUOTE" if evidence["quote_status"] == "MISSING" else "DATA_QUALITY",
            )
        if (
            observation["quote_status"] == "MISSING"
            and _REASON_CATEGORIES.get(reason or "") == "DATA_QUALITY"
        ):
            # The resolver rejected an invalid response; no accepted quote is
            # expected. Preserve that distinction from a genuinely empty reply.
            observation.update(quote_status="INVALID", response_valid=False)
        observation["attempt_started_at"] = evidence_time(
            details.get("attempt_started_at"), checked_at
        )
        if reason in {
            "FRANKFURT_TRANSPORT_TIMEOUT",
            "FRANKFURT_TRANSPORT_ERROR",
            "MARKET_DATA_TIMEOUT_ERROR",
            "ISSUER_PAGE_TRANSPORT_ERROR",
        }:
            observation["provider_reachable"] = False
        elif reason and re.fullmatch(r"(?:FRANKFURT|ISSUER_PAGE)_HTTP_[0-9]{3}", reason):
            observation["provider_reachable"] = True
            observation["response_valid"] = False
        elif reason == errors.MarketDataInvalidResponseError.code:
            observation["response_valid"] = False
    if observation["waiting"]:
        observation["category"] = None
        observation["qualified_success"] = False
    return observation


def _identity(check: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        check["kind"],
        check["source"] or "",
        str(check["listing_id"] or ""),
        check.get("identity_key") or "",
    )


def _preference(check: dict[str, Any]) -> tuple[int, str, str, str]:
    # A failed duplicate wins over success; a completed success wins over waiting.
    # Tie-breaking is independent of adapter/listing iteration order.
    rank = 2 if check["category"] else int(check["qualified_success"])
    return rank, check["category"] or "", check["reason"] or "", check["status"]


def _advance(
    observation: dict[str, Any], previous: dict[str, Any], checked_at: datetime
) -> dict[str, Any]:
    failures = previous.get("consecutive_failures", 0)
    first_failure_at = previous.get("first_failure_at")
    last_failure_at = previous.get("last_failure_at")
    last_failure_reason = previous.get("last_failure_reason")
    last_failure_category = previous.get("last_failure_category")
    last_success_at = previous.get("last_success_at")
    recovered_at = previous.get("recovered_at")
    if (
        observation["kind"] == "SOURCE"
        and observation["qualified_success"]
        and last_failure_at is not None
        and observation["quote_retrieved_at"] <= last_failure_at
    ):
        # A cached success from before the outage is not evidence of recovery.
        observation = {
            **observation,
            "qualified_success": False,
            "waiting": True,
            "reason": "WARRANT_QUOTE_RECOVERY_NOT_OBSERVED",
        }
    if observation["category"] is not None and not observation["waiting"]:
        first_failure_at = first_failure_at if failures else checked_at
        failures += 1
        last_failure_at = checked_at
        last_failure_reason = observation["reason"]
        last_failure_category = observation["category"]
        recovered_at = None
    elif observation["qualified_success"]:
        if failures:
            recovered_at = checked_at
        failures = 0
        first_failure_at = None
        success_at = (
            observation["quote_retrieved_at"] if observation["kind"] == "SOURCE" else checked_at
        )
        last_success_at = max(last_success_at, success_at) if last_success_at else success_at
    return {
        **observation,
        "consecutive_failures": failures,
        "first_failure_at": first_failure_at,
        "last_failure_at": last_failure_at,
        "last_failure_reason": last_failure_reason,
        "last_failure_category": last_failure_category,
        "last_success_at": last_success_at,
        "recovered_at": recovered_at,
        "last_checked_at": checked_at,
        "observed_in_latest_run": True,
    }


def job_diagnostics(
    previous: dict[str, Any] | None,
    status: str,
    details: dict[str, Any],
    checked_at: datetime,
) -> dict[str, Any]:
    """Fold one completed job into one current check per job/source/listing identity.

    ``previous`` is the prior diagnostics object, not the scheduler job. Waiting
    does not increment/reset failures or assert recovery. A source not checked in
    this run retains its last evidence, marked ``observed_in_latest_run=False``.
    AVAILABLE remains the raw resolver outcome. Source recovery additionally
    requires valid, usable evidence with the existing session freshness policy;
    retained or older cached successes never clear a current source failure.
    """
    old = {_identity(check): check for check in (previous or {}).get("checks", [])}
    job = _observation("JOB", None, None, status, details)
    observed = {_identity(job): job}
    completion_times = {_identity(job): checked_at}
    for attempt in details.get("source_attempts", []):
        source = safe_reason(attempt.get("source"))
        if source is None:
            continue
        raw_listing = attempt.get("warrant_listing_id")
        try:
            listing = UUID(str(raw_listing)) if raw_listing is not None else None
        except ValueError:
            continue
        completed_at = evidence_time(attempt.get("attempt_completed_at"), checked_at) or checked_at
        check = _observation(
            "SOURCE",
            source,
            listing,
            attempt.get("status", "ERROR"),
            attempt,
            quotes=details.get("quotes", []),
            checked_at=completed_at,
        )
        key = _identity(check)
        if key not in observed or _preference(check) > _preference(observed[key]):
            observed[key] = check
            completion_times[key] = completed_at
    checks = {key: {**check, "observed_in_latest_run": False} for key, check in old.items()}
    for key, check in observed.items():
        checks[key] = _advance(check, old.get(key, {}), completion_times[key])
    return {"scope": "PROCESS_LOCAL", "checks": [checks[key] for key in sorted(checks)]}
