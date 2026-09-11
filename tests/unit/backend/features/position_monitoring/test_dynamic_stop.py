from decimal import Decimal

import pytest

from app.features.position_monitoring.service.dynamic_stop import (
    DYNAMIC_STOP_POLICY_VERSION,
    DynamicStopInputs,
    calculate_dynamic_stop,
    resolve_atr_multiple,
)
from app.features.position_monitoring.service.phase_engine import PositionPhase


def inputs(**overrides: object) -> DynamicStopInputs:
    values: dict[str, object] = {
        "phase": PositionPhase.TREND,
        "trend_score": 80,
        "peak_score": 50,
        "latest_price": Decimal("120"),
        "atr_14": Decimal("4"),
        "highest_high_since_entry": Decimal("125"),
    }
    values.update(overrides)
    return DynamicStopInputs(**values)  # type: ignore[arg-type]


def test_policy_version_is_explicit() -> None:
    assert DYNAMIC_STOP_POLICY_VERSION == "DYNAMIC_STOP_V1"


@pytest.mark.parametrize(
    ("phase", "trend_score", "peak_score", "expected"),
    [
        (PositionPhase.BUILDING, 100, 100, Decimal("3")),
        (PositionPhase.CONFIRMED, 100, 100, Decimal("2.5")),
        (PositionPhase.TREND, 79, 100, Decimal("2")),
        (PositionPhase.TREND, 80, 0, Decimal("1.5")),
        (PositionPhase.PEAK_PROTECTION, 100, 74, Decimal("1.5")),
        (PositionPhase.PEAK_PROTECTION, 0, 75, Decimal("1")),
    ],
)
def test_atr_multiple_is_phase_and_score_driven(
    phase: PositionPhase,
    trend_score: int,
    peak_score: int,
    expected: Decimal,
) -> None:
    value = resolve_atr_multiple(
        inputs(phase=phase, trend_score=trend_score, peak_score=peak_score)
    )
    assert value == expected


def test_dynamic_stop_anchors_to_highest_high_since_entry() -> None:
    value = calculate_dynamic_stop(inputs())
    assert value.atr_multiple == Decimal("1.5")
    assert value.candidate_stop == Decimal("119.0")
    assert value.distance_to_stop == Decimal("1.0")
    assert value.breached is False


def test_dynamic_stop_marks_candidate_as_breached_at_or_below_stop() -> None:
    value = calculate_dynamic_stop(inputs(latest_price=Decimal("119")))
    assert value.candidate_stop == Decimal("119.0")
    assert value.distance_to_stop == Decimal("0.0")
    assert value.breached is True


def test_peak_protection_tightens_to_one_atr_at_score_threshold() -> None:
    value = calculate_dynamic_stop(
        inputs(
            phase=PositionPhase.PEAK_PROTECTION,
            peak_score=75,
            latest_price=Decimal("123"),
        )
    )
    assert value.atr_multiple == Decimal("1")
    assert value.candidate_stop == Decimal("121")
    assert value.breached is False
