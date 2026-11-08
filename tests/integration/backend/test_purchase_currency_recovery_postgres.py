"""Atomic purchase-currency recovery through real owners and native PostgreSQL.

Only synthetic captures enter a newly generated, guarded disposable database.
No user inventory, money, database or credentials are fixtures. The existing
confirmation owner commits savepoints; these tests observe the outer transaction
from independent connections, including rollback, replay and concurrent writers.
"""

import asyncio
import hashlib
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from tests.integration.backend.learning.test_journal_write_postgres import (
    journal_database as guarded_database,
)
from tests.integration.backend.test_currency_source_evidence_postgres import (
    evidence_url,
    historical,
    venue,
)
from tests.integration.backend.test_execution_currency_confirmations_postgres import (
    confirmation_url,
)
from tests.integration.backend.test_execution_currency_reuse_postgres import _correct, _payload
from tests.integration.backend.test_realized_gross_report_postgres import (
    DECLARATION,
    QUERY,
    _capture_reference,
    _client,
    _report,
    _state,
)
from tests.integration.backend.test_trade_capture_safety import ACTOR, BASE, WORKSPACE
from tests.integration.backend.test_usd_chf_currency_references import _migrate

from app.features.trade_position.persistence.currency_repository import (
    SqlAlchemyExecutionCurrencyConfirmationRepository,
)
from app.features.trade_position.service.currency_confirmations import (
    ExecutionCurrencyConfirmationService,
)
from app.tools import recover_purchase_currency as recovery


@pytest.fixture
def recovery_database() -> Iterator[str]:
    # Requires the designated trading_workspace_test base URL; the delegated
    # fixture creates/drops only its own randomly named tw_currency_ref_test_ DB.
    yield from guarded_database.__wrapped__()


@pytest.fixture(autouse=True)
def forbid_external_http(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    external_async = AsyncMock(side_effect=AssertionError("External HTTP forbidden"))
    external_sync = Mock(side_effect=AssertionError("External HTTP forbidden"))
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", external_async)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", external_sync)
    yield
    external_async.assert_not_awaited()
    external_sync.assert_not_called()


@dataclass(frozen=True)
class SyntheticInventory:
    product_id: str
    trade_id: str
    execution_ids: tuple[str, ...]
    buy_ids: tuple[str, ...]
    superseded_buy_id: str | None = None
    cancelled_buy_id: str | None = None
    cancelled_trade_id: str | None = None


async def _cancel(client: AsyncClient, product_id: str, trade_id: str) -> None:
    endpoint = f"{BASE}/trades/{trade_id}"
    preview = await client.get(endpoint + "/cancellation")
    assert preview.status_code == 200, preview.text
    response = await client.post(
        endpoint + "/cancel",
        json={
            "expected_product_id": product_id,
            "expected_state_token": preview.json()["state_token"],
            "reason": "Synthetic cancellation outside the recovery scope",
            "confirmed": True,
        },
    )
    assert response.status_code == 200, response.text


async def _seed(client: AsyncClient, *, exclusions: bool = False) -> SyntheticInventory:
    product_id, trade_id, ids = await _capture_reference(client, currency=False)
    buy_ids = [ids[0], ids[3]]
    superseded = cancelled = cancelled_trade = None
    if exclusions:
        replacement = await _correct(client, trade_id, ids[0], "BUY", 100, "2.10", "2026-08-05")
        superseded = ids[0]
        buy_ids[0] = replacement["id"]
        response = await client.post(
            BASE + "/purchases/external",
            json={"product_id": product_id} | _payload(10, "1.00", "2026-10-05"),
        )
        assert response.status_code == 201, response.text
        cancelled = response.json()["execution"]["id"]
        cancelled_trade = response.json()["trade"]["id"]
        await _cancel(client, product_id, cancelled_trade)
    return SyntheticInventory(
        product_id, trade_id, tuple(ids), tuple(buy_ids), superseded, cancelled, cancelled_trade
    )


async def _plan(
    client: AsyncClient, inventory: SyntheticInventory
) -> recovery.PurchaseCurrencyRecoveryPlan:
    report = await _report(client)
    assert report["summary"]["status"] == "NOT_COMPUTABLE"
    assert report["counts"]["usable"] == 0 and report["counts"]["unresolved"] == 2
    sources = {source["execution_id"]: source for source in report["sources"]}
    assert all(
        sources[item]["currency_resolution"]["source"] == "UNKNOWN" for item in inventory.buy_ids
    )
    # The manifest pins the original report basis and the expected qualified
    # post-state. This two-BUY trade catches an implementation that accidentally
    # stops after the first declaration makes the second BUY derivable.
    counts = report["counts"] | {"usable": 2, "unresolved": 0}
    plan = recovery.PurchaseCurrencyRecoveryPlan(
        schema_version="purchase-currency-recovery-v1",
        workspace_id=UUID(WORKSPACE),
        actor_id=UUID(ACTOR),
        currency="EUR",
        expected_basis=report["basis"]["id"],
        filters=recovery.RecoveryFilters(
            from_date=date.fromisoformat(QUERY["from_date"]),
            to_date=date.fromisoformat(QUERY["to_date"]),
            report_currency=QUERY["report_currency"],
            report_timezone=QUERY["report_timezone"],
        ),
        inventory_sha256=hashlib.sha256(b"synthetic native PostgreSQL inventory").hexdigest(),
        note="Synthetic existing EUR purchase declaration recovered for this exact inventory",
        targets=tuple(
            recovery.RecoveryTarget(
                execution_id=UUID(execution_id),
                trade_id=UUID(inventory.trade_id),
                product_id=UUID(inventory.product_id),
            )
            for execution_id in sorted(inventory.buy_ids)
        ),
        expected_counts=recovery.RecoveryCounts(**counts),
        expected_summary_status="COMPLETE",
    )
    return recovery.PurchaseCurrencyRecoveryPlan.model_validate_json(plan.model_dump_json())


async def _apply(engine: AsyncEngine, plan: recovery.PurchaseCurrencyRecoveryPlan) -> dict:
    # Production uses the same outer transaction. In particular, no fixture
    # transaction can hide a partial owner commit or an accidental early commit.
    async with engine.begin() as connection:
        return await recovery.apply_plan(connection, plan)


async def _inspect(engine: AsyncEngine, plan: recovery.PurchaseCurrencyRecoveryPlan) -> dict:
    async with engine.connect() as connection, connection.begin():
        await connection.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
        async with AsyncSession(
            bind=connection,
            expire_on_commit=False,
            autoflush=False,
            join_transaction_mode="create_savepoint",
        ) as session:
            return await recovery.inspect_plan(session, plan)


async def _confirm(
    client: AsyncClient,
    inventory: SyntheticInventory,
    *,
    currency: str = "EUR",
    supersedes: str | None = None,
) -> httpx.Response:
    return await client.post(
        confirmation_url(inventory.trade_id, inventory.buy_ids[0]),
        json=DECLARATION
        | {
            "currency_code": currency,
            "request_id": str(uuid4()),
            "supersedes_confirmation_id": supersedes,
        },
    )


async def _evidence(client: AsyncClient, inventory: SyntheticInventory) -> httpx.Response:
    return await client.post(
        evidence_url(inventory.product_id),
        json={
            "kind": "EXECUTION_DOCUMENT",
            "source_reference": "Synthetic independently reviewed purchase receipt",
            "request_id": str(uuid4()),
            "confirmation": "CONFIRM_SOURCE_REVIEW",
            "trade_id": inventory.trade_id,
            "execution_id": inventory.buy_ids[0],
            "currency_code": "EUR",
        },
    )


async def _assert_waiting_for_lock(engine: AsyncEngine, task: asyncio.Task) -> None:
    """Observe a real PostgreSQL lock wait instead of assuming timing proves it."""
    async with engine.connect() as connection:
        async with asyncio.timeout(10):
            while True:
                assert not task.done(), "Concurrent writer bypassed the recovery lock"
                count = await connection.scalar(
                    text(
                        "SELECT count(*) FROM pg_stat_activity "
                        "WHERE datname=current_database() AND pid<>pg_backend_pid() "
                        "AND wait_event_type='Lock' AND state='active'"
                    )
                )
                if count:
                    return
                await asyncio.sleep(0.01)


def test_bulk_recovery_preserves_all_business_rows_and_only_confirms_effective_buys(
    recovery_database: str,
) -> None:
    _migrate(recovery_database, "head")

    async def exercise() -> None:
        async with _client(recovery_database) as (client, database):
            inventory = await _seed(client, exclusions=True)
            plan = await _plan(client, inventory)
            before = await _state(database.engine)
            assert before["execution_currency_confirmations"] == []
            assert (await _inspect(database.engine, plan))["status"] == "READY"
            assert await _state(database.engine) == before

            result = await _apply(database.engine, plan)
            assert result["status"] == "APPLIED"
            after = await _state(database.engine)
            confirmations = after.pop("execution_currency_confirmations")
            assert len(confirmations) == len(result["confirmations"]) == 2
            assert after == {
                key: value
                for key, value in before.items()
                if key != "execution_currency_confirmations"
            }
            assert {str(row["execution_id"]) for row in confirmations} == set(inventory.buy_ids)
            assert all(
                row["currency_code"] == "EUR"
                and row["source"] == "USER_CONFIRMED"
                and str(row["confirmed_by"]) == ACTOR
                and row["note"] == plan.note
                and row["supersedes_confirmation_id"] is None
                for row in confirmations
            )
            requests = {
                target.execution_id: recovery.recovery_request_id(plan, target)
                for target in plan.targets
            }
            assert all(row["request_id"] == requests[row["execution_id"]] for row in confirmations)
            assert inventory.superseded_buy_id not in {
                str(row["execution_id"]) for row in confirmations
            }
            assert inventory.cancelled_buy_id not in {
                str(row["execution_id"]) for row in confirmations
            }
            report = await _report(client)
            assert report["summary"]["status"] == "COMPLETE"
            assert report["counts"] == plan.expected_counts.model_dump()
            assert report["basis"]["id"] != plan.expected_basis
            sales = [source for source in report["sources"] if source["side"] == "SELL"]
            assert len(sales) == 4
            assert all(source["currency_confirmation"] is None for source in sales)
            assert all(source["currency_resolution"]["source"] == "PRIOR_BUYS" for source in sales)

    asyncio.run(exercise())


def test_failure_after_first_owner_commit_rolls_back_every_confirmation(
    recovery_database: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    _migrate(recovery_database, "head")

    async def exercise() -> None:
        async with _client(recovery_database) as (client, database):
            inventory = await _seed(client)
            plan = await _plan(client, inventory)
            before = await _state(database.engine)
            original = ExecutionCurrencyConfirmationService.confirm
            committed = 0

            async def fail_after_one(self, **kwargs):
                nonlocal committed
                if committed == 1:
                    raise RuntimeError("Synthetic second owner write failure")
                result = await original(self, **kwargs)
                committed += 1
                return result

            monkeypatch.setattr(ExecutionCurrencyConfirmationService, "confirm", fail_after_one)
            with pytest.raises(RuntimeError, match="second owner write failure"):
                await _apply(database.engine, plan)
            assert committed == 1
            assert await _state(database.engine) == before
            assert (await _inspect(database.engine, plan))["status"] == "READY"

    asyncio.run(exercise())


def test_wrong_postcondition_rolls_back_the_successful_owner_writes(
    recovery_database: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    _migrate(recovery_database, "head")

    async def exercise() -> None:
        async with _client(recovery_database) as (client, database):
            inventory = await _seed(client)
            plan = await _plan(client, inventory)
            wrong = plan.model_copy(
                update={"expected_counts": plan.expected_counts.model_copy(update={"cancelled": 1})}
            )
            before = await _state(database.engine)
            original = ExecutionCurrencyConfirmationService.confirm
            committed = 0

            async def counted(self, **kwargs):
                nonlocal committed
                result = await original(self, **kwargs)
                committed += 1
                return result

            monkeypatch.setattr(ExecutionCurrencyConfirmationService, "confirm", counted)
            with pytest.raises(recovery.RecoveryError) as rejected:
                await _apply(database.engine, wrong)
            assert rejected.value.code == "POSTCONDITION_FAILED"
            assert committed == 2
            assert await _state(database.engine) == before

    asyncio.run(exercise())


def test_committed_batch_can_be_replayed_after_a_lost_response_without_duplicate_facts(
    recovery_database: str,
) -> None:
    _migrate(recovery_database, "head")

    async def exercise() -> None:
        async with _client(recovery_database) as (client, database):
            inventory = await _seed(client)
            plan = await _plan(client, inventory)
            await _apply(database.engine, plan)  # The caller lost this committed response.
            after = await _state(database.engine)
            assert len(after["execution_currency_confirmations"]) == 2
            assert (await _inspect(database.engine, plan))["status"] == "ALREADY_APPLIED"
            replay = await _apply(database.engine, plan)
            assert replay["status"] == "ALREADY_APPLIED"
            assert await _state(database.engine) == after

    asyncio.run(exercise())


def test_partial_deterministic_replay_is_rejected_without_completing_the_batch(
    recovery_database: str,
) -> None:
    _migrate(recovery_database, "head")

    async def exercise() -> None:
        async with _client(recovery_database) as (client, database):
            inventory = await _seed(client)
            plan = await _plan(client, inventory)
            target = plan.targets[0]
            response = await client.post(
                confirmation_url(target.trade_id, target.execution_id),
                json={
                    "currency_code": plan.currency,
                    "source": "USER_CONFIRMED",
                    "note": plan.note,
                    "request_id": str(recovery.recovery_request_id(plan, target)),
                    "supersedes_confirmation_id": None,
                },
            )
            assert response.status_code == 201, response.text
            before = await _state(database.engine)
            with pytest.raises(recovery.RecoveryError) as rejected:
                await _apply(database.engine, plan)
            assert rejected.value.code == "PARTIAL_REPLAY"
            assert await _state(database.engine) == before
            assert len(before["execution_currency_confirmations"]) == 1

    asyncio.run(exercise())


@pytest.mark.parametrize("currency", ["EUR", "USD"])
def test_foreign_confirmation_even_in_same_currency_aborts_whole_batch(
    recovery_database: str, currency: str
) -> None:
    _migrate(recovery_database, "head")

    async def exercise() -> None:
        async with _client(recovery_database) as (client, database):
            inventory = await _seed(client)
            plan = await _plan(client, inventory)
            response = await _confirm(client, inventory, currency=currency)
            assert response.status_code == 201, response.text
            before = await _state(database.engine)
            with pytest.raises(recovery.RecoveryError):
                await _apply(database.engine, plan)
            assert await _state(database.engine) == before
            assert len(before["execution_currency_confirmations"]) == 1

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "change", ["source", "new_execution", "correction", "cancellation", "basis"]
)
def test_changed_inventory_aborts_before_writing(recovery_database: str, change: str) -> None:
    _migrate(recovery_database, "head")

    async def exercise() -> None:
        async with _client(recovery_database) as (client, database):
            inventory = await _seed(client)
            plan = await _plan(client, inventory)
            if change == "source":
                response = await client.post(
                    evidence_url(inventory.product_id), json=historical(await venue(client))
                )
                assert response.status_code == 201, response.text
            elif change == "new_execution":
                response = await client.post(
                    BASE + "/purchases/external",
                    json={"product_id": inventory.product_id} | _payload(10, "1.00", "2026-10-05"),
                )
                assert response.status_code == 201, response.text
            elif change == "correction":
                await _correct(
                    client,
                    inventory.trade_id,
                    inventory.buy_ids[0],
                    "BUY",
                    100,
                    "2.10",
                    "2026-08-05",
                )
            elif change == "cancellation":
                await _cancel(client, inventory.product_id, inventory.trade_id)
            else:
                plan = plan.model_copy(update={"expected_basis": "0" * 64})
            before = await _state(database.engine)
            with pytest.raises(recovery.RecoveryError):
                await _apply(database.engine, plan)
            assert await _state(database.engine) == before
            assert before["execution_currency_confirmations"] == []

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "target",
    [
        "sell",
        "superseded",
        "cancelled",
        "wrong_trade",
        "wrong_product",
        "missing_buy",
        "wrong_workspace",
    ],
)
def test_invalid_scope_never_confirms_any_execution(recovery_database: str, target: str) -> None:
    _migrate(recovery_database, "head")

    async def exercise() -> None:
        async with _client(recovery_database) as (client, database):
            inventory = await _seed(client, exclusions=True)
            plan = await _plan(client, inventory)
            first, second = plan.targets
            if target == "wrong_workspace":
                plan = plan.model_copy(update={"workspace_id": uuid4()})
            elif target == "missing_buy":
                plan = plan.model_copy(update={"targets": (first,)})
            else:
                changes = {
                    "sell": {"execution_id": UUID(inventory.execution_ids[2])},
                    "superseded": {"execution_id": UUID(inventory.superseded_buy_id)},
                    "cancelled": {
                        "execution_id": UUID(inventory.cancelled_buy_id),
                        "trade_id": UUID(inventory.cancelled_trade_id),
                    },
                    "wrong_trade": {"trade_id": uuid4()},
                    "wrong_product": {"product_id": uuid4()},
                }
                plan = plan.model_copy(
                    update={"targets": (first.model_copy(update=changes[target]), second)}
                )
            before = await _state(database.engine)
            with pytest.raises(recovery.RecoveryError):
                await _apply(database.engine, plan)
            assert await _state(database.engine) == before

    asyncio.run(exercise())


@pytest.mark.parametrize("currency", ["EUR", "USD"])
def test_replay_never_overwrites_a_later_replacement_even_in_the_same_currency(
    recovery_database: str, currency: str
) -> None:
    _migrate(recovery_database, "head")

    async def exercise() -> None:
        async with _client(recovery_database) as (client, database):
            inventory = await _seed(client)
            plan = await _plan(client, inventory)
            await _apply(database.engine, plan)
            endpoint = confirmation_url(inventory.trade_id, inventory.buy_ids[0])
            history = (await client.get(endpoint)).json()
            response = await _confirm(
                client, inventory, currency=currency, supersedes=history["current"]["id"]
            )
            assert response.status_code == 201, response.text
            before = await _state(database.engine)
            with pytest.raises(recovery.RecoveryError) as rejected:
                await _apply(database.engine, plan)
            assert rejected.value.code == "REPLAY_CONFLICT"
            assert await _state(database.engine) == before
            assert (await client.get(endpoint)).json()["current"] == response.json()

    asyncio.run(exercise())


@pytest.mark.parametrize("writer", ["confirmation", "evidence", "correction"])
def test_concurrent_owner_writes_wait_until_the_whole_recovery_transaction_commits(
    recovery_database: str, monkeypatch: pytest.MonkeyPatch, writer: str
) -> None:
    _migrate(recovery_database, "head")

    async def exercise() -> None:
        observer = create_async_engine(
            recovery_database, poolclass=NullPool, isolation_level="AUTOCOMMIT"
        )
        try:
            async with _client(recovery_database) as (client, database):
                inventory = await _seed(client)
                plan = await _plan(client, inventory)
                entered, resume = asyncio.Event(), asyncio.Event()
                original = recovery.inspect_plan
                pause_once = True

                async def held(session, candidate):
                    nonlocal pause_once
                    result = await original(session, candidate)
                    if pause_once:
                        pause_once = False
                        entered.set()
                        await resume.wait()
                    return result

                monkeypatch.setattr(recovery, "inspect_plan", held)
                batch = asyncio.create_task(_apply(database.engine, plan))
                contender = None
                try:
                    await asyncio.wait_for(entered.wait(), timeout=10)
                    if writer == "confirmation":
                        operation = _confirm(client, inventory)
                    elif writer == "evidence":
                        operation = _evidence(client, inventory)
                    else:
                        operation = _correct(
                            client,
                            inventory.trade_id,
                            inventory.buy_ids[0],
                            "BUY",
                            100,
                            "2.10",
                            "2026-08-05",
                        )
                    contender = asyncio.create_task(operation)
                    await _assert_waiting_for_lock(observer, contender)
                finally:
                    resume.set()
                    results = await asyncio.wait_for(
                        asyncio.gather(
                            batch, *([contender] if contender else []), return_exceptions=True
                        ),
                        timeout=15,
                    )
                assert not isinstance(results[0], BaseException), results[0]
                assert results[0]["status"] == "APPLIED"
                assert len(results) == 2 and not isinstance(results[1], BaseException), results
                if writer == "confirmation":
                    assert results[1].status_code == 409, results[1].text
                    assert results[1].json()["code"] == "EXECUTION_CURRENCY_CONFLICT"
                elif writer == "evidence":
                    assert results[1].status_code == 201, results[1].text
                else:
                    assert results[1]["id"] != inventory.buy_ids[0]
                    assert results[1]["currency_confirmation"] is None
                state = await _state(database.engine)
                assert len(state["execution_currency_confirmations"]) == 2
                assert {
                    str(row["execution_id"]) for row in state["execution_currency_confirmations"]
                } == set(inventory.buy_ids)
                if writer == "correction":
                    replacement = next(
                        row
                        for row in state["execution_records"]
                        if str(row["id"]) == results[1]["id"]
                    )
                    assert str(replacement["supersedes_execution_id"]) == inventory.buy_ids[0]
        finally:
            await observer.dispose()

    asyncio.run(exercise())


def test_active_owner_writer_makes_batch_fail_closed_and_next_attempt_revalidates(
    recovery_database: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    _migrate(recovery_database, "head")

    async def exercise() -> None:
        async with _client(recovery_database) as (client, database):
            inventory = await _seed(client)
            plan = await _plan(client, inventory)
            entered, resume = asyncio.Event(), asyncio.Event()
            original = SqlAlchemyExecutionCurrencyConfirmationRepository.add
            pause_once = True

            async def held(self, confirmation):
                nonlocal pause_once
                result = await original(self, confirmation)
                if pause_once:
                    pause_once = False
                    entered.set()
                    await resume.wait()
                return result

            monkeypatch.setattr(SqlAlchemyExecutionCurrencyConfirmationRepository, "add", held)
            owner = asyncio.create_task(_confirm(client, inventory))
            try:
                await asyncio.wait_for(entered.wait(), timeout=10)
                with pytest.raises(DBAPIError) as rejected:
                    await asyncio.wait_for(_apply(database.engine, plan), timeout=10)
                assert rejected.value.orig.sqlstate == "55P03"  # PostgreSQL lock_not_available.
            finally:
                resume.set()
                response = await asyncio.wait_for(owner, timeout=10)
            assert response.status_code == 201, response.text
            state = await _state(database.engine)
            assert len(state["execution_currency_confirmations"]) == 1
            assert str(state["execution_currency_confirmations"][0]["id"]) == response.json()["id"]
            # A retry must reread the now committed winner, not continue a partly
            # applied batch or silently adopt its same-currency declaration.
            with pytest.raises(recovery.RecoveryError):
                await _apply(database.engine, plan)
            assert await _state(database.engine) == state

    asyncio.run(exercise())
