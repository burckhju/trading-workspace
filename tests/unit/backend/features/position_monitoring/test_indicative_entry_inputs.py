"""Synthetic existing-owner inputs, with no provider, target or economic writes."""

from dataclasses import replace
from datetime import UTC, datetime, time, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from tests.unit.backend.features.position_monitoring import (
    test_hebeltrader_original_bid_service as existing,
)
from tests.unit.backend.features.position_monitoring import (
    test_hebeltrader_product_price_scale as scales,
)
from tests.unit.backend.features.position_monitoring.test_indicative_entry import (
    issuer_saved,
)

from app.features.market_data.domain.issuer_indications import ISSUER_INDICATIONS
from app.features.market_data.domain.session_evidence import SessionDay, SessionWindow
from app.features.position_monitoring.service import indicative_entry_inputs as module
from app.features.position_monitoring.service.indicative_entry import (
    IndicativeEntryService,
)

case = existing.case
context = existing.context
pytestmark = pytest.mark.asyncio
NOW = existing.NOW


@pytest.fixture
def review_inputs(monkeypatch, context):
    state = context.state
    state.price_scale = scales.scale_evidence()
    state.selection_policy = "POSITION_QUOTE_SOURCE_POLICY_V1"
    state.status = None
    monkeypatch.setattr(module, "RiskMarketDataReader", context.quote_factory)
    monkeypatch.setattr(module, "SessionEvidenceReader", context.calendar_factory)
    monkeypatch.setattr(module, "ProductPriceScaleEvidenceReader", context.scale_factory)
    monkeypatch.setattr(
        module,
        "MarketStatusReader",
        Mock(return_value=SimpleNamespace(read=AsyncMock(side_effect=lambda **_: state.status))),
    )
    owner = state.owner.execution_basis
    monkeypatch.setattr(
        module,
        "SqlAlchemyReadOnlyTradeRepository",
        Mock(return_value=SimpleNamespace(get=AsyncMock(return_value=owner.trade))),
    )
    monkeypatch.setattr(
        module,
        "SqlAlchemyPositionRepository",
        Mock(
            return_value=SimpleNamespace(
                get_for_trade=AsyncMock(
                    side_effect=lambda *_: state.owner.execution_basis.valuation_basis.position
                )
            )
        ),
    )
    basis_read = AsyncMock(side_effect=lambda *_, **__: state.owner.execution_basis)
    monkeypatch.setattr(module, "read_position_execution_basis", basis_read)
    monkeypatch.setattr(
        module,
        "WarrantService",
        Mock(
            return_value=SimpleNamespace(
                get=AsyncMock(
                    return_value=SimpleNamespace(
                        underlying_id=state.owner.coverage.underlying_id,
                        display_name="Synthetic held warrant",
                        isin=state.saved.quote.isin,
                        wkn="TEST01",
                    )
                )
            )
        ),
    )
    context.session.get = AsyncMock(
        side_effect=lambda *_: SimpleNamespace(policy_version=state.selection_policy)
    )
    return context, basis_read


async def read(review_inputs):
    context, _ = review_inputs
    return await module.read_indicative_inputs(context.session, **context.scope, now=NOW)


async def test_original_owner_inputs_without_target_or_product_open_calendar(
    review_inputs,
):
    context, basis_read = review_inputs
    result = await read(review_inputs)
    assert result.problems == ()
    assert result.owner_basis_id == context.state.owner.execution_basis.valuation_basis.basis_id
    assert IndicativeEntryService._decision(result, None).outcome == "BELOW_ENTRY"
    assert result.review_count.evaluated_at == NOW
    assert result.comparison_count.evaluated_at == result.quote.original_bid_at
    assert {call.kwargs["instrument_kind"] for call in context.current_read.await_args_list} == {
        "UNDERLYING"
    }
    basis_read.assert_awaited_once()
    context.owner_read.assert_not_awaited()  # no F207/target aggregation
    context.session.commit.assert_not_awaited()


async def test_twentieth_close_between_original_bid_and_receipt_does_not_qualify_old_bid(
    review_inputs,
):
    context, _ = review_inputs
    closing = NOW - timedelta(seconds=30)
    context.state.saved = existing.scoped_quote(context.state.owner, timedelta(seconds=60))

    def days(_kind, day):
        if not NOW.date() - timedelta(days=19) <= day <= NOW.date():
            return SessionDay(day, "CLOSED", (), "Synthetic explicitly closed day")
        end = closing if day == NOW.date() else datetime.combine(day, time(17), UTC)
        return SessionDay(
            day,
            "SESSION",
            (SessionWindow(datetime.combine(day, time(9), UTC), end),),
            "Synthetic qualified session",
        )

    context.state.day = days
    result = await read(review_inputs)
    assert result.review_count.completed_sessions == 20
    assert result.comparison_count.completed_sessions == 19
    decision = IndicativeEntryService._decision(result, None)
    assert decision.outcome == "NOT_REACHED" and decision.review_due is True


async def test_registered_unknown_original_time_uses_review_clock_explicitly(
    review_inputs,
):
    context, _ = review_inputs
    saved = issuer_saved()
    context.state.saved = replace(
        saved,
        route=context.state.saved.route,
        retrieved_at=NOW,
        provenance=replace(saved.provenance, read_at=NOW, retrieved_at=NOW),
    )
    context.state.selection_policy = ISSUER_INDICATIONS["MORGAN_STANLEY"][2]
    result = await read(review_inputs)
    assert result.problems == ()
    assert result.quote.evaluation_mode == "INDICATIVE_ISSUER"
    assert result.quote.original_bid_at is None
    assert result.comparison_count.evaluated_at == NOW
    assert result.material["product_scale"]["coverage_basis"] == (
        "REVIEW_TIME_ORIGINAL_BID_TIME_UNKNOWN"
    )
    assert result.material["product_scale"]["owner_assessment"]["bid_status"] == "MISSING"
    assert IndicativeEntryService._decision(result, None).outcome == "BELOW_ENTRY"


@pytest.mark.parametrize("missing", ["bid", "currency", "scale", "calendar"])
async def test_incomplete_required_facts_produce_data_problem_without_target_gating(
    review_inputs, missing
):
    context, _ = review_inputs
    state = context.state
    if missing == "bid":
        state.saved = replace(
            state.saved,
            quote=replace(state.saved.quote, bid=None, original_evidence=None),
        )
    elif missing == "scale":
        state.price_scale = scales.scale_evidence(missing=True)
    elif missing == "calendar":
        state.changes["UNDERLYING"] = {
            "status": "INCOMPLETE",
            "reasons": ("SESSION_DAYS_MISSING",),
        }
    else:
        basis = state.owner.execution_basis
        state.owner = replace(
            state.owner,
            execution_basis=replace(
                basis,
                valuation_basis=replace(
                    basis.valuation_basis,
                    currency_status="UNKNOWN",
                    cost_basis_currency=None,
                ),
            ),
        )
    result = await read(review_inputs)
    decision = IndicativeEntryService._decision(result, None)
    assert decision.outcome == "UNAVAILABLE"
    if missing != "calendar":
        assert decision.review_due is True


async def test_latest_transport_gap_blocks_price_but_missing_status_does_not(
    review_inputs,
):
    context, _ = review_inputs
    context.state.status = SimpleNamespace(
        latest_gap=SimpleNamespace(reason="TransportError", captured_at=NOW),
        latest_observations=(),
        latest_capture=None,
    )
    # The pure classifier accepts a protocol-like status; composition persists
    # real dataclasses, exercised separately by the PostgreSQL pipeline.
    saved = context.state.saved
    quote = module.qualify_review_quote(saved, now=NOW, selection_policy=None)
    assert module.supply_problems(saved, quote, context.state.status) == (
        "REVIEW_PRICE_SUPPLY_INTERRUPTED",
    )
    context.state.status.latest_gap.reason = "ORIGINAL_MARKET_STATUS_NOT_DELIVERED"
    assert module.supply_problems(saved, quote, context.state.status) == ()


async def test_negative_priceless_source_point_blocks_old_bid_without_inventing_status_ttl(
    review_inputs,
):
    context, _ = review_inputs
    saved = context.state.saved
    quote = module.qualify_review_quote(saved, now=NOW, selection_policy=None)
    status = SimpleNamespace(
        latest_gap=None,
        latest_capture=None,
        latest_observations=(
            SimpleNamespace(
                original=SimpleNamespace(
                    observed_at=quote.original_bid_at + timedelta(seconds=1),
                    status="SUSPENDED",
                )
            ),
        ),
    )
    assert module.supply_problems(saved, quote, status) == (
        "REVIEW_LATER_NEGATIVE_STATUS_OBSERVED",
    )
    status.latest_observations[0].original.observed_at = quote.original_bid_at - timedelta(
        seconds=1
    )
    assert module.supply_problems(saved, quote, status) == ()


async def test_negative_status_received_after_unknown_clock_indication_is_retained_as_problem():
    saved = issuer_saved()
    quote = module.qualify_review_quote(
        saved,
        now=saved.retrieved_at,
        selection_policy=ISSUER_INDICATIONS["MORGAN_STANLEY"][2],
    )
    late = SimpleNamespace(
        original=SimpleNamespace(
            status="SUSPENDED", observed_at=saved.retrieved_at - timedelta(days=1)
        ),
        captured_at=saved.retrieved_at + timedelta(seconds=1),
    )
    status = SimpleNamespace(latest_gap=None, latest_observations=(), latest_capture=late)
    assert module.supply_problems(saved, quote, status) == (
        "REVIEW_NEGATIVE_STATUS_RECEIVED_AFTER_INDICATION",
    )


async def test_disclosed_status_point_has_original_and_capture_times_without_validity_claim():
    context = module.status_point_context(
        {
            "status_observations": {
                "latest_observations": [],
                "latest_capture": {
                    "captured_at": NOW.isoformat(),
                    "original": {
                        "status": "CLOSED",
                        "observed_at": (NOW - timedelta(days=1)).isoformat(),
                    },
                },
            }
        }
    )
    assert context["source_status_point"] == "CLOSED"
    assert context["source_status_observed_at"] != context["source_status_captured_at"]
    assert context["status_validity"] == "NOT_ESTABLISHED"
