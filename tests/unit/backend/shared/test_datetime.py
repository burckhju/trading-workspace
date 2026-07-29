from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.shared.contracts import Clock, SystemClock
from app.shared.utils import ensure_utc, utc_now


def test_utc_now_returns_aware_utc_datetime() -> None:
    value = utc_now()

    assert value.tzinfo is UTC
    assert value.utcoffset() == timedelta(0)


def test_ensure_utc_converts_aware_datetime() -> None:
    source = datetime(2026, 7, 29, 14, 0, tzinfo=timezone(timedelta(hours=2)))

    assert ensure_utc(source) == datetime(2026, 7, 29, 12, 0, tzinfo=UTC)


def test_ensure_utc_rejects_naive_datetime() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        ensure_utc(datetime(2026, 7, 29, 12, 0))


def test_system_clock_implements_clock_contract() -> None:
    clock = SystemClock()

    assert isinstance(clock, Clock)
    assert clock.now().tzinfo is UTC
