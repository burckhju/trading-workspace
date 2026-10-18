"""Independent report oracles exercise selection, evidence and owner arithmetic."""

from dataclasses import asdict, replace
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from tests.unit.backend.features.performance.fixtures import (
    RECORDED,
    SEPTEMBER,
    confirmed,
    execution,
    reference,
    snapshot,
    trade_fact,
)

from app.features.performance.domain.models import RealizedGrossReport
from app.features.performance.domain.report import ReportLimitExceeded, build_report, displayed
from app.features.trade_position.domain.enums import TradeOrigin
from app.features.trade_position.domain.projector import PositionProjector


def _identities(report: RealizedGrossReport) -> None:
    counts = report.counts
    assert counts.examined == len(report.items)
    assert counts.examined == (
        counts.in_period + counts.outside_period + counts.period_ambiguous + counts.period_unknown
    )
    assert counts.examined == counts.candidates + counts.excluded
    assert counts.candidates == counts.usable + counts.unresolved
    assert len({item.execution_id for item in report.items}) == len(report.items)
    assert len({source.execution_id for source in report.sources}) == len(report.sources)


@pytest.mark.parametrize("closed", [True, False])
def test_reference_september_uses_sell_contributions_with_full_prefix(closed: bool) -> None:
    facts = reference() if closed else reference()[:-1]
    basis = snapshot(facts)
    report = build_report(basis, SEPTEMBER)
    _identities(report)
    assert report.definition_version == "realized-gross-sell-v1"
    assert report.summary.status == "COMPLETE"
    assert report.summary.total == "10.00"
    assert report.summary.total_display == "10.00"
    assert report.summary.subtotal is None
    selected = [item for item in report.items if item.status == "USABLE"]
    assert [item.execution_id for item in selected] == [facts[2].id, facts[4].id]
    assert [item.realized_gross_pnl_delta for item in selected] == ["30.00", "-20.00"]
    assert [item.average_cost_per_unit for item in selected] == ["2.00", "3.00"]
    assert [item.cost_basis_before for item in selected] == ["160.00", "300.00"]
    assert [item.cost_basis_after for item in selected] == ["100.00", "180.00"]
    assert [item.open_quantity_after for item in selected] == [50, 60]
    assert [item.cost_basis_execution_ids for item in selected] == [
        tuple(fact.id for fact in facts[:2]),
        tuple(fact.id for fact in facts[:4]),
    ]
    assert selected[1].currency_confirmation_ids == (
        confirmed(facts[0]).id,
        confirmed(facts[3]).id,
        confirmed(facts[4]).id,
    )
    assert all(source.executed_at is None for source in report.sources)
    assert [source.execution_id for source in report.sources] == [fact.id for fact in facts]
    assert report.counts.in_period == report.counts.usable == 2
    assert report.counts.outside_period == 2 if closed else report.counts.outside_period == 1
    full = build_report(
        basis, replace(SEPTEMBER, from_date=date(2026, 8, 1), to_date=date(2026, 10, 31))
    )
    owner = PositionProjector.project(
        id=basis.trades[0].position_id,
        trade=basis.trades[0].trade,
        executions=[fact.to_domain() for fact in facts],
    )
    assert (
        Decimal(full.summary.total) == owner.realized_gross_pnl == Decimal("50" if closed else "20")
    )


def test_price_correction_keeps_old_source_and_counts_replacement_once() -> None:
    original = reference()
    replacement = replace(
        original[4],
        id=UUID(int=201),
        price_per_unit=Decimal("3.00"),
        supersedes_execution_id=original[4].id,
        recorded_at=RECORDED + timedelta(hours=1),
    )
    basis = snapshot((*original, replacement))
    report = build_report(basis, SEPTEMBER)
    _identities(report)
    assert report.summary.total == "30.00"
    assert report.counts.examined == 4
    assert {item.execution_id for item in report.items} == {
        original[1].id,
        original[2].id,
        replacement.id,
        original[5].id,
    }
    corrected_item = next(item for item in report.items if item.execution_id == replacement.id)
    assert corrected_item.realized_gross_pnl_delta == "0.00"
    old_source = next(source for source in report.sources if source.execution_id == original[4].id)
    new_source = next(source for source in report.sources if source.execution_id == replacement.id)
    assert not old_source.is_effective
    assert old_source.superseded_by_execution_id == replacement.id
    assert old_source.price_per_unit == "2.50"
    assert new_source.is_effective
    assert new_source.supersedes_execution_id == original[4].id
    all_months = replace(SEPTEMBER, from_date=date(2026, 8, 1), to_date=date(2026, 10, 31))
    assert build_report(basis, all_months).summary.total == "70.00"


def test_replacement_does_not_inherit_original_currency_confirmation() -> None:
    original = reference()
    replacement = replace(original[4], id=UUID(int=201), supersedes_execution_id=original[4].id)
    report = build_report(
        snapshot(
            (*original, replacement), confirmations=tuple(confirmed(fact) for fact in original)
        ),
        SEPTEMBER,
    )
    assert report.summary.status == "PARTIAL"
    assert report.summary.total is None
    assert report.summary.subtotal == "30.00"
    new_item = next(item for item in report.items if item.execution_id == replacement.id)
    assert new_item.reasons == ("CURRENCY_UNKNOWN",)
    assert new_item.realized_gross_pnl_delta is None


def test_unconfirmed_real_facts_are_not_a_zero_or_an_empty_selection() -> None:
    report = build_report(snapshot(confirmations=()), SEPTEMBER)
    _identities(report)
    assert report.summary.status == "NOT_COMPUTABLE"
    assert report.summary.total is report.summary.subtotal is None
    assert report.summary.total_display is report.summary.subtotal_display is None
    assert report.counts.candidates == report.counts.unresolved == 2
    assert report.counts.excluded == 2
    assert all(item.realized_gross_pnl_delta is None for item in report.items)
    assert all(source.currency_confirmation is None for source in report.sources)


@pytest.mark.parametrize("kind", ["empty", "buy_only", "outside", "foreign", "cancelled"])
def test_completely_examined_empty_selection_is_explicit(kind: str) -> None:
    facts = (
        execution(101, "BUY", 2, "2", "2026-08-01"),
        execution(102, "SELL", 1, "3", "2026-08-02" if kind == "outside" else "2026-09-02"),
    )
    trades = (trade_fact(),)
    if kind == "empty":
        facts = ()
    elif kind == "buy_only":
        facts = facts[:1]
    elif kind == "cancelled":
        trades = (
            replace(
                trades[0],
                trade=replace(
                    trades[0].trade, cancelled_at=RECORDED, cancellation_reason="Synthetic misentry"
                ),
            ),
        )
    declarations = tuple(confirmed(fact, "USD" if kind == "foreign" else "EUR") for fact in facts)
    report = build_report(snapshot(facts, confirmations=declarations, trades=trades), SEPTEMBER)
    _identities(report)
    assert report.summary.status == "EMPTY"
    assert report.summary.total == "0"
    assert report.summary.total_display == "0.00"
    assert report.summary.subtotal is None
    assert report.counts.candidates == 0
    assert report.counts.cancelled == (1 if kind == "cancelled" else 0)
    if kind == "cancelled":
        assert report.items == ()
        assert report.excluded_trades[0].execution_ids == tuple(fact.id for fact in facts)
        assert len(report.sources) == 2


def test_partial_known_zero_and_complete_zero_remain_measured_results() -> None:
    facts = (
        execution(101, "BUY", 2, "2", "2026-08-01"),
        execution(102, "SELL", 1, "2", "2026-09-02"),
        execution(103, "SELL", 1, "2", "2026-09-03"),
    )
    partial = build_report(
        snapshot(facts, confirmations=tuple(confirmed(fact) for fact in facts[:2])), SEPTEMBER
    )
    assert partial.summary.status == "PARTIAL"
    assert partial.summary.total is None
    assert partial.summary.subtotal == "0"
    assert partial.summary.subtotal_display == "0.00"
    assert partial.items[0].realized_gross_pnl_delta == "0"
    assert partial.items[1].realized_gross_pnl_delta is None
    complete = build_report(snapshot(facts), SEPTEMBER)
    assert complete.summary.status == "COMPLETE"
    assert complete.summary.total == "0"
    assert complete.counts.usable == 2


@pytest.mark.parametrize("prior_sale_currency", [None, "USD"])
def test_previous_sale_revenue_currency_does_not_poison_later_cost_basis(
    prior_sale_currency: str | None,
) -> None:
    facts = (
        execution(101, "BUY", 100, "2", "2026-08-01"),
        execution(102, "SELL", 20, "3", "2026-09-02"),
        execution(103, "SELL", 10, "2.50", "2026-09-03"),
    )
    declarations = (confirmed(facts[0]), confirmed(facts[2]))
    if prior_sale_currency:
        declarations += (confirmed(facts[1], prior_sale_currency),)
    report = build_report(snapshot(facts, confirmations=declarations), SEPTEMBER)
    _identities(report)
    assert report.items[1].status == "USABLE"
    assert report.items[1].realized_gross_pnl_delta == "5.00"
    assert report.items[1].cost_basis_execution_ids == (facts[0].id, facts[1].id)
    assert report.items[1].currency_confirmation_ids == (
        confirmed(facts[0]).id,
        confirmed(facts[2]).id,
    )
    if prior_sale_currency:
        assert report.items[0].status == "EXCLUDED"
        assert "CURRENCY_MIXED" in report.items[0].reasons
        assert report.summary.status == "COMPLETE"
        assert report.summary.total == "5.00"
    else:
        assert report.items[0].status == "NOT_COMPUTABLE"
        assert report.summary.status == "PARTIAL"
        assert report.summary.subtotal == "5.00"


def test_all_prior_buy_prices_require_confirmed_same_currency() -> None:
    facts = reference()
    report = build_report(
        snapshot(
            facts,
            confirmations=tuple(
                confirmed(fact, "USD" if fact.id == facts[3].id else "EUR") for fact in facts
            ),
        ),
        SEPTEMBER,
    )
    assert report.summary.status == "PARTIAL"
    assert report.summary.subtotal == "30.00"
    second = next(item for item in report.items if item.execution_id == facts[4].id)
    assert second.reasons == ("CURRENCY_MIXED",)
    assert second.average_cost_per_unit is None
    assert second.cost_basis_before is None
    assert second.cost_basis_after is None
    assert second.realized_gross_pnl_delta is None


def test_currency_supersession_uses_exact_execution_id_and_preserves_history() -> None:
    basis = snapshot()
    original = basis.confirmations[0]
    replacement = replace(
        original,
        id=UUID(int=30_000),
        currency_code="USD",
        confirmed_at=RECORDED + timedelta(hours=1),
        supersedes_confirmation_id=original.id,
        request_id=UUID(int=40_000),
    )
    changed = replace(basis, confirmations=(*basis.confirmations, replacement))
    report = build_report(changed, SEPTEMBER)
    assert report.summary.status == "NOT_COMPUTABLE"
    assert report.sources[0].currency_confirmation == replacement
    assert report.sources[0].currency_history == (original, replacement)
    assert report.basis.id != build_report(basis, SEPTEMBER).basis.id
    assert all(
        "CURRENCY_MIXED" in item.reasons for item in report.items if item.status == "NOT_COMPUTABLE"
    )


@pytest.mark.parametrize("wrong", ["workspace", "trade", "source", "duplicate_root"])
def test_unqualified_confirmation_never_establishes_currency(wrong: str) -> None:
    facts = reference()[:3]
    declarations = [confirmed(fact) for fact in facts]
    if wrong == "workspace":
        declarations[0] = replace(declarations[0], workspace_id=UUID(int=99))
    elif wrong == "trade":
        declarations[0] = replace(declarations[0], trade_id=UUID(int=99))
    elif wrong == "source":
        declarations[0] = replace(declarations[0], source="CURRENT_LISTING")
    else:
        declarations.append(replace(declarations[0], id=UUID(int=99)))
    report = build_report(snapshot(facts, confirmations=tuple(declarations)), SEPTEMBER)
    assert report.summary.status == "NOT_COMPUTABLE"
    assert report.sources[0].currency_confirmation is None
    assert report.items[1].reasons == ("CURRENCY_UNKNOWN",)


def test_eur_and_usd_are_explicit_separate_selections_without_fx() -> None:
    eur_trade, usd_trade = trade_fact(), trade_fact(2)
    eur_facts = (
        execution(101, "BUY", 10, "2", "2026-08-01"),
        execution(102, "SELL", 5, "3", "2026-09-02"),
    )
    usd_facts = (
        execution(201, "BUY", 10, "4", "2026-08-01", trade=usd_trade),
        execution(202, "SELL", 5, "2", "2026-09-02", trade=usd_trade),
    )
    facts = (*eur_facts, *usd_facts)
    declarations = tuple(confirmed(fact) for fact in eur_facts) + tuple(
        confirmed(fact, "USD") for fact in usd_facts
    )
    basis = snapshot(facts, confirmations=declarations, trades=(eur_trade, usd_trade))
    eur = build_report(basis, SEPTEMBER)
    usd = build_report(
        replace(basis, currency=replace(basis.currency, code="USD")),
        replace(SEPTEMBER, report_currency="USD"),
    )
    assert eur.summary.total == "5"
    assert usd.summary.total == "-10"
    assert eur.counts.usable == usd.counts.usable == 1
    assert eur.counts.excluded == usd.counts.excluded == 1
    assert eur.basis.id != usd.basis.id
    assert {item.currency_code for item in eur.items} == {"EUR", "USD"}


def test_foreign_date_only_overlap_blocks_total_and_is_counted_once() -> None:
    facts = (
        execution(101, "BUY", 3, "1", "2026-08-01"),
        execution(102, "SELL", 1, "2", "2026-09-02"),
        execution(103, "SELL", 1, "2", "2026-10-01", zone="Asia/Tokyo"),
    )
    report = build_report(snapshot(facts), SEPTEMBER)
    _identities(report)
    assert report.summary.status == "PARTIAL"
    assert report.summary.subtotal == "1"
    assert report.counts.period_ambiguous == report.counts.unresolved == 1
    assert report.items[1].reasons == ("PERIOD_AMBIGUOUS",)
    assert report.items[1].executed_at is None
    assert report.items[1].executed_on == date(2026, 10, 1)


def test_invalid_date_or_history_remains_visible_with_unknown_money() -> None:
    facts = reference()
    invalid = replace(facts[4], execution_timezone="Imaginary/Zone")
    report = build_report(snapshot((*facts[:4], invalid, facts[5])), SEPTEMBER)
    _identities(report)
    assert report.summary.status == "NOT_COMPUTABLE"
    assert report.counts.period_unknown == 1
    affected = next(item for item in report.items if item.execution_id == invalid.id)
    assert affected.reasons == ("PERIOD_UNKNOWN", "HISTORY_INVALID")
    assert affected.executed_at is None
    assert affected.realized_gross_pnl_delta is None


@pytest.mark.parametrize("problem", ["oversell", "missing_buy", "nonfinite", "missing_position"])
def test_owner_failures_are_data_gaps_without_relaxed_rules(problem: str) -> None:
    facts = reference()[:3]
    trades = (trade_fact(),)
    if problem == "oversell":
        facts = (facts[0], replace(facts[1], quantity=101), facts[2])
    elif problem == "missing_buy":
        facts = facts[1:]
    elif problem == "nonfinite":
        facts = (replace(facts[0], price_per_unit=Decimal("NaN")), *facts[1:])
    else:
        trades = (replace(trades[0], position_id=None),)
    report = build_report(snapshot(facts, trades=trades), SEPTEMBER)
    assert report.summary.status == "NOT_COMPUTABLE"
    assert report.items[-1].reasons == ("HISTORY_INVALID",)
    assert report.items[-1].realized_gross_pnl_delta is None


@pytest.mark.parametrize(
    "minor_unit,total_display,difference", [(2, "0.01", "0.01"), (3, "0.008", "0.000")]
)
def test_backend_display_rounds_sum_after_exact_contributions_and_exposes_difference(
    minor_unit: int,
    total_display: str,
    difference: str,
) -> None:
    facts = (
        execution(101, "BUY", 2, "1", "2026-08-01"),
        execution(102, "SELL", 1, "1.004", "2026-09-02"),
        execution(103, "SELL", 1, "1.004", "2026-09-03"),
    )
    report = build_report(snapshot(facts, minor_unit=minor_unit), SEPTEMBER)
    assert report.summary.total == "0.008"
    assert report.summary.total_display == total_display
    assert report.summary.rounding_difference == difference
    assert report.summary.rounding_difference_display == difference
    assert report.currency.reference_version == "SYNTHETIC-REFERENCE-v1"
    assert report.currency.rounding == "ROUND_HALF_EVEN"
    assert report.currency.minor_unit == minor_unit
    assert [item.realized_gross_pnl_delta for item in report.items] == ["0.004", "0.004"]


def test_half_even_display_normalizes_negative_zero_without_changing_exact_values() -> None:
    assert displayed(Decimal("1.005"), 2) == "1.00"
    assert displayed(Decimal("1.015"), 2) == "1.02"
    assert displayed(Decimal("-0.004"), 2) == "0.00"


def test_repeating_owner_decimals_and_close_residue_are_exact_api_strings() -> None:
    rows = [
        ("BUY", 1, "1"),
        ("BUY", 2, "2"),
        ("SELL", 1, "2"),
        ("BUY", 1, "1"),
        ("SELL", 1, "2"),
        ("SELL", 2, "2"),
    ]
    facts = tuple(
        execution(101 + index, side, quantity, price, f"2026-09-{index + 1:02}")
        for index, (side, quantity, price) in enumerate(rows)
    )
    report = build_report(snapshot(facts), SEPTEMBER)
    assert report.summary.total == "2.000000000000000000000000001"
    assert report.summary.total_display == "2.00"
    assert [item.realized_gross_pnl_delta for item in report.items] == [
        "0.333333333333333333333333333",
        "0.555555555555555555555555556",
        "1.111111111111111111111111112",
    ]
    assert report.items[-1].cost_basis_before_close_reset == "0.000000000000000000000000001"
    assert report.items[-1].cost_basis_after == "0"


def test_sort_and_source_fingerprint_are_stable_between_unchanged_reads() -> None:
    basis = snapshot()
    first = build_report(basis, SEPTEMBER)
    next_read = replace(
        basis,
        read_started_at=RECORDED + timedelta(days=1),
        read_completed_at=RECORDED + timedelta(days=1),
    )
    second = build_report(next_read, SEPTEMBER)
    assert first.basis.id == second.basis.id
    assert first.basis.read_started_at != second.basis.read_started_at
    assert first.items == second.items
    assert first.sources == second.sources
    assert first.basis.knowledge == "CURRENT_EFFECTIVE_FACTS"
    assert asdict(first.filters) == asdict(SEPTEMBER)
    assert (
        first.items
        == build_report(
            replace(basis, executions=tuple(reversed(basis.executions))), SEPTEMBER
        ).items
    )


def test_today_product_name_is_display_only_and_selection_origin_needs_no_learning() -> None:
    basis = snapshot()
    original_trade = basis.trades[0]
    selected_trade = replace(
        original_trade.trade,
        origin=TradeOrigin.WORKSPACE_SELECTION,
        trade_plan_id=UUID(int=11),
        trade_plan_version_id=UUID(int=12),
        product_selection_id=UUID(int=13),
        product_evaluation_id=UUID(int=14),
    )
    changed = replace(
        basis,
        trades=(
            replace(
                original_trade,
                trade=selected_trade,
                product_name="Updated display, no currency evidence",
            ),
        ),
    )
    report = build_report(changed, SEPTEMBER)
    assert report.summary.total == "10.00"
    assert all(item.origin == "WORKSPACE_SELECTION" for item in report.items)
    assert all(
        item.product_name == "Updated display, no currency evidence" for item in report.items
    )
    assert (
        build_report(replace(changed, confirmations=()), SEPTEMBER).summary.status
        == "NOT_COMPUTABLE"
    )


def test_provenance_limit_fails_whole_report_instead_of_silently_truncating(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.features.performance.domain.report.MAX_PROVENANCE_LINKS", 2)
    with pytest.raises(ReportLimitExceeded, match="complete provenance"):
        build_report(snapshot(), SEPTEMBER)


def test_snapshot_must_match_explicit_currency_filter() -> None:
    with pytest.raises(ValueError, match="match the snapshot"):
        build_report(snapshot(), replace(SEPTEMBER, report_currency="USD"))
