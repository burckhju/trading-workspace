"""Real owner captures, explicit currency evidence and short PostgreSQL snapshots.

Every test uses a newly generated disposable database with the actual migrations.
ASGI calls use the registered production routes; no scheduler/lifespan runs, all
outbound HTTP transports fail closed. No user database or execution SQL fixture.
"""

import asyncio
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from tests.integration.backend.learning.test_journal_write_postgres import (
    journal_database as guarded_database,
)
from tests.integration.backend.test_trade_capture_safety import BASE, product
from tests.integration.backend.test_usd_chf_currency_references import _migrate

from app.core.config import Environment, Settings
from app.core.config.settings import (
    MarketDataSettings,
    NotificationSettings,
    PositionMonitoringSettings,
)
from app.database import DatabaseManager
from app.features.performance.domain.models import ExecutionFact
from app.features.performance.service.reader import RealizedGrossSnapshotReader
from app.main import create_application

URL = "/api/v1/performance/realized-gross"
QUERY = {
    "from_date": "2026-09-01",
    "to_date": "2026-09-30",
    "report_currency": "EUR",
    "report_timezone": "Europe/Berlin",
}
DECLARATION = {
    "currency_code": "EUR",
    "source": "USER_CONFIRMED",
    "note": "Explicitly confirmed synthetic execution currency",
}


@pytest.fixture
def report_database() -> Iterator[str]:
    # The shared guard requires the designated trading_workspace_test base URL.
    # The delegated fixture creates/drops only its own generated random database.
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


@asynccontextmanager
async def _client(url: str) -> AsyncIterator[tuple[AsyncClient, DatabaseManager]]:
    assert make_url(url).database.startswith("tw_currency_ref_test_")
    settings = Settings(
        _env_file=None,
        environment=Environment.TEST,
        database_url=url,
        documentation_enabled=True,
        log_level="CRITICAL",
        database_pool_size=1,
        database_max_overflow=1,
        market_data=MarketDataSettings(),
        notification=NotificationSettings(),
        position_monitoring=PositionMonitoringSettings(),
    )
    assert not settings.position_monitoring.enabled
    assert not settings.market_data.refresh.enabled
    assert not settings.notification.telegram.enabled
    app = create_application(settings)
    try:
        # No lifespan runs: no scheduler, monitoring pass, delivery or provider call.
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client, app.state.container.database
    finally:
        await app.state.container.close()


async def _state(engine: AsyncEngine) -> dict[str, list[dict[str, object]]]:
    result = {}
    async with engine.connect() as connection:
        tables = (
            (
                await connection.execute(
                    text(
                        "SELECT tablename FROM pg_tables "
                        "WHERE schemaname = 'public' ORDER BY tablename"
                    )
                )
            )
            .scalars()
            .all()
        )
        for table in tables:
            assert table.replace("_", "").isalnum()
            rows = await connection.execute(
                text(f'SELECT * FROM "{table}" AS source_row ORDER BY to_jsonb(source_row)::text')
            )
            result[table] = [dict(row) for row in rows.mappings()]
    return result


async def _capture_reference(
    client: AsyncClient, *, currency: bool = True
) -> tuple[str, str, list[str]]:
    product_id = await product(client)
    body = {
        "product_id": product_id,
        "quantity": 100,
        "price_per_unit": "2.00",
        "executed_on": "2026-08-05",
        "execution_timezone": "Europe/Berlin",
        "request_id": str(uuid4()),
    }
    if currency:
        body["currency_confirmation"] = DECLARATION
    initial = await client.post(BASE + "/purchases/external", json=body)
    assert initial.status_code == 201, initial.text
    trade_id = initial.json()["trade"]["id"]
    execution_ids = [initial.json()["execution"]["id"]]
    for action, quantity, price, day in (
        ("sales", 20, "2.50", "2026-08-12"),
        ("sales", 30, "3.00", "2026-09-02"),
        ("purchases", 50, "4.00", "2026-09-06"),
        ("sales", 40, "2.50", "2026-09-12"),
        ("sales", 60, "3.50", "2026-10-03"),
    ):
        body = {
            "quantity": quantity,
            "price_per_unit": price,
            "executed_on": day,
            "execution_timezone": "Europe/Berlin",
            "request_id": str(uuid4()),
        }
        if currency:
            body["currency_confirmation"] = DECLARATION
        response = await client.post(f"{BASE}/trades/{trade_id}/{action}", json=body)
        assert response.status_code == 201, response.text
        execution_ids.append(response.json()["execution"]["id"])
    return product_id, trade_id, execution_ids


async def _report(client: AsyncClient, query: dict[str, str] | None = None) -> dict:
    response = await client.get(URL, params=query or QUERY)
    assert response.status_code == 200, response.text
    body = response.json()
    counts = body["counts"]
    assert counts["examined"] == len(body["items"])
    assert counts["examined"] == sum(
        counts[key] for key in ("in_period", "outside_period", "period_ambiguous", "period_unknown")
    )
    assert counts["examined"] == counts["candidates"] + counts["excluded"]
    assert counts["candidates"] == counts["usable"] + counts["unresolved"]
    assert len({item["execution_id"] for item in body["items"]}) == len(body["items"])
    assert len({source["execution_id"] for source in body["sources"]}) == len(body["sources"])
    return body


def test_real_captures_qualified_report_complete_sources_and_no_get_side_effects(
    report_database: str,
) -> None:
    _migrate(report_database, "head")

    async def exercise() -> None:
        async with _client(report_database) as (client, database):
            _, trade_id, ids = await _capture_reference(client)
            before = await _state(database.engine)
            assert (
                len(before["execution_records"])
                == len(before["execution_currency_confirmations"])
                == 6
            )
            for table in (
                "trade_journals",
                "trade_journal_versions",
                "learning_evidence",
                "ft011_evidence",
                "lessons",
                "lesson_versions",
                "exit_reviews",
                "post_trade_observations",
                "alerts",
                "notifications",
            ):
                assert before[table] == []
            report = await _report(client)
            assert report["summary"]["status"] == "COMPLETE"
            assert report["summary"]["total"] == "10.0000000000"
            assert report["summary"]["total_display"] == "10.00"
            assert report["counts"]["in_period"] == report["counts"]["usable"] == 2
            assert report["counts"]["outside_period"] == 2
            selected = [item for item in report["items"] if item["status"] == "USABLE"]
            assert [item["execution_id"] for item in selected] == [ids[2], ids[4]]
            assert [item["realized_gross_pnl_delta"] for item in selected] == [
                "30.0000000000",
                "-20.0000000000",
            ]
            assert selected[1]["cost_basis_execution_ids"] == ids[:4]
            assert selected[1]["cost_basis_before"] == "300.0000000000"
            assert selected[1]["cost_basis_after"] == "180.0000000000"
            assert selected[1]["open_quantity_after"] == 60
            assert selected[1]["executed_on"] == "2026-09-12"
            assert selected[1]["executed_at"] is None
            assert all(item["executed_at"] is None for item in report["sources"])
            assert [source["execution_id"] for source in report["sources"]] == ids
            assert all(
                source["currency_confirmation"]["currency_code"] == "EUR"
                for source in report["sources"]
            )
            assert all(
                source["currency_confirmation"]["source"] == "USER_CONFIRMED"
                for source in report["sources"]
            )
            all_months = await _report(
                client, QUERY | {"from_date": "2026-08-01", "to_date": "2026-10-31"}
            )
            position = await client.get(f"{BASE}/trades/{trade_id}/position")
            assert position.status_code == 200
            assert position.json()["is_closed"]
            assert (
                Decimal(all_months["summary"]["total"])
                == Decimal(position.json()["realized_gross_pnl"])
                == Decimal("50")
            )
            repeated = await _report(client)
            assert report["basis"]["id"] == repeated["basis"]["id"]
            assert report["items"] == repeated["items"]
            assert await _state(database.engine) == before
            async with database.engine.connect() as connection:
                assert (
                    await connection.execute(text("SHOW transaction_isolation"))
                ).scalar_one() == "read committed"
                assert (
                    await connection.execute(text("SHOW transaction_read_only"))
                ).scalar_one() == "off"

    asyncio.run(exercise())


@pytest.mark.parametrize("change", ["price", "date", "currency"])
def test_repeatable_read_allows_committed_owner_corrections_without_mixed_response(
    report_database: str,
    monkeypatch: pytest.MonkeyPatch,
    change: str,
) -> None:
    _migrate(report_database, "head")

    async def exercise() -> None:
        async with _client(report_database) as (client, _database):
            _, trade_id, ids = await _capture_reference(client)
            before = await _report(client)
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
                    # Currency and trade reads have already fixed A's source snapshot.
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
                if change == "currency":
                    old = before["sources"][0]["currency_confirmation"]
                    writer = await asyncio.wait_for(
                        client.post(
                            f"{BASE}/trades/{trade_id}/executions/{ids[0]}/currency-confirmations",
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
                    writer = await asyncio.wait_for(
                        client.post(
                            f"{BASE}/trades/{trade_id}/executions/{ids[4]}/corrections",
                            json={
                                "side": "SELL",
                                "quantity": 40,
                                "price_per_unit": "3.00" if change == "price" else "2.50",
                                "executed_on": "2026-10-01" if change == "date" else "2026-09-12",
                                "execution_timezone": "Europe/Berlin",
                                "currency_confirmation": DECLARATION,
                            },
                        ),
                        timeout=5,
                    )
                # The writer response is returned only after its independent command commits.
                # A still holds its read transaction, so a FOR UPDATE reader would deadlock here.
                assert writer.status_code == 201, writer.text
                assert not pending.done()
            finally:
                resume.set()
            old_response = await asyncio.wait_for(pending, timeout=10)
            assert old_response["basis"]["id"] == before["basis"]["id"]
            for field in ("summary", "counts", "items", "sources", "excluded_trades", "currency"):
                assert old_response[field] == before[field]
            assert old_response["summary"]["total_display"] == "10.00"

            current = await _report(client)
            assert current["basis"]["id"] != before["basis"]["id"]
            if change == "currency":
                assert current["summary"]["status"] == "NOT_COMPUTABLE"
                assert current["summary"]["total"] is None
                assert current["summary"]["subtotal"] is None
                assert current["counts"]["usable"] == 0
                assert current["counts"]["unresolved"] == 2
                assert [source["execution_id"] for source in current["sources"]] == ids
                source = current["sources"][0]
                assert source["currency_confirmation"]["currency_code"] == "USD"
                assert [c["currency_code"] for c in source["currency_history"]] == ["EUR", "USD"]
                assert source["currency_confirmation"]["supersedes_confirmation_id"] == old["id"]
                assert all(
                    "CURRENCY_MIXED" in item["reasons"]
                    for item in current["items"]
                    if item["period_status"] == "IN_PERIOD"
                )
            else:
                replacement_id = writer.json()["execution"]["id"]
                assert current["summary"]["status"] == "COMPLETE"
                assert current["summary"]["total_display"] == "30.00"
                assert len(current["sources"]) == 7
                assert current["counts"]["examined"] == 4
                assert ids[4] not in {item["execution_id"] for item in current["items"]}
                old_source = next(
                    source for source in current["sources"] if source["execution_id"] == ids[4]
                )
                assert old_source["is_effective"] is False
                assert old_source["superseded_by_execution_id"] == replacement_id
                changed_item = next(
                    item for item in current["items"] if item["execution_id"] == replacement_id
                )
                if change == "price":
                    assert changed_item["realized_gross_pnl_delta_display"] == "0.00"
                    assert changed_item["status"] == "USABLE"
                    assert current["counts"]["in_period"] == current["counts"]["usable"] == 2
                    whole = await _report(
                        client, QUERY | {"from_date": "2026-08-01", "to_date": "2026-10-31"}
                    )
                    assert whole["summary"]["total_display"] == "70.00"
                else:
                    assert changed_item["executed_on"] == "2026-10-01"
                    assert changed_item["executed_at"] is None
                    assert changed_item["period_status"] == "OUTSIDE_PERIOD"
                    assert changed_item["status"] == "EXCLUDED"
                    assert current["counts"]["in_period"] == current["counts"]["usable"] == 1
                    assert current["counts"]["outside_period"] == 3

    asyncio.run(exercise())


def test_legacy_unknown_listing_changes_explicit_confirmation_and_partial_coverage(
    report_database: str,
) -> None:
    _migrate(report_database, "head")

    async def exercise() -> None:
        async with _client(report_database) as (client, database):
            product_id, trade_id, ids = await _capture_reference(client, currency=False)
            first = await _report(client)
            assert first["summary"]["status"] == "NOT_COMPUTABLE"
            assert first["summary"]["total"] is None
            assert first["counts"]["unresolved"] == 2
            # A today's USD listing is deliberately added to the exact same product.
            venues = await client.get("/api/v1/market-reference-data/trading-venues")
            venue = next(item for item in venues.json()["items"] if item["mic"] == "XETR")
            listed = await client.post(
                f"/api/v1/warrants/{product_id}/listings",
                json={
                    "trading_venue_id": venue["id"],
                    "symbol": "REPORT-USD",
                    "quotation_currency_code": "USD",
                },
            )
            assert listed.status_code == 201, listed.text
            assert (await _report(client))["summary"] == first["summary"]
            before = await _state(database.engine)
            for index in (0, 2):
                confirmation = await client.post(
                    f"{BASE}/trades/{trade_id}/executions/{ids[index]}/currency-confirmations",
                    json=DECLARATION | {"request_id": str(uuid4())},
                )
                assert confirmation.status_code == 201, confirmation.text
            partial = await _report(client)
            assert partial["summary"]["status"] == "PARTIAL"
            assert partial["summary"]["total"] is None
            assert partial["summary"]["subtotal_display"] == "30.00"
            assert partial["counts"]["usable"] == partial["counts"]["unresolved"] == 1
            for index in (3, 4):
                confirmation = await client.post(
                    f"{BASE}/trades/{trade_id}/executions/{ids[index]}/currency-confirmations",
                    json=DECLARATION | {"request_id": str(uuid4())},
                )
                assert confirmation.status_code == 201, confirmation.text
            qualified = await _report(client)
            assert qualified["summary"]["status"] == "COMPLETE"
            assert qualified["summary"]["total_display"] == "10.00"
            assert qualified["counts"]["usable"] == 2
            # Outside SELL revenue currencies are still unknown; earlier sale amounts
            # never establish or obstruct the remaining EUR BUY cost basis.
            assert qualified["sources"][1]["currency_confirmation"] is None
            assert qualified["sources"][5]["currency_confirmation"] is None
            after = await _state(database.engine)
            assert after["execution_records"] == before["execution_records"]
            assert after["positions"] == before["positions"]
            assert len(after["execution_currency_confirmations"]) == 4
            assert (await _report(client))["basis"]["id"] == qualified["basis"]["id"]
            assert await _state(database.engine) == after

    asyncio.run(exercise())


def test_complete_resource_bounds_return_errors_and_never_truncated_summaries(
    report_database: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _migrate(report_database, "head")

    async def exercise() -> None:
        async with _client(report_database) as (client, database):
            await _capture_reference(client)
            before = await _state(database.engine)
            for constant, maximum in (
                ("MAX_TRADES", 0),
                ("MAX_EXECUTIONS", 5),
                ("MAX_CONFIRMATIONS", 5),
            ):
                with monkeypatch.context() as scoped:
                    scoped.setattr(f"app.features.performance.service.reader.{constant}", maximum)
                    response = await client.get(URL, params=QUERY)
                assert response.status_code == 413, response.text
                assert response.json()["code"] == "REPORT_RESOURCE_LIMIT"
                assert "summary" not in response.json()
            response = await client.get(URL, params=QUERY | {"report_currency": "ZZZ"})
            assert response.status_code == 422, response.text
            assert response.json()["code"] == "REPORT_INPUT_INVALID"
            assert (await _report(client))["summary"]["total_display"] == "10.00"
            assert await _state(database.engine) == before

    asyncio.run(exercise())
