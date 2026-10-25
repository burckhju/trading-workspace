"""Versioned source-quality contract; no historical snapshot normalization."""

from copy import deepcopy
from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.features.analysis.domain import calculator as legacy
from app.features.analysis.domain import calculator_v1_0_1 as corrected
from app.features.analysis.domain.enums import AnalysisQualityStatus, PriceField
from app.features.analysis.domain.models import (
    AnalysisParameters,
    SnapshotRow,
    calculate_input_hash,
)


def sample_rows(count: int = 220) -> tuple[SnapshotRow, ...]:
    """Complete synthetic observations; no provider access or user data."""
    rows = []
    for offset in range(count):
        value = Decimal("100") + Decimal(offset) / Decimal("10")
        rows.append(
            SnapshotRow(
                trading_date=date(2025, 1, 1) + timedelta(days=offset),
                open=value,
                high=value + 1,
                low=value - 1,
                close=value,
                adjusted_close=value,
                volume=Decimal("1000"),
                currency="EUR",
                provider="EODHD",
                provider_symbol="SYNTHETIC.QUALITY",
                quality_status="VALID",
                warnings=(),
            )
        )
    return tuple(rows)


@pytest.mark.parametrize("price_field", [PriceField.CLOSE, PriceField.ADJUSTED_CLOSE])
def test_complete_valid_source_rows_produce_good(price_field: PriceField) -> None:
    result = corrected.calculate(AnalysisParameters(price_field=price_field), sample_rows())
    assert result.quality_status is AnalysisQualityStatus.GOOD
    assert result.notes == ()


@pytest.mark.parametrize(
    "source_status", ["GOOD", "INCOMPLETE", "STALE", "REJECTED", "", "valid", "UNKNOWN"]
)
def test_non_valid_source_status_is_never_promoted(source_status: str) -> None:
    rows = tuple(replace(row, quality_status=source_status) for row in sample_rows())
    result = corrected.calculate(AnalysisParameters(), rows)
    assert result.quality_status is AnalysisQualityStatus.LIMITED


@pytest.mark.parametrize("warning", ["provider observation is incomplete", "", " "])
def test_source_warnings_remain_limiting(warning: str) -> None:
    rows = sample_rows()
    rows = (replace(rows[0], warnings=(warning,)), *rows[1:])
    result = corrected.calculate(AnalysisParameters(), rows)
    assert result.quality_status is AnalysisQualityStatus.LIMITED
    assert any("source warning" in note for note in result.notes)


def test_insufficient_observations_retain_the_legacy_failure_result() -> None:
    rows = sample_rows(199)
    old = legacy.calculate(AnalysisParameters(), rows)
    new = corrected.calculate(AnalysisParameters(), rows)
    assert new == old
    assert new.quality_status is AnalysisQualityStatus.INSUFFICIENT


def test_missing_adjusted_close_is_not_hidden_by_valid_source_status() -> None:
    rows = sample_rows()
    rows = (*rows[:-1], replace(rows[-1], adjusted_close=None))
    result = corrected.calculate(AnalysisParameters(), rows)
    assert result.quality_status is AnalysisQualityStatus.LIMITED
    assert any("adjusted close missing" in note for note in result.notes)


def test_close_mode_does_not_require_an_unused_adjusted_close() -> None:
    rows = tuple(replace(row, adjusted_close=None) for row in sample_rows())
    result = corrected.calculate(AnalysisParameters(price_field=PriceField.CLOSE), rows)
    assert result.quality_status is AnalysisQualityStatus.GOOD


def test_a_single_non_valid_observation_limits_the_whole_input() -> None:
    rows = sample_rows()
    rows = (replace(rows[0], quality_status="REJECTED"), *rows[1:])
    result = corrected.calculate(AnalysisParameters(), rows)
    assert result.quality_status is AnalysisQualityStatus.LIMITED


def test_numerics_criteria_inputs_and_legacy_hash_are_unchanged() -> None:
    parameters = AnalysisParameters()
    rows = sample_rows()
    before = deepcopy(tuple(row.canonical() for row in rows))
    old_hash = calculate_input_hash(legacy.MODEL_ID, legacy.MODEL_VERSION, parameters, rows)
    old = legacy.calculate(parameters, rows)
    new = corrected.calculate(parameters, rows)
    assert old.quality_status is AnalysisQualityStatus.LIMITED
    assert new.quality_status is AnalysisQualityStatus.GOOD
    assert new.metrics == old.metrics
    assert new.criteria == old.criteria
    assert tuple(row.canonical() for row in rows) == before
    assert calculate_input_hash(legacy.MODEL_ID, legacy.MODEL_VERSION, parameters, rows) == old_hash
    new_hash = calculate_input_hash(corrected.MODEL_ID, corrected.MODEL_VERSION, parameters, rows)
    assert new_hash != old_hash
    assert legacy.calculate(parameters, rows) == old


def test_legacy_contract_and_its_historical_warning_behavior_are_not_rewritten() -> None:
    source = sample_rows()
    rows = tuple(replace(row, quality_status="GOOD", warnings=("historic",)) for row in source)
    old = legacy.calculate(AnalysisParameters(), rows)
    new = corrected.calculate(AnalysisParameters(), rows)
    assert legacy.MODEL_VERSION == "1.0.0"
    assert corrected.MODEL_VERSION == "1.0.1"
    assert corrected.MODEL_ID == legacy.MODEL_ID
    assert old.quality_status is AnalysisQualityStatus.GOOD
    assert old.notes == ()
    assert new.quality_status is AnalysisQualityStatus.LIMITED
    assert legacy.calculate(AnalysisParameters(), rows) == old


@pytest.mark.parametrize("source_status", ["VALID", "GOOD", "REJECTED"])
@pytest.mark.parametrize("version", ["1.0.0", "1.0.1"])
def test_dispatch_preserves_the_explicit_version(version: str, source_status: str) -> None:
    from app.features.analysis.domain.model_versions import calculate_for_version

    parameters = AnalysisParameters()
    rows = tuple(replace(row, quality_status=source_status) for row in sample_rows())
    selected = legacy if version == "1.0.0" else corrected
    actual = calculate_for_version(
        parameters, rows, model_id=legacy.MODEL_ID, model_version=version
    )
    assert actual == selected.calculate(parameters, rows)


@pytest.mark.parametrize("version", ["", "latest", "1.0", "1.0.2", "2.0.0"])
def test_dispatch_has_no_unknown_version_fallback(version: str) -> None:
    from app.features.analysis.domain.errors import AnalysisConflict
    from app.features.analysis.domain.model_versions import calculate_for_version

    with pytest.raises(AnalysisConflict, match="not available"):
        calculate_for_version(
            AnalysisParameters(), sample_rows(), model_id=legacy.MODEL_ID, model_version=version
        )


def test_dispatch_rejects_a_foreign_model_even_with_a_known_version() -> None:
    from app.features.analysis.domain.errors import AnalysisConflict
    from app.features.analysis.domain.model_versions import calculate_for_version

    with pytest.raises(AnalysisConflict, match="not available"):
        calculate_for_version(
            AnalysisParameters(), sample_rows(), model_id="OTHER_MODEL", model_version="1.0.1"
        )


def test_insufficient_result_keeps_source_warning_evidence() -> None:
    rows = sample_rows(199)
    rows = (
        replace(rows[0], quality_status="REJECTED", warnings=("source warning detail",)),
        *rows[1:],
    )
    result = corrected.calculate(AnalysisParameters(), rows)
    assert result.quality_status is AnalysisQualityStatus.INSUFFICIENT
    assert any("Required 200, available 199" in note for note in result.notes)
    assert any("REJECTED" in note for note in result.notes)
    assert any("source warning detail" in note for note in result.notes)
