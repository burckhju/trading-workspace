"""Deterministic TOP_DOWN_CANDIDATE 1.0 qualification model."""

from __future__ import annotations

from app.features.analysis.domain.enums import (
    AnalysisQualityStatus,
    CriterionClassification,
)
from app.features.analysis.domain.top_down import (
    ContextClassification,
    TradingDirection,
)
from app.features.candidate.domain.enums import (
    CandidateCriterionEvaluation,
    CandidateQualification,
    CandidateRuleSeverity,
)
from app.features.candidate.domain.models import (
    CANDIDATE_MODEL_ID,
    CANDIDATE_MODEL_VERSION,
    CandidateCriterionResult,
    CandidateEvaluationInput,
    CandidateEvaluationResult,
)


def _required(
    criterion_id: str,
    group: str,
    source: str,
    actual: str,
    fulfilled: bool | None,
    expected: str,
    explanation: str,
) -> CandidateCriterionResult:
    evaluation = (
        CandidateCriterionEvaluation.NOT_EVALUABLE
        if fulfilled is None
        else (
            CandidateCriterionEvaluation.FULFILLED
            if fulfilled
            else CandidateCriterionEvaluation.NOT_FULFILLED
        )
    )
    return CandidateCriterionResult(
        criterion_id,
        group,
        CandidateRuleSeverity.REQUIRED,
        evaluation,
        source,
        actual,
        expected,
        explanation,
    )


def _warning(
    criterion_id: str,
    group: str,
    source: str,
    actual: str,
    fulfilled: bool | None,
    expected: str,
    explanation: str,
) -> CandidateCriterionResult:
    evaluation = (
        CandidateCriterionEvaluation.NOT_EVALUABLE
        if fulfilled is None
        else (
            CandidateCriterionEvaluation.FULFILLED
            if fulfilled
            else CandidateCriterionEvaluation.NOT_FULFILLED
        )
    )
    return CandidateCriterionResult(
        criterion_id,
        group,
        CandidateRuleSeverity.WARNING,
        evaluation,
        source,
        actual,
        expected,
        explanation,
    )


def _matches_direction(value: CriterionClassification, direction: TradingDirection) -> bool | None:
    if value is CriterionClassification.NOT_EVALUABLE:
        return None
    expected = (
        CriterionClassification.POSITIVE
        if direction is TradingDirection.LONG
        else CriterionClassification.NEGATIVE
    )
    return value is expected


def evaluate_candidate(value: CandidateEvaluationInput) -> CandidateEvaluationResult:
    """Evaluate TOP_DOWN_CANDIDATE 1.0 without score or hidden weighting.

    Candidate Model 1.0 is deliberately LONG-only. The domain keeps a direction
    type for forward compatibility, but SHORT rules require a separately approved
    model version rather than implicitly mirroring LONG rules.
    """

    if value.direction is not TradingDirection.LONG:
        raise ValueError("TOP_DOWN_CANDIDATE 1.0 supports LONG evaluations only")

    direction_expected = "POSITIVE"
    market_allowed = {
        ContextClassification.FAVORABLE,
        ContextClassification.CAUTIOUS,
    }
    market_eval: bool | None = (
        None
        if value.market_context is ContextClassification.NOT_EVALUABLE
        or value.market_quality is AnalysisQualityStatus.INSUFFICIENT
        else value.market_context in market_allowed
    )
    criteria: list[CandidateCriterionResult] = [
        _required(
            "TD-MARKET-001",
            "MARKET",
            "MarketContextAssessment",
            value.market_context.value,
            market_eval,
            "FAVORABLE or CAUTIOUS",
            "Primary market context must support the requested direction",
        ),
        _required(
            "TD-SECTOR-001",
            "SECTOR",
            "SectorAnalysis.LONG_TREND",
            value.sector_trend.value,
            (
                None
                if value.sector_quality is AnalysisQualityStatus.INSUFFICIENT
                else _matches_direction(value.sector_trend, value.direction)
            ),
            direction_expected,
            "Sector trend must align with the requested direction",
        ),
        _required(
            "TD-SECTOR-002",
            "SECTOR",
            "RelativeStrength(Sector, Market)",
            value.sector_relative_strength.value,
            (
                None
                if value.sector_quality is AnalysisQualityStatus.INSUFFICIENT
                else _matches_direction(value.sector_relative_strength, value.direction)
            ),
            direction_expected,
            "Sector must outperform the primary market in the requested direction",
        ),
        _required(
            "TD-UNDERLYING-001",
            "UNDERLYING",
            "UnderlyingAnalysis.LONG_TREND",
            value.underlying_long_trend.value,
            (
                None
                if value.underlying_quality is AnalysisQualityStatus.INSUFFICIENT
                else _matches_direction(value.underlying_long_trend, value.direction)
            ),
            direction_expected,
            "Underlying long trend must align with the requested direction",
        ),
        _required(
            "TD-UNDERLYING-002",
            "UNDERLYING",
            "UnderlyingAnalysis.MEDIUM_TREND",
            value.underlying_medium_trend.value,
            (
                None
                if value.underlying_quality is AnalysisQualityStatus.INSUFFICIENT
                else _matches_direction(value.underlying_medium_trend, value.direction)
            ),
            direction_expected,
            "Underlying medium trend must align with the requested direction",
        ),
        _required(
            "TD-UNDERLYING-003",
            "UNDERLYING",
            "RelativeStrength(Underlying, Sector)",
            value.underlying_relative_strength.value,
            (
                None
                if value.underlying_quality is AnalysisQualityStatus.INSUFFICIENT
                else _matches_direction(value.underlying_relative_strength, value.direction)
            ),
            direction_expected,
            "Underlying must outperform its sector in the requested direction",
        ),
        _warning(
            "TD-UNDERLYING-W01",
            "UNDERLYING",
            "UnderlyingAnalysis.SHORT_TREND",
            value.underlying_short_trend.value,
            (
                None
                if value.underlying_quality is AnalysisQualityStatus.INSUFFICIENT
                else _matches_direction(value.underlying_short_trend, value.direction)
            ),
            direction_expected,
            "Short-term trend is timing context and does not block qualification",
        ),
    ]
    if value.momentum is not None:
        criteria.append(
            _warning(
                "TD-UNDERLYING-W02",
                "UNDERLYING",
                "UnderlyingAnalysis.MOMENTUM",
                value.momentum.value,
                (
                    None
                    if value.underlying_quality is AnalysisQualityStatus.INSUFFICIENT
                    else _matches_direction(value.momentum, value.direction)
                ),
                direction_expected,
                "Momentum is warning-only in Candidate Model V1",
            )
        )
    if value.volatility is not None:
        criteria.append(
            CandidateCriterionResult(
                "TD-UNDERLYING-I01",
                "UNDERLYING",
                CandidateRuleSeverity.INFORMATIONAL,
                CandidateCriterionEvaluation.FULFILLED,
                "UnderlyingAnalysis.VOLATILITY",
                str(value.volatility),
                None,
                "Realized volatility is descriptive only in Candidate Model V1",
                value.volatility,
            )
        )
    if value.range_position is not None:
        criteria.append(
            CandidateCriterionResult(
                "TD-UNDERLYING-I02",
                "UNDERLYING",
                CandidateRuleSeverity.INFORMATIONAL,
                CandidateCriterionEvaluation.FULFILLED,
                "UnderlyingAnalysis.RANGE_POSITION",
                str(value.range_position),
                None,
                "Range position is descriptive only in Candidate Model V1",
                value.range_position,
            )
        )

    required = [item for item in criteria if item.severity is CandidateRuleSeverity.REQUIRED]
    if any(item.evaluation is CandidateCriterionEvaluation.NOT_FULFILLED for item in required):
        qualification = CandidateQualification.NOT_QUALIFIED
    elif any(item.evaluation is CandidateCriterionEvaluation.NOT_EVALUABLE for item in required):
        qualification = CandidateQualification.NOT_EVALUABLE
    else:
        qualification = CandidateQualification.QUALIFIED

    warnings = [
        item.explanation
        for item in criteria
        if item.severity is CandidateRuleSeverity.WARNING
        and item.evaluation is not CandidateCriterionEvaluation.FULFILLED
    ]
    if value.market_context is ContextClassification.CAUTIOUS:
        warnings.append("Market context is CAUTIOUS")
    qualities = (value.market_quality, value.sector_quality, value.underlying_quality)
    if AnalysisQualityStatus.INSUFFICIENT in qualities:
        quality = AnalysisQualityStatus.INSUFFICIENT
    elif AnalysisQualityStatus.LIMITED in qualities:
        quality = AnalysisQualityStatus.LIMITED
        warnings.append("At least one required analysis has LIMITED quality")
    else:
        quality = AnalysisQualityStatus.GOOD
    return CandidateEvaluationResult(
        CANDIDATE_MODEL_ID,
        CANDIDATE_MODEL_VERSION,
        qualification,
        tuple(criteria),
        tuple(dict.fromkeys(warnings)),
        quality,
    )
