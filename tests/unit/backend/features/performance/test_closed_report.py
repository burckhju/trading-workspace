"""Independent full-exit cohort oracles, separate from period SELL arithmetic."""

from dataclasses import asdict, replace
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from tests.unit.backend.features.performance.fixtures import (
    RECORDED,
    SEPTEMBER,
    WORKSPACE,
    confirmed,
    execution,
    reference,
    snapshot,
    trade_fact,
)

from app.features.performance.domain.closed_models import ClosedTradeReport
from app.features.performance.domain.closed_report import build_closed_report
from app.features.performance.domain.models import (
    Confirmation,
    ExecutionFact,
    ReportSnapshot,
    TradeFact,
)
from app.features.performance.domain.report import ReportLimitExceeded, build_report
from app.features.trade_position.domain.projector import PositionProjector

OCTOBER = replace(SEPTEMBER, from_date=date(2026, 10, 1), to_date=date(2026, 10, 31))


def _identities(report: ClosedTradeReport) -> None:
    counts = report.counts
    assert counts.examined == len(report.items) == len({item.trade_id for item in report.items})
    assert counts.examined == (
        counts.cancelled
        + counts.history_unresolved
        + counts.open
        + counts.outside_period
        + counts.other_currency
        + counts.period_unresolved
        + counts.monetary_unresolved
        + counts.qualified
    )
    assert counts.qualified == counts.positive + counts.negative + counts.neutral
    assert counts.unresolved == (
        counts.history_unresolved + counts.period_unresolved + counts.monetary_unresolved
    )
    assert counts.in_period == counts.monetary_unresolved + counts.qualified
    assert len(report.sources) == len({source.execution_id for source in report.sources})
    assert all(
        item.realized_gross_pnl is None and item.classification is None
        for item in report.items
        if item.group != "QUALIFIED"
    )


def _pair(
    number: int, price: str = "6", *, quantity: int = 10
) -> tuple[TradeFact, tuple[ExecutionFact, ...]]:
    trade = trade_fact(number)
    return trade, (
        execution(number * 100 + 1, "BUY", 10, "5", "2026-08-01", trade=trade),
        execution(number * 100 + 2, "SELL", quantity, price, "2026-10-03", trade=trade),
    )


def _cohort(*, include_unknown: bool = False, corrected: bool = False) -> ReportSnapshot:
    facts = list(reference())
    declarations = [confirmed(facts[0])]
    trades = [trade_fact()]
    for number, price, currency in (
        (2, "4", "EUR"),
        (3, "5", "EUR"),
        (5, "6", "USD"),
        (6, "7", "EUR"),
    ):
        trade, pair = _pair(number, price, quantity=5 if number == 6 else 10)
        trades.append(trade)
        facts.extend(pair)
        declarations.append(confirmed(pair[0], currency))
    if include_unknown:
        trade, pair = _pair(4)
        trades.append(trade)
        facts.extend(pair)
    if corrected:
        facts.append(
            replace(
                facts[4],
                id=UUID(int=9001),
                price_per_unit=Decimal("3.00"),
                supersedes_execution_id=facts[4].id,
                recorded_at=RECORDED + timedelta(hours=1),
            )
        )
    return snapshot(tuple(facts), confirmations=tuple(declarations), trades=tuple(trades))


def test_reference_closure_selects_one_lifetime_result_and_keeps_earlier_sell_meaning() -> None:
    facts = reference()
    basis = snapshot(confirmations=(confirmed(facts[0]),))
    september = build_closed_report(basis, SEPTEMBER)
    october = build_closed_report(basis, OCTOBER)
    for report in (september, october):
        _identities(report)
    assert september.summary.status == "EMPTY"
    assert september.summary.total == "0"
    assert september.counts.outside_period == 1
    assert october.definition_version == "closed-trade-gross-v1"
    assert october.summary.status == "COMPLETE"
    assert october.summary.total == october.summary.total_display == "50.00"
    assert october.counts.qualified == october.counts.positive == october.counts.in_period == 1
    item = october.items[0]
    assert item.origin == "EXTERNAL"
    assert item.group == "QUALIFIED"
    assert item.closing_execution_id == facts[-1].id
    assert item.closing_time is not None
    assert item.closing_time.executed_at is None
    assert item.closing_time.time_precision == "DATE_ONLY"
    assert item.closing_time.executed_on == date(2026, 10, 3)
    assert item.classification == "POSITIVE"
    assert item.currency_confirmation_ids == (confirmed(facts[0]).id,)
    assert item.execution_ids == item.effective_execution_ids == tuple(fact.id for fact in facts)
    assert [part.realized_gross_pnl_delta for part in item.sell_contributions] == [
        "10.00",
        "30.00",
        "-20.00",
        "30.00",
    ]
    assert [part.period_status for part in item.sell_contributions] == ["OUTSIDE_PERIOD"] * 3 + [
        "IN_PERIOD"
    ]
    assert all(part.status == "USABLE" for part in item.sell_contributions)
    assert [part.is_closing for part in item.sell_contributions] == [False, False, False, True]
    assert item.sell_contributions[-1].cost_basis_execution_ids == tuple(
        fact.id for fact in facts[:-1]
    )
    assert item.sell_contributions[-1].cost_basis_before == "180.00"
    assert item.sell_contributions[-1].cost_basis_before_close_reset == "0.00"
    assert len(october.sources) == 6
    assert sum(source.currency_confirmation is not None for source in october.sources) == 1
    assert all(source.currency_resolution.source == "PRIOR_BUYS" for source in october.sources[1:])
    # Existing report still selects SELL contributions, not the full trade.
    assert build_report(basis, SEPTEMBER).summary.total == "10.00"
    assert build_report(basis, OCTOBER).summary.total == "30.00"
    assert build_report(basis, SEPTEMBER).definition_version == "realized-gross-sell-v2"


@pytest.mark.parametrize("corrected,amount", [(False, "40.00"), (True, "60.00")])
@pytest.mark.parametrize("include_unknown", [False, True])
def test_independent_reference_cohort_counts_and_complete_trade_only_subtotal(
    corrected: bool, amount: str, include_unknown: bool
) -> None:
    report = build_closed_report(
        _cohort(include_unknown=include_unknown, corrected=corrected), OCTOBER
    )
    _identities(report)
    assert report.counts.qualified == 3
    assert report.counts.positive == report.counts.negative == report.counts.neutral == 1
    assert report.counts.other_currency == report.counts.open == 1
    assert report.counts.monetary_unresolved == int(include_unknown)
    assert report.counts.in_period == 3 + int(include_unknown)
    assert report.summary.status == ("PARTIAL" if include_unknown else "COMPLETE")
    assert report.summary.total == (None if include_unknown else amount)
    assert report.summary.subtotal == (amount if include_unknown else None)
    assert len({item.product_name for item in report.items}) == 1


def test_only_unknown_only_measured_zero_and_no_selection_are_distinct() -> None:
    trade, facts = _pair(4)
    unknown = build_closed_report(snapshot(facts, confirmations=(), trades=(trade,)), OCTOBER)
    zero_trade, zero_facts = _pair(3, "5")
    zero = build_closed_report(snapshot(zero_facts, trades=(zero_trade,)), OCTOBER)
    empty = build_closed_report(replace(snapshot(()), trades=()), OCTOBER)
    for report in (unknown, zero, empty):
        _identities(report)
    assert unknown.summary.status == "NOT_COMPUTABLE"
    assert unknown.summary.total is unknown.summary.subtotal is None
    assert unknown.items[0].classification is None
    assert zero.summary.status == "COMPLETE"
    assert zero.summary.total == "0"
    assert zero.counts.neutral == 1
    assert empty.summary.status == "EMPTY"
    assert empty.summary.total == "0"
    assert empty.counts.examined == 0


def test_partial_zero_does_not_disappear_and_unqualified_trade_never_adds_known_part() -> None:
    zero_trade, zero_facts = _pair(3, "5")
    mixed = reference()
    confirmations = (confirmed(zero_facts[0]), confirmed(mixed[0]), confirmed(mixed[1], "USD"))
    report = build_closed_report(
        snapshot(
            (*mixed, *zero_facts), confirmations=confirmations, trades=(trade_fact(), zero_trade)
        ),
        OCTOBER,
    )
    _identities(report)
    assert report.summary.status == "PARTIAL"
    assert report.summary.total is None
    assert report.summary.subtotal == "0"
    assert report.counts.neutral == report.counts.monetary_unresolved == 1
    mixed_item = next(item for item in report.items if item.trade_id == mixed[0].trade_id)
    assert mixed_item.realized_gross_pnl is None
    assert mixed_item.classification is None
    assert mixed_item.reasons == ("CURRENCY_MIXED",)
    assert mixed_item.sell_contributions[0].realized_gross_pnl_delta is None
    assert mixed_item.sell_contributions[-1].realized_gross_pnl_delta == "30.00"
    # A separately usable closing SELL is not sufficient for the whole trade.
    assert (
        build_report(snapshot(mixed, confirmations=confirmations[1:]), OCTOBER).summary.total
        == "30.00"
    )


@pytest.mark.parametrize("change", ["price", "date", "quantity", "currency"])
def test_current_corrections_change_basis_without_erasing_sources(change: str) -> None:
    facts = reference()
    original = snapshot(facts, confirmations=(confirmed(facts[0]),))
    before = build_closed_report(original, OCTOBER)
    declarations = original.confirmations
    if change == "currency":
        declarations += (
            replace(
                declarations[0],
                id=UUID(int=90000),
                currency_code="USD",
                supersedes_confirmation_id=declarations[0].id,
                confirmed_at=RECORDED + timedelta(hours=1),
            ),
        )
        changed = replace(original, confirmations=declarations)
    else:
        old = facts[4] if change == "price" else facts[-1]
        replacement = replace(
            old,
            id=UUID(int=90001),
            supersedes_execution_id=old.id,
            recorded_at=RECORDED + timedelta(hours=1),
        )
        if change == "price":
            replacement = replace(replacement, price_per_unit=Decimal("3.00"))
        elif change == "quantity":
            replacement = replace(replacement, quantity=59)
        else:
            moved = execution(90001, "SELL", 60, "3.50", "2026-09-30")
            replacement = replace(
                replacement, executed_on=moved.executed_on, executed_at=moved.executed_at
            )
        changed = replace(original, executions=(*facts, replacement))
    after = build_closed_report(changed, OCTOBER)
    _identities(after)
    assert before.summary.total == "50.00"
    assert before.basis.id != after.basis.id
    assert all(
        source.execution_id in {value.execution_id for value in after.sources}
        for source in before.sources
    )
    if change == "price":
        assert after.summary.total == "70.00"
        assert after.items[0].closing_execution_id == facts[-1].id
        old_source = next(value for value in after.sources if value.execution_id == facts[4].id)
        assert not old_source.is_effective
        assert old_source.price_per_unit == "2.50"
        assert old_source.superseded_by_execution_id == replacement.id
        new_source = next(value for value in after.sources if value.execution_id == replacement.id)
        assert new_source.currency_confirmation is None
        assert new_source.currency_resolution.currency_code == "EUR"
        assert build_report(changed, SEPTEMBER).summary.total == "30.00"
        assert build_report(changed, OCTOBER).summary.total == "30.00"
    elif change == "quantity":
        assert after.counts.open == 1
        assert after.items[0].closing_execution_id is None
        assert after.summary.status == "EMPTY"
    elif change == "date":
        assert after.counts.outside_period == 1
        assert build_closed_report(changed, SEPTEMBER).summary.total == "50.00"
    else:
        assert after.counts.other_currency == 1
        assert after.summary.status == "EMPTY"
        assert len(after.sources[0].currency_history) == 2
        assert after.sources[0].currency_confirmation == declarations[-1]
        usd = build_closed_report(
            replace(changed, currency=replace(changed.currency, code="USD")),
            replace(OCTOBER, report_currency="USD"),
        )
        assert usd.summary.total == "50.00"


def test_open_trade_keeps_valid_sells_without_counting_any_full_exit() -> None:
    report = build_closed_report(snapshot(reference()[:-1]), SEPTEMBER)
    _identities(report)
    assert report.counts.open == 1
    assert report.summary.status == "EMPTY"
    assert report.items[0].closing_execution_id is None
    assert report.items[0].sell_contributions[-1].open_quantity_after == 60
    assert build_report(snapshot(reference()[:-1]), SEPTEMBER).summary.total == "10.00"


@pytest.mark.parametrize(
    "problem",
    [
        "empty",
        "missing_buy",
        "oversell",
        "missing_position",
        "wrong_product",
        "nonfinite",
        "buy_after_close",
        "invalid_zone",
        "incomplete_date",
    ],
)
def test_invalid_history_is_relevant_even_when_old_or_last_sell_has_other_currency(
    problem: str,
) -> None:
    trade, facts = _pair(2)
    if problem == "empty":
        facts = ()
    elif problem == "missing_buy":
        facts = facts[1:]
    elif problem == "oversell":
        facts = (facts[0], replace(facts[1], quantity=11))
    elif problem == "missing_position":
        trade = replace(trade, position_id=None)
    elif problem == "wrong_product":
        facts = (facts[0], replace(facts[1], product_id=UUID(int=999)))
    elif problem == "nonfinite":
        facts = (replace(facts[0], price_per_unit=Decimal("NaN")), facts[1])
    elif problem == "buy_after_close":
        facts += (execution(209, "BUY", 1, "2", "2026-10-04", trade=trade),)
    elif problem == "invalid_zone":
        facts = (facts[0], replace(facts[1], execution_timezone="Imaginary/Zone"))
    else:
        facts = (facts[0], replace(facts[1], execution_timezone=None))
    basis = snapshot(
        facts, confirmations=tuple(confirmed(fact, "USD") for fact in facts), trades=(trade,)
    )
    # Even a report a decade after all known timestamps cannot infer a safe exit.
    report = build_closed_report(
        basis, replace(OCTOBER, from_date=date(2040, 10, 1), to_date=date(2040, 10, 31))
    )
    _identities(report)
    assert report.counts.history_unresolved == report.counts.unresolved == 1
    assert report.counts.open == report.counts.other_currency == report.counts.outside_period == 0
    assert report.summary.status == "NOT_COMPUTABLE"
    assert report.items[0].reasons == ("HISTORY_INVALID",)
    assert report.items[0].closing_execution_id is None
    assert report.items[0].sell_contributions == ()


@pytest.mark.parametrize("problem", ["missing_predecessor", "fork", "cycle", "self"])
def test_malformed_supersession_graph_never_proves_a_plausible_current_closure(
    problem: str,
) -> None:
    trade, facts = _pair(2)
    if problem == "missing_predecessor":
        facts = (facts[0], replace(facts[1], supersedes_execution_id=UUID(int=990)))
    elif problem == "self":
        facts = (facts[0], replace(facts[1], supersedes_execution_id=facts[1].id))
    elif problem == "fork":
        facts += (
            replace(facts[0], id=UUID(int=211), quantity=5, supersedes_execution_id=facts[0].id),
            replace(facts[0], id=UUID(int=212), quantity=5, supersedes_execution_id=facts[0].id),
        )
    else:
        facts += (
            replace(facts[0], id=UUID(int=211), supersedes_execution_id=UUID(int=212)),
            replace(facts[0], id=UUID(int=212), supersedes_execution_id=UUID(int=211)),
        )
    report = build_closed_report(snapshot(facts, trades=(trade,)), OCTOBER)
    _identities(report)
    assert report.counts.history_unresolved == 1
    assert report.summary.status == "NOT_COMPUTABLE"
    assert report.items[0].realized_gross_pnl is None
    assert len(report.sources) == len(facts)


def test_cancelled_trade_wins_precedence_over_invalid_history_and_missing_currency() -> None:
    trade = trade_fact()
    cancelled = replace(
        trade,
        trade=replace(trade.trade, cancelled_at=RECORDED, cancellation_reason="Synthetic misentry"),
        position_id=None,
    )
    facts = reference()[1:]
    report = build_closed_report(snapshot(facts, confirmations=(), trades=(cancelled,)), OCTOBER)
    _identities(report)
    assert report.counts.cancelled == 1
    assert report.counts.unresolved == 0
    assert report.summary.status == "EMPTY"
    assert report.items[0].reasons == ("TRADE_CANCELLED",)
    assert report.items[0].sell_contributions == ()
    assert len(report.sources) == len(facts)


def test_reliably_outside_period_wins_over_unknown_or_mixed_currency() -> None:
    facts = reference()
    for confirmations in ((), (confirmed(facts[0]), confirmed(facts[-1], "USD"))):
        report = build_closed_report(snapshot(facts, confirmations=confirmations), SEPTEMBER)
        _identities(report)
        assert report.counts.outside_period == 1
        assert report.counts.unresolved == 0
        assert report.summary.status == "EMPTY"


@pytest.mark.parametrize(
    "currency,expected_group",
    [("EUR", "PERIOD_UNRESOLVED"), ("USD", "OTHER_CURRENCY"), (None, "PERIOD_UNRESOLVED")],
)
@pytest.mark.parametrize("unknown", [False, True])
def test_uncertain_period_is_excluded_only_by_a_fully_qualified_other_currency(
    currency: str | None, expected_group: str, unknown: bool
) -> None:
    day, zone = ("2011-12-30", "Pacific/Apia") if unknown else ("2026-10-01", "Asia/Tokyo")
    facts = (
        execution(101, "BUY", 1, "2", "2010-08-01"),
        execution(102, "SELL", 1, "3", day, zone=zone),
    )
    confirmations = (confirmed(facts[0], currency),) if currency else ()
    filters = (
        replace(
            SEPTEMBER,
            from_date=date(2011, 12, 1),
            to_date=date(2011, 12, 31),
            report_timezone="UTC",
        )
        if unknown
        else SEPTEMBER
    )
    report = build_closed_report(snapshot(facts, confirmations=confirmations), filters)
    _identities(report)
    assert report.items[0].group == expected_group
    assert report.items[0].period_status == ("PERIOD_UNKNOWN" if unknown else "PERIOD_AMBIGUOUS")
    assert report.items[0].closing_time is not None
    assert report.items[0].closing_time.executed_at is None
    assert report.counts.in_period == 0
    assert report.summary.status == ("EMPTY" if currency == "USD" else "NOT_COMPUTABLE")


@pytest.mark.parametrize("day,hours", [("2026-03-29", 23), ("2026-10-25", 25)])
def test_whole_date_only_dst_day_is_contained_without_exposing_its_anchor(
    day: str, hours: int
) -> None:
    facts = (execution(101, "BUY", 1, "2", "2026-01-01"), execution(102, "SELL", 1, "3", day))
    filters = replace(SEPTEMBER, from_date=date.fromisoformat(day), to_date=date.fromisoformat(day))
    report = build_closed_report(snapshot(facts), filters)
    assert report.summary.total == "1"
    closing = report.items[0].closing_time
    assert closing is not None
    assert closing.executed_at is None
    assert closing.possible_end_at - closing.possible_start_at == timedelta(hours=hours)


@pytest.mark.parametrize(
    "instant,group",
    [
        ("2026-09-30T21:59:59.999999Z", "OUTSIDE_PERIOD"),
        ("2026-09-30T22:00:00Z", "QUALIFIED"),
        ("2026-10-31T23:00:00Z", "OUTSIDE_PERIOD"),
    ],
)
def test_closing_timestamp_obeys_explicit_report_zone_half_open_interval(
    instant: str, group: str
) -> None:
    facts = (
        execution(101, "BUY", 1, "2", "2026-08-01"),
        replace(
            execution(102, "SELL", 1, "3", "2026-10-03", zone=None),
            executed_at=datetime.fromisoformat(instant),
        ),
    )
    report = build_closed_report(snapshot(facts), OCTOBER)
    assert report.items[0].group == group
    assert report.items[0].closing_time.executed_at == datetime.fromisoformat(instant)


@pytest.mark.parametrize(
    "price,raw,classification",
    [("1.004", "0.004", "POSITIVE"), ("0.996", "-0.004", "NEGATIVE"), ("1", "0", "NEUTRAL")],
)
def test_sign_uses_exact_owner_value_even_when_display_is_zero(
    price: str, raw: str, classification: str
) -> None:
    facts = (
        execution(101, "BUY", 1, "1", "2026-08-01"),
        execution(102, "SELL", 1, price, "2026-10-03"),
    )
    report = build_closed_report(snapshot(facts), OCTOBER)
    _identities(report)
    assert report.summary.status == "COMPLETE"
    assert report.summary.total == raw
    assert report.summary.total_display == "0.00"
    assert report.items[0].classification == classification


def test_summed_exact_trade_values_round_once_with_visible_row_rounding_difference() -> None:
    trades = (trade_fact(), trade_fact(2))
    facts = tuple(
        fact
        for index, trade in enumerate(trades)
        for fact in (
            execution(101 + index * 100, "BUY", 1, "1", "2026-08-01", trade=trade),
            execution(102 + index * 100, "SELL", 1, "1.004", "2026-10-03", trade=trade),
        )
    )
    report = build_closed_report(snapshot(facts, trades=trades), OCTOBER)
    assert report.summary.total == "0.008"
    assert report.summary.total_display == report.summary.rounding_difference == "0.01"
    assert [item.realized_gross_pnl_display for item in report.items] == ["0.00", "0.00"]
    assert report.counts.positive == 2


def test_full_owner_precision_and_close_residue_are_consumed_without_new_arithmetic() -> None:
    rows = [
        ("BUY", 1, "1"),
        ("BUY", 2, "2"),
        ("SELL", 1, "2"),
        ("BUY", 1, "1"),
        ("SELL", 1, "2"),
        ("SELL", 2, "2"),
    ]
    facts = tuple(
        execution(101 + index, side, quantity, price, f"2026-10-{index + 1:02}")
        for index, (side, quantity, price) in enumerate(rows)
    )
    basis = snapshot(facts)
    owner = PositionProjector.project_with_trace(
        id=basis.trades[0].position_id,
        trade=basis.trades[0].trade,
        executions=[fact.to_domain() for fact in facts],
    )
    report = build_closed_report(basis, OCTOBER)
    assert (
        report.items[0].realized_gross_pnl
        == str(owner.position.realized_gross_pnl)
        == "2.000000000000000000000000001"
    )
    assert (
        report.items[0].sell_contributions[-1].cost_basis_before_close_reset
        == "0.000000000000000000000000001"
    )
    assert report.items[0].sell_contributions[-1].cost_basis_after == "0"


@pytest.mark.parametrize("problem", ["workspace", "trade", "source", "duplicate_root"])
def test_unqualified_currency_declaration_cannot_prove_money(problem: str) -> None:
    facts = reference()
    declarations: tuple[Confirmation, ...] = (confirmed(facts[0]),)
    if problem == "workspace":
        declarations = (replace(declarations[0], workspace_id=UUID(int=99)),)
    elif problem == "trade":
        declarations = (replace(declarations[0], trade_id=UUID(int=99)),)
    elif problem == "source":
        declarations = (replace(declarations[0], source="CURRENT_LISTING"),)
    else:
        declarations += (replace(declarations[0], id=UUID(int=99)),)
    report = build_closed_report(snapshot(facts, confirmations=declarations), OCTOBER)
    assert report.counts.monetary_unresolved == 1
    assert report.summary.status == "NOT_COMPUTABLE"


def test_same_product_and_duplicate_trade_rows_do_not_duplicate_trade_identity() -> None:
    first, first_facts = _pair(2, "6")
    second, second_facts = _pair(3, "4")
    second = replace(second, trade=replace(second.trade, product_id=first.trade.product_id))
    second_facts = tuple(replace(fact, product_id=first.trade.product_id) for fact in second_facts)
    report = build_closed_report(
        snapshot((*first_facts, *second_facts), trades=(first, second, first)), OCTOBER
    )
    _identities(report)
    assert report.counts.examined == report.counts.qualified == 2
    assert report.counts.positive == report.counts.negative == 1
    assert report.summary.total == "0"


def test_foreign_workspace_facts_never_enter_examined_count_or_provenance() -> None:
    foreign, facts = _pair(2)
    foreign = replace(foreign, trade=replace(foreign.trade, workspace_id=UUID(int=999)))
    report = build_closed_report(
        snapshot((*reference(), *facts), trades=(trade_fact(), foreign)), OCTOBER
    )
    _identities(report)
    assert report.counts.examined == 1
    assert report.summary.total == "50.00"
    assert all(source.trade_id == trade_fact().trade.id for source in report.sources)
    assert report.sources[0].currency_confirmation.workspace_id == WORKSPACE


def test_current_fingerprint_is_stable_after_unchanged_reads_and_binds_selection() -> None:
    basis = snapshot()
    first = build_closed_report(basis, OCTOBER)
    next_read = replace(
        basis,
        read_started_at=RECORDED + timedelta(days=1),
        read_completed_at=RECORDED + timedelta(days=1),
    )
    second = build_closed_report(next_read, OCTOBER)
    assert first.basis.id == second.basis.id
    assert first.items == second.items
    assert first.sources == second.sources
    assert first.basis.read_started_at != second.basis.read_started_at
    assert first.basis.knowledge == "CURRENT_EFFECTIVE_FACTS"
    assert first.basis.id != build_closed_report(basis, SEPTEMBER).basis.id
    assert first.basis.id != build_report(basis, OCTOBER).basis.id
    assert asdict(first.filters) == asdict(OCTOBER)
    assert (
        build_closed_report(
            replace(basis, executions=tuple(reversed(basis.executions))), OCTOBER
        ).basis.id
        == first.basis.id
    )


@pytest.mark.parametrize("limit", [2, 20, 41, 56])
def test_complete_provenance_budget_includes_row_and_contribution_edges(
    limit: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.features.performance.domain.closed_report.MAX_PROVENANCE_LINKS", limit)
    with pytest.raises(ReportLimitExceeded, match="complete provenance"):
        build_closed_report(snapshot(), OCTOBER)


def test_snapshot_currency_must_equal_explicit_filter() -> None:
    with pytest.raises(ValueError, match="match the snapshot"):
        build_closed_report(snapshot(), replace(OCTOBER, report_currency="USD"))
