from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.features.trade_position.domain.enums import (
    TradeManagementEventType,
    TradeOrigin,
)
from app.features.trade_position.domain.management import TradeManagementStateProjector
from app.features.trade_position.domain.models import Trade, TradeManagementEvent
from app.features.trade_position.persistence.models import TradeManagementEventModel
from app.features.trade_position.persistence.repositories import (
    SqlAlchemyTradeManagementEventRepository,
)
from app.features.trade_position.service.application import TradePositionService

NOW = datetime(2026, 8, 17, 8, 0, tzinfo=UTC)


def test_stop_event_requires_positive_numeric_value() -> None:
    with pytest.raises(ValueError, match="positive numeric_value"):
        TradeManagementEvent(
            id=uuid4(),
            trade_id=uuid4(),
            event_type=TradeManagementEventType.STOP_CHANGED,
            effective_at=NOW,
            recorded_at=NOW,
            recorded_by=uuid4(),
            numeric_value=Decimal("0"),
        )


def test_management_note_requires_text() -> None:
    with pytest.raises(ValueError, match="non-empty text_value"):
        TradeManagementEvent(
            id=uuid4(),
            trade_id=uuid4(),
            event_type=TradeManagementEventType.MANAGEMENT_NOTE,
            effective_at=NOW,
            recorded_at=NOW,
            recorded_by=uuid4(),
            text_value=" ",
        )


def test_management_event_cannot_supersede_itself() -> None:
    event_id = uuid4()
    with pytest.raises(ValueError, match="must not supersede itself"):
        TradeManagementEvent(
            id=event_id,
            trade_id=uuid4(),
            event_type=TradeManagementEventType.MANAGEMENT_NOTE,
            effective_at=NOW,
            recorded_at=NOW,
            recorded_by=uuid4(),
            text_value="note",
            supersedes_event_id=event_id,
        )


@pytest.mark.asyncio
async def test_management_event_repository_add_maps_domain() -> None:
    session = Mock()
    session.add = Mock()
    event = TradeManagementEvent(
        id=uuid4(),
        trade_id=uuid4(),
        event_type=TradeManagementEventType.STOP_CHANGED,
        effective_at=NOW,
        recorded_at=NOW,
        recorded_by=uuid4(),
        numeric_value=Decimal("1.25"),
    )
    repo = SqlAlchemyTradeManagementEventRepository(session)

    await repo.add(event)

    model = session.add.call_args.args[0]
    assert isinstance(model, TradeManagementEventModel)
    assert model.event_type == "STOP_CHANGED"
    assert model.numeric_value == Decimal("1.25")


@pytest.mark.asyncio
async def test_record_management_event_persists_user_decision() -> None:
    trade = Trade(
        id=uuid4(),
        workspace_id=uuid4(),
        product_id=uuid4(),
        origin=TradeOrigin.EXTERNAL,
        created_at=NOW,
        created_by=uuid4(),
    )
    uow = SimpleNamespace()
    uow.trades = SimpleNamespace(get=AsyncMock(return_value=trade))
    uow.management_events = SimpleNamespace(add=AsyncMock())
    uow.commit = AsyncMock()
    uow.rollback = AsyncMock()

    async def enter():
        return uow

    async def exit(exc_type, exc, tb):
        if exc_type:
            await uow.rollback()

    uow.__aenter__ = enter
    uow.__aexit__ = exit

    class UowWrapper:
        async def __aenter__(self):
            return uow

        async def __aexit__(self, exc_type, exc, tb):
            if exc_type:
                await uow.rollback()

    service = TradePositionService(
        uow=UowWrapper(),
        workspace_selections=SimpleNamespace(resolve=AsyncMock()),
    )

    event = await service.record_management_event(
        workspace_id=trade.workspace_id,
        trade_id=trade.id,
        event_type=TradeManagementEventType.TARGET_CHANGED,
        effective_at=NOW,
        actor=uuid4(),
        numeric_value=Decimal("2.50"),
    )

    assert event.event_type is TradeManagementEventType.TARGET_CHANGED
    assert event.numeric_value == Decimal("2.50")
    uow.management_events.add.assert_awaited_once_with(event)
    uow.commit.assert_awaited_once()


def test_management_state_projector_applies_latest_effective_values() -> None:
    trade_id = uuid4()
    actor = uuid4()
    events = [
        TradeManagementEvent(
            id=uuid4(),
            trade_id=trade_id,
            event_type=TradeManagementEventType.STOP_CHANGED,
            effective_at=NOW,
            recorded_at=NOW,
            recorded_by=actor,
            numeric_value=Decimal("1.00"),
        ),
        TradeManagementEvent(
            id=uuid4(),
            trade_id=trade_id,
            event_type=TradeManagementEventType.TARGET_CHANGED,
            effective_at=NOW,
            recorded_at=NOW,
            recorded_by=actor,
            numeric_value=Decimal("2.50"),
        ),
        TradeManagementEvent(
            id=uuid4(),
            trade_id=trade_id,
            event_type=TradeManagementEventType.THESIS_UPDATED,
            effective_at=NOW,
            recorded_at=NOW,
            recorded_by=actor,
            text_value="Trend remains intact",
        ),
        TradeManagementEvent(
            id=uuid4(),
            trade_id=trade_id,
            event_type=TradeManagementEventType.MANAGEMENT_NOTE,
            effective_at=NOW,
            recorded_at=NOW,
            recorded_by=actor,
            text_value="Observed intraday volatility",
        ),
    ]

    state = TradeManagementStateProjector.project(
        trade_id=trade_id,
        events=events,
    )

    assert state.stop_price == Decimal("1.00")
    assert state.target_price == Decimal("2.50")
    assert state.thesis == "Trend remains intact"
    assert state.notes == ("Observed intraday volatility",)


def test_management_state_projector_rejects_other_trade_event() -> None:
    with pytest.raises(ValueError, match="does not belong to trade"):
        TradeManagementStateProjector.project(
            trade_id=uuid4(),
            events=[
                TradeManagementEvent(
                    id=uuid4(),
                    trade_id=uuid4(),
                    event_type=TradeManagementEventType.MANAGEMENT_NOTE,
                    effective_at=NOW,
                    recorded_at=NOW,
                    recorded_by=uuid4(),
                    text_value="note",
                )
            ],
        )


@pytest.mark.asyncio
async def test_management_repository_effective_query_excludes_superseded_events() -> None:
    session = Mock()
    session.scalars = AsyncMock()
    result = Mock()
    result.all.return_value = []
    session.scalars.return_value = result
    repo = SqlAlchemyTradeManagementEventRepository(session)

    events = await repo.list_effective_for_trade(uuid4())

    assert events == []
    statement = session.scalars.await_args.args[0]
    sql = str(statement)
    assert "supersedes_event_id" in sql
    assert "NOT (EXISTS" in sql


@pytest.mark.asyncio
async def test_management_commands_use_explicit_event_types() -> None:
    trade = Trade(
        id=uuid4(),
        workspace_id=uuid4(),
        product_id=uuid4(),
        origin=TradeOrigin.EXTERNAL,
        created_at=NOW,
        created_by=uuid4(),
    )
    management_events = SimpleNamespace(
        add=AsyncMock(),
        list_effective_for_trade=AsyncMock(return_value=[]),
    )
    uow = SimpleNamespace(
        trades=SimpleNamespace(get=AsyncMock(return_value=trade)),
        management_events=management_events,
        commit=AsyncMock(),
        rollback=AsyncMock(),
    )

    class UowWrapper:
        async def __aenter__(self):
            return uow

        async def __aexit__(self, exc_type, exc, tb):
            if exc_type:
                await uow.rollback()

    service = TradePositionService(
        uow=UowWrapper(),
        workspace_selections=SimpleNamespace(resolve=AsyncMock()),
    )
    actor = uuid4()

    stop = await service.change_stop(
        workspace_id=trade.workspace_id,
        trade_id=trade.id,
        stop_price=Decimal("1.10"),
        effective_at=NOW,
        actor=actor,
    )
    target = await service.change_target(
        workspace_id=trade.workspace_id,
        trade_id=trade.id,
        target_price=Decimal("2.20"),
        effective_at=NOW,
        actor=actor,
    )
    thesis = await service.update_thesis(
        workspace_id=trade.workspace_id,
        trade_id=trade.id,
        thesis="Momentum improving",
        effective_at=NOW,
        actor=actor,
    )
    note = await service.add_management_note(
        workspace_id=trade.workspace_id,
        trade_id=trade.id,
        note="Manual observation",
        effective_at=NOW,
        actor=actor,
    )

    assert stop.event_type is TradeManagementEventType.STOP_CHANGED
    assert target.event_type is TradeManagementEventType.TARGET_CHANGED
    assert thesis.event_type is TradeManagementEventType.THESIS_UPDATED
    assert note.event_type is TradeManagementEventType.MANAGEMENT_NOTE


@pytest.mark.asyncio
async def test_get_management_state_uses_effective_event_history() -> None:
    trade = Trade(
        id=uuid4(),
        workspace_id=uuid4(),
        product_id=uuid4(),
        origin=TradeOrigin.EXTERNAL,
        created_at=NOW,
        created_by=uuid4(),
    )
    event = TradeManagementEvent(
        id=uuid4(),
        trade_id=trade.id,
        event_type=TradeManagementEventType.STOP_CHANGED,
        effective_at=NOW,
        recorded_at=NOW,
        recorded_by=uuid4(),
        numeric_value=Decimal("1.25"),
    )
    management_events = SimpleNamespace(
        add=AsyncMock(),
        list_effective_for_trade=AsyncMock(return_value=[event]),
    )
    uow = SimpleNamespace(
        trades=SimpleNamespace(get=AsyncMock(return_value=trade)),
        management_events=management_events,
        commit=AsyncMock(),
        rollback=AsyncMock(),
    )

    class UowWrapper:
        async def __aenter__(self):
            return uow

        async def __aexit__(self, exc_type, exc, tb):
            if exc_type:
                await uow.rollback()

    service = TradePositionService(
        uow=UowWrapper(),
        workspace_selections=SimpleNamespace(resolve=AsyncMock()),
    )

    state = await service.get_management_state(
        workspace_id=trade.workspace_id,
        trade_id=trade.id,
    )

    assert state.stop_price == Decimal("1.25")
    management_events.list_effective_for_trade.assert_awaited_once_with(trade.id)
