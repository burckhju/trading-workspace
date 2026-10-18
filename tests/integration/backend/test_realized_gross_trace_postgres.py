"""Real REST captures, PostgreSQL effective-history reads and the owner trace.

EUR is only an external assumption of this synthetic arithmetic example; the
currency-less ExecutionRecord does not establish it. Explicit September fixture
IDs are used as an oracle, not a production period filter. This sequential owner
test is not a financial report, browser flow or report-snapshot qualification.
"""

import asyncio
from collections.abc import Iterator
from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from tests.integration.backend.learning.test_journal_write_postgres import (
    journal_database as guarded_database,
)
from tests.integration.backend.test_trade_capture_safety import BASE, WORKSPACE, product
from tests.integration.backend.test_usd_chf_currency_references import _client, _migrate

from app.features.trade_position.domain.models import ExecutionRecord
from app.features.trade_position.domain.projector import PositionProjectionTrace, PositionProjector
from app.features.trade_position.persistence.repositories import (
    SqlAlchemyExecutionRecordRepository,
    SqlAlchemyPositionRepository,
    SqlAlchemyTradeRepository,
)

BUSINESS_TABLES = (
    "trades",
    "execution_records",
    "positions",
    "trade_management_events",
    "trade_journals",
    "trade_journal_versions",
    "learning_evidence",
    "ft011_evidence",
    "lessons",
    "lesson_versions",
    "exit_reviews",
    "exit_review_versions",
    "post_trade_observations",
    "ft012_idempotency_records",
    "alerts",
    "notifications",
    "monitoring_rule_states",
)


@pytest.fixture
def trace_database() -> Iterator[str]:
    # Existing guard requires the explicit trading_workspace_test base URL.
    # Its delegated fixture creates/drops only its generated disposable database.
    yield from guarded_database.__wrapped__()


async def _business_state(engine: AsyncEngine) -> dict[str, list[dict[str, object]]]:
    result = {}
    async with engine.connect() as connection:
        for table in BUSINESS_TABLES:
            rows = await connection.execute(
                text(
                    f'SELECT * FROM "{table}" AS snapshot_row ORDER BY to_jsonb(snapshot_row)::text'
                )
            )
            result[table] = [dict(row) for row in rows.mappings()]
    return result


async def _read_trace(
    engine: AsyncEngine, trade_id: UUID
) -> tuple[PositionProjectionTrace, tuple[ExecutionRecord, ...]]:
    sessions = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with sessions() as session:
        trade = await SqlAlchemyTradeRepository(session).get(UUID(WORKSPACE), trade_id)
        position = await SqlAlchemyPositionRepository(session).get_for_trade(
            UUID(WORKSPACE), trade_id
        )
        assert trade is not None and position is not None
        repository = SqlAlchemyExecutionRecordRepository(session)
        effective = await repository.list_effective_for_trade(trade_id)
        complete = await repository.list_for_trade(trade_id)
        trace = PositionProjector.project_with_trace(
            id=position.id, trade=trade, executions=effective
        )
        assert trace.position == position
        assert trace.position == PositionProjector.project(
            id=position.id, trade=trade, executions=effective
        )
        return trace, tuple(complete)


def _selected_sum(trace: PositionProjectionTrace, execution_ids: set[UUID]) -> Decimal:
    selected = [
        sale
        for sale in trace.sells
        if trace.ordered_executions[sale.execution_index].id in execution_ids
    ]
    assert len(selected) == len(execution_ids)
    return sum((sale.realized_gross_pnl_delta for sale in selected), Decimal("0"))


def test_actual_captures_effective_correction_and_read_only_trace(
    trace_database: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    _migrate(trace_database, "head")
    external_async = AsyncMock(
        side_effect=AssertionError("External HTTP is forbidden in this test")
    )
    external_sync = Mock(side_effect=AssertionError("External HTTP is forbidden in this test"))
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", external_async)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", external_sync)

    async def exercise() -> None:
        engine = create_async_engine(trace_database, poolclass=NullPool)
        try:
            async with _client(trace_database) as client:
                product_id = await product(client)
                initial = await client.post(
                    BASE + "/purchases/external",
                    json={
                        "product_id": product_id,
                        "quantity": 100,
                        "price_per_unit": "2.00",
                        "executed_on": "2026-08-05",
                        "execution_timezone": "Europe/Berlin",
                        "request_id": str(uuid4()),
                    },
                )
                assert initial.status_code == 201, initial.text
                initial_body = initial.json()
                assert initial_body["trade"]["origin"] == "EXTERNAL"
                trade_id = UUID(initial_body["trade"]["id"])
                position_id = initial_body["position"]["id"]
                trade_url = BASE + f"/trades/{trade_id}"
                execution_ids = [UUID(initial_body["execution"]["id"])]
                # All following rows are actual owner commands, not execution SQL fixtures.
                following = [
                    ("sales", 20, "2.50", "2026-08-12", 80, "160.00", "10.00"),
                    ("sales", 30, "3.00", "2026-09-02", 50, "100.00", "40.00"),
                    ("purchases", 50, "4.00", "2026-09-06", 100, "300.00", "40.00"),
                    ("sales", 40, "2.50", "2026-09-12", 60, "180.00", "20.00"),
                    ("sales", 60, "3.50", "2026-10-03", 0, "0", "50.00"),
                ]
                for action, quantity, price, day, remaining, cost, cumulative in following:
                    response = await client.post(
                        trade_url + f"/{action}",
                        json={
                            "quantity": quantity,
                            "price_per_unit": price,
                            "executed_on": day,
                            "execution_timezone": "Europe/Berlin",
                            "request_id": str(uuid4()),
                        },
                    )
                    assert response.status_code == 201, response.text
                    body = response.json()
                    execution_ids.append(UUID(body["execution"]["id"]))
                    assert body["execution"]["executed_on"] == day
                    assert body["execution"]["execution_timezone"] == "Europe/Berlin"
                    assert body["position"]["id"] == position_id
                    assert body["position"]["open_quantity"] == remaining
                    assert Decimal(body["position"]["cost_basis"]) == Decimal(cost)
                    assert Decimal(body["position"]["realized_gross_pnl"]) == Decimal(cumulative)

                before_reads = await _business_state(engine)
                assert len(before_reads["trades"]) == 1
                assert len(before_reads["execution_records"]) == 6
                assert len(before_reads["positions"]) == 1
                assert all(before_reads[table] == [] for table in BUSINESS_TABLES[3:])

                original, complete = await _read_trace(engine, trade_id)
                assert [execution.id for execution in original.ordered_executions] == execution_ids
                assert complete == original.ordered_executions
                assert [sale.execution_index for sale in original.sells] == [1, 2, 4, 5]
                assert [sale.realized_gross_pnl_delta for sale in original.sells] == [
                    Decimal("10.00"),
                    Decimal("30.00"),
                    Decimal("-20.00"),
                    Decimal("30.00"),
                ]
                assert _selected_sum(original, {execution_ids[2], execution_ids[4]}) == Decimal(
                    "10.00"
                )
                assert original.position.realized_gross_pnl == Decimal("50.00")
                assert [sale.average_cost_per_unit for sale in original.sells] == [
                    Decimal("2.00"),
                    Decimal("2.00"),
                    Decimal("3.00"),
                    Decimal("3.00"),
                ]
                assert [sale.open_quantity_before for sale in original.sells] == [100, 80, 100, 60]
                assert [sale.open_quantity_after for sale in original.sells] == [80, 50, 60, 0]
                assert original.sells[1].cost_basis_after == Decimal("100.00")
                assert original.sells[2].cost_basis_before == Decimal("300.00")
                assert original.sells[2].cost_basis_after == Decimal("180.00")
                assert [
                    execution.id
                    for execution in original.ordered_executions[
                        : original.sells[2].execution_index
                    ]
                ] == execution_ids[:4]
                persisted = await client.get(trade_url + "/position")
                assert persisted.status_code == 200, persisted.text
                assert Decimal(persisted.json()["realized_gross_pnl"]) == Decimal("50.00")
                assert persisted.json()["is_closed"]
                assert await _business_state(engine) == before_reads

                replaced_id = execution_ids[4]
                corrected = await client.post(
                    trade_url + f"/executions/{replaced_id}/corrections",
                    json={
                        "side": "SELL",
                        "quantity": 40,
                        "price_per_unit": "3.00",
                        "executed_on": "2026-09-12",
                        "execution_timezone": "Europe/Berlin",
                    },
                )
                assert corrected.status_code == 201, corrected.text
                replacement_id = UUID(corrected.json()["execution"]["id"])
                assert replacement_id != replaced_id
                assert Decimal(corrected.json()["position"]["realized_gross_pnl"]) == Decimal(
                    "70.00"
                )

                before_corrected_reads = await _business_state(engine)
                assert len(before_corrected_reads["execution_records"]) == 7
                assert all(
                    before_corrected_reads[table] == before_reads[table]
                    for table in BUSINESS_TABLES
                    if table not in {"execution_records", "positions"}
                )
                current, complete = await _read_trace(engine, trade_id)
                expected_effective_ids = [*execution_ids[:4], replacement_id, execution_ids[5]]
                assert [execution.id for execution in current.ordered_executions] == (
                    expected_effective_ids
                )
                assert replaced_id not in {execution.id for execution in current.ordered_executions}
                assert {execution.id for execution in complete} == {*execution_ids, replacement_id}
                retained_original = next(
                    execution for execution in complete if execution.id == replaced_id
                )
                assert retained_original == original.ordered_executions[4]
                replacement = current.ordered_executions[4]
                assert replacement.supersedes_execution_id == replaced_id
                assert replacement.price_per_unit == Decimal("3.00")
                assert replacement.executed_on == retained_original.executed_on
                assert replacement.execution_timezone == retained_original.execution_timezone
                assert replacement.recorded_at >= retained_original.recorded_at
                assert [sale.realized_gross_pnl_delta for sale in current.sells] == [
                    Decimal("10.00"),
                    Decimal("30.00"),
                    Decimal("0.00"),
                    Decimal("30.00"),
                ]
                assert _selected_sum(current, {execution_ids[2], replacement_id}) == Decimal(
                    "30.00"
                )
                assert current.position.realized_gross_pnl == Decimal("70.00")
                assert current.sells[2].open_quantity_before == 100
                assert current.sells[2].cost_basis_before == Decimal("300.00")
                assert current.sells[2].open_quantity_after == 60
                assert current.sells[2].cost_basis_after == Decimal("180.00")
                assert current.ordered_executions[: current.sells[-1].execution_index] == (
                    *original.ordered_executions[:4],
                    replacement,
                )
                assert original.sells[2].realized_gross_pnl_delta == Decimal("-20.00")
                assert original.position.realized_gross_pnl == Decimal("50.00")
                persisted = await client.get(trade_url + "/position")
                assert persisted.status_code == 200, persisted.text
                assert persisted.json()["id"] == position_id
                assert Decimal(persisted.json()["realized_gross_pnl"]) == Decimal("70.00")
                assert await _business_state(engine) == before_corrected_reads
        finally:
            await engine.dispose()

    asyncio.run(exercise())
    external_async.assert_not_awaited()
    external_sync.assert_not_called()
