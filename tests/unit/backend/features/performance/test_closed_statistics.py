"""Predeclared statistics goldens over real owner projections, never SELL subsets."""

from dataclasses import asdict, replace
from datetime import timedelta
from decimal import ROUND_DOWN, ROUND_HALF_EVEN, Decimal, getcontext, localcontext
from uuid import UUID

import pytest
from tests.unit.backend.features.performance.fixtures import (
    RECORDED,
    SEPTEMBER,
    closed_statistics_snapshot,
    confirmed,
    execution,
    snapshot,
    trade_fact,
)
from tests.unit.backend.features.performance.test_closed_report import OCTOBER

from app.features.performance.domain.closed_models import ClosedTradeReport, ClosedTradeStatistic
from app.features.performance.domain.closed_report import build_closed_report
from app.features.performance.domain.closed_statistics import build_closed_statistics


def _assert_metric(metric: ClosedTradeStatistic, raw: str, display: str) -> None:
    assert isinstance(metric.raw, str)
    assert Decimal(metric.raw) == Decimal(raw)
    assert metric.display == display
    assert metric.reason is None


def _assert_unavailable(report: ClosedTradeReport, reason: str) -> None:
    stats = report.statistics
    assert stats.definition_version == "closed-trade-statistics-v1"
    assert stats.report_basis_id == report.basis.id
    assert stats.report_status == report.summary.status
    assert stats.population == (0 if report.summary.status == "EMPTY" else None)
    for metric in (
        stats.win_rate,
        stats.average_gross_pnl,
        stats.median_gross_pnl,
        stats.gross_profit_factor,
    ):
        assert asdict(metric) == {"raw": None, "display": None, "reason": reason}


def test_independent_four_trade_golden_and_effective_price_correction() -> None:
    facts = closed_statistics_snapshot()
    original = build_closed_report(facts, OCTOBER)
    assert original.summary.total == "250"
    assert (
        original.counts.qualified,
        original.counts.positive,
        original.counts.negative,
        original.counts.neutral,
    ) == (4, 2, 1, 1)
    stats = original.statistics
    assert stats.population == 4
    assert stats.report_status == "COMPLETE"
    assert stats.report_basis_id == original.basis.id
    _assert_metric(stats.win_rate, "50", "50.00")
    _assert_metric(stats.average_gross_pnl, "62.5", "62.50")
    _assert_metric(stats.median_gross_pnl, "50", "50.00")
    _assert_metric(stats.gross_profit_factor, "6", "6.00")

    old = facts.executions[-1]
    correction = replace(
        old,
        id=UUID(int=9001),
        price_per_unit=Decimal("1050"),
        supersedes_execution_id=old.id,
        recorded_at=RECORDED + timedelta(hours=1),
    )
    corrected = build_closed_report(
        replace(facts, executions=(*facts.executions, correction)), OCTOBER
    )
    assert corrected.summary.total == "100"
    assert corrected.counts == original.counts
    _assert_metric(corrected.statistics.win_rate, "50", "50.00")
    _assert_metric(corrected.statistics.average_gross_pnl, "25", "25.00")
    _assert_metric(corrected.statistics.median_gross_pnl, "25", "25.00")
    _assert_metric(corrected.statistics.gross_profit_factor, "3", "3.00")
    assert corrected.statistics.report_basis_id == corrected.basis.id != original.basis.id
    source = next(source for source in corrected.sources if source.execution_id == old.id)
    assert not source.is_effective
    assert source.superseded_by_execution_id == correction.id
    replacement = next(
        source for source in corrected.sources if source.execution_id == correction.id
    )
    assert replacement.is_effective
    assert replacement.supersedes_execution_id == old.id
    assert len(corrected.sources) == len(original.sources) + 1
    assert corrected.sources[0].currency_history == original.sources[0].currency_history


@pytest.mark.parametrize(
    "prices,rate,average,median,factor",
    [
        (("1010", "996", "1000"), "33.33", "2.00", "0.00", "2.50"),
        (("1001.005",), "100.00", "1.00", "1.00", None),
        (("1010", "1020"), "100.00", "15.00", "15.00", None),
        (("998", "996"), "0.00", "-3.00", "-3.00", "0.00"),
        (("1000", "1000", "1000"), "0.00", "0.00", "0.00", None),
        (("1000.004", "999.996"), "50.00", "0.00", "0.00", "1.00"),
    ],
)
def test_odd_even_single_and_signed_zero_population_goldens(
    prices: tuple[str, ...], rate: str, average: str, median: str, factor: str | None
) -> None:
    report = build_closed_report(closed_statistics_snapshot(prices), OCTOBER)
    stats = report.statistics
    assert stats.population == len(prices)
    assert stats.win_rate.display == rate
    assert stats.average_gross_pnl.display == average
    assert stats.median_gross_pnl.display == median
    assert stats.gross_profit_factor.display == factor
    if factor is None:
        assert stats.gross_profit_factor.raw is None
        assert stats.gross_profit_factor.reason == "Nicht definiert: keine Verlusttrades"
    else:
        assert stats.gross_profit_factor.reason is None
    for metric in (stats.win_rate, stats.average_gross_pnl, stats.median_gross_pnl):
        assert isinstance(metric.raw, str)
        assert Decimal(metric.raw).is_finite()
        assert metric.reason is None


def test_unrounded_small_signs_and_neutral_trades_control_rate_and_factor() -> None:
    report = build_closed_report(
        closed_statistics_snapshot(("1000.004", "999.996", "1000")), OCTOBER
    )
    assert [item.realized_gross_pnl_display for item in report.items] == ["0.00"] * 3
    assert [item.classification for item in report.items] == ["POSITIVE", "NEGATIVE", "NEUTRAL"]
    _assert_metric(report.statistics.win_rate, "33.33333333333333333333333333", "33.33")
    _assert_metric(report.statistics.gross_profit_factor, "1", "1.00")


@pytest.mark.parametrize("positive,display", [(1, "3.12"), (3, "9.38")])
def test_rate_display_rounds_exact_half_to_even(positive: int, display: str) -> None:
    prices = ("1001",) * positive + ("1000",) * (32 - positive)
    report = build_closed_report(closed_statistics_snapshot(prices), OCTOBER)
    assert report.statistics.win_rate.display == display


@pytest.mark.parametrize(
    "price,raw,display", [("1001.005", "1.005", "1.00"), ("1001.015", "1.015", "1.02")]
)
def test_profit_factor_display_rounds_half_to_even(price: str, raw: str, display: str) -> None:
    report = build_closed_report(closed_statistics_snapshot((price, "999")), OCTOBER)
    _assert_metric(report.statistics.gross_profit_factor, raw, display)


@pytest.mark.parametrize(
    "currency,minor_unit,price,raw,display",
    [("JPY", 0, "1002.5", "2.5", "2"), ("KWD", 3, "1001.2345", "1.2345", "1.234")],
)
def test_money_statistics_use_existing_currency_reference_minor_units(
    currency: str, minor_unit: int, price: str, raw: str, display: str
) -> None:
    basis = closed_statistics_snapshot((price,))
    basis = replace(
        basis,
        confirmations=tuple(
            replace(value, currency_code=currency) for value in basis.confirmations
        ),
        currency=replace(basis.currency, code=currency, minor_unit=minor_unit),
    )
    report = build_closed_report(basis, replace(OCTOBER, report_currency=currency))
    _assert_metric(report.statistics.average_gross_pnl, raw, display)
    _assert_metric(report.statistics.median_gross_pnl, raw, display)
    assert report.statistics.win_rate.display == "100.00"


@pytest.mark.parametrize("problem", ["missing", "mixed"])
def test_incomplete_money_evidence_hides_all_statistics_but_preserves_known_subtotal(
    problem: str,
) -> None:
    basis = closed_statistics_snapshot(("1100", "950"))
    declarations = (
        (basis.confirmations[0],)
        if problem == "missing"
        else (*basis.confirmations, confirmed(basis.executions[-1], "USD"))
    )
    report = build_closed_report(replace(basis, confirmations=declarations), OCTOBER)
    assert report.summary.status == "PARTIAL"
    assert report.summary.total is None
    assert report.summary.subtotal == "100"
    assert report.counts.positive == report.counts.qualified == 1
    assert report.counts.monetary_unresolved == 1
    _assert_unavailable(report, "Berichtsgrundlage unvollständig")


def test_not_computable_and_empty_have_distinct_reasons_without_artificial_statistics() -> None:
    basis = replace(closed_statistics_snapshot(), confirmations=())
    unknown = build_closed_report(basis, OCTOBER)
    empty = build_closed_report(basis, SEPTEMBER)
    assert unknown.summary.status == "NOT_COMPUTABLE"
    assert unknown.summary.total is None
    assert unknown.counts.qualified == 0
    _assert_unavailable(unknown, "Berichtsgrundlage unvollständig")
    assert empty.summary.status == "EMPTY"
    assert empty.summary.total == "0"
    _assert_unavailable(empty, "Keine abgeschlossenen Trades in der Auswahl")


def test_mean_reuses_original_summary_sum_in_its_finite_decimal_operation_order() -> None:
    trades = (trade_fact(1), trade_fact(2), trade_fact(3))
    facts = tuple(
        fact
        for index, (trade, buy, sell) in enumerate(
            zip(trades, ("1", "1000", "1"), ("1000", "1", "1.4"), strict=True)
        )
        for fact in (
            execution(101 + index * 100, "BUY", 1, buy, "2026-08-01", trade=trade),
            execution(102 + index * 100, "SELL", 1, sell, "2026-10-03", trade=trade),
        )
    )
    with localcontext() as context:
        context.prec = 3
        context.rounding = ROUND_HALF_EVEN
        report = build_closed_report(snapshot(facts, trades=trades), OCTOBER)
    assert [item.realized_gross_pnl for item in report.items] == ["999", "-999", "0.4"]
    assert report.summary.total == "0.4"
    _assert_metric(report.statistics.average_gross_pnl, "0.133", "0.13")
    # Summing the sorted median inputs at precision 3 would instead yield zero.
    _assert_metric(report.statistics.median_gross_pnl, "0.4", "0.40")


def test_statistics_use_a_local_context_without_mutating_precision_rounding_or_flags() -> None:
    outer = getcontext().copy()
    with localcontext() as context:
        context.prec = 17
        context.rounding = ROUND_DOWN
        context.clear_flags()
        report = build_closed_report(closed_statistics_snapshot(("1001", "1000", "1000")), OCTOBER)
        assert context.prec == 17
        assert context.rounding == ROUND_DOWN
        assert not any(context.flags.values())
        _assert_metric(report.statistics.win_rate, "33.333333333333333", "33.33")
        _assert_metric(report.statistics.average_gross_pnl, "0.33333333333333333", "0.33")
    assert getcontext().prec == outer.prec
    assert getcontext().rounding == outer.rounding
    assert getcontext().flags == outer.flags
    assert getcontext().traps == outer.traps


@pytest.mark.parametrize("raw", [None, "NaN", "Infinity"])
def test_missing_or_nonfinite_qualified_amount_is_never_replaced_with_zero(raw: str | None) -> None:
    report = build_closed_report(closed_statistics_snapshot(("1100",)), OCTOBER)
    with pytest.raises(ValueError, match="require"):
        build_closed_statistics(
            summary=report.summary,
            counts=report.counts,
            items=(replace(report.items[0], realized_gross_pnl=raw),),
            minor_unit=report.currency.minor_unit,
            report_basis_id=report.basis.id,
        )


def test_missing_existing_total_is_not_reconstructed_from_trade_amounts() -> None:
    report = build_closed_report(closed_statistics_snapshot(), OCTOBER)
    with pytest.raises(ValueError, match="qualified amounts"):
        build_closed_statistics(
            summary=replace(report.summary, total=None),
            counts=report.counts,
            items=report.items,
            minor_unit=report.currency.minor_unit,
            report_basis_id=report.basis.id,
        )


def test_statistics_are_reproducible_and_leave_preimplementation_source_fingerprint_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with localcontext() as context:
        context.prec = 28
        context.rounding = ROUND_HALF_EVEN
        basis = snapshot()
        first = build_closed_report(basis, OCTOBER)
        second = build_closed_report(
            replace(
                basis,
                executions=tuple(reversed(basis.executions)),
                read_started_at=RECORDED + timedelta(days=1),
                read_completed_at=RECORDED + timedelta(days=1),
            ),
            OCTOBER,
        )
        # Captured from unmodified b49e87e before the statistics implementation.
        assert first.basis.id == "ffb7c92a677b6d6f685388638257aa0a433c12dd9b523f99742b080ead9668b5"
        assert first.statistics == second.statistics
        assert first.statistics.report_basis_id == first.basis.id == second.basis.id
        assert first.items == second.items
        assert first.sources == second.sources
        monkeypatch.setattr(
            "app.features.performance.domain.closed_statistics.DEFINITION_VERSION",
            "synthetic-next-statistics-definition",
        )
        next_definition = build_closed_report(basis, OCTOBER)
        assert next_definition.basis.id == first.basis.id
        assert next_definition.statistics.definition_version != first.statistics.definition_version
        assert next_definition.items == first.items
        assert next_definition.sources == first.sources
