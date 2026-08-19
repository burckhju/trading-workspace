"""Domain/persistence mapping for FT-011 Post Trade."""

from app.features.post_trade.domain import (
    ExitReview,
    ExitReviewAssessment,
    ExitReviewCurrentness,
    ExitReviewStatus,
    ExitReviewVersion,
    PostTradeObservation,
    PostTradeObservationStatus,
)
from app.features.post_trade.persistence.models import (
    ExitReviewModel,
    ExitReviewVersionModel,
    PostTradeObservationModel,
)


def observation_to_model(value: PostTradeObservation) -> PostTradeObservationModel:
    return PostTradeObservationModel(
        id=value.id,
        workspace_id=value.workspace_id,
        trade_id=value.trade_id,
        underlying_listing_id=value.underlying_listing_id,
        status=value.status.value,
        target_observation_count=value.target_observation_count,
        started_at=value.started_at,
        started_by=value.started_by,
        completed_at=value.completed_at,
        created_at=value.created_at,
        updated_at=value.updated_at,
    )


def observation_from_model(value: PostTradeObservationModel) -> PostTradeObservation:
    return PostTradeObservation(
        id=value.id,
        workspace_id=value.workspace_id,
        trade_id=value.trade_id,
        underlying_listing_id=value.underlying_listing_id,
        status=PostTradeObservationStatus(value.status),
        target_observation_count=value.target_observation_count,
        started_at=value.started_at,
        started_by=value.started_by,
        completed_at=value.completed_at,
        created_at=value.created_at,
        updated_at=value.updated_at,
    )


def exit_review_to_model(value: ExitReview) -> ExitReviewModel:
    return ExitReviewModel(
        id=value.id,
        workspace_id=value.workspace_id,
        post_trade_observation_id=value.post_trade_observation_id,
        created_at=value.created_at,
        created_by=value.created_by,
    )


def exit_review_from_model(value: ExitReviewModel) -> ExitReview:
    return ExitReview(
        id=value.id,
        workspace_id=value.workspace_id,
        post_trade_observation_id=value.post_trade_observation_id,
        created_at=value.created_at,
        created_by=value.created_by,
    )


def exit_review_version_to_model(
    value: ExitReviewVersion,
) -> ExitReviewVersionModel:
    return ExitReviewVersionModel(
        id=value.id,
        exit_review_id=value.exit_review_id,
        version=value.version,
        status=value.status.value,
        currentness=value.currentness.value,
        timing=value.timing.value if value.timing else None,
        process_adherence=(value.process_adherence.value if value.process_adherence else None),
        risk_decision=(value.risk_decision.value if value.risk_decision else None),
        overall_exit_decision=(
            value.overall_exit_decision.value if value.overall_exit_decision else None
        ),
        rationale=value.rationale,
        input_fingerprint=value.input_fingerprint,
        created_at=value.created_at,
        created_by=value.created_by,
        finalized_at=value.finalized_at,
        finalized_by=value.finalized_by,
        supersedes_version_id=value.supersedes_version_id,
        stale_at=value.stale_at,
        stale_reason=value.stale_reason,
    )


def exit_review_version_from_model(
    value: ExitReviewVersionModel,
) -> ExitReviewVersion:
    return ExitReviewVersion(
        id=value.id,
        exit_review_id=value.exit_review_id,
        version=value.version,
        status=ExitReviewStatus(value.status),
        currentness=ExitReviewCurrentness(value.currentness),
        timing=ExitReviewAssessment(value.timing) if value.timing else None,
        process_adherence=(
            ExitReviewAssessment(value.process_adherence) if value.process_adherence else None
        ),
        risk_decision=(ExitReviewAssessment(value.risk_decision) if value.risk_decision else None),
        overall_exit_decision=(
            ExitReviewAssessment(value.overall_exit_decision)
            if value.overall_exit_decision
            else None
        ),
        rationale=value.rationale,
        input_fingerprint=value.input_fingerprint,
        created_at=value.created_at,
        created_by=value.created_by,
        finalized_at=value.finalized_at,
        finalized_by=value.finalized_by,
        supersedes_version_id=value.supersedes_version_id,
        stale_at=value.stale_at,
        stale_reason=value.stale_reason,
    )
