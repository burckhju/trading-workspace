"""Currency reuse follows evidenced BUYs, immutable corrections and exact scope."""

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from tests.unit.backend.features.trade_position.test_application import FakeUow

from app.features.trade_position.api.router import _execution, _timeline_entry
from app.features.trade_position.domain.currency import (
    ExecutionCurrencyConfirmation,
    ExecutionCurrencyResolution,
    ExecutionCurrencySource,
)
from app.features.trade_position.domain.currency_resolution import (
    CurrencyResolutionLimitExceeded,
    resolve_execution_currencies,
)
from app.features.trade_position.domain.enums import ExecutionSide, TradeOrigin
from app.features.trade_position.domain.models import ExecutionRecord, Position, Trade
from app.features.trade_position.service.application import TradePositionService

AT = datetime(2026, 8, 1, tzinfo=UTC)
ACTOR = UUID(int=3)
TRADE = Trade(
    id=UUID(int=1),
    workspace_id=UUID(int=2),
    product_id=UUID(int=4),
    origin=TradeOrigin.EXTERNAL,
    created_at=AT,
    created_by=ACTOR,
)


def execution(number: int, side: str = "BUY", *, day: int | None = None) -> ExecutionRecord:
    return ExecutionRecord(
        id=UUID(int=number),
        trade_id=TRADE.id,
        product_id=TRADE.product_id,
        side=ExecutionSide(side),
        quantity=10 if side == "BUY" else 1,
        price_per_unit=Decimal("2" if side == "BUY" else "3"),
        executed_at=AT + timedelta(days=number if day is None else day),
        recorded_at=AT + timedelta(days=70),
        recorded_by=ACTOR,
    )


def confirmed(fact: ExecutionRecord, code: str = "EUR") -> ExecutionCurrencyConfirmation:
    return ExecutionCurrencyConfirmation(
        id=UUID(int=fact.id.int + 1000),
        workspace_id=TRADE.workspace_id,
        trade_id=TRADE.id,
        execution_id=fact.id,
        currency_code=code,
        source=ExecutionCurrencySource.USER_CONFIRMED,
        note="Synthetic actual purchase declaration",
        confirmed_at=AT + timedelta(days=71),
        confirmed_by=ACTOR,
        supersedes_confirmation_id=None,
        request_id=UUID(int=fact.id.int + 2000),
        request_fingerprint="a" * 64,
    )


def resolve(facts, confirmations=()):
    return resolve_execution_currencies(
        trade=TRADE,
        executions=facts,
        current={item.execution_id: item for item in confirmations},
    )


def test_one_confirmed_buy_resolves_partial_sales_and_rebuy_without_new_declarations():
    facts = [execution(10), execution(11, "SELL"), execution(12), execution(13, "SELL")]
    declaration = confirmed(facts[0])
    before = tuple(facts)
    values = resolve(facts, (declaration,))
    assert values[facts[0].id] == ExecutionCurrencyResolution(
        "EUR", "USER_CONFIRMED", (facts[0].id,), (declaration.id,)
    )
    assert (
        values[facts[1].id]
        == values[facts[2].id]
        == ExecutionCurrencyResolution("EUR", "PRIOR_BUYS", (facts[0].id,), (declaration.id,))
    )
    assert values[facts[3].id] == ExecutionCurrencyResolution(
        "EUR", "PRIOR_BUYS", (facts[0].id, facts[2].id), (declaration.id,)
    )
    assert tuple(facts) == before
    assert all(fact.currency_confirmation is None for fact in facts)
    assert values == resolve(list(reversed(facts)), (declaration,))
    with pytest.raises(FrozenInstanceError):
        values[facts[1].id].currency_code = "USD"


def test_later_buy_cannot_fill_earlier_unknown_costs_or_seed_an_incomplete_prefix():
    facts = [execution(10), execution(11, "SELL"), execution(12), execution(13)]
    values = resolve(facts, (confirmed(facts[2]),))
    assert values[facts[0].id].currency_code is None
    assert values[facts[1].id].source == "UNKNOWN"
    assert values[facts[2].id].source == "USER_CONFIRMED"
    assert values[facts[3].id].source == "UNKNOWN"
    assert values[facts[3].id].source_execution_ids == (facts[0].id, facts[2].id)
    assert values[facts[3].id].confirmation_ids == (confirmed(facts[2]).id,)


def test_sell_proceeds_never_establish_the_currency_of_a_buy():
    facts = [execution(10), execution(11, "SELL"), execution(12), execution(13, "SELL")]
    values = resolve(facts, (confirmed(facts[1]),))
    assert values[facts[1].id].source == "USER_CONFIRMED"
    assert values[facts[2].id].source == values[facts[3].id].source == "UNKNOWN"
    assert values[facts[3].id].confirmation_ids == ()


def test_explicit_foreign_sale_remains_foreign_and_does_not_poison_later_buy_currency():
    facts = [execution(10), execution(11, "SELL"), execution(12), execution(13, "SELL")]
    values = resolve(facts, (confirmed(facts[0]), confirmed(facts[1], "USD")))
    assert values[facts[1].id].currency_code == "USD"
    assert values[facts[1].id].source == "USER_CONFIRMED"
    assert values[facts[2].id].currency_code == values[facts[3].id].currency_code == "EUR"
    assert confirmed(facts[1], "USD").id not in values[facts[3].id].confirmation_ids


def test_mixed_prior_buys_block_omitted_currency_without_overwriting_explicit_evidence():
    facts = [execution(10), execution(11), execution(12), execution(13, "SELL")]
    declarations = (confirmed(facts[0]), confirmed(facts[1], "USD"))
    values = resolve(facts, declarations)
    assert values[facts[2].id].source == values[facts[3].id].source == "MIXED"
    assert values[facts[2].id].currency_code is values[facts[3].id].currency_code is None
    overridden = resolve(facts, (*declarations, confirmed(facts[3])))
    assert overridden[facts[3].id].source == "USER_CONFIRMED"
    assert overridden[facts[3].id].currency_code == "EUR"
    assert overridden[facts[2].id].source == "MIXED"


@pytest.mark.parametrize("side", ["BUY", "SELL"])
def test_same_side_correction_chain_preserves_exact_nearest_confirmed_ancestor(side):
    original = execution(10, side)
    first = replace(
        original, id=UUID(int=11), price_per_unit=Decimal("4"), supersedes_execution_id=original.id
    )
    second = replace(
        first, id=UUID(int=12), executed_at=AT + timedelta(days=9), supersedes_execution_id=first.id
    )
    facts = [second, original, first]
    values = resolve(facts, (confirmed(original),))
    expected = ExecutionCurrencyResolution(
        "EUR", "REPLACED_EXECUTION", (original.id,), (confirmed(original).id,)
    )
    assert values[first.id] == values[second.id] == expected
    newer = resolve(facts, (confirmed(original), confirmed(first, "USD")))
    assert newer[second.id] == ExecutionCurrencyResolution(
        "USD", "REPLACED_EXECUTION", (first.id,), (confirmed(first).id,)
    )
    explicit = resolve(facts, (confirmed(original), confirmed(first, "USD"), confirmed(second)))
    assert explicit[second.id].source == "USER_CONFIRMED"
    assert explicit[second.id].currency_code == "EUR"


def test_same_side_replacement_uses_ancestor_evidence_in_later_sell_provenance():
    original, sale = execution(10), execution(13, "SELL")
    replacement = replace(original, id=UUID(int=12), supersedes_execution_id=original.id)
    values = resolve([original, sale, replacement], (confirmed(original),))
    assert values[sale.id] == ExecutionCurrencyResolution(
        "EUR", "PRIOR_BUYS", (replacement.id, original.id), (confirmed(original).id,)
    )
    assert original.currency_confirmation is replacement.currency_confirmation is None


def test_moving_confirmed_buy_after_an_unconfirmed_buy_never_backfills_that_earlier_buy():
    original, additional, sale = execution(10), execution(11), execution(15, "SELL")
    replacement = replace(
        original,
        id=UUID(int=13),
        executed_at=AT + timedelta(days=13),
        supersedes_execution_id=original.id,
    )
    values = resolve([original, additional, replacement, sale], (confirmed(original),))
    assert values[additional.id].source == "UNKNOWN"
    assert values[replacement.id].source == "REPLACED_EXECUTION"
    assert values[sale.id].source == "UNKNOWN"


def test_side_change_stops_ancestor_inheritance_even_if_a_later_ancestor_matches_again():
    original = execution(10)
    changed = replace(
        original, id=UUID(int=11), side=ExecutionSide.SELL, supersedes_execution_id=original.id
    )
    changed_back = replace(original, id=UUID(int=12), supersedes_execution_id=changed.id)
    values = resolve([original, changed, changed_back], (confirmed(original),))
    assert values[changed.id].source == values[changed_back.id].source == "UNKNOWN"


@pytest.mark.parametrize("wrong", ["workspace", "trade", "execution", "source", "product"])
def test_unqualified_or_cross_scope_evidence_cannot_seed_inheritance(wrong):
    first, sale = execution(10), execution(11, "SELL")
    declaration = confirmed(first)
    if wrong == "workspace":
        declaration = replace(declaration, workspace_id=UUID(int=99))
    elif wrong == "trade":
        declaration = replace(declaration, trade_id=UUID(int=99))
    elif wrong == "execution":
        declaration = replace(declaration, execution_id=UUID(int=99))
    elif wrong == "source":
        declaration = replace(declaration, source="CURRENT_LISTING")
    else:
        first = replace(first, product_id=UUID(int=99))
    values = resolve_execution_currencies(
        trade=TRADE, executions=[first, sale], current={first.id: declaration}
    )
    assert values[first.id].currency_code is values[sale.id].currency_code is None
    assert values[sale.id].confirmation_ids == ()


def test_other_trade_cannot_supply_a_buy_or_supersede_an_in_scope_buy():
    first, sale = execution(10), execution(12, "SELL")
    foreign = replace(execution(11), trade_id=UUID(int=99), supersedes_execution_id=first.id)
    values = resolve([first, foreign, sale], (confirmed(first),))
    assert values[foreign.id].source == "UNKNOWN"
    assert values[sale.id].currency_code == "EUR"
    assert values[sale.id].source_execution_ids == (first.id,)


@pytest.mark.parametrize("kind", ["missing", "cycle"])
def test_broken_unconfirmed_correction_ancestry_stays_unknown_without_recursion(kind):
    first = replace(execution(10), supersedes_execution_id=UUID(int=11))
    facts = [first]
    if kind == "cycle":
        facts.append(replace(execution(11), supersedes_execution_id=first.id))
    assert all(value.source == "UNKNOWN" for value in resolve(facts).values())


def test_complete_provenance_limit_rejects_instead_of_truncating():
    first, sale = execution(10), execution(11, "SELL")
    with pytest.raises(CurrencyResolutionLimitExceeded):
        resolve_execution_currencies(
            trade=TRADE,
            executions=[first, sale],
            current={first.id: confirmed(first)},
            max_provenance_links=3,
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("action", ["sale", "purchase", "correction", "replay", "timeline"])
async def test_owner_response_enrichment_reuses_currency_without_confirmation_writes(action):
    first = execution(10)
    declaration = confirmed(first)
    uow = FakeUow()
    uow.trades.get.return_value = TRADE
    uow.executions.list_for_trade = AsyncMock(return_value=[first])
    uow.executions.list_effective_for_trade.return_value = [first]
    uow.executions.find_request = AsyncMock(return_value=None)
    uow.positions.get_for_trade.return_value = Position.from_execution(
        id=UUID(int=50), trade=TRADE, execution=first
    )
    currency_owner = SimpleNamespace(
        current_for_trade=AsyncMock(return_value={first.id: declaration}), capture=AsyncMock()
    )
    service = TradePositionService(
        uow=uow, workspace_selections=SimpleNamespace(), currency_confirmations=currency_owner
    )
    args = dict(
        workspace_id=TRADE.workspace_id,
        trade_id=TRADE.id,
        quantity=1,
        price_per_unit=Decimal("3"),
        executed_at=AT + timedelta(days=12),
        actor=ACTOR,
    )
    if action == "sale":
        value, _ = await service.record_sale(**args)
    elif action == "purchase":
        value, _ = await service.record_additional_purchase(**args)
    elif action == "correction":
        value, _ = await service.correct_execution(
            **args, execution_id=first.id, side=ExecutionSide.BUY
        )
    elif action == "replay":
        key, fingerprint = service._request_identity(
            TRADE.workspace_id,
            UUID(int=51),
            f"sale:{TRADE.id}",
            1,
            Decimal("3"),
            args["executed_at"],
        )
        sale = replace(execution(12, "SELL"), request_key=key, request_fingerprint=fingerprint)
        uow.executions.find_request.return_value = sale
        uow.executions.list_for_trade.return_value = [first, sale]
        value, _ = await service.record_sale(**args, request_id=UUID(int=51))
        uow.executions.add.assert_not_awaited()
        uow.commit.assert_not_awaited()
    else:
        sale = execution(12, "SELL")
        uow.executions.list_for_trade.return_value = [first, sale]
        entries = await service.get_trade_timeline(
            workspace_id=TRADE.workspace_id, trade_id=TRADE.id
        )
        body = _timeline_entry(entries[1]).model_dump(mode="json")
        assert body["currency_resolution"]["source"] == "PRIOR_BUYS"
        assert body["currency_resolution"]["confirmation_ids"] == [str(declaration.id)]
        assert body["currency_confirmation"] is None
        currency_owner.capture.assert_not_awaited()
        uow.executions.add.assert_not_awaited()
        uow.commit.assert_not_awaited()
        return
    assert value.currency_confirmation is None
    assert value.currency_resolution == ExecutionCurrencyResolution(
        "EUR",
        "REPLACED_EXECUTION" if action == "correction" else "PRIOR_BUYS",
        (first.id,),
        (declaration.id,),
    )
    body = _execution(value).model_dump(mode="json")
    assert body["currency_resolution"]["currency_code"] == "EUR"
    assert body["currency_resolution"]["confirmation_ids"] == [str(declaration.id)]
    currency_owner.capture.assert_not_awaited()
