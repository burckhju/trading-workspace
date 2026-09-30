"""Issuer streams progress independently; only mapped Frankfurt routes are paced."""

import asyncio
from dataclasses import replace
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from tests.unit.backend.features.market_data.test_refresh import runtime, session_context

from app.features.market_data.domain.enums import MappingStatus
from app.features.market_data.domain.enums import MarketDataProvider as P
from app.features.market_data.service import refresh as module
from app.features.market_data.service.refresh import RefreshLane
from app.features.market_data.service.refresh_catalog import (
    RefreshInstrument,
    read_issuer_route_groups,
)


@pytest.mark.asyncio
async def test_issuer_jobs_finish_and_repeat_while_exchange_job_is_blocked(monkeypatch):
    value = runtime(auto_configure=False)
    value.container = replace(value.container, jpmorgan=object())
    exchange = RefreshInstrument(uuid4(), "Exchange", None, held=True)
    issuer = RefreshInstrument(uuid4(), "Issuer", None, held=True)
    monkeypatch.setattr(module, "read_catalog", AsyncMock(return_value=([exchange, issuer], [])))
    monkeypatch.setattr(
        module, "read_issuer_route_groups", AsyncMock(return_value=({issuer.id}, {issuer.id}))
    )
    exchange_started, issuer_done = asyncio.Event(), asyncio.Event()
    calls = []
    cancelled = []

    async def work(item, *, issuers_only=False):
        calls.append((item.id, issuers_only))
        if item == exchange:
            exchange_started.set()
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.append(item.id)
        issuer_done.set()
        return {"reason": "QUOTE_OBSERVATIONS_AVAILABLE"}

    value._warrant = work
    try:
        await value.run_once(wait_for_completion=False)
        await asyncio.wait_for(exchange_started.wait(), 1)
        await asyncio.wait_for(issuer_done.wait(), 1)
        await value._lane_tasks[RefreshLane.ISSUER_QUOTES]
        assert value.status()["lanes"]["ISSUER_QUOTES"]["pending_jobs"] == 0
        assert f"WARRANT_QUOTES:{issuer.id}" not in value.jobs
        await value.run_once(wait_for_completion=False)
        await value._lane_tasks[RefreshLane.ISSUER_QUOTES]
        assert len(calls) == 2
        value.timer = lambda: 1301
        issuer_done.clear()
        await value.run_once(wait_for_completion=False)
        await asyncio.wait_for(issuer_done.wait(), 1)
        assert calls == [(exchange.id, False), (issuer.id, True), (issuer.id, True)]
    finally:
        await value.stop()
    assert cancelled == [exchange.id] and not value.running
    assert all(key is None for key in value.status()["current_jobs"].values())


@pytest.mark.asyncio
async def test_mixed_mapping_keeps_both_jobs(monkeypatch):
    value = runtime(auto_configure=False)
    value.container = replace(value.container, jpmorgan=object())
    item = RefreshInstrument(uuid4(), "Mixed", None)
    monkeypatch.setattr(module, "read_catalog", AsyncMock(return_value=([item], [])))
    monkeypatch.setattr(
        module, "read_issuer_route_groups", AsyncMock(return_value=({item.id}, set()))
    )
    value._warrant = AsyncMock(return_value={"reason": "OK"})
    await value.run_once()
    assert set(value.jobs) == {f"WARRANT_QUOTES:{item.id}", f"ISSUER_QUOTES:{item.id}"}
    assert value._warrant.await_count == 2


@pytest.mark.asyncio
async def test_unmapped_routes_are_skipped_and_issuer_routes_are_isolated():
    value = runtime(auto_configure=False)
    item = RefreshInstrument(uuid4(), "Mixed", None)
    listings = [SimpleNamespace(id=uuid4(), quotation_currency_code="EUR") for _ in range(4)]

    def mapping(index, provider, status=MappingStatus.ACTIVE, validated=True):
        return SimpleNamespace(
            warrant_listing_id=listings[index].id,
            provider=provider,
            status=status,
            validated_at=datetime.now(UTC) if validated else None,
        )

    mappings = [
        mapping(0, P.JPMORGAN),
        mapping(1, P.FRANKFURT_QUOTES),
        mapping(1, P.GETTEX_DELAYED),
        mapping(2, P.FRANKFURT_QUOTES, MappingStatus.DISABLED),
        mapping(2, P.MORGAN_STANLEY, validated=False),
    ]
    session = SimpleNamespace(
        scalars=AsyncMock(side_effect=[listings, mappings, listings, mappings])
    )
    value.container = replace(
        value.container, database=SimpleNamespace(session_context=lambda: session_context(session))
    )
    value._resolver = SimpleNamespace(
        resolve_selected=AsyncMock(return_value=SimpleNamespace(attempts=(), result=None))
    )
    value.container = replace(value.container, frankfurt=object())
    value._pace_other = AsyncMock()
    issuer = await value._warrant(item, issuers_only=True)
    assert issuer["attempted_route_count"] == 1
    value._pace.assert_not_awaited()
    value._pace_other.assert_not_awaited()
    normal = await value._warrant(item)
    assert normal["attempted_route_count"] == 2
    value._pace.assert_awaited_once()
    assert [c.args[0] for c in value._resolver.resolve_selected.await_args_list] == [
        "JPMORGAN",
        "FRANKFURT_QUOTES",
        "GETTEX_DELAYED",
    ]


@pytest.mark.asyncio
async def test_catalog_groups_are_workspace_scoped_and_do_not_drop_mixed_sources():
    one, both, other, workspace = uuid4(), uuid4(), uuid4(), uuid4()
    rows = [
        (one, P.JPMORGAN),
        (both, P.MORGAN_STANLEY),
        (both, P.FRANKFURT_QUOTES),
        (other, P.GETTEX_DELAYED),
    ]
    session = SimpleNamespace(execute=AsyncMock(return_value=SimpleNamespace(all=lambda: rows)))
    database = SimpleNamespace(session_context=lambda: session_context(session))
    assert await read_issuer_route_groups(database, workspace) == ({one, both}, {one})
    query = session.execute.call_args.args[0]
    params = query.compile().params
    assert sum(value == workspace for value in params.values()) == 2
    sql = str(query)
    assert "validated_at IS NOT NULL" in sql and "lifecycle_status" in sql and "status" in sql
