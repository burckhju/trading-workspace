"""Pure input review shares target prerequisites without granting qualification."""

from dataclasses import asdict, replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock
from uuid import UUID

import pytest
from tests.unit.backend.features.position_monitoring import test_hebeltrader_targets as examples

from app.features.position_monitoring.domain import hebeltrader_targets as module
from app.features.position_monitoring.domain.hebeltrader_targets import (
    TargetInputReview,
    TargetInputRowReview,
    review_hebeltrader_target_inputs,
)
from app.features.trade_position.domain.price_binding import PriceBasis, PriceBinding


@pytest.fixture
def case():
    return examples.case.__wrapped__()


def review(case, *, as_of=examples.NOW, **changes):
    values = {key: case[key] for key in ("position", "source", "history")}
    return review_hebeltrader_target_inputs(**(values | changes), as_of=as_of)


def test_review_does_not_qualify_compare_targets_create_events_or_mutate_inputs(case, monkeypatch):
    before = {key: asdict(value) for key, value in case.items()}
    forbidden = Mock(side_effect=AssertionError("Review must not create a qualification or event"))
    for name in (
        "evaluate_hebeltrader_targets",
        "_target_result",
        "_event_id",
        "_fingerprint",
        "TargetProof",
        "TargetResult",
        "TargetComparisonQualification",
    ):
        monkeypatch.setattr(module, name, forbidden)
    original = case["history"].rows[0]
    assert review(case) == TargetInputReview(
        (), 1, (TargetInputRowReview(original.source_row_id, original.fingerprint, True, ()),)
    )
    assert {key: asdict(value) for key, value in case.items()} == before
    forbidden.assert_not_called()


def test_technical_review_does_not_remove_the_separate_qualification_requirement(case):
    result = review(case)
    assert result.usable_row_count == 1 and result.global_reasons == ()
    unqualified = examples.evaluate(case, qualification=None)
    assert unqualified.z1.status == unqualified.z2.status == "NOT_ASSESSABLE"
    assert unqualified.z1.reasons == ("PRICE_COMPARISON_NOT_CONFIRMED",)
    assert unqualified.z1.proof is None and unqualified.z2.proof is None
    qualified = examples.evaluate(case)
    assert qualified.z1.status == "PROVEN"
    assert qualified.z2.status == "NOT_PROVEN"


@pytest.mark.parametrize(
    "owner,changes,reason",
    [
        ("position", {"opened_at": None}, "ENTRY_TIME_MISSING_OR_INVALID"),
        (
            "position",
            {"opened_on": date(2026, 9, 1)},
            "ENTRY_TIME_PRECISION_CONFLICT",
        ),
        (
            "position",
            {"opened_at": None, "opened_on": date(2026, 9, 1)},
            "ENTRY_TIMEZONE_MISSING",
        ),
        ("position", {"closed": True}, "POSITION_CLOSED_OR_CANCELLED"),
        ("position", {"cancelled": True}, "POSITION_CLOSED_OR_CANCELLED"),
        ("position", {"option_direction": "PUT"}, "PRODUCT_DIRECTION_NOT_SUPPORTED"),
        ("source", None, "SOURCE_BASIS_MISSING"),
        ("source", {"scale_reference": None}, "SOURCE_SCALE_REFERENCE_MISSING"),
        ("source", {"scale_reference": " "}, "SOURCE_SCALE_REFERENCE_MISSING"),
        ("source", {"issue_date": None}, "SOURCE_ISSUE_DATE_MISSING"),
        ("source", {"target_2": Decimal("109")}, "SOURCE_CALL_TARGET_ORDER_INVALID"),
        (
            "source",
            {"binding": PriceBinding(PriceBasis.WARRANT, examples.PRODUCT, "USD")},
            "SOURCE_PRICE_BINDING_MISMATCH",
        ),
        ("history", {"workspace_id": UUID(int=900)}, "HISTORY_SCOPE_MISMATCH"),
        ("history", {"underlying_id": UUID(int=901)}, "HISTORY_SCOPE_MISMATCH"),
        ("history", {"listing_id": None}, "HISTORICAL_LISTING_BINDING_MISSING"),
        (
            "history",
            {"binding": PriceBinding(PriceBasis.UNDERLYING, examples.UNDERLYING, "EUR")},
            "HISTORY_PRICE_BINDING_MISMATCH",
        ),
        ("history", {"listing_timezone": "Unknown/Zone"}, "LISTING_TIMEZONE_INVALID"),
        (
            "history",
            {"known_at": examples.NOW + timedelta(seconds=1)},
            "HISTORY_CUTOFF_INVALID",
        ),
        ("history", {"stored_range_complete": False}, "STORED_HISTORY_RANGE_INCOMPLETE"),
        ("history", {"status": "LIMIT_EXCEEDED"}, "HISTORY_LIMIT_EXCEEDED"),
    ],
)
def test_global_blockers_match_evaluator_without_inventing_qualification(
    case, owner, changes, reason
):
    current = dict(case)
    current[owner] = replace(case[owner], **changes) if changes is not None else None
    result = review(current)
    assert reason in result.global_reasons
    assert result.usable_row_count == 0 and result.rows == ()
    assert "PRICE_COMPARISON_NOT_CONFIRMED" not in result.global_reasons
    evaluated = examples.evaluate(current, qualification=None)
    assert evaluated.z1.status == evaluated.z2.status == "NOT_ASSESSABLE"
    assert evaluated.z1.reasons == (*result.global_reasons, "PRICE_COMPARISON_NOT_CONFIRMED")
    assert current["history"].rows == case["history"].rows


@pytest.mark.parametrize(
    "changes,reasons",
    [
        ({"workspace_id": UUID(int=902)}, ("ROW_SCOPE_OR_CURRENCY_MISMATCH",)),
        ({"listing_id": UUID(int=903)}, ("ROW_SCOPE_OR_CURRENCY_MISMATCH",)),
        ({"currency": "EUR"}, ("ROW_SCOPE_OR_CURRENCY_MISMATCH",)),
        ({"fingerprint": ""}, ("ROW_ORIGINAL_VALUES_INVALID",)),
        ({"high": Decimal("NaN")}, ("ROW_ORIGINAL_VALUES_INVALID",)),
        (
            {"issues": ("DATA_NOT_KNOWN_AT_CUTOFF",)},
            ("ROW_EVIDENCE_UNSUITABLE", "DATA_NOT_KNOWN_AT_CUTOFF"),
        ),
        (
            {"scale_status": "ADJUSTMENT_INDICATION_PRESENT"},
            ("ROW_ADJUSTMENT_REQUIRES_OWNER_EVIDENCE",),
        ),
        ({"interval_start": None}, ("FULL_DAILY_INTERVAL_NOT_ESTABLISHED",)),
        (
            {"interval_end": datetime(2026, 9, 2, 12, tzinfo=UTC)},
            ("FULL_DAILY_INTERVAL_NOT_ESTABLISHED",),
        ),
    ],
)
def test_unsuitable_row_keeps_original_identity_and_same_rejection_as_evaluator(
    case, changes, reasons
):
    current = examples.changed_history(case, [examples.row(**changes)])
    original = current["history"].rows[0]
    result = review(current)
    assert result == TargetInputReview(
        ("NO_SUITABLE_POST_ENTRY_DAILY_EVIDENCE",),
        0,
        (TargetInputRowReview(original.source_row_id, original.fingerprint, False, reasons),),
    )
    evaluated = examples.evaluate(current)
    assert evaluated.z1.status == evaluated.z2.status == "NOT_ASSESSABLE"
    assert evaluated.z1.reasons == (*reasons, *result.global_reasons)
    assert evaluated.z1.proof is None


@pytest.mark.parametrize(
    "day,history_changes,reason",
    [
        (date(2026, 9, 1), {}, "INTERVAL_NOT_ENTIRELY_AFTER_ENTRY"),
        (
            examples.NOW.date(),
            {"end_date": examples.NOW.date()},
            "FULL_DAILY_INTERVAL_NOT_COMPLETED",
        ),
        (
            date(2026, 9, 2),
            {"start_date": date(2026, 9, 3)},
            "ROW_OUTSIDE_REQUESTED_RANGE",
        ),
    ],
)
def test_daily_interval_entry_completion_and_range_match_actual_evaluation(
    case, day, history_changes, reason
):
    current = examples.changed_history(case, [examples.row(day=day)], **history_changes)
    result = review(current)
    assert result.usable_row_count == 0
    assert result.rows[0].reasons == (reason,)
    assert examples.evaluate(current).z1.reasons == (
        reason,
        "NO_SUITABLE_POST_ENTRY_DAILY_EVIDENCE",
    )


def test_date_only_entry_keeps_its_timezone_and_does_not_hide_a_later_usable_row(case):
    position = replace(
        case["position"],
        opened_at=None,
        opened_on=date(2026, 9, 1),
        opening_timezone="America/New_York",
    )
    current = examples.changed_history(
        case, [examples.row(), examples.row(21, day=date(2026, 9, 3))]
    )
    current["position"] = position
    result = review(current)
    assert result.global_reasons == () and result.usable_row_count == 1
    assert result.rows[0].reasons == ("INTERVAL_NOT_ENTIRELY_AFTER_ENTRY",)
    assert result.rows[1].usable and result.rows[1].reasons == ()
    assert examples.evaluate(current).z1.proof.evidence.source_row_id == UUID(int=21)


def test_publication_uncertainty_does_not_turn_import_time_into_a_publication_clock(case):
    source = replace(case["source"], issue_date=date(2026, 9, 2))
    current = examples.changed_history(
        case,
        [
            examples.row(20, day=date(2026, 9, 2)),
            examples.row(21, day=date(2026, 9, 3)),
            examples.row(22, day=date(2026, 9, 4)),
        ],
    )
    current["source"] = source
    result = review(current)
    assert result.global_reasons == () and result.usable_row_count == 1
    assert [row.reasons for row in result.rows] == [
        ("SOURCE_PUBLICATION_ORDER_NOT_ESTABLISHED",),
        ("SOURCE_PUBLICATION_ORDER_NOT_ESTABLISHED",),
        (),
    ]
    assert examples.evaluate(current).z1.proof.evidence.source_row_id == UUID(int=22)


@pytest.mark.parametrize("day,hours", [(date(2026, 3, 29), 23), (date(2026, 10, 25), 25)])
def test_complete_dst_days_keep_the_actual_local_envelope(case, day, hours):
    at = datetime(2026, 11, 14, 12, tzinfo=UTC)
    original = examples.row(day=day)
    current = examples.changed_history(
        case,
        [original],
        start_date=date(2026, 1, 1),
        end_date=date(2026, 11, 13),
        known_at=at,
    )
    current["position"] = replace(case["position"], opened_at=datetime(2026, 1, 1, tzinfo=UTC))
    current["source"] = replace(case["source"], issue_date=date(2025, 12, 28))
    assert original.interval_end - original.interval_start == timedelta(hours=hours)
    assert review(current, as_of=at).usable_row_count == 1
    assert examples.evaluate(current, assessed_at=at).z1.status == "PROVEN"


@pytest.mark.parametrize("conflicting", [False, True])
def test_duplicate_ids_count_once_and_conflicting_originals_remain_unsuitable(case, conflicting):
    original = examples.row()
    repeated = replace(original, high=Decimal("130")) if conflicting else original
    other = examples.row(21, day=date(2026, 9, 3))
    current = examples.changed_history(case, [original, repeated, other])
    result = review(current)
    assert len(current["history"].rows) == 3
    assert len(result.rows) == 2
    assert result.usable_row_count == (1 if conflicting else 2)
    assert result.rows[0].reasons == (
        ("CONFLICTING_ORIGINAL_PRICE_EVIDENCE",) if conflicting else ()
    )
    assert result.rows[1].usable
    evaluated = examples.evaluate(current)
    assert evaluated.z1.proof.evidence.source_row_id == UUID(int=21 if conflicting else 20)


def test_mixed_rows_keep_first_rejection_reason_order_and_earliest_usable_target(case):
    current = examples.changed_history(
        case,
        [
            examples.row(30, currency="EUR", issues=("IGNORED_AFTER_SCOPE_FAILURE",)),
            examples.row(
                31,
                issues=("EOD_QUALITY_LIMITED", "DATA_NOT_KNOWN_AT_CUTOFF", "EOD_QUALITY_LIMITED"),
                scale_status="ADJUSTMENT_INDICATION_PRESENT",
            ),
            examples.row(32, scale_status="ADJUSTMENT_INDICATION_PRESENT"),
            examples.row(22, day=date(2026, 9, 4)),
            examples.row(21, day=date(2026, 9, 3)),
        ],
    )
    result = review(current)
    assert result.global_reasons == () and result.usable_row_count == 2
    assert [row.source_row_id for row in result.rows] == [UUID(int=n) for n in (30, 31, 32, 22, 21)]
    expected = (
        "ROW_SCOPE_OR_CURRENCY_MISMATCH",
        "ROW_EVIDENCE_UNSUITABLE",
        "EOD_QUALITY_LIMITED",
        "DATA_NOT_KNOWN_AT_CUTOFF",
        "ROW_ADJUSTMENT_REQUIRES_OWNER_EVIDENCE",
    )
    evaluated = examples.evaluate(current)
    assert evaluated.z1.reasons == expected
    assert evaluated.z1.proof.evidence.source_row_id == UUID(int=21)
    assert tuple(dict.fromkeys(reason for row in result.rows for reason in row.reasons)) == expected


def test_empty_available_history_is_explicit_and_not_a_successful_review(case):
    current = examples.changed_history(case, [])
    assert review(current) == TargetInputReview(("NO_SUITABLE_POST_ENTRY_DAILY_EVIDENCE",), 0, ())
    assert examples.evaluate(current).z1.status == "NOT_ASSESSABLE"


@pytest.mark.parametrize("quantity", [-1, True])
def test_invalid_owner_quantity_remains_an_error_instead_of_new_interpretation(case, quantity):
    position = replace(case["position"], remaining_quantity=quantity)
    with pytest.raises(ValueError, match="INVALID_OWNER_REMAINING_QUANTITY"):
        review(case, position=position)
    with pytest.raises(ValueError, match="INVALID_OWNER_REMAINING_QUANTITY"):
        examples.evaluate(case, position=position)


def test_unknown_review_timezone_is_not_filled_in(case):
    with pytest.raises(ValueError, match="ASSESSMENT_TIME_MUST_BE_AWARE"):
        review(case, as_of=examples.NOW.replace(tzinfo=None))
