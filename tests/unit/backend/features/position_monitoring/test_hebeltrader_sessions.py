"""Calendar-day zero and actual completed sessions, using explicit synthetic documents."""

from copy import deepcopy
from dataclasses import asdict, replace
from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest

from app.features.market_data.domain.session_evidence import (
    MAX_SESSION_DAYS,
    SessionBinding,
    SessionDay,
    SessionWindow,
)
from app.features.position_monitoring.domain.hebeltrader_sessions import (
    SessionEntry,
    count_completed_sessions,
    session_anchor,
)

DAY_ZERO = date(2026, 10, 23)
ZONE = ZoneInfo("Europe/Berlin")


def binding(**changes):
    return SessionBinding(
        **(
            dict(
                instrument_kind="UNDERLYING",
                instrument_id=UUID(int=6),
                listing_id=UUID(int=7801),
                trading_venue_id=UUID(int=7802),
                venue_mic="XETR",
                timezone="Europe/Berlin",
                market_segment="Synthetic explicitly documented regular sessions",
                valid_from=date(2026, 1, 1),
                valid_through=date(2026, 12, 31),
            )
            | changes
        )
    )


def exact_entry(day=DAY_ZERO, **changes):
    return SessionEntry(
        **(
            dict(
                execution_id=UUID(int=7803),
                executed_at=datetime.combine(day, time(12), ZONE),
                executed_on=None,
                execution_timezone=None,
                time_precision="EXACT",
            )
            | changes
        )
    )


def original_day(day, *, status="SESSION", windows=None):
    # All dates and closures here are explicitly synthetic source facts, not a
    # production weekday/holiday inference or a generated market calendar.
    return SessionDay(
        session_date=day,
        status=status,
        intervals=(
            windows
            if windows is not None
            else (
                (
                    SessionWindow(
                        datetime.combine(day, time(9), ZONE),
                        datetime.combine(day, time(17, 30), ZONE),
                    ),
                )
                if status == "SESSION"
                else ()
            )
        ),
        source_reference=f"Synthetic original calendar document, explicit row {day}",
    )


def evaluate(days, *, entry=None, clock=None, calendar=None):
    return count_completed_sessions(
        entry=exact_entry() if entry is None else entry,
        binding=binding() if calendar is None else calendar,
        days=tuple(days),
        event_at=clock or datetime(2026, 10, 26, 18, tzinfo=ZONE),
    )


def test_day_zero_and_explicit_closures_do_not_count_and_input_is_immutable():
    days = (
        original_day(DAY_ZERO),
        original_day(date(2026, 10, 24), status="CLOSED"),
        original_day(date(2026, 10, 25), status="CLOSED"),
        original_day(date(2026, 10, 26)),
    )
    before = deepcopy(tuple(asdict(day) for day in days))
    result = evaluate(days)
    assert result.status == "AVAILABLE"
    assert result.anchor_date == DAY_ZERO
    assert result.completed_sessions == 1
    assert result.completed_session_dates == (date(2026, 10, 26),)
    assert result.twentieth_session_date is result.twentieth_closes_at is None
    assert result.threshold_reached is False
    assert tuple(asdict(day) for day in days) == before


@pytest.mark.parametrize("missing_status", [None, "UNKNOWN"])
def test_missing_weekend_day_is_not_invented_as_closed(missing_status):
    days = [original_day(date(2026, 10, 25), status="CLOSED"), original_day(date(2026, 10, 26))]
    if missing_status:
        days.insert(0, original_day(date(2026, 10, 24), status=missing_status))
    result = evaluate(days)
    assert result.status == "NOT_ASSESSABLE"
    assert result.completed_sessions is result.threshold_reached is None
    assert result.completed_session_dates == ()
    assert result.reasons == (
        ("SESSION_DAYS_UNKNOWN",) if missing_status else ("SESSION_DAYS_MISSING",)
    )


def test_twentieth_session_only_counts_at_its_last_close_not_at_later_retrieval():
    days = tuple(original_day(DAY_ZERO + timedelta(days=index)) for index in range(1, 21))
    close = days[-1].intervals[-1].closes_at
    before = evaluate(days, clock=close - timedelta(microseconds=1))
    at = evaluate(days, clock=close)
    assert before.completed_sessions == 19
    assert before.threshold_reached is False
    assert before.twentieth_closes_at is None
    assert at.completed_sessions == 20
    assert at.threshold_reached is True
    assert at.twentieth_session_date == days[-1].session_date
    assert at.twentieth_closes_at == close
    assert at.evaluated_at == close


def test_midday_break_is_not_a_completed_session_and_two_intervals_count_once():
    day = date(2026, 10, 24)
    windows = tuple(
        SessionWindow(
            datetime.combine(day, time(start), ZONE), datetime.combine(day, time(end), ZONE)
        )
        for start, end in ((9, 12), (13, 17))
    )
    row = original_day(day, windows=windows)
    assert evaluate([row], clock=datetime.combine(day, time(12, 30), ZONE)).completed_sessions == 0
    assert evaluate([row], clock=windows[-1].closes_at).completed_sessions == 1


def test_overnight_session_waits_for_its_actual_next_day_close():
    day = date(2026, 10, 24)
    close = datetime(2026, 10, 25, 3, 30, tzinfo=ZONE)
    row = original_day(
        day,
        windows=(SessionWindow(datetime.combine(day, time(22), ZONE), close),),
    )
    days = (row, original_day(day + timedelta(days=1), status="CLOSED"))
    assert (
        evaluate(days, clock=close.astimezone(UTC) - timedelta(seconds=1)).completed_sessions == 0
    )
    assert evaluate(days, clock=close.astimezone(UTC)).completed_sessions == 1


def test_dst_repeated_clock_is_compared_as_instant_not_identical_local_wall_time():
    day = date(2026, 10, 25)
    close = datetime(2026, 10, 25, 2, 30, tzinfo=ZONE, fold=1)
    row = original_day(
        day,
        windows=(SessionWindow(datetime.combine(day, time(1), ZONE), close),),
    )
    days = (original_day(day - timedelta(days=1), status="CLOSED"), row)
    before = datetime(2026, 10, 25, 2, 45, tzinfo=ZONE, fold=0)
    assert evaluate(days, clock=before).completed_sessions == 0
    assert evaluate(days, clock=close).completed_sessions == 1


def test_exact_entry_day_uses_bound_calendar_zone_instead_of_utc_date():
    entry = exact_entry(executed_at=datetime(2026, 10, 23, 23, 30, tzinfo=UTC))
    result = evaluate([], entry=entry, clock=datetime(2026, 10, 24, 10, tzinfo=ZONE))
    assert result.anchor_date == date(2026, 10, 24)
    assert result.completed_sessions == 0


@pytest.mark.parametrize("day", [date(2026, 3, 29), date(2026, 10, 25)])
def test_date_only_entry_preserves_precision_on_23_and_25_hour_days(day):
    entry = exact_entry(
        executed_at=None,
        executed_on=day,
        execution_timezone="Europe/Berlin",
        time_precision="DATE_ONLY",
    )
    result = evaluate([], entry=entry, clock=datetime.combine(day, time(18), ZONE))
    assert result.status == "AVAILABLE"
    assert result.anchor_date == day
    assert result.completed_sessions == 0
    assert entry.executed_at is None


def test_date_only_different_zone_with_multiple_possible_days_is_not_a_midnight_execution():
    entry = exact_entry(
        executed_at=None,
        executed_on=DAY_ZERO,
        execution_timezone="America/New_York",
        time_precision="DATE_ONLY",
    )
    result = evaluate([], entry=entry)
    assert result.status == "NOT_ASSESSABLE"
    assert result.anchor_date is None
    assert result.reasons == ("ENTRY_CALENDAR_DAY_AMBIGUOUS",)


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"executed_at": None}, "ENTRY_TIME_INVALID"),
        ({"executed_at": datetime(2026, 10, 23, 12)}, "ENTRY_TIME_INVALID"),
        ({"executed_on": DAY_ZERO}, "ENTRY_TIME_INVALID"),
        ({"executed_at": datetime(2026, 11, 1, tzinfo=UTC)}, "ENTRY_AFTER_EVALUATION"),
        ({"time_precision": "UNKNOWN"}, "ENTRY_TIME_INVALID"),
        ({"time_precision": "DATE_ONLY", "executed_on": DAY_ZERO}, "ENTRY_TIME_INVALID"),
        (
            {
                "time_precision": "DATE_ONLY",
                "executed_at": None,
                "executed_on": DAY_ZERO,
                "execution_timezone": "Unknown/Zone",
            },
            "ENTRY_TIMEZONE_INVALID",
        ),
        (
            {
                "time_precision": "DATE_ONLY",
                "executed_at": None,
                "executed_on": date(2026, 11, 1),
                "execution_timezone": "Europe/Berlin",
            },
            "ENTRY_AFTER_EVALUATION",
        ),
        (
            {
                "time_precision": "DATE_ONLY",
                "executed_at": None,
                "executed_on": date(2011, 12, 30),
                "execution_timezone": "Pacific/Apia",
            },
            "ENTRY_DATE_INTERVAL_INVALID",
        ),
    ],
)
def test_unsuitable_entry_times_remain_unassessable(changes, reason):
    result = evaluate([], entry=replace(exact_entry(), **changes))
    assert result.status == "NOT_ASSESSABLE"
    assert result.reasons == (reason,)
    assert result.completed_sessions is None


@pytest.mark.parametrize(
    ("calendar", "reason"),
    [
        (binding(valid_from=date(2026, 10, 24)), "ENTRY_OUTSIDE_BINDING_VALIDITY"),
        (binding(valid_through=date(2026, 10, 25)), "EVALUATION_OUTSIDE_BINDING_VALIDITY"),
    ],
)
def test_historical_binding_must_cover_both_anchor_and_evaluation(calendar, reason):
    result = evaluate([], calendar=calendar)
    assert result.reasons == (reason,)
    assert result.completed_sessions is None


def test_unknown_entry_or_binding_is_not_zero_sessions():
    clock = datetime(2026, 10, 26, tzinfo=UTC)
    assert session_anchor(None, binding(), event_at=clock).reasons == ("EFFECTIVE_ENTRY_MISSING",)
    assert session_anchor(exact_entry(), None, event_at=clock).reasons == (
        "SESSION_BINDING_MISSING",
    )
    with pytest.raises(ValueError, match="timezone-aware"):
        session_anchor(exact_entry(), binding(), event_at=clock.replace(tzinfo=None))


@pytest.mark.parametrize("duplicate", [False, True])
def test_conflicting_or_unsorted_days_do_not_count(duplicate):
    first = original_day(date(2026, 10, 24))
    second = original_day(date(2026, 10, 25))
    result = evaluate([first, first] if duplicate else [second, first])
    assert result.reasons == ("SESSION_DAYS_CONFLICT",)


def test_count_range_is_bounded_without_truncating_to_an_apparent_threshold():
    clock = datetime.combine(DAY_ZERO + timedelta(days=MAX_SESSION_DAYS + 1), time(18), ZONE)
    calendar = binding(valid_through=clock.date())
    result = evaluate([], calendar=calendar, clock=clock)
    assert result.reasons == ("SESSION_COUNT_LIMIT",)
    assert result.completed_sessions is result.threshold_reached is None
