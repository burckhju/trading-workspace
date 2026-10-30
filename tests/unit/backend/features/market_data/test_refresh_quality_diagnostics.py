"""Recovery requires usable evidence from the same current quote identity."""

import asyncio
from copy import deepcopy
from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from tests.unit.backend.features.position_monitoring.test_quote_sources import (
    _Provider,
    _request,
    _result,
)

from app.features.market_data.domain.models import WarrantQuoteSnapshot
from app.features.market_data.service.errors import MarketDataInvalidResponseError
from app.features.market_data.service.refresh_catalog import RefreshInstrument
from app.features.market_data.service.refresh_diagnostics import job_diagnostics
from app.features.position_monitoring.service.quote_sources import (
    MultiSourceWarrantQuoteResolver,
    NamedWarrantQuoteSource,
)

NOW = datetime(2026, 10, 30, 12, tzinfo=UTC)
LISTING = UUID("00000000-0000-4000-8000-000000000303")
IDENTITY = "a" * 64
SOURCE = "FRANKFURT_QUOTES"


def quote(at=NOW, **changes):
    return replace(
        WarrantQuoteSnapshot(
            warrant_listing_id=LISTING,
            bid=Decimal("2.40"),
            ask=Decimal("2.45"),
            currency="EUR",
            provider_symbol="DE000VH2LU21",
            provider_exchange_code="XSC",
            observed_at=at - timedelta(seconds=5),
            assessed_at=at,
            max_quote_age_seconds=900,
            trading_status="OPEN",
        ),
        **changes,
    )


def details(
    value=None,
    *,
    status="AVAILABLE",
    reason="VALID_BID_AVAILABLE",
    retrieved_at=NOW,
    source=SOURCE,
    identity=IDENTITY,
    cache_status="MISS",
    quality_status="VALID",
):
    attempt = {
        "source": source,
        "warrant_listing_id": LISTING,
        "identity_key": identity,
        "status": status,
        "reason": reason,
        "cache_status": cache_status,
        "bid_available": value is not None and value.bid is not None,
        "ask_available": value is not None and value.ask is not None,
        "observed_at": value.observed_at if value is not None else None,
        "refresh_error": value.refresh_error if value is not None else None,
    }
    return {
        "source_attempts": [attempt],
        "quotes": (
            [
                {
                    **asdict(value),
                    "provider": source,
                    "identity_key": identity,
                    "retrieved_at": retrieved_at,
                    "quality_status": quality_status,
                    "cache_status": cache_status,
                }
            ]
            if value is not None
            else []
        ),
    }


def source_check(diagnostics, *, source=SOURCE, identity=IDENTITY):
    return next(
        check
        for check in diagnostics["checks"]
        if check["kind"] == "SOURCE"
        and check["source"] == source
        and check.get("identity_key") == identity
    )


def failed(at=NOW, *, source=SOURCE, identity=IDENTITY):
    return job_diagnostics(
        None,
        "MISSING",
        details(
            status="ERROR",
            reason="FRANKFURT_TRANSPORT_TIMEOUT",
            source=source,
            identity=identity,
        ),
        at,
    )


def test_first_failure_repeated_failure_then_qualified_recovery_preserve_source_clocks():
    first = failed()
    check = source_check(first)
    assert check["consecutive_failures"] == 1
    assert check["last_success_at"] is None
    assert check["first_failure_at"] == check["last_failure_at"] == NOW
    assert check["recovered_at"] is None
    retry_at = NOW + timedelta(minutes=1)
    second = job_diagnostics(
        first,
        "MISSING",
        details(status="ERROR", reason="FRANKFURT_TRANSPORT_TIMEOUT"),
        retry_at,
    )
    assert source_check(second)["consecutive_failures"] == 2
    retrieved_at = NOW + timedelta(minutes=2)
    completed_at = retrieved_at + timedelta(seconds=9)
    recovered = job_diagnostics(
        second,
        "AVAILABLE",
        details(quote(retrieved_at), retrieved_at=retrieved_at),
        completed_at,
    )
    check = source_check(recovered)
    assert check["qualified_success"] is True
    assert check["consecutive_failures"] == 0
    assert check["last_success_at"] == retrieved_at
    assert check["last_failure_at"] == retry_at
    assert check["recovered_at"] == completed_at
    assert check["quote_status"] == "FRESH"
    assert check["quote_usable"] is True
    assert check["quote_observed_at"] == retrieved_at - timedelta(seconds=5)
    assert check["quote_retrieved_at"] == retrieved_at


def test_stale_quote_after_transport_failure_is_data_quality_without_recovery():
    checked_at = NOW + timedelta(minutes=1)
    result = job_diagnostics(
        failed(),
        "AVAILABLE",
        details(
            quote(checked_at, observed_at=NOW - timedelta(days=2)),
            retrieved_at=checked_at,
        ),
        checked_at,
    )
    check = source_check(result)
    assert check["status"] == "AVAILABLE"
    assert check["quote_status"] == "STALE"
    assert check["category"] == "DATA_QUALITY"
    assert check["qualified_success"] is False
    assert check["consecutive_failures"] == 2
    assert check["last_success_at"] is None
    assert check["recovered_at"] is None


def test_zero_age_budget_is_preserved_instead_of_replaced_with_default_freshness():
    checked_at = NOW + timedelta(minutes=1)
    result = job_diagnostics(
        failed(),
        "AVAILABLE",
        details(quote(checked_at, max_quote_age_seconds=0), retrieved_at=checked_at),
        checked_at,
    )
    check = source_check(result)
    assert check["quote_status"] == "STALE"
    assert check["qualified_success"] is False
    assert check["consecutive_failures"] == 2
    assert check["last_success_at"] is None
    assert check["recovered_at"] is None


def test_missing_payload_does_not_promote_available_source_to_success():
    result = job_diagnostics(failed(), "AVAILABLE", details(), NOW + timedelta(minutes=1))
    check = source_check(result)
    assert check["qualified_success"] is False
    assert check["consecutive_failures"] > 0
    assert check["last_success_at"] is None
    assert check["recovered_at"] is None


@pytest.mark.parametrize("invalid", ["crossed", "nonfinite", "future", "quality", "identity"])
def test_invalid_or_contradictory_payload_cannot_recover_an_available_attempt(invalid):
    checked_at = NOW + timedelta(minutes=1)
    evidence = details(quote(checked_at), retrieved_at=checked_at)
    payload = evidence["quotes"][0]
    if invalid == "crossed":
        payload["ask"] = Decimal("2.00")
    elif invalid == "nonfinite":
        payload["bid"] = Decimal("NaN")
    elif invalid == "future":
        payload["observed_at"] = checked_at + timedelta(seconds=1)
    elif invalid == "quality":
        payload["quality_status"] = "SUSPICIOUS"
    else:
        payload["warrant_listing_id"] = uuid4()
    result = job_diagnostics(failed(), "AVAILABLE", evidence, checked_at)
    check = source_check(result)
    assert check["qualified_success"] is False
    assert check["consecutive_failures"] > 0
    assert check["last_success_at"] is None
    assert check["recovered_at"] is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("rejection", "expected_reason"),
    [
        ("time", "WARRANT_QUOTE_TIME_INCONSISTENT"),
        ("currency", "WARRANT_QUOTE_CURRENCY_MISMATCH"),
        ("response", MarketDataInvalidResponseError.code),
    ],
)
async def test_resolver_rejected_response_remains_invalid_even_without_an_accepted_quote(
    rejection, expected_reason
):
    result = _result(LISTING)
    if rejection == "time":
        result = replace(
            result,
            data=replace(result.data, observed_at=result.retrieved_at + timedelta(seconds=1)),
        )
    elif rejection == "currency":
        result = replace(result, data=replace(result.data, currency="USD"))
    provider = _Provider(
        result=result,
        error=(
            MarketDataInvalidResponseError("Unusable provider response")
            if rejection == "response"
            else None
        ),
    )
    resolver = MultiSourceWarrantQuoteResolver((NamedWarrantQuoteSource(SOURCE, provider),))
    resolution = await resolver.resolve_selected(
        SOURCE, replace(_request(LISTING), expected_currency="EUR")
    )
    assert resolution.result is None
    assert resolution.attempts[0].status == "ERROR"
    diagnostic = job_diagnostics(
        failed(NOW - timedelta(minutes=1)),
        "MISSING",
        {
            "source_attempts": [
                {**asdict(attempt), "identity_key": IDENTITY} for attempt in resolution.attempts
            ],
            "quotes": [],
        },
        NOW,
    )
    check = source_check(diagnostic)
    assert check["reason"] == expected_reason
    assert check["category"] == "DATA_QUALITY"
    assert check["quote_status"] == "INVALID"
    assert check["response_valid"] is False
    assert check["qualified_success"] is False
    assert check["consecutive_failures"] == 2
    assert check["last_success_at"] is check["recovered_at"] is None


def test_reference_only_stays_analysis_evidence_without_claiming_bid_recovery():
    checked_at = NOW + timedelta(minutes=1)
    reference = quote(
        checked_at,
        bid=None,
        ask=None,
        reference_price=Decimal("2.40"),
        reference_price_type="LAST_TRADE",
    )
    result = job_diagnostics(
        failed(), "AVAILABLE", details(reference, retrieved_at=checked_at), checked_at
    )
    check = source_check(result)
    assert check["quote_status"] == "REFERENCE_ONLY"
    assert check["qualified_success"] is False
    assert check["consecutive_failures"] > 0
    assert check["recovered_at"] is None


def test_issuer_bid_without_verified_timestamp_does_not_assert_recovery():
    checked_at = NOW + timedelta(minutes=1)
    unknown_time = quote(
        checked_at,
        observed_at=None,
        provider_exchange_code="ISSUER",
        source_mode="OFFICIAL_ISSUER_INDICATION_TIME_ONLY",
        quote_time_basis="DATE_AND_TIMEZONE_UNKNOWN",
    )
    result = job_diagnostics(
        failed(source="JPMORGAN"),
        "AVAILABLE",
        details(unknown_time, source="JPMORGAN", retrieved_at=checked_at),
        checked_at,
    )
    check = source_check(result, source="JPMORGAN")
    assert check["quote_status"] == "TIMESTAMP_UNKNOWN"
    assert check["qualified_success"] is False
    assert check["recovered_at"] is None


def test_session_policy_allows_last_available_weekend_quote_but_not_next_session_staleness():
    closed_at = datetime(2026, 10, 30, 21, tzinfo=UTC)
    weekend = datetime(2026, 10, 31, 10, tzinfo=UTC)
    previous_close = quote(weekend, observed_at=closed_at, trading_status="CLOSED")
    recovered = job_diagnostics(
        failed(closed_at + timedelta(hours=1)),
        "AVAILABLE",
        details(previous_close, retrieved_at=weekend),
        weekend,
    )
    check = source_check(recovered)
    assert check["quote_status"] == "LAST_AVAILABLE"
    assert check["quote_usable"] is True
    assert check["qualified_success"] is True
    assert check["last_success_at"] == check["recovered_at"] == weekend
    monday = datetime(2026, 11, 2, 8, tzinfo=UTC)
    stale = job_diagnostics(
        recovered,
        "AVAILABLE",
        details(replace(previous_close, assessed_at=monday), retrieved_at=monday),
        monday,
    )
    check = source_check(stale)
    assert check["quote_status"] == "STALE"
    assert check["qualified_success"] is False
    assert check["consecutive_failures"] == 1
    assert check["last_success_at"] == weekend
    assert check["recovered_at"] is None


@pytest.mark.parametrize("refresh_error", [None, "FRANKFURT_TRANSPORT_TIMEOUT"])
def test_stored_substitute_never_recovers_current_fetch_even_with_a_recent_quote(
    refresh_error,
):
    checked_at = NOW + timedelta(minutes=1)
    retained = quote(NOW, retained=True, refresh_error=refresh_error)
    result = job_diagnostics(
        failed(),
        "AVAILABLE",
        details(retained, cache_status="HIT", retrieved_at=NOW),
        checked_at,
    )
    check = source_check(result)
    assert check["retained_quote"] is True
    assert check["qualified_success"] is False
    assert check["consecutive_failures"] > 0
    assert check["last_success_at"] is None
    assert check["recovered_at"] is None


def test_old_cache_hit_cannot_prove_recovery_or_a_new_provider_contact():
    original = job_diagnostics(None, "AVAILABLE", details(quote()), NOW)
    failure_at = NOW + timedelta(seconds=20)
    outage = job_diagnostics(
        original,
        "MISSING",
        details(status="ERROR", reason="FRANKFURT_TRANSPORT_TIMEOUT"),
        failure_at,
    )
    result = job_diagnostics(
        outage,
        "AVAILABLE",
        details(quote(), cache_status="HIT"),
        NOW + timedelta(seconds=30),
    )
    check = source_check(result)
    assert check["provider_reachable"] is None
    assert check["last_success_at"] == NOW
    assert check["consecutive_failures"] > 0
    assert check["recovered_at"] is None


def test_healthy_cache_hit_keeps_original_retrieval_clock():
    original = job_diagnostics(None, "AVAILABLE", details(quote()), NOW)
    result = job_diagnostics(
        original,
        "AVAILABLE",
        details(quote(), cache_status="HIT"),
        NOW + timedelta(seconds=30),
    )
    check = source_check(result)
    assert check["quote_status"] == "FRESH"
    assert check["quote_usable"] is True
    assert check["provider_reachable"] is None
    assert check["last_success_at"] == NOW
    assert check["consecutive_failures"] == 0
    assert check["recovered_at"] is None


def test_replacement_mapping_is_new_identity_and_leaves_old_failure_unresolved():
    replacement = "b" * 64
    checked_at = NOW + timedelta(minutes=1)
    result = job_diagnostics(
        failed(),
        "AVAILABLE",
        details(quote(checked_at), retrieved_at=checked_at, identity=replacement),
        checked_at,
    )
    old, new = source_check(result), source_check(result, identity=replacement)
    assert old["consecutive_failures"] == 1
    assert old["observed_in_latest_run"] is False
    assert old["recovered_at"] is None
    assert new["qualified_success"] is True
    assert new["consecutive_failures"] == 0
    assert new["recovered_at"] is None
    assert new["last_success_at"] == checked_at


def test_provider_success_does_not_clear_another_provider_failure_in_available_job():
    checked_at = NOW + timedelta(minutes=1)
    evidence = details(status="ERROR", reason="FRANKFURT_TRANSPORT_TIMEOUT")
    healthy = details(quote(checked_at), retrieved_at=checked_at, source="GETTEX_DELAYED")
    evidence["source_attempts"] += healthy["source_attempts"]
    evidence["quotes"] += healthy["quotes"]
    result = job_diagnostics(failed(), "AVAILABLE", evidence, checked_at)
    broken, current = source_check(result), source_check(result, source="GETTEX_DELAYED")
    assert broken["consecutive_failures"] == 2
    assert broken["recovered_at"] is None
    assert current["qualified_success"] is True
    assert current["consecutive_failures"] == 0
    assert current["recovered_at"] is None
    assert next(c for c in result["checks"] if c["kind"] == "JOB")["status"] == "AVAILABLE"


def test_each_source_uses_its_own_attempt_clock_for_failure_freshness_and_recovery():
    evidence = details(status="ERROR", reason="FRANKFURT_TRANSPORT_TIMEOUT")
    secondary = details(status="ERROR", reason="MARKET_DATA_TIMEOUT_ERROR", source="GETTEX_DELAYED")
    evidence["source_attempts"] += secondary["source_attempts"]
    for attempt, start, end in zip(evidence["source_attempts"], (0, 10), (1, 12), strict=True):
        attempt["attempt_started_at"] = NOW + timedelta(seconds=start)
        attempt["attempt_completed_at"] = NOW + timedelta(seconds=end)
    first = job_diagnostics(None, "MISSING", evidence, NOW + timedelta(seconds=30))
    primary = source_check(first)
    other = source_check(first, source="GETTEX_DELAYED")
    assert primary["attempt_started_at"] == NOW
    assert primary["last_checked_at"] == primary["last_failure_at"] == NOW + timedelta(seconds=1)
    assert other["attempt_started_at"] == NOW + timedelta(seconds=10)
    assert other["last_checked_at"] == other["last_failure_at"] == NOW + timedelta(seconds=12)

    retrieved_at = NOW + timedelta(seconds=61)
    evidence = details(quote(retrieved_at, max_quote_age_seconds=10), retrieved_at=retrieved_at)
    evidence["source_attempts"] += secondary["source_attempts"]
    for attempt, start, end in zip(evidence["source_attempts"], (60, 70), (62, 72), strict=True):
        attempt["attempt_started_at"] = NOW + timedelta(seconds=start)
        attempt["attempt_completed_at"] = NOW + timedelta(seconds=end)
    result = job_diagnostics(first, "AVAILABLE", evidence, NOW + timedelta(seconds=90))
    recovered = source_check(result)
    assert recovered["quote_status"] == "FRESH"
    assert recovered["qualified_success"] is True
    assert recovered["attempt_started_at"] == NOW + timedelta(seconds=60)
    assert recovered["last_checked_at"] == recovered["recovered_at"] == NOW + timedelta(seconds=62)
    assert recovered["last_success_at"] == retrieved_at
    assert recovered["last_failure_at"] == NOW + timedelta(seconds=1)
    assert recovered["consecutive_failures"] == 0
    broken = source_check(result, source="GETTEX_DELAYED")
    assert broken["attempt_started_at"] == NOW + timedelta(seconds=70)
    assert broken["last_checked_at"] == broken["last_failure_at"] == NOW + timedelta(seconds=72)
    assert broken["first_failure_at"] == NOW + timedelta(seconds=12)
    assert broken["consecutive_failures"] == 2
    assert broken["recovered_at"] is None


@pytest.mark.parametrize("retained", [False, True])
@pytest.mark.parametrize(
    ("source", "failure", "throttled"),
    [
        (SOURCE, "FRANKFURT_TRANSPORT_TIMEOUT", "FRANKFURT_REQUEST_THROTTLED"),
        ("GETTEX_DELAYED", "GETTEX_DELAYED_RATE_LIMITED", "GETTEX_DELAYED_REQUEST_THROTTLED"),
    ],
)
def test_source_local_throttle_preserves_failure_without_counting_an_unmade_request(
    retained, source, failure, throttled
):
    original = job_diagnostics(
        None, "MISSING", details(status="ERROR", reason=failure, source=source), NOW
    )
    if retained:
        evidence = details(
            quote(retained=True, refresh_error=throttled),
            cache_status="HIT",
            source=source,
        )
    else:
        evidence = details(status="ERROR", reason=throttled, source=source)
    result = original
    for seconds in (30, 60):
        result = job_diagnostics(
            result,
            "AVAILABLE" if retained else "MISSING",
            evidence,
            NOW + timedelta(seconds=seconds),
        )
        check = source_check(result, source=source)
        assert check["waiting"] is True
        assert check["category"] is None
        assert check["consecutive_failures"] == 1
        assert check["last_failure_at"] == NOW
        assert check["last_failure_reason"] == failure
        assert check["last_success_at"] is None
        assert check["recovered_at"] is None

    recovered_at = NOW + timedelta(seconds=120)
    recovered = job_diagnostics(
        result,
        "AVAILABLE",
        details(quote(recovered_at), retrieved_at=recovered_at, source=source),
        recovered_at,
    )
    check = source_check(recovered, source=source)
    assert check["qualified_success"] is True
    assert check["consecutive_failures"] == 0
    assert check["last_failure_at"] == NOW
    assert check["last_failure_reason"] == failure
    assert check["last_success_at"] == check["recovered_at"] == recovered_at


@pytest.mark.parametrize("retained", [False, True])
@pytest.mark.parametrize(
    ("reason", "category"),
    [
        ("GETTEX_DELAYED_AUTHENTICATION_REQUIRED", "CONFIGURATION"),
        ("GETTEX_DELAYED_ACCESS_FORBIDDEN", "CONFIGURATION"),
        ("GETTEX_DELAYED_ACTIVE_MAPPING_NOT_FOUND", "CONFIGURATION"),
        ("GETTEX_DELAYED_NO_TRACKED_ISINS", "CONFIGURATION"),
        ("GETTEX_DELAYED_RATE_LIMITED", "PROVIDER_ERROR"),
        ("GETTEX_DELAYED_RECENT_FILE_NOT_AVAILABLE", "PROVIDER_ERROR"),
        ("GETTEX_DELAYED_UPSTREAM_UNAVAILABLE", "PROVIDER_ERROR"),
        ("GETTEX_DELAYED_TIMEOUT", "PROVIDER_ERROR"),
        ("GETTEX_DELAYED_NETWORK_ERROR", "PROVIDER_ERROR"),
        ("GETTEX_DELAYED_CONTENT_LENGTH_INVALID", "DATA_QUALITY"),
        ("GETTEX_DELAYED_CONTENT_LENGTH_MISMATCH", "DATA_QUALITY"),
        ("GETTEX_DELAYED_FILE_TOO_LARGE", "DATA_QUALITY"),
        ("GETTEX_DELAYED_REDIRECT_REJECTED", "DATA_QUALITY"),
        ("GETTEX_DELAYED_UNEXPECTED_HTTP_206", "DATA_QUALITY"),
        ("GETTEX_DELAYED_EXPECTED_CURRENCY_MISMATCH", "DATA_QUALITY"),
        ("GETTEX_DELAYED_CURRENCY_MISMATCH", "DATA_QUALITY"),
        ("GETTEX_GZIP_INVALID", "DATA_QUALITY"),
        ("GETTEX_DUPLICATE_TIMESTAMP_CONFLICT", "DATA_QUALITY"),
        ("GETTEX_ROW_CROSSED_QUOTE", "DATA_QUALITY"),
        ("GETTEX_ROW_CURRENCY_INVALID", "DATA_QUALITY"),
        ("GETTEX_ROW_TIME_OUTSIDE_FILE_WINDOW", "DATA_QUALITY"),
        ("GETTEX_ROW_BID_NOT_POSITIVE", "DATA_QUALITY"),
        ("GETTEX_ROW_ASK_INVALID", "DATA_QUALITY"),
        ("GETTEX_ROW_BID_VOLUME_NEGATIVE", "DATA_QUALITY"),
    ],
)
def test_gettex_failure_categories_survive_retention_without_asserting_recovery(
    reason, category, retained
):
    source = "GETTEX_DELAYED"
    evidence = (
        details(quote(retained=True, refresh_error=reason), source=source, cache_status="HIT")
        if retained
        else details(status="ERROR", reason=reason, source=source)
    )
    result = job_diagnostics(None, "AVAILABLE" if retained else "MISSING", evidence, NOW)
    check = source_check(result, source=source)
    assert check["reason"] == reason
    assert check["category"] == check["last_failure_category"] == category
    assert check["consecutive_failures"] == 1
    assert check["waiting"] is False
    assert check["qualified_success"] is False
    assert check["last_success_at"] is check["recovered_at"] is None
    assert check["retained_quote"] is retained
    if retained:
        # The rejected refresh does not corrupt the original stored quote evidence.
        assert check["quote_status"] == "FRESH"
        assert check["quote_observed_at"] == NOW - timedelta(seconds=5)
        assert check["quote_retrieved_at"] == NOW
        assert check["response_valid"] is None
    else:
        assert check["quote_status"] == ("INVALID" if category == "DATA_QUALITY" else "MISSING")
        assert check["response_valid"] is (False if category == "DATA_QUALITY" else None)


@pytest.mark.asyncio
async def test_overlapping_attempts_count_the_actual_completed_read_once_and_polling_is_passive():
    from tests.unit.backend.features.market_data.test_refresh import runtime

    value = runtime()
    item = RefreshInstrument(uuid4(), "Concurrent warrant", None)
    key = f"WARRANT_QUOTES:{item.id}"
    entered, release = asyncio.Event(), asyncio.Event()
    calls = 0

    async def operation():
        nonlocal calls
        calls += 1
        entered.set()
        await release.wait()
        return {
            "status": "MISSING",
            **details(status="ERROR", reason="FRANKFURT_TRANSPORT_TIMEOUT"),
        }

    value.jobs[key] = {"status": "PENDING", "job": key}
    task = asyncio.create_task(value._job(key, item, 300, operation))
    try:
        await asyncio.wait_for(entered.wait(), timeout=1)
        snapshot = deepcopy(value.jobs)
        deadlines = dict(value._due)
        await value._job(key, item, 300, operation)
        assert calls == 1
        for _ in range(2):
            assert value.status()["jobs"][0]["execution"]["running"] is True
        assert value.jobs == snapshot
        assert value._due == deadlines
        release.set()
        await asyncio.wait_for(task, timeout=1)
        check = source_check(value.jobs[key]["diagnostics"])
        assert check["consecutive_failures"] == 1
        assert check["recovered_at"] is None
        assert value.status()["jobs"][0]["execution"]["running"] is False
    finally:
        release.set()
        await task
        await value.container.close()
