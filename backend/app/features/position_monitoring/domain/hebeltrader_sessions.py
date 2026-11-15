"""Completed documented sessions after an original day zero, without rule activation."""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.features.market_data.domain.session_evidence import (
    MAX_SESSION_DAYS,
    SessionBinding,
    SessionDay,
)


@dataclass(frozen=True, slots=True)
class SessionEntry:
    execution_id: UUID
    executed_at: datetime | None
    executed_on: date | None
    execution_timezone: str | None
    time_precision: Literal["EXACT", "DATE_ONLY"]


@dataclass(frozen=True, slots=True)
class SessionAnchor:
    day: date | None
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CompletedSessionCount:
    status: Literal["AVAILABLE", "NOT_ASSESSABLE", "NOT_APPLICABLE"]
    anchor_date: date | None
    evaluated_at: datetime
    completed_sessions: int | None
    completed_session_dates: tuple[date, ...]
    twentieth_session_date: date | None
    twentieth_closes_at: datetime | None
    threshold_reached: bool | None
    reasons: tuple[str, ...]
    threshold_sessions: Literal[20] = 20


def session_anchor(
    entry: SessionEntry | None, binding: SessionBinding | None, *, event_at: datetime
) -> SessionAnchor:
    """Resolve a calendar day, never the ordering anchor of a date-only execution."""
    if event_at.utcoffset() is None:
        raise ValueError("The evaluation event requires a timezone-aware clock")
    if entry is None:
        return SessionAnchor(None, ("EFFECTIVE_ENTRY_MISSING",))
    if binding is None:
        return SessionAnchor(None, ("SESSION_BINDING_MISSING",))
    try:
        zone = ZoneInfo(binding.timezone)
        if entry.time_precision == "EXACT":
            if (
                entry.executed_at is None
                or entry.executed_at.utcoffset() is None
                or entry.executed_on is not None
            ):
                return SessionAnchor(None, ("ENTRY_TIME_INVALID",))
            if entry.executed_at.astimezone(UTC) > event_at.astimezone(UTC):
                return SessionAnchor(None, ("ENTRY_AFTER_EVALUATION",))
            day = entry.executed_at.astimezone(zone).date()
        elif entry.time_precision == "DATE_ONLY":
            if (
                entry.executed_on is None
                or entry.execution_timezone is None
                or entry.executed_at is not None
                or entry.executed_on == date.max
            ):
                return SessionAnchor(None, ("ENTRY_TIME_INVALID",))
            entry_zone = ZoneInfo(entry.execution_timezone)
            start = datetime.combine(entry.executed_on, time.min, entry_zone).astimezone(UTC)
            end = datetime.combine(
                entry.executed_on + timedelta(days=1), time.min, entry_zone
            ).astimezone(UTC)
            if end <= start:
                return SessionAnchor(None, ("ENTRY_DATE_INTERVAL_INVALID",))
            if start > event_at.astimezone(UTC):
                return SessionAnchor(None, ("ENTRY_AFTER_EVALUATION",))
            first = start.astimezone(zone).date()
            last = (end - timedelta(microseconds=1)).astimezone(zone).date()
            if first != last:
                return SessionAnchor(None, ("ENTRY_CALENDAR_DAY_AMBIGUOUS",))
            day = first
        else:
            return SessionAnchor(None, ("ENTRY_TIME_INVALID",))
    except (ZoneInfoNotFoundError, ValueError, OverflowError):
        return SessionAnchor(None, ("ENTRY_TIMEZONE_INVALID",))
    if not binding.valid_from <= day <= binding.valid_through:
        return SessionAnchor(day, ("ENTRY_OUTSIDE_BINDING_VALIDITY",))
    if day > event_at.astimezone(zone).date():
        return SessionAnchor(None, ("ENTRY_AFTER_EVALUATION",))
    return SessionAnchor(day, ())


def unavailable_session_count(
    *,
    event_at: datetime,
    anchor_date: date | None,
    reasons: tuple[str, ...],
    applicable: bool = True,
) -> CompletedSessionCount:
    return CompletedSessionCount(
        status="NOT_ASSESSABLE" if applicable else "NOT_APPLICABLE",
        anchor_date=anchor_date,
        evaluated_at=event_at,
        completed_sessions=None,
        completed_session_dates=(),
        twentieth_session_date=None,
        twentieth_closes_at=None,
        threshold_reached=None,
        reasons=reasons,
    )


def count_completed_sessions(
    *,
    entry: SessionEntry | None,
    binding: SessionBinding | None,
    days: tuple[SessionDay, ...],
    event_at: datetime,
) -> CompletedSessionCount:
    """Count after day zero at the supplied event clock, not a later fetch clock.

    Callers must also qualify the document revision and complete owner-read scope.
    Missing/unknown dates never stand in for holidays. A multi-interval session
    counts only once, after its final documented close, including overnight closes.
    """
    anchor = session_anchor(entry, binding, event_at=event_at)
    if anchor.reasons or binding is None or anchor.day is None:
        return unavailable_session_count(
            event_at=event_at, anchor_date=anchor.day, reasons=anchor.reasons
        )
    last_day = event_at.astimezone(ZoneInfo(binding.timezone)).date()
    if last_day > binding.valid_through:
        return unavailable_session_count(
            event_at=event_at,
            anchor_date=anchor.day,
            reasons=("EVALUATION_OUTSIDE_BINDING_VALIDITY",),
        )
    if (last_day - anchor.day).days > MAX_SESSION_DAYS:
        return unavailable_session_count(
            event_at=event_at, anchor_date=anchor.day, reasons=("SESSION_COUNT_LIMIT",)
        )
    relevant = tuple(day for day in days if anchor.day < day.session_date <= last_day)
    dates = [day.session_date for day in relevant]
    if len(set(dates)) != len(dates) or dates != sorted(dates):
        return unavailable_session_count(
            event_at=event_at, anchor_date=anchor.day, reasons=("SESSION_DAYS_CONFLICT",)
        )
    expected_dates = {
        anchor.day + timedelta(days=offset) for offset in range(1, (last_day - anchor.day).days + 1)
    }
    reasons: list[str] = []
    if expected_dates != set(dates):
        reasons.append("SESSION_DAYS_MISSING")
    if any(day.status == "UNKNOWN" for day in relevant):
        reasons.append("SESSION_DAYS_UNKNOWN")
    if reasons:
        return unavailable_session_count(
            event_at=event_at, anchor_date=anchor.day, reasons=tuple(reasons)
        )
    completed = tuple(
        day
        for day in relevant
        if day.status == "SESSION"
        and day.intervals[-1].closes_at.astimezone(UTC) <= event_at.astimezone(UTC)
    )
    twentieth = completed[19] if len(completed) >= 20 else None
    return CompletedSessionCount(
        status="AVAILABLE",
        anchor_date=anchor.day,
        evaluated_at=event_at,
        completed_sessions=len(completed),
        completed_session_dates=tuple(day.session_date for day in completed),
        twentieth_session_date=twentieth.session_date if twentieth else None,
        twentieth_closes_at=twentieth.intervals[-1].closes_at if twentieth else None,
        threshold_reached=twentieth is not None,
        reasons=(),
    )
