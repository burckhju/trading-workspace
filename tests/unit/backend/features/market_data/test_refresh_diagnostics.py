"""Failure episodes track real checks, independently for each provider/listing."""

from copy import deepcopy
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.features.market_data.domain.models import WarrantQuoteSnapshot
from app.features.market_data.service.errors import (
    MarketDataAuthenticationError,
    MarketDataCurrencyConflictError,
    MarketDataMappingError,
    MarketDataTimeoutError,
    MarketDataUnavailableError,
)
from app.features.market_data.service.refresh_diagnostics import (
    exception_reason,
    job_diagnostics,
    safe_reason,
)
from app.features.position_monitoring.service.quote_sources import (
    QuoteSourceAttempt,
    QuoteSourceAttemptStatus,
)
from app.providers.frankfurt_quotes.schema import FrankfurtSourceError

NOW = datetime(2026, 10, 30, 12, tzinfo=UTC)
LISTING = UUID("00000000-0000-4000-8000-000000000002")


def source_attempt(source="FRANKFURT_QUOTES", status="ERROR", **changes):
    return {
        "source": source,
        "status": status,
        "reason": ("FRANKFURT_TRANSPORT_TIMEOUT" if status == "ERROR" else "VALID_BID_AVAILABLE"),
        "warrant_listing_id": LISTING,
        **changes,
    }


def source_checks(value):
    return [check for check in value["checks"] if check["kind"] == "SOURCE"]


def valid_quotes(at, *attempts):
    return [
        {
            **asdict(
                WarrantQuoteSnapshot(
                    warrant_listing_id=attempt["warrant_listing_id"],
                    bid=Decimal("2.40"),
                    ask=Decimal("2.45"),
                    currency="EUR",
                    provider_symbol="DE000VH2LU21",
                    provider_exchange_code="XSC",
                    observed_at=at,
                )
            ),
            "provider": attempt["source"],
            "retrieved_at": at,
        }
        for attempt in attempts
    ]


@pytest.mark.parametrize(
    ("error", "reason", "category"),
    [
        (
            MarketDataTimeoutError("GET https://private/?token=secret"),
            "MARKET_DATA_TIMEOUT_ERROR",
            "PROVIDER_ERROR",
        ),
        (
            MarketDataUnavailableError("upstream body with secret"),
            "MARKET_DATA_UNAVAILABLE_ERROR",
            "PROVIDER_ERROR",
        ),
        (
            MarketDataAuthenticationError("access denied: secret"),
            "MARKET_DATA_AUTHENTICATION_ERROR",
            "CONFIGURATION",
        ),
        (
            MarketDataMappingError("ambiguous product"),
            "MARKET_DATA_MAPPING_ERROR",
            "CONFIGURATION",
        ),
        (
            MarketDataCurrencyConflictError("EUR != USD"),
            "MARKET_DATA_CURRENCY_CONFLICT",
            "DATA_QUALITY",
        ),
        (ValueError("ISIN_REQUIRED"), "ISIN_REQUIRED", "CONFIGURATION"),
        (ValueError("https://provider/?token=secret"), "ValueError", "JOB_ERROR"),
        (RuntimeError("secret URL"), "RuntimeError", "JOB_ERROR"),
        (
            ValueError("VONTOBEL_MAPPING_CONFLICT"),
            "VONTOBEL_MAPPING_CONFLICT",
            "CONFIGURATION",
        ),
        (
            ValueError("ACTIVE_WARRANT_ISIN_REQUIRED"),
            "ACTIVE_WARRANT_ISIN_REQUIRED",
            "CONFIGURATION",
        ),
        (
            ValueError("ISSUER_RENDERER_UNAVAILABLE"),
            "ISSUER_RENDERER_UNAVAILABLE",
            "PROVIDER_ERROR",
        ),
        (
            FrankfurtSourceError("FRANKFURT_HTTP_503"),
            "FRANKFURT_HTTP_503",
            "PROVIDER_ERROR",
        ),
        (FrankfurtSourceError("FRANKFURT_HTTP_404"), "FRANKFURT_HTTP_404", "NO_QUOTE"),
        (ValueError("ISSUER_PAGE_HTTP_403"), "ISSUER_PAGE_HTTP_403", "CONFIGURATION"),
    ],
)
def test_job_errors_keep_safe_existing_codes_and_distinguish_causes(error, reason, category):
    assert exception_reason(error) == reason
    check = job_diagnostics(None, "ERROR", {"reason": reason}, NOW)["checks"][0]
    assert check["kind"] == "JOB"
    assert check["category"] == category
    assert check["reason"] == reason
    assert check["consecutive_failures"] == 1
    assert check["first_failure_at"] == check["last_failure_at"] == NOW
    assert check["recovered_at"] is None


def test_specific_provider_codes_and_safe_reason_boundaries():
    assert exception_reason(MarketDataTimeoutError("GETTEX_DOWNLOAD_TIMEOUT")) == (
        "GETTEX_DOWNLOAD_TIMEOUT"
    )
    assert exception_reason(FrankfurtSourceError("FRANKFURT_TRANSPORT_TIMEOUT")) == (
        "FRANKFURT_TRANSPORT_TIMEOUT"
    )
    assert safe_reason("MarketDataUnavailableError") == "MARKET_DATA_UNAVAILABLE_ERROR"
    for unsafe in (
        "https://host/?key=secret",
        "secret body",
        "secret",
        "ERROR\nTOKEN",
        "X" * 141,
    ):
        assert safe_reason(unsafe) is None
        assert safe_reason(unsafe, "UNCLASSIFIED_PROVIDER_ERROR") == "UNCLASSIFIED_PROVIDER_ERROR"
    assert safe_reason(None) is None
    assert safe_reason(None, "unsafe fallback") is None


def test_retries_waiting_recovery_and_new_failure_episode_preserve_their_times():
    first = job_diagnostics(None, "ERROR", {"reason": "RuntimeError"}, NOW)
    snapshot = deepcopy(first)
    deferred_at = NOW + timedelta(minutes=1)
    deferred = job_diagnostics(
        first, "DEFERRED", {"reason": "FRANKFURT_REQUEST_THROTTLED"}, deferred_at
    )
    pending = job_diagnostics(deferred, "PENDING", {}, deferred_at)
    for check in (deferred["checks"][0], pending["checks"][0]):
        assert check["consecutive_failures"] == 1
        assert check["first_failure_at"] == check["last_failure_at"] == NOW
        assert check["last_failure_reason"] == "RuntimeError"
        assert check["last_failure_category"] == "JOB_ERROR"
        assert check["recovered_at"] is None
    retry_at = NOW + timedelta(minutes=2)
    retried = job_diagnostics(pending, "ERROR", {"reason": "TimeoutError"}, retry_at)
    check = retried["checks"][0]
    assert check["consecutive_failures"] == 2
    assert check["first_failure_at"] == NOW
    assert check["last_failure_at"] == retry_at
    assert check["last_failure_reason"] == "TimeoutError"
    assert check["last_failure_category"] == "JOB_ERROR"
    restored_at = NOW + timedelta(minutes=3)
    restored = job_diagnostics(retried, "AVAILABLE", {"reason": "OK"}, restored_at)
    check = restored["checks"][0]
    assert check["consecutive_failures"] == 0
    assert check["first_failure_at"] is None
    assert check["last_failure_at"] == retry_at
    assert check["recovered_at"] == restored_at
    assert check["last_failure_reason"] == "TimeoutError"
    assert check["last_failure_category"] == "JOB_ERROR"
    healthy = job_diagnostics(restored, "AVAILABLE", {}, restored_at + timedelta(minutes=1))
    assert healthy["checks"][0]["recovered_at"] == restored_at
    new_failure_at = NOW + timedelta(minutes=5)
    failed_again = job_diagnostics(healthy, "ERROR", {}, new_failure_at)["checks"][0]
    assert failed_again["consecutive_failures"] == 1
    assert failed_again["first_failure_at"] == new_failure_at
    assert failed_again["recovered_at"] is None
    assert first == snapshot


@pytest.mark.parametrize(
    ("status", "reason", "category"),
    [
        ("MISSING", "NO_QUOTE_RETURNED", "NO_QUOTE"),
        ("MISSING", "JPMORGAN_VERIFIED_MAPPING_REQUIRED", "CONFIGURATION"),
        ("INSUFFICIENT", "QUALITY_STALE", "DATA_QUALITY"),
        ("ERROR", "WARRANT_QUOTE_CURRENCY_MISMATCH", "DATA_QUALITY"),
        ("UNAVAILABLE", "POSITION_QUOTE_SOURCE_NOT_CONFIGURED", "CONFIGURATION"),
        ("ERROR", "MarketDataUnavailableError", "PROVIDER_ERROR"),
    ],
)
def test_provider_outcomes_are_classified_without_inventing_freshness(status, reason, category):
    value = job_diagnostics(
        None,
        "MISSING",
        {"source_attempts": [source_attempt(status=status, reason=reason)]},
        NOW,
    )
    check = source_checks(value)[0]
    assert check["category"] == category
    assert check["consecutive_failures"] == 1
    assert check["reason"] == safe_reason(reason)


def test_success_of_other_provider_or_listing_does_not_resolve_a_source_failure():
    other_listing = uuid4()
    failed = source_attempt()
    healthy_provider = source_attempt("JPMORGAN", "AVAILABLE")
    healthy_listing = source_attempt(status="AVAILABLE", warrant_listing_id=other_listing)
    first = job_diagnostics(
        None,
        "AVAILABLE",
        {
            "source_attempts": [failed, healthy_provider, healthy_listing],
            "quotes": valid_quotes(NOW, healthy_provider, healthy_listing),
        },
        NOW,
    )
    assert first["checks"][0]["category"] is None
    assert len(first["checks"]) == 4
    second_at = NOW + timedelta(minutes=1)
    second = job_diagnostics(
        first,
        "AVAILABLE",
        {
            "source_attempts": [healthy_provider, healthy_listing],
            "quotes": valid_quotes(second_at, healthy_provider, healthy_listing),
        },
        second_at,
    )
    missing = next(
        check
        for check in source_checks(second)
        if check["source"] == "FRANKFURT_QUOTES" and check["listing_id"] == LISTING
    )
    assert missing["observed_in_latest_run"] is False
    assert missing["consecutive_failures"] == 1
    assert missing["last_checked_at"] == NOW
    assert missing["recovered_at"] is None
    restored = job_diagnostics(
        second,
        "AVAILABLE",
        {
            "source_attempts": [source_attempt(status="AVAILABLE")],
            "quotes": valid_quotes(second_at, source_attempt(status="AVAILABLE")),
        },
        second_at,
    )
    recovered = next(check for check in source_checks(restored) if check["recovered_at"])
    assert recovered["listing_id"] == LISTING
    assert recovered["source"] == "FRANKFURT_QUOTES"
    assert recovered["consecutive_failures"] == 0
    assert recovered["recovered_at"] == second_at


def test_retained_quote_available_status_does_not_hide_failed_refresh_or_assert_recovery():
    retained = asdict(
        QuoteSourceAttempt(
            source="FRANKFURT_QUOTES",
            status=QuoteSourceAttemptStatus.AVAILABLE,
            reason="LAST_SUCCESSFUL_QUOTE_REFRESH_FAILED",
            delayed=False,
            warrant_listing_id=LISTING,
            refresh_error="FRANKFURT_TRANSPORT_TIMEOUT",
        )
    )
    first = job_diagnostics(None, "AVAILABLE", {"source_attempts": [retained]}, NOW)
    retried = job_diagnostics(first, "AVAILABLE", {"source_attempts": [retained]}, NOW)
    assert retried["checks"][0]["consecutive_failures"] == 0
    source = source_checks(retried)[0]
    assert source["status"] == "AVAILABLE"
    assert source["category"] == "PROVIDER_ERROR"
    assert source["reason"] == "FRANKFURT_TRANSPORT_TIMEOUT"
    assert source["consecutive_failures"] == 2
    assert source["recovered_at"] is None


@pytest.mark.parametrize(
    ("reason", "category"),
    [
        ("MarketDataAuthenticationError", "CONFIGURATION"),
        ("MARKET_DATA_CURRENCY_CONFLICT", "DATA_QUALITY"),
        ("WARRANT_QUOTE_TIME_INCONSISTENT", "DATA_QUALITY"),
        ("WARRANT_NO_QUOTE_RETURNED", "NO_QUOTE"),
    ],
)
def test_retained_refresh_error_preserves_known_cause_and_requires_real_recovery(reason, category):
    failed = source_attempt(status="AVAILABLE", refresh_error=reason)
    first = job_diagnostics(None, "AVAILABLE", {"source_attempts": [failed]}, NOW)
    check = source_checks(first)[0]
    assert check["category"] == check["last_failure_category"] == category
    assert check["reason"] == check["last_failure_reason"] == safe_reason(reason)
    assert check["consecutive_failures"] == 1
    deferred = job_diagnostics(
        first,
        "DEFERRED",
        {
            "source_attempts": [
                source_attempt(
                    status="DEFERRED",
                    reason="FRANKFURT_REQUEST_THROTTLED",
                )
            ]
        },
        NOW + timedelta(minutes=1),
    )
    check = source_checks(deferred)[0]
    assert check["reason"] == "FRANKFURT_REQUEST_THROTTLED"
    assert check["category"] is None
    assert check["consecutive_failures"] == 1
    assert check["last_failure_category"] == category
    assert check["last_failure_reason"] == safe_reason(reason)
    assert check["recovered_at"] is None
    recovered_at = NOW + timedelta(minutes=2)
    recovered = job_diagnostics(
        deferred,
        "AVAILABLE",
        {
            "source_attempts": [
                source_attempt(
                    status="AVAILABLE",
                )
            ],
            "quotes": valid_quotes(recovered_at, source_attempt(status="AVAILABLE")),
        },
        recovered_at,
    )
    check = source_checks(recovered)[0]
    assert check["category"] is None
    assert check["consecutive_failures"] == 0
    assert check["recovered_at"] == recovered_at
    assert check["last_failure_category"] == category
    assert check["last_failure_reason"] == safe_reason(reason)


def test_duplicate_source_attempts_count_once_and_failure_wins_in_either_order():
    failed, healthy = source_attempt(), source_attempt(status="AVAILABLE")
    results = [
        job_diagnostics(None, "AVAILABLE", {"source_attempts": attempts}, NOW)
        for attempts in ([failed, healthy, failed], [healthy, failed, healthy])
    ]
    assert results[0] == results[1]
    assert source_checks(results[0])[0]["consecutive_failures"] == 1
    second = job_diagnostics(results[0], "AVAILABLE", {"source_attempts": [failed, failed]}, NOW)
    assert source_checks(second)[0]["consecutive_failures"] == 2


def test_unsafe_source_details_are_not_copied_to_diagnostics():
    value = job_diagnostics(
        None,
        "AVAILABLE",
        {
            "source_attempts": [
                source_attempt(reason="https://host/?token=secret"),
                source_attempt(source="https://host/?token=secret"),
                source_attempt(warrant_listing_id="not a UUID: secret"),
                source_attempt("JPMORGAN", "AVAILABLE", refresh_error="body with secret"),
            ]
        },
        NOW,
    )
    assert "secret" not in str(value)
    assert len(source_checks(value)) == 2
    assert source_checks(value)[0]["reason"] is None
    assert source_checks(value)[1]["reason"] == "UNCLASSIFIED_PROVIDER_ERROR"


def test_existing_age_policy_qualifies_old_quotes_and_process_local_scope_is_explicit():
    old_quote = valid_quotes(NOW - timedelta(days=20), source_attempt(status="AVAILABLE"))[0]
    old_quote["max_quote_age_seconds"] = 1
    value = job_diagnostics(
        None,
        "AVAILABLE",
        {
            "source_attempts": [
                source_attempt(
                    status="AVAILABLE",
                    observed_at=NOW - timedelta(days=20),
                    max_quote_age_seconds=1,
                )
            ],
            "quotes": [old_quote],
        },
        NOW,
    )
    assert value["scope"] == "PROCESS_LOCAL"
    assert source_checks(value)[0]["category"] == "DATA_QUALITY"
    assert source_checks(value)[0]["quote_status"] == "STALE"
    assert source_checks(value)[0]["consecutive_failures"] == 1
    assert source_checks(value)[0]["qualified_success"] is False
