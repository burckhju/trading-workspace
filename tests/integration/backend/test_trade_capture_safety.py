"""Actual migrations and API writes on disposable databases, never user data."""

import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool
from tests.integration.backend.test_usd_chf_currency_references import (
    _client,
    _migrate,
    _product_payload,
)
from tests.integration.backend.test_usd_chf_currency_references import (
    currency_database as base_database,
)

BASE = "/api/v1/trade-position"
WORKSPACE = "00000000-0000-4000-8000-000000000001"
ACTOR = "00000000-0000-4000-8000-000000000002"


@pytest.fixture
def database():
    yield from base_database.__wrapped__()


async def product(client):
    response = await client.post("/api/v1/warrants", json=await _product_payload(client))
    assert response.status_code == 201, response.text
    return response.json()["id"]


def purchase(product_id, *, key=None, day="2026-08-17", quantity=10):
    return {
        "product_id": product_id,
        "quantity": quantity,
        "price_per_unit": "0.55",
        "executed_on": day,
        "execution_timezone": "Europe/Berlin",
        "request_id": str(key or uuid4()),
    }


async def sql(url, statement, params=None):
    engine = create_async_engine(url, poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            result = await connection.execute(text(statement), params or {})
            return result.mappings().all() if result.returns_rows else []
    finally:
        await engine.dispose()


async def seed_legacy_pair(url, product_id):
    ids = [str(uuid4()), str(uuid4())]
    for trade_id in ids:
        args = {
            "id": trade_id,
            "workspace": WORKSPACE,
            "actor": ACTOR,
            "product": product_id,
            "execution": str(uuid4()),
            "position": str(uuid4()),
        }
        await sql(
            url,
            "INSERT INTO trades(id, workspace_id, product_id, origin, created_at, "
            "created_by) "
            "VALUES(:id,:workspace,:product,'EXTERNAL','2026-08-17T08:00:00Z',:actor)",
            args,
        )
        await sql(
            url,
            "INSERT INTO "
            "execution_records(id,trade_id,product_id,side,quantity,price_per_unit,"
            "executed_at,recorded_at,recorded_by) "
            "VALUES(:execution,:id,:product,'BUY',3500,0.55,'2026-08-17T08:00:00Z',"
            "'2026-08-17T09:00:00Z',:actor)",
            args,
        )
        await sql(
            url,
            "INSERT INTO "
            "positions(id,trade_id,product_id,open_quantity,cost_basis,average_entry_price,"
            "opened_at,last_execution_at,realized_gross_pnl) "
            "VALUES(:position,:id,:product,3500,1925,0.55,'2026-08-17T08:00:00Z',"
            "'2026-08-17T08:00:00Z',0)",
            args,
        )
    return ids


def test_keyed_capture_duplicate_open_block_and_real_additional_purchase(database):
    _migrate(database, "head")

    async def exercise():
        async with _client(database) as client:
            pid = await product(client)
            body = purchase(pid)
            responses = await asyncio.gather(
                *[client.post(BASE + "/purchases/external", json=body) for _ in range(3)]
            )
            assert [r.status_code for r in responses] == [201, 201, 201], [
                r.text for r in responses
            ]
            trade_id = responses[0].json()["trade"]["id"]
            assert {r.json()["trade"]["id"] for r in responses} == {trade_id}
            assert {r.json()["execution"]["id"] for r in responses} == {
                responses[0].json()["execution"]["id"]
            }
            assert responses[0].json()["execution"]["executed_on"] == "2026-08-17"
            assert responses[0].json()["position"]["opened_on"] == "2026-08-17"
            assert (
                responses[0].json()["execution"]["recorded_at"]
                != responses[0].json()["execution"]["executed_at"]
            )
            conflict = await client.post(BASE + "/purchases/external", json=purchase(pid))
            assert conflict.status_code == 409, conflict.text
            assert conflict.json()["code"] == "OPEN_TRADE_EXISTS"
            assert conflict.json()["details"][0]["context"]["existing_trade_id"] == trade_id
            changed = await client.post(BASE + "/purchases/external", json={**body, "quantity": 11})
            assert changed.status_code == 409 and changed.json()["code"] == "CAPTURE_KEY_CONFLICT"
            additional = {
                k: v
                for k, v in purchase(pid, quantity=5, day="2026-08-18").items()
                if k != "product_id"
            }
            replies = await asyncio.gather(
                *[
                    client.post(BASE + f"/trades/{trade_id}/purchases", json=additional)
                    for _ in range(3)
                ]
            )
            assert all(r.status_code == 201 for r in replies), [r.text for r in replies]
            assert len({r.json()["execution"]["id"] for r in replies}) == 1
            assert (await client.get(BASE + f"/trades/{trade_id}/position")).json()[
                "open_quantity"
            ] == 15
            sale = {
                **additional,
                "quantity": 15,
                "executed_on": "2026-08-19",
                "request_id": str(uuid4()),
            }
            sold = await client.post(BASE + f"/trades/{trade_id}/sales", json=sale)
            assert sold.status_code == 201, sold.text
            assert sold.json()["position"]["closed_on"] == "2026-08-19"
            assert (
                await client.post(BASE + f"/trades/{trade_id}/sales", json=sale)
            ).status_code == 201
            next_trade = await client.post(
                BASE + "/purchases/external", json=purchase(pid, day="2026-08-20")
            )
            assert next_trade.status_code == 201 and next_trade.json()["trade"]["id"] != trade_id

    asyncio.run(exercise())


def test_legacy_duplicate_cancel_is_targeted_auditable_and_not_a_sale(database):
    _migrate(database, "20260912_0035")

    async def setup():
        async with _client(database) as client:
            pid = await product(client)
        ids = await seed_legacy_pair(database, pid)
        return pid, ids

    pid, (keep, cancel) = asyncio.run(setup())
    before = asyncio.run(sql(database, "SELECT * FROM positions ORDER BY id"))
    _migrate(database, "head")
    assert asyncio.run(
        sql(database, "SELECT trade_id,open_quantity FROM positions ORDER BY id")
    ) == [{"trade_id": row["trade_id"], "open_quantity": row["open_quantity"]} for row in before]

    async def exercise():
        async with _client(database) as client:
            url = BASE + f"/trades/{cancel}"
            preview = (await client.get(url + "/cancellation")).json()
            assert preview["can_cancel"] and preview["other_open_trade_ids"] == [keep]
            body = {
                "expected_product_id": pid,
                "expected_state_token": preview["state_token"],
                "reason": "versehentlich doppelt erfasst",
                "duplicate_of_trade_id": keep,
                "confirmed": True,
            }
            invalid = await client.post(
                url + "/cancel", json={**body, "expected_product_id": str(uuid4())}
            )
            assert invalid.status_code == 409
            assert (
                await client.post(url + "/cancel", json={**body, "confirmed": False})
            ).status_code == 422
            cancelled = await client.post(url + "/cancel", json=body)
            assert cancelled.status_code == 200, cancelled.text
            assert cancelled.json()["cancelled_at"] is not None
            assert (await client.post(url + "/cancel", json=body)).status_code == 200
            history = (await client.get(url + "/timeline")).json()
            assert [item["execution_side"] for item in history if item["kind"] == "EXECUTION"] == [
                "BUY"
            ]
            assert sum(item["kind"] == "CANCELLATION" for item in history) == 1
            position = (await client.get(url + "/position")).json()
            assert (
                position["is_cancelled"]
                and position["open_quantity"] == 3500
                and not position["is_closed"]
            )
            retained = (await client.get(BASE + f"/trades/{keep}")).json()
            assert retained["cancelled_at"] is None
            assert not (await client.get(url + "/ft011-eligibility")).json()["eligible"]
            execution = {k: v for k, v in purchase(pid).items() if k != "product_id"}
            for suffix in ("/purchases", "/sales"):
                result = await client.post(url + suffix, json=execution)
                assert (
                    result.status_code == 409 and result.json()["code"] == "TRADE_CANCELLED"
                ), result.text
            assert (
                await client.post(url + "/management/stop", json={"price": "0.3"})
            ).status_code == 409
            audits = await sql(database, "SELECT * FROM audit_events WHERE aggregate_type='TRADE'")
            assert len(audits) == 1 and str(audits[0]["aggregate_id"]) == cancel
            assert len(await sql(database, "SELECT * FROM execution_records")) == 2
            after = await sql(database, "SELECT * FROM positions ORDER BY id")
            for old, new in zip(before, after, strict=True):
                assert all(new[key] == value for key, value in old.items())
            # No new independent first purchase while retained trade remains open.
            assert (
                await client.post(BASE + "/purchases/external", json=purchase(pid))
            ).status_code == 409
            # Cancellation status and all numerical position facts survive API retries.
            assert (await client.get(url + "/cancellation")).json()["reason"] == body["reason"]

    asyncio.run(exercise())


def test_simultaneous_different_initial_requests_create_only_one_trade(database):
    _migrate(database, "head")

    async def exercise():
        async with _client(database) as client:
            pid = await product(client)
            replies = await asyncio.gather(
                *[client.post(BASE + "/purchases/external", json=purchase(pid)) for _ in range(4)]
            )
            assert sorted(r.status_code for r in replies) == [201, 409, 409, 409], [
                r.text for r in replies
            ]
            assert (
                len(await sql(database, "SELECT id FROM trades WHERE product_id=:id", {"id": pid}))
                == 1
            )

    asyncio.run(exercise())


def test_stale_preview_sales_and_foreign_trade_fail_closed(database):
    _migrate(database, "head")

    async def exercise():
        async with _client(database) as client:
            pid = await product(client)
            created = await client.post(BASE + "/purchases/external", json=purchase(pid))
            trade_id = created.json()["trade"]["id"]
            url = BASE + f"/trades/{trade_id}"
            preview = (await client.get(url + "/cancellation")).json()
            body = {
                "expected_product_id": pid,
                "expected_state_token": preview["state_token"],
                "reason": "wrong entry",
                "confirmed": True,
            }
            assert (
                await client.post(url + "/management/notes", json={"text": "new note"})
            ).status_code == 201
            stale = await client.post(url + "/cancel", json=body)
            assert stale.status_code == 409 and stale.json()["code"] == "CANCELLATION_STALE"
            sale = {
                k: v
                for k, v in purchase(pid, day="2026-08-18", quantity=1).items()
                if k != "product_id"
            }
            assert (await client.post(url + "/sales", json=sale)).status_code == 201
            preview = (await client.get(url + "/cancellation")).json()
            assert not preview["can_cancel"]
            blocked = await client.post(
                url + "/cancel", json={**body, "expected_state_token": preview["state_token"]}
            )
            assert blocked.status_code == 409 and blocked.json()["code"] == "CANCELLATION_BLOCKED"
            assert (await client.get(BASE + f"/trades/{uuid4()}/cancellation")).status_code == 404
            original = (await client.get(url + "/timeline")).json()[0]
            correction = await client.post(
                url + f"/executions/{original['id']}/corrections",
                json={
                    "side": "BUY",
                    "quantity": 10,
                    "price_per_unit": "0.55",
                    "executed_on": "2026-08-16",
                    "execution_timezone": "Europe/Berlin",
                },
            )
            assert correction.status_code == 201, correction.text
            assert correction.json()["position"]["opened_on"] == "2026-08-16"
            history = (await client.get(url + "/timeline")).json()
            assert any(
                item["id"] == original["id"] and item["executed_on"] == "2026-08-17"
                for item in history
            )

    asyncio.run(exercise())


def test_database_guard_serializes_raw_position_creation_and_reopening(database):
    from sqlalchemy.exc import IntegrityError

    _migrate(database, "head")

    async def exercise():
        async with _client(database) as client:
            pid = await product(client)
            engine = create_async_engine(database, poolclass=NullPool)

            async def raw_purchase():
                tid = str(uuid4())
                args = {
                    "id": tid,
                    "product": pid,
                    "workspace": WORKSPACE,
                    "actor": ACTOR,
                    "position": str(uuid4()),
                    "execution": str(uuid4()),
                }
                try:
                    async with engine.begin() as connection:
                        await connection.execute(
                            text(
                                "INSERT INTO trades(id,workspace_id,product_id,origin,"
                                "created_at,created_by) "
                                "VALUES(:id,:workspace,:product,'EXTERNAL',now(),:actor)"
                            ),
                            args,
                        )
                        await connection.execute(
                            text(
                                "INSERT INTO "
                                "execution_records(id,trade_id,product_id,side,quantity,price_per_unit,"
                                "executed_at,recorded_at,recorded_by) "
                                "VALUES(:execution,:id,:product,'BUY',10,0.55,'2026-08-17T08:00:00Z',now(),"
                                ":actor)"
                            ),
                            args,
                        )
                        await connection.execute(
                            text(
                                "INSERT INTO "
                                "positions(id,trade_id,product_id,open_quantity,cost_basis,average_entry_price,"
                                "opened_at,last_execution_at,realized_gross_pnl) "
                                "VALUES(:position,:id,:product,10,5.5,0.55,'2026-08-17T08:00:00Z',"
                                "'2026-08-17T08:00:00Z',0)"
                            ),
                            args,
                        )
                    return tid
                except IntegrityError as error:
                    assert (
                        getattr(error.orig.__cause__, "constraint_name", None)
                        == "tw_one_open_trade"
                    )
                    return None

            try:
                replies = await asyncio.gather(raw_purchase(), raw_purchase(), raw_purchase())
                assert len([tid for tid in replies if tid]) == 1, replies
                tid = next(tid for tid in replies if tid)
                sale = {
                    k: v for k, v in purchase(pid, day="2026-08-18").items() if k != "product_id"
                }
                assert (
                    await client.post(BASE + f"/trades/{tid}/sales", json=sale)
                ).status_code == 201
                assert (
                    await client.post(
                        BASE + "/purchases/external", json=purchase(pid, day="2026-08-19")
                    )
                ).status_code == 201
                with pytest.raises(IntegrityError) as failure:
                    async with engine.begin() as connection:
                        await connection.execute(
                            text(
                                "UPDATE positions SET "
                                "open_quantity=10,cost_basis=5.5,closed_at=NULL,"
                                "closed_on=NULL WHERE "
                                "trade_id=:id"
                            ),
                            {"id": tid},
                        )
                assert failure.value.orig.__cause__.constraint_name == "tw_one_open_trade"
                assert len(await sql(database, "SELECT id FROM trades")) == 2
            finally:
                await engine.dispose()

    asyncio.run(exercise())


def test_cancellation_rollback_monitoring_exclusion_and_pending_notifications(
    database, monkeypatch
):
    from datetime import UTC, datetime, timedelta
    from unittest.mock import AsyncMock
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.core.config import Settings
    from app.database import DatabaseManager
    from app.features.market.persistence.models import AuditEventModel
    from app.features.notification.persistence.durable_delivery import (
        SqlAlchemyDurableNotificationDeliveryStore,
    )
    from app.features.operational_workspace.service.position_snapshot import (
        OperationalPositionSnapshotService,
    )
    from app.features.position_monitoring.service.product_valuation import (
        ProductPositionValuationService,
    )
    from app.features.position_monitoring.service.subjects import SqlAlchemyMonitoringSubjectReader
    from app.features.trade_position.service.cancellation import TradeCancellationService

    _migrate(database, "head")

    async def exercise():
        async with _client(database) as client:
            pid = await product(client)
            result = (await client.post(BASE + "/purchases/external", json=purchase(pid))).json()
            tid, position_id = result["trade"]["id"], result["position"]["id"]
            aid, nid, attempt = str(uuid4()), str(uuid4()), str(uuid4())
            args = {
                "trade": tid,
                "position": position_id,
                "alert": aid,
                "notification": nid,
                "attempt": attempt,
            }
            await sql(
                database,
                "INSERT INTO "
                "alerts(id,position_id,trade_id,alert_type,severity,rule_key,reason,"
                "observed_value,threshold_value,market_data_observed_at,detected_at,status) "
                "VALUES(:alert,:position,:trade,'STOP_BREACHED','WARNING','test','test',1,2,"
                "now(),now(),'OPEN')",
                args,
            )
            await sql(
                database,
                "INSERT INTO "
                "notifications(id,alert_id,channel,destination_key,body,created_at,status) "
                "VALUES(:notification,:alert,'TELEGRAM','test','test',now(),'PENDING')",
                args,
            )
            await sql(
                database,
                "INSERT INTO "
                "notification_delivery_attempts(id,notification_id,attempt_number,status,"
                "attempted_at,retryable) "
                "VALUES(:attempt,:notification,1,'IN_PROGRESS',now(),false)",
                args,
            )
            url = BASE + f"/trades/{tid}"
            blocked = (await client.get(url + "/cancellation")).json()
            assert not blocked["can_cancel"] and any("versendet" in b for b in blocked["blockers"])
            await sql(
                database,
                "UPDATE notification_delivery_attempts SET status='FAILED',completed_at=now() "
                "WHERE id=:id",
                {"id": attempt},
            )
            preview = (await client.get(url + "/cancellation")).json()
            engine = create_async_engine(database, poolclass=NullPool)
            sessions = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
            try:
                async with sessions() as session:
                    original_add = AsyncSession.add

                    def broken_audit(self, instance, **kwargs):
                        if isinstance(instance, AuditEventModel):
                            raise RuntimeError("audit unavailable")
                        return original_add(self, instance, **kwargs)

                    with monkeypatch.context() as patch:
                        patch.setattr(AsyncSession, "add", broken_audit)
                        with pytest.raises(RuntimeError, match="audit unavailable"):
                            await TradeCancellationService(session).cancel(
                                workspace_id=UUID(WORKSPACE),
                                trade_id=UUID(tid),
                                expected_product_id=UUID(pid),
                                expected_state_token=preview["state_token"],
                                actor=UUID(ACTOR),
                                reason="entry mistake",
                            )
                assert (await client.get(url)).json()["cancelled_at"] is None
                assert (
                    await sql(
                        database, "SELECT status FROM notifications WHERE id=:id", {"id": nid}
                    )
                )[0]["status"] == "PENDING"
                body = {
                    "expected_product_id": pid,
                    "expected_state_token": preview["state_token"],
                    "reason": "entry mistake",
                    "confirmed": True,
                }
                cancelled = await client.post(url + "/cancel", json=body)
                assert cancelled.status_code == 200, cancelled.text
                assert (
                    await sql(
                        database, "SELECT status FROM notifications WHERE id=:id", {"id": nid}
                    )
                )[0]["status"] == "FAILED"
                assert (await sql(database, "SELECT status FROM alerts WHERE id=:id", {"id": aid}))[
                    0
                ]["status"] == "RESOLVED"
                async with sessions() as session:
                    health, valuation = AsyncMock(), AsyncMock()
                    rows = await OperationalPositionSnapshotService(
                        session, health_reader=health, valuation_reader=valuation
                    ).list_positions(workspace_id=UUID(WORKSPACE))
                    assert rows == ()
                    health.assert_not_awaited()
                    valuation.assert_not_awaited()
                    assert await SqlAlchemyMonitoringSubjectReader(session).list_resolutions() == ()
                db = DatabaseManager(Settings(_env_file=None, database_url=database))
                try:
                    store = SqlAlchemyDurableNotificationDeliveryStore(db)
                    assert await store.list_pending_notification_ids(limit=10) == ()
                    preparation = await store.prepare(
                        notification_id=UUID(nid),
                        attempt_id=uuid4(),
                        now=datetime.now(UTC),
                        stale_before=datetime.now(UTC) - timedelta(minutes=5),
                        max_attempts=3,
                    )
                    assert preparation.terminal_result.error_code == "TRADE_CANCELLED"
                    assert (
                        await ProductPositionValuationService(database=db).for_trade(UUID(tid))
                        is None
                    )
                finally:
                    await db.dispose()
            finally:
                await engine.dispose()

    asyncio.run(exercise())
