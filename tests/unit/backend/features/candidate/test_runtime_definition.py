from decimal import Decimal

import pytest

from app.features.analysis.domain.enums import AnalysisQualityStatus, CriterionClassification
from app.features.analysis.domain.top_down import ContextClassification, TradingDirection
from app.features.candidate.domain.enums import (
    CandidateCriterionEvaluation,
    CandidateQualification,
)
from app.features.candidate.domain.models import CandidateEvaluationInput
from app.features.candidate.domain.runtime_definition import (
    adapt_candidate_runtime_definition,
    evaluate_candidate_with_runtime_rules,
)


def _qualified_input(
    market_context: ContextClassification = ContextClassification.FAVORABLE,
    market_quality: AnalysisQualityStatus = AnalysisQualityStatus.GOOD,
) -> CandidateEvaluationInput:
    return CandidateEvaluationInput(
        direction=TradingDirection.LONG,
        market_context=market_context,
        market_quality=market_quality,
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


def _definition_v1() -> dict[str, object]:
    return {
        "schema": "TOP_DOWN_CANDIDATE/1.0",
        "direction": "LONG",
        "market_context_allowed": ["FAVORABLE", "CAUTIOUS"],
    }


def _definition_v2(*contexts: str) -> dict[str, object]:
    return {
        "schema": "TOP_DOWN_CANDIDATE/2.0",
        "direction": "LONG",
        "market_context_allowed": list(contexts),
    }


def test_adapts_supported_v1_definition_and_preserves_governed_identity() -> None:
    rules = adapt_candidate_runtime_definition(
        model_key="TOP_DOWN_CANDIDATE",
        version=3,
        definition=_definition_v1(),
    )

    result = evaluate_candidate_with_runtime_rules(_qualified_input(), rules)

    assert result.qualification is CandidateQualification.QUALIFIED
    assert result.model_id == "TOP_DOWN_CANDIDATE"
    assert result.model_version == "3"


def test_v2_market_context_parameter_changes_real_candidate_result() -> None:
    value = _qualified_input(ContextClassification.CAUTIOUS)
    permissive = adapt_candidate_runtime_definition(
        model_key="TOP_DOWN_CANDIDATE",
        version=10,
        definition=_definition_v2("FAVORABLE", "CAUTIOUS"),
    )
    strict = adapt_candidate_runtime_definition(
        model_key="TOP_DOWN_CANDIDATE",
        version=11,
        definition=_definition_v2("FAVORABLE"),
    )

    permissive_result = evaluate_candidate_with_runtime_rules(value, permissive)
    strict_result = evaluate_candidate_with_runtime_rules(value, strict)

    assert permissive_result.qualification is CandidateQualification.QUALIFIED
    assert strict_result.qualification is CandidateQualification.NOT_QUALIFIED
    assert permissive_result.model_version == "10"
    assert strict_result.model_version == "11"
    market = next(item for item in strict_result.criteria if item.criterion_id == "TD-MARKET-001")
    assert market.evaluation is CandidateCriterionEvaluation.NOT_FULFILLED
    assert market.actual_value == "CAUTIOUS"
    assert market.expected_value == "FAVORABLE"
    assert "CAUTIOUS is not allowed" in market.explanation
    assert "FAVORABLE" in market.explanation


def test_v2_preserves_not_evaluable_for_missing_market_input() -> None:
    rules = adapt_candidate_runtime_definition(
        model_key="TOP_DOWN_CANDIDATE",
        version=12,
        definition=_definition_v2("FAVORABLE"),
    )

    result = evaluate_candidate_with_runtime_rules(
        _qualified_input(ContextClassification.NOT_EVALUABLE),
        rules,
    )

    market = next(item for item in result.criteria if item.criterion_id == "TD-MARKET-001")
    assert market.evaluation is CandidateCriterionEvaluation.NOT_EVALUABLE
    assert result.qualification is CandidateQualification.NOT_EVALUABLE


def test_rejects_unknown_definition_keys_instead_of_ignoring_semantics() -> None:
    definition = {**_definition_v1(), "min_relative_strength": 1.2}

    with pytest.raises(ValueError, match="unsupported Candidate definition keys"):
        adapt_candidate_runtime_definition(
            model_key="TOP_DOWN_CANDIDATE",
            version=2,
            definition=definition,
        )


def test_rejects_changed_market_context_semantics_for_schema_v1() -> None:
    definition = {**_definition_v1(), "market_context_allowed": ["FAVORABLE"]}

    with pytest.raises(ValueError, match="requires FAVORABLE and CAUTIOUS"):
        adapt_candidate_runtime_definition(
            model_key="TOP_DOWN_CANDIDATE",
            version=2,
            definition=definition,
        )


@pytest.mark.parametrize(
    "definition",
    [
        {"schema": "TOP_DOWN_CANDIDATE/2.0", "direction": "LONG"},
        _definition_v2(),
        _definition_v2("CAUTIOUS"),
        _definition_v2("UNFAVORABLE"),
        _definition_v2("NOT_EVALUABLE"),
    ],
)
def test_v2_invalid_or_missing_market_context_configuration_fails_closed(
    definition: dict[str, object],
) -> None:
    with pytest.raises(ValueError, match=r"market_context_allowed|TOP_DOWN_CANDIDATE/2\.0"):
        adapt_candidate_runtime_definition(
            model_key="TOP_DOWN_CANDIDATE",
            version=2,
            definition=definition,
        )


def test_rejects_wrong_model_key() -> None:
    with pytest.raises(ValueError, match="unsupported governed model key"):
        adapt_candidate_runtime_definition(
            model_key="OTHER_MODEL",
            version=1,
            definition=_definition_v1(),
        )


def test_rejects_unsupported_schema() -> None:
    definition = {**_definition_v1(), "schema": "TOP_DOWN_CANDIDATE/3.0"}

    with pytest.raises(ValueError, match="unsupported Candidate definition schema"):
        adapt_candidate_runtime_definition(
            model_key="TOP_DOWN_CANDIDATE",
            version=2,
            definition=definition,
        )
