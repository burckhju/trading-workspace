"""Partial date reminders reuse documented B05 arithmetic without any price."""

from dataclasses import replace
from datetime import datetime, timedelta

import pytest
from tests.unit.backend.features.position_monitoring import test_hebeltrader_deadlines as facts

from app.features.position_monitoring.domain.product_deadline_review import (
    ACTIVATION_SCOPE,
    RULE_SCOPE,
    RULE_VERSION,
    decide_product_deadline_review,
    desired_deadline_episode,
)


def evaluate(*, event_at, calendar=None, problems=(), closed=False):
    calculation = facts.evaluate(read=calendar, event_at=event_at)
    return decide_product_deadline_review(
        closed=closed, calculation=calculation, input_problems=problems
    )


@pytest.mark.parametrize(
    ("event", "stage", "due", "scheduled"),
    [
        ((2026, 10, 11, 7, 59, 59), "BEFORE_WARNING", False, None),
        ((2026, 10, 11, 8, 0, 0), "WARNING_DUE", True, (2026, 10, 11, 8)),
        ((2026, 10, 12, 7, 59, 59), "WARNING_DUE", True, (2026, 10, 11, 8)),
        ((2026, 10, 12, 8, 0, 0), "EXIT_SESSION_STARTED", True, (2026, 10, 12, 8)),
        ((2026, 10, 12, 21, 59, 59), "EXIT_SESSION_STARTED", True, (2026, 10, 12, 8)),
        ((2026, 10, 12, 22, 0, 0), "CALENDAR_SESSION_ENDED", True, (2026, 10, 12, 22)),
        ((2026, 12, 1, 8, 0, 0), "CALENDAR_SESSION_ENDED", True, (2026, 10, 12, 22)),
    ],
)
def test_documented_stage_boundaries_and_late_detection_do_not_backdate_delivery(
    event, stage, due, scheduled
):
    result = evaluate(event_at=datetime(*event, tzinfo=facts.ZONE))
    assert result.outcome == stage
    assert result.reminder_due is due
    assert result.scheduled_at == (
        datetime(*scheduled, tzinfo=facts.ZONE) if scheduled is not None else None
    )
    assert result.calculation.evaluated_at == datetime(*event, tzinfo=facts.ZONE)
    assert result.qualified_b05 is False
    assert result.product_cutoff_status == "UNVERIFIED"
    assert result.decision_kind == "POSITION_REVIEW"
    assert result.scope == RULE_SCOPE == "DOCUMENTED_PRODUCT_DEADLINE_REVIEW_V1"
    assert result.rule_version == RULE_VERSION == "product-deadline-review-v1"
    assert ACTIVATION_SCOPE == "INDICATIVE_ENTRY_V2"
    assert desired_deadline_episode("DEADLINE_REVIEW", result) is due
    assert desired_deadline_episode("DATA_UNAVAILABLE", result) is False


@pytest.mark.parametrize(
    "reason",
    [
        "PRODUCT_EXIT_LISTING_MISSING",
        "PRODUCT_DEADLINE_EVIDENCE_UNAVAILABLE",
        "PRODUCT_LAST_TRADING_DAY_EVIDENCE_MISSING",
        "PRODUCT_DEADLINE_KNOWLEDGE_TIME_INVALID",
        "PRODUCT_EXIT_CALENDAR_VENUE_MISMATCH",
    ],
)
def test_missing_product_premise_keeps_prior_event_and_separate_data_problem(reason):
    result = evaluate(event_at=datetime(2026, 10, 12, 12, tzinfo=facts.ZONE), problems=(reason,))
    assert result.outcome == "UNAVAILABLE"
    assert result.reasons == (reason,)
    assert result.scheduled_at is None
    assert desired_deadline_episode("DEADLINE_REVIEW", result) is None
    assert desired_deadline_episode("DATA_UNAVAILABLE", result) is True


@pytest.mark.parametrize("count", [0, 19, 20])
def test_missing_or_insufficient_documented_warning_cannot_invent_earlier_notice(count):
    calendar = (
        replace(facts.calendar(), status="MISSING", days=(), reasons=("SESSION_EVIDENCE_MISSING",))
        if count == 0
        else facts.calendar(start=facts.TERM - timedelta(days=count))
    )
    result = evaluate(event_at=facts.NOW, calendar=calendar)
    assert result.outcome == "UNAVAILABLE"
    assert result.reminder_due is None
    assert result.scheduled_at is None


def test_exactly_twenty_sessions_allow_documented_day_reminder_without_invented_pre_warning():
    calendar = facts.calendar(start=facts.TERM - timedelta(days=20))
    result = evaluate(event_at=datetime(2026, 10, 12, 12, tzinfo=facts.ZONE), calendar=calendar)
    assert result.outcome == "EXIT_SESSION_STARTED"
    assert result.reminder_due is True
    assert result.reasons == ("PREWARNING_PRODUCT_SESSION_MISSING",)
    assert result.calculation.warning_at is None
    assert result.product_cutoff_status == "UNVERIFIED"


@pytest.mark.parametrize("present", [False, True])
def test_full_sale_closes_all_notice_kinds_despite_missing_inputs(present):
    result = decide_product_deadline_review(
        closed=True,
        calculation=facts.evaluate() if present else None,
        input_problems=("PRODUCT_EXIT_LISTING_MISSING",),
    )
    assert result.outcome == "CLOSED"
    assert result.calculation is None
    assert result.reasons == ()
    assert desired_deadline_episode("DEADLINE_REVIEW", result) is False
    assert desired_deadline_episode("DATA_UNAVAILABLE", result) is False


def test_absent_calculation_is_an_explicit_gap():
    result = decide_product_deadline_review(closed=False, calculation=None)
    assert result.outcome == "UNAVAILABLE"
    assert result.reasons == ("PRODUCT_DEADLINE_INPUTS_MISSING",)
