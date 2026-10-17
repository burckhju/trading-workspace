"""REST invocation seam for FT-011 LearningEvidence materialization."""

from dataclasses import asdict
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, status
from pydantic import BaseModel, ConfigDict

from app.core.exceptions import ApplicationError
from app.features.learning.api.materialization_dependencies import (
    get_ft011_evidence_history_service,
    get_ft011_materialization_service,
    get_ft011_materialization_status_service,
)
from app.features.learning.application.ft011_evidence_history_service import (
    Ft011EvidenceHistoryService,
)
from app.features.learning.application.ft011_materialization_service import (
    Ft011MaterializationError,
    MaterializeFt011LearningEvidenceService,
)
from app.features.learning.application.ft011_materialization_status_service import (
    Ft011MaterializationStatusService,
)
from app.features.learning.domain import LessonEvidenceRelation

router = APIRouter(prefix="/api/v1/learning", tags=["learning"])
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")


class MaterializeFt011LearningEvidenceRequest(BaseModel):
    """Explicit source confirmation; omitted body retains the legacy contract."""

    model_config = ConfigDict(extra="forbid")

    expected_exit_review_version_id: UUID


class MaterializeFt011LearningEvidenceResponse(BaseModel):
    learning_evidence_id: UUID
    exit_review_version_id: UUID
    created: bool
    replayed: bool


class Ft011MaterializationStatusResponse(BaseModel):
    ready: bool
    reason: str
    materialized: bool
    learning_evidence_id: UUID | None
    exit_review_version_id: UUID | None


class HistoricalLessonLinkResponse(BaseModel):
    link_id: UUID
    lesson_id: UUID
    lesson_title: str
    lesson_version_id: UUID
    lesson_version: int
    relation: LessonEvidenceRelation
    is_current_version: bool


class Ft011EvidenceHistoryResponse(BaseModel):
    learning_evidence_id: UUID
    evidence_type: str
    materialized_at: datetime
    trade_id: UUID
    post_trade_observation_id: UUID
    exit_review_id: UUID
    exit_review_version_id: UUID
    review_version: int | None
    review_status: str | None
    stored_review_currentness: str | None
    source_currentness: str
    superseded_by_version_id: UUID | None
    checked_at: datetime
    lesson_links: list[HistoricalLessonLinkResponse]


@router.get(
    "/trades/{trade_id}/ft011-evidence/history", response_model=list[Ft011EvidenceHistoryResponse]
)
async def get_ft011_evidence_history(
    trade_id: UUID,
    service: Annotated[Ft011EvidenceHistoryService, Depends(get_ft011_evidence_history_service)],
) -> list[Ft011EvidenceHistoryResponse]:
    items = await service.get(workspace_id=WORKSPACE_ID, trade_id=trade_id)
    return [Ft011EvidenceHistoryResponse.model_validate(asdict(item)) for item in items]


@router.get(
    "/trades/{trade_id}/ft011-evidence/materialization-status",
    response_model=Ft011MaterializationStatusResponse,
)
async def get_ft011_materialization_status(
    trade_id: UUID,
    service: Annotated[
        Ft011MaterializationStatusService,
        Depends(get_ft011_materialization_status_service),
    ],
) -> Ft011MaterializationStatusResponse:
    result = await service.get(
        workspace_id=WORKSPACE_ID,
        trade_id=trade_id,
    )
    return Ft011MaterializationStatusResponse(
        ready=result.ready,
        reason=result.reason,
        materialized=result.materialized,
        learning_evidence_id=result.learning_evidence_id,
        exit_review_version_id=result.exit_review_version_id,
    )


@router.post(
    "/trades/{trade_id}/ft011-evidence/materialize",
    response_model=MaterializeFt011LearningEvidenceResponse,
    status_code=status.HTTP_200_OK,
)
async def materialize_ft011_learning_evidence(
    trade_id: UUID,
    service: Annotated[
        MaterializeFt011LearningEvidenceService,
        Depends(get_ft011_materialization_service),
    ],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    request: MaterializeFt011LearningEvidenceRequest | None = None,
) -> MaterializeFt011LearningEvidenceResponse:
    try:
        if request is None:
            result = await service.execute(
                workspace_id=WORKSPACE_ID,
                trade_id=trade_id,
                idempotency_key=idempotency_key,
            )
        else:
            result = await service.execute(
                workspace_id=WORKSPACE_ID,
                trade_id=trade_id,
                idempotency_key=idempotency_key,
                expected_exit_review_version_id=request.expected_exit_review_version_id,
            )
    except Ft011MaterializationError as error:
        raise ApplicationError(
            code=error.code.value,
            message=str(error),
            status_code=status.HTTP_409_CONFLICT,
        ) from error

    return MaterializeFt011LearningEvidenceResponse(
        learning_evidence_id=result.learning_evidence_id,
        exit_review_version_id=result.exit_review_version_id,
        created=result.created,
        replayed=result.replayed,
    )
