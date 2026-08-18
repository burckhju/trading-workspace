"""REST endpoints for FT-011 Post Trade."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, status

from app.core.exceptions import ApplicationError
from app.features.post_trade.api.dependencies import (
    get_exit_review_service,
    get_ft012_handoff_service,
    get_post_trade_observation_service,
    get_post_trade_query_service,
)
from app.features.post_trade.api.dtos import (
    ActualExitResponse,
    CounterfactualEvidenceResponse,
    ExitExecutionResponse,
    ExitReviewDraftRequest,
    ExitReviewResponse,
    HandoffResponse,
    LevelCrossingResponse,
    ManagementLevelResponse,
    ObservationEvidenceResponse,
    ObservationPointResponse,
    ObservationResponse,
    ObservedExtremeResponse,
    PlanningContextResponse,
    ProductContextResponse,
)
from app.features.post_trade.api.errors import (
    translate_post_trade_error,
)
from app.features.post_trade.application.exit_review_service import (
    ExitReviewIncompleteError,
    ExitReviewNotFoundError,
    ExitReviewService,
)
from app.features.post_trade.application.handoff_service import (
    Ft012HandoffService,
)
from app.features.post_trade.application.observation_service import (
    PostTradeContextNotFoundError,
    PostTradeObservationService,
)
from app.features.post_trade.application.query_service import (
    PostTradeQueryService,
)
from app.features.post_trade.domain import (
    ExitReview,
    ExitReviewVersion,
    PostTradeObservation,
)
from app.features.post_trade.domain.observation_metrics import (
    LevelCrossing,
    ObservedExtreme,
)

router = APIRouter(
    prefix="/api/v1/post-trade",
    tags=["post-trade"],
)

WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")
LOCAL_ACTOR_ID = UUID("00000000-0000-4000-8000-000000000002")


def _actor(value: UUID | None) -> UUID:
    return value or LOCAL_ACTOR_ID


def _observation_response(
    observation: PostTradeObservation,
    *,
    available_observation_count: int,
) -> ObservationResponse:
    missing = max(
        observation.target_observation_count - available_observation_count,
        0,
    )

    return ObservationResponse(
        id=observation.id,
        trade_id=observation.trade_id,
        status=observation.status,
        underlying_listing_id=observation.underlying_listing_id,
        target_observation_count=observation.target_observation_count,
        available_observation_count=available_observation_count,
        missing_observation_count=missing,
        is_complete=observation.status.value == "COMPLETED",
        started_at=observation.started_at,
        completed_at=observation.completed_at,
        created_at=observation.created_at,
    )


def _extreme(
    value: ObservedExtreme | None,
) -> ObservedExtremeResponse | None:
    if value is None:
        return None

    return ObservedExtremeResponse(
        trading_date=value.trading_date,
        value=value.value,
    )


def _crossing(
    value: LevelCrossing | None,
) -> LevelCrossingResponse | None:
    if value is None:
        return None

    return LevelCrossingResponse(
        level=value.level,
        crossed=value.crossed,
        first_crossed_on=value.first_crossed_on,
    )


def _review_response(
    review: ExitReview,
    version: ExitReviewVersion,
) -> ExitReviewResponse:
    return ExitReviewResponse(
        exit_review_id=review.id,
        current_version_id=version.id,
        version=version.version,
        status=version.status,
        currentness=version.currentness,
        timing=version.timing,
        process_adherence=version.process_adherence,
        risk_decision=version.risk_decision,
        overall_exit_decision=version.overall_exit_decision,
        rationale=version.rationale,
        created_at=version.created_at,
        created_by=version.created_by,
        finalized_at=version.finalized_at,
        finalized_by=version.finalized_by,
        supersedes_version_id=version.supersedes_version_id,
        stale_at=version.stale_at,
        stale_reason=version.stale_reason,
    )


@router.post(
    "/trades/{trade_id}/observation",
    response_model=ObservationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_observation(
    trade_id: UUID,
    service: Annotated[
        PostTradeObservationService,
        Depends(get_post_trade_observation_service),
    ],
    actor_id: Annotated[
        UUID | None,
        Header(alias="X-Actor-ID"),
    ] = None,
) -> ObservationResponse:
    try:
        observation = await service.start(
            workspace_id=WORKSPACE_ID,
            trade_id=trade_id,
            actor_id=_actor(actor_id),
        )

        return _observation_response(
            observation,
            available_observation_count=0,
        )
    except Exception as error:
        raise translate_post_trade_error(error) from error


@router.get(
    "/trades/{trade_id}/observation",
    response_model=ObservationResponse,
)
async def get_observation(
    trade_id: UUID,
    service: Annotated[
        PostTradeObservationService,
        Depends(get_post_trade_observation_service),
    ],
    query: Annotated[
        PostTradeQueryService,
        Depends(get_post_trade_query_service),
    ],
) -> ObservationResponse:
    try:
        observation = await query.get_observation_for_trade(
            workspace_id=WORKSPACE_ID,
            trade_id=trade_id,
        )
        if observation is None:
            raise PostTradeContextNotFoundError("post-trade observation not found")

        updated, evidence = await service.refresh(
            workspace_id=WORKSPACE_ID,
            observation_id=observation.id,
        )

        return _observation_response(
            updated,
            available_observation_count=(evidence.available_observation_count),
        )
    except Exception as error:
        raise translate_post_trade_error(error) from error


@router.get(
    "/trades/{trade_id}/observation/evidence",
    response_model=ObservationEvidenceResponse,
)
async def get_observation_evidence(
    trade_id: UUID,
    service: Annotated[
        PostTradeObservationService,
        Depends(get_post_trade_observation_service),
    ],
    query: Annotated[
        PostTradeQueryService,
        Depends(get_post_trade_query_service),
    ],
) -> ObservationEvidenceResponse:
    try:
        view = await query.get_observation_view(
            workspace_id=WORKSPACE_ID,
            trade_id=trade_id,
        )
        if view is None or view.trade.full_exit_at is None:
            raise PostTradeContextNotFoundError(
                "post-trade observation or trade exit context not found"
            )

        updated, evidence = await service.refresh(
            workspace_id=WORKSPACE_ID,
            observation_id=view.observation.id,
        )

        trade = view.trade

        return ObservationEvidenceResponse(
            observation_id=updated.id,
            trade_id=updated.trade_id,
            product_context=(
                ProductContextResponse(
                    warrant_id=view.product.warrant_id,
                    underlying_id=view.product.underlying_id,
                    historical_warrant_terms_version_id=(
                        view.product.historical_warrant_terms_version_id
                    ),
                    maturity_date=view.product.maturity_date,
                    historical_underlying_listing_id=(
                        view.product.historical_underlying_listing_id
                    ),
                )
                if view.product is not None
                else None
            ),
            planning_context=PlanningContextResponse(
                trade_plan_id=view.planning.trade_plan_id,
                trade_plan_version_id=view.planning.trade_plan_version_id,
                original_stop=view.planning.original_stop,
                original_targets=list(view.planning.original_targets),
            ),
            management_levels=[
                ManagementLevelResponse(
                    event_id=item.event_id,
                    kind=item.kind,
                    effective_at=item.effective_at,
                    numeric_value=item.numeric_value,
                )
                for item in trade.management_events
            ],
            actual_exit=ActualExitResponse(
                full_exit_at=trade.full_exit_at,
                realized_gross_pnl=trade.realized_gross_pnl,
                executions=[
                    ExitExecutionResponse(
                        execution_id=item.execution_id,
                        quantity=item.quantity,
                        price_per_unit=item.price_per_unit,
                        executed_at=item.executed_at,
                    )
                    for item in trade.executions
                ],
            ),
            counterfactual=CounterfactualEvidenceResponse(
                available_observation_count=(evidence.available_observation_count),
                target_observation_count=(evidence.target_observation_count),
                horizon_complete=evidence.horizon_complete,
                points=[
                    ObservationPointResponse(
                        trading_date=item.trading_date,
                        open=item.open,
                        high=item.high,
                        low=item.low,
                        close=item.close,
                        adjusted_close=item.adjusted_close,
                        quality_status=item.quality_status,
                    )
                    for item in evidence.points
                ],
                highest_high=_extreme(evidence.highest_high),
                lowest_low=_extreme(evidence.lowest_low),
                final_close=_extreme(evidence.final_close),
                target_crossings=[_crossing(item) for item in evidence.target_crossings],
                stop_crossing=_crossing(evidence.stop_crossing),
            ),
        )
    except Exception as error:
        raise translate_post_trade_error(error) from error


@router.post(
    "/trades/{trade_id}/exit-review",
    response_model=ExitReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_exit_review_draft(
    trade_id: UUID,
    service: Annotated[
        ExitReviewService,
        Depends(get_exit_review_service),
    ],
    query: Annotated[
        PostTradeQueryService,
        Depends(get_post_trade_query_service),
    ],
    actor_id: Annotated[
        UUID | None,
        Header(alias="X-Actor-ID"),
    ] = None,
) -> ExitReviewResponse:
    try:
        observation = await query.get_observation_for_trade(
            workspace_id=WORKSPACE_ID,
            trade_id=trade_id,
        )
        if observation is None:
            raise PostTradeContextNotFoundError("post-trade observation not found")

        review, draft = await service.get_or_create_draft(
            workspace_id=WORKSPACE_ID,
            observation_id=observation.id,
            actor_id=_actor(actor_id),
        )

        return _review_response(review, draft)
    except Exception as error:
        raise translate_post_trade_error(error) from error


@router.get(
    "/trades/{trade_id}/exit-review",
    response_model=ExitReviewResponse,
)
async def get_exit_review(
    trade_id: UUID,
    query: Annotated[
        PostTradeQueryService,
        Depends(get_post_trade_query_service),
    ],
) -> ExitReviewResponse:
    try:
        view = await query.get_latest_exit_review(
            workspace_id=WORKSPACE_ID,
            trade_id=trade_id,
        )
        if view is None:
            raise ExitReviewNotFoundError("exit review version not found")

        return _review_response(
            view.review,
            view.version,
        )
    except Exception as error:
        raise translate_post_trade_error(error) from error


@router.put(
    "/trades/{trade_id}/exit-review/draft",
    response_model=ExitReviewResponse,
)
async def update_exit_review_draft(
    trade_id: UUID,
    request: ExitReviewDraftRequest,
    service: Annotated[
        ExitReviewService,
        Depends(get_exit_review_service),
    ],
    query: Annotated[
        PostTradeQueryService,
        Depends(get_post_trade_query_service),
    ],
) -> ExitReviewResponse:
    try:
        view = await query.get_open_draft(
            workspace_id=WORKSPACE_ID,
            trade_id=trade_id,
        )
        if view is None:
            raise ExitReviewNotFoundError("exit review version not found")

        updated = await service.update_draft(
            workspace_id=WORKSPACE_ID,
            review_id=view.review.id,
            version_id=view.version.id,
            timing=request.timing,
            process_adherence=request.process_adherence,
            risk_decision=request.risk_decision,
            overall_exit_decision=request.overall_exit_decision,
            rationale=request.rationale,
        )

        return _review_response(
            view.review,
            updated,
        )
    except Exception as error:
        raise translate_post_trade_error(error) from error


@router.post(
    "/trades/{trade_id}/exit-review/finalize",
    response_model=ExitReviewResponse,
)
async def finalize_exit_review(
    trade_id: UUID,
    service: Annotated[
        ExitReviewService,
        Depends(get_exit_review_service),
    ],
    query: Annotated[
        PostTradeQueryService,
        Depends(get_post_trade_query_service),
    ],
    actor_id: Annotated[
        UUID | None,
        Header(alias="X-Actor-ID"),
    ] = None,
) -> ExitReviewResponse:
    try:
        view = await query.get_open_draft(
            workspace_id=WORKSPACE_ID,
            trade_id=trade_id,
        )
        if view is None:
            raise ExitReviewNotFoundError("exit review version not found")

        draft = view.version

        if (
            draft.timing is None
            or draft.process_adherence is None
            or draft.risk_decision is None
            or draft.overall_exit_decision is None
        ):
            raise ExitReviewIncompleteError("exit review assessments are incomplete")

        if not draft.rationale or not draft.rationale.strip():
            raise ApplicationError(
                code="EXIT_REVIEW_RATIONALE_REQUIRED",
                message="exit review rationale is required",
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            )

        finalized = await service.finalize(
            workspace_id=WORKSPACE_ID,
            review_id=view.review.id,
            version_id=draft.id,
            actor_id=_actor(actor_id),
            timing=draft.timing,
            process_adherence=draft.process_adherence,
            risk_decision=draft.risk_decision,
            overall_exit_decision=draft.overall_exit_decision,
            rationale=draft.rationale,
        )

        return _review_response(
            view.review,
            finalized,
        )
    except ApplicationError:
        raise
    except Exception as error:
        raise translate_post_trade_error(error) from error


@router.post(
    "/trades/{trade_id}/exit-review/revalidate",
    response_model=ExitReviewResponse,
)
async def revalidate_exit_review(
    trade_id: UUID,
    service: Annotated[
        ExitReviewService,
        Depends(get_exit_review_service),
    ],
    query: Annotated[
        PostTradeQueryService,
        Depends(get_post_trade_query_service),
    ],
) -> ExitReviewResponse:
    try:
        view = await query.get_latest_exit_review(
            workspace_id=WORKSPACE_ID,
            trade_id=trade_id,
        )
        if view is None:
            raise ExitReviewNotFoundError("exit review version not found")

        version = await service.refresh_currentness(
            workspace_id=WORKSPACE_ID,
            review_id=view.review.id,
        )
        if version is None:
            raise ExitReviewNotFoundError("exit review version not found")

        return _review_response(
            view.review,
            version,
        )
    except Exception as error:
        raise translate_post_trade_error(error) from error


@router.get(
    "/trades/{trade_id}/exit-review/history",
    response_model=list[ExitReviewResponse],
)
async def get_exit_review_history(
    trade_id: UUID,
    query: Annotated[
        PostTradeQueryService,
        Depends(get_post_trade_query_service),
    ],
) -> list[ExitReviewResponse]:
    try:
        views = await query.list_exit_review_history(
            workspace_id=WORKSPACE_ID,
            trade_id=trade_id,
        )

        return [
            _review_response(
                view.review,
                view.version,
            )
            for view in views
        ]
    except Exception as error:
        raise translate_post_trade_error(error) from error


@router.get(
    "/trades/{trade_id}/handoff",
    response_model=HandoffResponse,
)
async def get_ft012_handoff(
    trade_id: UUID,
    service: Annotated[
        Ft012HandoffService,
        Depends(get_ft012_handoff_service),
    ],
) -> HandoffResponse:
    result = await service.get(
        workspace_id=WORKSPACE_ID,
        trade_id=trade_id,
    )

    return HandoffResponse(
        ready=result.ready,
        reason=result.reason,
        post_trade_observation_id=(result.post_trade_observation_id),
        exit_review_id=result.exit_review_id,
        exit_review_version_id=result.exit_review_version_id,
    )
