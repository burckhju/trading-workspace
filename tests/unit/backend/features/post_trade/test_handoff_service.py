"""Unit tests for FT-012 handoff gate."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.features.post_trade.application.handoff_service import (
    Ft012HandoffService,
)
from app.features.post_trade.domain import (
    ExitReview,
    ExitReviewAssessment,
    ExitReviewCurrentness,
    ExitReviewStatus,
    ExitReviewVersion,
    PostTradeObservation,
    PostTradeObservationStatus,
)

NOW = datetime(2026, 8, 18, 12, 0, tzinfo=UTC)


def _uow():
    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=None)

    uow.observations = MagicMock()
    uow.exit_reviews = MagicMock()
    uow.exit_review_versions = MagicMock()

    return uow


def _observation(*, completed=True):
    return PostTradeObservation(
        id=uuid4(),
        workspace_id=uuid4(),
        trade_id=uuid4(),
        underlying_listing_id=uuid4(),
        status=(
            PostTradeObservationStatus.COMPLETED if completed else PostTradeObservationStatus.ACTIVE
        ),
        target_observation_count=20,
        started_at=NOW,
        started_by=uuid4(),
        completed_at=NOW if completed else None,
        created_at=NOW,
        updated_at=NOW,
    )


def _review(observation):
    return ExitReview(
        id=uuid4(),
        workspace_id=observation.workspace_id,
        post_trade_observation_id=observation.id,
        created_at=NOW,
        created_by=uuid4(),
    )


def _version(review, *, finalized=True, current=True):
    return ExitReviewVersion(
        id=uuid4(),
        exit_review_id=review.id,
        version=1,
        status=(ExitReviewStatus.FINALIZED if finalized else ExitReviewStatus.DRAFT),
        currentness=(ExitReviewCurrentness.CURRENT if current else ExitReviewCurrentness.STALE),
        timing=(ExitReviewAssessment.GOOD if finalized else None),
        process_adherence=(ExitReviewAssessment.GOOD if finalized else None),
        risk_decision=(ExitReviewAssessment.GOOD if finalized else None),
        overall_exit_decision=(ExitReviewAssessment.GOOD if finalized else None),
        rationale="done" if finalized else None,
        input_fingerprint=("a" * 64) if finalized else None,
        created_at=NOW,
        created_by=uuid4(),
        finalized_at=NOW if finalized else None,
        finalized_by=uuid4() if finalized else None,
        stale_at=NOW if not current else None,
        stale_reason="changed" if not current else None,
    )


@pytest.mark.asyncio
async def test_handoff_blocks_missing_observation() -> None:
    uow = _uow()
    uow.observations.get_for_trade = AsyncMock(return_value=None)

    result = await Ft012HandoffService(uow=uow).get(
        workspace_id=uuid4(),
        trade_id=uuid4(),
    )

    assert result.ready is False
    assert result.reason == "POST_TRADE_OBSERVATION_MISSING"


@pytest.mark.asyncio
async def test_handoff_blocks_incomplete_observation() -> None:
    observation = _observation(completed=False)

    uow = _uow()
    uow.observations.get_for_trade = AsyncMock(return_value=observation)

    result = await Ft012HandoffService(uow=uow).get(
        workspace_id=observation.workspace_id,
        trade_id=observation.trade_id,
    )

    assert result.ready is False
    assert result.reason == "POST_TRADE_OBSERVATION_INCOMPLETE"


@pytest.mark.asyncio
async def test_handoff_blocks_missing_review() -> None:
    observation = _observation()

    uow = _uow()
    uow.observations.get_for_trade = AsyncMock(return_value=observation)
    uow.exit_reviews.get_for_observation = AsyncMock(return_value=None)

    result = await Ft012HandoffService(uow=uow).get(
        workspace_id=observation.workspace_id,
        trade_id=observation.trade_id,
    )

    assert result.ready is False
    assert result.reason == "EXIT_REVIEW_MISSING"


@pytest.mark.asyncio
async def test_handoff_blocks_draft_review() -> None:
    observation = _observation()
    review = _review(observation)
    version = _version(review, finalized=False)

    uow = _uow()
    uow.observations.get_for_trade = AsyncMock(return_value=observation)
    uow.exit_reviews.get_for_observation = AsyncMock(return_value=review)
    uow.exit_review_versions.get_latest = AsyncMock(return_value=version)

    result = await Ft012HandoffService(uow=uow).get(
        workspace_id=observation.workspace_id,
        trade_id=observation.trade_id,
    )

    assert result.ready is False
    assert result.reason == "EXIT_REVIEW_NOT_FINALIZED"


@pytest.mark.asyncio
async def test_handoff_blocks_stale_review() -> None:
    observation = _observation()
    review = _review(observation)
    version = _version(review, current=False)

    uow = _uow()
    uow.observations.get_for_trade = AsyncMock(return_value=observation)
    uow.exit_reviews.get_for_observation = AsyncMock(return_value=review)
    uow.exit_review_versions.get_latest = AsyncMock(return_value=version)

    result = await Ft012HandoffService(uow=uow).get(
        workspace_id=observation.workspace_id,
        trade_id=observation.trade_id,
    )

    assert result.ready is False
    assert result.reason == "EXIT_REVIEW_STALE"


@pytest.mark.asyncio
async def test_handoff_ready_only_for_completed_finalized_current() -> None:
    observation = _observation()
    review = _review(observation)
    version = _version(review)

    uow = _uow()
    uow.observations.get_for_trade = AsyncMock(return_value=observation)
    uow.exit_reviews.get_for_observation = AsyncMock(return_value=review)
    uow.exit_review_versions.get_latest = AsyncMock(return_value=version)

    result = await Ft012HandoffService(uow=uow).get(
        workspace_id=observation.workspace_id,
        trade_id=observation.trade_id,
    )

    assert result.ready is True
    assert result.reason == "READY"
    assert result.post_trade_observation_id == observation.id
    assert result.exit_review_id == review.id
    assert result.exit_review_version_id == version.id
