"""Unit tests for FT-011 read-side query service."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.features.post_trade.application.query_service import (
    PostTradeQueryService,
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


def _observation():
    return PostTradeObservation(
        id=uuid4(),
        workspace_id=uuid4(),
        trade_id=uuid4(),
        underlying_listing_id=uuid4(),
        status=PostTradeObservationStatus.COMPLETED,
        target_observation_count=20,
        started_at=NOW,
        started_by=uuid4(),
        completed_at=NOW,
        created_at=NOW,
        updated_at=NOW,
    )


@pytest.mark.asyncio
async def test_get_observation_for_trade() -> None:
    observation = _observation()
    uow = _uow()
    uow.observations.get_for_trade = AsyncMock(return_value=observation)

    service = PostTradeQueryService(
        uow=uow,
        trade_reader=MagicMock(),
        planning_reader=MagicMock(),
        product_reader=MagicMock(),
    )

    result = await service.get_observation_for_trade(
        workspace_id=observation.workspace_id,
        trade_id=observation.trade_id,
    )

    assert result is observation


@pytest.mark.asyncio
async def test_get_latest_exit_review() -> None:
    observation = _observation()

    review = ExitReview(
        id=uuid4(),
        workspace_id=observation.workspace_id,
        post_trade_observation_id=observation.id,
        created_at=NOW,
        created_by=uuid4(),
    )

    finalized_by = uuid4()

    version = ExitReviewVersion(
        id=uuid4(),
        exit_review_id=review.id,
        version=1,
        status=ExitReviewStatus.FINALIZED,
        currentness=ExitReviewCurrentness.CURRENT,
        timing=ExitReviewAssessment.GOOD,
        process_adherence=ExitReviewAssessment.GOOD,
        risk_decision=ExitReviewAssessment.ACCEPTABLE,
        overall_exit_decision=ExitReviewAssessment.GOOD,
        rationale="Finalized review for query-service test.",
        input_fingerprint="a" * 64,
        created_at=NOW,
        created_by=uuid4(),
        finalized_at=NOW,
        finalized_by=finalized_by,
    )

    uow = _uow()
    uow.observations.get_for_trade = AsyncMock(return_value=observation)
    uow.exit_reviews.get_for_observation = AsyncMock(return_value=review)
    uow.exit_review_versions.get_latest = AsyncMock(return_value=version)

    service = PostTradeQueryService(
        uow=uow,
        trade_reader=MagicMock(),
        planning_reader=MagicMock(),
        product_reader=MagicMock(),
    )

    result = await service.get_latest_exit_review(
        workspace_id=observation.workspace_id,
        trade_id=observation.trade_id,
    )

    assert result is not None
    assert result.observation is observation
    assert result.review is review
    assert result.version is version


@pytest.mark.asyncio
async def test_history_returns_empty_when_review_missing() -> None:
    observation = _observation()

    uow = _uow()
    uow.observations.get_for_trade = AsyncMock(return_value=observation)
    uow.exit_reviews.get_for_observation = AsyncMock(return_value=None)

    service = PostTradeQueryService(
        uow=uow,
        trade_reader=MagicMock(),
        planning_reader=MagicMock(),
        product_reader=MagicMock(),
    )

    result = await service.list_exit_review_history(
        workspace_id=observation.workspace_id,
        trade_id=observation.trade_id,
    )

    assert result == ()
