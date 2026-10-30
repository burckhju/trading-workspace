"""Observe real scheduler attempts without changing intervals or lane ownership."""

import asyncio
from copy import deepcopy
from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from tests.unit.backend.features.market_data.test_refresh import runtime
from tests.unit.backend.features.position_monitoring.test_quote_sources import (
    _Provider,
    _request,
    _result,
)

from app.features.market_data.domain.enums import MarketDataProvider
from app.features.market_data.service import refresh as module
from app.features.market_data.service.errors import MarketDataUnavailableError
from app.features.market_data.service.refresh_catalog import RefreshInstrument
from app.features.position_monitoring.service.quote_sources import (
    MultiSourceWarrantQuoteResolver,
    NamedWarrantQuoteSource,
)
from app.providers.frankfurt_quotes.schema import FrankfurtSourceError

pytestmark = pytest.mark.asyncio


def current_result(listing, provider):
    result = _result(listing)
    now = datetime.now(UTC)
    return replace(
        result,
        provider=MarketDataProvider(provider),
        retrieved_at=now,
        data=replace(result.data, observed_at=now),
    )


def result_quotes(resolved):
    if resolved.result is None or resolved.result.data is None:
        return []
    return [
        {
            **asdict(resolved.result.data),
            "provider": resolved.result.provider,
            "retrieved_at": resolved.result.retrieved_at,
            "quality_status": resolved.result.quality_status,
            "cache_status": resolved.result.cache_status,
        }
    ]


async def test_catalog_rescan_preserves_failure_streak_and_only_due_retry_can_recover(monkeypatch):
    value = runtime()
    item = RefreshInstrument(uuid4(), "Synthetic warrant", None)
    key = f"WARRANT_QUOTES:{item.id}"
    monkeypatch.setattr(module, "read_catalog", AsyncMock(return_value=([item], [])))
    value._warrant = AsyncMock(
        side_effect=[
            MarketDataUnavailableError("https://provider.invalid/?token=SECRET"),
            MarketDataUnavailableError("private response"),
            {"status": "AVAILABLE", "reason": "QUOTE_OBSERVATIONS_AVAILABLE"},
        ]
    )

    await value.run_once()
    first = deepcopy(value.jobs[key])
    check = first["diagnostics"]["checks"][0]
    assert first["status"] == "ERROR"
    assert first["reason"] == "MarketDataUnavailableError"
    assert check["consecutive_failures"] == 1
    assert check["reason"] == "MARKET_DATA_UNAVAILABLE_ERROR"
    assert check["first_failure_at"] == first["checked_at"]
    assert check["recovered_at"] is None

    value.timer = lambda: 1299
    await value.run_once()
    value._warrant.assert_awaited_once()
    assert value.jobs[key]["diagnostics"] == first["diagnostics"]

    value.timer = lambda: 1300
    await value.run_once()
    check = value.jobs[key]["diagnostics"]["checks"][0]
    assert check["consecutive_failures"] == 2
    assert check["first_failure_at"] == first["checked_at"]
    assert check["last_failure_at"] == value.jobs[key]["checked_at"]
    assert value._due[key] == 1600

    value.timer = lambda: 1600
    await value.run_once()
    check = value.jobs[key]["diagnostics"]["checks"][0]
    assert check["consecutive_failures"] == 0
    assert check["first_failure_at"] is None
    assert check["last_failure_at"] is not None
    assert check["recovered_at"] == value.jobs[key]["checked_at"]
    assert value.jobs[key]["last_success_at"] is not None
    assert value._due[key] == 1900
    assert "SECRET" not in str(value.status())

    monkeypatch.setattr(module, "read_catalog", AsyncMock(return_value=([], [])))
    await value.run_once()
    assert value.status()["jobs"] == []


async def test_local_throttling_preserves_failure_evidence_without_counting_or_recovering():
    value = runtime()
    item = RefreshInstrument(uuid4(), "Synthetic warrant", None)
    key = f"FRANKFURT_MAPPING:{item.id}"
    await value._job(
        key, item, 3600, AsyncMock(side_effect=FrankfurtSourceError("FRANKFURT_HTTP_503"))
    )
    failed = deepcopy(value.jobs[key]["diagnostics"]["checks"][0])
    value.timer = lambda: 4600
    await value._job(
        key, item, 3600, AsyncMock(side_effect=FrankfurtSourceError("FRANKFURT_REQUEST_THROTTLED"))
    )
    deferred = value.jobs[key]
    check = deferred["diagnostics"]["checks"][0]
    assert deferred["status"] == "DEFERRED"
    assert deferred["retry_after_seconds"] == 15
    assert check["consecutive_failures"] == failed["consecutive_failures"] == 1
    assert check["first_failure_at"] == failed["first_failure_at"]
    assert check["last_failure_at"] == failed["last_failure_at"]
    assert check["recovered_at"] is None


async def test_running_attempt_has_own_clock_and_cancellation_does_not_invent_a_result():
    value = runtime()
    item = RefreshInstrument(uuid4(), "Synthetic warrant", None)
    key = f"WARRANT_QUOTES:{item.id}"
    await value._job(
        key, item, 300, AsyncMock(return_value={"reason": "QUOTE_OBSERVATIONS_AVAILABLE"})
    )
    completed = deepcopy(value.jobs[key])
    value.timer = lambda: 1300
    entered, release = asyncio.Event(), asyncio.Event()

    async def operation():
        entered.set()
        await release.wait()
        return {"reason": "QUOTE_OBSERVATIONS_AVAILABLE"}

    task = asyncio.create_task(value._job(key, item, 300, operation))
    try:
        await asyncio.wait_for(entered.wait(), timeout=1)
        value.timer = lambda: 1325
        snapshot = value.status()["jobs"][0]
        assert snapshot["execution"]["running"] is True
        assert snapshot["execution"]["started_at"] >= completed["checked_at"]
        assert snapshot["execution"]["elapsed_seconds"] == 25
        assert snapshot["checked_at"] == completed["checked_at"]
        assert snapshot["started_at"] == completed["started_at"]
        assert snapshot["diagnostics"] == completed["diagnostics"]
        # Inspection must not count a second attempt or advance the due time.
        assert value.jobs[key] == completed
        assert value._due[key] == 1300
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert value.status()["jobs"][0]["execution"] == {
        "running": False,
        "started_at": None,
        "elapsed_seconds": None,
    }
    assert value.jobs[key] == completed
    assert value.current_job is None


async def test_provider_outage_survives_successful_other_source_and_retained_quote():
    value = runtime()
    listing = uuid4()
    item = RefreshInstrument(uuid4(), "Synthetic warrant", None)
    key = f"WARRANT_QUOTES:{item.id}"
    primary = _Provider(error=MarketDataUnavailableError("private transport URL"))
    secondary = _Provider(result=current_result(listing, "GETTEX_DELAYED"))
    resolver = MultiSourceWarrantQuoteResolver(
        (
            NamedWarrantQuoteSource("FRANKFURT_QUOTES", primary),
            NamedWarrantQuoteSource("GETTEX_DELAYED", secondary),
        )
    )

    async def operation():
        resolved = await resolver.resolve(_request(listing))
        return {
            "status": "AVAILABLE" if resolved.result else "MISSING",
            "reason": "QUOTE_OBSERVATIONS_AVAILABLE",
            "source_attempts": [asdict(attempt) for attempt in resolved.attempts],
            "quotes": result_quotes(resolved),
        }

    await value._job(key, item, 300, operation)
    checks = value.jobs[key]["diagnostics"]["checks"]
    failed = next(check for check in checks if check["source"] == "FRANKFURT_QUOTES")
    assert value.jobs[key]["status"] == "AVAILABLE"
    assert failed["category"] == "PROVIDER_ERROR"
    assert failed["consecutive_failures"] == 1
    assert failed["reason"] == "MARKET_DATA_UNAVAILABLE_ERROR"

    primary.error = None
    result = current_result(listing, "FRANKFURT_QUOTES")
    primary.result = replace(
        result, data=replace(result.data, retained=True, refresh_error="FRANKFURT_HTTP_503")
    )
    value.timer = lambda: 1300
    await value._job(key, item, 300, operation)
    failed = next(
        check
        for check in value.jobs[key]["diagnostics"]["checks"]
        if check["source"] == "FRANKFURT_QUOTES"
    )
    assert failed["status"] == "AVAILABLE"
    assert failed["consecutive_failures"] == 2
    assert failed["recovered_at"] is None

    primary.result = current_result(listing, "FRANKFURT_QUOTES")
    value.timer = lambda: 1600
    await value._job(key, item, 300, operation)
    recovered = next(
        check
        for check in value.jobs[key]["diagnostics"]["checks"]
        if check["source"] == "FRANKFURT_QUOTES"
    )
    assert recovered["consecutive_failures"] == 0
    assert recovered["recovered_at"] is not None


@pytest.mark.parametrize("missing", [False, True])
async def test_missing_or_old_quote_does_not_become_a_transport_outage(missing):
    value = runtime()
    listing = uuid4()
    item = RefreshInstrument(uuid4(), "Synthetic warrant", None)
    result = current_result(listing, "GETTEX_DELAYED")
    old_time = result.data.observed_at - timedelta(days=1)
    result = replace(result, data=replace(result.data, observed_at=old_time))
    provider = _Provider(result=None if missing else result)
    resolver = MultiSourceWarrantQuoteResolver(
        (NamedWarrantQuoteSource("GETTEX_DELAYED", provider),)
    )
    resolved = await resolver.resolve(_request(listing))
    await value._job(
        f"WARRANT_QUOTES:{item.id}",
        item,
        300,
        AsyncMock(
            return_value={
                "status": "MISSING" if missing else "AVAILABLE",
                "reason": "NO_USABLE_WARRANT_QUOTE" if missing else "QUOTE_OBSERVATIONS_AVAILABLE",
                "source_attempts": [asdict(attempt) for attempt in resolved.attempts],
                "quotes": result_quotes(resolved),
            }
        ),
    )
    check = next(
        check
        for check in value.status()["jobs"][0]["diagnostics"]["checks"]
        if check["kind"] == "SOURCE"
    )
    assert check["category"] == ("NO_QUOTE" if missing else "DATA_QUALITY")
    assert check["consecutive_failures"] == 1
    assert check["qualified_success"] is False
    if not missing:
        # A completed request is not evidence of fresh data. The original quote
        # remains old for the existing coverage/valuation freshness policies.
        assert resolved.result.data.observed_at == old_time
        assert resolved.result.retrieved_at == result.retrieved_at
