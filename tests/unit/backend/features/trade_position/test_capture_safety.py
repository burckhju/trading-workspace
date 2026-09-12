from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import ValidationError
from tests.unit.backend.features.trade_position.test_application import (
    FakeUow,
    FakeWorkspaceSelections,
)

from app.core.exceptions.types import ApplicationError
from app.features.trade_position.api.dtos import ExternalPurchaseRequest
from app.features.trade_position.api.router import _capture_time
from app.features.trade_position.domain.enums import ExecutionSide, TradeOrigin
from app.features.trade_position.domain.models import ExecutionRecord, Position, Trade
from app.features.trade_position.domain.projector import PositionProjector
from app.features.trade_position.domain.timeline import ft011_eligibility
from app.features.trade_position.service.application import TradePositionService

AT = datetime(2026, 8, 17, 8, tzinfo=UTC)


def test_calendar_date_is_not_a_recording_timestamp_or_invented_exact_time():
    request = ExternalPurchaseRequest(
        product_id=uuid4(),
        quantity=10,
        price_per_unit="0.55",
        executed_on="2026-08-17",
        execution_timezone="Europe/Berlin",
        request_id=uuid4(),
    )
    resolved = _capture_time(request)
    assert resolved["executed_on"] == date(2026, 8, 17)
    assert resolved["executed_at"] == datetime(2026, 8, 16, 22, tzinfo=UTC)
    assert resolved["execution_timezone"] == "Europe/Berlin"
    assert resolved["request_id"] == request.request_id


@pytest.mark.parametrize(
    "extra",
    [
        {"executed_at": "2026-08-17T08:00:00"},  # naive timestamps rejected
        {"executed_on": "2026-08-17"},
        {"execution_timezone": "Europe/Berlin"},
        {"executed_on": "2026-08-17", "execution_timezone": "fake/zone"},
        {
            "executed_on": "2026-08-17",
            "execution_timezone": "Europe/Berlin",
            "executed_at": "2026-08-17T08:00:00Z",
        },
        {"request_id": str(uuid4())},
    ],
)
def test_capture_requires_unambiguous_time_and_stable_keyed_inputs(extra):
    with pytest.raises(ValidationError):
        ExternalPurchaseRequest(product_id=uuid4(), quantity=10, price_per_unit="1", **extra)


@pytest.mark.parametrize(
    "extra",
    [
        {"executed_on": "2099-01-01", "execution_timezone": "Europe/Berlin"},
        {"executed_at": "2099-01-01T08:00:00Z"},
    ],
)
def test_future_execution_rejected_instead_of_fabricating_recorded_at(extra):
    request = ExternalPurchaseRequest(product_id=uuid4(), quantity=10, price_per_unit="1", **extra)
    with pytest.raises(ValueError, match="Zukunft"):
        _capture_time(request)


@pytest.mark.parametrize("day, expected_hour", [(date(2026, 1, 12), 23), (date(2026, 8, 17), 22)])
def test_calendar_date_zone_survives_dst_offset(day, expected_hour):
    result = _capture_time(
        ExternalPurchaseRequest(
            product_id=uuid4(),
            quantity=1,
            price_per_unit=1,
            executed_on=day,
            execution_timezone="Europe/Berlin",
        )
    )
    assert result["executed_at"].hour == expected_hour
    assert result["executed_on"] == day


def facts():
    trade = Trade(
        id=uuid4(),
        workspace_id=uuid4(),
        product_id=uuid4(),
        origin=TradeOrigin.EXTERNAL,
        created_at=AT,
        created_by=uuid4(),
    )
    record = ExecutionRecord(
        id=uuid4(),
        trade_id=trade.id,
        product_id=trade.product_id,
        quantity=10,
        price_per_unit=Decimal("1"),
        executed_at=AT,
        recorded_at=AT,
        recorded_by=uuid4(),
    )
    return trade, record, Position.from_execution(id=uuid4(), trade=trade, execution=record)


@pytest.mark.asyncio
async def test_same_capture_key_replays_and_changed_payload_conflicts():
    trade, record, position = facts()
    uow = FakeUow()
    uow.executions.find_request = AsyncMock(
        return_value=replace(record, request_key="key", request_fingerprint="fingerprint")
    )
    uow.trades.get.return_value = trade
    uow.positions.get_for_trade.return_value = position
    service = TradePositionService(uow=uow, workspace_selections=FakeWorkspaceSelections())
    replay = await service._replay(trade.workspace_id, "key", "fingerprint")
    assert replay[0] == trade and replay[1].id == record.id
    uow.executions.add.assert_not_awaited()
    with pytest.raises(ApplicationError) as failure:
        await service._replay(trade.workspace_id, "key", "other")
    assert failure.value.code == "CAPTURE_KEY_CONFLICT"
    uow.trades.get.return_value = replace(trade, cancelled_at=AT)
    with pytest.raises(ApplicationError) as failure:
        await service._replay(trade.workspace_id, "key", "fingerprint")
    assert failure.value.code == "TRADE_CANCELLED"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "operation",
    ["record_additional_purchase", "record_sale", "correct_execution", "add_management_note"],
)
async def test_cancelled_trade_cannot_be_mutated(operation):
    trade, record, position = facts()
    uow = FakeUow()
    uow.trades.get.return_value = replace(
        trade, cancelled_at=AT, cancelled_by=trade.created_by, cancellation_reason="duplicate"
    )
    uow.positions.get_for_trade.return_value = position
    service = TradePositionService(uow=uow, workspace_selections=FakeWorkspaceSelections())
    args = dict(workspace_id=trade.workspace_id, trade_id=trade.id, actor=trade.created_by)
    if operation == "add_management_note":
        args.update(note="changed", effective_at=AT)
    else:
        args.update(quantity=1, price_per_unit=Decimal("1"), executed_at=AT)
    if operation == "correct_execution":
        args.update(execution_id=record.id, side=ExecutionSide.BUY)
    with pytest.raises(ApplicationError) as failure:
        await getattr(service, operation)(**args)
    assert failure.value.code == "TRADE_CANCELLED"
    uow.commit.assert_not_awaited()


def test_cancellation_is_not_a_full_exit():
    _, _, position = facts()
    assert not ft011_eligibility(replace(position, is_cancelled=True)).eligible


def test_projection_preserves_calendar_precision_and_corrects_history():
    trade, record, _ = facts()
    bought = replace(
        record,
        executed_at=datetime(2026, 8, 16, 22, tzinfo=UTC),
        executed_on=date(2026, 8, 17),
        execution_timezone="Europe/Berlin",
    )
    sold = replace(
        record,
        id=uuid4(),
        side=ExecutionSide.SELL,
        executed_at=datetime(2026, 8, 17, 22, tzinfo=UTC),
        recorded_at=AT + timedelta(days=2),
        executed_on=date(2026, 8, 18),
        execution_timezone="Europe/Berlin",
    )
    projection = PositionProjector.project(id=uuid4(), trade=trade, executions=[sold, bought])
    assert projection.opened_on == bought.executed_on
    assert projection.closed_on == sold.executed_on
    assert projection.last_execution_on == sold.executed_on
    assert projection.is_closed
    with pytest.raises(ValueError, match="anchor"):
        replace(bought, executed_on=date(2026, 8, 16))


def test_request_identity_is_workspace_scoped_and_includes_date_precision():
    workspace_id, request_id = uuid4(), uuid4()
    identity = TradePositionService._request_identity
    one = identity(workspace_id, request_id, "sale", 10, Decimal("0.55"), AT)
    assert identity(workspace_id, request_id, "sale", 10, Decimal("0.5500"), AT) == one
    assert identity(uuid4(), request_id, "sale", 10, Decimal("0.55"), AT)[0] != one[0]
    assert identity(workspace_id, request_id, "buy", 10, Decimal("0.55"), AT)[1] != one[1]
    assert (
        identity(
            workspace_id, request_id, "sale", 10, Decimal("0.55"), AT, date(2026, 8, 17), "UTC"
        )[1]
        != one[1]
    )


@pytest.mark.asyncio
async def test_request_dependency_closes_lock_holding_session_on_rejected_request():
    from types import SimpleNamespace

    from app.database.dependencies import get_database_session

    closed = False

    async def sessions():
        nonlocal closed
        try:
            yield object()
        finally:
            closed = True

    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                container=SimpleNamespace(database=SimpleNamespace(session=sessions))
            )
        )
    )
    dependency = get_database_session(request)
    await anext(dependency)
    with pytest.raises(ValueError):
        await dependency.athrow(ValueError("rejected"))
    assert closed
