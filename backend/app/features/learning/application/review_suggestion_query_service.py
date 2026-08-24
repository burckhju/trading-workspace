from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.features.learning.domain import (
    LessonReviewSignal,
    LessonSuggestion,
    LessonTag,
)
from app.features.learning.persistence.unit_of_work import LearningTradeLinkUnitOfWork


@dataclass(frozen=True, slots=True)
class LessonReviewSignalProjection:
    signal: LessonReviewSignal
    trigger_evidence_link_ids: tuple[UUID, ...]


@dataclass(frozen=True, slots=True)
class ReviewSuggestionQueryService:
    uow: LearningTradeLinkUnitOfWork

    async def list_review_signals(
        self,
        *,
        workspace_id: UUID,
        lesson_id: UUID,
    ) -> tuple[LessonReviewSignal, ...]:
        lesson = await self.uow.lessons.get(workspace_id, lesson_id)
        if lesson is None:
            return ()
        return tuple(await self.uow.lesson_review_signals.list_for_lesson(lesson_id))

    async def list_review_signal_projections(
        self,
        *,
        workspace_id: UUID,
        lesson_id: UUID,
    ) -> tuple[LessonReviewSignalProjection, ...]:
        lesson = await self.uow.lessons.get(workspace_id, lesson_id)
        if lesson is None:
            return ()

        signals = tuple(await self.uow.lesson_review_signals.list_for_lesson(lesson_id))
        result: list[LessonReviewSignalProjection] = []

        for signal in signals:
            trigger_ids = tuple(
                await self.uow.lesson_review_signals.list_trigger_link_ids(signal.id)
            )
            result.append(
                LessonReviewSignalProjection(
                    signal=signal,
                    trigger_evidence_link_ids=trigger_ids,
                )
            )

        return tuple(result)

    async def get_suggestion(
        self,
        *,
        workspace_id: UUID,
        suggestion_id: UUID,
    ) -> LessonSuggestion | None:
        return await self.uow.lesson_suggestions.get(
            workspace_id,
            suggestion_id,
        )

    async def list_suggestions(
        self,
        *,
        workspace_id: UUID,
    ) -> tuple[LessonSuggestion, ...]:
        return tuple(await self.uow.lesson_suggestions.list_for_workspace(workspace_id))

    async def list_tags(
        self,
        *,
        workspace_id: UUID,
    ) -> tuple[LessonTag, ...]:
        return tuple(await self.uow.lesson_tags.list_for_workspace(workspace_id))
