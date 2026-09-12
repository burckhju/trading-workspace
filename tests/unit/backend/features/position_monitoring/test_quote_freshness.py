from datetime import UTC, datetime

from app.features.position_monitoring.service.quote_freshness import (
    QuoteFreshness,
    TradingSessionFreshnessPolicy,
)


def _classify(observed_at: datetime, retrieved_at: datetime, status: str | None):
    return TradingSessionFreshnessPolicy().classify(
        observed_at=observed_at,
        retrieved_at=retrieved_at,
        max_age_seconds=3600,
        trading_status=status,
    )


def test_fresh_quote_remains_fresh_independent_of_session_status() -> None:
    observed = datetime(2026, 9, 11, 19, 59, tzinfo=UTC)

    assert _classify(observed, datetime(2026, 9, 11, 20, 30, tzinfo=UTC), "CLOSED") is (
        QuoteFreshness.FRESH
    )


def test_friday_close_is_last_available_until_monday_opening_grace_ends() -> None:
    observed = datetime(2026, 9, 11, 19, 59, tzinfo=UTC)

    assert _classify(observed, datetime(2026, 9, 12, 12, 0, tzinfo=UTC), "CLOSED") is (
        QuoteFreshness.LAST_AVAILABLE
    )
    assert _classify(observed, datetime(2026, 9, 14, 6, 14, tzinfo=UTC), "CLOSED") is (
        QuoteFreshness.LAST_AVAILABLE
    )
    assert _classify(observed, datetime(2026, 9, 14, 6, 16, tzinfo=UTC), "CLOSED") is (
        QuoteFreshness.STALE
    )


def test_closed_status_does_not_rescue_an_intraday_or_old_quote() -> None:
    friday_intraday = datetime(2026, 9, 11, 12, 0, tzinfo=UTC)
    thursday_close = datetime(2026, 9, 10, 19, 59, tzinfo=UTC)
    saturday = datetime(2026, 9, 12, 12, 0, tzinfo=UTC)

    assert _classify(friday_intraday, saturday, "CLOSED") is QuoteFreshness.STALE
    assert _classify(thursday_close, saturday, "CLOSED") is QuoteFreshness.STALE
    assert _classify(thursday_close, saturday, "OPEN") is QuoteFreshness.STALE


def test_exchange_holiday_delays_the_next_expected_quote_session() -> None:
    thursday_close = datetime(2026, 4, 2, 19, 59, tzinfo=UTC)
    easter_monday = datetime(2026, 4, 6, 12, 0, tzinfo=UTC)
    tuesday_after_grace = datetime(2026, 4, 7, 6, 16, tzinfo=UTC)

    assert _classify(thursday_close, easter_monday, "CLOSED") is (QuoteFreshness.LAST_AVAILABLE)
    assert _classify(thursday_close, tuesday_after_grace, "CLOSED") is QuoteFreshness.STALE
