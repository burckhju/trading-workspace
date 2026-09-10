from datetime import date, timedelta
from decimal import Decimal

from app.features.analysis.domain.calculator import MODEL_ID, MODEL_VERSION, calculate
from app.features.analysis.domain.enums import (
    AnalysisQualityStatus,
    CriterionClassification,
)
from app.features.analysis.domain.models import (
    AnalysisParameters,
    SnapshotRow,
    calculate_input_hash,
)
from app.features.analysis.domain.position_analytics import (
    INDICATOR_SET_VERSION,
    calculate_position_analytics,
)


def rows(count: int = 220) -> tuple[SnapshotRow, ...]:
    start = date(2025, 1, 1)
    return tuple(
        SnapshotRow(
            trading_date=start + timedelta(days=index),
            open=Decimal("100") + index,
            high=Decimal("102") + index,
            low=Decimal("99") + index,
            close=Decimal("101") + index,
            adjusted_close=Decimal("101") + index,
            volume=Decimal("1000"),
            currency="EUR",
            provider="EODHD",
            provider_symbol="TEST.XETRA",
            quality_status="GOOD",
            warnings=(),
        )
        for index in range(count)
    )


def test_calculation_is_deterministic_and_transparent() -> None:
    parameters = AnalysisParameters()
    first = calculate(parameters, rows())
    second = calculate(parameters, rows())
    assert first == second
    assert first.quality_status is AnalysisQualityStatus.GOOD
    assert first.metrics["sma_20"] is not None
    assert any(
        item.code == "LONG_TREND" and item.classification is CriterionClassification.POSITIVE
        for item in first.criteria
    )


def test_position_analytics_foundation_uses_persisted_ohlc() -> None:
    result = calculate_position_analytics(AnalysisParameters(), rows())
    assert result.metrics["atr_14"] == "3.000000"
    assert result.metrics["rsi_14"] == "100.000000"
    assert result.metrics["highest_high_20"] == "321.000000"
    assert result.metrics["distance_sma_20"] is not None
    assert result.metrics["distance_sma_50"] is not None
    assert result.metrics["distance_sma_200"] is not None
    assert result.metrics["indicator_set_version"] == INDICATOR_SET_VERSION


def test_flat_prices_have_neutral_rsi() -> None:
    flat = tuple(
        SnapshotRow(
            trading_date=date(2025, 1, 1) + timedelta(days=index),
            open=Decimal("100"),
            high=Decimal("100"),
            low=Decimal("100"),
            close=Decimal("100"),
            adjusted_close=Decimal("100"),
            volume=None,
            currency="EUR",
            provider="EODHD",
            provider_symbol="TEST.XETRA",
            quality_status="GOOD",
            warnings=(),
        )
        for index in range(220)
    )
    result = calculate_position_analytics(AnalysisParameters(), flat)
    assert result.metrics["atr_14"] == "0.000000"
    assert result.metrics["rsi_14"] == "50.000000"
    assert result.metrics["highest_high_20"] == "100.000000"


def test_input_hash_changes_with_input() -> None:
    parameters = AnalysisParameters()
    first = calculate_input_hash(MODEL_ID, MODEL_VERSION, parameters, rows())
    second = calculate_input_hash(MODEL_ID, MODEL_VERSION, parameters, rows(221))
    assert len(first) == 64
    assert first != second


def test_insufficient_data_is_not_evaluable() -> None:
    result = calculate_position_analytics(AnalysisParameters(), rows(20))
    assert result.quality_status is AnalysisQualityStatus.INSUFFICIENT
    assert result.metrics == {}
    assert result.criteria[0].classification is CriterionClassification.NOT_EVALUABLE
