"""Immutable FT-005 candidate evaluation domain model."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

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

CANDIDATE_MODEL_ID = "TOP_DOWN_CANDIDATE"
CANDIDATE_MODEL_VERSION = "1.0.0"


@dataclass(frozen=True, slots=True)
class AnalysisReference:
    analysis_id: UUID
    version: int
    model_id: str
    model_version: str

    def __post_init__(self) -> None:
        if self.version <= 0:
            raise ValueError("analysis reference version must be positive")


@dataclass(frozen=True, slots=True)
class CandidateCriterionResult:
    criterion_id: str
    group: str
    severity: CandidateRuleSeverity
    evaluation: CandidateCriterionEvaluation
    source: str
    actual_value: str | None
    expected_value: str | None
    explanation: str
    numeric_value: Decimal | None = None


@dataclass(frozen=True, slots=True)
class CandidateEvaluationInput:
    direction: TradingDirection
    market_context: ContextClassification
    market_quality: AnalysisQualityStatus
    sector_trend: CriterionClassification
    sector_relative_strength: CriterionClassification
    sector_quality: AnalysisQualityStatus
    underlying_long_trend: CriterionClassification
    underlying_medium_trend: CriterionClassification
    underlying_short_trend: CriterionClassification
    underlying_relative_strength: CriterionClassification
    underlying_quality: AnalysisQualityStatus
    momentum: CriterionClassification | None = None
    volatility: Decimal | None = None
    range_position: Decimal | None = None


@dataclass(frozen=True, slots=True)
class CandidateEvaluationResult:
    model_id: str
    model_version: str
    qualification: CandidateQualification
    criteria: tuple[CandidateCriterionResult, ...]
    warnings: tuple[str, ...]
    quality_status: AnalysisQualityStatus


@dataclass(frozen=True, slots=True)
class CandidateEvaluationSnapshot:
    id: UUID
    candidate_id: UUID
    version: int
    direction: TradingDirection
    result: CandidateEvaluationResult
    market_reference: AnalysisReference
    sector_reference: AnalysisReference
    underlying_reference: AnalysisReference
    evaluated_at: datetime
