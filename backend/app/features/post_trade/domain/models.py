"""Immutable FT-011 Post Trade domain snapshots."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from uuid import UUID

from app.features.post_trade.domain.enums import (
    ExitReviewAssessment,
    ExitReviewCurrentness,
    ExitReviewStatus,
    PostTradeObservationStatus,
)

FT011_V1_OBSERVATION_COUNT = 20


@dataclass(frozen=True, slots=True)
class PostTradeObservation:
    id: UUID
    workspace_id: UUID
    trade_id: UUID
    underlying_listing_id: UUID
    status: PostTradeObservationStatus
    target_observation_count: int
    started_at: datetime
    started_by: UUID
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        if self.target_observation_count != FT011_V1_OBSERVATION_COUNT:
            raise ValueError(f"FT-011 V1 observation count must be {FT011_V1_OBSERVATION_COUNT}")

        if self.created_at < self.started_at:
            raise ValueError("created_at must not precede started_at")

        if self.updated_at < self.created_at:
            raise ValueError("updated_at must not precede created_at")

        if self.status is PostTradeObservationStatus.ACTIVE:
            if self.completed_at is not None:
                raise ValueError("ACTIVE post-trade observation must not have completed_at")

        elif self.status is PostTradeObservationStatus.COMPLETED:
            if self.completed_at is None:
                raise ValueError("COMPLETED post-trade observation requires completed_at")
            if self.completed_at < self.started_at:
                raise ValueError("completed_at must not precede started_at")

    @property
    def is_complete(self) -> bool:
        return self.status is PostTradeObservationStatus.COMPLETED

    def complete(self, *, completed_at: datetime) -> PostTradeObservation:
        if self.status is PostTradeObservationStatus.COMPLETED:
            raise ValueError("post-trade observation is already completed")
        if completed_at < self.started_at:
            raise ValueError("completed_at must not precede started_at")

        return replace(
            self,
            status=PostTradeObservationStatus.COMPLETED,
            completed_at=completed_at,
            updated_at=completed_at,
        )


@dataclass(frozen=True, slots=True)
class ExitReview:
    id: UUID
    workspace_id: UUID
    post_trade_observation_id: UUID
    created_at: datetime
    created_by: UUID


@dataclass(frozen=True, slots=True)
class ExitReviewVersion:
    id: UUID
    exit_review_id: UUID
    version: int
    status: ExitReviewStatus
    currentness: ExitReviewCurrentness

    timing: ExitReviewAssessment | None
    process_adherence: ExitReviewAssessment | None
    risk_decision: ExitReviewAssessment | None
    overall_exit_decision: ExitReviewAssessment | None
    rationale: str | None

    input_fingerprint: str | None

    created_at: datetime
    created_by: UUID

    finalized_at: datetime | None = None
    finalized_by: UUID | None = None

    supersedes_version_id: UUID | None = None

    stale_at: datetime | None = None
    stale_reason: str | None = None

    def __post_init__(self) -> None:
        if self.version < 1:
            raise ValueError("exit review version must be positive")

        if self.supersedes_version_id == self.id:
            raise ValueError("exit review version must not supersede itself")

        if self.status is ExitReviewStatus.DRAFT:
            self._validate_draft()
        elif self.status is ExitReviewStatus.FINALIZED:
            self._validate_finalized()

        if self.currentness is ExitReviewCurrentness.CURRENT:
            if self.stale_at is not None or self.stale_reason is not None:
                raise ValueError("CURRENT exit review version must not carry stale metadata")

        elif self.currentness is ExitReviewCurrentness.STALE:
            if self.status is not ExitReviewStatus.FINALIZED:
                raise ValueError("only FINALIZED exit review version may be STALE")
            if self.stale_at is None:
                raise ValueError("STALE exit review version requires stale_at")
            if not self.stale_reason or not self.stale_reason.strip():
                raise ValueError("STALE exit review version requires stale_reason")
            if self.finalized_at is not None and self.stale_at < self.finalized_at:
                raise ValueError("stale_at must not precede finalized_at")

    def _validate_draft(self) -> None:
        if self.currentness is not ExitReviewCurrentness.CURRENT:
            raise ValueError("DRAFT exit review version must be CURRENT")

        if self.finalized_at is not None or self.finalized_by is not None:
            raise ValueError("DRAFT exit review version must not carry finalization metadata")

        if self.input_fingerprint is not None:
            raise ValueError("DRAFT exit review version must not carry input_fingerprint")

        if self.stale_at is not None or self.stale_reason is not None:
            raise ValueError("DRAFT exit review version must not carry stale metadata")

    def _validate_finalized(self) -> None:
        assessments = (
            self.timing,
            self.process_adherence,
            self.risk_decision,
            self.overall_exit_decision,
        )
        if any(value is None for value in assessments):
            raise ValueError("FINALIZED exit review version requires all assessments")

        if not self.rationale or not self.rationale.strip():
            raise ValueError("FINALIZED exit review version requires rationale")

        if not self.input_fingerprint or not self.input_fingerprint.strip():
            raise ValueError("FINALIZED exit review version requires input_fingerprint")

        if self.finalized_at is None or self.finalized_by is None:
            raise ValueError("FINALIZED exit review version requires finalization metadata")

        if self.finalized_at < self.created_at:
            raise ValueError("finalized_at must not precede created_at")

    @property
    def is_finalized(self) -> bool:
        return self.status is ExitReviewStatus.FINALIZED

    @property
    def is_stale(self) -> bool:
        return self.currentness is ExitReviewCurrentness.STALE

    def finalize(
        self,
        *,
        timing: ExitReviewAssessment,
        process_adherence: ExitReviewAssessment,
        risk_decision: ExitReviewAssessment,
        overall_exit_decision: ExitReviewAssessment,
        rationale: str,
        input_fingerprint: str,
        finalized_at: datetime,
        finalized_by: UUID,
    ) -> ExitReviewVersion:
        if self.status is not ExitReviewStatus.DRAFT:
            raise ValueError("only DRAFT exit review version may be finalized")

        if finalized_at < self.created_at:
            raise ValueError("finalized_at must not precede created_at")

        return replace(
            self,
            status=ExitReviewStatus.FINALIZED,
            currentness=ExitReviewCurrentness.CURRENT,
            timing=timing,
            process_adherence=process_adherence,
            risk_decision=risk_decision,
            overall_exit_decision=overall_exit_decision,
            rationale=rationale,
            input_fingerprint=input_fingerprint,
            finalized_at=finalized_at,
            finalized_by=finalized_by,
            stale_at=None,
            stale_reason=None,
        )

    def mark_stale(
        self,
        *,
        stale_at: datetime,
        stale_reason: str,
    ) -> ExitReviewVersion:
        if self.status is not ExitReviewStatus.FINALIZED:
            raise ValueError("only FINALIZED exit review version may become STALE")
        if self.currentness is ExitReviewCurrentness.STALE:
            raise ValueError("exit review version is already STALE")
        if self.finalized_at is not None and stale_at < self.finalized_at:
            raise ValueError("stale_at must not precede finalized_at")
        if not stale_reason.strip():
            raise ValueError("stale_reason is required")

        return replace(
            self,
            currentness=ExitReviewCurrentness.STALE,
            stale_at=stale_at,
            stale_reason=stale_reason,
        )
