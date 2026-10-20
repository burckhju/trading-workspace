"""Actual owner currency reuse and correction races in isolated PostgreSQL databases.

Only explicit user declarations create currency rows. Every execution is captured
through its registered owner API; a derived currency is checked against its exact
purchase/confirmation sources. No application lifespan or external provider runs.
"""

import asyncio
from collections.abc import Iterator
from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.backend.learning.test_journal_write_postgres import (
    journal_database as guarded_database,
)
from tests.integration.backend.test_realized_gross_report_postgres import (
    DECLARATION,
    QUERY,
    _capture_reference,
    _client,
    _report,
    _state,
)
from tests.integration.backend.test_trade_capture_safety import BASE, product
from tests.integration.backend.test_usd_chf_currency_references import _migrate

from app.features.performance.domain.models import ExecutionFact
from app.features.performance.service.reader import RealizedGrossSnapshotReader


@pytest.fixture
def reuse_database() -> Iterator[str]:
    yield from guarded_database.__wrapped__()


@pytest.fixture(autouse=True)
def forbid_external_calls(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    external_async = AsyncMock(side_effect=AssertionError("External HTTP forbidden"))
    external_sync = Mock(side_effect=AssertionError("External HTTP forbidden"))
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", external_async)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", external_sync)
    yield
    external_async.assert_not_awaited()
    external_sync.assert_not_called()


def _payload(quantity: int, price: str, day: str, currency: str | None = None) -> dict:
    result = {
        "quantity": quantity,
        "price_per_unit": price,
        "executed_on": day,
        "execution_timezone": "Europe/Berlin",
        "request_id": str(uuid4()),
    }
    if currency is not None:
        result["currency_confirmation"] = DECLARATION | {"currency_code": currency}
    return result


async def _post(client: AsyncClient, path: str, payload: dict) -> dict:
    response = await client.post(path, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


async def _buy(client: AsyncClient, currency: str | None = "EUR") -> tuple[str, dict]:
    captured = await _post(
        client,
        BASE + "/purchases/external",
        {"product_id": await product(client)} | _payload(100, "2.00", "2026-08-05", currency),
    )
    return captured["trade"]["id"], captured["execution"]


async def _book(client: AsyncClient, trade_id: str, action: str, payload: dict) -> dict:
    return (await _post(client, f"{BASE}/trades/{trade_id}/{action}", payload))["execution"]


async def _correct(
    client: AsyncClient,
    trade_id: str,
    execution_id: str,
    side: str,
    quantity: int,
    price: str,
    day: str,
) -> dict:
    payload = _payload(quantity, price, day)
    del payload["request_id"]
    return await _book(
        client, trade_id, f"executions/{execution_id}/corrections", payload | {"side": side}
    )


async def _timeline(client: AsyncClient, trade_id: str) -> dict[str, dict]:
    response = await client.get(f"{BASE}/trades/{trade_id}/timeline")
    assert response.status_code == 200, response.text
    return {row["id"]: row for row in response.json() if row["kind"] == "EXECUTION"}


def _resolution(
    code: str | None, source: str, execution_ids: list[str], confirmation_ids: list[str]
) -> dict:
    return {
        "currency_code": code,
        "source": source,
        "source_execution_ids": execution_ids,
        "confirmation_ids": confirmation_ids,
    }


def test_one_confirmed_purchase_qualifies_sales_additional_purchase_and_price_correction(
    reuse_database: str,
) -> None:
    _migrate(reuse_database, "head")

    async def exercise() -> None:
        async with _client(reuse_database) as (client, database):
            _, trade_id, ids = await _capture_reference(client, initial_currency_only=True)
            before = await _state(database.engine)
            assert len(before["execution_records"]) == 6
            assert len(before["execution_currency_confirmations"]) == 1
            confirmation_id = str(before["execution_currency_confirmations"][0]["id"])
            report = await _report(client)
            assert report["definition_version"] == "realized-gross-sell-v2"
            assert report["summary"]["status"] == "COMPLETE"
            assert report["summary"]["total"] == "10.0000000000"
            assert report["summary"]["total_display"] == "10.00"
            assert report["counts"]["usable"] == 2 and report["counts"]["unresolved"] == 0
            timeline = await _timeline(client, trade_id)
            for index, source in enumerate(report["sources"]):
                assert source["execution_id"] == ids[index]
                expected = _resolution(
                    "EUR",
                    "USER_CONFIRMED" if index == 0 else "PRIOR_BUYS",
                    [ids[0]] if index < 4 else [ids[0], ids[3]],
                    [confirmation_id],
                )
                assert source["currency_resolution"] == expected
                assert timeline[ids[index]]["currency_resolution"] == expected
                if index:
                    assert source["currency_confirmation"] is None
                    assert source["currency_history"] == []
                    assert timeline[ids[index]]["currency_confirmation"] is None
            selected = [row for row in report["items"] if row["status"] == "USABLE"]
            assert [row["realized_gross_pnl_delta_display"] for row in selected] == [
                "30.00",
                "-20.00",
            ]
            assert all(row["currency_confirmation_ids"] == [confirmation_id] for row in selected)
            assert selected[1]["cost_basis_execution_ids"] == ids[:4]
            all_months = QUERY | {"from_date": "2026-08-01", "to_date": "2026-10-31"}
            assert (await _report(client, all_months))["summary"]["total_display"] == "50.00"
            assert (await _report(client))["basis"]["id"] == report["basis"]["id"]
            assert await _state(database.engine) == before

            corrected = await _correct(client, trade_id, ids[4], "SELL", 40, "3.00", "2026-09-12")
            assert corrected["id"] != ids[4]
            assert corrected["currency_confirmation"] is None
            assert corrected["currency_resolution"] == _resolution(
                "EUR", "PRIOR_BUYS", [ids[0], ids[3]], [confirmation_id]
            )
            after_correction = await _state(database.engine)
            assert len(after_correction["execution_records"]) == 7
            assert (
                after_correction["execution_currency_confirmations"]
                == before["execution_currency_confirmations"]
            )
            changed = await _report(client)
            assert changed["basis"]["id"] != report["basis"]["id"]
            assert changed["summary"]["total_display"] == "30.00"
            assert changed["counts"]["examined"] == 4
            assert ids[4] not in {row["execution_id"] for row in changed["items"]}
            sources = {row["execution_id"]: row for row in changed["sources"]}
            assert sources[ids[4]]["is_effective"] is False
            assert sources[ids[4]]["superseded_by_execution_id"] == corrected["id"]
            assert sources[corrected["id"]]["supersedes_execution_id"] == ids[4]
            whole = await _report(client, all_months)
            position = await client.get(f"{BASE}/trades/{trade_id}/position")
            assert position.status_code == 200 and position.json()["is_closed"]
            assert (
                Decimal(whole["summary"]["total"])
                == Decimal(position.json()["realized_gross_pnl"])
                == Decimal("70")
            )
            assert (await _report(client))["basis"]["id"] == changed["basis"]["id"]
            assert await _state(database.engine) == after_correction

    asyncio.run(exercise())


@pytest.mark.parametrize("backdate_known_purchase", [False, True])
def test_later_known_purchase_never_retroactively_qualifies_an_earlier_unknown_buy(
    reuse_database: str, backdate_known_purchase: bool
) -> None:
    _migrate(reuse_database, "head")

    async def exercise() -> None:
        async with _client(reuse_database) as (client, database):
            trade_id, first = await _buy(client, "EUR" if backdate_known_purchase else None)
            additional = await _book(
                client,
                trade_id,
                "purchases",
                _payload(100, "4.00", "2026-08-20", None if backdate_known_purchase else "EUR"),
            )
            sale = await _book(client, trade_id, "sales", _payload(30, "4.00", "2026-09-02"))
            if backdate_known_purchase:
                assert sale["currency_resolution"]["currency_code"] == "EUR"
                # Move the confirmed first BUY after the formerly inherited additional BUY.
                # Both effective BUYs still precede the sale; the owner's quantity history is valid.
                replacement = await _correct(
                    client, trade_id, first["id"], "BUY", 100, "2.00", "2026-08-25"
                )
                assert replacement["currency_resolution"] == _resolution(
                    "EUR",
                    "REPLACED_EXECUTION",
                    [first["id"]],
                    [first["currency_confirmation"]["id"]],
                )
                unknown_id = additional["id"]
            else:
                unknown_id = first["id"]
                assert sale["currency_resolution"]["currency_code"] is None

            before = await _state(database.engine)
            report = await _report(client)
            assert report["summary"]["status"] == "NOT_COMPUTABLE"
            assert report["summary"]["total"] is None
            assert report["summary"]["subtotal"] is None
            assert report["counts"]["unresolved"] == 1 and report["counts"]["usable"] == 0
            assert report["items"][0]["status"] == "NOT_COMPUTABLE"
            assert "CURRENCY_UNKNOWN" in report["items"][0]["reasons"]
            assert report["items"][0]["realized_gross_pnl_delta"] is None
            timeline = await _timeline(client, trade_id)
            assert timeline[unknown_id]["currency_resolution"]["source"] == "UNKNOWN"
            assert timeline[unknown_id]["currency_confirmation"] is None
            assert timeline[sale["id"]]["currency_resolution"]["source"] == "UNKNOWN"
            assert len(before["execution_currency_confirmations"]) == 1
            assert (await _report(client))["basis"]["id"] == report["basis"]["id"]
            assert await _state(database.engine) == before

    asyncio.run(exercise())


def test_mixed_costs_and_explicit_conflicting_sales_preserve_facts_and_partial_coverage(
    reuse_database: str,
) -> None:
    _migrate(reuse_database, "head")

    async def exercise() -> None:
        async with _client(reuse_database) as (client, database):
            complete_trade, _ = await _buy(client)
            await _book(client, complete_trade, "sales", _payload(10, "3.00", "2026-09-01"))

            mixed_trade, first = await _buy(client)
            additional = await _book(
                client, mixed_trade, "purchases", _payload(100, "4.00", "2026-08-20", "USD")
            )
            mixed_sale = await _book(
                client, mixed_trade, "sales", _payload(30, "4.00", "2026-09-02")
            )
            assert mixed_sale["currency_confirmation"] is None
            assert mixed_sale["currency_resolution"] == _resolution(
                None,
                "MIXED",
                [first["id"], additional["id"]],
                [first["currency_confirmation"]["id"], additional["currency_confirmation"]["id"]],
            )

            conflicting_trade, conflicting_buy = await _buy(client)
            conflicting_sale = await _book(
                client, conflicting_trade, "sales", _payload(30, "4.00", "2026-09-03", "USD")
            )
            explicit = conflicting_sale["currency_confirmation"]
            assert conflicting_sale["currency_resolution"] == _resolution(
                "USD", "USER_CONFIRMED", [conflicting_sale["id"]], [explicit["id"]]
            )
            before = await _state(database.engine)
            eur = await _report(client)
            assert eur["summary"]["status"] == "PARTIAL"
            assert eur["summary"]["total"] is None
            assert eur["summary"]["subtotal_display"] == "10.00"
            assert eur["counts"]["usable"] == eur["counts"]["unresolved"] == 1
            assert eur["counts"]["excluded"] == 1
            mixed = next(row for row in eur["items"] if row["execution_id"] == mixed_sale["id"])
            assert mixed["status"] == "NOT_COMPUTABLE" and "CURRENCY_MIXED" in mixed["reasons"]
            assert mixed["realized_gross_pnl_delta"] is None
            usd = await _report(client, QUERY | {"report_currency": "USD"})
            conflict = next(
                row for row in usd["items"] if row["execution_id"] == conflicting_sale["id"]
            )
            assert conflict["currency_code"] == "USD"
            assert conflict["status"] == "NOT_COMPUTABLE"
            assert "CURRENCY_MIXED" in conflict["reasons"]
            assert usd["summary"]["status"] == "NOT_COMPUTABLE"
            assert usd["summary"]["total"] is None
            assert usd["summary"]["subtotal"] is None
            sources = {row["execution_id"]: row for row in usd["sources"]}
            assert sources[conflicting_sale["id"]]["currency_confirmation"]["id"] == explicit["id"]
            assert (
                sources[conflicting_sale["id"]]["currency_resolution"]
                == conflicting_sale["currency_resolution"]
            )
            assert sources[conflicting_buy["id"]]["currency_resolution"]["currency_code"] == "EUR"
            assert len(before["execution_currency_confirmations"]) == 5
            assert await _state(database.engine) == before

    asyncio.run(exercise())


def test_correction_chain_uses_nearest_confirmed_ancestor_without_copying_confirmation_rows(
    reuse_database: str,
) -> None:
    _migrate(reuse_database, "head")

    async def exercise() -> None:
        async with _client(reuse_database) as (client, database):
            trade_id, first = await _buy(client)
            middle = await _correct(client, trade_id, first["id"], "BUY", 100, "2.50", "2026-08-05")
            current = await _correct(
                client, trade_id, middle["id"], "BUY", 100, "3.00", "2026-08-05"
            )
            expected = _resolution(
                "EUR", "REPLACED_EXECUTION", [first["id"]], [first["currency_confirmation"]["id"]]
            )
            assert middle["currency_resolution"] == current["currency_resolution"] == expected
            assert middle["currency_confirmation"] is current["currency_confirmation"] is None
            sale = await _book(client, trade_id, "sales", _payload(40, "4.00", "2026-09-02"))
            assert sale["currency_confirmation"] is None
            assert sale["currency_resolution"]["confirmation_ids"] == expected["confirmation_ids"]
            assert set(sale["currency_resolution"]["source_execution_ids"]) == {
                current["id"],
                first["id"],
            }
            assert (await _report(client))["summary"]["total_display"] == "40.00"
            # A declaration on the nearer historical ancestor wins over the older one.
            declared = await _post(
                client,
                f"{BASE}/trades/{trade_id}/executions/{middle['id']}/currency-confirmations",
                DECLARATION | {"currency_code": "USD", "request_id": str(uuid4())},
            )
            expected = _resolution("USD", "REPLACED_EXECUTION", [middle["id"]], [declared["id"]])
            before = await _state(database.engine)
            assert len(before["execution_currency_confirmations"]) == 2
            history = await client.get(
                f"{BASE}/trades/{trade_id}/executions/{current['id']}/currency-confirmations"
            )
            assert history.status_code == 200 and history.json() == {
                "current": None,
                "history": [],
                "currency_resolution": expected,
            }
            timeline = await _timeline(client, trade_id)
            assert timeline[current["id"]]["currency_resolution"] == expected
            assert timeline[first["id"]]["currency_confirmation"]["currency_code"] == "EUR"
            assert timeline[middle["id"]]["currency_confirmation"]["currency_code"] == "USD"
            assert timeline[sale["id"]]["currency_resolution"]["confirmation_ids"] == [
                declared["id"]
            ]
            eur = await _report(client)
            assert eur["summary"]["status"] == "EMPTY" and eur["summary"]["total_display"] == "0.00"
            usd = await _report(client, QUERY | {"report_currency": "USD"})
            assert usd["summary"]["status"] == "COMPLETE"
            assert usd["summary"]["total_display"] == "40.00"
            sources = {row["execution_id"]: row for row in usd["sources"]}
            assert sources[current["id"]]["currency_resolution"] == expected
            assert sources[current["id"]]["supersedes_execution_id"] == middle["id"]
            assert sources[middle["id"]]["supersedes_execution_id"] == first["id"]
            assert sources[first["id"]]["is_effective"] is False
            assert sources[middle["id"]]["is_effective"] is False
            assert sources[current["id"]]["is_effective"] is True
            assert await _state(database.engine) == before

    asyncio.run(exercise())


def test_repeatable_read_keeps_all_inherited_currencies_on_one_committed_basis(
    reuse_database: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    _migrate(reuse_database, "head")

    async def exercise() -> None:
        async with _client(reuse_database) as (client, database):
            _, trade_id, ids = await _capture_reference(client, initial_currency_only=True)
            before = await _report(client)
            old = before["sources"][0]["currency_confirmation"]
            entered, resume = asyncio.Event(), asyncio.Event()
            original = RealizedGrossSnapshotReader._read_executions
            pause_once = True

            async def paused(
                reader: RealizedGrossSnapshotReader,
                session: AsyncSession,
                workspace_id: UUID,
            ) -> tuple[ExecutionFact, ...]:
                nonlocal pause_once
                if pause_once:
                    pause_once = False
                    assert (
                        await session.execute(text("SHOW transaction_isolation"))
                    ).scalar_one() == "repeatable read"
                    assert (
                        await session.execute(text("SHOW transaction_read_only"))
                    ).scalar_one() == "on"
                    entered.set()
                    await asyncio.wait_for(resume.wait(), timeout=15)
                return await original(reader, session, workspace_id)

            monkeypatch.setattr(RealizedGrossSnapshotReader, "_read_executions", paused)
            pending = asyncio.create_task(_report(client))
            await asyncio.wait_for(entered.wait(), timeout=10)
            try:
                changed = await asyncio.wait_for(
                    _post(
                        client,
                        f"{BASE}/trades/{trade_id}/executions/{ids[0]}/currency-confirmations",
                        DECLARATION
                        | {
                            "currency_code": "USD",
                            "request_id": str(uuid4()),
                            "supersedes_confirmation_id": old["id"],
                        },
                    ),
                    timeout=5,
                )
                assert not pending.done()  # Independent writer commits while reader is open.
            finally:
                resume.set()
            old_response = await asyncio.wait_for(pending, timeout=10)
            assert old_response["basis"]["id"] == before["basis"]["id"]
            for field in ("summary", "counts", "items", "sources", "excluded_trades", "currency"):
                assert old_response[field] == before[field]
            assert old_response["summary"]["total_display"] == "10.00"

            committed = await _state(database.engine)
            assert len(committed["execution_currency_confirmations"]) == 2
            current = await _report(client)
            assert current["basis"]["id"] != before["basis"]["id"]
            assert current["summary"]["status"] == "EMPTY"
            assert current["summary"]["total_display"] == "0.00"
            assert current["counts"]["excluded"] == 4 and current["counts"]["unresolved"] == 0
            assert all(
                source["currency_resolution"]["currency_code"] == "USD"
                and source["currency_resolution"]["confirmation_ids"] == [changed["id"]]
                for source in current["sources"]
            )
            assert current["sources"][0]["currency_confirmation"]["id"] == changed["id"]
            assert [item["id"] for item in current["sources"][0]["currency_history"]] == [
                old["id"],
                changed["id"],
            ]
            assert all(source["currency_confirmation"] is None for source in current["sources"][1:])
            usd = await _report(client, QUERY | {"report_currency": "USD"})
            assert usd["summary"]["status"] == "COMPLETE"
            assert usd["summary"]["total_display"] == "10.00"
            assert usd["counts"]["usable"] == 2
            assert (await _report(client))["basis"]["id"] == current["basis"]["id"]
            assert await _state(database.engine) == committed

    asyncio.run(exercise())
