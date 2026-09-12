"""Session-aware freshness classification for held-product quotes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from enum import StrEnum
from zoneinfo import ZoneInfo


class QuoteFreshness(StrEnum):
    FRESH = "FRESH"
    LAST_AVAILABLE = "LAST_AVAILABLE"
    STALE = "STALE"


@dataclass(frozen=True, slots=True)
class TradingSessionFreshnessPolicy:
    """Recognize the previous close until the next expected quote session."""

    policy_version: str = "DE_WARRANT_SESSION_FRESHNESS_V1"
    timezone_name: str = "Europe/Berlin"
    session_open: time = time(8, 0)
    session_close: time = time(22, 0)
    opening_grace: timedelta = timedelta(minutes=15)

    def classify(
        self,
        *,
        observed_at: datetime,
        retrieved_at: datetime,
        max_age_seconds: int,
        trading_status: str | None,
    ) -> QuoteFreshness:
        age_seconds = (retrieved_at - observed_at).total_seconds()
        if age_seconds <= max_age_seconds:
            return QuoteFreshness.FRESH
        if trading_status != "CLOSED":
            return QuoteFreshness.STALE

        timezone = ZoneInfo(self.timezone_name)
        observed_local = observed_at.astimezone(timezone)
        retrieved_local = retrieved_at.astimezone(timezone)
        close_threshold = datetime.combine(
            observed_local.date(), self.session_close, timezone
        ) - timedelta(seconds=max_age_seconds)
        if observed_local < close_threshold:
            return QuoteFreshness.STALE

        next_session = self._next_session_date(observed_local.date())
        next_quote_expected = (
            datetime.combine(next_session, self.session_open, timezone) + self.opening_grace
        )
        if retrieved_local < next_quote_expected:
            return QuoteFreshness.LAST_AVAILABLE
        return QuoteFreshness.STALE

    def _next_session_date(self, after: date) -> date:
        candidate = after + timedelta(days=1)
        while candidate.weekday() >= 5 or candidate in _german_exchange_holidays(candidate.year):
            candidate += timedelta(days=1)
        return candidate


def _german_exchange_holidays(year: int) -> frozenset[date]:
    """Return the regular full-day Frankfurt/Xetra closure dates."""

    easter = _easter_sunday(year)
    return frozenset(
        {
            date(year, 1, 1),
            easter - timedelta(days=2),
            easter + timedelta(days=1),
            date(year, 5, 1),
            date(year, 12, 24),
            date(year, 12, 25),
            date(year, 12, 26),
            date(year, 12, 31),
        }
    )


def _easter_sunday(year: int) -> date:
    """Calculate Gregorian Easter using the Anonymous Gregorian algorithm."""

    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    ell = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * ell) // 451
    month = (h + ell - 7 * m + 114) // 31
    day = (h + ell - 7 * m + 114) % 31 + 1
    return date(year, month, day)
