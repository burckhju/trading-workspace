"""B05/B17-B19 calendar arithmetic; no source verification, activation or price input.

Product must eventually supply qualified term dates and the fixed exit listing.
This pure preparation accepts those dates explicitly, consumes the existing
Market-Data calendar read, and exposes its limited calculation scope. A calendar
close is not promoted to a verified instrument-specific B20 execution deadline.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Literal
from uuid import UUID

from app.features.market_data.domain.session_evidence import (
    MAX_SESSION_DAYS,
    SessionEvidenceRead,
)

type DeadlineStage = Literal[
    "BEFORE_WARNING", "WARNING_DUE", "EXIT_SESSION_STARTED", "CALENDAR_SESSION_ENDED"
]


@dataclass(frozen=True, slots=True)
class ProductDeadlineCalculation:
    status: Literal["AVAILABLE", "PARTIAL", "NOT_ASSESSABLE"]
    evaluated_at: datetime
    relevant_product_date: date | None
    exit_session_date: date | None
    exit_session_opens_at: datetime | None
    calendar_session_closes_at: datetime | None
    warning_session_date: date | None
    warning_at: datetime | None
    preceding_session_dates: tuple[date, ...]
    stage: DeadlineStage | None
    reasons: tuple[str, ...]
    calendar_revision_id: UUID | None
    calendar_fingerprint: str | None
    calendar_verification: str | None
    sessions_before_product_date: Literal[20] = 20
    scope: Literal["DOCUMENTED_CALENDAR_CALCULATION_ONLY"] = "DOCUMENTED_CALENDAR_CALCULATION_ONLY"
    rule_status: Literal["B05_NOT_ACTIVATED"] = "B05_NOT_ACTIVATED"


def calculate_product_deadline(
    *,
    workspace_id: UUID,
    warrant_id: UUID,
    exit_listing_id: UUID | None,
    maturity_on: date | None,
    last_trading_on: date | None,
    calendar: SessionEvidenceRead | None,
    event_at: datetime,
) -> ProductDeadlineCalculation:
    """Find the twentieth documented product session strictly before the term.

    B17 selects the earlier of the two required product dates. B18 excludes that
    entire calendar date, even if it is a session or a closed day. B19 uses the
    first opening of the previous session, never a newly invented warning offset.
    Late evaluation changes the stage, not any of the original calendar dates.

    Dates are caller-supplied Product-owner inputs, not independently verified by
    this function. No settlement-date fallback, generated business days, BID,
    target evidence, writes, provider calls or notifications are involved.
    """
    if event_at.utcoffset() is None:
        raise ValueError("The evaluation requires a timezone-aware clock")
    terminal = min(maturity_on, last_trading_on) if maturity_on and last_trading_on else None
    reasons: list[str] = []
    if maturity_on is None:
        reasons.append("PRODUCT_MATURITY_EVIDENCE_MISSING")
    if last_trading_on is None:
        reasons.append("PRODUCT_LAST_TRADING_DAY_EVIDENCE_MISSING")
    if exit_listing_id is None:
        reasons.append("PRODUCT_EXIT_LISTING_MISSING")
    if terminal == date.min:
        reasons.append("PRODUCT_DATE_HAS_NO_PRECEDING_SESSION_RANGE")
    if calendar is None:
        reasons.append("PRODUCT_SESSION_EVIDENCE_MISSING")
    if reasons or calendar is None or terminal is None:
        return _unavailable(calendar, event_at, terminal, tuple(reasons))

    reasons.extend(
        _calendar_reasons(calendar, workspace_id, warrant_id, exit_listing_id, terminal, event_at)
    )
    if reasons:
        return _unavailable(calendar, event_at, terminal, tuple(reasons))

    # The read's complete date range is supplied by the existing calendar owner.
    # Validate the exact required portion; the excluded product date need not
    # occur in that portion and never contributes to the twenty sessions.
    last_date = terminal - timedelta(days=1)
    relevant = tuple(
        day for day in calendar.days if calendar.start_date <= day.session_date <= last_date
    )
    dates = [day.session_date for day in relevant]
    if len(dates) != len(set(dates)) or dates != sorted(dates):
        return _unavailable(calendar, event_at, terminal, ("PRODUCT_SESSION_DAYS_CONFLICT",))
    expected = {
        calendar.start_date + timedelta(days=offset)
        for offset in range((last_date - calendar.start_date).days + 1)
    }
    if set(dates) != expected:
        return _unavailable(calendar, event_at, terminal, ("PRODUCT_SESSION_DAYS_MISSING",))
    if any(day.status == "UNKNOWN" for day in relevant):
        return _unavailable(calendar, event_at, terminal, ("PRODUCT_SESSION_DAYS_UNKNOWN",))
    sessions = tuple(day for day in relevant if day.status == "SESSION")
    if len(sessions) < 20:
        return _unavailable(calendar, event_at, terminal, ("TWENTY_PRODUCT_SESSIONS_MISSING",))

    exit_day = sessions[-20]
    warning_day = sessions[-21] if len(sessions) >= 21 else None
    opening = exit_day.intervals[0].opens_at
    closing = exit_day.intervals[-1].closes_at
    warning_at = warning_day.intervals[0].opens_at if warning_day else None
    clock = event_at.astimezone(UTC)
    stage: DeadlineStage | None
    if clock >= closing.astimezone(UTC):
        stage = "CALENDAR_SESSION_ENDED"
    elif clock >= opening.astimezone(UTC):
        stage = "EXIT_SESSION_STARTED"
    elif warning_at is not None:
        stage = "WARNING_DUE" if clock >= warning_at.astimezone(UTC) else "BEFORE_WARNING"
    else:
        stage = None
    return ProductDeadlineCalculation(
        status="AVAILABLE" if warning_day else "PARTIAL",
        evaluated_at=event_at,
        relevant_product_date=terminal,
        exit_session_date=exit_day.session_date,
        exit_session_opens_at=opening,
        calendar_session_closes_at=closing,
        warning_session_date=warning_day.session_date if warning_day else None,
        warning_at=warning_at,
        preceding_session_dates=tuple(day.session_date for day in sessions[-20:]),
        stage=stage,
        reasons=() if warning_day else ("PREWARNING_PRODUCT_SESSION_MISSING",),
        calendar_revision_id=calendar.revision_id,
        calendar_fingerprint=calendar.fingerprint,
        calendar_verification=calendar.verification,
    )


def _calendar_reasons(
    calendar: SessionEvidenceRead,
    workspace_id: UUID,
    warrant_id: UUID,
    exit_listing_id: UUID | None,
    terminal: date,
    event_at: datetime,
) -> tuple[str, ...]:
    binding = calendar.binding
    if (
        calendar.workspace_id != workspace_id
        or calendar.instrument_kind != "WARRANT"
        or calendar.instrument_id != warrant_id
        or binding is None
        or binding.instrument_kind != "WARRANT"
        or binding.instrument_id != warrant_id
        or binding.listing_id != exit_listing_id
    ):
        return ("PRODUCT_SESSION_SCOPE_MISMATCH",)
    if (
        calendar.status != "COMPLETE"
        or calendar.evidence_status != "ACTIVE"
        or calendar.reasons
        or calendar.missing_dates
        or calendar.revision_id is None
        or calendar.source is None
    ):
        return ("PRODUCT_SESSION_EVIDENCE_UNSUITABLE", *calendar.reasons)
    if (
        calendar.known_at.utcoffset() is None
        or calendar.recorded_at is None
        or calendar.recorded_at.utcoffset() is None
        or not calendar.recorded_at.astimezone(UTC)
        <= calendar.known_at.astimezone(UTC)
        <= event_at.astimezone(UTC)
    ):
        return ("PRODUCT_SESSION_KNOWLEDGE_TIME_INVALID",)
    end = terminal - timedelta(days=1)
    if (
        calendar.start_date > end
        or calendar.end_date < end
        or calendar.coverage_start is None
        or calendar.coverage_end is None
        or calendar.coverage_start > calendar.start_date
        or calendar.coverage_end < end
        or binding.valid_from > calendar.start_date
        or binding.valid_through < end
    ):
        return ("PRODUCT_SESSION_RANGE_INCOMPLETE",)
    if (end - calendar.start_date).days >= MAX_SESSION_DAYS:
        return ("PRODUCT_SESSION_RANGE_LIMIT",)
    return ()


def _unavailable(
    calendar: SessionEvidenceRead | None,
    event_at: datetime,
    terminal: date | None,
    reasons: tuple[str, ...],
) -> ProductDeadlineCalculation:
    return ProductDeadlineCalculation(
        status="NOT_ASSESSABLE",
        evaluated_at=event_at,
        relevant_product_date=terminal,
        exit_session_date=None,
        exit_session_opens_at=None,
        calendar_session_closes_at=None,
        warning_session_date=None,
        warning_at=None,
        preceding_session_dates=(),
        stage=None,
        reasons=reasons,
        calendar_revision_id=calendar.revision_id if calendar else None,
        calendar_fingerprint=calendar.fingerprint if calendar else None,
        calendar_verification=calendar.verification if calendar else None,
    )
