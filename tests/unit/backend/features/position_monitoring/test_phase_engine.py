from decimal import Decimal

import pytest

from app.features.position_monitoring.service.phase_engine import (
    MIN_CONFIRMED_SESSIONS,
    MIN_TREND_SESSIONS,
    PhaseInputs,
    PositionPhase,
    classify_phase,
)


def phase_inputs(
    *,
    sessions: int = MIN_TREND_SESSIONS,
    latest: str = "120",
    sma20: str = "115",
    sma50: str = "110",
    sma200: str = "100",
    atr14: str = "4",
    rsi14: str = "60",
    peak: str = "125",
) -> PhaseInputs:
    return PhaseInputs(
        sessions_since_entry=sessions,
        latest_price=Decimal(latest),
        sma_20=Decimal(sma20),
        sma_50=Decimal(sma50),
        sma_200=Decimal(sma200),
        atr_14=Decimal(atr14),
        rsi_14=Decimal(rsi14),
        highest_high_since_entry=Decimal(peak),
    )


def test_building_until_minimum_confirmation_sessions() -> None:
    value = classify_phase(phase_inputs(sessions=MIN_CONFIRMED_SESSIONS - 1))
    assert value is PositionPhase.BUILDING


def test_building_when_short_trend_structure_is_not_confirmed() -> None:
    value = classify_phase(phase_inputs(sessions=MIN_CONFIRMED_SESSIONS, latest="110", sma20="115"))
    assert value is PositionPhase.BUILDING


def test_confirmed_with_short_structure_before_trend_maturity() -> None:
    value = classify_phase(phase_inputs(sessions=MIN_CONFIRMED_SESSIONS))
    assert value is PositionPhase.CONFIRMED


@pytest.mark.parametrize(
    ("sma50", "sma200", "rsi14"),
    [
        ("100", "110", "60"),
        ("110", "100", "49.99"),
    ],
)
def test_confirmed_when_long_trend_requirements_are_not_met(
    sma50: str,
    sma200: str,
    rsi14: str,
) -> None:
    value = classify_phase(phase_inputs(sma50=sma50, sma200=sma200, rsi14=rsi14))
    assert value is PositionPhase.CONFIRMED


def test_trend_requires_mature_long_structure() -> None:
    value = classify_phase(phase_inputs())
    assert value is PositionPhase.TREND


def test_peak_protection_requires_high_rsi_and_atr_proximity_to_peak() -> None:
    value = classify_phase(phase_inputs(rsi14="70", peak="123", atr14="4"))
    assert value is PositionPhase.PEAK_PROTECTION


def test_high_rsi_without_peak_proximity_stays_trend() -> None:
    value = classify_phase(phase_inputs(rsi14="75", peak="130", atr14="4"))
    assert value is PositionPhase.TREND


def test_future_peak_invariant_rejects_latest_above_recorded_peak_for_peak_state() -> None:
    value = classify_phase(phase_inputs(rsi14="75", latest="126", peak="125"))
    assert value is PositionPhase.TREND
