"""Actual keyset SQL and intercepted delivery in disposable in-memory SQLite."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session
from tests.unit.backend.features.market_data.test_retained_quotes import SqlDatabase

from app.features.notification.domain.models import (
    DeliveryAttempt,
    DeliveryPreparation,
    DeliveryResult,
    DeliveryStatus,
    Notification,
    NotificationChannel,
)
from app.features.notification.persistence.durable_delivery import (
    SqlAlchemyDurableNotificationDeliveryStore,
)
from app.features.notification.service.durable_delivery import DurableNotificationDeliveryService
from app.features.position_monitoring.domain.product_deadline_review import RULE_SCOPE

NOW = datetime(2026, 11, 18, 16, tzinfo=UTC)


@pytest.fixture
def context(monkeypatch):
    database = SqlDatabase("sqlite:///:memory:")
    metadata = sa.MetaData()
    trades = sa.Table(
        "trades",
        metadata,
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True)),
    )
    alerts = sa.Table(
        "alerts",
        metadata,
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("trade_id", sa.Uuid()),
        sa.Column("alert_type", sa.String()),
        sa.Column("status", sa.String()),
        sa.Column("price_context", sa.JSON()),
    )
    notifications = sa.Table(
        "notifications",
        metadata,
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("alert_id", sa.Uuid()),
        sa.Column("status", sa.String()),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
    metadata.create_all(database.engine)
    store = SqlAlchemyDurableNotificationDeliveryStore(
        database, review_delivery_enabled=True, deadline_delivery_enabled=True
    )
    state = SimpleNamespace(
        database=database,
        store=store,
        now=NOW,
        paused=set(),
        closed=set(),
        visited=[],
        prepared=[],
        sent=[],
        completed=[],
        pages=[],
        after_first_prepare=None,
        delivery_result=DeliveryResult(status=DeliveryStatus.DELIVERED, retryable=False),
    )

    def add(index, *, kind="STOP_REACHED", created_at=NOW - timedelta(minutes=1)):
        identifier = UUID(int=index)
        with Session(database.engine) as session:
            session.execute(trades.insert().values(id=identifier))
            session.execute(
                alerts.insert().values(
                    id=identifier,
                    trade_id=identifier,
                    alert_type=kind,
                    status="OPEN",
                    price_context=(
                        {"scope": RULE_SCOPE} if kind == "PRODUCT_DEADLINE_REVIEW" else {}
                    ),
                )
            )
            session.execute(
                notifications.insert().values(
                    id=identifier,
                    alert_id=identifier,
                    created_at=created_at,
                    status="PENDING",
                )
            )
            session.commit()
        return identifier

    def set_status(identifier, status):
        with Session(database.engine) as session:
            session.execute(
                notifications.update().where(notifications.c.id == identifier).values(status=status)
            )
            session.commit()

    def statuses():
        with Session(database.engine) as session:
            return dict(
                session.execute(sa.select(notifications.c.id, notifications.c.status)).all()
            )

    async def prepare(**kwargs):
        identifier = kwargs["notification_id"]
        state.visited.append(identifier)
        if len(state.visited) == 1 and state.after_first_prepare is not None:
            state.after_first_prepare()
        notification = Notification(
            id=identifier,
            alert_id=identifier,
            channel=NotificationChannel.TELEGRAM,
            destination_key="synthetic-intercepted",
            body=str(identifier),
            created_at=NOW - timedelta(minutes=1),
        )
        if identifier in state.paused or identifier in state.closed:
            closed = identifier in state.closed
            if closed:
                set_status(identifier, "FAILED")
            return DeliveryPreparation(
                notification=notification,
                terminal_result=DeliveryResult(
                    status=DeliveryStatus.FAILED,
                    retryable=not closed,
                    error_code=(
                        "REVIEW_POSITION_CLOSED" if closed else "REVIEW_DEADLINE_INPUTS_UNAVAILABLE"
                    ),
                ),
            )
        if statuses()[identifier] == "DELIVERED":
            return DeliveryPreparation(
                notification=notification,
                terminal_result=DeliveryResult(status=DeliveryStatus.DELIVERED, retryable=False),
            )
        state.prepared.append(identifier)
        return DeliveryPreparation(
            notification=notification,
            attempt=DeliveryAttempt(
                id=kwargs["attempt_id"],
                notification_id=identifier,
                attempt_number=1,
                status=DeliveryStatus.IN_PROGRESS,
                attempted_at=kwargs["now"],
                completed_at=None,
                retryable=True,
            ),
        )

    async def complete(**kwargs):
        state.completed.append(kwargs["notification_id"])
        set_status(
            kwargs["notification_id"],
            "DELIVERED" if kwargs["result"].status is DeliveryStatus.DELIVERED else "PENDING",
        )

    async def send(*, body):
        identifier = UUID(body)
        assert identifier in state.prepared
        state.sent.append(identifier)
        return state.delivery_result

    read_page = store.list_pending_notification_page

    async def page(**kwargs):
        state.pages.append(kwargs)
        return await read_page(**kwargs)

    monkeypatch.setattr(store, "prepare", prepare)
    monkeypatch.setattr(store, "complete", complete)
    monkeypatch.setattr(store, "list_pending_notification_page", page)
    state.add, state.statuses, state.set_status = add, statuses, set_status
    state.adapter = SimpleNamespace(deliver=AsyncMock(side_effect=send))
    state.service = DurableNotificationDeliveryService(
        store=store, adapter=state.adapter, new_id=uuid4, now=lambda: state.now
    )
    try:
        yield state
    finally:
        database.engine.dispose()


async def test_more_than_one_hundred_pauses_do_not_hide_later_send_or_take_send_budget(context):
    for index in range(1, 106):
        context.paused.add(context.add(index, kind="PRODUCT_DEADLINE_REVIEW"))
    normal = context.add(200)

    results = await context.service.deliver_pending(limit=1)

    assert len(results) == 106
    assert context.sent == context.prepared == context.completed == [normal]
    assert len(context.pages) == 2
    assert context.pages[0]["after"] is None
    assert context.pages[1]["after"] == (NOW - timedelta(minutes=1), UUID(int=100))
    assert context.visited == [UUID(int=index) for index in range(1, 106)] + [normal]
    assert all(context.statuses()[identifier] == "PENDING" for identifier in context.paused)
    assert context.statuses()[normal] == "DELIVERED"


async def test_fixed_cutoff_defers_simultaneous_and_later_insertions_until_next_cycle(context):
    for index in range(1, 101):
        context.paused.add(context.add(index, kind="PRODUCT_DEADLINE_REVIEW"))
    existing = context.add(200)

    def concurrent_insert():
        context.add(201, created_at=NOW)
        context.add(202, created_at=NOW + timedelta(microseconds=1))
        context.now += timedelta(seconds=1)

    context.after_first_prepare = concurrent_insert
    await context.service.deliver_pending(limit=5)
    assert context.sent == [existing]
    assert all(page["created_before"] == NOW for page in context.pages)
    assert context.statuses()[UUID(int=201)] == context.statuses()[UUID(int=202)] == "PENDING"

    await context.service.deliver_pending(limit=5)
    assert context.sent == [existing, UUID(int=201), UUID(int=202)]
    assert len(context.sent) == len(set(context.sent))


async def test_equal_clock_keyset_does_not_skip_after_terminal_rows_disappear(context):
    for index in range(1, 101):
        context.closed.add(context.add(index, kind="PRODUCT_DEADLINE_REVIEW"))
    ordinary = [context.add(index) for index in (101, 102, 103)]

    await context.service.deliver_pending(limit=2)
    assert context.sent == ordinary[:2]
    assert len(context.visited) == 102 and len(set(context.visited)) == 102
    assert context.statuses()[ordinary[-1]] == "PENDING"
    await context.service.deliver_pending(limit=2)
    assert context.sent == ordinary
    assert context.statuses()[ordinary[-1]] == "DELIVERED"


async def test_other_worker_completion_consumes_no_send_budget_and_does_not_duplicate(context):
    already_delivered, pending = context.add(1), context.add(2)
    context.after_first_prepare = lambda: context.set_status(already_delivered, "DELIVERED")
    await context.service.deliver_pending(limit=1)
    assert context.visited == [already_delivered, pending]
    assert context.sent == context.completed == [pending]


async def test_actual_retryable_send_consumes_budget_and_is_not_retried_in_same_cycle(context):
    first, second = context.add(1), context.add(2)
    context.delivery_result = DeliveryResult(
        status=DeliveryStatus.FAILED, retryable=True, error_code="SYNTHETIC_TRANSPORT_FAILURE"
    )
    await context.service.deliver_pending(limit=1)
    assert context.sent == [first]
    assert context.statuses()[first] == context.statuses()[second] == "PENDING"
    context.sent.clear()
    await context.service.deliver_pending(limit=2)
    assert context.sent == [first, second]


async def test_paged_reader_preserves_existing_scope_gates_and_legacy_reader(context):
    ordinary = context.add(1)
    context.add(2, kind="PRODUCT_DEADLINE_REVIEW")
    context.store._deadline_delivery_enabled = False
    assert await context.store.list_pending_notification_ids(limit=10) == (ordinary,)
    assert await context.store.list_pending_notification_page(limit=10, created_before=NOW) == (
        (NOW - timedelta(minutes=1), ordinary),
    )


@pytest.mark.parametrize("limit,cutoff", [(0, NOW), (1, NOW.replace(tzinfo=None))])
async def test_paged_reader_refuses_invalid_bounds(context, limit, cutoff):
    with pytest.raises(ValueError, match="positive limit and aware cutoff"):
        await context.store.list_pending_notification_page(limit=limit, created_before=cutoff)


async def test_invalid_cycle_clock_never_prepares_or_dispatches(context):
    context.add(1)
    context.now = NOW.replace(tzinfo=None)
    with pytest.raises(ValueError, match="aware cutoff"):
        await context.service.deliver_pending()
    assert context.visited == context.sent == context.pages == []
