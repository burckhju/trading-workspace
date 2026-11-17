"""B04 consumes existing economic/calendar/scale owners without Target evidence."""

from dataclasses import replace
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from tests.unit.backend.features.position_monitoring import (
    test_hebeltrader_original_bid_service as existing,
)
from tests.unit.backend.features.position_monitoring import (
    test_hebeltrader_product_price_scale as scales,
)

from app.features.market_data.domain.session_evidence import SessionDay, SessionWindow
from app.features.position_monitoring.domain.hebeltrader_original_bid import assess_original_bid
from app.features.position_monitoring.service import hebeltrader_loss_inputs as module
from app.features.position_monitoring.service.hebeltrader_loss import HebeltraderLossService

case = existing.case
context = existing.context
pytestmark = pytest.mark.asyncio
NOW = existing.NOW


@pytest.fixture
def loss_inputs(monkeypatch, context):
    state = context.state
    state.price_scale = scales.scale_evidence()
    monkeypatch.setattr(module, "RiskMarketDataReader", context.quote_factory)
    monkeypatch.setattr(module, "SessionEvidenceReader", context.calendar_factory)
    monkeypatch.setattr(module, "ProductPriceScaleEvidenceReader", context.scale_factory)
    owner = state.owner.execution_basis
    trade_read = AsyncMock(return_value=owner.trade)
    position_read = AsyncMock(
        side_effect=lambda *args: state.owner.execution_basis.valuation_basis.position
    )
    basis_read = AsyncMock(side_effect=lambda *args, **kwargs: state.owner.execution_basis)
    monkeypatch.setattr(
        module,
        "SqlAlchemyReadOnlyTradeRepository",
        Mock(return_value=SimpleNamespace(get=trade_read)),
    )
    monkeypatch.setattr(
        module,
        "SqlAlchemyPositionRepository",
        Mock(return_value=SimpleNamespace(get_for_trade=position_read)),
    )
    monkeypatch.setattr(module, "read_position_execution_basis", basis_read)
    monkeypatch.setattr(
        module,
        "WarrantService",
        Mock(
            return_value=SimpleNamespace(
                get=AsyncMock(
                    return_value=SimpleNamespace(
                        underlying_id=state.owner.coverage.underlying_id,
                        display_name="Synthetic owner product",
                        isin=state.saved.quote.isin,
                        wkn="TEST01",
                    )
                )
            )
        ),
    )
    return context, basis_read


async def read(loss_inputs):
    context, _ = loss_inputs
    return await module.read_loss_inputs(context.session, **context.scope, now=NOW)


async def test_existing_owner_supplies_entry_quantity_gross_and_currency_without_f207_targets(
    loss_inputs,
):
    context, basis_read = loss_inputs
    result = await read(loss_inputs)
    assert result.problems == ()
    owner = context.state.owner.execution_basis
    assert result.owner_basis_id == owner.valuation_basis.basis_id
    assert result.material["economic_basis"]["position"]["open_quantity"] == 80
    assert (
        Decimal(result.material["economic_basis"]["position"]["average_entry_price"])
        == owner.valuation_basis.position.average_entry_price
    )
    assert result.material["entry"]["execution_id"] == str(owner.effective_executions[0].id)
    assert (
        result.material["underlying_sessions"]["count"]["evaluated_at"]
        == result.material["bid"]["original_bid_at"]
    )
    basis_read.assert_awaited_once_with(
        context.session, trade=owner.trade, position_id=context.scope["position_id"]
    )
    context.owner_read.assert_not_awaited()  # no F207 aggregate/source/target read
    assert HebeltraderLossService._decision(result, (), None).outcome == "LOSS"
    context.session.commit.assert_not_awaited()


@pytest.mark.parametrize("age,outcome", [(900, "LOSS"), (901, "NOT_ASSESSABLE")])
async def test_real_bid_qualifier_boundary_reaches_actual_b04_decision(loss_inputs, age, outcome):
    context, _ = loss_inputs
    context.state.saved = existing.scoped_quote(context.state.owner, timedelta(seconds=age))
    result = await read(loss_inputs)
    assert HebeltraderLossService._decision(result, (), None).outcome == outcome
    if age == 901:
        assert "ORIGINAL_BID_TOO_OLD" in result.problems


@pytest.mark.parametrize("bid_after_close", [False, True])
async def test_twentieth_session_closes_between_bid_and_read_without_requalifying_old_bid(
    loss_inputs, bid_after_close
):
    context, _ = loss_inputs
    closing = NOW - timedelta(seconds=30)
    context.state.saved = existing.scoped_quote(
        context.state.owner, timedelta(seconds=10 if bid_after_close else 60)
    )

    def days(kind, day):
        if kind == "WARRANT":
            return existing.original_day(kind, day)
        countable = NOW.date() - timedelta(days=19) <= day <= NOW.date()
        if not countable:
            return SessionDay(day, "CLOSED", (), "Explicit synthetic closed day")
        end = closing if day == NOW.date() else datetime.combine(day, time(17), UTC)
        return SessionDay(
            day,
            "SESSION",
            (SessionWindow(datetime.combine(day, time(9), UTC), end),),
            "Synthetic 20-session source",
        )

    context.state.day = days
    result = await read(loss_inputs)
    assert result.material["underlying_sessions"]["count"]["completed_sessions"] == (
        20 if bid_after_close else 19
    )
    assert HebeltraderLossService._decision(result, (), None).outcome == (
        "LOSS" if bid_after_close else "NOT_REACHED"
    )


@pytest.mark.parametrize("missing", ["bid", "side_time", "scale", "currency", "currency_mismatch"])
async def test_no_price_time_scale_or_currency_substitutes(loss_inputs, missing):
    context, _ = loss_inputs
    saved = context.state.saved
    if missing == "bid":
        context.state.saved = replace(
            saved,
            quote=replace(
                saved.quote,
                bid=None,
                original_evidence=replace(saved.quote.original_evidence, bid=None),
            ),
        )
    elif missing == "side_time":
        context.state.saved = replace(saved, quote=replace(saved.quote, original_evidence=None))
    elif missing == "scale":
        context.state.price_scale = scales.scale_evidence(missing=True)
    else:
        basis = context.state.owner.execution_basis
        economic = replace(
            basis.valuation_basis,
            currency_status="UNKNOWN" if missing == "currency" else "KNOWN",
            cost_basis_currency=None if missing == "currency" else "USD",
        )
        context.state.owner = replace(
            context.state.owner, execution_basis=replace(basis, valuation_basis=economic)
        )
    result = await read(loss_inputs)
    assert result.problems
    assert HebeltraderLossService._decision(result, (), None).outcome == "NOT_ASSESSABLE"


async def test_full_sale_needs_no_price_calendar_scale_or_target_input(loss_inputs):
    context, _ = loss_inputs
    basis = context.state.owner.execution_basis
    economic = replace(
        basis.valuation_basis,
        position=replace(
            basis.valuation_basis.position, open_quantity=0, cost_basis=Decimal(0), closed_at=NOW
        ),
    )
    context.state.owner = replace(
        context.state.owner, execution_basis=replace(basis, valuation_basis=economic)
    )
    result = await read(loss_inputs)
    assert result.closed and result.problems == ()
    assert HebeltraderLossService._decision(result, ("SOURCE_MISSING",), None).outcome == "CLOSED"
    context.quote_read.assert_not_awaited()
    context.current_read.assert_not_awaited()
    context.scale_read.assert_not_awaited()


async def test_fingerprint_deduplicates_read_clock_but_not_stale_transition_or_owner_correction(
    loss_inputs,
):
    context, _ = loss_inputs
    result = await read(loss_inputs)
    result.material["source_qualification"] = {"status": "synthetic"}
    result.material["status_observations"] = None
    decision = HebeltraderLossService._decision(result, (), None)
    before = HebeltraderLossService._input_fingerprint(result, decision)
    result.material["saved_quote"]["provenance"]["read_at"] = (
        NOW + timedelta(seconds=1)
    ).isoformat()
    result.material["product_scale"]["evaluated_at"] = (NOW + timedelta(seconds=1)).isoformat()
    assert HebeltraderLossService._input_fingerprint(result, decision) == before
    assert (
        HebeltraderLossService._input_fingerprint(
            replace(result, owner_basis_id="f" * 64), decision
        )
        != before
    )
    stale = replace(decision, outcome="NOT_ASSESSABLE", reasons=("ORIGINAL_BID_TOO_OLD",))
    assert HebeltraderLossService._input_fingerprint(result, stale) != before
    # Independently demonstrate a freshly read older BID remains old.
    assert (
        assess_original_bid(
            context.state.saved, evaluated_at=NOW + timedelta(seconds=842), applicable=True
        ).status
        == "UNSUITABLE"
    )
