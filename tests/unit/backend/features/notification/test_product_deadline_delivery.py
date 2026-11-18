"""Synthetic deadline outbox qualification; no real database or external send."""

from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import httpx
import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool
from tests.unit.backend.features.market_data.test_retained_quotes import SqlDatabase
from tests.unit.backend.features.notification.test_hebeltrader_b04 import (
    NOW,
    executions,
    store_fixture,
)
from tests.unit.backend.features.position_monitoring.test_product_deadline_review_contract import (
    decision,
    inputs,
)

from app.features.alert.domain.models import AlertType
from app.features.notification.domain.models import DeliveryResult, DeliveryStatus
from app.features.notification.persistence.durable_delivery import (
    SqlAlchemyDurableNotificationDeliveryStore,
)
from app.features.notification.service.hebeltrader_lifecycle import REVIEW_SUPPRESSION_CODES
from app.features.position_monitoring.domain.product_deadline_review import RULE_SCOPE, RULE_VERSION
from app.features.position_monitoring.service import hebeltrader_loss as snapshot_owner
from app.features.position_monitoring.service import product_deadline_review_delivery as recheck
from app.features.position_monitoring.service.product_deadline_review import (
    product_deadline_context,
)
from app.features.trade_position.persistence.repositories import SqlAlchemyExecutionRecordRepository


@pytest.fixture(autouse=True)
def no_external_http(monkeypatch):
    asynchronous = AsyncMock(
        side_effect=AssertionError("External HTTP forbidden in synthetic test")
    )
    synchronous = Mock(side_effect=AssertionError("External HTTP forbidden in synthetic test"))
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", asynchronous)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", synchronous)
    yield
    asynchronous.assert_not_awaited()
    synchronous.assert_not_called()


def deadline_fixture(kind=AlertType.PRODUCT_DEADLINE_REVIEW, **options):
    fixture = store_fixture(**options)
    fixture.alert.alert_type = kind.value
    fixture.alert.price_context = {
        "scope": RULE_SCOPE,
        "rule_version": RULE_VERSION,
        "episode_kind": (
            "DATA_UNAVAILABLE" if kind is AlertType.POSITION_DATA_UNAVAILABLE else "DEADLINE_REVIEW"
        ),
    }
    return fixture


def prepare_values(fixture, *additional):
    fixture.session.scalar.side_effect = [
        fixture.trade.id,
        fixture.trade,
        fixture.notification,
        fixture.alert,
        *additional,
    ]


def open_owner(monkeypatch, fixture):
    owner = AsyncMock(return_value=executions(fixture.trade, sold=5))
    monkeypatch.setattr(SqlAlchemyExecutionRecordRepository, "list_effective_for_trade", owner)
    return owner


@pytest.mark.parametrize(
    "kind", [AlertType.PRODUCT_DEADLINE_REVIEW, AlertType.POSITION_DATA_UNAVAILABLE]
)
@pytest.mark.parametrize("review,deadline", [(True, False), (False, True), (False, False)])
async def test_scope_pause_never_checks_sources_or_creates_an_attempt(
    monkeypatch, kind, review, deadline
):
    fixture = deadline_fixture(kind)
    fixture.store._review_delivery_enabled = review
    fixture.store._deadline_delivery_enabled = deadline
    open_owner(monkeypatch, fixture)
    verify = AsyncMock(side_effect=AssertionError("A paused scope must not acquire sources"))
    monkeypatch.setattr(recheck, "deadline_review_delivery_problem", verify)
    prepare_values(fixture)
    result = await fixture.delivery.deliver(fixture.notification.id)
    assert result.error_code == "REVIEW_DELIVERY_DISABLED" and result.retryable
    assert fixture.notification.status == "PENDING"
    fixture.session.add.assert_not_called()
    fixture.session.commit.assert_not_awaited()
    fixture.adapter.deliver.assert_not_awaited()
    verify.assert_not_awaited()


@pytest.mark.parametrize(
    "kind", [AlertType.PRODUCT_DEADLINE_REVIEW, AlertType.POSITION_DATA_UNAVAILABLE]
)
async def test_full_sale_remains_terminal_under_v1_even_for_old_v2_data_notices(monkeypatch, kind):
    fixture = deadline_fixture(kind)
    assert fixture.store._review_delivery_enabled is True
    assert fixture.store._deadline_delivery_enabled is False
    owner = AsyncMock(return_value=executions(fixture.trade))
    monkeypatch.setattr(SqlAlchemyExecutionRecordRepository, "list_effective_for_trade", owner)
    verify = AsyncMock(side_effect=AssertionError("A full sale needs no source lookup"))
    monkeypatch.setattr(recheck, "deadline_review_delivery_problem", verify)
    prepare_values(fixture, None)
    result = await fixture.delivery.deliver(fixture.notification.id)
    assert result.error_code == "REVIEW_POSITION_CLOSED" and not result.retryable
    assert fixture.notification.status == "FAILED"
    attempt = fixture.session.add.call_args.args[0]
    assert attempt.attempt_number == 1 and attempt.provider_message_id is None
    assert attempt.status == "FAILED"
    fixture.adapter.deliver.assert_not_awaited()
    verify.assert_not_awaited()


async def test_temporary_source_gap_pauses_then_resumes_the_same_pending_outbox(monkeypatch):
    fixture = deadline_fixture()
    fixture.store._deadline_delivery_enabled = True
    open_owner(monkeypatch, fixture)
    checks = []

    async def check(session, **kwargs):
        assert session is fixture.session
        assert kwargs["trade_id"] == fixture.trade.id
        assert kwargs["known_at"] == NOW
        statements = [str(call.args[0]) for call in session.scalar.call_args_list]
        assert any("trades" in statement and "FOR UPDATE" in statement for statement in statements)
        assert any(
            "notifications" in statement and "FOR UPDATE" in statement for statement in statements
        )
        fixture.adapter.deliver.assert_not_awaited()
        checks.append(kwargs)
        return "REVIEW_DEADLINE_INPUTS_UNAVAILABLE" if len(checks) == 1 else None

    monkeypatch.setattr(recheck, "deadline_review_delivery_problem", check)
    prepare_values(fixture)
    paused = await fixture.delivery.deliver(fixture.notification.id)
    assert paused.error_code == "REVIEW_DEADLINE_INPUTS_UNAVAILABLE" and paused.retryable
    assert "REVIEW_DEADLINE_INPUTS_UNAVAILABLE" not in REVIEW_SUPPRESSION_CODES
    assert fixture.notification.status == "PENDING"
    fixture.session.add.assert_not_called()
    fixture.session.commit.assert_not_awaited()
    fixture.adapter.deliver.assert_not_awaited()

    async def external_boundary(*, body):
        assert body == fixture.notification.body
        fixture.session.commit.assert_awaited_once()
        attempt = fixture.session.add.call_args.args[0]
        assert attempt.notification_id == fixture.notification.id
        assert attempt.status == "IN_PROGRESS" and attempt.attempt_number == 1
        return DeliveryResult(status=DeliveryStatus.DELIVERED, retryable=False)

    fixture.adapter.deliver.side_effect = external_boundary
    complete = AsyncMock()
    monkeypatch.setattr(fixture.store, "complete", complete)
    prepare_values(fixture, None, None)
    delivered = await fixture.delivery.deliver(fixture.notification.id)
    assert delivered.status is DeliveryStatus.DELIVERED
    assert len(checks) == 2
    fixture.session.add.assert_called_once()
    fixture.adapter.deliver.assert_awaited_once()
    assert complete.await_args.kwargs["notification_id"] == fixture.notification.id


@pytest.mark.parametrize("reason", ["REVIEW_ALERT_RESOLVED", "REVIEW_ALERT_INVALIDATED"])
async def test_real_event_or_version_change_remains_a_terminal_suppression(monkeypatch, reason):
    fixture = deadline_fixture()
    fixture.store._deadline_delivery_enabled = True
    open_owner(monkeypatch, fixture)
    monkeypatch.setattr(recheck, "deadline_review_delivery_problem", AsyncMock(return_value=reason))
    prepare_values(fixture, 2)
    result = await fixture.delivery.deliver(fixture.notification.id)
    assert result.error_code == reason and not result.retryable
    assert fixture.notification.status == "FAILED"
    assert fixture.session.add.call_args.args[0].attempt_number == 3
    fixture.adapter.deliver.assert_not_awaited()


async def test_unreadable_owner_snapshot_leaves_outbox_pending_without_guessing(monkeypatch):
    fixture = deadline_fixture()
    fixture.store._deadline_delivery_enabled = True
    open_owner(monkeypatch, fixture)
    monkeypatch.setattr(
        recheck,
        "deadline_review_delivery_problem",
        AsyncMock(side_effect=RuntimeError("Synthetic snapshot unavailable")),
    )
    prepare_values(fixture)
    with pytest.raises(RuntimeError, match="Synthetic snapshot unavailable"):
        await fixture.delivery.deliver(fixture.notification.id)
    assert fixture.notification.status == "PENDING"
    fixture.session.add.assert_not_called()
    fixture.adapter.deliver.assert_not_awaited()


@pytest.mark.parametrize(
    "review,deadline", [(True, False), (False, False), (False, True), (True, True)]
)
async def test_pending_sql_filters_both_deadline_types_without_starving_other_rules(
    tmp_path, review, deadline
):
    database = SqlDatabase(f"sqlite:///{tmp_path}/synthetic_deadline_pending_filter.db")
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
    candidates = (
        ("STOP_REACHED", None),
        ("INDICATIVE_ENTRY_LOSS", {"scope": "INDICATIVE_ENTRY_V2"}),
        ("PRODUCT_DEADLINE_REVIEW", {"scope": RULE_SCOPE}),
        ("POSITION_DATA_UNAVAILABLE", {"scope": RULE_SCOPE}),
        ("POSITION_DATA_UNAVAILABLE", {"scope": "INDICATIVE_ENTRY_V2"}),
        ("PRODUCT_DEADLINE_REVIEW", None),
        ("POSITION_REVIEW_DUE", {}),
    )
    try:
        with Session(database.engine) as session:
            for index, (kind, context) in enumerate(candidates, start=1):
                identifier = UUID(int=index)
                session.execute(trades.insert().values(id=identifier))
                session.execute(
                    alerts.insert().values(
                        id=identifier,
                        trade_id=identifier,
                        alert_type=kind,
                        status="OPEN",
                        price_context=context,
                    )
                )
                session.execute(
                    notifications.insert().values(
                        id=identifier,
                        alert_id=identifier,
                        status="PENDING",
                        created_at=NOW,
                    )
                )
            session.commit()
        store = SqlAlchemyDurableNotificationDeliveryStore(
            database, review_delivery_enabled=review, deadline_delivery_enabled=deadline
        )
        expected = [1]
        if review:
            expected.extend([2, 5, 7])
            if deadline:
                expected.extend([3, 4, 6])
        assert await store.list_pending_notification_ids(limit=20) == tuple(
            UUID(int=index) for index in sorted(expected)
        )
    finally:
        database.engine.dispose()


async def test_deadline_snapshot_uses_separate_read_only_connection_not_last_pool_slot(monkeypatch):
    value = inputs()
    context = product_deadline_context(
        value, decision(value), "DEADLINE_REVIEW", uuid4(), uuid4(), NOW
    )
    # Engine construction does not connect. All session/connection boundaries
    # below are intercepted; no PostgreSQL server is contacted by this test.
    engine = create_async_engine(
        "postgresql+asyncpg://unused.invalid/synthetic_deadline_pool_one",
        pool_size=1,
        max_overflow=0,
    )
    independent = SimpleNamespace(dispose=AsyncMock())
    factory = Mock(return_value=independent)
    snapshot = SimpleNamespace(execute=AsyncMock(), rollback=AsyncMock())

    @asynccontextmanager
    async def session_factory(selected_engine, **options):
        assert selected_engine is independent
        assert options == {"expire_on_commit": False, "autoflush": False}
        yield snapshot

    monkeypatch.setattr(snapshot_owner, "create_async_engine", factory)
    monkeypatch.setattr(snapshot_owner, "AsyncSession", session_factory)
    reader = AsyncMock(return_value=value)
    monkeypatch.setattr(recheck, "read_product_deadline_inputs", reader)
    try:
        assert (
            await recheck.deadline_review_delivery_problem(
                SimpleNamespace(bind=engine),
                workspace_id=value.workspace_id,
                trade_id=value.trade_id,
                position_id=value.position_id,
                price_context=context,
                known_at=NOW,
            )
            is None
        )
        factory.assert_called_once_with(engine.url, poolclass=NullPool)
        assert "REPEATABLE READ READ ONLY" in str(snapshot.execute.await_args_list[0].args[0])
        reader.assert_awaited_once_with(
            snapshot,
            workspace_id=value.workspace_id,
            trade_id=value.trade_id,
            position_id=value.position_id,
            now=NOW,
        )
        snapshot.rollback.assert_awaited_once()
        independent.dispose.assert_awaited_once()
    finally:
        await engine.dispose()
