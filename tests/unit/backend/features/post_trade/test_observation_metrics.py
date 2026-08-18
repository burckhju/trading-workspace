"""Unit tests for FT-011 observation selection and metrics."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from app.features.post_trade.application.ports import DailyObservation
from app.features.post_trade.domain.observation_metrics import (
    build_observation_evidence,
    select_observation_points,
)

EXIT = datetime(2026, 8, 18, 15, 30, tzinfo=UTC)
LISTING_ID = uuid4()


def _point(
    day: date,
    *,
    high: str = "110",
    low: str = "90",
    close: str = "100",
) -> DailyObservation:
    return DailyObservation(
        listing_id=LISTING_ID,
        trading_date=day,
        open=Decimal("100"),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        adjusted_close=None,
        quality_status="VALID",
    )


def test_same_day_eod_is_excluded() -> None:
    values = (
        _point(date(2026, 8, 18)),
        _point(date(2026, 8, 19)),
    )

    result = select_observation_points(
        values,
        full_exit_at=EXIT,
        target_count=20,
    )

    assert [value.trading_date for value in result] == [date(2026, 8, 19)]


def test_points_are_sorted_chronologically() -> None:
    values = (
        _point(date(2026, 8, 21)),
        _point(date(2026, 8, 19)),
        _point(date(2026, 8, 20)),
    )

    result = select_observation_points(
        values,
        full_exit_at=EXIT,
        target_count=20,
    )

    assert [value.trading_date for value in result] == [
        date(2026, 8, 19),
        date(2026, 8, 20),
        date(2026, 8, 21),
    ]


def test_missing_dates_are_not_synthesized() -> None:
    values = (
        _point(date(2026, 8, 19)),
        _point(date(2026, 8, 24)),
    )

    result = select_observation_points(
        values,
        full_exit_at=EXIT,
        target_count=20,
    )

    assert len(result) == 2


def test_selection_stops_at_target_count() -> None:
    values = tuple(_point(date(2026, 8, 19) + timedelta(days=i)) for i in range(25))

    result = select_observation_points(
        values,
        full_exit_at=EXIT,
        target_count=20,
    )

    assert len(result) == 20


def test_duplicate_trading_date_is_rejected() -> None:
    same_day = date(2026, 8, 19)

    with pytest.raises(
        ValueError,
        match="multiple observation points for the same trading_date",
    ):
        select_observation_points(
            (_point(same_day), _point(same_day)),
            full_exit_at=EXIT,
            target_count=20,
        )


def test_evidence_reports_incomplete_horizon() -> None:
    evidence = build_observation_evidence(
        (
            _point(date(2026, 8, 19)),
            _point(date(2026, 8, 20)),
        ),
        full_exit_at=EXIT,
        target_count=20,
    )

    assert evidence.available_observation_count == 2
    assert evidence.target_observation_count == 20
    assert evidence.horizon_complete is False


def test_evidence_reports_complete_horizon_at_twenty() -> None:
    values = tuple(_point(date(2026, 8, 19) + timedelta(days=i)) for i in range(20))

    evidence = build_observation_evidence(
        values,
        full_exit_at=EXIT,
        target_count=20,
    )

    assert evidence.available_observation_count == 20
    assert evidence.horizon_complete is True


def test_highest_high_and_date_are_reported() -> None:
    evidence = build_observation_evidence(
        (
            _point(date(2026, 8, 19), high="105"),
            _point(date(2026, 8, 20), high="125"),
            _point(date(2026, 8, 21), high="115"),
        ),
        full_exit_at=EXIT,
        target_count=20,
    )

    assert evidence.highest_high is not None
    assert evidence.highest_high.value == Decimal("125")
    assert evidence.highest_high.trading_date == date(2026, 8, 20)


def test_lowest_low_and_date_are_reported() -> None:
    evidence = build_observation_evidence(
        (
            _point(date(2026, 8, 19), low="95"),
            _point(date(2026, 8, 20), low="80"),
            _point(date(2026, 8, 21), low="90"),
        ),
        full_exit_at=EXIT,
        target_count=20,
    )

    assert evidence.lowest_low is not None
    assert evidence.lowest_low.value == Decimal("80")
    assert evidence.lowest_low.trading_date == date(2026, 8, 20)


def test_final_close_is_last_selected_point() -> None:
    evidence = build_observation_evidence(
        (
            _point(date(2026, 8, 19), close="101"),
            _point(date(2026, 8, 20), close="102"),
            _point(date(2026, 8, 21), close="103"),
        ),
        full_exit_at=EXIT,
        target_count=20,
    )

    assert evidence.final_close is not None
    assert evidence.final_close.value == Decimal("103")
    assert evidence.final_close.trading_date == date(2026, 8, 21)


def test_target_crossing_uses_daily_high() -> None:
    evidence = build_observation_evidence(
        (
            _point(date(2026, 8, 19), high="109"),
            _point(date(2026, 8, 20), high="111"),
        ),
        full_exit_at=EXIT,
        target_count=20,
        targets=(Decimal("110"),),
    )

    crossing = evidence.target_crossings[0]

    assert crossing.crossed is True
    assert crossing.first_crossed_on == date(2026, 8, 20)


def test_uncrossed_target_remains_false() -> None:
    evidence = build_observation_evidence(
        (_point(date(2026, 8, 19), high="109"),),
        full_exit_at=EXIT,
        target_count=20,
        targets=(Decimal("110"),),
    )

    crossing = evidence.target_crossings[0]

    assert crossing.crossed is False
    assert crossing.first_crossed_on is None


def test_stop_crossing_uses_daily_low() -> None:
    evidence = build_observation_evidence(
        (
            _point(date(2026, 8, 19), low="96"),
            _point(date(2026, 8, 20), low="94"),
        ),
        full_exit_at=EXIT,
        target_count=20,
        stop=Decimal("95"),
    )

    assert evidence.stop_crossing is not None
    assert evidence.stop_crossing.crossed is True
    assert evidence.stop_crossing.first_crossed_on == date(2026, 8, 20)


def test_no_stop_produces_no_stop_crossing() -> None:
    evidence = build_observation_evidence(
        (_point(date(2026, 8, 19)),),
        full_exit_at=EXIT,
        target_count=20,
        stop=None,
    )

    assert evidence.stop_crossing is None


def test_empty_observations_produce_empty_metrics() -> None:
    evidence = build_observation_evidence(
        (),
        full_exit_at=EXIT,
        target_count=20,
    )

    assert evidence.available_observation_count == 0
    assert evidence.highest_high is None
    assert evidence.lowest_low is None
    assert evidence.final_close is None


def test_non_positive_target_count_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="target_count must be positive",
    ):
        select_observation_points(
            (),
            full_exit_at=EXIT,
            target_count=0,
        )
