"""Real append-only/CAS guards in separately created synthetic PostgreSQL databases."""

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from tests.integration.backend.learning.test_journal_write_postgres import (
    journal_database as guarded_database,
)
from tests.integration.backend.test_realized_gross_report_postgres import (
    _client as snapshot_client,
)
from tests.integration.backend.test_realized_gross_report_postgres import (
    _state as database_state,
)
from tests.integration.backend.test_trade_capture_safety import (
    ACTOR,
    BASE,
    WORKSPACE,
    product,
    purchase,
    sql,
)
from tests.integration.backend.test_usd_chf_currency_references import _client, _migrate

from app.features.trade_position.domain.hebeltrader_evidence import (
    EntryOrderEvidence,
    HebeltraderEvidenceDeclaration,
    HebeltraderEvidenceRevision,
    UnderlyingTradeEvidence,
    Z1SaleEvidence,
)
from app.features.trade_position.domain.price_binding import PriceBasis, PriceBinding
from app.features.trade_position.persistence.hebeltrader_evidence import (
    DECLARATION,
    HebeltraderEvidenceModel,
    SqlAlchemyHebeltraderEvidenceRepository,
)


@pytest.fixture
def baseline_database():
    # Asserts exact disposable parent name, then creates a unique synthetic DB.
    yield from guarded_database.__wrapped__()


@pytest.fixture(autouse=True)
def forbid_external_http(monkeypatch):
    asynchronous = AsyncMock(side_effect=AssertionError("External HTTP forbidden"))
    synchronous = Mock(side_effect=AssertionError("External HTTP forbidden"))
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", asynchronous)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", synchronous)
    yield
    asynchronous.assert_not_awaited()
    synchronous.assert_not_called()


async def seed(client):
    pid = await product(client)
    bought = await client.post(BASE + "/purchases/external", json=purchase(pid))
    assert bought.status_code == 201, bought.text
    data = bought.json()
    details = (await client.get(f"/api/v1/warrants/{pid}")).json()
    return data, UUID(details["underlying_id"])


def revision(data, underlying_id):
    buy = UUID(data["execution"]["id"])
    return HebeltraderEvidenceRevision(
        id=uuid4(),
        workspace_id=UUID(WORKSPACE),
        trade_id=UUID(data["trade"]["id"]),
        position_id=UUID(data["position"]["id"]),
        product_id=UUID(data["trade"]["product_id"]),
        underlying_id=underlying_id,
        declaration=HebeltraderEvidenceDeclaration(
            entry_order=EntryOrderEvidence("Synthetic original order receipt", (buy,), True),
            underlying_trades=(
                UnderlyingTradeEvidence(
                    execution_id=buy,
                    source_reference="Synthetic original market trade archive",
                    price=Decimal("100.1234567890"),
                    binding=PriceBinding(PriceBasis.UNDERLYING, underlying_id, "EUR"),
                    scale_reference="Synthetic unchanged archive units",
                    last_trade_verified=True,
                    observed_at=datetime(2026, 8, 14, 12, tzinfo=UTC),
                ),
            ),
        ),
        recorded_at=datetime.now(UTC) + timedelta(seconds=1),
        recorded_by=UUID(ACTOR),
        request_id=uuid4(),
        request_fingerprint="a" * 64,
    )


async def append(database, value, *, rollback=False):
    engine = create_async_engine(database, poolclass=NullPool)
    try:
        async with async_sessionmaker(engine)() as session:
            await SqlAlchemyHebeltraderEvidenceRepository(session).add(value)
            if rollback:
                await session.rollback()
            else:
                await session.commit()
    finally:
        await engine.dispose()


async def history(database, value):
    engine = create_async_engine(database, poolclass=NullPool)
    try:
        async with async_sessionmaker(engine)() as session:
            return await SqlAlchemyHebeltraderEvidenceRepository(session).history(
                value.workspace_id, value.trade_id, value.position_id
            )
    finally:
        await engine.dispose()


async def raw_append(database, value, **changes):
    values = {
        name: getattr(value, name) for name in value.__dataclass_fields__ if name != "declaration"
    }
    values.update(
        id=uuid4(),
        request_id=uuid4(),
        source_version_id=value.declaration.source_version_id,
        declaration=DECLARATION.dump_python(value.declaration, mode="json"),
    )
    values.update(changes)
    engine = create_async_engine(database, poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.execute(insert(HebeltraderEvidenceModel).values(**values))
    finally:
        await engine.dispose()


async def business_rows(database):
    return tuple(
        [
            await sql(database, "SELECT * FROM execution_records ORDER BY id"),
            await sql(database, "SELECT * FROM positions ORDER BY id"),
        ]
    )


def test_migration_keeps_existing_economics_empty_evidence_and_refuses_destructive_downgrade(
    baseline_database,
):
    _migrate(baseline_database, "20261109_0049")

    async def prepare():
        async with _client(baseline_database) as client:
            return await seed(client)

    data, underlying = asyncio.run(prepare())
    before = asyncio.run(business_rows(baseline_database))
    _migrate(baseline_database, "head")
    assert asyncio.run(business_rows(baseline_database)) == before
    assert asyncio.run(sql(baseline_database, "SELECT * FROM position_baseline_evidence")) == []
    _migrate(baseline_database, "20261109_0049", action="downgrade")
    _migrate(baseline_database, "head")
    value = revision(data, underlying)
    asyncio.run(append(baseline_database, value))
    with pytest.raises(AssertionError, match="Refusing downgrade: position baseline evidence"):
        _migrate(baseline_database, "20261109_0049", action="downgrade")
    assert asyncio.run(history(baseline_database, value)) == (value,)
    assert asyncio.run(business_rows(baseline_database)) == before


def test_revision_cas_references_and_transaction_rollback_preserve_originals(baseline_database):
    _migrate(baseline_database, "head")

    async def exercise():
        async with _client(baseline_database) as client:
            data, underlying = await seed(client)
            first = revision(data, underlying)
            before = await business_rows(baseline_database)
            await append(baseline_database, first, rollback=True)
            assert await history(baseline_database, first) == ()
            await append(baseline_database, first)
            rows = await sql(baseline_database, "SELECT * FROM position_baseline_execution_refs")
            assert {(r["execution_id"], r["role"]) for r in rows} == {
                (UUID(data["execution"]["id"]), "ENTRY_BUY"),
                (UUID(data["execution"]["id"]), "UNDERLYING_BUY"),
            }
            with pytest.raises(IntegrityError, match="uq_position_baseline_root"):
                await append(baseline_database, replace(first, id=uuid4(), request_id=uuid4()))
            successor = replace(
                first,
                id=uuid4(),
                request_id=uuid4(),
                supersedes_evidence_id=first.id,
                declaration=replace(first.declaration, z1_sales_reviewed=True),
            )
            await append(baseline_database, successor)
            with pytest.raises(IntegrityError, match="uq_position_baseline_successor"):
                await append(baseline_database, replace(successor, id=uuid4(), request_id=uuid4()))
            with pytest.raises(IntegrityError, match="uq_position_baseline_request"):
                await append(
                    baseline_database,
                    replace(successor, id=uuid4(), supersedes_evidence_id=successor.id),
                )
            assert await history(baseline_database, first) == (first, successor)
            for statement in (
                "UPDATE position_baseline_evidence SET request_fingerprint=repeat('b',64)",
                "DELETE FROM position_baseline_evidence",
                "UPDATE position_baseline_execution_refs SET role='Z1_SELL'",
                "DELETE FROM position_baseline_execution_refs",
            ):
                with pytest.raises(IntegrityError, match="immutable"):
                    await sql(baseline_database, statement)
            with pytest.raises(IntegrityError):
                await sql(
                    baseline_database,
                    "DELETE FROM execution_records WHERE id=:id",
                    {"id": data["execution"]["id"]},
                )
            assert await business_rows(baseline_database) == before

    asyncio.run(exercise())


def test_database_rejects_foreign_scope_wrong_side_source_axis_and_chronology(baseline_database):
    _migrate(baseline_database, "head")

    async def exercise():
        async with _client(baseline_database) as client:
            data, underlying = await seed(client)
            original = revision(data, underlying)
            await append(baseline_database, original)
            successor = replace(
                original, id=uuid4(), request_id=uuid4(), supersedes_evidence_id=original.id
            )
            for change, expected in (
                ({"workspace_id": uuid4()}, "trade/workspace/product scope"),
                ({"product_id": uuid4()}, "trade/workspace/product scope"),
                ({"trade_id": uuid4()}, "trade/workspace/product scope"),
                ({"position_id": uuid4()}, "position scope"),
                ({"underlying_id": uuid4()}, "underlying scope"),
                ({"supersedes_evidence_id": uuid4()}, "predecessor scope"),
                ({"recorded_at": original.recorded_at - timedelta(seconds=1)}, "chronology"),
            ):
                with pytest.raises(IntegrityError, match=expected):
                    await append(baseline_database, replace(successor, **change))
            wrong_source = replace(original.declaration, source_version_id=uuid4())
            with pytest.raises(IntegrityError, match="source version scope or confirmation"):
                await append(baseline_database, replace(successor, declaration=wrong_source))
            with pytest.raises(IntegrityError, match="source reference mismatch"):
                await raw_append(baseline_database, successor, source_version_id=uuid4())
            wrong_axis = replace(
                original.declaration,
                underlying_trades=(
                    replace(
                        original.declaration.underlying_trades[0],
                        binding=PriceBinding(PriceBasis.WARRANT, original.product_id, "EUR"),
                    ),
                ),
            )
            with pytest.raises(IntegrityError, match="identity or price axis mismatch"):
                await append(baseline_database, replace(successor, declaration=wrong_axis))
            buy_as_sale = replace(
                original.declaration,
                z1_sales=(Z1SaleEvidence(UUID(data["execution"]["id"]), "Synthetic wrong side"),),
                z1_sales_reviewed=True,
            )
            with pytest.raises(IntegrityError, match="trade/product/side/time scope"):
                await append(baseline_database, replace(successor, declaration=buy_as_sale))
            foreign_execution = replace(
                original.declaration,
                entry_order=EntryOrderEvidence("Synthetic missing execution", (uuid4(),), True),
            )
            with pytest.raises(IntegrityError, match="trade/product/side/time scope"):
                await append(baseline_database, replace(successor, declaration=foreign_execution))
            assert await history(baseline_database, original) == (original,)

    asyncio.run(exercise())


def test_real_api_coverage_commands_and_corrections_keep_economics_and_original_evidence(
    baseline_database,
):
    """Real REST+snapshot path, with outbound transports denied and no lifespan jobs."""
    _migrate(baseline_database, "head")

    async def exercise():
        async with snapshot_client(baseline_database) as (client, database):
            pid = await product(client)
            currency = {
                "currency_code": "EUR",
                "source": "USER_CONFIRMED",
                "note": "Synthetic receipt explicitly confirms EUR execution currency",
            }
            first = await client.post(
                BASE + "/purchases/external",
                json={
                    **purchase(pid, quantity=100),
                    "price_per_unit": "2.00",
                    "currency_confirmation": currency,
                },
            )
            assert first.status_code == 201, first.text
            initial = first.json()
            trade_id = initial["trade"]["id"]
            position_id = initial["position"]["id"]
            trade_url = BASE + f"/trades/{trade_id}"

            async def capture(action, quantity, price, day):
                response = await client.post(
                    trade_url + f"/{action}",
                    json={
                        "quantity": quantity,
                        "price_per_unit": price,
                        "executed_on": day,
                        "execution_timezone": "Europe/Berlin",
                        "request_id": str(uuid4()),
                        "currency_confirmation": currency,
                    },
                )
                assert response.status_code == 201, response.text
                return response.json()

            partial = await capture("purchases", 50, "2.20", "2026-08-17")
            sold = await capture("sales", 40, "3.00", "2026-08-18")
            endpoint = trade_url + "/hebeltrader-evidence"
            query = {"position_id": position_id}
            before_read = await database_state(database.engine)
            assert {
                "execution_records",
                "positions",
                "monitoring_rule_states",
                "position_risk_configurations",
                "position_risk_snapshots",
                "alerts",
                "notifications",
                "notification_delivery_attempts",
            } <= before_read.keys()
            uncovered = await client.get(endpoint, params=query)
            assert uncovered.status_code == 200, uncovered.text
            assert uncovered.json()["coverage_status"] == "INCOMPLETE"
            assert uncovered.json()["valuation_basis"]["position"]["open_quantity"] == 110
            assert uncovered.json()["original_z1_quantity"] is None
            assert uncovered.json()["source"] is None
            assert await database_state(database.engine) == before_read

            original_buy = initial["execution"]["id"]
            body = {
                "position_id": position_id,
                "request_id": str(uuid4()),
                "confirmation": "CONFIRM_HISTORICAL_EVIDENCE",
                "declaration": {
                    "entry_order": {
                        "source_reference": "Synthetic order receipt lists both original fills",
                        "execution_ids": [original_buy, partial["execution"]["id"]],
                        "complete": True,
                    },
                    "z1_sales": [
                        {
                            "execution_id": sold["execution"]["id"],
                            "source_reference": "Synthetic executed sale explicitly assigned to Z1",
                        }
                    ],
                    "z1_sales_reviewed": True,
                },
            }
            saved = await client.post(endpoint, json=body)
            assert saved.status_code == 201, saved.text
            original_revision = saved.json()
            # Explicit evidence commands must not change owner economics or activate rules.
            after_command = await database_state(database.engine)
            for table, rows in before_read.items():
                if table not in {"position_baseline_evidence", "position_baseline_execution_refs"}:
                    assert after_command[table] == rows, table
            replay = await client.post(endpoint, json=body)
            assert replay.status_code == 201 and replay.json() == original_revision, replay.text
            assert await database_state(database.engine) == after_command

            covered = await client.get(endpoint, params=query)
            assert covered.status_code == 200, covered.text
            assert covered.json()["original_z1_quantity"] == 150
            assert covered.json()["assigned_z1_sold_quantity"] == 40
            assert covered.json()["coverage_status"] == "INCOMPLETE"  # Source/trades remain absent.
            assert covered.json()["implementation_status"] == "F207_4_EVIDENCE_ONLY"
            assert covered.json()["operation_status"] == "NOT_ASSESSED"
            assert await database_state(database.engine) == after_command

            rebuy = await capture("purchases", 20, "4.00", "2026-08-19")
            after_rebuy = await database_state(database.engine)
            coverage = await client.get(endpoint, params=query)
            assert coverage.status_code == 200, coverage.text
            result = coverage.json()
            assert result["original_z1_quantity"] == 150
            assert result["assigned_z1_sold_quantity"] == 40
            assert result["valuation_basis"]["position"]["open_quantity"] == 130
            for field in ("cost_basis", "average_entry_price"):
                assert Decimal(result["valuation_basis"]["position"][field]) == Decimal(
                    rebuy["position"][field]
                )
            assert result["valuation_basis"]["currency_status"] == "KNOWN"
            assert result["valuation_basis"]["cost_basis_currency"] == "EUR"
            assert await database_state(database.engine) == after_rebuy

            correction = await client.post(
                trade_url + f"/executions/{original_buy}/corrections",
                json={
                    "side": "BUY",
                    "quantity": 120,
                    "price_per_unit": "2.00",
                    "executed_on": "2026-08-17",
                    "execution_timezone": "Europe/Berlin",
                    "currency_confirmation": currency,
                },
            )
            assert correction.status_code == 201, correction.text
            corrected_id = correction.json()["execution"]["id"]
            after_correction = await database_state(database.engine)
            updated = await client.get(endpoint, params=query)
            assert updated.status_code == 200, updated.text
            result = updated.json()
            assert result["original_z1_quantity"] == 170  # Corrected original fills only.
            assert result["assigned_z1_sold_quantity"] == 40
            assert result["valuation_basis"]["position"]["open_quantity"] == 150
            assert len(result["valuation_basis"]["effective_execution_ids"]) == 4
            entry_link = next(
                item
                for item in result["execution_links"]
                if item["role"] == "ENTRY_ORDER" and item["original_execution_id"] == original_buy
            )
            assert entry_link["effective_execution_id"] == corrected_id
            assert entry_link["correction_chain"] == [original_buy, corrected_id]
            history_response = await client.get(endpoint + "/history", params=query)
            assert history_response.status_code == 200, history_response.text
            history_result = history_response.json()
            assert history_result["current_revision_id"] == original_revision["id"]
            assert history_result["history"] == [original_revision]
            assert await database_state(database.engine) == after_correction
            assert len(after_correction["execution_records"]) == 5
            original_row = next(
                row
                for row in after_correction["execution_records"]
                if str(row["id"]) == original_buy
            )
            assert (
                original_row["quantity"] == 100 and original_row["supersedes_execution_id"] is None
            )
            assert (
                after_correction["position_baseline_evidence"]
                == after_command["position_baseline_evidence"]
            )
            replay_after_correction = await client.post(endpoint, json=body)
            assert replay_after_correction.status_code == 201, replay_after_correction.text
            assert replay_after_correction.json() == original_revision
            assert await database_state(database.engine) == after_correction

    asyncio.run(exercise())
