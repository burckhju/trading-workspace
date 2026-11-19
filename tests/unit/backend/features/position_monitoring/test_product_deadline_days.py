"""Original day facts count dates only; synthetic rows cannot create trading hours."""

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest
from tests.unit.backend.features.position_monitoring import test_hebeltrader_deadlines as facts

from app.features.market_data.domain.review_calendars import ReviewDay, ReviewDayCalendarRead
from app.features.position_monitoring.domain.product_deadline_days import (
    calculate_product_day_deadline,
)
from app.features.position_monitoring.domain.product_deadline_review import (
    decide_product_deadline_review,
)


def calendar(*, count=31, closed=()):
    start, end = facts.TERM - timedelta(days=count), facts.TERM - timedelta(days=1)
    return ReviewDayCalendarRead(
        facts.WORKSPACE,
        facts.WARRANT,
        facts.LISTING,
        "XSTU",
        "Europe/Berlin",
        facts.KNOWN,
        facts.KNOWN,
        uuid4(),
        "d" * 64,
        "SYNTHETIC_ORIGINAL_DATE_ROWS_NOT_INDEPENDENT_VERIFICATION",
        "AVAILABLE",
        (),
        start,
        end,
        tuple(
            ReviewDay(day, "CLOSED" if day in closed else "SESSION")
            for offset in range(count)
            for day in (start + timedelta(days=offset),)
        ),
        "https://example.invalid/synthetic-original-calendar-dates",
        start,
        end,
    )


def evaluate(*, read=None, at=facts.NOW, **changes):
    return calculate_product_day_deadline(
        **(
            dict(
                workspace_id=facts.WORKSPACE,
                warrant_id=facts.WARRANT,
                exit_listing_id=facts.LISTING,
                exit_venue_mic="XSTU",
                maturity_on=facts.TERM,
                last_trading_on=facts.TERM,
                calendar=calendar() if read is None else read,
                event_at=at,
            )
            | changes
        )
    )


@pytest.mark.parametrize(
    ("at", "stage", "scheduled"),
    [
        (datetime(2026, 10, 10, 23, 59, tzinfo=facts.ZONE), "BEFORE_WARNING", None),
        (datetime(2026, 10, 10, 22, tzinfo=UTC), "WARNING_DAY_REACHED", date(2026, 10, 11)),
        (
            datetime(2026, 10, 11, 23, 59, tzinfo=facts.ZONE),
            "WARNING_DAY_REACHED",
            date(2026, 10, 11),
        ),
        (datetime(2026, 10, 12, 0, tzinfo=facts.ZONE), "DEADLINE_DAY_REACHED", date(2026, 10, 12)),
        (
            datetime(2026, 10, 12, 23, 59, tzinfo=facts.ZONE),
            "DEADLINE_DAY_REACHED",
            date(2026, 10, 12),
        ),
        (datetime(2026, 10, 13, 0, tzinfo=facts.ZONE), "DEADLINE_DAY_PASSED", date(2026, 10, 12)),
        (datetime(2027, 1, 1, 12, tzinfo=facts.ZONE), "DEADLINE_DAY_PASSED", date(2026, 10, 12)),
    ],
)
def test_day_boundaries_keep_original_dates_without_invented_midnight_session(at, stage, scheduled):
    calculation = evaluate(at=at)
    result = decide_product_deadline_review(closed=False, calculation=calculation)
    assert result.outcome == stage
    assert result.scheduled_on == scheduled
    assert result.scheduled_at is None
    assert calculation.exit_session_opens_at is None
    assert calculation.calendar_session_closes_at is None
    assert calculation.warning_at is None
    assert calculation.calendar_precision == "DAY_ONLY"
    assert calculation.scope == "DAY_ONLY_CALENDAR_REVIEW"
    assert calculation.calendar_timezone == "Europe/Berlin"
    assert result.qualified_b05 is False and result.product_cutoff_status == "UNVERIFIED"


def test_closed_original_rows_and_excluded_term_move_day_count_without_price():
    result = evaluate(read=calendar(closed=(date(2026, 10, 11), date(2026, 10, 18))))
    assert result.exit_session_date == date(2026, 10, 10)
    assert result.warning_session_date == date(2026, 10, 9)
    assert len(result.preceding_session_dates) == 20
    assert facts.TERM not in result.preceding_session_dates


@pytest.mark.parametrize(
    ("count", "status", "reason"),
    [
        (19, "NOT_ASSESSABLE", "TWENTY_PRODUCT_SESSIONS_MISSING"),
        (20, "PARTIAL", "PREWARNING_PRODUCT_SESSION_MISSING"),
        (21, "AVAILABLE", None),
    ],
)
def test_nineteen_twenty_twenty_one_sessions_do_not_fill_missing_warning(count, status, reason):
    result = evaluate(read=calendar(count=count))
    assert result.status == status
    assert result.reasons == ((reason,) if reason else ())
    if count == 20:
        assert result.stage is None


@pytest.mark.parametrize("field", ["workspace_id", "warrant_id", "listing_id"])
def test_calendar_cannot_be_rebound_to_a_different_product_or_personal_listing(field):
    result = evaluate(read=replace(calendar(), **{field: uuid4()}))
    assert result.reasons == ("PRODUCT_DAY_CALENDAR_SCOPE_MISMATCH",)


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ({"venue_mic": "XFRA"}, "PRODUCT_DAY_CALENDAR_SCOPE_MISMATCH"),
        ({"status": "MISSING"}, "PRODUCT_DAY_CALENDAR_UNSUITABLE"),
        ({"status": "UNSUITABLE"}, "PRODUCT_DAY_CALENDAR_UNSUITABLE"),
        ({"revision_id": None}, "PRODUCT_DAY_CALENDAR_UNSUITABLE"),
        ({"source_reference": None}, "PRODUCT_DAY_CALENDAR_UNSUITABLE"),
        ({"recorded_at": None}, "PRODUCT_DAY_CALENDAR_TIME_INVALID"),
        ({"known_at": facts.NOW + timedelta(days=1)}, "PRODUCT_DAY_CALENDAR_TIME_INVALID"),
        ({"timezone": "Not/A_Real_Zone"}, "PRODUCT_DAY_CALENDAR_ZONE_INVALID"),
        ({"coverage_end": date(2026, 10, 30)}, "PRODUCT_DAY_CALENDAR_RANGE_INCOMPLETE"),
        ({"valid_through": date(2026, 10, 30)}, "PRODUCT_DAY_CALENDAR_RANGE_INCOMPLETE"),
    ],
)
def test_qualified_day_reminder_requires_original_knowledge_and_exact_coverage(change, reason):
    result = evaluate(read=replace(calendar(), **change))
    assert result.status == "NOT_ASSESSABLE"
    assert reason in result.reasons


@pytest.mark.parametrize("mode", ["missing", "duplicate", "unordered", "unknown"])
def test_missing_conflicting_or_unknown_rows_are_never_generated_as_business_days(mode):
    read = calendar()
    days = read.days
    changed = {
        "missing": days[1:],
        "duplicate": (days[0], *days),
        "unordered": tuple(reversed(days)),
        "unknown": (replace(days[0], status="UNKNOWN"), *days[1:]),
    }[mode]
    result = evaluate(read=replace(read, days=changed))
    assert result.status == "NOT_ASSESSABLE"
    assert result.stage is None


def test_missing_later_year_coverage_is_not_extended_from_previous_year():
    result = evaluate(maturity_on=date(2027, 1, 15), last_trading_on=date(2027, 1, 15))
    assert result.reasons == ("PRODUCT_DAY_CALENDAR_RANGE_INCOMPLETE",)


def test_naive_evaluation_clock_is_rejected():
    with pytest.raises(ValueError, match="aware"):
        evaluate(at=facts.NOW.replace(tzinfo=None))
