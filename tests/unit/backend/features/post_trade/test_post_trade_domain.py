"""Unit tests for FT-011 Post Trade domain invariants."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.features.post_trade.domain import (
    FT011_V1_OBSERVATION_COUNT,
    ExitReview,
    ExitReviewAssessment,
    ExitReviewCurrentness,
    ExitReviewStatus,
    ExitReviewVersion,
    PostTradeObservation,
    PostTradeObservationStatus,
)

NOW = datetime(2026, 8, 18, 12, 0, tzinfo=UTC)


def _observation(
    *,
    status: PostTradeObservationStatus = PostTradeObservationStatus.ACTIVE,
    target_observation_count: int = FT011_V1_OBSERVATION_COUNT,
    completed_at: datetime | None = None,
) -> PostTradeObservation:
    return PostTradeObservation(
        id=uuid4(),
        workspace_id=uuid4(),
        trade_id=uuid4(),
        underlying_listing_id=uuid4(),
        status=status,
        target_observation_count=target_observation_count,
        started_at=NOW,
        started_by=uuid4(),
        completed_at=completed_at,
        created_at=NOW,
        updated_at=completed_at or NOW,
    )


def _draft(
    *,
    version: int = 1,
    supersedes_version_id: UUID | None = None,
) -> ExitReviewVersion:
    return ExitReviewVersion(
        id=uuid4(),
        exit_review_id=uuid4(),
        version=version,
        status=ExitReviewStatus.DRAFT,
        currentness=ExitReviewCurrentness.CURRENT,
        timing=None,
        process_adherence=None,
        risk_decision=None,
        overall_exit_decision=None,
        rationale=None,
        input_fingerprint=None,
        created_at=NOW,
        created_by=uuid4(),
        supersedes_version_id=supersedes_version_id,
    )


def _finalized() -> ExitReviewVersion:
    return _draft().finalize(
        timing=ExitReviewAssessment.IMPROVABLE,
        process_adherence=ExitReviewAssessment.GOOD,
        risk_decision=ExitReviewAssessment.GOOD,
        overall_exit_decision=ExitReviewAssessment.ACCEPTABLE,
        rationale="Timing war verbesserungswürdig, der Prozess wurde eingehalten.",
        input_fingerprint="a" * 64,
        finalized_at=NOW + timedelta(minutes=1),
        finalized_by=uuid4(),
    )


def test_active_observation_is_valid() -> None:
    observation = _observation()

    assert observation.status is PostTradeObservationStatus.ACTIVE
    assert observation.completed_at is None
    assert observation.is_complete is False
    assert observation.target_observation_count == 20


def test_active_observation_must_not_have_completed_at() -> None:
    with pytest.raises(
        ValueError,
        match="ACTIVE post-trade observation must not have completed_at",
    ):
        _observation(
            status=PostTradeObservationStatus.ACTIVE,
            completed_at=NOW + timedelta(days=1),
        )


def test_completed_observation_requires_completed_at() -> None:
    with pytest.raises(
        ValueError,
        match="COMPLETED post-trade observation requires completed_at",
    ):
        _observation(status=PostTradeObservationStatus.COMPLETED)


def test_v1_observation_count_is_exactly_twenty() -> None:
    with pytest.raises(
        ValueError,
        match="FT-011 V1 observation count must be 20",
    ):
        _observation(target_observation_count=10)


def test_observation_complete_returns_new_immutable_snapshot() -> None:
    original = _observation()
    completed_at = NOW + timedelta(days=30)

    completed = original.complete(completed_at=completed_at)

    assert original.status is PostTradeObservationStatus.ACTIVE
    assert original.completed_at is None

    assert completed.status is PostTradeObservationStatus.COMPLETED
    assert completed.completed_at == completed_at
    assert completed.updated_at == completed_at
    assert completed.is_complete is True


def test_completed_observation_cannot_be_completed_twice() -> None:
    observation = _observation().complete(completed_at=NOW + timedelta(days=30))

    with pytest.raises(
        ValueError,
        match="post-trade observation is already completed",
    ):
        observation.complete(completed_at=NOW + timedelta(days=31))


def test_observation_is_frozen() -> None:
    observation = _observation()

    with pytest.raises(FrozenInstanceError):
        observation.status = PostTradeObservationStatus.COMPLETED  # type: ignore[misc]


def test_exit_review_identity_is_immutable() -> None:
    review = ExitReview(
        id=uuid4(),
        workspace_id=uuid4(),
        post_trade_observation_id=uuid4(),
        created_at=NOW,
        created_by=uuid4(),
    )

    with pytest.raises(FrozenInstanceError):
        review.created_by = uuid4()  # type: ignore[misc]


def test_draft_review_version_is_valid() -> None:
    version = _draft()

    assert version.status is ExitReviewStatus.DRAFT
    assert version.currentness is ExitReviewCurrentness.CURRENT
    assert version.is_finalized is False
    assert version.is_stale is False


def test_draft_must_not_have_fingerprint() -> None:
    with pytest.raises(
        ValueError,
        match="DRAFT exit review version must not carry input_fingerprint",
    ):
        ExitReviewVersion(
            id=uuid4(),
            exit_review_id=uuid4(),
            version=1,
            status=ExitReviewStatus.DRAFT,
            currentness=ExitReviewCurrentness.CURRENT,
            timing=None,
            process_adherence=None,
            risk_decision=None,
            overall_exit_decision=None,
            rationale=None,
            input_fingerprint="a" * 64,
            created_at=NOW,
            created_by=uuid4(),
        )


def test_review_version_must_be_positive() -> None:
    with pytest.raises(
        ValueError,
        match="exit review version must be positive",
    ):
        _draft(version=0)


def test_review_version_must_not_supersede_itself() -> None:
    version_id = uuid4()

    with pytest.raises(
        ValueError,
        match="exit review version must not supersede itself",
    ):
        ExitReviewVersion(
            id=version_id,
            exit_review_id=uuid4(),
            version=2,
            status=ExitReviewStatus.DRAFT,
            currentness=ExitReviewCurrentness.CURRENT,
            timing=None,
            process_adherence=None,
            risk_decision=None,
            overall_exit_decision=None,
            rationale=None,
            input_fingerprint=None,
            created_at=NOW,
            created_by=uuid4(),
            supersedes_version_id=version_id,
        )


def test_finalize_creates_finalized_current_snapshot() -> None:
    draft = _draft()
    actor = uuid4()

    finalized = draft.finalize(
        timing=ExitReviewAssessment.IMPROVABLE,
        process_adherence=ExitReviewAssessment.GOOD,
        risk_decision=ExitReviewAssessment.GOOD,
        overall_exit_decision=ExitReviewAssessment.ACCEPTABLE,
        rationale="Frühes Timing, aber regelkonformes Risikomanagement.",
        input_fingerprint="b" * 64,
        finalized_at=NOW + timedelta(minutes=1),
        finalized_by=actor,
    )

    assert draft.status is ExitReviewStatus.DRAFT
    assert finalized.status is ExitReviewStatus.FINALIZED
    assert finalized.currentness is ExitReviewCurrentness.CURRENT
    assert finalized.timing is ExitReviewAssessment.IMPROVABLE
    assert finalized.process_adherence is ExitReviewAssessment.GOOD
    assert finalized.risk_decision is ExitReviewAssessment.GOOD
    assert finalized.overall_exit_decision is ExitReviewAssessment.ACCEPTABLE
    assert finalized.input_fingerprint == "b" * 64
    assert finalized.finalized_by == actor
    assert finalized.is_finalized is True
    assert finalized.is_stale is False


def test_finalized_review_requires_all_assessments() -> None:
    with pytest.raises(
        ValueError,
        match="FINALIZED exit review version requires all assessments",
    ):
        ExitReviewVersion(
            id=uuid4(),
            exit_review_id=uuid4(),
            version=1,
            status=ExitReviewStatus.FINALIZED,
            currentness=ExitReviewCurrentness.CURRENT,
            timing=None,
            process_adherence=ExitReviewAssessment.GOOD,
            risk_decision=ExitReviewAssessment.GOOD,
            overall_exit_decision=ExitReviewAssessment.ACCEPTABLE,
            rationale="Begründung",
            input_fingerprint="c" * 64,
            created_at=NOW,
            created_by=uuid4(),
            finalized_at=NOW + timedelta(minutes=1),
            finalized_by=uuid4(),
        )


def test_finalized_review_requires_rationale() -> None:
    with pytest.raises(
        ValueError,
        match="FINALIZED exit review version requires rationale",
    ):
        ExitReviewVersion(
            id=uuid4(),
            exit_review_id=uuid4(),
            version=1,
            status=ExitReviewStatus.FINALIZED,
            currentness=ExitReviewCurrentness.CURRENT,
            timing=ExitReviewAssessment.GOOD,
            process_adherence=ExitReviewAssessment.GOOD,
            risk_decision=ExitReviewAssessment.GOOD,
            overall_exit_decision=ExitReviewAssessment.GOOD,
            rationale=" ",
            input_fingerprint="d" * 64,
            created_at=NOW,
            created_by=uuid4(),
            finalized_at=NOW + timedelta(minutes=1),
            finalized_by=uuid4(),
        )


def test_finalized_review_requires_fingerprint() -> None:
    with pytest.raises(
        ValueError,
        match="FINALIZED exit review version requires input_fingerprint",
    ):
        ExitReviewVersion(
            id=uuid4(),
            exit_review_id=uuid4(),
            version=1,
            status=ExitReviewStatus.FINALIZED,
            currentness=ExitReviewCurrentness.CURRENT,
            timing=ExitReviewAssessment.GOOD,
            process_adherence=ExitReviewAssessment.GOOD,
            risk_decision=ExitReviewAssessment.GOOD,
            overall_exit_decision=ExitReviewAssessment.GOOD,
            rationale="Begründung",
            input_fingerprint=None,
            created_at=NOW,
            created_by=uuid4(),
            finalized_at=NOW + timedelta(minutes=1),
            finalized_by=uuid4(),
        )


def test_mark_stale_preserves_review_content() -> None:
    finalized = _finalized()
    stale_at = NOW + timedelta(minutes=2)

    stale = finalized.mark_stale(
        stale_at=stale_at,
        stale_reason="effective SELL execution changed",
    )

    assert finalized.currentness is ExitReviewCurrentness.CURRENT
    assert finalized.stale_at is None

    assert stale.currentness is ExitReviewCurrentness.STALE
    assert stale.stale_at == stale_at
    assert stale.stale_reason == "effective SELL execution changed"

    assert stale.timing == finalized.timing
    assert stale.process_adherence == finalized.process_adherence
    assert stale.risk_decision == finalized.risk_decision
    assert stale.overall_exit_decision == finalized.overall_exit_decision
    assert stale.rationale == finalized.rationale
    assert stale.input_fingerprint == finalized.input_fingerprint


def test_draft_cannot_be_marked_stale() -> None:
    with pytest.raises(
        ValueError,
        match="only FINALIZED exit review version may become STALE",
    ):
        _draft().mark_stale(
            stale_at=NOW + timedelta(minutes=1),
            stale_reason="changed input",
        )


def test_stale_at_must_not_precede_finalized_at() -> None:
    finalized = _finalized()

    with pytest.raises(
        ValueError,
        match="stale_at must not precede finalized_at",
    ):
        finalized.mark_stale(
            stale_at=NOW,
            stale_reason="changed input",
        )
