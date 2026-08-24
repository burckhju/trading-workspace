"""Domain contracts for bulk external-observation imports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class ExternalObservationImportJobStatus(StrEnum):
    OPEN = "OPEN"
    PROCESSING = "PROCESSING"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    READY = "READY"
    COMPLETED = "COMPLETED"


class ExternalObservationImportFileStatus(StrEnum):
    QUEUED = "QUEUED"
    PARSED = "PARSED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    DUPLICATE = "DUPLICATE"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"


@dataclass(frozen=True, slots=True)
class ExternalObservationImportJob:
    id: UUID
    workspace_id: UUID
    status: ExternalObservationImportJobStatus
    created_at: datetime
    created_by: UUID
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ExternalObservationImportFile:
    id: UUID
    job_id: UUID
    workspace_id: UUID
    import_batch_id: UUID | None
    original_filename: str
    content_hash: str
    content_type: str | None
    file_size_bytes: int
    status: ExternalObservationImportFileStatus
    duplicate_of_file_id: UUID | None
    failure_code: str | None
    failure_detail: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ExternalObservationImportJobSummary:
    files_total: int
    files_queued: int
    files_parsed: int
    files_review_required: int
    files_duplicate: int
    files_failed: int
    files_completed: int
