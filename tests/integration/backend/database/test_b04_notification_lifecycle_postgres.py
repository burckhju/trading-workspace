"""Real economic owner writes and B04 dispatch races in a generated disposable DB."""

import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import event, select, update
from sqlalchemy.engine import make_url
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
from app.features.notification.persistence.repositories import (
    SqlAlchemyNotificationRepository,
)
from app.features.notification.service.creation import AlertNotificationService
from app.features.notification.service.durable_delivery import (
    DurableNotificationDeliveryService,
)
from app.features.notification.service.hebeltrader_lifecycle import (
    suppress_pending_b04_notifications,
)
from app.features.operational_workspace.service.read_model import (
    OperationalWorkspaceReadModel,
)
from app.features.trade_position.persistence.models import PositionModel, TradeModel
from app.features.trade_position.persistence.unit_of_work import (
    SqlAlchemyTradePositionUnitOfWork,
)


@pytest.fixture
def b04_notification_database():
    # Requires the exact designated test parent; creates/drops only its own UUID database.
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


async def pending(database, trade_id, position_id):
    now = datetime.now(UTC)
    item = Alert(
        id=uuid4(),
        trade_id=trade_id,
        position_id=position_id,
        alert_type=AlertType.HEBELTRADER_B04_LOSS,
        severity=AlertSeverity.WARNING,
        rule_key=f"synthetic-b04:{uuid4()}",
        reason="Synthetic B04 loss, no original provider qualification asserted.",
        observed_value=Decimal("0.48"),
        threshold_value=Decimal("0.55"),
        market_data_observed_at=now,
        detected_at=now,
        price_context={
            "basis": "WARRANT",
            "rule_version": "hebeltrader-b04-b57-v1",
            "remaining_quantity": "10",
            "completed_sessions_at_bid": "20",
            "currency": "EUR",
            "provider": "SYNTHETIC",
            "observed_at": now.isoformat(),
        },
    )
    async with database.session_context() as session:
        await SqlAlchemyAlertRepository(session).add(item)
        await session.flush()
        notification = await AlertNotificationService(
            notifications=SqlAlchemyNotificationRepository(session),
            new_id=uuid4,
            now=lambda: now,
        ).create_telegram(alert=item, symbol="SYNTHETIC-NO-PROVIDER")
        await session.commit()
    return item, notification


def test_partial_sale_then_concurrent_full_sale_suppresses_pending_before_mock_dispatch(
    b04_notification_database, monkeypatch
):
    _migrate(b04_notification_database, "head")

    async def exercise():
        assert make_url(b04_notification_database).database.startswith("tw_currency_ref_test_")
        async with _client(b04_notification_database) as (client, database):
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
                partial_position = await session.get(PositionModel, position)
                assert partial_position is not None
                partial_projection = {
                    column.name: getattr(partial_position, column.name)
                    for column in PositionModel.__table__.columns
                    if column.name not in {"id", "trade_id", "product_id"}
                }
            _, already_sent = await pending(database, trade, position)
            adapter = SimpleNamespace(
                deliver=AsyncMock(
                    return_value=DeliveryResult(
                        status=DeliveryStatus.DELIVERED,
                        retryable=False,
                        provider_message_id="synthetic-mock-only",
                    )
                )
            )
            store = SqlAlchemyDurableNotificationDeliveryStore(database)
            delivery = DurableNotificationDeliveryService(
                store=store,
                adapter=adapter,
                new_id=uuid4,
                now=lambda: datetime.now(UTC),
            )
            assert (await delivery.deliver(already_sent.id)).status is DeliveryStatus.DELIVERED
            adapter.deliver.assert_awaited_once()
            adapter.deliver.reset_mock()

            _, awaiting = await pending(database, trade, position)
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
                closed = await asyncio.wait_for(sale_task, timeout=10)
                result = await asyncio.wait_for(dispatch_task, timeout=10)
                event.remove(database.engine.sync_engine, "before_cursor_execute", before_execute)
            assert closed.status_code == 201, closed.text
            assert closed.json()["position"]["open_quantity"] == 0
            assert result.error_code == "B04_POSITION_CLOSED" and not result.retryable
            adapter.deliver.assert_not_awaited()

            # Reuse the consistent earlier owner projection, including its cost
            # basis and date fields; it still cannot override the effective sale.
            async with database.session_context() as session:
                await session.execute(
                    update(PositionModel)
                    .where(PositionModel.id == position)
                    .values(**partial_projection)
                )
                await session.commit()
            _, stale_projection = await pending(database, trade, position)
            assert (await delivery.deliver(stale_projection.id)).error_code == "B04_POSITION_CLOSED"
            assert (await delivery.deliver(awaiting.id)).error_code == "B04_POSITION_CLOSED"
            assert (await delivery.deliver(already_sent.id)).status is DeliveryStatus.DELIVERED
            adapter.deliver.assert_not_awaited()
            assert await store.list_pending_notification_ids(limit=100) == ()

            async with database.session_context() as session:
                rows = tuple(await session.scalars(select(NotificationModel)))
                assert {row.id: row.status for row in rows} == {
                    already_sent.id: "DELIVERED",
                    awaiting.id: "FAILED",
                    stale_projection.id: "FAILED",
                }
                attempts = tuple(await session.scalars(select(NotificationDeliveryAttemptModel)))
                assert len(attempts) == 3
                assert len([a for a in attempts if a.error_code == "B04_POSITION_CLOSED"]) == 2
                assert len(tuple(await session.scalars(select(AlertModel)))) == 3
                assert (
                    await OperationalWorkspaceReadModel(session)._notification_failure_actions(
                        UUID(WORKSPACE)
                    )
                    == []
                )

    asyncio.run(exercise())


def test_lifecycle_resolution_is_atomic_replayable_and_keeps_delivered_history(
    b04_notification_database,
):
    _migrate(b04_notification_database, "head")

    async def exercise():
        async with _client(b04_notification_database) as (client, database):
            warrant = await product(client)
            bought = await client.post(BASE + "/purchases/external", json=purchase(warrant))
            assert bought.status_code == 201, bought.text
            trade = UUID(bought.json()["trade"]["id"])
            position = UUID(bought.json()["position"]["id"])
            item, notification = await pending(database, trade, position)
            for expected in (1, 0):
                async with database.session_context() as session:
                    await session.scalar(
                        select(TradeModel).where(TradeModel.id == trade).with_for_update()
                    )
                    await SqlAlchemyAlertRepository(session).resolve(
                        item.id, resolved_at=datetime.now(UTC)
                    )
                    changed = await suppress_pending_b04_notifications(
                        session,
                        alert_id=item.id,
                        now=datetime.now(UTC),
                        reason="B04_ALERT_RESOLVED",
                    )
                    assert changed == expected
                    await session.commit()
            async with database.session_context() as session:
                current = await session.get(NotificationModel, notification.id)
                assert current.status == "FAILED"
                attempts = tuple(await session.scalars(select(NotificationDeliveryAttemptModel)))
                assert len(attempts) == 1
                assert attempts[0].error_code == "B04_ALERT_RESOLVED"
                assert not attempts[0].retryable and attempts[0].provider_message_id is None
                assert (await session.get(AlertModel, item.id)).status == "RESOLVED"
                assert (
                    await OperationalWorkspaceReadModel(session)._notification_failure_actions(
                        UUID(WORKSPACE)
                    )
                    == []
                )

    asyncio.run(exercise())
