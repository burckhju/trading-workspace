"""Candidate domain exports."""

from app.features.candidate.domain.enums import (
    CandidateCriterionEvaluation,
    CandidateQualification,
    CandidateRuleSeverity,
    CandidateStatus,
)
from app.features.candidate.domain.models import (
    CANDIDATE_MODEL_ID,
    CANDIDATE_MODEL_VERSION,
    AnalysisReference,
    CandidateEvaluationInput,
    CandidateEvaluationResult,
)
from app.features.candidate.domain.qualification import evaluate_candidate

__all__ = [
    "CANDIDATE_MODEL_ID",
    "CANDIDATE_MODEL_VERSION",
    "AnalysisReference",
    "CandidateCriterionEvaluation",
    "CandidateEvaluationInput",
    "CandidateEvaluationResult",
    "CandidateQualification",
    "CandidateRuleSeverity",
    "CandidateStatus",
    "evaluate_candidate",
]
