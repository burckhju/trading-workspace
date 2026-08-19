"""Unit-of-work contract and SQLAlchemy implementation for FT-011."""

from __future__ import annotations

from types import TracebackType
from typing import Protocol, Self

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.post_trade.persistence.repositories import (
    ExitReviewRepository,
    ExitReviewVersionRepository,
    PostTradeObservationRepository,
    SqlAlchemyExitReviewRepository,
    SqlAlchemyExitReviewVersionRepository,
    SqlAlchemyPostTradeObservationRepository,
)


class PostTradeLearningUnitOfWork(Protocol):
    observations: PostTradeObservationRepository
    exit_reviews: ExitReviewRepository
    exit_review_versions: ExitReviewVersionRepository

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    async def flush(self) -> None: ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...


class SqlAlchemyPostTradeLearningUnitOfWork:
    observations: PostTradeObservationRepository
    exit_reviews: ExitReviewRepository
    exit_review_versions: ExitReviewVersionRepository

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.observations = SqlAlchemyPostTradeObservationRepository(session)
        self.exit_reviews = SqlAlchemyExitReviewRepository(session)
        self.exit_review_versions = SqlAlchemyExitReviewVersionRepository(
            session,
            self.exit_reviews,
        )

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()

    async def flush(self) -> None:
        await self._session.flush()

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
