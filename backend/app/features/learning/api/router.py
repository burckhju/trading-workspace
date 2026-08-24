"""REST endpoints for FT-012 Learning TradeLinks."""

from __future__ import annotations

from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response, status

from app.core.exceptions import ApplicationError
from app.features.learning.api.dependencies import (
    get_execute_as_trade_service,
    get_learning_evidence_query_service,
    get_lesson_query_service,
    get_lesson_review_service,
    get_lesson_service,
    get_lesson_suggestion_service,
    get_review_suggestion_query_service,
    get_trade_link_projection_service,
    get_trade_link_query_service,
    get_trade_link_service,
)
from app.features.learning.api.dtos import (
    ExecuteAsTradeRequest,
    ExecuteAsTradeResponse,
    ExternalObservationEvidenceSourceResponse,
    ExternalObservationJournalEvidenceSourceResponse,
    FT011EvidenceSourceResponse,
    LearningEvidenceResponse,
    LearningEvidenceSourceResponse,
    LessonCreateContractRequest,
    LessonCreateContractResponse,
    LessonEvidenceLinkResponse,
    LessonEvidenceResponse,
    LessonHistoryResponse,
    LessonListItemResponse,
    LessonListPageResponse,
    LessonResponse,
    LessonReviewCreatedVersionResponse,
    LessonReviewNewVersionRequest,
    LessonReviewNewVersionResponse,
    LessonReviewSignalContractResponse,
    LessonReviewSignalOpenRequest,
    LessonReviewSignalResponse,
    LessonReviewTriggerEvidenceResponse,
    LessonStateTransitionRequest,
    LessonStateTransitionResponse,
    LessonSuggestionConfirmRequest,
    LessonSuggestionConfirmResponse,
    LessonSuggestionListResponse,
    LessonSuggestionResponse,
    LessonTagListResponse,
    LessonTagReplaceRequest,
    LessonTagReplaceResponse,
    LessonTagResponse,
    LessonTitleUpdateRequest,
    LessonTitleUpdateResponse,
    LessonVersionCreateRequest,
    LessonVersionCreateResponse,
    LessonVersionHistoryItemResponse,
    TradeJournalEvidenceSourceResponse,
    TradeLinkCreateRequest,
    TradeLinkHistoryEntryResponse,
    TradeLinkReactivationRequest,
    TradeLinkResponse,
    TradeLinkRetractionRequest,
    TradeLinkRevalidateSourceRequest,
    TradeLinkTargetCorrectionRequest,
)
from app.features.learning.api.errors import (
    LearningEvidenceNotFoundError,
    translate_execute_as_trade_error,
    translate_learning_evidence_error,
    translate_lesson_error,
    translate_lesson_page_error,
    translate_lesson_review_error,
    translate_lesson_suggestion_error,
    translate_trade_link_error,
)
from app.features.learning.application.execute_as_trade_service import (
    ExecuteExternalObservationAsTradeService,
)
from app.features.learning.application.learning_evidence_query_service import (
    LearningEvidenceQueryService,
)
from app.features.learning.application.lesson_query_service import (
    LessonProjection,
    LessonQueryService,
)
from app.features.learning.application.lesson_review_service import LessonReviewService
from app.features.learning.application.lesson_service import (
    LessonEvidenceInput,
    LessonService,
)
from app.features.learning.application.lesson_suggestion_service import LessonSuggestionService
from app.features.learning.application.review_suggestion_query_service import (
    ReviewSuggestionQueryService,
)
from app.features.learning.application.trade_link_projection_service import (
    TradeLinkProjection,
    TradeLinkProjectionService,
)
from app.features.learning.application.trade_link_query_service import TradeLinkQueryService
from app.features.learning.application.trade_link_service import (
    ExternalObservationTradeLinkService,
)
from app.features.learning.domain import (
    ExternalObservationEvidence,
    FT011Evidence,
    LessonReviewSignal,
    LessonSuggestion,
    TradeJournalVersionEvidence,
)
from app.features.learning.persistence.repositories import LearningEvidenceProjection

router = APIRouter(prefix="/api/v1/learning", tags=["learning"])

WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")
LOCAL_ACTOR_ID = UUID("00000000-0000-4000-8000-000000000002")


def _actor(value: UUID | None) -> UUID:
    return value or LOCAL_ACTOR_ID


def _raise(error: Exception) -> NoReturn:
    raise translate_trade_link_error(error) from error


def _response(value: TradeLinkProjection) -> TradeLinkResponse:
    return TradeLinkResponse(
        trade_link_id=value.link.id,
        external_observation_id=value.link.external_observation_id,
        current_version_id=value.version.id,
        version=value.version.version,
        external_observation_version_id=value.version.external_observation_version_id,
        trade_id=value.version.trade_id,
        status=value.version.status,
        change_reason=value.version.change_reason,
        change_note=value.version.change_note,
        created_at=value.version.created_at,
        created_by=value.version.created_by,
        supersedes_version_id=value.version.supersedes_version_id,
        source_state=value.source_state,
        current_source_compatibility=value.current_source_compatibility,
    )


async def _projection_or_error(
    projection_service: TradeLinkProjectionService,
    *,
    trade_link_id: UUID,
) -> TradeLinkResponse:
    projection = await projection_service.get(
        workspace_id=WORKSPACE_ID,
        trade_link_id=trade_link_id,
    )
    if projection is None:
        from app.features.learning.application.trade_link_service import (
            TradeLinkErrorCode,
            TradeLinkServiceError,
        )

        raise TradeLinkServiceError(
            TradeLinkErrorCode.TRADE_LINK_NOT_FOUND,
            "trade link not found",
        )
    return _response(projection)


@router.post(
    "/external-observations/{observation_id}/trade-links",
    response_model=TradeLinkResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_trade_link(
    observation_id: UUID,
    request: TradeLinkCreateRequest,
    service: Annotated[
        ExternalObservationTradeLinkService,
        Depends(get_trade_link_service),
    ],
    projection: Annotated[
        TradeLinkProjectionService,
        Depends(get_trade_link_projection_service),
    ],
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-ID")] = None,
) -> TradeLinkResponse:
    try:
        result = await service.create(
            workspace_id=WORKSPACE_ID,
            external_observation_id=observation_id,
            trade_id=request.trade_id,
            actor_id=_actor(actor_id),
        )
        return await _projection_or_error(
            projection,
            trade_link_id=result.external_observation_trade_link_id,
        )
    except Exception as error:
        _raise(error)


@router.post(
    "/trade-links/{trade_link_id}/correct-target",
    response_model=TradeLinkResponse,
    status_code=status.HTTP_201_CREATED,
)
async def correct_trade_link_target(
    trade_link_id: UUID,
    request: TradeLinkTargetCorrectionRequest,
    service: Annotated[
        ExternalObservationTradeLinkService,
        Depends(get_trade_link_service),
    ],
    projection: Annotated[
        TradeLinkProjectionService,
        Depends(get_trade_link_projection_service),
    ],
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-ID")] = None,
) -> TradeLinkResponse:
    try:
        await service.correct_target(
            workspace_id=WORKSPACE_ID,
            trade_link_id=trade_link_id,
            trade_id=request.trade_id,
            actor_id=_actor(actor_id),
            change_note=request.change_note,
        )
        return await _projection_or_error(
            projection,
            trade_link_id=trade_link_id,
        )
    except Exception as error:
        _raise(error)


@router.post(
    "/trade-links/{trade_link_id}/retract",
    response_model=TradeLinkResponse,
    status_code=status.HTTP_201_CREATED,
)
async def retract_trade_link(
    trade_link_id: UUID,
    request: TradeLinkRetractionRequest,
    service: Annotated[
        ExternalObservationTradeLinkService,
        Depends(get_trade_link_service),
    ],
    projection: Annotated[
        TradeLinkProjectionService,
        Depends(get_trade_link_projection_service),
    ],
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-ID")] = None,
) -> TradeLinkResponse:
    try:
        await service.retract(
            workspace_id=WORKSPACE_ID,
            trade_link_id=trade_link_id,
            actor_id=_actor(actor_id),
            change_note=request.change_note,
        )
        return await _projection_or_error(
            projection,
            trade_link_id=trade_link_id,
        )
    except Exception as error:
        _raise(error)


@router.post(
    "/trade-links/{trade_link_id}/reactivate",
    response_model=TradeLinkResponse,
    status_code=status.HTTP_201_CREATED,
)
async def reactivate_trade_link(
    trade_link_id: UUID,
    request: TradeLinkReactivationRequest,
    service: Annotated[
        ExternalObservationTradeLinkService,
        Depends(get_trade_link_service),
    ],
    projection: Annotated[
        TradeLinkProjectionService,
        Depends(get_trade_link_projection_service),
    ],
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-ID")] = None,
) -> TradeLinkResponse:
    try:
        await service.reactivate(
            workspace_id=WORKSPACE_ID,
            trade_link_id=trade_link_id,
            actor_id=_actor(actor_id),
            trade_id=request.trade_id,
            change_note=request.change_note,
        )
        return await _projection_or_error(
            projection,
            trade_link_id=trade_link_id,
        )
    except Exception as error:
        _raise(error)


@router.post(
    "/trade-links/{trade_link_id}/revalidate-source",
    response_model=TradeLinkResponse,
    status_code=status.HTTP_201_CREATED,
)
async def revalidate_trade_link_source(
    trade_link_id: UUID,
    request: TradeLinkRevalidateSourceRequest,
    service: Annotated[
        ExternalObservationTradeLinkService,
        Depends(get_trade_link_service),
    ],
    projection: Annotated[
        TradeLinkProjectionService,
        Depends(get_trade_link_projection_service),
    ],
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-ID")] = None,
) -> TradeLinkResponse:
    try:
        await service.revalidate_source(
            workspace_id=WORKSPACE_ID,
            trade_link_id=trade_link_id,
            actor_id=_actor(actor_id),
            change_note=request.change_note,
        )
        return await _projection_or_error(
            projection,
            trade_link_id=trade_link_id,
        )
    except Exception as error:
        _raise(error)


@router.get(
    "/trade-links/{trade_link_id}",
    response_model=TradeLinkResponse,
)
async def get_trade_link(
    trade_link_id: UUID,
    query: Annotated[
        TradeLinkQueryService,
        Depends(get_trade_link_query_service),
    ],
) -> TradeLinkResponse:
    try:
        projection = await query.get(
            workspace_id=WORKSPACE_ID,
            trade_link_id=trade_link_id,
        )
        if projection is None:
            from app.features.learning.application.trade_link_service import (
                TradeLinkErrorCode,
                TradeLinkServiceError,
            )

            raise TradeLinkServiceError(
                TradeLinkErrorCode.TRADE_LINK_NOT_FOUND,
                "trade link not found",
            )
        return _response(projection)
    except Exception as error:
        _raise(error)


@router.get(
    "/external-observations/{observation_id}/trade-links",
    response_model=list[TradeLinkResponse],
)
async def list_trade_links_for_observation(
    observation_id: UUID,
    query: Annotated[
        TradeLinkQueryService,
        Depends(get_trade_link_query_service),
    ],
) -> list[TradeLinkResponse]:
    try:
        values = await query.list_for_observation(
            workspace_id=WORKSPACE_ID,
            observation_id=observation_id,
        )
        return [_response(value) for value in values]
    except Exception as error:
        _raise(error)


@router.get(
    "/trade-links/{trade_link_id}/history",
    response_model=list[TradeLinkHistoryEntryResponse],
)
async def get_trade_link_history(
    trade_link_id: UUID,
    query: Annotated[
        TradeLinkQueryService,
        Depends(get_trade_link_query_service),
    ],
) -> list[TradeLinkHistoryEntryResponse]:
    try:
        entries = await query.history(
            workspace_id=WORKSPACE_ID,
            trade_link_id=trade_link_id,
        )
        if entries is None:
            from app.features.learning.application.trade_link_service import (
                TradeLinkErrorCode,
                TradeLinkServiceError,
            )

            raise TradeLinkServiceError(
                TradeLinkErrorCode.TRADE_LINK_NOT_FOUND,
                "trade link not found",
            )

        return [
            TradeLinkHistoryEntryResponse(
                current_version_id=entry.version.id,
                version=entry.version.version,
                external_observation_version_id=(entry.version.external_observation_version_id),
                trade_id=entry.version.trade_id,
                status=entry.version.status,
                change_reason=entry.version.change_reason,
                change_note=entry.version.change_note,
                created_at=entry.version.created_at,
                created_by=entry.version.created_by,
                supersedes_version_id=entry.version.supersedes_version_id,
                source_state=entry.source_state,
                current_source_compatibility=(entry.current_source_compatibility),
            )
            for entry in entries
        ]
    except Exception as error:
        _raise(error)


@router.post(
    "/external-observations/{observation_id}/execute-as-trade",
    response_model=ExecuteAsTradeResponse,
)
async def execute_external_observation_as_trade(
    observation_id: UUID,
    request: ExecuteAsTradeRequest,
    response: Response,
    service: Annotated[
        ExecuteExternalObservationAsTradeService,
        Depends(get_execute_as_trade_service),
    ],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-ID")] = None,
) -> ExecuteAsTradeResponse:
    try:
        result = await service.execute(
            workspace_id=WORKSPACE_ID,
            observation_id=observation_id,
            quantity=request.quantity,
            price_per_unit=request.price_per_unit,
            executed_at=request.executed_at,
            actor_id=_actor(actor_id),
            idempotency_key=idempotency_key,
        )
    except Exception as error:
        raise translate_execute_as_trade_error(error) from error

    response.status_code = status.HTTP_200_OK if result.replayed else status.HTTP_201_CREATED
    return ExecuteAsTradeResponse(
        trade_id=result.trade_id,
        trade_link_id=result.trade_link_id,
        replayed=result.replayed,
    )


def _learning_evidence_response(
    projection: LearningEvidenceProjection,
) -> LearningEvidenceResponse:
    evidence = projection.evidence
    source = projection.source

    source_response: LearningEvidenceSourceResponse

    if isinstance(source, FT011Evidence):
        source_response = FT011EvidenceSourceResponse(
            type="FT011",
            trade_id=source.trade_id,
            post_trade_observation_id=source.post_trade_observation_id,
            exit_review_id=source.exit_review_id,
            exit_review_version_id=source.exit_review_version_id,
        )

    elif isinstance(source, TradeJournalVersionEvidence):
        source_response = TradeJournalEvidenceSourceResponse(
            type="TRADE_JOURNAL_VERSION",
            trade_journal_version_id=source.trade_journal_version_id,
        )

    elif isinstance(source, ExternalObservationEvidence):
        source_response = ExternalObservationEvidenceSourceResponse(
            type="EXTERNAL_OBSERVATION",
            external_observation_version_id=(source.external_observation_version_id),
        )

    else:
        source_response = ExternalObservationJournalEvidenceSourceResponse(
            type="EXTERNAL_OBSERVATION_JOURNAL_VERSION",
            external_observation_journal_version_id=(
                source.external_observation_journal_version_id
            ),
        )

    return LearningEvidenceResponse(
        evidence_id=evidence.id,
        workspace_id=evidence.workspace_id,
        provenance_class=evidence.evidence_type,
        source_type=evidence.evidence_type,
        source=source_response,
        created_at=evidence.created_at,
    )


@router.get(
    "/learning-evidence/{evidence_id}",
    response_model=LearningEvidenceResponse,
)
async def get_learning_evidence(
    evidence_id: UUID,
    query: Annotated[
        LearningEvidenceQueryService,
        Depends(get_learning_evidence_query_service),
    ],
) -> LearningEvidenceResponse:
    try:
        projection = await query.get(
            workspace_id=WORKSPACE_ID,
            evidence_id=evidence_id,
        )
        if projection is None:
            raise LearningEvidenceNotFoundError("learning evidence not found")
        return _learning_evidence_response(projection)
    except Exception as error:
        raise translate_learning_evidence_error(error) from error


@router.get(
    "/learning-evidence",
    response_model=list[LearningEvidenceResponse],
)
async def list_learning_evidence(
    query: Annotated[
        LearningEvidenceQueryService,
        Depends(get_learning_evidence_query_service),
    ],
) -> list[LearningEvidenceResponse]:
    projections = await query.list(
        workspace_id=WORKSPACE_ID,
    )
    return [_learning_evidence_response(projection) for projection in projections]


def _lesson_read_response(
    projection: LessonProjection,
) -> LessonResponse:
    return LessonResponse(
        lesson_id=projection.lesson.id,
        current_version_id=projection.lesson.current_version_id,
        current_state=projection.lesson.current_state,
        version=projection.version.version,
        title=projection.lesson.title,
        main_category=projection.version.main_category,
        content=projection.version.content,
        evidence=[
            LessonEvidenceLinkResponse(
                id=link.id,
                learning_evidence_id=link.learning_evidence_id,
                relation=link.relation,
            )
            for link in projection.evidence_links
        ],
        created_at=projection.lesson.created_at,
        created_by=projection.lesson.created_by,
    )


@router.get(
    "/lessons/{lesson_id}",
    response_model=LessonResponse,
)
async def get_lesson(
    lesson_id: UUID,
    query: Annotated[
        LessonQueryService,
        Depends(get_lesson_query_service),
    ],
) -> LessonResponse:
    projection = await query.get(
        workspace_id=WORKSPACE_ID,
        lesson_id=lesson_id,
    )
    if projection is None:
        raise ApplicationError(
            code="LESSON_NOT_FOUND",
            message="lesson not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return _lesson_read_response(projection)


@router.get(
    "/lessons",
    response_model=LessonListPageResponse,
)
async def list_lessons(
    query: Annotated[
        LessonQueryService,
        Depends(get_lesson_query_service),
    ],
    limit: Annotated[int, Query()] = 50,
    cursor: Annotated[str | None, Query()] = None,
) -> LessonListPageResponse:
    try:
        page = await query.page(
            workspace_id=WORKSPACE_ID,
            limit=limit,
            cursor=cursor,
        )
    except Exception as error:
        raise translate_lesson_page_error(error) from error

    return LessonListPageResponse(
        items=[
            LessonListItemResponse(
                lesson_id=item.lesson.id,
                current_version_id=item.lesson.current_version_id,
                version=item.version.version,
                current_state=item.lesson.current_state,
                title=item.lesson.title,
                main_category=item.version.main_category,
                content=item.version.content,
                created_at=item.lesson.created_at,
                created_by=item.lesson.created_by,
            )
            for item in page.items
        ],
        next_cursor=page.next_cursor,
    )


@router.get(
    "/lessons/{lesson_id}/history",
    response_model=LessonHistoryResponse,
)
async def get_lesson_history(
    lesson_id: UUID,
    query: Annotated[
        LessonQueryService,
        Depends(get_lesson_query_service),
    ],
) -> LessonHistoryResponse:
    history = await query.history(
        workspace_id=WORKSPACE_ID,
        lesson_id=lesson_id,
    )
    if history is None:
        raise ApplicationError(
            code="LESSON_NOT_FOUND",
            message="lesson not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    return LessonHistoryResponse(
        lesson_id=lesson_id,
        versions=[
            LessonVersionHistoryItemResponse(
                version_id=item.version.id,
                version=item.version.version,
                main_category=item.version.main_category,
                content=item.version.content,
                created_at=item.version.created_at,
                created_by=item.version.created_by,
                supersedes_version_id=item.version.supersedes_version_id,
                evidence=[
                    LessonEvidenceLinkResponse(
                        id=link.id,
                        learning_evidence_id=link.learning_evidence_id,
                        relation=link.relation,
                    )
                    for link in item.evidence_links
                ],
            )
            for item in history
        ],
    )


@router.get(
    "/lessons/{lesson_id}/evidence",
    response_model=LessonEvidenceResponse,
)
async def get_lesson_evidence(
    lesson_id: UUID,
    query: Annotated[
        LessonQueryService,
        Depends(get_lesson_query_service),
    ],
) -> LessonEvidenceResponse:
    projection = await query.get(
        workspace_id=WORKSPACE_ID,
        lesson_id=lesson_id,
    )
    if projection is None:
        raise ApplicationError(
            code="LESSON_NOT_FOUND",
            message="lesson not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    return LessonEvidenceResponse(
        lesson_id=lesson_id,
        current_version_id=projection.version.id,
        evidence=[
            LessonEvidenceLinkResponse(
                id=link.id,
                learning_evidence_id=link.learning_evidence_id,
                relation=link.relation,
            )
            for link in projection.evidence_links
        ],
    )


@router.patch(
    "/lessons/{lesson_id}/title",
    response_model=LessonTitleUpdateResponse,
)
async def update_lesson_title(
    lesson_id: UUID,
    request: LessonTitleUpdateRequest,
    service: Annotated[
        LessonService,
        Depends(get_lesson_service),
    ],
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-ID")] = None,
) -> LessonTitleUpdateResponse:
    try:
        lesson = await service.update_title(
            workspace_id=WORKSPACE_ID,
            lesson_id=lesson_id,
            title=request.title,
            actor_id=_actor(actor_id),
        )
    except Exception as error:
        raise translate_lesson_error(error) from error

    return LessonTitleUpdateResponse(
        lesson_id=lesson.id,
        title=lesson.title,
        current_version_id=lesson.current_version_id,
        current_state=lesson.current_state,
        updated_at=lesson.updated_at,
        updated_by=lesson.updated_by,
    )


@router.post(
    "/lessons/{lesson_id}/versions",
    response_model=LessonVersionCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_lesson_version(
    lesson_id: UUID,
    request: LessonVersionCreateRequest,
    service: Annotated[
        LessonService,
        Depends(get_lesson_service),
    ],
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-ID")] = None,
) -> LessonVersionCreateResponse:
    try:
        result = await service.create_new_version(
            workspace_id=WORKSPACE_ID,
            lesson_id=lesson_id,
            main_category=request.main_category,
            content=request.content,
            evidence=tuple(
                LessonEvidenceInput(
                    learning_evidence_id=item.learning_evidence_id,
                    relation=item.relation,
                )
                for item in request.evidence_links
            ),
            expected_current_version_id=request.expected_current_version_id,
            expected_current_state=request.expected_current_state,
            actor_id=_actor(actor_id),
        )
    except Exception as error:
        raise translate_lesson_error(error) from error

    return LessonVersionCreateResponse(
        lesson_id=result.lesson.id,
        current_version_id=result.version.id,
        version=result.version.version,
        current_state=result.lesson.current_state,
        main_category=result.version.main_category,
        content=result.version.content,
        supersedes_version_id=result.version.supersedes_version_id,
        evidence=[
            LessonEvidenceLinkResponse(
                id=link.id,
                learning_evidence_id=link.learning_evidence_id,
                relation=link.relation,
            )
            for link in result.evidence_links
        ],
    )


@router.post(
    "/lessons/{lesson_id}/state-transitions",
    response_model=LessonStateTransitionResponse,
    status_code=status.HTTP_200_OK,
)
async def transition_lesson_state(
    lesson_id: UUID,
    request: LessonStateTransitionRequest,
    service: Annotated[
        LessonService,
        Depends(get_lesson_service),
    ],
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-ID")] = None,
) -> LessonStateTransitionResponse:
    try:
        result = await service.transition_state(
            workspace_id=WORKSPACE_ID,
            lesson_id=lesson_id,
            expected_state=request.expected_state,
            new_state=request.new_state,
            reason=request.reason,
            related_lesson_version_id=request.related_lesson_version_id,
            actor_id=_actor(actor_id),
        )
    except Exception as error:
        raise translate_lesson_error(error) from error

    return LessonStateTransitionResponse(
        lesson_id=result.lesson.id,
        from_state=result.transition.from_state,
        to_state=result.transition.to_state,
        reason=result.transition.reason,
        related_lesson_version_id=result.transition.related_lesson_version_id,
        occurred_at=result.transition.occurred_at,
        occurred_by=result.transition.occurred_by,
    )


@router.put(
    "/lessons/{lesson_id}/tags",
    response_model=LessonTagReplaceResponse,
)
async def replace_lesson_tags(
    lesson_id: UUID,
    request: LessonTagReplaceRequest,
    service: Annotated[
        LessonService,
        Depends(get_lesson_service),
    ],
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-ID")] = None,
) -> LessonTagReplaceResponse:
    try:
        tags = await service.replace_tags(
            workspace_id=WORKSPACE_ID,
            lesson_id=lesson_id,
            tags=tuple(request.tags),
            actor_id=_actor(actor_id),
        )
    except Exception as error:
        raise translate_lesson_error(error) from error

    return LessonTagReplaceResponse(
        lesson_id=lesson_id,
        tags=[
            LessonTagResponse(
                id=tag.id,
                name=tag.name,
                normalized_name=tag.normalized_name,
            )
            for tag in tags
        ],
    )


def _review_signal_response(
    signal: LessonReviewSignal,
) -> LessonReviewSignalResponse:
    return LessonReviewSignalResponse(
        signal_id=signal.id,
        lesson_id=signal.lesson_id,
        lesson_version_id=signal.lesson_version_id,
        status=signal.status.value,
        raised_at=signal.raised_at,
        resolution=(signal.resolution.value if signal.resolution is not None else None),
        resolved_at=signal.resolved_at,
        resolved_by=signal.resolved_by,
        resulting_lesson_version_id=signal.resulting_lesson_version_id,
    )


def _review_signal_contract_response(
    signal: LessonReviewSignal,
    trigger_evidence_link_ids: tuple[UUID, ...],
) -> LessonReviewSignalContractResponse:
    return LessonReviewSignalContractResponse(
        signal_id=signal.id,
        lesson_id=signal.lesson_id,
        status=signal.status.value,
        trigger_evidence=[
            LessonReviewTriggerEvidenceResponse(
                lesson_evidence_link_id=link_id,
            )
            for link_id in trigger_evidence_link_ids
        ],
        opened_at=signal.raised_at,
        opened_by=signal.opened_by,
        resolution=(signal.resolution.value if signal.resolution is not None else None),
        resolved_at=signal.resolved_at,
        resolved_by=signal.resolved_by,
        resulting_lesson_version_id=signal.resulting_lesson_version_id,
    )


def _suggestion_response(
    suggestion: LessonSuggestion,
) -> LessonSuggestionResponse:
    return LessonSuggestionResponse(
        suggestion_id=suggestion.id,
        status=suggestion.status.value,
        proposed_title=suggestion.proposed_title,
        proposed_main_category=suggestion.proposed_main_category,
        proposed_content=suggestion.proposed_content,
        created_at=suggestion.created_at,
        created_by=suggestion.created_by,
        decided_at=suggestion.decided_at,
        decided_by=suggestion.decided_by,
        resulting_lesson_id=suggestion.resulting_lesson_id,
    )


@router.post(
    "/lessons/{lesson_id}/review-signals",
    response_model=LessonReviewSignalContractResponse,
    status_code=status.HTTP_201_CREATED,
)
async def open_lesson_review_signal(
    lesson_id: UUID,
    request: LessonReviewSignalOpenRequest,
    service: Annotated[
        LessonReviewService,
        Depends(get_lesson_review_service),
    ],
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-ID")] = None,
) -> LessonReviewSignalContractResponse:
    try:
        result = await service.open_signal(
            workspace_id=WORKSPACE_ID,
            lesson_id=lesson_id,
            contradiction_link_ids=tuple(request.contradiction_link_ids),
            actor_id=_actor(actor_id),
        )
    except Exception as error:
        raise translate_lesson_review_error(error) from error

    return _review_signal_contract_response(
        result.signal,
        tuple(request.contradiction_link_ids),
    )


@router.post(
    "/lesson-review-signals/{signal_id}/resolve-unchanged",
    response_model=LessonReviewSignalResponse,
)
async def resolve_lesson_review_unchanged(
    signal_id: UUID,
    lesson_id: UUID,
    service: Annotated[
        LessonReviewService,
        Depends(get_lesson_review_service),
    ],
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-ID")] = None,
) -> LessonReviewSignalResponse:
    try:
        signal = await service.resolve_unchanged(
            workspace_id=WORKSPACE_ID,
            lesson_id=lesson_id,
            signal_id=signal_id,
            actor_id=_actor(actor_id),
        )
    except Exception as error:
        raise translate_lesson_review_error(error) from error

    return _review_signal_response(signal)


@router.post(
    "/lesson-review-signals/{signal_id}/resolve-new-version",
    response_model=LessonReviewNewVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def resolve_lesson_review_new_version(
    signal_id: UUID,
    lesson_id: UUID,
    request: LessonReviewNewVersionRequest,
    service: Annotated[
        LessonReviewService,
        Depends(get_lesson_review_service),
    ],
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-ID")] = None,
) -> LessonReviewNewVersionResponse:
    try:
        result = await service.resolve_with_new_version(
            workspace_id=WORKSPACE_ID,
            lesson_id=lesson_id,
            signal_id=signal_id,
            main_category=request.main_category,
            content=request.content,
            evidence=tuple(
                LessonEvidenceInput(
                    learning_evidence_id=item.learning_evidence_id,
                    relation=item.relation,
                )
                for item in request.evidence_links
            ),
            actor_id=_actor(actor_id),
        )
    except Exception as error:
        raise translate_lesson_review_error(error) from error

    return LessonReviewNewVersionResponse(
        signal=_review_signal_response(result.signal),
        lesson_version=LessonReviewCreatedVersionResponse(
            version_id=result.version.id,
            lesson_id=result.version.lesson_id,
            version=result.version.version,
            main_category=result.version.main_category,
            content=result.version.content,
            supersedes_version_id=result.version.supersedes_version_id,
            evidence=[
                LessonEvidenceLinkResponse(
                    id=link.id,
                    learning_evidence_id=link.learning_evidence_id,
                    relation=link.relation,
                )
                for link in result.evidence_links
            ],
        ),
    )


@router.post(
    "/lesson-review-signals/{signal_id}/resolve-retired",
    response_model=LessonReviewSignalResponse,
)
async def resolve_lesson_review_retired(
    signal_id: UUID,
    lesson_id: UUID,
    service: Annotated[
        LessonReviewService,
        Depends(get_lesson_review_service),
    ],
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-ID")] = None,
) -> LessonReviewSignalResponse:
    try:
        signal = await service.resolve_retired(
            workspace_id=WORKSPACE_ID,
            lesson_id=lesson_id,
            signal_id=signal_id,
            actor_id=_actor(actor_id),
        )
    except Exception as error:
        raise translate_lesson_review_error(error) from error

    return _review_signal_response(signal)


@router.post(
    "/lesson-suggestions/{suggestion_id}/reject",
    response_model=LessonSuggestionResponse,
)
async def reject_lesson_suggestion(
    suggestion_id: UUID,
    service: Annotated[
        LessonSuggestionService,
        Depends(get_lesson_suggestion_service),
    ],
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-ID")] = None,
) -> LessonSuggestionResponse:
    try:
        suggestion = await service.reject(
            workspace_id=WORKSPACE_ID,
            suggestion_id=suggestion_id,
            actor_id=_actor(actor_id),
        )
    except Exception as error:
        raise translate_lesson_suggestion_error(error) from error

    return _suggestion_response(suggestion)


@router.post(
    "/lesson-suggestions/{suggestion_id}/confirm",
    response_model=LessonSuggestionConfirmResponse,
    status_code=status.HTTP_201_CREATED,
)
async def confirm_lesson_suggestion(
    suggestion_id: UUID,
    request: LessonSuggestionConfirmRequest,
    service: Annotated[
        LessonSuggestionService,
        Depends(get_lesson_suggestion_service),
    ],
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-ID")] = None,
) -> LessonSuggestionConfirmResponse:
    try:
        result = await service.confirm(
            workspace_id=WORKSPACE_ID,
            suggestion_id=suggestion_id,
            evidence=tuple(
                LessonEvidenceInput(
                    learning_evidence_id=item.learning_evidence_id,
                    relation=item.relation,
                )
                for item in request.evidence_links
            ),
            actor_id=_actor(actor_id),
            title=request.title,
            main_category=request.main_category,
            content=request.content,
        )
    except Exception as error:
        raise translate_lesson_suggestion_error(error) from error

    return LessonSuggestionConfirmResponse(
        suggestion=_suggestion_response(result.suggestion),
        lesson_id=result.lesson.id,
        current_version_id=result.version.id,
        version=result.version.version,
        current_state=result.lesson.current_state,
        title=result.lesson.title,
        main_category=result.version.main_category,
        content=result.version.content,
        evidence=[
            LessonEvidenceLinkResponse(
                id=link.id,
                learning_evidence_id=link.learning_evidence_id,
                relation=link.relation,
            )
            for link in result.evidence_links
        ],
    )


@router.get(
    "/lessons/{lesson_id}/review-signals",
    response_model=list[LessonReviewSignalContractResponse],
)
async def list_lesson_review_signals(
    lesson_id: UUID,
    query: Annotated[
        ReviewSuggestionQueryService,
        Depends(get_review_suggestion_query_service),
    ],
) -> list[LessonReviewSignalContractResponse]:
    projections = await query.list_review_signal_projections(
        workspace_id=WORKSPACE_ID,
        lesson_id=lesson_id,
    )
    return [
        _review_signal_contract_response(
            projection.signal,
            projection.trigger_evidence_link_ids,
        )
        for projection in projections
    ]


@router.get(
    "/lesson-suggestions/{suggestion_id}",
    response_model=LessonSuggestionResponse,
)
async def get_lesson_suggestion(
    suggestion_id: UUID,
    query: Annotated[
        ReviewSuggestionQueryService,
        Depends(get_review_suggestion_query_service),
    ],
) -> LessonSuggestionResponse:
    suggestion = await query.get_suggestion(
        workspace_id=WORKSPACE_ID,
        suggestion_id=suggestion_id,
    )
    if suggestion is None:
        raise ApplicationError(
            code="LESSON_SUGGESTION_NOT_FOUND",
            message="lesson suggestion not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return _suggestion_response(suggestion)


@router.get(
    "/lesson-suggestions",
    response_model=LessonSuggestionListResponse,
)
async def list_lesson_suggestions(
    query: Annotated[
        ReviewSuggestionQueryService,
        Depends(get_review_suggestion_query_service),
    ],
) -> LessonSuggestionListResponse:
    suggestions = await query.list_suggestions(
        workspace_id=WORKSPACE_ID,
    )
    return LessonSuggestionListResponse(items=[_suggestion_response(item) for item in suggestions])


@router.get(
    "/lesson-tags",
    response_model=LessonTagListResponse,
)
async def list_lesson_tags(
    query: Annotated[
        ReviewSuggestionQueryService,
        Depends(get_review_suggestion_query_service),
    ],
) -> LessonTagListResponse:
    tags = await query.list_tags(workspace_id=WORKSPACE_ID)

    return LessonTagListResponse(
        items=[
            LessonTagResponse(
                id=tag.id,
                name=tag.name,
                normalized_name=tag.normalized_name,
            )
            for tag in tags
        ]
    )


@router.post(
    "/lessons",
    response_model=LessonCreateContractResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_lesson(
    request: LessonCreateContractRequest,
    service: Annotated[
        LessonService,
        Depends(get_lesson_service),
    ],
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-ID")] = None,
) -> LessonCreateContractResponse:
    actor = _actor(actor_id)

    try:
        result = await service.create(
            workspace_id=WORKSPACE_ID,
            title=request.title,
            main_category=request.main_category,
            content=request.content,
            evidence=tuple(
                LessonEvidenceInput(
                    learning_evidence_id=item.learning_evidence_id,
                    relation=item.relation,
                )
                for item in request.evidence_links
            ),
            actor_id=actor,
        )

        tags = await service.replace_tags(
            workspace_id=WORKSPACE_ID,
            lesson_id=result.lesson.id,
            tags=tuple(request.tags),
            actor_id=actor,
        )
    except Exception as error:
        raise translate_lesson_error(error) from error

    return LessonCreateContractResponse(
        lesson_id=result.lesson.id,
        current_version_id=result.version.id,
        version=result.version.version,
        current_state=result.lesson.current_state,
        title=result.lesson.title,
        main_category=result.version.main_category,
        content=result.version.content,
        tags=[
            LessonTagResponse(
                id=tag.id,
                name=tag.name,
                normalized_name=tag.normalized_name,
            )
            for tag in tags
        ],
        evidence=[
            LessonEvidenceLinkResponse(
                id=link.id,
                learning_evidence_id=link.learning_evidence_id,
                relation=link.relation,
            )
            for link in result.evidence_links
        ],
        created_at=result.lesson.created_at,
        created_by=result.lesson.created_by,
    )
