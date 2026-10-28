"""Independent money oracles for qualified historical currencies and preserved locks."""

from dataclasses import asdict, replace
from datetime import UTC, date, datetime, timedelta
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
from tests.unit.backend.features.trade_position.currency_evidence_fixtures import (
    FRANKFURT,
    XETRA,
    document,
    historical,
    listing,
)

from app.features.performance.domain.closed_report import build_closed_report
from app.features.performance.domain.report import build_report

OCTOBER = replace(SEPTEMBER, from_date=date(2026, 10, 1), to_date=date(2026, 10, 28))
LIFETIME = replace(SEPTEMBER, from_date=date(2026, 1, 1), to_date=date(2026, 12, 31))


def evidence_snapshot(facts=None, *, evidence=None, confirmations=(), trades=None):
    source = historical(trade_fact().trade)
    return replace(
        snapshot(facts, confirmations=confirmations, trades=trades),
        currency_evidence=(source,) if evidence is None else evidence,
    )


def test_eur_buys_partial_sales_and_rebuy_use_existing_owner_average_cost():
    source = evidence_snapshot()
    report = build_report(source, LIFETIME)
    assert report.summary.status == "COMPLETE"
    assert report.summary.total_display == "50.00"
    assert report.counts.usable == report.counts.in_period == 4
    assert report.counts.unresolved == 0
    assert [Decimal(item.realized_gross_pnl_delta) for item in report.items] == [
        Decimal("10"),
        Decimal("30"),
        Decimal("-20"),
        Decimal("30"),
    ]
    assert [Decimal(item.average_cost_per_unit) for item in report.items] == [
        Decimal("2"),
        Decimal("2"),
        Decimal("3"),
        Decimal("3"),
    ]
    assert [Decimal(item.cost_basis_after) for item in report.items] == [
        Decimal("160"),
        Decimal("100"),
        Decimal("180"),
        Decimal("0"),
    ]
    assert report.items[-1].open_quantity_after == 0
    assert all(item.currency_confirmation_ids == () for item in report.items)
    assert all(item.currency_confirmation is None for item in report.sources)
    assert all(item.currency_resolution.source == "HISTORICAL_LISTINGS" for item in report.sources)
    assert all(
        item.currency_resolution.evidence_ids == (source.currency_evidence[0].id,)
        for item in report.sources
    )


def test_period_sell_and_complete_trade_reports_share_provenance_but_keep_their_meanings():
    source = evidence_snapshot()
    september = build_report(source, SEPTEMBER)
    october = build_report(source, OCTOBER)
    completed = build_closed_report(source, OCTOBER)
    assert september.counts.usable == 2
    assert september.summary.total_display == "10.00"
    assert october.counts.usable == 1
    assert october.summary.total_display == "30.00"
    assert completed.counts.qualified == 1
    assert completed.summary.total_display == "50.00"
    assert completed.items[0].group == "QUALIFIED"
    assert completed.items[0].currency_confirmation_ids == ()
    assert [item.currency_resolution for item in completed.sources] == [
        item.currency_resolution for item in october.sources
    ]


def test_exact_execution_documents_qualify_every_required_buy_and_sale_without_new_confirmations():
    facts = reference()
    evidence = tuple(
        document(trade_fact().trade, fact.id, 9000 + index) for index, fact in enumerate(facts)
    )
    report = build_report(evidence_snapshot(evidence=evidence), LIFETIME)
    assert report.summary.status == "COMPLETE"
    assert report.summary.total_display == "50.00"
    assert all(item.currency_resolution.source == "EXECUTION_DOCUMENT" for item in report.sources)
    assert all(item.currency_confirmation is None for item in report.sources)


@pytest.mark.parametrize("kind", ["absent", "today_only", "partial", "unknown_code", "mixed"])
def test_previous_currency_gaps_remain_noncomputable_without_complete_historical_proof(kind):
    historical_source = historical(trade_fact().trade)
    sources = {
        "absent": (),
        "today_only": (
            replace(
                historical_source,
                valid_from=RECORDED,
                valid_to=RECORDED + timedelta(days=1),
            ),
        ),
        "partial": (replace(historical_source, complete_listing_set=False),),
        "unknown_code": (
            replace(historical_source, listings=(listing(), listing(FRANKFURT, None))),
        ),
        "mixed": (replace(historical_source, listings=(listing(), listing(FRANKFURT, "USD"))),),
    }
    basis = evidence_snapshot(evidence=sources[kind])
    report = build_report(basis, OCTOBER)
    completed = build_closed_report(basis, OCTOBER)
    assert report.counts.usable == 0
    assert report.counts.unresolved == 1
    assert report.summary.status == "NOT_COMPUTABLE"
    assert report.summary.total is None
    assert all(item.realized_gross_pnl_delta is None for item in report.items)
    assert completed.counts.qualified == 0
    assert completed.summary.total is None
    assert completed.items[0].realized_gross_pnl is None


def test_historical_sale_currency_does_not_fill_a_missing_earlier_buy_cost_currency():
    source = historical(trade_fact().trade, start=datetime(2026, 9, 1, tzinfo=UTC))
    report = build_report(evidence_snapshot(evidence=(source,)), SEPTEMBER)
    sales = [item for item in report.items if item.period_status == "IN_PERIOD"]
    assert len(sales) == 2
    assert all(item.currency_code == "EUR" for item in sales)
    assert all(item.status == "NOT_COMPUTABLE" for item in sales)
    assert all(item.realized_gross_pnl_delta is None for item in sales)
    assert all("CURRENCY_UNKNOWN" in item.reasons for item in sales)


def test_conflicting_receipts_block_sale_and_complete_result_but_preserve_known_parts():
    facts = reference()
    disputed = facts[4]
    evidence = (
        historical(trade_fact().trade),
        document(trade_fact().trade, disputed.id, 9001),
        document(trade_fact().trade, disputed.id, 9002, code="USD"),
    )
    basis = evidence_snapshot(evidence=evidence)
    report = build_report(basis, SEPTEMBER)
    completed = build_closed_report(basis, OCTOBER)
    assert report.counts.usable == 1
    assert report.counts.unresolved == 1
    assert report.summary.status == "PARTIAL"
    assert report.summary.total is None
    assert report.summary.subtotal_display == "30.00"
    dispute = next(item for item in report.items if item.execution_id == disputed.id)
    assert dispute.status == "NOT_COMPUTABLE"
    assert dispute.realized_gross_pnl_delta is None
    assert dispute.currency_code is None
    assert completed.counts.qualified == 0
    assert completed.items[0].realized_gross_pnl is None


def test_eur_report_does_not_convert_historically_evidenced_usd():
    source = historical(trade_fact().trade, codes=(listing(XETRA, "USD"),))
    basis = evidence_snapshot(evidence=(source,))
    report = build_report(basis, LIFETIME)
    completed = build_closed_report(basis, OCTOBER)
    assert report.counts.usable == 0
    assert report.counts.excluded == 4
    assert all(item.currency_code == "USD" for item in report.items)
    assert all(item.realized_gross_pnl_delta is None for item in report.items)
    assert all("OTHER_CURRENCY" in item.reasons for item in report.items)
    assert completed.counts.other_currency == 1
    assert completed.counts.qualified == 0
    assert completed.items[0].realized_gross_pnl is None


def test_different_buy_currency_never_becomes_eur_cost_basis_even_with_eur_sale_evidence():
    facts = reference()
    source = historical(trade_fact().trade)
    purchase = document(trade_fact().trade, facts[3].id, code="USD")
    report = build_report(evidence_snapshot(evidence=(source, purchase)), OCTOBER)
    sale = next(item for item in report.items if item.period_status == "IN_PERIOD")
    assert sale.currency_code == "EUR"
    assert sale.status == "NOT_COMPUTABLE"
    assert "CURRENCY_MIXED" in sale.reasons
    assert sale.cost_basis_before is None
    assert sale.realized_gross_pnl_delta is None


def test_cancelled_trade_keeps_source_history_but_never_reenters_money_totals():
    trade = trade_fact()
    cancelled = replace(
        trade,
        trade=replace(
            trade.trade,
            cancelled_at=RECORDED,
            cancelled_by=UUID(int=4),
            cancellation_reason="Synthetic duplicate",
        ),
    )
    basis = evidence_snapshot(trades=(cancelled,))
    report = build_report(basis, LIFETIME)
    completed = build_closed_report(basis, OCTOBER)
    assert report.counts.cancelled == 1
    assert report.counts.usable == report.counts.examined == 0
    assert len(report.sources) == len(reference())
    assert completed.counts.cancelled == 1
    assert completed.counts.qualified == 0
    assert completed.items[0].realized_gross_pnl is None


def test_replaced_sale_is_counted_once_and_automatic_currency_is_rederived_for_replacement():
    facts = reference()
    corrected = replace(
        facts[4],
        id=UUID(int=9991),
        supersedes_execution_id=facts[4].id,
        price_per_unit=Decimal("3.00"),
        recorded_at=RECORDED + timedelta(days=1),
    )
    basis = evidence_snapshot((*facts, corrected))
    report = build_report(basis, SEPTEMBER)
    completed = build_closed_report(basis, OCTOBER)
    assert report.counts.examined == 4
    assert report.counts.usable == 2
    assert report.summary.total_display == "30.00"
    assert completed.summary.total_display == "70.00"
    original = next(item for item in report.sources if item.execution_id == facts[4].id)
    replacement = next(item for item in report.sources if item.execution_id == corrected.id)
    assert original.is_effective is False
    assert replacement.is_effective is True
    assert replacement.currency_resolution.source == "HISTORICAL_LISTINGS"
    assert replacement.currency_confirmation is None


def test_date_correction_outside_evidenced_interval_does_not_inherit_old_automatic_currency():
    facts = (
        execution(101, "BUY", 10, "2", "2026-08-01"),
        execution(102, "SELL", 10, "3", "2026-09-01"),
    )
    corrected = replace(
        execution(103, "BUY", 10, "2", "2026-07-01"),
        supersedes_execution_id=facts[0].id,
    )
    source = historical(trade_fact().trade, start=datetime(2026, 7, 31, tzinfo=UTC))
    report = build_report(evidence_snapshot((*facts, corrected), evidence=(source,)), SEPTEMBER)
    assert report.counts.usable == 0
    assert report.counts.unresolved == 1
    assert report.items[0].realized_gross_pnl_delta is None
    replacement = next(item for item in report.sources if item.execution_id == corrected.id)
    assert replacement.currency_resolution.currency_code is None


@pytest.mark.parametrize("conflicting", [False, True])
def test_replacement_receipt_prevents_false_eur_result_from_ancestor_confirmation(conflicting):
    facts = (
        execution(101, "BUY", 10, "2", "2026-08-01"),
        execution(102, "SELL", 10, "3", "2026-10-03"),
    )
    corrected = replace(
        execution(103, "SELL", 10, "4", "2026-10-04"),
        supersedes_execution_id=facts[1].id,
    )
    evidence = (document(trade_fact().trade, corrected.id, 9001, code="USD"),)
    if conflicting:
        evidence += (document(trade_fact().trade, corrected.id, 9002, code="EUR"),)
    basis = evidence_snapshot(
        (*facts, corrected),
        evidence=evidence,
        confirmations=(confirmed(facts[0]), confirmed(facts[1])),
    )
    sales = build_report(basis, OCTOBER)
    closed = build_closed_report(basis, OCTOBER)
    assert sales.counts.usable == 0
    assert sales.items[0].realized_gross_pnl_delta is None
    assert sales.items[0].currency_code == (None if conflicting else "USD")
    assert closed.counts.qualified == 0
    assert closed.items[0].realized_gross_pnl is None


def test_repeated_correction_cannot_revive_eur_after_a_conflicting_intermediate_document():
    facts = (
        execution(101, "BUY", 10, "2", "2026-08-01"),
        execution(102, "SELL", 10, "3", "2026-10-03"),
    )
    middle = replace(
        execution(103, "SELL", 10, "3.5", "2026-10-04"),
        supersedes_execution_id=facts[1].id,
    )
    latest = replace(
        execution(104, "SELL", 10, "4", "2026-10-05"),
        supersedes_execution_id=middle.id,
    )
    basis = evidence_snapshot(
        (*facts, middle, latest),
        evidence=(document(trade_fact().trade, middle.id, code="USD"),),
        confirmations=(confirmed(facts[0]), confirmed(facts[1])),
    )
    sales = build_report(basis, OCTOBER)
    closed = build_closed_report(basis, OCTOBER)
    assert sales.counts.usable == 0
    assert sales.items[0].currency_code is None
    assert sales.items[0].realized_gross_pnl_delta is None
    assert closed.counts.qualified == 0
    assert closed.items[0].realized_gross_pnl is None


def test_explicit_correction_overrides_automatic_currency_without_rewriting_source_evidence():
    facts = reference()
    original = evidence_snapshot()
    source_before = tuple(asdict(item) for item in original.currency_evidence)
    corrected = replace(original, confirmations=(confirmed(facts[-1], "USD"),))
    report = build_report(corrected, OCTOBER)
    assert report.counts.usable == 0
    assert report.counts.excluded == 4
    sale = next(item for item in report.items if item.execution_id == facts[-1].id)
    assert sale.currency_code == "USD"
    assert sale.realized_gross_pnl_delta is None
    assert tuple(asdict(item) for item in corrected.currency_evidence) == source_before


def test_evidence_correction_and_revocation_recompute_both_reports_without_retired_fallback():
    first = historical(trade_fact().trade)
    updated = replace(
        historical(trade_fact().trade, 8002, codes=(listing(XETRA, "USD"),)),
        supersedes_evidence_id=first.id,
    )
    revoked = replace(
        updated,
        id=UUID(int=8003),
        request_id=UUID(int=18003),
        supersedes_evidence_id=updated.id,
        revoked=True,
    )
    first_basis = evidence_snapshot(evidence=(first,))
    updated_basis = evidence_snapshot(evidence=(first, updated))
    revoked_basis = evidence_snapshot(evidence=(first, updated, revoked))
    for builder in (build_report, build_closed_report):
        original = builder(first_basis, OCTOBER)
        corrected = builder(updated_basis, OCTOBER)
        withdrawn = builder(revoked_basis, OCTOBER)
        assert original.summary.status == "COMPLETE"
        assert corrected.summary.status == "EMPTY"
        assert withdrawn.summary.status == "NOT_COMPUTABLE"
        assert withdrawn.summary.total is None
        assert len({original.basis.id, corrected.basis.id, withdrawn.basis.id}) == 3


def test_unchanged_sources_preserve_historical_money_provenance_and_basis_across_reads():
    basis = evidence_snapshot()
    before = asdict(basis)
    reread = replace(
        basis,
        read_started_at=RECORDED + timedelta(hours=2),
        read_completed_at=RECORDED + timedelta(hours=2, seconds=1),
    )
    for builder in (build_report, build_closed_report):
        original = builder(basis, OCTOBER)
        repeated = builder(reread, OCTOBER)
        assert original.basis.id == repeated.basis.id
        assert original.items == repeated.items
        assert original.sources == repeated.sources
        assert original.summary == repeated.summary
    assert asdict(basis) == before
