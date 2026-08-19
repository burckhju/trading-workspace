"""Unit tests for FT-011 SQLAlchemy repositories."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.features.post_trade.domain import (
    ExitReview,
    ExitReviewCurrentness,
    ExitReviewStatus,
    ExitReviewVersion,
    PostTradeObservation,
    PostTradeObservationStatus,
)
from app.features.post_trade.persistence.repositories import (
    SqlAlchemyExitReviewRepository,
    SqlAlchemyExitReviewVersionRepository,
    SqlAlchemyPostTradeObservationRepository,
)

NOW = datetime(2026, 8, 18, 12, 0, tzinfo=UTC)


def _observation() -> PostTradeObservation:
    return PostTradeObservation(
        id=uuid4(),
        workspace_id=uuid4(),
        trade_id=uuid4(),
        underlying_listing_id=uuid4(),
        status=PostTradeObservationStatus.ACTIVE,
        target_observation_count=20,
        started_at=NOW,
        started_by=uuid4(),
        completed_at=None,
        created_at=NOW,
        updated_at=NOW,
    )


def _review() -> ExitReview:
    return ExitReview(
        id=uuid4(),
        workspace_id=uuid4(),
        post_trade_observation_id=uuid4(),
        created_at=NOW,
        created_by=uuid4(),
    )


def _draft(review_id=None, *, version: int = 1) -> ExitReviewVersion:
    return ExitReviewVersion(
        id=uuid4(),
        exit_review_id=review_id or uuid4(),
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
    )


@pytest.mark.asyncio
async def test_observation_add_maps_domain_to_model() -> None:
    session = MagicMock()
    repo = SqlAlchemyPostTradeObservationRepository(session)
    value = _observation()

    await repo.add(value)

    session.add.assert_called_once()
    model = session.add.call_args.args[0]
    assert model.id == value.id
    assert model.trade_id == value.trade_id
    assert model.status == "ACTIVE"


@pytest.mark.asyncio
async def test_observation_get_returns_none_when_missing() -> None:
    session = MagicMock()
    session.scalar = AsyncMock(return_value=None)

    repo = SqlAlchemyPostTradeObservationRepository(session)

    assert await repo.get(uuid4(), uuid4()) is None


@pytest.mark.asyncio
async def test_observation_replace_raises_when_missing() -> None:
    session = MagicMock()
    session.scalar = AsyncMock(return_value=None)

    repo = SqlAlchemyPostTradeObservationRepository(session)

    with pytest.raises(
        LookupError,
        match="post-trade observation not found",
    ):
        await repo.replace(_observation())


@pytest.mark.asyncio
async def test_exit_review_add_maps_domain_to_model() -> None:
    session = MagicMock()
    repo = SqlAlchemyExitReviewRepository(session)
    value = _review()

    await repo.add(value)

    session.add.assert_called_once()
    model = session.add.call_args.args[0]
    assert model.id == value.id
    assert model.workspace_id == value.workspace_id


@pytest.mark.asyncio
async def test_exit_review_lock_returns_boolean() -> None:
    session = MagicMock()
    session.scalar = AsyncMock(return_value=uuid4())

    repo = SqlAlchemyExitReviewRepository(session)

    assert await repo.lock(uuid4(), uuid4()) is True


@pytest.mark.asyncio
async def test_exit_review_version_add_maps_domain_to_model() -> None:
    session = MagicMock()
    reviews = MagicMock()
    repo = SqlAlchemyExitReviewVersionRepository(session, reviews)
    value = _draft()

    await repo.add(value)

    session.add.assert_called_once()
    model = session.add.call_args.args[0]
    assert model.version == 1
    assert model.status == "DRAFT"


@pytest.mark.asyncio
async def test_exit_review_version_get_returns_none_when_missing() -> None:
    session = MagicMock()
    session.scalar = AsyncMock(return_value=None)

    repo = SqlAlchemyExitReviewVersionRepository(
        session,
        MagicMock(),
    )

    assert await repo.get(uuid4()) is None


@pytest.mark.asyncio
async def test_next_version_number_locks_review_and_increments() -> None:
    session = MagicMock()
    session.scalar = AsyncMock(return_value=3)

    reviews = MagicMock()
    reviews.lock = AsyncMock(return_value=True)

    repo = SqlAlchemyExitReviewVersionRepository(session, reviews)

    result = await repo.next_version_number(uuid4(), uuid4())

    assert result == 4
    reviews.lock.assert_awaited_once()


@pytest.mark.asyncio
async def test_next_version_number_starts_at_one() -> None:
    session = MagicMock()
    session.scalar = AsyncMock(return_value=None)

    reviews = MagicMock()
    reviews.lock = AsyncMock(return_value=True)

    repo = SqlAlchemyExitReviewVersionRepository(session, reviews)

    assert await repo.next_version_number(uuid4(), uuid4()) == 1


@pytest.mark.asyncio
async def test_next_version_number_requires_existing_review() -> None:
    session = MagicMock()

    reviews = MagicMock()
    reviews.lock = AsyncMock(return_value=False)

    repo = SqlAlchemyExitReviewVersionRepository(session, reviews)

    with pytest.raises(LookupError, match="exit review not found"):
        await repo.next_version_number(uuid4(), uuid4())


@pytest.mark.asyncio
async def test_version_replace_updates_model() -> None:
    review_id = uuid4()
    value = _draft(review_id)

    model = SimpleNamespace(
        version=0,
        status="",
        currentness="",
        timing=None,
        process_adherence=None,
        risk_decision=None,
        overall_exit_decision=None,
        rationale=None,
        input_fingerprint=None,
        created_at=None,
        created_by=None,
        finalized_at=None,
        finalized_by=None,
        supersedes_version_id=None,
        stale_at=None,
        stale_reason=None,
    )

    session = MagicMock()
    session.scalar = AsyncMock(return_value=model)

    repo = SqlAlchemyExitReviewVersionRepository(
        session,
        MagicMock(),
    )

    await repo.replace(value)

    assert model.version == 1
    assert model.status == "DRAFT"
    assert model.currentness == "CURRENT"
    assert model.created_by == value.created_by
