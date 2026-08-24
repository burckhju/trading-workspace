"""Persisted and public FT-012 enum values."""

from enum import StrEnum


class JournalVersionStatus(StrEnum):
    DRAFT = "DRAFT"
    FINALIZED = "FINALIZED"


class ImportValidationStatus(StrEnum):
    VALID = "VALID"
    UNRESOLVED = "UNRESOLVED"
    INVALID = "INVALID"


class ImportRowDisposition(StrEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    DISCARDED = "DISCARDED"


class LessonState(StrEnum):
    CURRENT = "CURRENT"
    REVIEW_RECOMMENDED = "REVIEW_RECOMMENDED"
    RETIRED = "RETIRED"


class LessonEvidenceRelation(StrEnum):
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    CONTEXTUAL = "CONTEXTUAL"


class LessonReviewSignalStatus(StrEnum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"


class LessonReviewResolution(StrEnum):
    UNCHANGED_CONFIRMED = "UNCHANGED_CONFIRMED"
    NEW_VERSION_CREATED = "NEW_VERSION_CREATED"
    LESSON_RETIRED = "LESSON_RETIRED"


class LessonSuggestionStatus(StrEnum):
    SUGGESTED = "SUGGESTED"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"


class TradeLinkStatus(StrEnum):
    ACTIVE = "ACTIVE"
    RETRACTED = "RETRACTED"


class TradeLinkChangeReason(StrEnum):
    INITIAL_LINK = "INITIAL_LINK"
    TARGET_CORRECTED = "TARGET_CORRECTED"
    LINK_RETRACTED = "LINK_RETRACTED"
    LINK_REACTIVATED = "LINK_REACTIVATED"
    LINK_REACTIVATED_WITH_TARGET_CORRECTION = "LINK_REACTIVATED_WITH_TARGET_CORRECTION"
    SOURCE_REVALIDATED = "SOURCE_REVALIDATED"


class IdempotencyStatus(StrEnum):
    IN_PROGRESS = "IN_PROGRESS"
    SUCCEEDED = "SUCCEEDED"
    FAILED_FINAL = "FAILED_FINAL"


class EvidenceMatchPriority(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ExternalObservationRecordingMethod(StrEnum):
    FILE_IMPORT = "FILE_IMPORT"
    MANUAL = "MANUAL"


class ImportIssueSeverity(StrEnum):
    ERROR = "ERROR"
    WARNING = "WARNING"


class LearningEvidenceType(StrEnum):
    FT011 = "FT011"
    TRADE_JOURNAL_VERSION = "TRADE_JOURNAL_VERSION"
    EXTERNAL_OBSERVATION = "EXTERNAL_OBSERVATION"
    EXTERNAL_OBSERVATION_JOURNAL_VERSION = "EXTERNAL_OBSERVATION_JOURNAL_VERSION"
