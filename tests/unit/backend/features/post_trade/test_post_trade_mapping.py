"""Unit tests for FT-011 persistence mapping."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.features.post_trade.domain import (
    ExitReview,
    ExitReviewAssessment,
    ExitReviewCurrentness,
    ExitReviewStatus,
    ExitReviewVersion,
    PostTradeObservation,
    PostTradeObservationStatus,
)
from app.features.post_trade.persistence.mapping import (
    exit_review_from_model,
    exit_review_to_model,
    exit_review_version_from_model,
    exit_review_version_to_model,
    observation_from_model,
    observation_to_model,
)

NOW = datetime(2026, 8, 18, 12, 0, tzinfo=UTC)


def test_observation_mapping_roundtrip() -> None:
    value = PostTradeObservation(
        id=uuid4(),
        workspace_id=uuid4(),
        trade_id=uuid4(),
        underlying_listing_id=uuid4(),
        status=PostTradeObservationStatus.COMPLETED,
        target_observation_count=20,
        started_at=NOW,
        started_by=uuid4(),
        completed_at=NOW + timedelta(days=30),
        created_at=NOW,
        updated_at=NOW + timedelta(days=30),
    )

    assert observation_from_model(observation_to_model(value)) == value


def test_exit_review_mapping_roundtrip() -> None:
    value = ExitReview(
        id=uuid4(),
        workspace_id=uuid4(),
        post_trade_observation_id=uuid4(),
        created_at=NOW,
        created_by=uuid4(),
    )

    assert exit_review_from_model(exit_review_to_model(value)) == value


def test_exit_review_version_mapping_roundtrip() -> None:
    value = ExitReviewVersion(
        id=uuid4(),
        exit_review_id=uuid4(),
        version=2,
        status=ExitReviewStatus.FINALIZED,
        currentness=ExitReviewCurrentness.STALE,
        timing=ExitReviewAssessment.IMPROVABLE,
        process_adherence=ExitReviewAssessment.GOOD,
        risk_decision=ExitReviewAssessment.ACCEPTABLE,
        overall_exit_decision=ExitReviewAssessment.ACCEPTABLE,
        rationale="Review rationale",
        input_fingerprint="f" * 64,
        created_at=NOW,
        created_by=uuid4(),
        finalized_at=NOW + timedelta(minutes=1),
        finalized_by=uuid4(),
        supersedes_version_id=uuid4(),
        stale_at=NOW + timedelta(minutes=2),
        stale_reason="effective SELL changed",
    )

    assert exit_review_version_from_model(exit_review_version_to_model(value)) == value
