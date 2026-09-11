from decimal import Decimal

from app.features.position_monitoring.service.score_engine import (
    SCORE_POLICY_VERSION,
    ScoreInputs,
    calculate_peak_score,
    calculate_trend_score,
)


def inputs(**overrides: object) -> ScoreInputs:
    values: dict[str, object] = {
        "sessions_since_entry": 12,
        "latest_price": Decimal("120"),
        "sma_20": Decimal("115"),
        "sma_50": Decimal("110"),
        "sma_200": Decimal("100"),
        "atr_14": Decimal("4"),
        "rsi_14": Decimal("72"),
        "highest_high_since_entry": Decimal("123"),
    }
    values.update(overrides)
    return ScoreInputs(**values)  # type: ignore[arg-type]


def test_score_policy_version_is_explicit() -> None:
    assert SCORE_POLICY_VERSION == "POSITION_SCORE_V1"


def test_full_trend_score_is_100() -> None:
    result = calculate_trend_score(inputs())
    assert result.value == 100
    assert result.components == {
        "maturity": 20,
        "price_above_sma20": 20,
        "sma20_above_sma50": 20,
        "sma50_above_sma200": 20,
        "rsi_support": 20,
    }


def test_trend_score_exposes_failed_components() -> None:
    result = calculate_trend_score(
        inputs(
            sessions_since_entry=5,
            latest_price=Decimal("109"),
            rsi_14=Decimal("45"),
        )
    )
    assert result.value == 40
    assert result.components["maturity"] == 0
    assert result.components["price_above_sma20"] == 0
    assert result.components["rsi_support"] == 0


def test_full_peak_score_is_100_when_near_high() -> None:
    result = calculate_peak_score(inputs())
    assert result.value == 100
    assert result.components["near_peak"] == 25


def test_peak_score_drops_when_more_than_one_atr_below_high() -> None:
    result = calculate_peak_score(inputs(latest_price=Decimal("118"), highest_high_since_entry=Decimal("123")))
    assert result.value == 75
    assert result.components["near_peak"] == 0


def test_peak_score_requires_hot_rsi() -> None:
    result = calculate_peak_score(inputs(rsi_14=Decimal("69.99")))
    assert result.value == 75
    assert result.components["rsi_hot"] == 0


def test_peak_score_does_not_treat_new_current_high_as_near_prior_peak() -> None:
    result = calculate_peak_score(
        inputs(latest_price=Decimal("124"), highest_high_since_entry=Decimal("123"))
    )
    assert result.value == 75
    assert result.components["near_peak"] == 0
