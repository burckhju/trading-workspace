"""Finite original calendar packages; never trading-status observations."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo

from app.features.market_data.domain.session_evidence import SessionDay, SessionWindow

VERIFICATION = "ENGINEERING_REVIEW_OF_ORIGINAL_CALENDAR_NOT_INDEPENDENT_VERIFICATION"


@dataclass(frozen=True, slots=True)
class ReviewCalendarBinding:
    venue_mic: str
    timezone: str
    valid_from: date
    valid_through: date
    segment: str


@dataclass(frozen=True, slots=True)
class PublishedCalendarDefinition:
    source_version: str
    binding: ReviewCalendarBinding
    closed_dates: tuple[date, ...]
    early_closes: tuple[date, ...]
    opens_at: time
    closes_at: time
    early_close_at: time
    sources: tuple[tuple[str, str], ...]


def calendar_days(definition: PublishedCalendarDefinition) -> tuple[SessionDay, ...]:
    """Expand the published Monday-Friday schedule and its explicit exceptions."""
    binding = definition.binding
    zone = ZoneInfo(binding.timezone)
    days = []
    day = binding.valid_from
    while day <= binding.valid_through:
        closed = day.weekday() >= 5 or day in definition.closed_dates
        end = definition.early_close_at if day in definition.early_closes else definition.closes_at
        intervals = (
            ()
            if closed
            else (
                SessionWindow(
                    datetime.combine(day, definition.opens_at, zone),
                    datetime.combine(day, end, zone),
                ),
            )
        )
        days.append(
            SessionDay(
                day,
                "CLOSED" if closed else "SESSION",
                intervals,
                definition.sources[0][0],
            )
        )
        day += timedelta(days=1)
    return tuple(days)


def dates(values: str) -> tuple[date, ...]:
    return tuple(date.fromisoformat(value) for value in values.split())


NYSE_CALENDAR = PublishedCalendarDefinition(
    "nyse-cash-2025-2027-reviewed-20261118-v1",
    ReviewCalendarBinding(
        "XNYS",
        "America/New_York",
        date(2025, 1, 1),
        date(2027, 12, 31),
        "CORE_CASH_EQUITIES",
    ),
    dates(
        "2025-01-01 2025-01-09 2025-01-20 2025-02-17 2025-04-18 2025-05-26 "
        "2025-06-19 2025-07-04 2025-09-01 2025-11-27 2025-12-25 "
        "2026-01-01 2026-01-19 2026-02-16 2026-04-03 2026-05-25 2026-06-19 "
        "2026-07-03 2026-09-07 2026-11-26 2026-12-25 "
        "2027-01-01 2027-01-18 2027-02-15 2027-03-26 2027-05-31 2027-06-18 "
        "2027-07-05 2027-09-06 2027-11-25 2027-12-24"
    ),
    dates("2025-07-03 2025-11-28 2025-12-24 2026-11-27 2026-12-24 2027-11-26"),
    time(9, 30),
    time(16),
    time(13),
    (
        (
            "https://s2.q4cdn.com/154085107/files/doc_news/NYSE-Group-Announces-2025-2026-and-2027-Holiday-and-Early-Closings-Calendar-2024.pdf",
            "6d719aaaf827c909f362725293c8e932f1b879687e4705eeb8a16f7201fe3355",
        ),
        (
            "https://www.nyse.com/trade/hours-calendars",
            "d7741bc3339e7d188ba219beef2799f4df8e44f8c4d7029b6c1709214726f2fd",
        ),
        (
            "https://s2.q4cdn.com/154085107/files/doc_news/The-New-York-Stock-Exchange-Will-Close-Markets-on-January-9-to-Honor-the-Passing-of-Former-President-Jimmy-Carter-on-National-Day-of--IGCRS.pdf",
            "b83882b2f29554a969c30f5a48c37eff3b6baab449273bfdb3d8c3df62244c69",
        ),
    ),
)


@dataclass(frozen=True, slots=True)
class ReviewDay:
    session_date: date
    status: Literal["SESSION", "CLOSED", "UNKNOWN"]


@dataclass(frozen=True, slots=True)
class ReviewDayCalendarRead:
    workspace_id: UUID
    warrant_id: UUID
    listing_id: UUID
    venue_mic: str
    timezone: str
    known_at: datetime
    recorded_at: datetime | None
    revision_id: UUID | None
    fingerprint: str
    verification: str
    status: Literal["AVAILABLE", "MISSING", "UNSUITABLE"]
    reasons: tuple[str, ...]
    coverage_start: date | None
    coverage_end: date | None
    days: tuple[ReviewDay, ...]
    source_reference: str | None
    valid_from: date | None
    valid_through: date | None
