"""Review value constraints and dispatch races on explicitly guarded synthetic PostgreSQL."""

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import httpx
import pytest
from app.features.alert.domain.models import Alert, AlertSeverity, AlertType
from app.features.alert.persistence.models import AlertModel
from app.features.alert.persistence.repositories import SqlAlchemyAlertRepository
from app.features.notification.domain.models import DeliveryResult, DeliveryStatus
from app.features.notification.persistence.durable_delivery import (
    SqlAlchemyDurableNotificationDeliveryStore,
)
from app.features.notification.persistence.models import (
    NotificationDeliveryAttemptModel,
    NotificationModel,
)
from app.features.notification.persistence.repositories import SqlAlchemyNotificationRepository
from app.features.notification.service.creation import AlertNotificationService
from app.features.notification.service.durable_delivery import DurableNotificationDeliveryService
from app.features.notification.service.hebeltrader_lifecycle import (
    suppress_pending_review_notifications,
)
from app.features.operational_workspace.service.read_model import OperationalWorkspaceReadModel
from app.features.trade_position.persistence.models import PositionModel, TradeModel
from app.features.trade_position.persistence.unit_of_work import SqlAlchemyTradePositionUnitOfWork
from sqlalchemy import event, select, text, update
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError

from tests.integration.backend.learning.test_journal_write_postgres import (
    journal_database as guarded_database,
)
from tests.integration.backend.test_realized_gross_report_postgres import _client
from tests.integration.backend.test_trade_capture_safety import (
    BASE,
    WORKSPACE,
    product,
    purchase,
)
from tests.integration.backend.test_usd_chf_currency_references import _migrate

REVIEW_TYPES = (
    AlertType.INDICATIVE_ENTRY_LOSS,
    AlertType.POSITION_REVIEW_DUE,
    AlertType.POSITION_DATA_UNAVAILABLE,
)
NON_PRICE_TYPES = REVIEW_TYPES[1:]
MIGRATION_ALERT_TYPES = (
    AlertType.STOP_REACHED,
    AlertType.TARGET_REACHED,
    AlertType.RISK_TREND_CHANGED,
    AlertType.RISK_VOLATILITY_HIGH,
    AlertType.HEBELTRADER_B04_LOSS,
    *REVIEW_TYPES,
)


@pytest.fixture
def review_notification_database():
    # No parent URL means skip; the existing owner guard requires the exact
    # trading_workspace_test target and generates/drops only its own UUID DB.
    yield from guarded_database.__wrapped__()


@pytest.fixture(autouse=True)
def forbid_external_calls(monkeypatch):
    asynchronous = AsyncMock(side_effect=AssertionError("External HTTP forbidden"))
    synchronous = Mock(side_effect=AssertionError("External HTTP forbidden"))
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", asynchronous)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", synchronous)
    yield
    asynchronous.assert_not_awaited()
    synchronous.assert_not_called()


def alert_fact(trade_id, position_id, kind):
    now = datetime.now(UTC)
    priced = kind not in NON_PRICE_TYPES
    return Alert(
        id=uuid4(),
        trade_id=trade_id,
        position_id=position_id,
        alert_type=kind,
        severity=AlertSeverity.WARNING,
        rule_key=f"synthetic-review:{uuid4()}",
        reason="Synthetic separate review; no original provider qualification asserted.",
        observed_value=Decimal("0.48") if priced else None,
        threshold_value=Decimal("0.55") if priced else None,
        market_data_observed_at=now if priced else None,
        detected_at=now,
        price_context={
            "basis": "WARRANT",
            "rule_version": "synthetic-position-review-v1",
            "completed_sessions": "20",
            "session_count_at": now.isoformat(),
            "currency": "EUR",
            "provider": "SYNTHETIC",
            "evaluation_mode": "SOURCE_BID" if priced else None,
            "observed_at": now.isoformat() if priced else None,
            "review_completed_sessions": "20",
            "review_session_count_at": now.isoformat(),
        },
    )


async def notification_for(session, item, *, destination_key="synthetic-no-delivery"):
    return await AlertNotificationService(
        notifications=SqlAlchemyNotificationRepository(session),
        new_id=uuid4,
        now=lambda: datetime.now(UTC),
    ).create_telegram(
        alert=item,
        symbol="SYNTHETIC-NO-PROVIDER",
        destination_key=destination_key,
    )


async def pending(database, trade_id, position_id, kind):
    item = alert_fact(trade_id, position_id, kind)
    async with database.session_context() as session:
        await SqlAlchemyAlertRepository(session).add(item)
        await session.flush()
        notification = await notification_for(session, item)
        await session.commit()
    return item, notification


def mocked_delivery(database):
    store = SqlAlchemyDurableNotificationDeliveryStore(database)
    adapter = SimpleNamespace(
        deliver=AsyncMock(
            return_value=DeliveryResult(
                status=DeliveryStatus.DELIVERED,
                retryable=False,
                provider_message_id="synthetic-mock-only",
            )
        )
    )
    delivery = DurableNotificationDeliveryService(
        store=store, adapter=adapter, new_id=uuid4, now=lambda: datetime.now(UTC)
    )
    return store, adapter, delivery


def test_0056_preserves_old_alert_and_enforces_nullable_shape_only_for_non_price_reviews(
    review_notification_database,
):
    _migrate(review_notification_database, "20261117_0055")

    async def previous_version():
        async with _client(review_notification_database) as (client, database):
            warrant = await product(client)
            bought = await client.post(BASE + "/purchases/external", json=purchase(warrant))
            assert bought.status_code == 201, bought.text
            trade = UUID(bought.json()["trade"]["id"])
            position = UUID(bought.json()["position"]["id"])
            old = alert_fact(trade, position, AlertType.HEBELTRADER_B04_LOSS)
            async with database.session_context() as session:
                await SqlAlchemyAlertRepository(session).add(old)
                await session.commit()
            return old

    previous = asyncio.run(previous_version())
    _migrate(review_notification_database, "20261117_0056")

    async def after_upgrade():
        async with _client(review_notification_database) as (client, database):
            async with database.session_context() as session:
                assert await session.scalar(text("SELECT version_num FROM alembic_version")) == (
                    "20261117_0056"
                )
                repository = SqlAlchemyAlertRepository(session)
                assert await repository.get(previous.id) == previous
                valid = {
                    kind: alert_fact(previous.trade_id, previous.position_id, kind)
                    for kind in MIGRATION_ALERT_TYPES
                }
                for item in valid.values():
                    await repository.add(item)
                await session.commit()
                for kind, item in valid.items():
                    assert await repository.get(item.id) == item
                    invalid_pairs = (
                        [(Decimal("0"), None), (None, Decimal("0")), (Decimal("0"), Decimal("0"))]
                        if kind in NON_PRICE_TYPES
                        else [(None, None), (Decimal("0.48"), None), (None, Decimal("0.55"))]
                    )
                    for observed, threshold in invalid_pairs:
                        with pytest.raises(IntegrityError, match="ck_alerts_alert_value_shape"):
                            async with session.begin_nested():
                                await session.execute(
                                    update(AlertModel)
                                    .where(AlertModel.id == item.id)
                                    .values(observed_value=observed, threshold_value=threshold)
                                )
                await session.rollback()
            response = await client.get(f"/api/v1/alerts/trades/{previous.trade_id}")
            assert response.status_code == 200, response.text
            by_id = {value["id"]: value for value in response.json()}
            assert len(by_id) == len(MIGRATION_ALERT_TYPES) + 1
            for kind in NON_PRICE_TYPES:
                value = by_id[str(valid[kind].id)]
                assert value["observed_value"] is None and value["threshold_value"] is None
                assert value["market_data_observed_at"] is None
            indicative = by_id[str(valid[AlertType.INDICATIVE_ENTRY_LOSS].id)]
            assert Decimal(indicative["observed_value"]) == Decimal("0.48")
            assert Decimal(indicative["threshold_value"]) == Decimal("0.55")

    asyncio.run(after_upgrade())
    with pytest.raises(AssertionError, match="destructive downgrade refused"):
        _migrate(review_notification_database, "20261117_0055", action="downgrade")

    async def history_survives_refused_downgrade():
        async with (
            _client(review_notification_database) as (_, database),
            database.session_context() as session,
        ):
            assert await session.scalar(text("SELECT version_num FROM alembic_version")) == (
                "20261117_0056"
            )
            assert await SqlAlchemyAlertRepository(session).get(previous.id) == previous
            assert len(tuple(await session.scalars(select(AlertModel)))) == (
                len(MIGRATION_ALERT_TYPES) + 1
            )

    asyncio.run(history_survives_refused_downgrade())


@pytest.mark.parametrize("kind", REVIEW_TYPES)
def test_full_sale_locks_dispatch_and_effective_owner_overrides_stale_projection(
    review_notification_database, monkeypatch, kind
):
    _migrate(review_notification_database, "head")

    async def exercise():
        assert make_url(review_notification_database).database.startswith("tw_currency_ref_test_")
        async with _client(review_notification_database) as (client, database):
            warrant = await product(client)
            bought = await client.post(BASE + "/purchases/external", json=purchase(warrant))
            assert bought.status_code == 201, bought.text
            trade = UUID(bought.json()["trade"]["id"])
            position = UUID(bought.json()["position"]["id"])
            sale = {
                "quantity": 4,
                "price_per_unit": "0.48",
                "executed_on": "2026-08-18",
                "execution_timezone": "Europe/Berlin",
                "request_id": str(uuid4()),
            }
            partial = await client.post(f"{BASE}/trades/{trade}/sales", json=sale)
            assert partial.status_code == 201, partial.text
            assert partial.json()["position"]["open_quantity"] == 6
            async with database.session_context() as session:
                old_position = await session.get(PositionModel, position)
                partial_projection = {
                    column.name: getattr(old_position, column.name)
                    for column in PositionModel.__table__.columns
                    if column.name not in {"id", "trade_id", "product_id"}
                }
            _, already_sent = await pending(database, trade, position, kind)
            store, adapter, delivery = mocked_delivery(database)
            assert (await delivery.deliver(already_sent.id)).status is DeliveryStatus.DELIVERED
            adapter.deliver.assert_awaited_once()
            adapter.deliver.reset_mock()
            _, awaiting = await pending(database, trade, position, kind)
            sale_ready, release_sale, dispatch_waiting = (asyncio.Event() for _ in range(3))
            original_commit = SqlAlchemyTradePositionUnitOfWork.commit

            async def pause_sale_commit(uow):
                await uow.flush()
                sale_ready.set()
                await asyncio.wait_for(release_sale.wait(), timeout=10)
                await original_commit(uow)

            monkeypatch.setattr(SqlAlchemyTradePositionUnitOfWork, "commit", pause_sale_commit)
            sale_task = asyncio.create_task(
                client.post(
                    f"{BASE}/trades/{trade}/sales",
                    json={**sale, "quantity": 6, "request_id": str(uuid4())},
                )
            )
            await asyncio.wait_for(sale_ready.wait(), timeout=10)

            def before_execute(_connection, _cursor, statement, _params, _context, _many):
                if "FROM trades" in statement and "FOR UPDATE" in statement:
                    dispatch_waiting.set()

            event.listen(database.engine.sync_engine, "before_cursor_execute", before_execute)
            dispatch_task = asyncio.create_task(delivery.deliver(awaiting.id))
            try:
                await asyncio.wait_for(dispatch_waiting.wait(), timeout=10)
                assert not dispatch_task.done()
                adapter.deliver.assert_not_awaited()
            finally:
                release_sale.set()
                try:
                    closed = await asyncio.wait_for(sale_task, timeout=10)
                    result = await asyncio.wait_for(dispatch_task, timeout=10)
                finally:
                    event.remove(
                        database.engine.sync_engine, "before_cursor_execute", before_execute
                    )
            assert closed.status_code == 201, closed.text
            assert closed.json()["position"]["open_quantity"] == 0
            assert result.error_code == "REVIEW_POSITION_CLOSED" and not result.retryable
            adapter.deliver.assert_not_awaited()

            # Restore the entire consistent earlier projection only in this
            # synthetic DB; it must not outweigh the actual economic SELL.
            async with database.session_context() as session:
                await session.execute(
                    update(PositionModel)
                    .where(PositionModel.id == position)
                    .values(**partial_projection)
                )
                await session.commit()
            _, stale = await pending(database, trade, position, kind)
            assert (await delivery.deliver(stale.id)).error_code == "REVIEW_POSITION_CLOSED"
            assert (await delivery.deliver(awaiting.id)).error_code == "REVIEW_POSITION_CLOSED"
            assert (await delivery.deliver(already_sent.id)).status is DeliveryStatus.DELIVERED
            adapter.deliver.assert_not_awaited()
            assert await store.list_pending_notification_ids(limit=100) == ()
            async with database.session_context() as session:
                rows = tuple(await session.scalars(select(NotificationModel)))
                assert {row.id: row.status for row in rows} == {
                    already_sent.id: "DELIVERED",
                    awaiting.id: "FAILED",
                    stale.id: "FAILED",
                }
                attempts = tuple(await session.scalars(select(NotificationDeliveryAttemptModel)))
                assert len(attempts) == 3
                assert len([a for a in attempts if a.error_code == "REVIEW_POSITION_CLOSED"]) == 2
                assert len(tuple(await session.scalars(select(AlertModel)))) == 3
                assert (
                    await OperationalWorkspaceReadModel(session)._notification_failure_actions(
                        UUID(WORKSPACE)
                    )
                    == []
                )

    asyncio.run(exercise())


@pytest.mark.parametrize("kind", REVIEW_TYPES)
def test_review_suppression_is_atomic_and_late_retry_never_reopens_its_outbox(
    review_notification_database, kind
):
    _migrate(review_notification_database, "head")

    async def exercise():
        async with _client(review_notification_database) as (client, database):
            warrant = await product(client)
            bought = await client.post(BASE + "/purchases/external", json=purchase(warrant))
            assert bought.status_code == 201, bought.text
            trade = UUID(bought.json()["trade"]["id"])
            position = UUID(bought.json()["position"]["id"])
            item, awaiting = await pending(database, trade, position, kind)
            b04, baseline_notification = await pending(
                database, trade, position, AlertType.HEBELTRADER_B04_LOSS
            )
            async with database.session_context() as session:
                already_sent = await notification_for(
                    session, item, destination_key="synthetic-delivered-before-resolution"
                )
                await session.commit()
            store, adapter, delivery = mocked_delivery(database)
            assert (await delivery.deliver(already_sent.id)).status is DeliveryStatus.DELIVERED
            adapter.deliver.reset_mock()
            now = datetime.now(UTC)
            prepared = await store.prepare(
                notification_id=awaiting.id,
                attempt_id=uuid4(),
                now=now,
                stale_before=now - timedelta(minutes=5),
                max_attempts=3,
            )
            assert prepared.attempt is not None and prepared.terminal_result is None

            # The helper must leave rollback/commit under the economic caller's
            # control, including its new terminal delivery-attempt record.
            for commit, expected in ((False, 1), (True, 1), (True, 0)):
                async with database.session_context() as session:
                    await session.scalar(
                        select(TradeModel).where(TradeModel.id == trade).with_for_update()
                    )
                    await SqlAlchemyAlertRepository(session).resolve(item.id, resolved_at=now)
                    assert (
                        await suppress_pending_review_notifications(
                            session,
                            alert_id=item.id,
                            now=now,
                            reason="REVIEW_ALERT_RESOLVED",
                        )
                        == expected
                    )
                    if commit:
                        await session.commit()
                    else:
                        await session.flush()
                        await session.rollback()
                if not commit:
                    async with database.session_context() as session:
                        assert (await session.get(AlertModel, item.id)).status == "OPEN"
                        assert (
                            await session.get(NotificationModel, awaiting.id)
                        ).status == "PENDING"
                        attempts = tuple(
                            await session.scalars(
                                select(NotificationDeliveryAttemptModel).where(
                                    NotificationDeliveryAttemptModel.notification_id == awaiting.id
                                )
                            )
                        )
                        assert len(attempts) == 1 and attempts[0].status == "IN_PROGRESS"

            late_result = DeliveryResult(
                status=DeliveryStatus.FAILED, retryable=True, error_code="SYNTHETIC_TIMEOUT"
            )
            for _ in range(2):
                await store.complete(
                    notification_id=awaiting.id,
                    attempt_id=prepared.attempt.id,
                    result=late_result,
                    completed_at=now + timedelta(seconds=1),
                    max_attempts=3,
                )
            assert (await delivery.deliver(awaiting.id)).error_code == "REVIEW_ALERT_RESOLVED"
            assert (await delivery.deliver(already_sent.id)).status is DeliveryStatus.DELIVERED
            adapter.deliver.assert_not_awaited()
            assert await store.list_pending_notification_ids(limit=100) == (
                baseline_notification.id,
            )
            async with database.session_context() as session:
                assert (await session.get(AlertModel, item.id)).status == "RESOLVED"
                assert (await session.get(AlertModel, b04.id)).status == "OPEN"
                assert (await session.get(NotificationModel, baseline_notification.id)).status == (
                    "PENDING"
                )
                assert (await session.get(NotificationModel, awaiting.id)).status == "FAILED"
                assert (await session.get(NotificationModel, already_sent.id)).status == "DELIVERED"
                attempts = tuple(
                    await session.scalars(
                        select(NotificationDeliveryAttemptModel)
                        .where(NotificationDeliveryAttemptModel.notification_id == awaiting.id)
                        .order_by(NotificationDeliveryAttemptModel.attempt_number)
                    )
                )
                assert len(attempts) == 2
                assert attempts[0].error_code == "SYNTHETIC_TIMEOUT" and attempts[0].retryable
                assert attempts[1].error_code == "REVIEW_ALERT_RESOLVED"
                assert not attempts[1].retryable and attempts[1].provider_message_id is None
                assert (
                    await OperationalWorkspaceReadModel(session)._notification_failure_actions(
                        UUID(WORKSPACE)
                    )
                    == []
                )

    asyncio.run(exercise())
