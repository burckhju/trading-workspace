"""Approved full-close cohort over real owner commands and fresh PostgreSQL.

The financial oracle is the independently specified T1--T6 example. The report
does not create executions or confirmations, and every read window compares all
persisted public tables. Writer races use a committed independent owner command
while the production bounded reader holds its short read-only snapshot.
"""

import asyncio
from collections.abc import Iterator
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.backend.test_realized_gross_report_postgres import (
    BASE,
    DECLARATION,
    QUERY,
    _capture_reference,
    _client,
    _report,
    _state,
)
from tests.integration.backend.test_realized_gross_report_postgres import (
    forbid_external_calls as guarded_http,
)
from tests.integration.backend.test_realized_gross_report_postgres import (
    report_database as guarded_database,
)
from tests.integration.backend.test_trade_capture_safety import product
from tests.integration.backend.test_usd_chf_currency_references import _migrate

from app.features.performance.domain.models import ExecutionFact
from app.features.performance.service.reader import RealizedGrossSnapshotReader

URL = "/api/v1/performance/closed-trades"
OCTOBER = QUERY | {"from_date": "2026-10-01", "to_date": "2026-10-31"}
GROUPS = (
    "cancelled",
    "history_unresolved",
    "open",
    "outside_period",
    "other_currency",
    "period_unresolved",
    "monetary_unresolved",
    "qualified",
)


@pytest.fixture
def closed_report_database() -> Iterator[str]:
    yield from guarded_database.__wrapped__()


@pytest.fixture(autouse=True)
def forbid_external_calls(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    yield from guarded_http.__wrapped__(monkeypatch)


async def _closed_report(client: AsyncClient, query: dict[str, str] | None = None) -> dict:
    response = await client.get(URL, params=query or OCTOBER)
    assert response.status_code == 200, response.text
    report = response.json()
    assert report["definition_version"] == "closed-trade-gross-v1"
    counts = report["counts"]
    assert counts["examined"] == len(report["items"]) == sum(counts[key] for key in GROUPS)
    assert counts["qualified"] == sum(counts[key] for key in ("positive", "negative", "neutral"))
    assert counts["unresolved"] == sum(
        counts[key] for key in ("history_unresolved", "period_unresolved", "monetary_unresolved")
    )
    assert counts["in_period"] == counts["qualified"] + counts["monetary_unresolved"]
    assert len({item["trade_id"] for item in report["items"]}) == len(report["items"])
    assert len({source["execution_id"] for source in report["sources"]}) == len(report["sources"])
    return report


async def _simple_trade(
    client: AsyncClient,
    product_id: str,
    sale_price: str,
    *,
    currency: str | None = "EUR",
    sale_quantity: int = 10,
    day: str = "2026-10-04",
) -> tuple[str, str, str]:
    body = {
        "product_id": product_id,
        "quantity": 10,
        "price_per_unit": "5.00",
        "executed_on": "2026-06-01",
        "execution_timezone": "Europe/Berlin",
        "request_id": str(uuid4()),
    }
    if currency:
        body["currency_confirmation"] = DECLARATION | {"currency_code": currency}
    bought = await client.post(BASE + "/purchases/external", json=body)
    assert bought.status_code == 201, bought.text
    trade_id = bought.json()["trade"]["id"]
    sold = await client.post(
        f"{BASE}/trades/{trade_id}/sales",
        json={
            "quantity": sale_quantity,
            "price_per_unit": sale_price,
            "executed_on": day,
            "execution_timezone": "Europe/Berlin",
            "request_id": str(uuid4()),
        },
    )
    assert sold.status_code == 201, sold.text
    return trade_id, bought.json()["execution"]["id"], sold.json()["execution"]["id"]


def test_real_t1_to_t6_complete_trade_results_exclusions_and_read_only_sources(
    closed_report_database: str,
) -> None:
    _migrate(closed_report_database, "head")

    async def exercise() -> None:
        async with _client(closed_report_database) as (client, database):
            empty = await _closed_report(client)
            assert empty["summary"]["status"] == "EMPTY"
            assert empty["summary"]["total"] == "0"
            product_id, t1, ids = await _capture_reference(client, initial_currency_only=True)
            original = await _closed_report(client)
            assert original["summary"]["status"] == "COMPLETE"
            assert original["summary"]["total_display"] == "50.00"
            assert original["counts"]["qualified"] == original["counts"]["positive"] == 1
            item = original["items"][0]
            assert item["trade_id"] == t1 and item["origin"] == "EXTERNAL"
            assert item["closing_execution_id"] == ids[-1]
            assert item["closing_time"]["time_precision"] == "DATE_ONLY"
            assert item["closing_time"]["executed_at"] is None
            assert item["closing_time"]["executed_on"] == "2026-10-03"
            assert item["effective_execution_ids"] == ids
            assert [entry["execution_id"] for entry in item["sell_contributions"]] == [
                ids[1],
                ids[2],
                ids[4],
                ids[5],
            ]
            assert [
                entry["realized_gross_pnl_delta_display"] for entry in item["sell_contributions"]
            ] == ["10.00", "30.00", "-20.00", "30.00"]
            assert [entry["period_status"] for entry in item["sell_contributions"]] == [
                "OUTSIDE_PERIOD",
                "OUTSIDE_PERIOD",
                "OUTSIDE_PERIOD",
                "IN_PERIOD",
            ]
            assert [entry["is_closing"] for entry in item["sell_contributions"]] == [
                False,
                False,
                False,
                True,
            ]
            september = await _closed_report(client, QUERY)
            assert september["summary"]["status"] == "EMPTY"
            assert september["counts"]["outside_period"] == 1
            assert (await _report(client))["summary"]["total_display"] == "10.00"
            assert (await _report(client, OCTOBER))["summary"]["total_display"] == "30.00"

            t2, _, _ = await _simple_trade(client, product_id, "4.00")
            t3, _, _ = await _simple_trade(client, product_id, "5.00")
            qualified = await _closed_report(client)
            assert qualified["summary"]["total_display"] == "40.00"
            assert qualified["summary"]["status"] == "COMPLETE"
            assert qualified["counts"]["qualified"] == 3
            assert [qualified["counts"][key] for key in ("positive", "negative", "neutral")] == [
                1,
                1,
                1,
            ]
            assert {entry["trade_id"] for entry in qualified["items"]} == {t1, t2, t3}
            # All three share the exact product, so product identity cannot deduplicate trades.
            assert {entry["product_id"] for entry in qualified["items"]} == {product_id}

            t4, _, _ = await _simple_trade(client, product_id, "6.00", currency=None)
            t5, _, _ = await _simple_trade(client, product_id, "6.00", currency="USD")
            t6, _, _ = await _simple_trade(client, product_id, "7.00", sale_quantity=5)
            partial = await _closed_report(client)
            assert partial["summary"]["status"] == "PARTIAL"
            assert partial["summary"]["total"] is None
            assert partial["summary"]["subtotal_display"] == "40.00"
            assert [partial["counts"][key] for key in GROUPS] == [0, 0, 1, 0, 1, 0, 1, 3]
            by_trade = {entry["trade_id"]: entry for entry in partial["items"]}
            assert by_trade[t4]["group"] == "MONETARY_UNRESOLVED"
            assert by_trade[t4]["realized_gross_pnl"] is None
            assert by_trade[t4]["classification"] is None
            assert by_trade[t5]["group"] == "OTHER_CURRENCY"
            assert by_trade[t6]["group"] == "OPEN"
            before_reads = await _state(database.engine)
            assert len(before_reads["execution_currency_confirmations"]) == 5
            assert len(before_reads["execution_records"]) == 16
            assert (await _closed_report(client))["basis"]["id"] == partial["basis"]["id"]
            await _closed_report(client, QUERY)
            await _report(client)
            assert await _state(database.engine) == before_reads

            correction = await client.post(
                f"{BASE}/trades/{t1}/executions/{ids[4]}/corrections",
                json={
                    "side": "SELL",
                    "quantity": 40,
                    "price_per_unit": "3.00",
                    "executed_on": "2026-09-12",
                    "execution_timezone": "Europe/Berlin",
                },
            )
            assert correction.status_code == 201, correction.text
            replacement_id = correction.json()["execution"]["id"]
            changed = await _closed_report(client)
            assert changed["summary"]["status"] == "PARTIAL"
            assert changed["summary"]["subtotal_display"] == "60.00"
            assert changed["counts"] == partial["counts"]
            assert changed["basis"]["id"] != partial["basis"]["id"]
            corrected_t1 = next(entry for entry in changed["items"] if entry["trade_id"] == t1)
            assert corrected_t1["realized_gross_pnl_display"] == "70.00"
            assert corrected_t1["closing_execution_id"] == ids[-1]
            assert ids[4] not in corrected_t1["effective_execution_ids"]
            assert replacement_id in corrected_t1["effective_execution_ids"]
            retained = next(
                source for source in changed["sources"] if source["execution_id"] == ids[4]
            )
            assert retained["is_effective"] is False
            assert retained["superseded_by_execution_id"] == replacement_id
            assert (await _report(client))["summary"]["total_display"] == "30.00"
            after_correction = await _state(database.engine)
            assert len(after_correction["execution_currency_confirmations"]) == 5
            assert len(after_correction["execution_records"]) == 17
            for table in (
                "trade_journals",
                "learning_evidence",
                "exit_reviews",
                "notifications",
                "alerts",
            ):
                assert after_correction[table] == []
            await _closed_report(client)
            assert await _state(database.engine) == after_correction

            mistaken = await client.post(
                BASE + "/purchases/external",
                json={
                    "product_id": product_id,
                    "quantity": 1,
                    "price_per_unit": "5.00",
                    "executed_on": "2026-10-05",
                    "execution_timezone": "Europe/Berlin",
                    "currency_confirmation": DECLARATION,
                    "request_id": str(uuid4()),
                },
            )
            assert mistaken.status_code == 201, mistaken.text
            cancelled_id = mistaken.json()["trade"]["id"]
            preview = await client.get(f"{BASE}/trades/{cancelled_id}/cancellation")
            assert preview.status_code == 200, preview.text
            cancelled = await client.post(
                f"{BASE}/trades/{cancelled_id}/cancel",
                json={
                    "expected_product_id": product_id,
                    "expected_state_token": preview.json()["state_token"],
                    "reason": "Synthetic mistaken capture, not an economic exit",
                    "confirmed": True,
                },
            )
            assert cancelled.status_code == 200, cancelled.text
            after_cancellation = await _state(database.engine)
            report = await _closed_report(client)
            assert report["counts"]["examined"] == 7
            assert report["counts"]["cancelled"] == 1
            assert report["counts"]["qualified"] == 3
            assert report["summary"]["subtotal_display"] == "60.00"
            cancelled_item = next(
                item for item in report["items"] if item["trade_id"] == cancelled_id
            )
            assert cancelled_item["group"] == "CANCELLED"
            assert cancelled_item["closing_execution_id"] is None
            assert cancelled_item["classification"] is None
            assert await _state(database.engine) == after_cancellation

    asyncio.run(exercise())


@pytest.mark.parametrize("change", ["price", "date", "quantity", "currency"])
def test_full_close_snapshot_does_not_mix_concurrent_committed_owner_correction(
    closed_report_database: str, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    _migrate(closed_report_database, "head")

    async def exercise() -> None:
        async with _client(closed_report_database) as (client, database):
            _, trade_id, ids = await _capture_reference(client)
            before = await _closed_report(client)
            entered, resume = asyncio.Event(), asyncio.Event()
            original = RealizedGrossSnapshotReader._read_executions
            pause_once = True

            async def paused(
                reader: RealizedGrossSnapshotReader, session: AsyncSession, workspace_id: UUID
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
            pending = asyncio.create_task(_closed_report(client))
            await asyncio.wait_for(entered.wait(), timeout=10)
            try:
                if change == "currency":
                    old = next(
                        source for source in before["sources"] if source["execution_id"] == ids[1]
                    )["currency_confirmation"]
                    writer = await asyncio.wait_for(
                        client.post(
                            f"{BASE}/trades/{trade_id}/executions/{ids[1]}/currency-confirmations",
                            json=DECLARATION
                            | {
                                "currency_code": "USD",
                                "request_id": str(uuid4()),
                                "supersedes_confirmation_id": old["id"],
                            },
                        ),
                        timeout=5,
                    )
                else:
                    target = ids[4] if change == "price" else ids[5]
                    writer = await asyncio.wait_for(
                        client.post(
                            f"{BASE}/trades/{trade_id}/executions/{target}/corrections",
                            json={
                                "side": "SELL",
                                "quantity": (
                                    40 if change == "price" else 59 if change == "quantity" else 60
                                ),
                                "price_per_unit": "3.00" if change == "price" else "3.50",
                                "executed_on": (
                                    "2026-09-12"
                                    if change == "price"
                                    else "2026-09-30" if change == "date" else "2026-10-03"
                                ),
                                "execution_timezone": "Europe/Berlin",
                            },
                        ),
                        timeout=5,
                    )
                assert writer.status_code == 201, writer.text
                assert not pending.done()
            finally:
                resume.set()
            old_response = await asyncio.wait_for(pending, timeout=10)
            assert old_response["basis"]["id"] == before["basis"]["id"]
            assert {key: value for key, value in old_response.items() if key != "basis"} == {
                key: value for key, value in before.items() if key != "basis"
            }
            after_writer = await _state(database.engine)
            current = await _closed_report(client)
            assert current["basis"]["id"] != before["basis"]["id"]
            assert current["counts"]["examined"] == 1
            item = current["items"][0]
            if change == "price":
                assert current["summary"]["total_display"] == "70.00"
                assert current["counts"] == before["counts"]
                assert item["closing_execution_id"] == ids[-1]
            elif change == "date":
                assert current["summary"]["status"] == "EMPTY"
                assert current["counts"]["outside_period"] == 1
                assert item["closing_time"]["executed_on"] == "2026-09-30"
                assert item["closing_time"]["executed_at"] is None
                shifted = await _closed_report(client, QUERY)
                assert shifted["summary"]["total_display"] == "50.00"
                assert shifted["counts"]["positive"] == 1
            elif change == "quantity":
                assert current["summary"]["status"] == "EMPTY"
                assert current["counts"]["open"] == 1
                assert item["closing_execution_id"] is None
                assert item["classification"] is None
                assert writer.json()["position"]["open_quantity"] == 1
            else:
                assert current["summary"]["status"] == "NOT_COMPUTABLE"
                assert current["summary"]["total"] is None
                assert current["summary"]["subtotal"] is None
                assert current["counts"]["monetary_unresolved"] == 1
                assert "CURRENCY_MIXED" in item["reasons"]
                assert item["classification"] is None
                previous_sell = next(
                    source for source in current["sources"] if source["execution_id"] == ids[1]
                )
                assert [
                    confirmation["currency_code"]
                    for confirmation in previous_sell["currency_history"]
                ] == ["EUR", "USD"]
                # Later EUR sale remains individually valid; the complete trade does not.
                existing = await _report(client, OCTOBER)
                assert existing["summary"]["total_display"] == "30.00"
            if change != "currency":
                retained = next(
                    source for source in current["sources"] if source["execution_id"] == target
                )
                assert retained["is_effective"] is False
                assert retained["superseded_by_execution_id"] == writer.json()["execution"]["id"]
            await _closed_report(client)
            assert await _state(database.engine) == after_writer
            async with database.engine.connect() as connection:
                assert (
                    await connection.execute(text("SHOW transaction_isolation"))
                ).scalar_one() == "read committed"
                assert (
                    await connection.execute(text("SHOW transaction_read_only"))
                ).scalar_one() == "off"

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "currency,price,status", [(None, "6.00", "NOT_COMPUTABLE"), ("EUR", "5.00", "COMPLETE")]
)
def test_only_unknown_is_not_zero_and_qualified_exact_zero_is_neutral(
    closed_report_database: str, currency: str | None, price: str, status: str
) -> None:
    _migrate(closed_report_database, "head")

    async def exercise() -> None:
        async with _client(closed_report_database) as (client, database):
            pid = await product(client)
            await _simple_trade(client, pid, price, currency=currency)
            before = await _state(database.engine)
            report = await _closed_report(client)
            assert report["summary"]["status"] == status
            assert report["summary"]["subtotal"] is None
            if currency:
                assert report["summary"]["total_display"] == "0.00"
                assert report["counts"]["neutral"] == report["counts"]["qualified"] == 1
            else:
                assert report["summary"]["total"] is None
                assert report["counts"]["monetary_unresolved"] == 1
                assert report["counts"]["qualified"] == 0
            outside = await _closed_report(client, QUERY)
            assert outside["summary"]["status"] == "EMPTY"
            assert outside["summary"]["total"] == "0"
            assert outside["counts"]["outside_period"] == 1
            assert await _state(database.engine) == before

    asyncio.run(exercise())
