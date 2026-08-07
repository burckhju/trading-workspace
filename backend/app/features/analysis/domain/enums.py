"""Enumerations for reproducible market analysis."""

from enum import StrEnum


class AnalysisStatus(StrEnum):
    DRAFT = "DRAFT"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_WARNINGS = "COMPLETED_WITH_WARNINGS"
    NOT_EVALUABLE = "NOT_EVALUABLE"
    FAILED = "FAILED"
    SUPERSEDED = "SUPERSEDED"


class AnalysisQualityStatus(StrEnum):
    GOOD = "GOOD"
    LIMITED = "LIMITED"
    INSUFFICIENT = "INSUFFICIENT"


class CriterionClassification(StrEnum):
    POSITIVE = "POSITIVE"
    NEUTRAL = "NEUTRAL"
    NEGATIVE = "NEGATIVE"
    NOT_EVALUABLE = "NOT_EVALUABLE"


class PriceField(StrEnum):
    CLOSE = "CLOSE"
    ADJUSTED_CLOSE = "ADJUSTED_CLOSE"
