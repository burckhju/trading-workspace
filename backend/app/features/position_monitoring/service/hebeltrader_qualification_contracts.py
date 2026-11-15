"""Saved comparison evidence and request receipts, separate from target evaluation."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal
from uuid import UUID

from app.features.learning.application.hebeltrader_source_reader import (
    ConfirmedHebeltraderSource,
)
from app.features.market_data.service.hebeltrader_history import HebeltraderPriceHistory
from app.features.position_monitoring.domain.hebeltrader_targets import (
    TargetComparisonQualification,
)
from app.features.position_monitoring.service.hebeltrader_target_contracts import (
    HebeltraderTargetsReport,
    TargetAssessmentView,
)
from app.features.trade_position.service.hebeltrader_evidence import HebeltraderScaleBasis


@dataclass(frozen=True, slots=True)
class TargetQualificationIssue:
    code: str
    detail: str


@dataclass(frozen=True, slots=True)
class TargetQualificationEntry:
    product_id: UUID
    underlying_id: UUID
    option_direction: Literal["CALL", "PUT"] | None
    opened_at: datetime | None
    opened_on: date | None
    opening_timezone: str | None
    evidence_revision_id: UUID | None


@dataclass(frozen=True, slots=True)
class TargetQualificationBinding:
    history_fingerprint: str
    listing_fingerprint: str
    source_version_id: UUID
    source_scale_reference: str


@dataclass(frozen=True, slots=True)
class TargetQualificationRowReview:
    source_row_id: UUID
    fingerprint: str
    status: Literal["SUITABLE_AFTER_CONFIRMATION", "UNSUITABLE"]
    issues: tuple[TargetQualificationIssue, ...]


@dataclass(frozen=True, slots=True)
class TargetQualificationReadiness:
    status: Literal["REVIEWABLE", "BLOCKED", "NOT_APPLICABLE"]
    issues: tuple[TargetQualificationIssue, ...]
    usable_row_count: int
    rows: tuple[TargetQualificationRowReview, ...]


@dataclass(frozen=True, slots=True)
class StoredTargetQualification:
    status: Literal["MISSING", "REUSABLE", "STALE"]
    value: TargetComparisonQualification | None
    # This identifies the containing snapshot, not the original human attestor.
    contained_in_assessment_id: UUID | None
    contained_in_recorded_at: datetime | None
    origin: Literal["USER_DECLARATION_NOT_INDEPENDENT_VERIFICATION"] = (
        "USER_DECLARATION_NOT_INDEPENDENT_VERIFICATION"
    )


@dataclass(frozen=True, slots=True)
class TargetQualificationPreview:
    report: HebeltraderTargetsReport
    entry: TargetQualificationEntry
    source: ConfirmedHebeltraderSource | None
    attempted_source_version_id: UUID | None
    source_issues: tuple[TargetQualificationIssue, ...]
    source_scale: HebeltraderScaleBasis
    history: HebeltraderPriceHistory
    readiness: TargetQualificationReadiness
    qualification: StoredTargetQualification
    qualification_binding: TargetQualificationBinding | None
    notices: tuple[str, ...]
    definition_version: Literal["hebeltrader-qualification-preview-v1"] = (
        "hebeltrader-qualification-preview-v1"
    )
    operation_status: Literal["READ_ONLY"] = "READ_ONLY"


@dataclass(frozen=True, slots=True)
class TargetRequestStatus:
    trade_id: UUID
    position_id: UUID
    request_id: UUID
    status: Literal["RECORDED", "UNKNOWN"]
    read_started_at: datetime
    read_completed_at: datetime
    recorded_at: datetime | None
    assessment: TargetAssessmentView | None
    qualification: TargetComparisonQualification | None
    definition_version: Literal["hebeltrader-request-status-v1"] = "hebeltrader-request-status-v1"
    operation_status: Literal["READ_ONLY"] = "READ_ONLY"
