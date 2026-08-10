"""Candidate qualification and lifecycle enumerations."""

from enum import StrEnum


class CandidateQualification(StrEnum):
    QUALIFIED = "QUALIFIED"
    NOT_QUALIFIED = "NOT_QUALIFIED"
    NOT_EVALUABLE = "NOT_EVALUABLE"


class CandidateCriterionEvaluation(StrEnum):
    FULFILLED = "FULFILLED"
    NOT_FULFILLED = "NOT_FULFILLED"
    NOT_EVALUABLE = "NOT_EVALUABLE"
    SKIPPED = "SKIPPED"


class CandidateRuleSeverity(StrEnum):
    REQUIRED = "REQUIRED"
    WARNING = "WARNING"
    INFORMATIONAL = "INFORMATIONAL"


class CandidateStatus(StrEnum):
    IDENTIFIED = "IDENTIFIED"
    UNDER_REVIEW = "UNDER_REVIEW"
    WATCHING = "WATCHING"
    READY_FOR_PLANNING = "READY_FOR_PLANNING"
    REJECTED = "REJECTED"
