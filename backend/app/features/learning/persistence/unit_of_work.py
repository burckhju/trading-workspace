"""TradeLink unit-of-work foundation for FT-012 Learning."""

from __future__ import annotations

from types import TracebackType
from typing import Protocol, Self

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.learning.persistence.repositories import (
    ExternalObservationRepository,
    ExternalObservationTradeLinkRepository,
    ExternalObservationTradeLinkVersionRepository,
    ExternalObservationVersionRepository,
    IdempotencyRecordRepository,
    LearningEvidenceRepository,
    LessonEvidenceLinkRepository,
    LessonRepository,
    LessonReviewSignalRepository,
    LessonStateTransitionRepository,
    LessonSuggestionRepository,
    LessonTagRepository,
    LessonVersionRepository,
    SqlAlchemyExternalObservationRepository,
    SqlAlchemyExternalObservationTradeLinkRepository,
    SqlAlchemyExternalObservationTradeLinkVersionRepository,
    SqlAlchemyExternalObservationVersionRepository,
    SqlAlchemyIdempotencyRecordRepository,
    SqlAlchemyLearningEvidenceRepository,
    SqlAlchemyLessonEvidenceLinkRepository,
    SqlAlchemyLessonRepository,
    SqlAlchemyLessonReviewSignalRepository,
    SqlAlchemyLessonStateTransitionRepository,
    SqlAlchemyLessonSuggestionRepository,
    SqlAlchemyLessonTagRepository,
    SqlAlchemyLessonVersionRepository,
)


class LearningTradeLinkUnitOfWork(Protocol):
    lesson_evidence_links: LessonEvidenceLinkRepository
    lesson_state_transitions: LessonStateTransitionRepository
    lesson_review_signals: LessonReviewSignalRepository
    lesson_suggestions: LessonSuggestionRepository
    lesson_tags: LessonTagRepository
    lesson_versions: LessonVersionRepository
    lessons: LessonRepository
    learning_evidence: LearningEvidenceRepository
    idempotency_records: IdempotencyRecordRepository
    external_observations: ExternalObservationRepository
    external_observation_versions: ExternalObservationVersionRepository
    external_observation_trade_links: ExternalObservationTradeLinkRepository
    external_observation_trade_link_versions: ExternalObservationTradeLinkVersionRepository

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


class SqlAlchemyLearningTradeLinkUnitOfWork:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.lessons = SqlAlchemyLessonRepository(session)
        self.lesson_versions = SqlAlchemyLessonVersionRepository(session)
        self.lesson_evidence_links = SqlAlchemyLessonEvidenceLinkRepository(session)
        self.lesson_state_transitions = SqlAlchemyLessonStateTransitionRepository(session)
        self.lesson_review_signals = SqlAlchemyLessonReviewSignalRepository(session)
        self.lesson_suggestions = SqlAlchemyLessonSuggestionRepository(session)
        self.lesson_tags = SqlAlchemyLessonTagRepository(session)
        self.learning_evidence = SqlAlchemyLearningEvidenceRepository(session)
        self.external_observations = SqlAlchemyExternalObservationRepository(session)
        self.external_observation_versions = SqlAlchemyExternalObservationVersionRepository(session)
        self.idempotency_records = SqlAlchemyIdempotencyRecordRepository(session)
        self.external_observation_trade_links = SqlAlchemyExternalObservationTradeLinkRepository(
            session
        )
        self.external_observation_trade_link_versions = (
            SqlAlchemyExternalObservationTradeLinkVersionRepository(
                session,
                self.external_observation_trade_links,
            )
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
