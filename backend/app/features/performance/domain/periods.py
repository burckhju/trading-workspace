"""Calendar interval membership without turning date-only anchors into executions."""

from datetime import UTC, date, datetime, time, timedelta
from typing import Literal, TypedDict
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.features.performance.domain.models import (
    ExecutionFact,
    ExecutionTime,
    PeriodStatus,
    ReportFilters,
)


def day_start(day: date, zone: ZoneInfo) -> datetime:
    naive = datetime.combine(day, time.min)
    candidates = {
        aware.astimezone(UTC)
        for fold in (0, 1)
        if (aware := naive.replace(tzinfo=zone, fold=fold))
        .astimezone(UTC)
        .astimezone(zone)
        .replace(tzinfo=None)
        == naive
    }
    if len(candidates) != 1:
        raise ValueError("Local day boundary is nonexistent or ambiguous")
    return candidates.pop()


def day_interval(first: date, last: date, zone_name: str) -> tuple[datetime, datetime]:
    if first > last:
        raise ValueError("from_date must not follow to_date")
    try:
        zone = ZoneInfo(zone_name)
        start = day_start(first, zone)
        end = day_start(last + timedelta(days=1), zone)
    except (OverflowError, ZoneInfoNotFoundError, ValueError) as error:
        raise ValueError("Calendar dates or timezone boundaries are unsupported") from error
    if end <= start:
        raise ValueError("Calendar interval must not be empty")
    return start, end


def report_interval(filters: ReportFilters) -> tuple[datetime, datetime]:
    code = filters.report_currency
    if len(code) != 3 or not code.isascii() or not code.isalpha() or code != code.upper():
        raise ValueError("report_currency requires an uppercase three-letter currency code")
    return day_interval(filters.from_date, filters.to_date, filters.report_timezone)


def execution_time(execution: ExecutionFact) -> ExecutionTime:
    if execution.executed_on is not None and execution.execution_timezone is not None:
        start: datetime | None
        end: datetime | None
        try:
            start, end = day_interval(
                execution.executed_on, execution.executed_on, execution.execution_timezone
            )
        except ValueError:
            start = end = None
        return ExecutionTime(
            time_precision="DATE_ONLY",
            executed_at=None,
            executed_on=execution.executed_on,
            execution_timezone=execution.execution_timezone,
            recorded_at=execution.recorded_at,
            possible_start_at=start,
            possible_end_at=end,
        )
    precise = (
        execution.executed_on is None
        and execution.execution_timezone is None
        and execution.executed_at.utcoffset() is not None
    )
    return ExecutionTime(
        time_precision="TIMESTAMP" if precise else "UNKNOWN",
        executed_at=execution.executed_at if precise else None,
        executed_on=execution.executed_on,
        execution_timezone=execution.execution_timezone,
        recorded_at=execution.recorded_at,
        possible_start_at=None,
        possible_end_at=None,
    )


def classify_period(view: ExecutionTime, start: datetime, end: datetime) -> PeriodStatus:
    if view.time_precision == "TIMESTAMP" and view.executed_at is not None:
        return "IN_PERIOD" if start <= view.executed_at < end else "OUTSIDE_PERIOD"
    possible_start, possible_end = view.possible_start_at, view.possible_end_at
    if possible_start is None or possible_end is None:
        return "PERIOD_UNKNOWN"
    if start <= possible_start and possible_end <= end:
        return "IN_PERIOD"
    if possible_end <= start or possible_start >= end:
        return "OUTSIDE_PERIOD"
    return "PERIOD_AMBIGUOUS"


class TimeFields(TypedDict):
    time_precision: Literal["TIMESTAMP", "DATE_ONLY", "UNKNOWN"]
    executed_at: datetime | None
    executed_on: date | None
    execution_timezone: str | None
    recorded_at: datetime
    possible_start_at: datetime | None
    possible_end_at: datetime | None


def time_fields(execution: ExecutionFact) -> TimeFields:
    view = execution_time(execution)
    return TimeFields(
        time_precision=view.time_precision,
        executed_at=view.executed_at,
        executed_on=view.executed_on,
        execution_timezone=view.execution_timezone,
        recorded_at=view.recorded_at,
        possible_start_at=view.possible_start_at,
        possible_end_at=view.possible_end_at,
    )
