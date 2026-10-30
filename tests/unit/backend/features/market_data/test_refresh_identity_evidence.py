"""Real SQL, retained providers and the existing status API share quote evidence."""

import asyncio
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from tests.unit.backend.features.market_data import test_retained_quotes as retained_tests

from app.core.config import Settings
from app.core.config.frankfurt import FrankfurtSourceMode
from app.core.di import ApplicationContainer
from app.features.market_data.api.router import router
from app.features.market_data.domain.enums import MarketDataProvider
from app.features.market_data.persistence.models import (
    WarrantProviderMappingModel,
    WarrantQuoteObservationModel,
)
from app.features.market_data.service import refresh as refresh_module
from app.features.market_data.service import retained_quotes as retained_module
from app.features.market_data.service.errors import MarketDataTimeoutError
from app.features.market_data.service.quote_history import QuoteHistoryReader
from app.features.market_data.service.refresh import MarketDataRefreshRuntime
from app.features.market_data.service.refresh_catalog import RefreshInstrument

context = retained_tests.context
NOW = datetime(2026, 10, 30, 12, tzinfo=UTC)
PROVIDER = MarketDataProvider.FRANKFURT_QUOTES


@pytest.fixture
def clock(monkeypatch):
    value = SimpleNamespace(at=NOW, tick=1000.0)

    class ControlledDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return value.at.astimezone(tz) if tz is not None else value.at.replace(tzinfo=None)

    monkeypatch.setattr(refresh_module, "datetime", ControlledDateTime)
    monkeypatch.setattr(retained_module, "datetime", ControlledDateTime)
    return value


def advance(clock, seconds=300):
    clock.at += timedelta(seconds=seconds)
    clock.tick += seconds


def fresh_result(c, at):
    return replace(
        c.result,
        retrieved_at=at,
        data=replace(
            c.result.data,
            bid=Decimal("2.40"),
            ask=Decimal("2.45"),
            reference_price=None,
            reference_price_type=None,
            observed_at=at - timedelta(seconds=5),
            assessed_at=at,
            source_mode="NORMALIZED_SNAPSHOT",
            max_quote_age_seconds=900,
            trading_status="OPEN",
        ),
    )


def runtime(c, clock):
    c.provider.settings = SimpleNamespace(source_mode=FrankfurtSourceMode.HTTPS_JSON)
    container = ApplicationContainer(
        settings=Settings(
            _env_file=None,
            environment="test",
            market_data={
                "refresh": {
                    "enabled": True,
                    "workspace_id": c.request.workspace_id,
                    "auto_configure": False,
                }
            },
        ),
        database=c.database,
        frankfurt=c.provider,
    )
    return MarketDataRefreshRuntime(container, timer=lambda: clock.tick)


async def refresh(value, c):
    item = RefreshInstrument(c.warrant, "Persisted quote", retained_tests.ISIN)
    key = f"WARRANT_QUOTES:{item.id}"
    await value._job(key, item, 300, lambda: value._warrant(item))
    return value.jobs[key]


def source(job, identity=None):
    return next(
        check
        for check in job["diagnostics"]["checks"]
        if check["kind"] == "SOURCE" and (identity is None or check["identity_key"] == identity)
    )


def app_for(value):
    app = FastAPI()
    app.include_router(router)
    app.state.market_data_refresh = value
    return app


async def history(c, at):
    async with c.database.session_context() as session:
        return await QuoteHistoryReader(session).report(c.request.workspace_id, c.warrant, now=at)


@pytest.mark.asyncio
async def test_persisted_quote_outage_and_real_recovery_are_visible_without_poll_side_effects(
    context, clock
):
    c = context
    value = runtime(c, clock)
    c.provider.get_warrant_listing_quote.return_value = fresh_result(c, clock.at)
    try:
        initial = await refresh(value, c)
        identity = await value._quote_identity(c.request, PROVIDER)
        check = source(initial)
        assert identity is not None and check["identity_key"] == identity.key
        assert check["qualified_success"] is True
        assert check["last_success_at"] == NOW
        assert initial["quotes"][0]["cache_status"] == "MISS"
        assert initial["quotes"][0]["quality_status"] == "VALID"
        with Session(c.database.engine) as session:
            row = session.scalar(select(WarrantQuoteObservationModel))
            original_payload = deepcopy(row.payload)
            assert row.identity_key == identity.key

        c.provider.get_warrant_listing_quote.side_effect = MarketDataTimeoutError(
            "FRANKFURT_TRANSPORT_TIMEOUT"
        )
        advance(clock)
        failed = await refresh(value, c)
        check = source(failed)
        assert failed["status"] == "AVAILABLE"
        assert check["retained_quote"] is True
        assert check["qualified_success"] is False
        assert check["last_success_at"] == NOW
        assert check["consecutive_failures"] == 1
        assert check["recovered_at"] is None
        assert failed["quotes"][0]["retrieved_at"] == NOW
        assert failed["quotes"][0]["observed_at"] == NOW - timedelta(seconds=5)
        snapshot, deadlines = deepcopy(value.jobs), dict(value._due)
        calls = c.provider.get_warrant_listing_quote.await_count
        async with AsyncClient(
            transport=ASGITransport(app=app_for(value)), base_url="http://test"
        ) as client:
            for _ in range(2):
                response = await client.get("/api/v1/market-data/refresh/status")
                assert response.status_code == 200
                displayed = source(response.json()["jobs"][0])
                assert displayed["identity_key"] == identity.key
                assert displayed["retained_quote"] is True
                assert displayed["consecutive_failures"] == 1
                assert datetime.fromisoformat(displayed["last_success_at"]) == NOW
                assert displayed["recovered_at"] is None
        assert c.provider.get_warrant_listing_quote.await_count == calls
        assert value.jobs == snapshot and value._due == deadlines

        advance(clock)
        assert source(await refresh(value, c))["consecutive_failures"] == 2
        with Session(c.database.engine) as session:
            assert session.scalar(select(WarrantQuoteObservationModel)).payload == original_payload
        advance(clock)
        c.provider.get_warrant_listing_quote.side_effect = None
        c.provider.get_warrant_listing_quote.return_value = fresh_result(c, clock.at)
        recovered = source(await refresh(value, c))
        assert recovered["identity_key"] == identity.key
        assert recovered["qualified_success"] is True
        assert recovered["consecutive_failures"] == 0
        assert recovered["last_success_at"] == recovered["recovered_at"] == clock.at
        report = await history(c, clock.at)
        assert len(report.items) == 4
        assert report.segments[0].statuses["REQUEST_FAILED"] == 2
        assert report.segments[0].statuses["TWO_SIDED_WITHIN_AGE_LIMIT"] == 2
        assert report.items[0].quote.observed_at == clock.at - timedelta(seconds=5)
    finally:
        await value.stop()
        c.database.engine.dispose()


@pytest.mark.asyncio
async def test_mapping_revision_after_resolver_success_keeps_old_failure_and_blocks_false_recovery(
    context, clock, monkeypatch
):
    c = context
    value = runtime(c, clock)
    c.provider.get_warrant_listing_quote.side_effect = MarketDataTimeoutError(
        "FRANKFURT_TRANSPORT_TIMEOUT"
    )
    entered, release = asyncio.Event(), asyncio.Event()
    task = None
    try:
        first = await refresh(value, c)
        old_identity = source(first)["identity_key"]
        assert source(first)["consecutive_failures"] == 1
        advance(clock)
        c.provider.get_warrant_listing_quote.side_effect = None
        c.provider.get_warrant_listing_quote.return_value = fresh_result(c, clock.at)
        resolve = value._resolver.resolve_selected

        async def pause_after_real_resolution(provider, request):
            result = await resolve(provider, request)
            assert result.result is not None
            entered.set()
            await release.wait()
            return result

        monkeypatch.setattr(value._resolver, "resolve_selected", pause_after_real_resolution)
        task = asyncio.create_task(refresh(value, c))
        await asyncio.wait_for(entered.wait(), timeout=1)
        with Session(c.database.engine) as session:
            mapping = session.get(WarrantProviderMappingModel, c.mapping)
            mapping.version += 1
            mapping.updated_at = clock.at
            session.commit()
        current = await value._quote_identity(c.request, PROVIDER)
        assert current is not None and current.key != old_identity
        release.set()
        changed = await asyncio.wait_for(task, timeout=1)
        check = source(changed, old_identity)
        assert changed["status"] == "AVAILABLE"
        assert changed["source_attempts"][0]["identity_changed"] is True
        assert changed["source_attempts"][0]["identity_verified"] is False
        assert check["quote_status"] == "INVALID"
        assert check["qualified_success"] is False
        assert check["reason"] == "WARRANT_QUOTE_IDENTITY_CHANGED_DURING_REFRESH"
        assert check["consecutive_failures"] == 2
        assert check["last_success_at"] is check["recovered_at"] is None
        with Session(c.database.engine) as session:
            assert session.scalar(select(WarrantQuoteObservationModel)).identity_key == old_identity

        monkeypatch.setattr(value._resolver, "resolve_selected", resolve)
        advance(clock)
        c.provider.get_warrant_listing_quote.return_value = fresh_result(c, clock.at)
        updated = await refresh(value, c)
        old, new = source(updated, old_identity), source(updated, current.key)
        assert old["observed_in_latest_run"] is False
        assert old["consecutive_failures"] == 2 and old["recovered_at"] is None
        assert new["qualified_success"] is True and new["consecutive_failures"] == 0
        assert new["recovered_at"] is None
        with Session(c.database.engine) as session:
            assert session.scalar(select(WarrantQuoteObservationModel)).identity_key == current.key
    finally:
        release.set()
        if task is not None:
            await task
        await value.stop()
        c.database.engine.dispose()


@pytest.mark.asyncio
async def test_restart_preserves_original_quote_and_history_but_not_process_local_failure_counters(
    context, clock
):
    c = context
    first_runtime = runtime(c, clock)
    restarted = None
    c.provider.get_warrant_listing_quote.return_value = fresh_result(c, clock.at)
    try:
        initial = await refresh(first_runtime, c)
        identity = source(initial)["identity_key"]
        c.provider.get_warrant_listing_quote.side_effect = MarketDataTimeoutError(
            "FRANKFURT_TRANSPORT_TIMEOUT"
        )
        advance(clock)
        before_restart = await refresh(first_runtime, c)
        assert source(before_restart)["consecutive_failures"] == 1
        stored_history = await history(c, clock.at)
        with Session(c.database.engine) as session:
            stored_quote = deepcopy(session.scalar(select(WarrantQuoteObservationModel)).payload)
        await first_runtime.stop()
        c.database.engine.dispose()
        c.database = retained_tests.SqlDatabase(c.url)
        restarted = runtime(c, clock)
        assert restarted.status()["jobs"] == []
        assert await history(c, clock.at) == stored_history
        advance(clock)
        restored = await refresh(restarted, c)
        check = source(restored)
        assert restored["diagnostics"]["scope"] == "PROCESS_LOCAL"
        assert check["identity_key"] == identity
        assert check["retained_quote"] is True
        assert check["quote_observed_at"] == NOW - timedelta(seconds=5)
        assert check["quote_retrieved_at"] == NOW
        assert check["qualified_success"] is False
        assert check["consecutive_failures"] == 1
        assert check["last_success_at"] is check["recovered_at"] is None
        with Session(c.database.engine) as session:
            assert session.scalar(select(WarrantQuoteObservationModel)).payload == stored_quote
        report = await history(c, clock.at)
        assert len(report.items) == 3
        assert report.segments[0].statuses["REQUEST_FAILED"] == 2
        assert report.segments[0].statuses["TWO_SIDED_WITHIN_AGE_LIMIT"] == 1
        assert report.items[-1].quote.observed_at == NOW - timedelta(seconds=5)
        assert report.items[-1].retrieved_at == NOW
        async with AsyncClient(
            transport=ASGITransport(app=app_for(restarted)), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/market-data/refresh/status")
            assert response.status_code == 200
            displayed = source(response.json()["jobs"][0])
            assert displayed["retained_quote"] is True
            assert displayed["consecutive_failures"] == 1
            assert displayed["last_success_at"] is None
            assert datetime.fromisoformat(displayed["quote_retrieved_at"]) == NOW
    finally:
        await first_runtime.stop()
        if restarted is not None:
            await restarted.stop()
        c.database.engine.dispose()
