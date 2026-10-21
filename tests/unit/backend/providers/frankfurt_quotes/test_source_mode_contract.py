"""Synthetic characterization of existing per-process source/cache boundaries."""

import asyncio
import json
import os
from contextlib import asynccontextmanager
from datetime import timedelta

import httpx
import pytest

from app.core.config.frankfurt import FrankfurtSourceMode
from app.providers.frankfurt_quotes.client import FrankfurtSnapshotClient
from app.providers.frankfurt_quotes.schema import FrankfurtSourceError, assess_snapshot
from tests.unit.backend.providers.frankfurt_quotes.test_client import settings
from tests.unit.backend.providers.frankfurt_quotes.test_public import (
    public_settings,
    wire,
)
from tests.unit.backend.providers.frankfurt_quotes.test_schema import NOW, payload

HELD = "DE000VH2LU21"
OTHER = "DE000VH7S657"
MODES = tuple(FrankfurtSourceMode)


@asynccontextmanager
async def source(mode, tmp_path, monkeypatch, moment, *, cache_seconds=None, **overrides):
    data = payload()
    data["records"].append({**data["records"][0], "isin": OTHER, "wkn": "VH7S65"})
    path = tmp_path / "snapshot.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    accesses = {"http": 0, "file": 0}

    def respond(request):
        assert mode is not FrankfurtSourceMode.LOCAL_FILE, "Local source attempted HTTP"
        accesses["http"] += 1
        body = (
            wire(isin=request.url.params["isin"])
            if mode is FrankfurtSourceMode.PUBLIC_WEBSITE
            else data
        )
        return httpx.Response(200, json=body)

    if mode is FrankfurtSourceMode.PUBLIC_WEBSITE:
        config = public_settings(**overrides)
    elif mode is FrankfurtSourceMode.LOCAL_FILE:
        config = settings(
            source_mode=mode,
            local_file=str(path),
            snapshot_url=None,
            allowed_host=None,
            **overrides,
        )
    else:
        config = settings(**overrides)
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond), trust_env=False) as http:
        client = FrankfurtSnapshotClient(
            config,
            client=http,
            timer=lambda: moment[0],
            clock=lambda: NOW + timedelta(seconds=moment[0] - 100),
            cache_seconds=cache_seconds,
        )
        read_file = client._read_file

        def counted_file_read():
            accesses["file"] += 1
            return read_file()

        monkeypatch.setattr(client, "_read_file", counted_file_read)
        yield client, accesses, path


async def load(client, isin=HELD):
    if client.settings.source_mode is FrankfurtSourceMode.PUBLIC_WEBSITE:
        return await client.load_public(isin)
    return await client.load()


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("cache_seconds", [None, 300])
async def test_mode_cache_hits_expiry_and_identity(mode, cache_seconds, tmp_path, monkeypatch):
    moment = [100.0]
    async with source(mode, tmp_path, monkeypatch, moment, cache_seconds=cache_seconds) as (
        client,
        accesses,
        _path,
    ):
        first = await load(client)
        assert first[1:] == (NOW, False)
        assert client.request_delay_seconds() == 15
        moment[0] = 101
        hit = await load(client)
        assert hit == (*first[:2], True)
        assert client.last_success_at == NOW
        assert client.request_delay_seconds() == 14
        if mode is FrankfurtSourceMode.PUBLIC_WEBSITE:
            with pytest.raises(FrankfurtSourceError, match=r"^FRANKFURT_REQUEST_THROTTLED$"):
                await load(client, OTHER)
            assert first[0].isin == HELD
        else:
            shared = await load(client, OTHER)
            assert shared == hit
            other = assess_snapshot(
                shared[0],
                isin=OTHER,
                wkn="VH7S65",
                currency="EUR",
                now=NOW,
                retrieved_at=shared[1],
            )
            assert other.record.isin == OTHER and other.status == "AVAILABLE"
        assert sum(accesses.values()) == 1
        expiry = 100 + (cache_seconds or 15)
        moment[0] = expiry - 0.001
        assert await load(client) == (*first[:2], True)
        assert sum(accesses.values()) == 1
        moment[0] = expiry
        fresh = await load(client)
        assert fresh[0] == first[0]  # A new fetch does not rewrite original source timestamps.
        assert fresh[1:] == (NOW + timedelta(seconds=expiry - 100), False)
        assert client.request_delay_seconds() == 15
        assert accesses == (
            {"http": 0, "file": 2}
            if mode is FrankfurtSourceMode.LOCAL_FILE
            else {"http": 2, "file": 0}
        )
        if mode is FrankfurtSourceMode.PUBLIC_WEBSITE:
            moment[0] += 15
            other = await load(client, OTHER)
            assert other[0].isin == OTHER and other[2] is False
            assert accesses == {"http": 3, "file": 0}


@pytest.mark.asyncio
@pytest.mark.parametrize("code", [429, 503])
async def test_https_retry_after_survives_repeated_and_historical_reads(code):
    moment, calls = [100.0], []

    def respond(request):
        calls.append(request)
        return (
            httpx.Response(code, headers={"Retry-After": "120"})
            if len(calls) == 2
            else httpx.Response(200, json=payload())
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond), trust_env=False) as http:
        client = FrankfurtSnapshotClient(
            settings(),
            client=http,
            timer=lambda: moment[0],
            clock=lambda: NOW + timedelta(seconds=moment[0] - 100),
        )
        original = await client.load()
        for current in (115, 116, 130, 174, 234.999):
            moment[0] = current
            with pytest.raises(FrankfurtSourceError, match=f"^FRANKFURT_HTTP_{code}$"):
                await client.load()
            assert client.request_delay_seconds() == pytest.approx(235 - current)
            assert client.cached_after_error(f"FRANKFURT_HTTP_{code}") == original[:2]
            assert client.last_success_at == NOW
            assert len(calls) == 2
        moment[0] = 235
        recovered = await client.load()
        assert recovered[1:] == (NOW + timedelta(seconds=135), False)
        assert recovered[0] == original[0]
        assert client.last_error is None and len(calls) == 3
        assert client.request_delay_seconds() == 15


@pytest.mark.asyncio
@pytest.mark.parametrize("cancel_waiter", [False, True])
async def test_shared_snapshot_lock_coalesces_readers_and_releases_cancelled_waiter(
    cancel_waiter,
):
    entered, release, waiting = asyncio.Event(), asyncio.Event(), asyncio.Event()
    calls = []

    async def respond(request):
        calls.append(request)
        entered.set()
        await release.wait()
        return httpx.Response(200, json=payload())

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond), trust_env=False) as http:
        client = FrankfurtSnapshotClient(
            settings(), client=http, timer=lambda: 100, clock=lambda: NOW
        )

        async def second_reader():
            waiting.set()
            return await client.load()

        first = asyncio.create_task(client.load())
        second = None
        try:
            await asyncio.wait_for(entered.wait(), timeout=1)
            second = asyncio.create_task(second_reader())
            await asyncio.wait_for(waiting.wait(), timeout=1)
            assert not first.done() and not second.done()
            assert len(calls) == 1
            if cancel_waiter:
                second.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await second
            release.set()
            original = await asyncio.wait_for(first, timeout=1)
            if not cancel_waiter:
                assert await asyncio.wait_for(second, timeout=1) == (
                    *original[:2],
                    True,
                )
            assert await client.load() == (*original[:2], True)
            assert len(calls) == 1 and client.request_delay_seconds() == 15
        finally:
            release.set()
            tasks = [task for task in (first, second) if task is not None]
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)


@pytest.mark.asyncio
async def test_local_file_mtime_and_new_reads_do_not_refresh_old_market_time(tmp_path, monkeypatch):
    moment = [100.0]
    async with source(FrankfurtSourceMode.LOCAL_FILE, tmp_path, monkeypatch, moment) as (
        client,
        accesses,
        path,
    ):
        data = payload()
        old = NOW - timedelta(seconds=901)
        data["generated_at"] = old.isoformat()
        data["records"][0].update(bid_at=old.isoformat(), ask_at=old.isoformat())
        path.write_text(json.dumps(data), encoding="utf-8")
        initial_mtime = path.stat().st_mtime
        original = await client.load()
        for elapsed, expected_reads, expected_hit in (
            (1, 1, True),
            (15, 2, False),
            (30, 3, False),
        ):
            moment[0] = 100 + elapsed
            os.utime(path, (initial_mtime + elapsed, initial_mtime + elapsed))
            value, retrieved_at, hit = await client.load()
            assert value == original[0] and hit is expected_hit
            expected_retrieval = NOW if expected_hit else NOW + timedelta(seconds=elapsed)
            assert retrieved_at == expected_retrieval
            assessed = assess_snapshot(
                value,
                isin=HELD,
                wkn="VH2LU2",
                currency="EUR",
                now=NOW + timedelta(seconds=elapsed),
                retrieved_at=retrieved_at,
            )
            assert assessed.status == "STALE"
            assert assessed.reason == "FRANKFURT_SNAPSHOT_STALE"
            assert assessed.observed_at == assessed.snapshot_generated_at == old
            assert assessed.age_seconds == 901 + elapsed
            assert assessed.execution_usable is False
            assert accesses == {"http": 0, "file": expected_reads}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure,reason",
    [
        ("missing", "LOCAL_FILE_UNAVAILABLE"),
        ("large", "PAYLOAD_TOO_LARGE"),
        ("invalid", "SCHEMA_INVALID"),
        ("foreign", "SOURCE_MISMATCH"),
        ("delay", "FEED_DELAY_MISMATCH"),
    ],
)
async def test_local_failures_are_bounded_and_recover_only_after_backoff(
    failure, reason, tmp_path, monkeypatch
):
    moment = [100.0]
    async with source(
        FrankfurtSourceMode.LOCAL_FILE,
        tmp_path,
        monkeypatch,
        moment,
        max_response_bytes=1024,
    ) as (client, accesses, path):
        await client.load()
        assert accesses == {"http": 0, "file": 1}
        if failure == "missing":
            path.unlink()
        else:
            body = {
                "large": "x" * 1025,
                "invalid": "{",
                "foreign": json.dumps({**payload(), "source": "other"}),
                "delay": json.dumps({**payload(), "delay_seconds": 1}),
            }
            path.write_text(body[failure], encoding="utf-8")
        for current in (115, 116, 130, 174.999):
            moment[0] = current
            with pytest.raises(FrankfurtSourceError, match=f"^FRANKFURT_{reason}$"):
                await client.load()
            assert client.request_delay_seconds() == pytest.approx(175 - current)
            assert accesses == {"http": 0, "file": 2}
            assert client.cached_after_error("FRANKFURT_HTTP_503") is None
            assert client.last_success_at == NOW
        path.write_text(json.dumps(payload()), encoding="utf-8")
        moment[0] = 175
        assert (await client.load())[1:] == (NOW + timedelta(seconds=75), False)
        assert accesses == {"http": 0, "file": 3}


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize(
    "field,reason",
    [
        ("enabled", "DISABLED"),
        ("usage_approved", "USAGE_NOT_APPROVED"),
        ("contract_verified", "CONTRACT_NOT_VERIFIED"),
    ],
)
async def test_mode_permissions_block_before_any_access(mode, field, reason, tmp_path, monkeypatch):
    async with source(mode, tmp_path, monkeypatch, [100.0], **{field: False}) as (
        client,
        accesses,
        _path,
    ):
        with pytest.raises(FrankfurtSourceError, match=f"^FRANKFURT_{reason}$"):
            await load(client)
        assert accesses == {"http": 0, "file": 0}
        assert client.last_success_at is None and client.request_delay_seconds() == 0
