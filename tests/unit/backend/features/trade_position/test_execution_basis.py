"""Owner-owned remaining BUY weights and immutable execution/currency evidence."""

from dataclasses import FrozenInstanceError, replace
from datetime import timedelta
from decimal import Decimal, localcontext
from unittest.mock import patch
from uuid import UUID

import pytest
from tests.unit.backend.features.trade_position.currency_evidence_fixtures import historical
from tests.unit.backend.features.trade_position.test_historical_position_valuation_basis import (
    POSITION,
    owner_snapshot,
)
from tests.unit.backend.features.trade_position.test_projector_trace import (
    _execution,
    _trade,
)

from app.features.trade_position.domain.enums import ExecutionSide
from app.features.trade_position.domain.projector import PositionProjector
from app.features.trade_position.service import valuation_basis as module


def history():
    trade = _trade()
    rows = (
        (10, ExecutionSide.BUY, 100, "2", "2026-08-01"),
        (11, ExecutionSide.SELL, 40, "3", "2026-08-02"),
        (12, ExecutionSide.BUY, 20, "4", "2026-08-03"),
    )
    return trade, [
        _execution(trade, number=number, side=side, quantity=quantity, price=price, day=day)
        for number, side, quantity, price, day in rows
    ]


def test_remaining_weights_follow_partial_sale_and_rebuy_without_altering_costs():
    trade, facts = history()
    trace = PositionProjector.project_with_trace(id=POSITION, trade=trade, executions=facts)
    assert trace.position == PositionProjector.project(id=POSITION, trade=trade, executions=facts)
    assert trace.position.open_quantity == 80
    assert trace.position.cost_basis == Decimal("200")
    assert trace.position.average_entry_price == Decimal("2.5")
    assert trace.position.opened_at == facts[0].executed_at
    assert [item.execution_id for item in trace.buy_contributions] == [
        facts[0].id,
        facts[2].id,
    ]
    assert [item.original_quantity for item in trace.buy_contributions] == [100, 20]
    assert [item.remaining_quantity for item in trace.buy_contributions] == [
        Decimal("60"),
        Decimal("20"),
    ]
    with pytest.raises(FrozenInstanceError):
        trace.buy_contributions[0].remaining_quantity = Decimal("100")


def test_multiple_fills_retain_each_contribution_and_full_close_zeroes_weights():
    trade, facts = history()
    first = replace(facts[0], quantity=30)
    second = replace(first, id=UUID(int=13), quantity=70, price_per_unit=Decimal("3"))
    # Recording order is only the owner's ordering, never evidence of order membership.
    second = replace(second, recorded_at=first.recorded_at + timedelta(seconds=1))
    effective = [first, second, *facts[1:]]
    trace = PositionProjector.project_with_trace(id=POSITION, trade=trade, executions=effective)
    assert trace.position.cost_basis == Decimal("242")
    assert trace.position.average_entry_price == Decimal("3.025")
    assert [item.remaining_quantity for item in trace.buy_contributions] == [
        Decimal("18"),
        Decimal("42"),
        Decimal("20"),
    ]
    closed = _execution(
        trade,
        number=14,
        side=ExecutionSide.SELL,
        quantity=80,
        price="5",
        day="2026-08-04",
    )
    after = PositionProjector.project_with_trace(
        id=POSITION, trade=trade, executions=[*effective, closed]
    )
    assert after.position.is_closed
    assert after.position.cost_basis == 0
    assert all(item.remaining_quantity == 0 for item in after.buy_contributions)
    assert [item.original_quantity for item in after.buy_contributions] == [30, 70, 20]
    assert trace.buy_contributions[0].remaining_quantity == Decimal("18")


def test_fractional_remaining_weights_do_not_round_at_each_sale():
    trade, facts = history()
    one = replace(facts[0], quantity=1)
    two = replace(one, id=UUID(int=13), quantity=2)
    two = replace(two, recorded_at=one.recorded_at + timedelta(seconds=1))
    sale = replace(facts[1], quantity=1)
    later_sale = replace(sale, id=UUID(int=14), executed_at=facts[2].executed_at)
    with localcontext() as context:
        context.prec = 28
        trace = PositionProjector.project_with_trace(
            id=POSITION, trade=trade, executions=[one, two, sale, later_sale]
        )
    assert trace.position.open_quantity == 1
    assert [item.remaining_quantity for item in trace.buy_contributions] == [
        Decimal("0.3333333333333333333333333333"),
        Decimal("0.6666666666666666666666666667"),
    ]


@pytest.mark.asyncio
async def test_execution_basis_keeps_correction_history_and_uses_one_projection(
    monkeypatch,
):
    trade, facts = history()
    original = facts[0]
    replacement = replace(
        original,
        id=UUID(int=14),
        quantity=120,
        recorded_at=original.recorded_at + timedelta(days=1),
        supersedes_execution_id=original.id,
    )
    session, records, _, _ = owner_snapshot(monkeypatch, [*facts, replacement])
    with patch.object(
        PositionProjector,
        "project_with_trace",
        wraps=PositionProjector.project_with_trace,
    ) as projector:
        basis = await module.read_position_execution_basis(
            session, trade=trade, position_id=POSITION
        )
    projector.assert_called_once()
    assert [fact.id for fact in basis.effective_executions] == [
        replacement.id,
        facts[1].id,
        facts[2].id,
    ]
    assert len(basis.history) == 4
    saved_original = next(fact for fact in basis.history if fact.id == original.id)
    assert saved_original.quantity == 100
    assert saved_original.recorded_at == original.recorded_at
    assert basis.effective_executions[0].supersedes_execution_id == original.id
    assert [item.remaining_quantity for item in basis.buy_contributions] == [
        Decimal("80"),
        Decimal("20"),
    ]
    assert basis.valuation_basis.position.open_quantity == 100
    assert basis.valuation_basis.position.cost_basis == Decimal("240")
    assert basis.valuation_basis.position.average_entry_price == Decimal("2.4")
    assert basis.valuation_basis.effective_execution_ids == tuple(
        fact.id for fact in basis.effective_executions
    )
    assert basis.valuation_basis.currency_status == "UNKNOWN"
    records.list_for_trade.assert_awaited_once_with(trade.id)
    records.list_effective_for_trade.assert_awaited_once_with(trade.id)


@pytest.mark.asyncio
async def test_existing_valuation_shape_and_basis_id_are_preserved(monkeypatch):
    trade, facts = history()
    session, *_ = owner_snapshot(monkeypatch, facts)
    execution_basis = await module.read_position_execution_basis(
        session, trade=trade, position_id=POSITION
    )
    valuation = await module.read_position_valuation_basis(
        session, trade=trade, position_id=POSITION
    )
    assert valuation == execution_basis.valuation_basis
    # Golden value from the unchanged Main owner at b84544ed. New provenance
    # output is additive and must not reidentify an unchanged monetary basis.
    assert valuation.basis_id == "ee057d16003e024d34b79a53c25820dacaf805e601f1e42a615cee90539e72ae"
    assert not hasattr(valuation, "history")
    assert not hasattr(valuation, "buy_contributions")


@pytest.mark.asyncio
async def test_execution_basis_reuses_historical_currency_without_new_confirmations(monkeypatch):
    trade, facts = history()
    source = historical(trade)
    session, *_ = owner_snapshot(monkeypatch, facts, sources=(source,))
    basis = await module.read_position_execution_basis(session, trade=trade, position_id=POSITION)
    assert basis.valuation_basis.currency_status == "KNOWN"
    assert basis.valuation_basis.cost_basis_currency == "EUR"
    for execution in basis.history:
        assert execution.currency_confirmation is None
        assert execution.currency_resolution.currency_code == "EUR"
        assert execution.currency_resolution.source == "HISTORICAL_LISTINGS"
        assert execution.currency_resolution.evidence_ids == (source.id,)
    assert all(fact.currency_resolution.currency_code is None for fact in facts)
