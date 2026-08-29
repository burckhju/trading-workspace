from decimal import Decimal

import pytest

from app.features.analysis.domain.enums import AnalysisQualityStatus, CriterionClassification
from app.features.analysis.domain.top_down import ContextClassification, TradingDirection
from app.features.candidate.domain.enums import CandidateQualification
from app.features.candidate.domain.models import CandidateEvaluationInput
from app.features.candidate.domain.runtime_definition import (
    adapt_candidate_runtime_definition,
    evaluate_candidate_with_runtime_rules,
)


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


def _definition() -> dict[str, object]:
    return {
        "schema": "TOP_DOWN_CANDIDATE/1.0",
        "direction": "LONG",
        "market_context_allowed": ["FAVORABLE", "CAUTIOUS"],
    }


def test_adapts_supported_definition_and_preserves_governed_identity() -> None:
    rules = adapt_candidate_runtime_definition(
        model_key="TOP_DOWN_CANDIDATE",
        version=3,
        definition=_definition(),
    )

    result = evaluate_candidate_with_runtime_rules(_qualified_input(), rules)

    assert result.qualification is CandidateQualification.QUALIFIED
    assert result.model_id == "TOP_DOWN_CANDIDATE"
    assert result.model_version == "3"


def test_rejects_unknown_definition_keys_instead_of_ignoring_semantics() -> None:
    definition = {**_definition(), "min_relative_strength": 1.2}

    with pytest.raises(ValueError, match="unsupported Candidate definition keys"):
        adapt_candidate_runtime_definition(
            model_key="TOP_DOWN_CANDIDATE",
            version=2,
            definition=definition,
        )


def test_rejects_changed_market_context_semantics_for_schema_v1() -> None:
    definition = {**_definition(), "market_context_allowed": ["FAVORABLE"]}

    with pytest.raises(ValueError, match="requires FAVORABLE and CAUTIOUS"):
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
            definition=_definition(),
        )


def test_rejects_unsupported_schema() -> None:
    definition = {**_definition(), "schema": "TOP_DOWN_CANDIDATE/2.0"}

    with pytest.raises(ValueError, match="unsupported Candidate definition schema"):
        adapt_candidate_runtime_definition(
            model_key="TOP_DOWN_CANDIDATE",
            version=2,
            definition=definition,
        )
