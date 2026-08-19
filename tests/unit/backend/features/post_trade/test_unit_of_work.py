"""Unit tests for FT-011 SQLAlchemy unit of work."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.features.post_trade.persistence.repositories import (
    SqlAlchemyExitReviewRepository,
    SqlAlchemyExitReviewVersionRepository,
    SqlAlchemyPostTradeObservationRepository,
)
from app.features.post_trade.persistence.unit_of_work import (
    SqlAlchemyPostTradeLearningUnitOfWork,
)


def test_uow_builds_ft011_repositories() -> None:
    session = MagicMock()

    uow = SqlAlchemyPostTradeLearningUnitOfWork(session)

    assert isinstance(
        uow.observations,
        SqlAlchemyPostTradeObservationRepository,
    )
    assert isinstance(
        uow.exit_reviews,
        SqlAlchemyExitReviewRepository,
    )
    assert isinstance(
        uow.exit_review_versions,
        SqlAlchemyExitReviewVersionRepository,
    )


@pytest.mark.asyncio
async def test_uow_flush_delegates_to_session() -> None:
    session = MagicMock()
    session.flush = AsyncMock()

    uow = SqlAlchemyPostTradeLearningUnitOfWork(session)

    await uow.flush()

    session.flush.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_uow_commit_delegates_to_session() -> None:
    session = MagicMock()
    session.commit = AsyncMock()

    uow = SqlAlchemyPostTradeLearningUnitOfWork(session)

    await uow.commit()

    session.commit.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_uow_rollback_delegates_to_session() -> None:
    session = MagicMock()
    session.rollback = AsyncMock()

    uow = SqlAlchemyPostTradeLearningUnitOfWork(session)

    await uow.rollback()

    session.rollback.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_uow_rolls_back_on_context_exception() -> None:
    session = MagicMock()
    session.rollback = AsyncMock()

    uow = SqlAlchemyPostTradeLearningUnitOfWork(session)

    await uow.__aexit__(
        RuntimeError,
        RuntimeError("boom"),
        None,
    )

    session.rollback.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_uow_does_not_rollback_successful_context() -> None:
    session = MagicMock()
    session.rollback = AsyncMock()

    uow = SqlAlchemyPostTradeLearningUnitOfWork(session)

    await uow.__aexit__(None, None, None)

    session.rollback.assert_not_awaited()
