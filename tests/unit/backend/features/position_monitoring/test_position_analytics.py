from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from app.features.analysis.persistence.models import MarketAnalysisSnapshotRowModel
from app.features.position_monitoring.service.position_analytics import highest_high_since_entry


def _row(trading_date: date, high: str) -> MarketAnalysisSnapshotRowModel:
    return MarketAnalysisSnapshotRowModel(
        id=uuid4(),
        run_id=uuid4(),
        trading_date=trading_date,
        open=Decimal("100"),
        high=Decimal(high),
        low=Decimal("90"),
        close=Decimal("100"),
        adjusted_close=None,
        volume=None,
        currency="EUR",
        provider="EODHD",
        provider_symbol="TEST",
        quality_status="VALID",
        warnings=[],
    )


def test_highest_high_since_entry_uses_completed_sessions_after_entry() -> None:
    peak, sessions = highest_high_since_entry(
        entry_executed_at=datetime(2026, 9, 1, 15, tzinfo=UTC),
        evaluation_time=datetime(2026, 9, 5, 12, tzinfo=UTC),
        rows=(
            _row(date(2026, 9, 1), "999"),
            _row(date(2026, 9, 2), "110"),
            _row(date(2026, 9, 3), "125"),
            _row(date(2026, 9, 4), "120"),
        ),
    )

    assert peak == Decimal("125")
    assert sessions == 3


def test_highest_high_since_entry_can_be_first_eligible_session() -> None:
    peak, _ = highest_high_since_entry(
        entry_executed_at=datetime(2026, 9, 1, 15, tzinfo=UTC),
        evaluation_time=datetime(2026, 9, 5, 12, tzinfo=UTC),
        rows=(_row(date(2026, 9, 2), "130"), _row(date(2026, 9, 3), "120")),
    )
    assert peak == Decimal("130")


def test_highest_high_since_entry_rises_with_last_completed_session() -> None:
    peak, _ = highest_high_since_entry(
        entry_executed_at=datetime(2026, 9, 1, 15, tzinfo=UTC),
        evaluation_time=datetime(2026, 9, 5, 12, tzinfo=UTC),
        rows=(_row(date(2026, 9, 2), "110"), _row(date(2026, 9, 4), "140")),
    )
    assert peak == Decimal("140")


def test_entry_day_is_excluded_conservatively() -> None:
    peak, sessions = highest_high_since_entry(
        entry_executed_at=datetime(2026, 9, 10, 15, tzinfo=UTC),
        evaluation_time=datetime(2026, 9, 11, 12, tzinfo=UTC),
        rows=(_row(date(2026, 9, 10), "999"),),
    )
    assert peak is None
    assert sessions == 0


def test_evaluation_day_and_future_rows_are_not_used() -> None:
    peak, sessions = highest_high_since_entry(
        entry_executed_at=datetime(2026, 9, 1, 15, tzinfo=UTC),
        evaluation_time=datetime(2026, 9, 4, 12, tzinfo=UTC),
        rows=(
            _row(date(2026, 9, 2), "110"),
            _row(date(2026, 9, 4), "500"),
            _row(date(2026, 9, 5), "900"),
        ),
    )
    assert peak == Decimal("110")
    assert sessions == 1


def test_no_history_after_entry_is_insufficient_input() -> None:
    peak, sessions = highest_high_since_entry(
        entry_executed_at=datetime(2026, 9, 4, 15, tzinfo=UTC),
        evaluation_time=datetime(2026, 9, 5, 12, tzinfo=UTC),
        rows=(),
    )
    assert peak is None
    assert sessions == 0


def test_projection_requires_timezone_aware_timestamps() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        highest_high_since_entry(
            entry_executed_at=datetime(2026, 9, 1, 15),
            evaluation_time=datetime(2026, 9, 5, 12, tzinfo=UTC),
            rows=(),
        )
