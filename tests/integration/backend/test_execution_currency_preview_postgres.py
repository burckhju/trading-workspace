"""Proposed execution currency on guarded disposable PostgreSQL, never user data."""

import asyncio
from collections.abc import Iterator
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import text
from tests.integration.backend.learning.test_journal_write_postgres import (
    journal_database as guarded_database,
)
from tests.integration.backend.test_currency_source_evidence_postgres import (
    evidence_url,
    historical,
    venue,
)
from tests.integration.backend.test_execution_currency_reuse_postgres import (
    _book,
    _buy,
    _correct,
    _payload,
    _post,
)
from tests.integration.backend.test_realized_gross_report_postgres import (
    DECLARATION,
    _client,
    _state,
)
from tests.integration.backend.test_trade_capture_safety import BASE, product
from tests.integration.backend.test_usd_chf_currency_references import _migrate

from app.features.trade_position.persistence.repositories import (
    SqlAlchemyExecutionRecordRepository,
)


@pytest.fixture
def preview_database() -> Iterator[str]:
    yield from guarded_database.__wrapped__()


@pytest.fixture(autouse=True)
def forbid_external_calls(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    asynchronous = AsyncMock(side_effect=AssertionError("External HTTP forbidden"))
    synchronous = Mock(side_effect=AssertionError("External HTTP forbidden"))
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", asynchronous)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", synchronous)
    yield
    asynchronous.assert_not_awaited()
    synchronous.assert_not_called()


def query(side="BUY", day="2026-08-05"):
    return {"side": side, "executed_on": day, "execution_timezone": "Europe/Vienna"}


async def preview(client, identity, *, kind="trades", side="SELL", day="2026-08-20"):
    response = await client.get(
        f"{BASE}/{kind}/{identity}/execution-currency-preview", params=query(side, day)
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_initial_preview_and_actual_capture_share_historical_sources_without_confirmation_writes(
    preview_database,
):
    _migrate(preview_database, "head")

    async def exercise():
        async with _client(preview_database) as (client, database):
            pid = await product(client)
            venue_id = await venue(client)
            await _post(
                client,
                f"/api/v1/warrants/{pid}/listings",
                {"trading_venue_id": venue_id, "quotation_currency_code": "EUR"},
            )
            before = await _state(database.engine)
            unknown = await preview(client, pid, kind="products", side="BUY", day="2026-08-05")
            assert unknown["currency_code"] is None and unknown["source"] == "UNKNOWN"
            assert await _state(database.engine) == before  # A current EUR listing proves nothing.

            source = await _post(client, evidence_url(pid), historical(venue_id))
            before = await _state(database.engine)
            known = await preview(client, pid, kind="products", side="BUY", day="2026-08-05")
            assert known["currency_code"] == "EUR" and known["source"] == "HISTORICAL_LISTINGS"
            assert known["evidence_ids"] == [source["id"]]
            assert known["evidence"][0]["source_reference"] == source["source_reference"]
            assert known["confirmation_ids"] == known["source_execution_ids"] == []
            outside = await preview(client, pid, kind="products", side="BUY", day="2026-09-01")
            assert outside["currency_code"] is None
            assert await _state(database.engine) == before

            trade_id, bought = await _buy(client, None, product_id=pid)
            assert bought["currency_confirmation"] is None
            assert bought["currency_resolution"] == known
            assert (await _state(database.engine))["execution_currency_confirmations"] == []
            await _post(
                client,
                evidence_url(pid),
                {
                    "kind": "EXECUTION_DOCUMENT",
                    "source_reference": "Synthetic statement for this earlier BUY only",
                    "request_id": str(uuid4()),
                    "confirmation": "CONFIRM_SOURCE_REVIEW",
                    "trade_id": trade_id,
                    "execution_id": bought["id"],
                    "currency_code": "CHF",
                },
            )
            before = await _state(database.engine)
            assert (
                await preview(client, pid, kind="products", side="BUY", day="2026-08-05") == known
            )
            assert await _state(database.engine) == before
            assert before["execution_currency_confirmations"] == []

    asyncio.run(exercise())


def test_trade_preview_uses_effective_buys_exact_time_and_corrections_without_mutation(
    preview_database,
):
    _migrate(preview_database, "head")

    async def exercise():
        async with _client(preview_database) as (client, database):
            trade_id, first = await _buy(client)
            before = await _state(database.engine)
            for side in ("BUY", "SELL"):
                known = await preview(client, trade_id, side=side)
                assert known["currency_code"] == "EUR" and known["source"] == "PRIOR_BUYS"
                assert known["source_execution_ids"] == [first["id"]]
                assert known["confirmation_ids"] == [first["currency_confirmation"]["id"]]
            assert (await preview(client, trade_id, day="2026-08-04"))["currency_code"] is None
            for kind in ("products", "trades"):
                missing = await client.get(
                    f"{BASE}/{kind}/{uuid4()}/execution-currency-preview",
                    params=query(),
                )
                assert missing.status_code == 404
            assert await _state(database.engine) == before

            corrected = await _correct(
                client, trade_id, first["id"], "BUY", 100, "2.50", "2026-08-07"
            )
            before = await _state(database.engine)
            assert (await preview(client, trade_id, day="2026-08-06"))["currency_code"] is None
            result = await preview(client, trade_id)
            assert result["currency_code"] == "EUR" and result["source"] == "PRIOR_BUYS"
            assert result["source_execution_ids"] == [corrected["id"], first["id"]]
            assert result["confirmation_ids"] == [first["currency_confirmation"]["id"]]
            assert await _state(database.engine) == before

            await _book(client, trade_id, "purchases", _payload(50, "3.00", "2026-08-21", "USD"))
            before = await _state(database.engine)
            result = await preview(client, trade_id, day="2026-08-22")
            assert result["currency_code"] is None and result["source"] == "MIXED"
            assert len(result["confirmation_ids"]) == 2
            assert await _state(database.engine) == before

    asyncio.run(exercise())


def test_preview_snapshot_stays_consistent_while_explicit_confirmation_changes(
    preview_database, monkeypatch
):
    _migrate(preview_database, "head")

    async def exercise():
        async with _client(preview_database) as (client, database):
            trade_id, first = await _buy(client)
            entered, resume = asyncio.Event(), asyncio.Event()
            original = SqlAlchemyExecutionRecordRepository.list_for_trade
            pause_once = True

            async def paused(repository, identity: UUID):
                nonlocal pause_once
                if pause_once:
                    pause_once = False
                    assert (
                        await repository._session.execute(text("SHOW transaction_isolation"))
                    ).scalar_one() == "repeatable read"
                    assert (
                        await repository._session.execute(text("SHOW transaction_read_only"))
                    ).scalar_one() == "on"
                    entered.set()
                    await asyncio.wait_for(resume.wait(), timeout=15)
                return await original(repository, identity)

            monkeypatch.setattr(SqlAlchemyExecutionRecordRepository, "list_for_trade", paused)
            pending = asyncio.create_task(preview(client, trade_id))
            await asyncio.wait_for(entered.wait(), timeout=10)
            try:
                changed = await asyncio.wait_for(
                    _post(
                        client,
                        f"{BASE}/trades/{trade_id}/executions/{first['id']}/currency-confirmations",
                        DECLARATION
                        | {
                            "currency_code": "USD",
                            "request_id": str(uuid4()),
                            "supersedes_confirmation_id": first["currency_confirmation"]["id"],
                        },
                    ),
                    timeout=5,
                )
                assert not pending.done()  # A source preview must not acquire a command lock.
            finally:
                resume.set()
            old = await asyncio.wait_for(pending, timeout=10)
            assert old["currency_code"] == "EUR"
            assert old["confirmation_ids"] == [first["currency_confirmation"]["id"]]
            before = await _state(database.engine)
            current = await preview(client, trade_id)
            assert current["currency_code"] == "USD"
            assert current["confirmation_ids"] == [changed["id"]]
            assert len(before["execution_records"]) == 1
            assert len(before["execution_currency_confirmations"]) == 2
            assert await _state(database.engine) == before

    asyncio.run(exercise())
