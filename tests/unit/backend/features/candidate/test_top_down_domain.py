from dataclasses import replace
from decimal import Decimal

import pytest

from app.features.analysis.domain.enums import (
    AnalysisQualityStatus,
    CriterionClassification,
)
from app.features.analysis.domain.top_down import (
    ContextClassification,
    RelativeStrengthParameters,
    TradingDirection,
    calculate_market_context,
    calculate_relative_strength,
)
from app.features.candidate.domain.enums import CandidateQualification
from app.features.candidate.domain.models import CandidateEvaluationInput
from app.features.candidate.domain.qualification import evaluate_candidate


def test_relative_strength_v1_positive_above_two_percentage_points() -> None:
    subject = tuple([Decimal("100")] * 60 + [Decimal("110")])
    reference = tuple([Decimal("100")] * 60 + [Decimal("107")])
    result = calculate_relative_strength(subject, reference)
    assert result.model_version == "1.0.0"
    assert result.relative_performance == Decimal("0.030000")
    assert result.classification is CriterionClassification.POSITIVE


def test_relative_strength_v1_uses_neutral_zone() -> None:
    subject = tuple([Decimal("100")] * 60 + [Decimal("108")])
    reference = tuple([Decimal("100")] * 60 + [Decimal("107")])
    result = calculate_relative_strength(subject, reference)
    assert result.relative_performance == Decimal("0.010000")
    assert result.classification is CriterionClassification.NEUTRAL


def test_relative_strength_requires_61_aligned_observations() -> None:
    result = calculate_relative_strength(
        tuple([Decimal("100")] * 60), tuple([Decimal("100")] * 60)
    )
    assert result.classification is CriterionClassification.NOT_EVALUABLE
    assert result.quality_status is AnalysisQualityStatus.INSUFFICIENT


def test_relative_strength_parameters_reject_invalid_values() -> None:
    with pytest.raises(ValueError):
        RelativeStrengthParameters(window=0)


def test_market_context_short_term_countertrend_is_cautious() -> None:
    result = calculate_market_context(
        direction=TradingDirection.LONG,
        long_trend=CriterionClassification.POSITIVE,
        medium_trend=CriterionClassification.POSITIVE,
        short_trend=CriterionClassification.NEGATIVE,
    )
    assert result.classification is ContextClassification.CAUTIOUS
    assert result.warnings


def test_market_context_medium_countertrend_is_unfavorable() -> None:
    result = calculate_market_context(
        direction=TradingDirection.LONG,
        long_trend=CriterionClassification.POSITIVE,
        medium_trend=CriterionClassification.NEGATIVE,
        short_trend=CriterionClassification.POSITIVE,
    )
    assert result.classification is ContextClassification.UNFAVORABLE


def _qualified_input() -> CandidateEvaluationInput:
    return CandidateEvaluationInput(
        direction=TradingDirection.LONG,
        market_context=ContextClassification.FAVORABLE,
        market_quality=AnalysisQualityStatus.GOOD,
        sector_trend=CriterionClassification.POSITIVE,
        sector_relative_strength=CriterionClassification.POSITIVE,
        sector_quality=AnalysisQualityStatus.GOOD,
        underlying_long_trend=CriterionClassification.POSITIVE,
        underlying_medium_trend=CriterionClassification.POSITIVE,
        underlying_short_trend=CriterionClassification.NEUTRAL,
        underlying_relative_strength=CriterionClassification.POSITIVE,
        underlying_quality=AnalysisQualityStatus.GOOD,
        momentum=CriterionClassification.NEUTRAL,
        volatility=Decimal("0.31"),
        range_position=Decimal("0.72"),
    )


def test_candidate_v1_qualifies_with_warning_but_no_score() -> None:
    result = evaluate_candidate(_qualified_input())
    assert result.qualification is CandidateQualification.QUALIFIED
    assert result.model_version == "1.0.0"
    assert result.warnings
    assert {item.severity.value for item in result.criteria} == {
        "REQUIRED",
        "WARNING",
        "INFORMATIONAL",
    }


def test_candidate_v1_sector_relative_strength_is_required() -> None:
    value = _qualified_input()
    changed = replace(value, sector_relative_strength=CriterionClassification.NEUTRAL)
    result = evaluate_candidate(changed)
    assert result.qualification is CandidateQualification.NOT_QUALIFIED


def test_candidate_v1_missing_required_input_is_not_evaluable() -> None:
    value = _qualified_input()
    changed = replace(
        value, underlying_relative_strength=CriterionClassification.NOT_EVALUABLE
    )
    result = evaluate_candidate(changed)
    assert result.qualification is CandidateQualification.NOT_EVALUABLE


def test_candidate_v1_cautious_market_is_allowed_with_warning() -> None:
    value = _qualified_input()
    changed = replace(value, market_context=ContextClassification.CAUTIOUS)
    result = evaluate_candidate(changed)
    assert result.qualification is CandidateQualification.QUALIFIED
    assert "Market context is CAUTIOUS" in result.warnings


def test_candidate_v1_insufficient_sector_quality_is_not_evaluable() -> None:
    value = _qualified_input()
    changed = replace(value, sector_quality=AnalysisQualityStatus.INSUFFICIENT)
    result = evaluate_candidate(changed)
    assert result.qualification is CandidateQualification.NOT_EVALUABLE


def test_candidate_v1_insufficient_underlying_quality_is_not_evaluable() -> None:
    value = _qualified_input()
    changed = replace(value, underlying_quality=AnalysisQualityStatus.INSUFFICIENT)
    result = evaluate_candidate(changed)
    assert result.qualification is CandidateQualification.NOT_EVALUABLE


def test_candidate_v1_rejects_short_until_separate_rules_are_approved() -> None:
    value = _qualified_input()
    changed = replace(value, direction=TradingDirection.SHORT)
    with pytest.raises(ValueError, match="supports LONG evaluations only"):
        evaluate_candidate(changed)


def test_relative_strength_exact_positive_boundary_remains_neutral() -> None:
    subject = tuple([Decimal("100")] * 60 + [Decimal("109")])
    reference = tuple([Decimal("100")] * 60 + [Decimal("107")])
    result = calculate_relative_strength(subject, reference)
    assert result.relative_performance == Decimal("0.020000")
    assert result.classification is CriterionClassification.NEUTRAL


def test_relative_strength_exact_negative_boundary_remains_neutral() -> None:
    subject = tuple([Decimal("100")] * 60 + [Decimal("105")])
    reference = tuple([Decimal("100")] * 60 + [Decimal("107")])
    result = calculate_relative_strength(subject, reference)
    assert result.relative_performance == Decimal("-0.020000")
    assert result.classification is CriterionClassification.NEUTRAL
