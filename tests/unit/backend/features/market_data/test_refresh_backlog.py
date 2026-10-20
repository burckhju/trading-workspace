"""Local throttling must not postpone discovery for an hour or hide overdue work."""

import json
from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from tests.unit.backend.features.market_data.test_refresh import runtime
from tests.unit.backend.providers.frankfurt_quotes.test_public import (
    public_settings,
    wire,
)
from tests.unit.backend.providers.frankfurt_quotes.test_schema import NOW

from app.features.market_data.service.refresh import RefreshLane
from app.features.market_data.service.refresh_catalog import RefreshInstrument
from app.providers.frankfurt_quotes.client import FrankfurtSnapshotClient
from app.providers.frankfurt_quotes.schema import FrankfurtSourceError

pytestmark = pytest.mark.asyncio


async def test_shared_budget_defers_discovery_then_retries_without_another_request_budget():
    clock = [1000.0]
    value = runtime()
    value.timer = lambda: clock[0]
    client = FrankfurtSnapshotClient(
        public_settings(), timer=value.timer, clock=lambda: NOW, cache_seconds=300
    )
    item = RefreshInstrument(uuid4(), "Second warrant", "DE000HM4EB12", held=True)
    client._read = AsyncMock(
        side_effect=[
            json.dumps(wire()).encode(),
            json.dumps({**wire(), "isin": item.isin}).encode(),
        ]
    )
    value.container = replace(
        value.container,
        frankfurt=SimpleNamespace(settings=client.settings, snapshots=client),
    )
    # A UI read consumes the same provider slot as background discovery.
    await client.load_public("DE000VH2LU21")
    key = f"FRANKFURT_MAPPING:{item.id}"

    async def discover():
        await client.load_public(item.isin)
        return {"reason": "FRANKFURT_IDENTITY_VERIFIED"}

    operation = AsyncMock(side_effect=discover)
    await value._job(key, item, 3600, operation)
    job = value.jobs[key]
    assert job["status"] == "DEFERRED"
    assert job["reason"] == "FRANKFURT_REQUEST_THROTTLED"
    assert job["last_success_at"] is None
    assert job["retry_after_seconds"] == 15
    assert job["next_run_at"] - job["checked_at"] == timedelta(seconds=15)
    client._read.assert_awaited_once()
    clock[0] += 14
    await value._job(key, item, 3600, operation)
    operation.assert_awaited_once()
    clock[0] += 1
    await value._job(key, item, 3600, operation)
    assert client._read.await_count == 2
    assert value.jobs[key]["status"] == "AVAILABLE"
    assert value.jobs[key]["reason"] == "FRANKFURT_IDENTITY_VERIFIED"
    assert "retry_after_seconds" not in value.jobs[key]
    assert value._due[key] == clock[0] + 3600


@pytest.mark.parametrize("cooldown", [0, 7.1, 120, 7200])
async def test_deferred_retry_respects_spacing_and_longer_provider_cooldowns(cooldown):
    value = runtime()
    value._next_request = 1020
    value.container = replace(
        value.container,
        frankfurt=SimpleNamespace(
            snapshots=SimpleNamespace(request_delay_seconds=lambda: cooldown)
        ),
    )
    value.jobs["mapping"] = {"last_success_at": NOW}
    await value._job(
        "mapping",
        RefreshInstrument(uuid4(), "Warrant", None),
        3600,
        AsyncMock(side_effect=FrankfurtSourceError("FRANKFURT_REQUEST_THROTTLED")),
    )
    assert value._due["mapping"] == 1000 + max(20, cooldown)
    assert value.jobs["mapping"]["last_success_at"] == NOW
    assert value.jobs["mapping"]["status"] == "DEFERRED"


@pytest.mark.parametrize(
    "reason",
    [
        "FRANKFURT_HTTP_404",
        "FRANKFURT_ISIN_INVALID",
        "FRANKFURT_HTTP_429",
        "FRANKFURT_HTTP_403",
    ],
)
async def test_real_provider_failures_keep_the_existing_retry_policy(reason):
    value = runtime()
    await value._job(
        "mapping",
        RefreshInstrument(uuid4(), "Warrant", None),
        3600,
        AsyncMock(side_effect=FrankfurtSourceError(reason)),
    )
    assert value.jobs["mapping"]["status"] == "ERROR"
    assert value.jobs["mapping"]["reason"] == reason
    assert value._due["mapping"] == 4600
    assert "retry_after_seconds" not in value.jobs["mapping"]


async def test_completed_checks_still_show_due_backlog_without_counting_inflight_work():
    value = runtime()
    item = RefreshInstrument(uuid4(), "Warrant", None)
    for key in ("WARRANT_QUOTES:old", "WARRANT_QUOTES:running", "UNDERLYING_EOD:stock"):
        await value._job(key, item, 300, AsyncMock(return_value={"reason": "OK"}))
    value.timer = lambda: 1420
    value._current_jobs[RefreshLane.WARRANTS] = "WARRANT_QUOTES:running"
    # An idle EOD lane can be future-dated while warrants are behind schedule.
    value._due["UNDERLYING_EOD:stock"] = 2000
    status = value.status()
    assert status["pending_jobs"] == 0
    assert status["due_jobs"] == status["overdue_jobs"] == 1
    assert status["max_overdue_seconds"] == 120
    assert status["lanes"]["WARRANTS"]["overdue_jobs"] == 1
    assert status["lanes"]["UNDERLYINGS"]["due_jobs"] == 0
    # Unattempted work is due but has no invented historical deadline.
    value.jobs["WARRANT_QUOTES:new"] = {"status": "PENDING"}
    status = value.status()
    assert status["pending_jobs"] == 1
    assert status["due_jobs"] == 2
    assert status["overdue_jobs"] == 1
    # Reading status neither changes deadlines nor runs operations.
    assert value._due["WARRANT_QUOTES:old"] == 1300
    assert "WARRANT_QUOTES:new" not in value._due


async def test_retry_deadline_is_due_at_boundary_and_deferred_status_is_visible():
    value = runtime()
    await value._job(
        "FRANKFURT_MAPPING:retry",
        RefreshInstrument(uuid4(), "Warrant", None),
        3600,
        AsyncMock(side_effect=FrankfurtSourceError("FRANKFURT_REQUEST_THROTTLED")),
    )
    status = value.status()
    assert status["deferred_jobs"] == 1
    assert status["due_jobs"] == 0
    value.timer = lambda: 1015
    status = value.status()
    assert status["due_jobs"] == 1
    assert status["overdue_jobs"] == 0
    assert status["max_overdue_seconds"] == 0
