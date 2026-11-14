"""Synthetic target evidence tests: no database, provider, stop or order writes."""

from dataclasses import asdict, replace
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest
from pydantic import TypeAdapter

from app.features.position_monitoring.domain.hebeltrader_targets import (
    PROTECTION_BASIS_NOTICE,
    TargetAssessment,
    TargetComparisonQualification,
    TargetDailyEvidence,
    TargetHistoryBasis,
    TargetPositionBasis,
    TargetSourceBasis,
    evaluate_hebeltrader_targets,
)
from app.features.trade_position.domain.price_binding import PriceBasis, PriceBinding

NOW = datetime(2026, 9, 10, 12, tzinfo=UTC)
WORKSPACE = UUID(int=1)
TRADE = UUID(int=2)
POSITION = UUID(int=3)
PRODUCT = UUID(int=4)
UNDERLYING = UUID(int=5)
LISTING = UUID(int=6)
SOURCE = UUID(int=7)
BINDING = PriceBinding(PriceBasis.UNDERLYING, UNDERLYING, "USD")


def row(number=20, *, day=date(2026, 9, 2), high="111", zone="Europe/Berlin", **changes):
    timezone = ZoneInfo(zone)
    value = TargetDailyEvidence(
        source_row_id=UUID(int=number),
        fingerprint=f"original-price-{number}",
        workspace_id=WORKSPACE,
        listing_id=LISTING,
        trading_date=day,
        high=Decimal(high),
        currency="USD",
        interval_start=datetime.combine(day, time.min, timezone).astimezone(UTC),
        interval_end=datetime.combine(day + timedelta(days=1), time.min, timezone).astimezone(UTC),
    )
    return replace(value, **changes)


def qualification(history, source):
    return TargetComparisonQualification(
        history.fingerprint,
        history.listing_fingerprint,
        source.source_version_id,
        source.scale_reference,
        "Synthetic reviewed original listing history, publisher marks and common scale",
    )


@pytest.fixture
def case():
    position = TargetPositionBasis(
        WORKSPACE,
        TRADE,
        POSITION,
        PRODUCT,
        UNDERLYING,
        "original-execution-owner-basis",
        datetime(2026, 9, 1, 10, tzinfo=UTC),
        None,
        None,
        80,
        False,
        "CALL",
        original_z1_quantity=100,
        assigned_z1_sold_quantity=40,
        personal_underlying_entry=Decimal("106"),
        personal_underlying_binding=BINDING,
        evidence_revision_id=UUID(int=8),
    )
    source = TargetSourceBasis(
        SOURCE,
        BINDING,
        "original-unadjusted-units",
        Decimal("100"),
        Decimal("110"),
        Decimal("120"),
        issue_date=date(2026, 8, 28),
        content_hash="a" * 64,
    )
    history = TargetHistoryBasis(
        WORKSPACE,
        UNDERLYING,
        "original-history-fingerprint",
        (row(),),
        LISTING,
        BINDING,
        "original-listing-fingerprint",
        "Europe/Berlin",
        NOW,
        start_date=date(2026, 9, 1),
        end_date=date(2026, 9, 9),
    )
    return {
        "position": position,
        "source": source,
        "history": history,
        "qualification": qualification(history, source),
    }


def evaluate(case, **changes):
    return evaluate_hebeltrader_targets(
        **({"assessment_id": UUID(int=100), "assessed_at": NOW, **case} | changes)
    )


def changed_history(case, rows, **changes):
    history = replace(case["history"], rows=tuple(rows), fingerprint="changed-history", **changes)
    return {**case, "history": history, "qualification": qualification(history, case["source"])}


def test_target_proof_is_independent_of_missing_quantity_and_personal_entry(case):
    position = replace(
        case["position"],
        original_z1_quantity=None,
        assigned_z1_sold_quantity=None,
        personal_underlying_entry=None,
    )
    result = evaluate(case, position=position)
    assert result.z1.status == "PROVEN"
    assert result.z1.current_assessability == "ASSESSABLE"
    assert result.z2.status == "NOT_PROVEN"
    assert result.z1_orientation.status == "NOT_ASSESSABLE"
    assert result.protection_basis.status == "NOT_ASSESSABLE"
    assert result.z1.proof.evidence.trading_date == date(2026, 9, 2)
    assert result.z1.proof.detected_at == NOW
    assert result.z1.proof.time_precision == "DATE_ONLY"
    assert result.z1.proof.evidence.interval_start < result.z1.proof.evidence.interval_end < NOW


@pytest.mark.parametrize(("sold", "expected"), [(0, "READY"), (50, "READY"), (51, "COVERED")])
def test_z1_returns_fraction_and_owner_facts_without_rounding_sale_quantities(case, sold, expected):
    position = replace(case["position"], original_z1_quantity=101, assigned_z1_sold_quantity=sold)
    result = evaluate(case, position=position)
    assert result.z1_orientation.status == expected
    assert asdict(result.z1_orientation) == {
        "status": expected,
        "original_quantity": 101,
        "assigned_sold_quantity": sold,
        "reasons": (),
        "fraction": Decimal("0.5"),
    }
    assert position.remaining_quantity == 80


def test_z2_uses_owner_remainder_and_prioritizes_review_without_changing_stops(case):
    case = changed_history(case, [row(high="120")])
    before = {key: asdict(value) for key, value in case.items()}
    result = evaluate(case)
    assert result.z1.status == result.z2.status == "PROVEN"
    assert result.z2_exit_review.status == "READY"
    assert result.z2_exit_review.remaining_quantity == 80
    assert result.guidance_priority == ("B03", "B01", "B02")
    assert result.protection_basis.personal_underlying_entry == Decimal("106")
    assert result.protection_basis.notice == PROTECTION_BASIS_NOTICE
    assert {key: asdict(value) for key, value in case.items()} == before


def test_a_bar_ending_after_buy_is_insufficient_when_it_started_before_buy(case):
    result = evaluate(changed_history(case, [row(day=date(2026, 9, 1), high="130")]))
    assert result.z1.status == result.z2.status == "NOT_ASSESSABLE"
    assert "INTERVAL_NOT_ENTIRELY_AFTER_ENTRY" in result.z1.reasons
    assert result.z1.proof is None


def test_date_only_buy_uses_its_own_timezone_and_never_invents_intraday_order(case):
    position = replace(
        case["position"],
        opened_at=None,
        opened_on=date(2026, 9, 1),
        opening_timezone="America/New_York",
    )
    # Berlin's following calendar day starts while the unknown New York BUY day
    # may still be in progress. Even that entire bar cannot prove post-entry order.
    first = evaluate(case, position=position)
    assert first.z1.status == "NOT_ASSESSABLE"
    later = changed_history(case, [row(day=date(2026, 9, 3))])
    assert evaluate(later, position=position).z1.status == "PROVEN"


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"opened_at": None}, "ENTRY_TIME_MISSING_OR_INVALID"),
        ({"opened_at": None, "opened_on": date(2026, 9, 1)}, "ENTRY_TIMEZONE_MISSING"),
        ({"opened_on": date(2026, 9, 1)}, "ENTRY_TIME_PRECISION_CONFLICT"),
        (
            {"opened_at": None, "opened_on": date(2026, 9, 1), "opening_timezone": "bad/zone"},
            "ENTRY_TIMEZONE_INVALID",
        ),
    ],
)
def test_missing_or_conflicting_entry_time_is_not_filled_in(case, changes, reason):
    result = evaluate(case, position=replace(case["position"], **changes))
    assert result.z1.status == "NOT_ASSESSABLE"
    assert reason in result.z1.reasons


@pytest.mark.parametrize("direction", ["PUT", None])
def test_put_and_unknown_direction_are_not_silently_treated_as_upward_calls(case, direction):
    result = evaluate(case, position=replace(case["position"], option_direction=direction))
    assert result.z1.status == "NOT_ASSESSABLE"
    assert "PRODUCT_DIRECTION_NOT_SUPPORTED" in result.z1.reasons


@pytest.mark.parametrize(
    "changes",
    [
        {"reference_price": Decimal("110")},
        {"target_2": Decimal("109")},
        {"target_1": Decimal("NaN")},
        {"target_2": Decimal("Infinity")},
    ],
)
def test_source_marks_require_a_finite_ordered_call_constellation(case, changes):
    result = evaluate(case, source=replace(case["source"], **changes))
    assert result.z1.status == "NOT_ASSESSABLE"
    assert "SOURCE_CALL_TARGET_ORDER_INVALID" in result.z1.reasons


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("history_fingerprint", "other", "COMPARISON_HISTORY_FINGERPRINT_MISMATCH"),
        ("listing_fingerprint", "other", "COMPARISON_LISTING_FINGERPRINT_MISMATCH"),
        ("source_version_id", UUID(int=500), "COMPARISON_SOURCE_VERSION_MISMATCH"),
        ("source_scale_reference", "other", "COMPARISON_SCALE_REFERENCE_MISMATCH"),
        ("evidence_reference", " ", "COMPARISON_EVIDENCE_REFERENCE_MISSING"),
    ],
)
def test_explicit_comparison_must_match_every_exact_original_reference(case, field, value, reason):
    result = evaluate(case, qualification=replace(case["qualification"], **{field: value}))
    assert result.z1.status == "NOT_ASSESSABLE"
    assert reason in result.z1.reasons


def test_f2074_source_scale_does_not_replace_new_market_comparison_confirmation(case):
    result = evaluate(case, qualification=None)
    assert result.z1.status == "NOT_ASSESSABLE"
    assert "PRICE_COMPARISON_NOT_CONFIRMED" in result.z1.reasons


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"workspace_id": UUID(int=510)}, "ROW_SCOPE_OR_CURRENCY_MISMATCH"),
        ({"listing_id": UUID(int=511)}, "ROW_SCOPE_OR_CURRENCY_MISMATCH"),
        ({"currency": "EUR"}, "ROW_SCOPE_OR_CURRENCY_MISMATCH"),
        ({"interval_start": None}, "FULL_DAILY_INTERVAL_NOT_ESTABLISHED"),
        (
            {"interval_start": datetime(2026, 9, 2, 10, tzinfo=UTC)},
            "FULL_DAILY_INTERVAL_NOT_ESTABLISHED",
        ),
        ({"issues": ("INVALID_ORIGINAL_VALUES",)}, "ROW_EVIDENCE_UNSUITABLE"),
        (
            {"scale_status": "ADJUSTMENT_INDICATION_PRESENT"},
            "ROW_ADJUSTMENT_REQUIRES_OWNER_EVIDENCE",
        ),
    ],
)
def test_foreign_or_unsuitable_daily_evidence_cannot_prove_a_target(case, changes, reason):
    result = evaluate(changed_history(case, [row(**changes)]))
    assert result.z1.status == "NOT_ASSESSABLE"
    assert reason in result.z1.reasons


def test_fingerprint_does_not_qualify_a_foreign_source_axis_or_history_scope(case):
    source = replace(case["source"], binding=PriceBinding(PriceBasis.WARRANT, PRODUCT, "USD"))
    assert "SOURCE_PRICE_BINDING_MISMATCH" in evaluate(case, source=source).z1.reasons
    history = replace(case["history"], workspace_id=UUID(int=520))
    assert "HISTORY_SCOPE_MISMATCH" in evaluate(case, history=history).z1.reasons
    history = replace(
        case["history"], binding=PriceBinding(PriceBasis.UNDERLYING, UNDERLYING, "EUR")
    )
    assert "HISTORY_PRICE_BINDING_MISMATCH" in evaluate(case, history=history).z1.reasons


def test_publication_date_needs_source_before_event_not_source_before_buy(case):
    source = replace(case["source"], issue_date=date(2026, 9, 2))
    case = {**case, "source": source, "qualification": qualification(case["history"], source)}
    same_day = evaluate(case)
    assert same_day.z1.status == "NOT_ASSESSABLE"
    assert "SOURCE_PUBLICATION_ORDER_NOT_ESTABLISHED" in same_day.z1.reasons
    # The full September 3 Berlin interval also begins inside the uncertainty
    # envelope ending September 3 at 12:00 UTC; no publisher zone is invented.
    uncertain = evaluate(changed_history(case, [row(day=date(2026, 9, 3))]))
    assert uncertain.z1.status == "NOT_ASSESSABLE"
    later = evaluate(changed_history(case, [row(day=date(2026, 9, 4))]))
    assert later.z1.status == "PROVEN"
    assert later.z1.proof.source.issue_date > case["position"].opened_at.date()


def test_missing_publication_date_is_explicitly_not_assessable(case):
    result = evaluate(case, source=replace(case["source"], issue_date=None))
    assert "SOURCE_ISSUE_DATE_MISSING" in result.z1.reasons
    assert result.z1.status == "NOT_ASSESSABLE"


def test_price_retracement_and_restart_preserve_the_same_original_proof(case):
    first = evaluate(case)
    adapter = TypeAdapter(TargetAssessment)
    restored = adapter.validate_json(adapter.dump_json(first))
    later = changed_history(case, [row(21, day=date(2026, 9, 3), high="101")])
    second = evaluate(later, previous=restored, assessment_id=UUID(int=101))
    assert second.z1.status == "PROVEN"
    assert second.z1.current_assessability == "ASSESSABLE"
    assert second.z1.proof == first.z1.proof
    assert second.z1.event_id == first.z1.event_id
    assert second.previous_assessment_id == first.assessment_id
    assert second.z1_orientation.status == "READY"


def test_missing_new_data_does_not_erase_a_historical_hit_or_claim_current_assessability(case):
    first = evaluate(case)
    history = replace(case["history"], rows=(), status="MISSING", fingerprint="no-current-data")
    second = evaluate(
        case, history=history, qualification=None, previous=first, assessment_id=UUID(int=101)
    )
    assert second.z1.status == "PROVEN"
    assert second.z1.proof is first.z1.proof
    assert second.z1.current_assessability == "NOT_ASSESSABLE"
    assert second.z2.status == "NOT_ASSESSABLE"


def test_rebuy_changes_owner_basis_and_personal_entry_without_restarting_z1(case):
    first = evaluate(case)
    position = replace(
        case["position"],
        owner_basis_id="owner-after-rebuy",
        remaining_quantity=100,
        personal_underlying_entry=Decimal("104"),
    )
    second = evaluate(case, position=position, previous=first, assessment_id=UUID(int=101))
    assert second.input_fingerprint != first.input_fingerprint
    assert second.z1.event_id == first.z1.event_id
    assert second.z1.proof is first.z1.proof
    assert second.z1_orientation.original_quantity == 100
    assert second.protection_basis.personal_underlying_entry == Decimal("104")
    assert second.protection_basis.notice == PROTECTION_BASIS_NOTICE


@pytest.mark.parametrize("change", ["buy_time", "source_version", "source_mark", "original_price"])
def test_correction_keeps_original_proof_but_requires_review(case, change):
    first = evaluate(case)
    original = asdict(first)
    if change == "buy_time":
        case = {**case, "position": replace(case["position"], opened_at=NOW - timedelta(days=1))}
    elif change == "source_version":
        case = {**case, "source": replace(case["source"], source_version_id=UUID(int=530))}
    elif change == "source_mark":
        case = {**case, "source": replace(case["source"], target_1=Decimal("115"))}
    else:
        case = changed_history(case, [row(high="101", fingerprint="corrected-original-price")])
    case = {**case, "qualification": qualification(case["history"], case["source"])}
    second = evaluate(case, previous=first, assessment_id=UUID(int=101))
    assert second.z1.status == "REVIEW_REQUIRED"
    assert second.z1.proof is first.z1.proof
    assert second.z1_orientation.status == second.protection_basis.status == "REVIEW_REQUIRED"
    assert asdict(first) == original
    third = evaluate(case, previous=second, assessment_id=UUID(int=102))
    assert third.z1.status == "REVIEW_REQUIRED"
    assert third.z1.proof is first.z1.proof


def test_replaced_original_row_and_changed_listing_provenance_require_review(case):
    first = evaluate(case)
    replaced = evaluate(
        changed_history(case, [row(22)]), previous=first, assessment_id=UUID(int=101)
    )
    assert "ORIGINAL_PRICE_EVIDENCE_REPLACED" in replaced.z1.review_reasons
    history = replace(case["history"], listing_fingerprint="corrected-listing-reference")
    changed = evaluate(case, history=history, previous=first, assessment_id=UUID(int=102))
    assert "PROVEN_LISTING_BASIS_CHANGED" in changed.z1.review_reasons


def test_closed_positions_keep_history_and_never_generate_fresh_guidance(case):
    first = evaluate(case)
    position = replace(case["position"], remaining_quantity=0, closed=True)
    second = evaluate(case, position=position, previous=first, assessment_id=UUID(int=101))
    assert second.z1.status == "PROVEN"
    assert second.z1.proof is first.z1.proof
    assert second.z1_orientation.status == "POSITION_CLOSED"
    assert second.z2_exit_review.status == "POSITION_CLOSED"
    assert second.protection_basis.status == "POSITION_CLOSED"
    assert second.guidance_priority == ()
    assert evaluate(case, position=position).z1.proof is None


def test_zero_sales_is_known_and_protection_never_uses_warrant_entry_prices(case):
    position = replace(
        case["position"],
        assigned_z1_sold_quantity=0,
        personal_underlying_binding=PriceBinding(PriceBasis.WARRANT, PRODUCT, "USD"),
    )
    result = evaluate(case, position=position)
    assert result.z1_orientation.status == "READY"
    assert result.protection_basis.status == "NOT_ASSESSABLE"
    assert result.protection_basis.personal_underlying_entry is None


@pytest.mark.parametrize("field", ["workspace_id", "trade_id", "position_id"])
def test_previous_assessment_from_another_scope_is_rejected(case, field):
    first = replace(evaluate(case), **{field: UUID(int=540)})
    with pytest.raises(ValueError, match="PREVIOUS_ASSESSMENT_SCOPE_MISMATCH"):
        evaluate(case, previous=first, assessment_id=UUID(int=101))


def test_invalid_previous_version_and_cycle_are_rejected(case):
    first = evaluate(case)
    with pytest.raises(ValueError, match="PREVIOUS_ASSESSMENT_VERSION_MISMATCH"):
        evaluate(
            case, previous=replace(first, baseline_version="other"), assessment_id=UUID(int=101)
        )
    with pytest.raises(ValueError, match="ASSESSMENT_PREDECESSOR_INVALID"):
        evaluate(case, previous=first)


def test_incomplete_or_unfinished_history_does_not_appear_as_no_hit(case):
    history = replace(case["history"], stored_range_complete=False)
    assert evaluate(case, history=history).z1.status == "NOT_ASSESSABLE"
    future = changed_history(case, [row(day=NOW.date(), high="130")], end_date=NOW.date())
    result = evaluate(future)
    assert result.z1.status == "NOT_ASSESSABLE"
    assert "FULL_DAILY_INTERVAL_NOT_COMPLETED" in result.z1.reasons


def test_no_hit_only_describes_the_existing_suitable_evidence(case):
    result = evaluate(changed_history(case, [row(high="109.99")]))
    assert result.z1.status == result.z2.status == "NOT_PROVEN"
    assert result.z1.current_assessability == "ASSESSABLE"
    assert result.guidance_priority == ()


def test_assessment_clock_does_not_change_fact_fingerprint_or_event_identity(case):
    first = evaluate(case)
    later = evaluate(case, assessment_id=UUID(int=101), assessed_at=NOW + timedelta(seconds=3))
    assert first.input_fingerprint == later.input_fingerprint
    assert first.z1.event_id == later.z1.event_id
