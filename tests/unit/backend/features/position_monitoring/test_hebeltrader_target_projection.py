"""Readable target history preserves actual owner facts and original provenance."""

from dataclasses import asdict, replace
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest
from pydantic import TypeAdapter
from tests.unit.backend.features.trade_position import test_hebeltrader_coverage as examples

from app.features.market_data.service.hebeltrader_history import (
    HebeltraderPriceHistory,
    HistoricalDailyEvidence,
    HistoricalListingBinding,
)
from app.features.position_monitoring.domain.hebeltrader_targets import (
    TargetComparisonQualification,
    evaluate_hebeltrader_targets,
)
from app.features.position_monitoring.persistence.hebeltrader_targets import TargetAssessmentRecord
from app.features.position_monitoring.service import hebeltrader_target_projection as module
from app.features.product.domain.models import OptionDirection
from app.features.trade_position.domain.enums import ExecutionSide
from app.features.trade_position.service.hebeltrader_evidence import (
    HebeltraderMonitoringBasis,
    HebeltraderScaleBasis,
)

case = examples.case
NOW = examples.NOW
LISTING = UUID(int=900)


def owner_basis(case):
    basis, revision, source = case
    declaration = revision.declaration
    return HebeltraderMonitoringBasis(
        examples.project(case),
        basis,
        revision,
        source,
        HebeltraderScaleBasis(
            declaration.scale_review_status,
            declaration.source_scale_reference,
            declaration.scale_review_reference,
        ),
        OptionDirection.CALL,
        (UUID(int=901),),
        None,
    )


def price_history(owner, *, high="120", trading_date=date(2026, 8, 6)):
    trade = owner.execution_basis.trade
    created = datetime(2025, 1, 1, tzinfo=UTC)
    binding = HistoricalListingBinding(
        workspace_id=trade.workspace_id,
        underlying_id=owner.coverage.underlying_id,
        listing_id=LISTING,
        trading_venue_id=UUID(int=902),
        venue_mic="SYNTH",
        timezone="Europe/Berlin",
        currency="USD",
        listing_version=1,
        venue_version=1,
        venue_reference_version="synthetic-reference-v1",
        listing_recorded_at=created,
        listing_updated_at=created,
        venue_recorded_at=created,
        venue_updated_at=created,
        fingerprint="c" * 64,
    )
    zone = ZoneInfo(binding.timezone)
    row = HistoricalDailyEvidence(
        source_row_id=UUID(int=903),
        workspace_id=trade.workspace_id,
        listing_id=LISTING,
        market_data_instrument_id=None,
        fingerprint="d" * 64,
        trading_date=trading_date,
        open=Decimal("100"),
        high=Decimal(high),
        low=Decimal("99"),
        close=Decimal("105"),
        adjusted_close=Decimal("105"),
        volume=Decimal("123"),
        currency="USD",
        provider="SYNTHETIC",
        provider_symbol="SYNTH.USD",
        price_type="EOD",
        quality_status="VALID",
        warnings=(),
        interval_start=datetime.combine(trading_date, time.min, zone).astimezone(UTC),
        interval_end=datetime.combine(trading_date + timedelta(days=1), time.min, zone).astimezone(
            UTC
        ),
        retrieved_at=NOW - timedelta(days=2),
        source_updated_at=NOW - timedelta(days=3),
        recorded_at=NOW - timedelta(days=1),
        last_updated_at=NOW - timedelta(days=1),
        issues=(),
        scale_status="REQUIRES_EXPLICIT_COMPARISON_QUALIFICATION",
    )
    return HebeltraderPriceHistory(
        workspace_id=trade.workspace_id,
        underlying_id=owner.coverage.underlying_id,
        binding=binding,
        rows=(row,),
        status="AVAILABLE",
        reasons=(),
        fingerprint="e" * 64,
        start_date=date(2026, 8, 2),
        end_date=NOW.date(),
        known_at=NOW,
        read_at=NOW,
        stored_range_complete=True,
        intervals_complete=True,
        rows_observed=1,
    )


def comparison(owner, history):
    source = module.target_source(owner)
    return TargetComparisonQualification(
        history.fingerprint,
        history.binding.fingerprint,
        source.source_version_id,
        source.scale_reference,
        "Synthetic qualification of this exact original market history",
    )


def assessment(owner, history, *, previous=None, number=910, qualification=True):
    return evaluate_hebeltrader_targets(
        position=module.target_position(owner),
        source=module.target_source(owner),
        history=module.target_history(history),
        qualification=comparison(owner, history) if qualification else None,
        assessment_id=UUID(int=number),
        assessed_at=NOW,
        previous=previous,
    )


def record(owner, history, result, *, previous=None):
    source = module.target_source(owner)
    view = module.assessment_view(
        result,
        basis_id="f" * 64,
        source=source,
        history=history,
        previous=previous,
        recorded_at=NOW,
    )
    trade = owner.execution_basis.trade
    return TargetAssessmentRecord(
        result.assessment_id,
        trade.workspace_id,
        trade.id,
        owner.coverage.position_id,
        trade.product_id,
        owner.coverage.underlying_id,
        source.source_version_id if source else None,
        owner.coverage.evidence_revision_id,
        result.previous_assessment_id,
        result.definition_version,
        result.baseline_id,
        result.baseline_version,
        "f" * 64,
        result.input_fingerprint,
        NOW,
        trade.created_by,
        {
            "history": TypeAdapter(HebeltraderPriceHistory).dump_python(history, mode="json"),
            "qualification": TypeAdapter(TargetComparisonQualification).dump_python(
                comparison(owner, history), mode="json"
            ),
        },
        {
            **module.VIEW_ADAPTER.dump_python(view, mode="json"),
            "domain": module.ASSESSMENT_ADAPTER.dump_python(result, mode="json"),
        },
    )


def test_mapper_uses_actual_owner_remainder_and_underlying_axis_without_recalculation(case):
    owner = owner_basis(case)
    before = asdict(owner)
    position = module.target_position(owner)
    source = module.target_source(owner)
    assert position.remaining_quantity == 80
    assert position.original_z1_quantity == 100
    assert position.assigned_z1_sold_quantity == 40
    assert position.personal_underlying_entry == Decimal("109.5")
    assert position.personal_underlying_binding.currency == "USD"
    assert owner.coverage.valuation_basis.cost_basis_currency == "EUR"
    assert source.target_1 == Decimal("110")
    assert source.target_1 != owner.coverage.source.product.target_1
    assert source.issue_date == owner.coverage.source.issue_date
    assert asdict(owner) == before


def test_mapper_preserves_date_only_buy_without_promoting_stored_midnight_to_execution_time(case):
    basis, revision, source = case
    first = replace(
        basis.history[0],
        executed_at=datetime(2026, 8, 3, tzinfo=ZoneInfo("Europe/Berlin")).astimezone(UTC),
        executed_on=date(2026, 8, 3),
        execution_timezone="Europe/Berlin",
    )
    basis = examples.execution_basis([first, *basis.history[1:]])
    position = module.target_position(owner_basis((basis, revision, source)))
    assert position.opened_at is None
    assert position.opened_on == date(2026, 8, 3)
    assert position.opening_timezone == "Europe/Berlin"


def test_daily_mapping_keeps_original_interval_not_retrieval_or_update_time(case):
    owner = owner_basis(case)
    history = price_history(owner)
    mapped = module.target_history(history)
    daily = mapped.rows[0]
    assert daily.interval_start == history.rows[0].interval_start
    assert daily.interval_end == history.rows[0].interval_end
    assert daily.interval_end < history.rows[0].source_updated_at < history.rows[0].retrieved_at
    assert daily.time_precision == "DATE_ONLY"
    assert daily.fingerprint == history.rows[0].fingerprint
    assert mapped.listing_fingerprint == history.binding.fingerprint


def test_threshold_equality_is_displayed_as_reached_with_exact_proof_source(case):
    owner = owner_basis(case)
    history = price_history(owner, high="120")
    result = assessment(owner, history)
    view = module.persisted_view(record(owner, history, result))
    z2 = next(target for target in view.targets if target.target == "Z2")
    assert z2.status == "PROVEN"
    assert "erreicht" in z2.detail
    assert "überschritten" not in z2.detail
    assert z2.threshold == z2.evidence.high == Decimal("120")
    assert z2.proof_source_version_id == owner.coverage.source.source_version_id
    assert z2.proof_scale_reference == owner.scale.source_scale_reference


@pytest.mark.parametrize("mode", ["missing", "corrected"])
def test_missing_or_corrected_cache_cannot_rewrite_original_readable_proof(case, mode):
    owner = owner_basis(case)
    history = price_history(owner)
    first = assessment(owner, history)
    original = record(owner, history, first)
    before = asdict(original)
    rows = (
        ()
        if mode == "missing"
        else (
            replace(history.rows[0], high=Decimal("106"), fingerprint="9" * 64, provider="CHANGED"),
        )
    )
    current = replace(
        history,
        rows=rows,
        status="MISSING" if mode == "missing" else "AVAILABLE",
        fingerprint="8" * 64,
    )
    second = assessment(owner, current, previous=first, number=911)
    view = module.assessment_view(
        second,
        basis_id="7" * 64,
        source=module.target_source(owner),
        history=current,
        previous=original,
        recorded_at=NOW,
    )
    assert view.targets[0].status == ("PROVEN" if mode == "missing" else "REVIEW_REQUIRED")
    assert view.targets[0].evidence == module.persisted_view(original).targets[0].evidence
    assert view.targets[0].evidence.provider == "SYNTHETIC"
    assert view.targets[0].evidence.high == Decimal("120")
    assert asdict(original) == before


def test_new_source_is_distinct_from_historical_proof_source_and_threshold(case):
    owner = owner_basis(case)
    history = price_history(owner)
    first = assessment(owner, history)
    original = record(owner, history, first)
    new_source = replace(
        owner.coverage.source,
        source_version_id=UUID(int=920),
        underlying=replace(owner.coverage.source.underlying, target_1=Decimal("115")),
    )
    current_owner = replace(owner, coverage=replace(owner.coverage, source=new_source))
    second = assessment(current_owner, history, previous=first, number=911)
    view = module.assessment_view(
        second,
        basis_id="7" * 64,
        source=module.target_source(current_owner),
        history=history,
        previous=original,
        recorded_at=NOW,
    )
    assert view.source_version_id == new_source.source_version_id
    z1 = view.targets[0]
    assert z1.status == "REVIEW_REQUIRED"
    assert z1.threshold == Decimal("110")
    assert z1.proof_source_version_id == owner.coverage.source.source_version_id
    assert z1.proof_source_version_id != view.source_version_id
    assert z1.proof_scale_reference == owner.scale.source_scale_reference


def test_original_provenance_must_not_be_fabricated_when_no_retained_copy_exists(case):
    owner = owner_basis(case)
    history = price_history(owner)
    result = assessment(owner, history)
    with pytest.raises(ValueError, match="retained original market provenance"):
        module.assessment_view(
            result,
            basis_id="f" * 64,
            source=module.target_source(owner),
            history=replace(history, rows=()),
            previous=None,
            recorded_at=NOW,
        )


def test_protection_details_distinguish_missing_entry_no_target_and_closed_position(case):
    owner = owner_basis(case)
    history = price_history(owner)
    missing = replace(owner, coverage=replace(owner.coverage, personal_underlying_entry=None))
    before_hit = price_history(owner, high="109")
    closing_sale = examples.fact(904, quantity=80, side=ExecutionSide.SELL, after=timedelta(days=3))
    closed_basis = examples.execution_basis([*case[0].history, closing_sale])
    closed = owner_basis((closed_basis, case[1], case[2]))
    views = [
        module.persisted_view(record(value, prices, assessment(value, prices)))
        for value, prices in ((missing, history), (owner, before_hit), (closed, history))
    ]
    details = [view.protection_basis.detail for view in views]
    assert len(set(details)) == 3
    assert views[0].protection_basis.status == "NOT_ASSESSABLE"
    assert views[1].protection_basis.status == views[2].protection_basis.status == "NOT_APPLICABLE"
    assert all(
        "bekanntgegebener Schutzvorschlag" in detail or "folgenden" in detail for detail in details
    )


def test_distinct_relevant_reasons_remain_readable_and_specific():
    codes = (
        "PRICE_COMPARISON_NOT_CONFIRMED",
        "SOURCE_PUBLICATION_ORDER_NOT_ESTABLISHED",
        "INTERVAL_NOT_ENTIRELY_AFTER_ENTRY",
        "ORIGINAL_PRICE_EVIDENCE_CHANGED",
    )
    meanings = [module.reason_text(code) for code in codes]
    assert len(set(meanings)) == len(codes)
    assert all(code not in text for code, text in zip(codes, meanings, strict=True))
