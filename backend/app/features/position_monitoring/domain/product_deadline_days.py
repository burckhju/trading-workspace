"""Date-only B05 preparation from explicit original calendar rows.

A day classified SESSION supports counting that date, not an instrument's
opening, closing time or executable B20 cutoff. The scheduled date is retained
separately from the actual later detection clock.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING, Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.features.market_data.domain.session_evidence import MAX_SESSION_DAYS

if TYPE_CHECKING:
    from app.features.market_data.domain.review_calendars import ReviewDayCalendarRead

type ProductDayDeadlineStage = Literal[
    "BEFORE_WARNING", "WARNING_DAY_REACHED", "DEADLINE_DAY_REACHED", "DEADLINE_DAY_PASSED"
]


@dataclass(frozen=True, slots=True)
class ProductDeadlineDayCalculation:
    status: Literal["AVAILABLE", "PARTIAL", "NOT_ASSESSABLE"]
    evaluated_at: datetime
    relevant_product_date: date | None
    exit_session_date: date | None
    warning_session_date: date | None
    preceding_session_dates: tuple[date, ...]
    stage: ProductDayDeadlineStage | None
    reasons: tuple[str, ...]
    calendar_revision_id: UUID | None
    calendar_fingerprint: str | None
    calendar_verification: str | None
    calendar_timezone: str | None
    calendar_precision: Literal["DAY_ONLY"] = "DAY_ONLY"
    exit_session_opens_at: None = None
    calendar_session_closes_at: None = None
    warning_at: None = None
    sessions_before_product_date: Literal[20] = 20
    scope: Literal["DAY_ONLY_CALENDAR_REVIEW"] = "DAY_ONLY_CALENDAR_REVIEW"
    rule_status: Literal["B05_PARTIAL_B20_UNVERIFIED"] = "B05_PARTIAL_B20_UNVERIFIED"


def calculate_product_day_deadline(
    *,
    workspace_id: UUID,
    warrant_id: UUID,
    exit_listing_id: UUID | None,
    exit_venue_mic: str | None,
    maturity_on: date | None,
    last_trading_on: date | None,
    calendar: ReviewDayCalendarRead | None,
    event_at: datetime,
) -> ProductDeadlineDayCalculation:
    if event_at.utcoffset() is None:
        raise ValueError("Product day reminder requires an aware clock")
    terminal = min(maturity_on, last_trading_on) if maturity_on and last_trading_on else None
    problems: list[str] = []
    if maturity_on is None:
        problems.append("PRODUCT_MATURITY_EVIDENCE_MISSING")
    if last_trading_on is None:
        problems.append("PRODUCT_LAST_TRADING_DAY_EVIDENCE_MISSING")
    if exit_listing_id is None or not exit_venue_mic:
        problems.append("PRODUCT_EXIT_LISTING_MISSING")
    if terminal == date.min:
        problems.append("PRODUCT_DATE_HAS_NO_PRECEDING_SESSION_RANGE")
    if calendar is None:
        problems.append("PRODUCT_DAY_CALENDAR_MISSING")
    if problems or terminal is None or calendar is None:
        return _unavailable(calendar, event_at, terminal, tuple(problems))
    if (
        calendar.workspace_id != workspace_id
        or calendar.warrant_id != warrant_id
        or calendar.listing_id != exit_listing_id
        or calendar.venue_mic != exit_venue_mic
    ):
        return _unavailable(calendar, event_at, terminal, ("PRODUCT_DAY_CALENDAR_SCOPE_MISMATCH",))
    if (
        calendar.status != "AVAILABLE"
        or calendar.reasons
        or calendar.revision_id is None
        or not calendar.fingerprint
        or not calendar.source_reference
        or not calendar.verification
    ):
        return _unavailable(
            calendar,
            event_at,
            terminal,
            ("PRODUCT_DAY_CALENDAR_UNSUITABLE", *calendar.reasons),
        )
    if (
        calendar.known_at.utcoffset() is None
        or calendar.recorded_at is None
        or calendar.recorded_at.utcoffset() is None
        or not calendar.recorded_at.astimezone(UTC)
        <= calendar.known_at.astimezone(UTC)
        <= event_at.astimezone(UTC)
    ):
        return _unavailable(calendar, event_at, terminal, ("PRODUCT_DAY_CALENDAR_TIME_INVALID",))
    try:
        zone = ZoneInfo(calendar.timezone)
    except (ValueError, ZoneInfoNotFoundError):
        return _unavailable(calendar, event_at, terminal, ("PRODUCT_DAY_CALENDAR_ZONE_INVALID",))
    start, end = calendar.coverage_start, terminal - timedelta(days=1)
    if (
        start is None
        or start > end
        or calendar.coverage_end is None
        or calendar.coverage_end < end
        or calendar.valid_from is None
        or calendar.valid_through is None
        or calendar.valid_from > start
        or calendar.valid_through < end
        or (end - start).days >= MAX_SESSION_DAYS
    ):
        return _unavailable(
            calendar, event_at, terminal, ("PRODUCT_DAY_CALENDAR_RANGE_INCOMPLETE",)
        )
    relevant = tuple(day for day in calendar.days if start <= day.session_date <= end)
    dates = [day.session_date for day in relevant]
    expected = [start + timedelta(days=offset) for offset in range((end - start).days + 1)]
    if dates != expected:
        return _unavailable(calendar, event_at, terminal, ("PRODUCT_DAY_CALENDAR_ROWS_INCOMPLETE",))
    if any(day.status not in {"SESSION", "CLOSED"} for day in relevant):
        return _unavailable(calendar, event_at, terminal, ("PRODUCT_DAY_CALENDAR_ROWS_UNSUITABLE",))
    sessions = tuple(day.session_date for day in relevant if day.status == "SESSION")
    if len(sessions) < 20:
        return _unavailable(calendar, event_at, terminal, ("TWENTY_PRODUCT_SESSIONS_MISSING",))
    exit_day = sessions[-20]
    warning_day = sessions[-21] if len(sessions) >= 21 else None
    local_day = event_at.astimezone(zone).date()
    stage: ProductDayDeadlineStage | None
    if local_day > exit_day:
        stage = "DEADLINE_DAY_PASSED"
    elif local_day == exit_day:
        stage = "DEADLINE_DAY_REACHED"
    elif warning_day is not None:
        stage = "WARNING_DAY_REACHED" if local_day >= warning_day else "BEFORE_WARNING"
    else:
        stage = None
    return ProductDeadlineDayCalculation(
        status="AVAILABLE" if warning_day else "PARTIAL",
        evaluated_at=event_at,
        relevant_product_date=terminal,
        exit_session_date=exit_day,
        warning_session_date=warning_day,
        preceding_session_dates=sessions[-20:],
        stage=stage,
        reasons=() if warning_day else ("PREWARNING_PRODUCT_SESSION_MISSING",),
        calendar_revision_id=calendar.revision_id,
        calendar_fingerprint=calendar.fingerprint,
        calendar_verification=calendar.verification,
        calendar_timezone=calendar.timezone,
    )


def _unavailable(
    calendar: ReviewDayCalendarRead | None,
    event_at: datetime,
    terminal: date | None,
    reasons: tuple[str, ...],
) -> ProductDeadlineDayCalculation:
    return ProductDeadlineDayCalculation(
        "NOT_ASSESSABLE",
        event_at,
        terminal,
        None,
        None,
        (),
        None,
        reasons,
        calendar.revision_id if calendar else None,
        calendar.fingerprint if calendar else None,
        calendar.verification if calendar else None,
        calendar.timezone if calendar else None,
    )
