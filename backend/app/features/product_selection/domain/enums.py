"""FT-008 Product Selection domain enumerations."""

from enum import StrEnum


class DataAvailability(StrEnum):
    AVAILABLE = "AVAILABLE"
    MISSING = "MISSING"
    INSUFFICIENT = "INSUFFICIENT"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class CriterionOutcome(StrEnum):
    FULFILLED = "FULFILLED"
    NOT_FULFILLED = "NOT_FULFILLED"
    NOT_EVALUABLE = "NOT_EVALUABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class EligibilityStatus(StrEnum):
    ELIGIBLE = "ELIGIBLE"
    INELIGIBLE = "INELIGIBLE"
    NOT_EVALUABLE = "NOT_EVALUABLE"


class MetricOrigin(StrEnum):
    CALCULATED = "CALCULATED"
    PROVIDER = "PROVIDER"
