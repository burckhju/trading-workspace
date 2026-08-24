"""REST DTOs for FT-012 Learning TradeLinks."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.features.learning.application.trade_link_projection_service import (
    TradeLinkCurrentSourceCompatibility,
    TradeLinkSourceState,
)
from app.features.learning.domain import (
    LearningEvidenceType,
    LessonEvidenceRelation,
    LessonState,
    TradeLinkChangeReason,
    TradeLinkStatus,
)


class TradeLinkCreateRequest(BaseModel):
    trade_id: UUID


class TradeLinkTargetCorrectionRequest(BaseModel):
    trade_id: UUID
    change_note: str | None = None


class TradeLinkRetractionRequest(BaseModel):
    change_note: str | None = None


class TradeLinkReactivationRequest(BaseModel):
    trade_id: UUID | None = None
    change_note: str | None = None


class TradeLinkRevalidateSourceRequest(BaseModel):
    change_note: str | None = None


class TradeLinkResponse(BaseModel):
    trade_link_id: UUID
    external_observation_id: UUID
    current_version_id: UUID
    version: int
    external_observation_version_id: UUID
    trade_id: UUID
    status: TradeLinkStatus
    change_reason: TradeLinkChangeReason
    change_note: str | None
    created_at: datetime
    created_by: UUID
    supersedes_version_id: UUID | None
    source_state: TradeLinkSourceState
    current_source_compatibility: TradeLinkCurrentSourceCompatibility


class TradeLinkHistoryEntryResponse(BaseModel):
    current_version_id: UUID
    version: int
    external_observation_version_id: UUID
    trade_id: UUID
    status: TradeLinkStatus
    change_reason: TradeLinkChangeReason
    change_note: str | None
    created_at: datetime
    created_by: UUID
    supersedes_version_id: UUID | None
    source_state: TradeLinkSourceState
    current_source_compatibility: TradeLinkCurrentSourceCompatibility


class ExecuteAsTradeRequest(BaseModel):
    quantity: int
    price_per_unit: Decimal
    executed_at: datetime


class ExecuteAsTradeResponse(BaseModel):
    trade_id: UUID
    trade_link_id: UUID
    replayed: bool


class FT011EvidenceSourceResponse(BaseModel):
    type: Literal["FT011"]
    trade_id: UUID
    post_trade_observation_id: UUID
    exit_review_id: UUID
    exit_review_version_id: UUID


class TradeJournalEvidenceSourceResponse(BaseModel):
    type: Literal["TRADE_JOURNAL_VERSION"]
    trade_journal_version_id: UUID


class ExternalObservationEvidenceSourceResponse(BaseModel):
    type: Literal["EXTERNAL_OBSERVATION"]
    external_observation_version_id: UUID


class ExternalObservationJournalEvidenceSourceResponse(BaseModel):
    type: Literal["EXTERNAL_OBSERVATION_JOURNAL_VERSION"]
    external_observation_journal_version_id: UUID


LearningEvidenceSourceResponse = (
    FT011EvidenceSourceResponse
    | TradeJournalEvidenceSourceResponse
    | ExternalObservationEvidenceSourceResponse
    | ExternalObservationJournalEvidenceSourceResponse
)


class LearningEvidenceResponse(BaseModel):
    evidence_id: UUID
    workspace_id: UUID
    provenance_class: LearningEvidenceType
    source_type: LearningEvidenceType
    source: LearningEvidenceSourceResponse
    created_at: datetime


class LessonEvidenceInputRequest(BaseModel):
    learning_evidence_id: UUID
    relation: LessonEvidenceRelation


class LessonCreateRequest(BaseModel):
    title: str
    main_category: str
    content: str
    evidence: list[LessonEvidenceInputRequest]


class LessonEvidenceLinkResponse(BaseModel):
    id: UUID
    learning_evidence_id: UUID
    relation: LessonEvidenceRelation


class LessonCreateResponse(BaseModel):
    lesson_id: UUID
    current_version_id: UUID
    current_state: LessonState
    version: int
    title: str
    main_category: str
    content: str
    evidence: list[LessonEvidenceLinkResponse]


class LessonResponse(LessonCreateResponse):
    created_at: datetime
    created_by: UUID


class LessonListItemResponse(BaseModel):
    lesson_id: UUID
    current_version_id: UUID
    version: int
    current_state: LessonState
    title: str
    main_category: str
    content: str
    created_at: datetime
    created_by: UUID


class LessonListPageResponse(BaseModel):
    items: list[LessonListItemResponse]
    next_cursor: str | None


class LessonVersionHistoryItemResponse(BaseModel):
    version_id: UUID
    version: int
    main_category: str
    content: str
    created_at: datetime
    created_by: UUID
    supersedes_version_id: UUID | None
    evidence: list[LessonEvidenceLinkResponse]


class LessonHistoryResponse(BaseModel):
    lesson_id: UUID
    versions: list[LessonVersionHistoryItemResponse]


class LessonEvidenceResponse(BaseModel):
    lesson_id: UUID
    current_version_id: UUID
    evidence: list[LessonEvidenceLinkResponse]


class LessonTitleUpdateRequest(BaseModel):
    title: str


class LessonTitleUpdateResponse(BaseModel):
    lesson_id: UUID
    title: str
    current_version_id: UUID
    current_state: LessonState
    updated_at: datetime
    updated_by: UUID


class LessonVersionCreateRequest(BaseModel):
    main_category: str
    content: str
    evidence_links: list[LessonEvidenceInputRequest]
    expected_current_version_id: UUID
    expected_current_state: LessonState


class LessonVersionCreateResponse(BaseModel):
    lesson_id: UUID
    current_version_id: UUID
    version: int
    current_state: LessonState
    main_category: str
    content: str
    supersedes_version_id: UUID
    evidence: list[LessonEvidenceLinkResponse]


class LessonStateTransitionRequest(BaseModel):
    expected_state: LessonState
    new_state: LessonState
    reason: str
    related_lesson_version_id: UUID | None = None


class LessonStateTransitionResponse(BaseModel):
    lesson_id: UUID
    from_state: LessonState
    to_state: LessonState
    reason: str
    related_lesson_version_id: UUID | None
    occurred_at: datetime
    occurred_by: UUID


class LessonTagReplaceRequest(BaseModel):
    tags: list[str]


class LessonTagResponse(BaseModel):
    id: UUID
    name: str
    normalized_name: str


class LessonTagReplaceResponse(BaseModel):
    lesson_id: UUID
    tags: list[LessonTagResponse]


class LessonReviewSignalOpenRequest(BaseModel):
    contradiction_link_ids: list[UUID]


class LessonReviewSignalResponse(BaseModel):
    signal_id: UUID
    lesson_id: UUID
    lesson_version_id: UUID
    status: str
    raised_at: datetime
    resolution: str | None = None
    resolved_at: datetime | None = None
    resolved_by: UUID | None = None
    resulting_lesson_version_id: UUID | None = None


class LessonReviewNewVersionRequest(BaseModel):
    main_category: str
    content: str
    evidence_links: list[LessonEvidenceInputRequest]


class LessonReviewCreatedVersionResponse(BaseModel):
    version_id: UUID
    lesson_id: UUID
    version: int
    main_category: str
    content: str
    supersedes_version_id: UUID | None
    evidence: list[LessonEvidenceLinkResponse]


class LessonReviewNewVersionResponse(BaseModel):
    signal: LessonReviewSignalResponse
    lesson_version: LessonReviewCreatedVersionResponse


class LessonSuggestionConfirmRequest(BaseModel):
    evidence_links: list[LessonEvidenceInputRequest]
    title: str | None = None
    main_category: str | None = None
    content: str | None = None


class LessonSuggestionResponse(BaseModel):
    suggestion_id: UUID
    status: str
    proposed_title: str
    proposed_main_category: str
    proposed_content: str
    created_at: datetime
    created_by: UUID | None
    decided_at: datetime | None = None
    decided_by: UUID | None = None
    resulting_lesson_id: UUID | None = None


class LessonSuggestionConfirmResponse(BaseModel):
    suggestion: LessonSuggestionResponse
    lesson_id: UUID
    current_version_id: UUID
    version: int
    current_state: LessonState
    title: str
    main_category: str
    content: str
    evidence: list[LessonEvidenceLinkResponse]


class LessonReviewSignalListResponse(BaseModel):
    items: list[LessonReviewSignalResponse]


class LessonSuggestionListResponse(BaseModel):
    items: list[LessonSuggestionResponse]


class LessonTagListResponse(BaseModel):
    items: list[LessonTagResponse]


class LessonCreateContractRequest(BaseModel):
    title: str
    main_category: str
    content: str
    evidence_links: list[LessonEvidenceInputRequest]
    tags: list[str]


class LessonCreateContractResponse(BaseModel):
    lesson_id: UUID
    current_version_id: UUID
    version: int
    current_state: LessonState
    title: str
    main_category: str
    content: str
    tags: list[LessonTagResponse]
    evidence: list[LessonEvidenceLinkResponse]
    created_at: datetime
    created_by: UUID


class LessonReviewTriggerEvidenceResponse(BaseModel):
    lesson_evidence_link_id: UUID


class LessonReviewSignalContractResponse(BaseModel):
    signal_id: UUID
    lesson_id: UUID
    status: str
    trigger_evidence: list[LessonReviewTriggerEvidenceResponse]
    opened_at: datetime
    opened_by: UUID
    resolution: str | None = None
    resolved_at: datetime | None = None
    resolved_by: UUID | None = None
    resulting_lesson_version_id: UUID | None = None
