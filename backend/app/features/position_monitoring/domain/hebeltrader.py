"""Read-only Hebeltrader management projection; never records a fill or a stop."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from zoneinfo import ZoneInfo

from app.features.trade_plan.domain.hebeltrader import HALF, ONE, ZERO, Levels, positive


@dataclass(frozen=True, slots=True)
class SessionCalendar:
    """Complete venue-session snapshot supplied by a calendar provider/caller.

    No weekday approximation. Coverage is explicit, including non-session dates.
    A session count excludes the starting date and includes the ending date.
    """

    venue: str
    source: str
    coverage_start: date
    coverage_end: date
    sessions: tuple[date, ...]
    time_zone: str = "Europe/Berlin"

    def __post_init__(self) -> None:
        try:
            ZoneInfo(self.time_zone)
        except (KeyError, ValueError) as error:
            raise ValueError("unknown calendar time_zone") from error
        if not self.venue.strip() or not self.source.strip():
            raise ValueError("calendar venue and source are required")
        if self.coverage_start > self.coverage_end or not self.sessions:
            raise ValueError("invalid or empty calendar coverage")
        if tuple(sorted(set(self.sessions))) != self.sessions:
            raise ValueError("calendar sessions must be unique and strictly increasing")
        if self.sessions[0] < self.coverage_start or self.sessions[-1] > self.coverage_end:
            raise ValueError("sessions outside calendar coverage")

    def count(self, start: date, end: date) -> int:
        if not self.coverage_start <= start <= end <= self.coverage_end:
            raise ValueError("calendar coverage does not contain the requested interval")
        return sum(start < day <= end for day in self.sessions)


@dataclass(frozen=True, slots=True)
class ManagementDecision:
    action: str
    reason: str
    sell_fraction_of_initial: Decimal
    proposed_stop: Decimal
    stop_after_confirmed_fill: Decimal | None
    held_sessions: int
    sessions_to_last_trade: int | None
    requires_fill_confirmation: bool = False


def evaluate_management(
    *,
    levels: Levels,
    actual_entry: Decimal,
    current_stop: Decimal,
    bid: Decimal | None,
    quote_usable: bool,
    entered_on: date,
    as_of: date,
    calendar: SessionCalendar,
    remaining_fraction: Decimal = ONE,
    target1_completed_on: date | None = None,
    late_entry: bool = False,
    last_trading_date: date | None = None,
    instrument_kind: str = "STOCK",
) -> ManagementDecision:
    """Latest profile only (>= 2026-08-10); signals, not historical fill simulation.

    Priority: closed > expiry exit > unusable quote > stop > loss-time exit > T2 > T1.
    T1 completion is an externally confirmed half-fill, or documented late entry.
    The monotonic max() rule deliberately fixes the publisher's lowering ambiguity.
    """
    if as_of < date(2026, 8, 10):
        raise ValueError("this policy profile is not valid before 2026-08-10")
    positive(actual_entry, "actual_entry")
    positive(current_stop, "current_stop")
    positive(remaining_fraction, "remaining_fraction", allow_zero=True)
    if instrument_kind not in {"STOCK", "CALL"}:
        raise ValueError("instrument_kind must be STOCK or CALL")
    if instrument_kind == "CALL" and last_trading_date is None:
        raise ValueError("a CALL requires verified last_trading_date, not payment date")
    if current_stop < levels.stop:
        raise ValueError("current_stop must not be below the initial stop")
    if remaining_fraction not in {ZERO, HALF, ONE}:
        raise ValueError("only unmodified 1, 0.5 or closed 0 states are supported")
    if entered_on not in calendar.sessions:
        raise ValueError("entry must be a covered trading session")
    held = calendar.count(entered_on, as_of)
    if target1_completed_on is not None:
        if (
            target1_completed_on not in calendar.sessions
            or not entered_on <= target1_completed_on <= as_of
        ):
            raise ValueError("invalid target1 completion session")
        if remaining_fraction == ONE:
            raise ValueError("completed target1 requires at most half the original position")
    elif remaining_fraction == HALF or late_entry:
        raise ValueError("half position / late entry requires target1_completed_on")
    if late_entry and target1_completed_on != entered_on:
        raise ValueError("late entry starts its post-target timer on the entry session")
    if not late_entry and actual_entry >= levels.target1:
        raise ValueError("normal entry must be below target1")
    if late_entry and not levels.entry < actual_entry < levels.target2:
        raise ValueError("late entry requires original entry < actual entry < target2")
    if last_trading_date is not None:
        if not calendar.coverage_start <= last_trading_date <= calendar.coverage_end:
            raise ValueError("calendar must cover last_trading_date")
        if last_trading_date not in calendar.sessions or last_trading_date < entered_on:
            raise ValueError("invalid last_trading_date")
    remaining_days = (
        None
        if last_trading_date is None
        else (0 if as_of >= last_trading_date else calendar.count(as_of, last_trading_date))
    )
    stop = current_stop
    if target1_completed_on is not None:
        stop = max(stop, levels.entry if late_entry else actual_entry)
        if calendar.count(target1_completed_on, as_of) >= 20:
            stop = max(stop, Decimal("0.8") * levels.target1)

    def decision(
        action: str,
        reason: str,
        fraction: Decimal = ZERO,
        after_fill: Decimal | None = None,
    ) -> ManagementDecision:
        return ManagementDecision(
            action, reason, fraction, stop, after_fill, held, remaining_days, fraction > ZERO
        )

    if remaining_fraction == ZERO:
        return decision("NONE", "POSITION_CLOSED")
    if remaining_days is not None and remaining_days <= 20:
        return decision("EXIT_REVIEW", "EXPIRY_20_SESSIONS", remaining_fraction)
    if not quote_usable or bid is None:
        return decision("DATA_REQUIRED", "EXECUTABLE_BID_REQUIRED")
    positive(bid, "bid", allow_zero=True)
    if bid <= stop:
        return decision("EXIT_REVIEW", "STOP_REACHED", remaining_fraction)
    if held >= 20 and bid < actual_entry:
        return decision("EXIT_REVIEW", "LOSS_AFTER_20_SESSIONS", remaining_fraction)
    if bid >= levels.target2:
        return decision("EXIT_REVIEW", "TARGET2_REACHED", remaining_fraction)
    if target1_completed_on is None and bid >= levels.target1:
        return decision("PARTIAL_EXIT_REVIEW", "TARGET1_REACHED", HALF, max(stop, actual_entry))
    return decision("HOLD_REVIEW", "NO_EXIT_CONDITION")
