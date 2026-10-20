"""Actual currency commands and captures against a guarded disposable PostgreSQL.

Synthetic user declarations are explicit facts in this test. No listing, quote,
product identity or EUR fixture default supplies an execution currency. These
owner tests do not claim the independent report's snapshot or browser contract.
"""

import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from tests.integration.backend.learning.test_journal_write_postgres import (
    journal_database as guarded_database,
)
from tests.integration.backend.learning.test_journal_write_postgres import planned_purchase
from tests.integration.backend.learning.test_trade_link_application_postgres import (
    _seed_observation,
)
from tests.integration.backend.test_realized_gross_trace_postgres import _business_state
from tests.integration.backend.test_trade_capture_safety import (
    ACTOR,
    BASE,
    WORKSPACE,
    product,
    purchase,
    sql,
)
from tests.integration.backend.test_usd_chf_currency_references import _client, _migrate

from app.features.learning.persistence.repositories import SqlAlchemyIdempotencyRecordRepository

DECLARATION = {"currency_code": "EUR", "source": "USER_CONFIRMED", "note": "Synthetic receipt"}


@pytest.fixture
def confirmation_database() -> Iterator[str]:
    yield from guarded_database.__wrapped__()


@pytest.fixture(autouse=True)
def no_external_http(monkeypatch: pytest.MonkeyPatch):
    external_async = AsyncMock(side_effect=AssertionError("External HTTP forbidden"))
    external_sync = Mock(side_effect=AssertionError("External HTTP forbidden"))
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", external_async)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", external_sync)
    yield
    external_async.assert_not_awaited()
    external_sync.assert_not_called()


def confirmation_url(trade_id, execution_id):
    return BASE + f"/trades/{trade_id}/executions/{execution_id}/currency-confirmations"


async def confirmations(url):
    return await sql(url, "SELECT * FROM execution_currency_confirmations ORDER BY confirmed_at,id")


def test_migration_preserves_unknown_history_and_capture_failure_rolls_back(confirmation_database):
    _migrate(confirmation_database, "head")

    async def capture_unknown():
        async with _client(confirmation_database) as client:
            pid = await product(client)
            body = purchase(pid)
            bought = await client.post(BASE + "/purchases/external", json=body)
            assert bought.status_code == 201, bought.text
            trade_id, execution_id = bought.json()["trade"]["id"], bought.json()["execution"]["id"]
        old_executions = await sql(confirmation_database, "SELECT * FROM execution_records")
        old_positions = await sql(confirmation_database, "SELECT * FROM positions")
        assert await confirmations(confirmation_database) == []
        return pid, body, trade_id, execution_id, old_executions, old_positions

    pid, body, trade_id, execution_id, old_executions, old_positions = asyncio.run(
        capture_unknown()
    )
    # Current API responses resolve provenance and therefore require schema0047.
    # Create the unconfirmed fact through that real owner, then use the permitted
    # empty-evidence downgrade to reproduce legacy0046 without inserting SQL facts.
    # Application connections are closed during migration, as in actual startup.
    _migrate(confirmation_database, "20261014_0046", action="downgrade")
    assert asyncio.run(sql(confirmation_database, "SELECT version_num FROM alembic_version")) == [
        {"version_num": "20261014_0046"}
    ]
    _migrate(confirmation_database, "head")

    async def exercise():
        async with _client(confirmation_database) as client:
            assert await confirmations(confirmation_database) == []
            assert (
                await sql(confirmation_database, "SELECT * FROM execution_records")
                == old_executions
            )
            assert await sql(confirmation_database, "SELECT * FROM positions") == old_positions
            history = await client.get(confirmation_url(trade_id, execution_id))
            assert history.status_code == 200 and history.json() == {
                "current": None,
                "history": [],
                "currency_resolution": {
                    "currency_code": None,
                    "source": "UNKNOWN",
                    "source_execution_ids": [],
                    "confirmation_ids": [],
                },
            }
            replay = await client.post(BASE + "/purchases/external", json=body)
            assert (
                replay.status_code == 201
                and replay.json()["execution"]["currency_confirmation"] is None
            )

            invalid = {
                k: v for k, v in purchase(pid, day="2026-08-18").items() if k != "product_id"
            }
            invalid["currency_confirmation"] = {**DECLARATION, "currency_code": "ZZZ"}
            failed = await client.post(BASE + f"/trades/{trade_id}/purchases", json=invalid)
            assert failed.status_code == 422 and failed.json()["code"] == "CURRENCY_NOT_FOUND"
            assert await confirmations(confirmation_database) == []
            assert (
                await sql(confirmation_database, "SELECT * FROM execution_records")
                == old_executions
            )
            assert await sql(confirmation_database, "SELECT * FROM positions") == old_positions

            posted = await client.post(
                confirmation_url(trade_id, execution_id),
                json={**DECLARATION, "request_id": str(uuid4())},
            )
            assert posted.status_code == 201, posted.text
            with pytest.raises(
                AssertionError,
                match="Refusing downgrade: execution currency provenance would be lost",
            ):
                await asyncio.to_thread(
                    _migrate, confirmation_database, "20261014_0046", action="downgrade"
                )
            assert len(await confirmations(confirmation_database)) == 1
            assert (
                await sql(confirmation_database, "SELECT * FROM execution_records")
                == old_executions
            )

    asyncio.run(exercise())


def test_capture_retry_correction_and_read_enrichment_use_exact_execution(confirmation_database):
    _migrate(confirmation_database, "head")

    async def exercise():
        engine = create_async_engine(confirmation_database, poolclass=NullPool)
        try:
            async with _client(confirmation_database) as client:
                pid = await product(client)
                body = {**purchase(pid), "currency_confirmation": DECLARATION}
                replies = await asyncio.gather(
                    *[client.post(BASE + "/purchases/external", json=body) for _ in range(3)]
                )
                assert [reply.status_code for reply in replies] == [201, 201, 201], [
                    r.text for r in replies
                ]
                bought = replies[0].json()
                trade_id = bought["trade"]["id"]
                original_id = bought["execution"]["id"]
                original_fact = bought["execution"]["currency_confirmation"]
                assert {r.json()["execution"]["currency_confirmation"]["id"] for r in replies} == {
                    original_fact["id"]
                }
                assert original_fact["execution_id"] == original_id
                assert (
                    original_fact["source"] == "USER_CONFIRMED"
                    and original_fact["confirmed_by"] == ACTOR
                )
                changed = await client.post(
                    BASE + "/purchases/external",
                    json={**body, "currency_confirmation": {**DECLARATION, "currency_code": "USD"}},
                )
                assert (
                    changed.status_code == 409 and changed.json()["code"] == "CAPTURE_KEY_CONFLICT"
                )

                additional_body = {
                    k: v
                    for k, v in purchase(pid, day="2026-08-18", quantity=5).items()
                    if k != "product_id"
                }
                additional = await client.post(
                    BASE + f"/trades/{trade_id}/purchases",
                    json={**additional_body, "currency_confirmation": DECLARATION},
                )
                assert additional.status_code == 201, additional.text
                assert (
                    additional.json()["execution"]["currency_confirmation"]["execution_id"]
                    == additional.json()["execution"]["id"]
                )
                sale_body = {
                    **additional_body,
                    "quantity": 5,
                    "price_per_unit": "1.55",
                    "executed_on": "2026-08-19",
                    "request_id": str(uuid4()),
                    "currency_confirmation": DECLARATION,
                }
                sale = await client.post(BASE + f"/trades/{trade_id}/sales", json=sale_body)
                assert sale.status_code == 201, sale.text
                sale_id = sale.json()["execution"]["id"]
                sale_fact = sale.json()["execution"]["currency_confirmation"]
                assert sale_fact["execution_id"] == sale_id

                corrected_body = {
                    "side": "SELL",
                    "quantity": 5,
                    "price_per_unit": "1.65",
                    "executed_on": "2026-08-19",
                    "execution_timezone": "Europe/Berlin",
                }
                corrected = await client.post(
                    BASE + f"/trades/{trade_id}/executions/{sale_id}/corrections",
                    json=corrected_body,
                )
                assert corrected.status_code == 201, corrected.text
                replacement_id = corrected.json()["execution"]["id"]
                assert (
                    replacement_id != sale_id
                    and corrected.json()["execution"]["currency_confirmation"] is None
                )
                assert (await client.get(confirmation_url(trade_id, sale_id))).json()[
                    "current"
                ] == sale_fact
                assert (await client.get(confirmation_url(trade_id, replacement_id))).json() == {
                    "current": None,
                    "history": [],
                    "currency_resolution": {
                        "currency_code": "EUR",
                        "source": "REPLACED_EXECUTION",
                        "source_execution_ids": [sale_id],
                        "confirmation_ids": [sale_fact["id"]],
                    },
                }
                second = await client.post(
                    BASE + f"/trades/{trade_id}/executions/{replacement_id}/corrections",
                    json={
                        **corrected_body,
                        "price_per_unit": "1.75",
                        "currency_confirmation": DECLARATION,
                    },
                )
                assert second.status_code == 201, second.text
                current_id = second.json()["execution"]["id"]
                assert (
                    second.json()["execution"]["currency_confirmation"]["execution_id"]
                    == current_id
                )
                assert len(await confirmations(confirmation_database)) == 4

                before = await _business_state(engine)
                provenance_before = await confirmations(confirmation_database)
                timeline = await client.get(BASE + f"/trades/{trade_id}/timeline")
                assert timeline.status_code == 200, timeline.text
                entries = {row["id"]: row for row in timeline.json()}
                assert entries[original_id]["currency_confirmation"] == original_fact
                assert entries[sale_id]["currency_confirmation"] == sale_fact
                assert entries[replacement_id]["currency_confirmation"] is None
                assert entries[current_id]["currency_confirmation"]["execution_id"] == current_id
                for execution_id in (original_id, sale_id, replacement_id, current_id):
                    assert (
                        await client.get(confirmation_url(trade_id, execution_id))
                    ).status_code == 200
                assert await _business_state(engine) == before
                assert await confirmations(confirmation_database) == provenance_before
        finally:
            await engine.dispose()

    asyncio.run(exercise())


def test_confirmation_concurrency_scope_and_native_append_only_integrity(confirmation_database):
    _migrate(confirmation_database, "head")

    async def exercise():
        async with _client(confirmation_database) as client:
            pid = await product(client)
            bought = await client.post(BASE + "/purchases/external", json=purchase(pid))
            assert bought.status_code == 201, bought.text
            trade_id, execution_id = bought.json()["trade"]["id"], bought.json()["execution"]["id"]
            url = confirmation_url(trade_id, execution_id)
            body = {**DECLARATION, "request_id": str(uuid4())}
            results = await asyncio.gather(*[client.post(url, json=body) for _ in range(3)])
            assert [r.status_code for r in results] == [201, 201, 201], [r.text for r in results]
            first = results[0].json()
            assert {r.json()["id"] for r in results} == {first["id"]}
            changed = await client.post(url, json={**body, "currency_code": "USD"})
            assert (
                changed.status_code == 409
                and changed.json()["code"] == "EXECUTION_CURRENCY_REQUEST_CONFLICT"
            )
            contenders = [
                {
                    **DECLARATION,
                    "currency_code": code,
                    "supersedes_confirmation_id": first["id"],
                    "request_id": str(uuid4()),
                }
                for code in ("USD", "CHF")
            ]
            results = await asyncio.gather(*[client.post(url, json=value) for value in contenders])
            assert sorted(r.status_code for r in results) == [201, 409], [r.text for r in results]
            winner = next(r.json() for r in results if r.status_code == 201)
            rejected = next(r.json() for r in results if r.status_code == 409)
            assert rejected["code"] == "EXECUTION_CURRENCY_CONFLICT"
            history = (await client.get(url)).json()
            assert history == {"current": winner, "history": [first, winner]}
            assert (
                await client.post(url, json=body)
            ).json() == first  # Historical receipt, not currentness.
            assert (await client.get(url)).json()["current"] == winner
            wrong_scope = await client.get(confirmation_url(trade_id, str(uuid4())))
            assert (
                wrong_scope.status_code == 404
                and wrong_scope.json()["code"] == "EXECUTION_NOT_FOUND"
            )

            # Historical user-confirmed currency remains visible after catalog deactivation.
            await sql(
                confirmation_database,
                "UPDATE currencies SET is_active=false WHERE code=:code",
                {"code": winner["currency_code"]},
            )
            assert (await client.get(url)).json()["current"] == winner
            final_body = {
                **DECLARATION,
                "currency_code": winner["currency_code"],
                "supersedes_confirmation_id": winner["id"],
                "request_id": str(uuid4()),
            }
            final = await client.post(url, json=final_body)
            assert final.status_code == 201, final.text

            before = await confirmations(confirmation_database)
            for statement in (
                "UPDATE execution_currency_confirmations SET currency_code='EUR' WHERE id=:id",
                "DELETE FROM execution_currency_confirmations WHERE id=:id",
            ):
                with pytest.raises(IntegrityError, match="immutable"):
                    await sql(confirmation_database, statement, {"id": first["id"]})
            insert = """INSERT INTO execution_currency_confirmations
                (id,workspace_id,trade_id,execution_id,currency_code,source,note,confirmed_at,
                 confirmed_by,supersedes_confirmation_id,request_id,request_fingerprint)
                VALUES(:id,:workspace,:trade,:execution,:currency,:source,NULL,:at,:actor,:previous,:request,:fingerprint)"""
            valid = dict(
                id=uuid4(),
                workspace=WORKSPACE,
                trade=trade_id,
                execution=execution_id,
                currency="EUR",
                source="USER_CONFIRMED",
                at=datetime.now(UTC),
                actor=ACTOR,
                previous=None,
                request=uuid4(),
                fingerprint="a" * 64,
            )
            violations = [
                ({}, "uq_execution_currency_root"),
                ({"previous": first["id"]}, "uq_execution_currency_successor"),
                ({"workspace": uuid4()}, "trade/workspace mismatch"),
                ({"execution": uuid4()}, "fk_execution_currency_execution_scope"),
                ({"previous": uuid4()}, "predecessor mismatch"),
                (
                    {"previous": final.json()["id"], "request": body["request_id"]},
                    "uq_execution_currency_request",
                ),
                (
                    {"previous": final.json()["id"], "currency": "ZZZ"},
                    "fk_execution_currency_code",
                ),
                (
                    {"previous": final.json()["id"], "at": datetime.now(UTC) - timedelta(days=1)},
                    "cannot precede",
                ),
                (
                    {"source": "LISTING", "previous": final.json()["id"]},
                    "CheckViolationError",
                ),
            ]
            for changes, expected in violations:
                with pytest.raises(IntegrityError, match=expected):
                    await sql(confirmation_database, insert, {**valid, **changes})
            assert await confirmations(confirmation_database) == before
            preview = (await client.get(BASE + f"/trades/{trade_id}/cancellation")).json()
            cancelled = await client.post(
                BASE + f"/trades/{trade_id}/cancel",
                json={
                    "expected_product_id": pid,
                    "expected_state_token": preview["state_token"],
                    "reason": "Synthetic mistaken entry",
                    "confirmed": True,
                },
            )
            assert cancelled.status_code == 200, cancelled.text
            rejected = await client.post(
                url,
                json={
                    **DECLARATION,
                    "supersedes_confirmation_id": final.json()["id"],
                    "request_id": str(uuid4()),
                },
            )
            assert rejected.status_code == 409 and rejected.json()["code"] == "TRADE_CANCELLED"
            with pytest.raises(IntegrityError, match="cancelled trade"):
                await sql(confirmation_database, insert, {**valid, "previous": final.json()["id"]})
            assert (await client.get(url)).json()["current"] == final.json()
            assert await confirmations(confirmation_database) == before

    asyncio.run(exercise())


def test_workspace_capture_and_learning_handoff_confirm_in_the_owner_transaction(
    confirmation_database, monkeypatch
):
    _migrate(confirmation_database, "head")

    async def exercise():
        async with _client(confirmation_database) as client:
            pid = await product(client)
            original_post = client.post

            async def with_explicit_workspace_declaration(url, **kwargs):
                if url == BASE + "/purchases/from-selection":
                    kwargs["json"] = {**kwargs["json"], "currency_confirmation": DECLARATION}
                return await original_post(url, **kwargs)

            # Reuse the complete plan/selection owner fixture; only add the actual request field.
            with monkeypatch.context() as context:
                context.setattr(client, "post", with_explicit_workspace_declaration)
                bought = await planned_purchase(client, pid)
            execution = bought.json()["execution"]
            assert execution["currency_confirmation"]["execution_id"] == execution["id"]
            closed = await client.post(
                BASE + f"/trades/{bought.json()['trade']['id']}/sales",
                json={
                    "quantity": 10,
                    "price_per_unit": "0.55",
                    "executed_on": "2026-08-18",
                    "execution_timezone": "Europe/Berlin",
                },
            )
            assert closed.status_code == 201, closed.text
            assert closed.json()["execution"]["currency_confirmation"] is None
            assert closed.json()["execution"]["currency_resolution"] == {
                "currency_code": "EUR",
                "source": "PRIOR_BUYS",
                "source_execution_ids": [execution["id"]],
                "confirmation_ids": [execution["currency_confirmation"]["id"]],
            }

            underlying_id = (await client.get(f"/api/v1/warrants/{pid}")).json()["underlying_id"]
            engine = create_async_engine(confirmation_database, poolclass=NullPool)
            try:
                sessions = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
                async with sessions() as session:
                    observation_id, _ = await _seed_observation(
                        session,
                        workspace_id=UUID(WORKSPACE),
                        underlying_id=UUID(underlying_id),
                        product_id=UUID(pid),
                    )
                    await session.commit()
                before = await _business_state(engine)
                before_confirmations = await confirmations(confirmation_database)
                url = f"/api/v1/learning/external-observations/{observation_id}/execute-as-trade"
                body = {
                    "quantity": 2,
                    "price_per_unit": "11.25",
                    "executed_at": "2026-08-23T08:00:00Z",
                    "currency_confirmation": DECLARATION,
                }
                headers = {"Idempotency-Key": str(uuid4())}
                failed = await client.post(
                    url,
                    json={**body, "currency_confirmation": {**DECLARATION, "currency_code": "ZZZ"}},
                    headers=headers,
                )
                assert (
                    failed.status_code == 422 and failed.json()["code"] == "CURRENCY_NOT_FOUND"
                ), failed.text
                assert await _business_state(engine) == before
                assert await confirmations(confirmation_database) == before_confirmations
                # Fail after the real link insert but before receipt completion. A nested
                # link commit would leave a trade, declaration and IN_PROGRESS receipt.
                with monkeypatch.context() as context:
                    context.setattr(
                        SqlAlchemyIdempotencyRecordRepository,
                        "mark_succeeded",
                        AsyncMock(side_effect=RuntimeError("Synthetic receipt failure")),
                    )
                    failed_receipt = await client.post(url, json=body, headers=headers)
                    assert failed_receipt.status_code == 422, failed_receipt.text
                assert await _business_state(engine) == before
                assert await confirmations(confirmation_database) == before_confirmations
                assert (
                    await sql(
                        confirmation_database, "SELECT id FROM external_observation_trade_links"
                    )
                    == []
                )
                assert (
                    await sql(
                        confirmation_database,
                        "SELECT id FROM external_observation_trade_link_versions",
                    )
                    == []
                )
                created = await client.post(url, json=body, headers=headers)
                assert created.status_code == 201, created.text
                replay = await client.post(url, json=body, headers=headers)
                assert replay.status_code == 200 and replay.json()["replayed"], replay.text
                assert replay.json()["trade_id"] == created.json()["trade_id"]
                changed = await client.post(
                    url,
                    json={**body, "currency_confirmation": {**DECLARATION, "currency_code": "USD"}},
                    headers=headers,
                )
                assert (
                    changed.status_code == 409
                    and changed.json()["code"] == "IDEMPOTENCY_KEY_REUSED"
                )
                rows = await sql(
                    confirmation_database,
                    "SELECT id FROM execution_records WHERE trade_id=:trade",
                    {"trade": created.json()["trade_id"]},
                )
                assert len(rows) == 1
                history = (
                    await client.get(confirmation_url(created.json()["trade_id"], rows[0]["id"]))
                ).json()
                assert history["current"]["currency_code"] == "EUR" and len(history["history"]) == 1
                assert history["currency_resolution"] == {
                    "currency_code": "EUR",
                    "source": "USER_CONFIRMED",
                    "source_execution_ids": [str(rows[0]["id"])],
                    "confirmation_ids": [history["current"]["id"]],
                }
                confirmations_before_sale = await confirmations(confirmation_database)
                sold = await client.post(
                    f"{BASE}/trades/{created.json()['trade_id']}/sales",
                    json={
                        "quantity": 2,
                        "price_per_unit": "12.25",
                        "executed_at": "2026-08-24T08:00:00Z",
                    },
                )
                assert sold.status_code == 201, sold.text
                assert sold.json()["execution"]["currency_confirmation"] is None
                assert sold.json()["execution"]["currency_resolution"] == {
                    "currency_code": "EUR",
                    "source": "PRIOR_BUYS",
                    "source_execution_ids": [str(rows[0]["id"])],
                    "confirmation_ids": [history["current"]["id"]],
                }
                assert await confirmations(confirmation_database) == confirmations_before_sale
            finally:
                await engine.dispose()

    asyncio.run(exercise())
