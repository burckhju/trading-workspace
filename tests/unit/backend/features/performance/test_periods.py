from dataclasses import replace
from datetime import UTC, date, datetime, timedelta

import pytest
from tests.unit.backend.features.performance.fixtures import SEPTEMBER, execution

from app.features.performance.domain.models import ReportFilters
from app.features.performance.domain.periods import (
    classify_period,
    day_interval,
    execution_time,
    report_interval,
)


@pytest.mark.parametrize(
    "day,start,end,hours",
    [
        ("2026-03-29", "2026-03-28T23:00Z", "2026-03-29T22:00Z", 23),
        ("2026-10-25", "2026-10-24T22:00Z", "2026-10-25T23:00Z", 25),
        ("2026-12-31", "2026-12-30T23:00Z", "2026-12-31T23:00Z", 24),
    ],
)
def test_calendar_days_use_separate_local_boundaries(
    day: str, start: str, end: str, hours: int
) -> None:
    filters = ReportFilters(
        date.fromisoformat(day), date.fromisoformat(day), "EUR", "Europe/Berlin"
    )
    actual = report_interval(filters)
    assert actual == (datetime.fromisoformat(start), datetime.fromisoformat(end))
    assert actual[1] - actual[0] == timedelta(hours=hours)


@pytest.mark.parametrize(
    "instant,expected",
    [
        ("2026-08-31T21:59:59.999999Z", "OUTSIDE_PERIOD"),
        ("2026-08-31T22:00:00Z", "IN_PERIOD"),
        ("2026-09-30T21:59:59.999999Z", "IN_PERIOD"),
        ("2026-09-30T22:00:00Z", "OUTSIDE_PERIOD"),
        ("2026-10-01T00:00:00+02:00", "OUTSIDE_PERIOD"),
    ],
)
def test_precise_instants_obey_half_open_month(instant: str, expected: str) -> None:
    fact = replace(
        execution(1, "SELL", 1, "2", "2026-09-01", zone=None),
        executed_at=datetime.fromisoformat(instant),
    )
    view = execution_time(fact)
    assert view.time_precision == "TIMESTAMP"
    assert classify_period(view, *report_interval(SEPTEMBER)) == expected


def test_both_offset_bound_autumn_instants_belong_to_the_25_hour_day() -> None:
    day = date(2026, 10, 25)
    interval = day_interval(day, day, "Europe/Berlin")
    instants = []
    for offset in ("+02:00", "+01:00"):
        instant = datetime.fromisoformat("2026-10-25T02:30:00" + offset)
        fact = replace(
            execution(1, "SELL", 1, "2", day.isoformat(), zone=None), executed_at=instant
        )
        assert classify_period(execution_time(fact), *interval) == "IN_PERIOD"
        instants.append(instant.astimezone(UTC))
    assert instants[1] - instants[0] == timedelta(hours=1)


@pytest.mark.parametrize(
    "day,zone,expected",
    [
        ("2026-09-02", "Asia/Tokyo", "IN_PERIOD"),
        ("2026-09-01", "Asia/Tokyo", "PERIOD_AMBIGUOUS"),
        ("2026-10-01", "Asia/Tokyo", "PERIOD_AMBIGUOUS"),
        ("2026-08-31", "America/New_York", "PERIOD_AMBIGUOUS"),
        ("2026-09-30", "America/New_York", "PERIOD_AMBIGUOUS"),
        ("2026-08-31", "Europe/Berlin", "OUTSIDE_PERIOD"),
        ("2026-10-01", "Europe/Berlin", "OUTSIDE_PERIOD"),
        ("2026-09-01", "Europe/Berlin", "IN_PERIOD"),
        ("2026-09-30", "Europe/Berlin", "IN_PERIOD"),
    ],
)
def test_date_only_possible_day_is_preserved(day: str, zone: str, expected: str) -> None:
    fact = execution(1, "SELL", 1, "2", day, zone=zone)
    view = execution_time(fact)
    assert view.time_precision == "DATE_ONLY"
    assert view.executed_at is None
    assert view.executed_on == date.fromisoformat(day)
    assert view.execution_timezone == zone
    assert view.possible_start_at is not None and view.possible_end_at is not None
    assert classify_period(view, *report_interval(SEPTEMBER)) == expected


@pytest.mark.parametrize(
    "first,last,zone",
    [
        (date(2026, 9, 30), date(2026, 9, 1), "Europe/Berlin"),
        (date(9999, 12, 31), date(9999, 12, 31), "UTC"),
        (date(2026, 9, 1), date(2026, 9, 30), "Imaginary/Zone"),
        (date(2011, 12, 30), date(2011, 12, 30), "Pacific/Apia"),
        (date(2026, 11, 1), date(2026, 11, 1), "America/Havana"),
    ],
)
def test_invalid_or_unsupported_report_boundaries_are_input_errors(
    first: date, last: date, zone: str
) -> None:
    with pytest.raises(ValueError):
        day_interval(first, last, zone)


@pytest.mark.parametrize("currency", ["eur", "EU", "EURO", "€UR", "123"])
def test_currency_filter_requires_explicit_code(currency: str) -> None:
    with pytest.raises(ValueError):
        report_interval(replace(SEPTEMBER, report_currency=currency))


@pytest.mark.parametrize("kind", ["zone", "pair", "naive", "skipped", "ambiguous"])
def test_invalid_source_dates_are_unknown_without_invented_anchor_time(kind: str) -> None:
    fact = execution(1, "SELL", 1, "2", "2026-09-01")
    if kind == "zone":
        fact = replace(fact, execution_timezone="Imaginary/Zone")
    elif kind == "pair":
        fact = replace(fact, execution_timezone=None)
    elif kind == "naive":
        fact = replace(
            fact, executed_on=None, execution_timezone=None, executed_at=datetime(2026, 9, 1)
        )
    elif kind == "skipped":
        fact = execution(1, "SELL", 1, "2", "2011-12-30", zone="Pacific/Apia")
    else:
        fact = execution(1, "SELL", 1, "2", "2026-11-01", zone="America/Havana")
    view = execution_time(fact)
    assert view.executed_at is None
    assert classify_period(view, *report_interval(SEPTEMBER)) == "PERIOD_UNKNOWN"
