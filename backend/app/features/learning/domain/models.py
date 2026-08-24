"""Immutable FT-012 Learning domain snapshots for build slice 01."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from uuid import UUID

from app.features.learning.domain.enums import (
    ExternalObservationRecordingMethod,
    IdempotencyStatus,
    ImportIssueSeverity,
    ImportRowDisposition,
    ImportValidationStatus,
    JournalVersionStatus,
    LearningEvidenceType,
    LessonEvidenceRelation,
    LessonReviewResolution,
    LessonReviewSignalStatus,
    LessonState,
    LessonSuggestionStatus,
    TradeLinkChangeReason,
    TradeLinkStatus,
)


def _require_nonblank(value: str, field: str) -> None:
    if not value.strip():
        raise ValueError(f"{field} is required")


@dataclass(frozen=True, slots=True)
class TradeJournal:
    id: UUID
    workspace_id: UUID
    trade_id: UUID
    created_at: datetime
    created_by: UUID


@dataclass(frozen=True, slots=True)
class TradeJournalVersion:
    id: UUID
    trade_journal_id: UUID
    version: int
    status: JournalVersionStatus
    what_went_well: str | None
    would_do_differently: str | None
    additional_notes: str | None
    created_at: datetime
    created_by: UUID
    updated_at: datetime
    updated_by: UUID
    finalized_at: datetime | None = None
    finalized_by: UUID | None = None
    supersedes_version_id: UUID | None = None

    def __post_init__(self) -> None:
        if self.version < 1:
            raise ValueError("trade journal version must be positive")
        if self.supersedes_version_id == self.id:
            raise ValueError("trade journal version must not supersede itself")
        if self.updated_at < self.created_at:
            raise ValueError("updated_at must not precede created_at")
        if self.status is JournalVersionStatus.DRAFT:
            if self.finalized_at is not None or self.finalized_by is not None:
                raise ValueError("DRAFT trade journal version must not be finalized")
        elif self.status is JournalVersionStatus.FINALIZED:
            if self.finalized_at is None or self.finalized_by is None:
                raise ValueError("FINALIZED trade journal version requires finalization audit")
            if self.finalized_at < self.created_at:
                raise ValueError("finalized_at must not precede created_at")

    def replace_draft_content(
        self,
        *,
        what_went_well: str | None,
        would_do_differently: str | None,
        additional_notes: str | None,
        updated_at: datetime,
        updated_by: UUID,
    ) -> TradeJournalVersion:
        if self.status is not JournalVersionStatus.DRAFT:
            raise ValueError("only DRAFT trade journal version may be edited")
        if updated_at < self.created_at:
            raise ValueError("updated_at must not precede created_at")
        return replace(
            self,
            what_went_well=what_went_well,
            would_do_differently=would_do_differently,
            additional_notes=additional_notes,
            updated_at=updated_at,
            updated_by=updated_by,
        )

    def finalize(self, *, finalized_at: datetime, finalized_by: UUID) -> TradeJournalVersion:
        if self.status is not JournalVersionStatus.DRAFT:
            raise ValueError("only DRAFT trade journal version may be finalized")
        if finalized_at < self.created_at:
            raise ValueError("finalized_at must not precede created_at")
        return replace(
            self,
            status=JournalVersionStatus.FINALIZED,
            finalized_at=finalized_at,
            finalized_by=finalized_by,
            updated_at=max(self.updated_at, finalized_at),
            updated_by=finalized_by,
        )


@dataclass(frozen=True, slots=True)
class ExternalObservationJournal:
    id: UUID
    workspace_id: UUID
    external_observation_id: UUID
    created_at: datetime
    created_by: UUID


@dataclass(frozen=True, slots=True)
class ExternalObservationJournalVersion:
    id: UUID
    external_observation_journal_id: UUID
    version: int
    status: JournalVersionStatus
    external_observation_version_id: UUID
    what_stands_out: str | None
    relevance_to_own_process: str | None
    additional_notes: str | None
    created_at: datetime
    created_by: UUID
    updated_at: datetime
    updated_by: UUID
    finalized_at: datetime | None = None
    finalized_by: UUID | None = None
    supersedes_version_id: UUID | None = None

    def __post_init__(self) -> None:
        if self.version < 1:
            raise ValueError("external journal version must be positive")
        if self.supersedes_version_id == self.id:
            raise ValueError("external journal version must not supersede itself")
        if self.updated_at < self.created_at:
            raise ValueError("updated_at must not precede created_at")
        if self.status is JournalVersionStatus.DRAFT:
            if self.finalized_at is not None or self.finalized_by is not None:
                raise ValueError("DRAFT external journal version must not be finalized")
        elif self.status is JournalVersionStatus.FINALIZED:
            if self.finalized_at is None or self.finalized_by is None:
                raise ValueError("FINALIZED external journal version requires finalization audit")
            if self.finalized_at < self.created_at:
                raise ValueError("finalized_at must not precede created_at")


@dataclass(frozen=True, slots=True)
class Lesson:
    id: UUID
    workspace_id: UUID
    title: str
    current_version_id: UUID
    current_state: LessonState
    created_at: datetime
    created_by: UUID
    updated_at: datetime
    updated_by: UUID

    def __post_init__(self) -> None:
        _require_nonblank(self.title, "title")
        if self.updated_at < self.created_at:
            raise ValueError("updated_at must not precede created_at")


@dataclass(frozen=True, slots=True)
class LessonTag:
    id: UUID
    workspace_id: UUID
    name: str
    normalized_name: str
    created_at: datetime
    created_by: UUID

    def __post_init__(self) -> None:
        _require_nonblank(self.name, "name")
        _require_nonblank(self.normalized_name, "normalized_name")

    @property
    def display_name(self) -> str:
        return self.name


@dataclass(frozen=True, slots=True)
class LessonStateTransition:
    id: UUID
    lesson_id: UUID
    from_state: LessonState | None
    to_state: LessonState
    reason: str
    related_lesson_version_id: UUID | None
    occurred_at: datetime
    occurred_by: UUID

    def __post_init__(self) -> None:
        _require_nonblank(self.reason, "reason")
        if self.from_state is not None and self.from_state is self.to_state:
            raise ValueError("lesson state transition must change state")


@dataclass(frozen=True, slots=True)
class LessonVersion:
    id: UUID
    lesson_id: UUID
    version: int
    main_category: str
    content: str
    created_at: datetime
    created_by: UUID
    supersedes_version_id: UUID | None = None

    def __post_init__(self) -> None:
        if self.version < 1:
            raise ValueError("lesson version must be positive")
        if self.supersedes_version_id == self.id:
            raise ValueError("lesson version must not supersede itself")
        _require_nonblank(self.main_category, "main_category")
        _require_nonblank(self.content, "content")


@dataclass(frozen=True, slots=True)
class LessonEvidenceLink:
    id: UUID
    lesson_version_id: UUID
    learning_evidence_id: UUID
    relation: LessonEvidenceRelation
    created_at: datetime
    created_by: UUID


@dataclass(frozen=True, slots=True)
class LessonReviewSignal:
    id: UUID
    lesson_id: UUID
    lesson_version_id: UUID
    status: LessonReviewSignalStatus
    raised_at: datetime
    opened_by: UUID
    resolution: LessonReviewResolution | None = None
    resolved_at: datetime | None = None
    resolved_by: UUID | None = None
    resulting_lesson_version_id: UUID | None = None

    def __post_init__(self) -> None:
        if self.status is LessonReviewSignalStatus.OPEN:
            if any(
                value is not None
                for value in (
                    self.resolution,
                    self.resolved_at,
                    self.resolved_by,
                    self.resulting_lesson_version_id,
                )
            ):
                raise ValueError("OPEN review signal must not carry resolution metadata")
        else:
            if self.resolution is None or self.resolved_at is None or self.resolved_by is None:
                raise ValueError("RESOLVED review signal requires resolution audit")
            if (
                self.resolution is LessonReviewResolution.NEW_VERSION_CREATED
                and self.resulting_lesson_version_id is None
            ):
                raise ValueError("NEW_VERSION_CREATED requires resulting lesson version")


@dataclass(frozen=True, slots=True)
class LessonReviewSignalEvidence:
    lesson_review_signal_id: UUID
    lesson_evidence_link_id: UUID
    lesson_version_id: UUID


@dataclass(frozen=True, slots=True)
class LessonSuggestion:
    id: UUID
    workspace_id: UUID
    status: LessonSuggestionStatus
    proposed_title: str
    proposed_main_category: str
    proposed_content: str
    created_at: datetime
    created_by: UUID | None
    decided_at: datetime | None = None
    decided_by: UUID | None = None
    resulting_lesson_id: UUID | None = None

    def __post_init__(self) -> None:
        _require_nonblank(self.proposed_title, "proposed_title")
        _require_nonblank(self.proposed_main_category, "proposed_main_category")
        _require_nonblank(self.proposed_content, "proposed_content")
        if self.status is LessonSuggestionStatus.SUGGESTED and any(
            value is not None
            for value in (self.decided_at, self.decided_by, self.resulting_lesson_id)
        ):
            raise ValueError("SUGGESTED lesson suggestion must not carry decision metadata")
        if self.status is LessonSuggestionStatus.REJECTED and (
            self.decided_at is None
            or self.decided_by is None
            or self.resulting_lesson_id is not None
        ):
            raise ValueError("REJECTED lesson suggestion requires decision audit and no result")
        if self.status is LessonSuggestionStatus.CONFIRMED and (
            self.decided_at is None or self.decided_by is None or self.resulting_lesson_id is None
        ):
            raise ValueError("CONFIRMED lesson suggestion requires decision audit and result")


@dataclass(frozen=True, slots=True)
class ExternalObservationTradeLink:
    id: UUID
    workspace_id: UUID
    external_observation_id: UUID
    current_version_id: UUID
    created_at: datetime
    created_by: UUID


@dataclass(frozen=True, slots=True)
class ExternalObservationTradeLinkVersion:
    id: UUID
    external_observation_trade_link_id: UUID
    version: int
    external_observation_version_id: UUID
    trade_id: UUID
    status: TradeLinkStatus
    change_reason: TradeLinkChangeReason
    created_at: datetime
    created_by: UUID
    supersedes_version_id: UUID | None = None
    change_note: str | None = None

    def __post_init__(self) -> None:
        if self.version < 1:
            raise ValueError("trade link version must be positive")
        if self.supersedes_version_id == self.id:
            raise ValueError("trade link version must not supersede itself")
        if self.version == 1:
            if self.status is not TradeLinkStatus.ACTIVE:
                raise ValueError("trade link V1 must be ACTIVE")
            if self.change_reason is not TradeLinkChangeReason.INITIAL_LINK:
                raise ValueError("trade link V1 must use INITIAL_LINK")
            if self.supersedes_version_id is not None:
                raise ValueError("trade link V1 must not have predecessor")
        elif self.change_reason is TradeLinkChangeReason.INITIAL_LINK:
            raise ValueError("INITIAL_LINK is only valid for V1")


@dataclass(frozen=True, slots=True)
class IdempotencyRecord:
    id: UUID
    workspace_id: UUID
    command_type: str
    idempotency_key: str
    request_fingerprint: str
    status: IdempotencyStatus
    created_at: datetime
    result_type: str | None = None
    result_id: UUID | None = None
    error_code: str | None = None
    completed_at: datetime | None = None

    def __post_init__(self) -> None:
        _require_nonblank(self.command_type, "command_type")
        _require_nonblank(self.idempotency_key, "idempotency_key")
        _require_nonblank(self.request_fingerprint, "request_fingerprint")
        terminal = (self.result_type, self.result_id, self.error_code, self.completed_at)
        if self.status is IdempotencyStatus.IN_PROGRESS and any(
            value is not None for value in terminal
        ):
            raise ValueError("IN_PROGRESS idempotency record must not carry terminal metadata")
        if self.status is IdempotencyStatus.SUCCEEDED and (
            self.result_type is None
            or self.result_id is None
            or self.completed_at is None
            or self.error_code is not None
        ):
            raise ValueError("SUCCEEDED idempotency record requires success result")
        if self.status is IdempotencyStatus.FAILED_FINAL and (
            self.error_code is None
            or self.completed_at is None
            or self.result_type is not None
            or self.result_id is not None
        ):
            raise ValueError("FAILED_FINAL idempotency record requires final error only")


@dataclass(frozen=True, slots=True)
class ExternalObservation:
    id: UUID
    workspace_id: UUID
    current_version_id: UUID
    created_at: datetime
    created_by: UUID


@dataclass(frozen=True, slots=True)
class ExternalObservationVersion:
    id: UUID
    external_observation_id: UUID
    version: int
    underlying_id: UUID
    product_id: UUID | None
    source_type: str
    source_name: str
    external_reference: str | None
    observed_at: datetime
    recorded_at: datetime
    imported_at: datetime | None
    recording_method: ExternalObservationRecordingMethod
    import_row_id: UUID | None
    source_metadata: dict[str, object] | None
    supersedes_version_id: UUID | None
    created_at: datetime
    created_by: UUID

    def __post_init__(self) -> None:
        if self.version < 1:
            raise ValueError("external observation version must be positive")
        if self.supersedes_version_id == self.id:
            raise ValueError("external observation version must not supersede itself")
        _require_nonblank(self.source_type, "source_type")
        _require_nonblank(self.source_name, "source_name")
        if self.recording_method is ExternalObservationRecordingMethod.FILE_IMPORT and (
            self.imported_at is None or self.import_row_id is None
        ):
            raise ValueError("FILE_IMPORT source requires import provenance")
        if self.recording_method is ExternalObservationRecordingMethod.MANUAL and (
            self.imported_at is not None or self.import_row_id is not None
        ):
            raise ValueError("MANUAL source must not carry import provenance")


@dataclass(frozen=True, slots=True)
class ExternalObservationImportBatch:
    id: UUID
    workspace_id: UUID
    original_filename: str
    content_hash: str
    content_type: str | None
    file_size_bytes: int
    imported_at: datetime
    imported_by: UUID

    def __post_init__(self) -> None:
        _require_nonblank(self.original_filename, "original_filename")
        if len(self.content_hash) != 64:
            raise ValueError("content_hash must be a 64-character SHA-256 hex string")
        if self.file_size_bytes <= 0:
            raise ValueError("file_size_bytes must be positive")


@dataclass(frozen=True, slots=True)
class ExternalObservationImportRow:
    id: UUID
    batch_id: UUID
    workspace_id: UUID
    source_row_number: int
    raw_payload: dict[str, object]
    validation_status: ImportValidationStatus
    disposition: ImportRowDisposition
    resolved_underlying_id: UUID | None
    resolved_product_id: UUID | None
    target_external_observation_id: UUID | None
    accepted_external_observation_version_id: UUID | None
    disposed_at: datetime | None
    disposed_by: UUID | None
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        if self.source_row_number < 1:
            raise ValueError("source_row_number must be positive")
        if self.updated_at < self.created_at:
            raise ValueError("updated_at must not precede created_at")
        if self.disposition is ImportRowDisposition.PENDING and (
            self.disposed_at is not None
            or self.disposed_by is not None
            or self.accepted_external_observation_version_id is not None
        ):
            raise ValueError("PENDING import row must not carry disposition result")
        if self.disposition is ImportRowDisposition.ACCEPTED and (
            self.disposed_at is None
            or self.disposed_by is None
            or self.accepted_external_observation_version_id is None
        ):
            raise ValueError("ACCEPTED import row requires disposition result")
        if self.disposition is ImportRowDisposition.DISCARDED and (
            self.disposed_at is None
            or self.disposed_by is None
            or self.accepted_external_observation_version_id is not None
        ):
            raise ValueError("DISCARDED import row requires audit and no accepted version")


@dataclass(frozen=True, slots=True)
class ExternalObservationImportRowIssue:
    id: UUID
    import_row_id: UUID
    code: str
    severity: ImportIssueSeverity
    field: str | None
    message: str
    created_at: datetime

    def __post_init__(self) -> None:
        _require_nonblank(self.code, "code")
        _require_nonblank(self.message, "message")


@dataclass(frozen=True, slots=True)
class LearningEvidence:
    id: UUID
    workspace_id: UUID
    evidence_type: LearningEvidenceType
    created_at: datetime


@dataclass(frozen=True, slots=True)
class FT011Evidence:
    learning_evidence_id: UUID
    trade_id: UUID
    post_trade_observation_id: UUID
    exit_review_id: UUID
    exit_review_version_id: UUID


@dataclass(frozen=True, slots=True)
class TradeJournalVersionEvidence:
    learning_evidence_id: UUID
    trade_journal_version_id: UUID


@dataclass(frozen=True, slots=True)
class ExternalObservationEvidence:
    learning_evidence_id: UUID
    external_observation_version_id: UUID


@dataclass(frozen=True, slots=True)
class ExternalObservationJournalVersionEvidence:
    learning_evidence_id: UUID
    external_observation_journal_version_id: UUID
