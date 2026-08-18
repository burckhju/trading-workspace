"""FT-011 Post Trade domain enumerations."""

from enum import StrEnum


class PostTradeObservationStatus(StrEnum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"


class ExitReviewStatus(StrEnum):
    DRAFT = "DRAFT"
    FINALIZED = "FINALIZED"


class ExitReviewCurrentness(StrEnum):
    CURRENT = "CURRENT"
    STALE = "STALE"


class ExitReviewAssessment(StrEnum):
    GOOD = "GOOD"
    ACCEPTABLE = "ACCEPTABLE"
    IMPROVABLE = "IMPROVABLE"
    NOT_ASSESSABLE = "NOT_ASSESSABLE"
