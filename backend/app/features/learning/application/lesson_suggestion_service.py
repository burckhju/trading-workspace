from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from app.features.learning.application.lesson_service import LessonEvidenceInput
from app.features.learning.domain import (
    Lesson,
    LessonEvidenceLink,
    LessonEvidenceRelation,
    LessonState,
    LessonStateTransition,
    LessonSuggestion,
    LessonSuggestionStatus,
    LessonVersion,
)
from app.features.learning.persistence.unit_of_work import LearningTradeLinkUnitOfWork


class Clock(Protocol):
    def now(self) -> datetime: ...


class IdFactory(Protocol):
    def new_uuid(self) -> UUID: ...


class LessonSuggestionErrorCode(StrEnum):
    LESSON_SUGGESTION_NOT_FOUND = "LESSON_SUGGESTION_NOT_FOUND"
    LESSON_SUGGESTION_ALREADY_DECIDED = "LESSON_SUGGESTION_ALREADY_DECIDED"
    LESSON_SUGGESTION_INVALID = "LESSON_SUGGESTION_INVALID"


class LessonSuggestionServiceError(Exception):
    def __init__(
        self,
        code: LessonSuggestionErrorCode,
        message: str,
    ) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class ConfirmSuggestionResult:
    suggestion: LessonSuggestion
    lesson: Lesson
    version: LessonVersion
    evidence_links: tuple[LessonEvidenceLink, ...]


class LessonSuggestionService:
    def __init__(
        self,
        *,
        uow: LearningTradeLinkUnitOfWork,
        clock: Clock,
        id_factory: IdFactory,
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._id_factory = id_factory

    async def reject(
        self,
        *,
        workspace_id: UUID,
        suggestion_id: UUID,
        actor_id: UUID,
    ) -> LessonSuggestion:
        locked = await self._uow.lesson_suggestions.lock(
            workspace_id,
            suggestion_id,
        )
        if not locked:
            raise LessonSuggestionServiceError(
                LessonSuggestionErrorCode.LESSON_SUGGESTION_NOT_FOUND,
                "lesson suggestion not found",
            )

        suggestion = await self._uow.lesson_suggestions.get(
            workspace_id,
            suggestion_id,
        )
        if suggestion is None:
            raise LessonSuggestionServiceError(
                LessonSuggestionErrorCode.LESSON_SUGGESTION_NOT_FOUND,
                "lesson suggestion not found",
            )
        if suggestion.status is not LessonSuggestionStatus.SUGGESTED:
            raise LessonSuggestionServiceError(
                LessonSuggestionErrorCode.LESSON_SUGGESTION_ALREADY_DECIDED,
                "lesson suggestion already decided",
            )

        now = self._clock.now()
        changed = await self._uow.lesson_suggestions.reject(
            suggestion_id=suggestion_id,
            expected_status=LessonSuggestionStatus.SUGGESTED,
            decided_at=now,
            decided_by=actor_id,
        )
        if not changed:
            raise LessonSuggestionServiceError(
                LessonSuggestionErrorCode.LESSON_SUGGESTION_ALREADY_DECIDED,
                "lesson suggestion already decided",
            )

        await self._uow.flush()
        return LessonSuggestion(
            id=suggestion.id,
            workspace_id=suggestion.workspace_id,
            status=LessonSuggestionStatus.REJECTED,
            proposed_title=suggestion.proposed_title,
            proposed_main_category=suggestion.proposed_main_category,
            proposed_content=suggestion.proposed_content,
            created_at=suggestion.created_at,
            created_by=suggestion.created_by,
            decided_at=now,
            decided_by=actor_id,
            resulting_lesson_id=None,
        )

    async def confirm(
        self,
        *,
        workspace_id: UUID,
        suggestion_id: UUID,
        evidence: tuple[LessonEvidenceInput, ...],
        actor_id: UUID,
        title: str | None = None,
        main_category: str | None = None,
        content: str | None = None,
    ) -> ConfirmSuggestionResult:
        locked = await self._uow.lesson_suggestions.lock(
            workspace_id,
            suggestion_id,
        )
        if not locked:
            raise LessonSuggestionServiceError(
                LessonSuggestionErrorCode.LESSON_SUGGESTION_NOT_FOUND,
                "lesson suggestion not found",
            )

        suggestion = await self._uow.lesson_suggestions.get(
            workspace_id,
            suggestion_id,
        )
        if suggestion is None:
            raise LessonSuggestionServiceError(
                LessonSuggestionErrorCode.LESSON_SUGGESTION_NOT_FOUND,
                "lesson suggestion not found",
            )
        if suggestion.status is not LessonSuggestionStatus.SUGGESTED:
            raise LessonSuggestionServiceError(
                LessonSuggestionErrorCode.LESSON_SUGGESTION_ALREADY_DECIDED,
                "lesson suggestion already decided",
            )

        resolved_title = title or suggestion.proposed_title
        resolved_category = main_category or suggestion.proposed_main_category
        resolved_content = content or suggestion.proposed_content

        if (
            not resolved_title.strip()
            or not resolved_category.strip()
            or not resolved_content.strip()
        ):
            raise LessonSuggestionServiceError(
                LessonSuggestionErrorCode.LESSON_SUGGESTION_INVALID,
                "confirmed lesson content must be nonblank",
            )

        if not evidence or not any(
            item.relation is LessonEvidenceRelation.SUPPORTS for item in evidence
        ):
            raise LessonSuggestionServiceError(
                LessonSuggestionErrorCode.LESSON_SUGGESTION_INVALID,
                "confirmed lesson requires supporting evidence",
            )

        seen: set[UUID] = set()
        for item in evidence:
            if item.learning_evidence_id in seen:
                continue
            seen.add(item.learning_evidence_id)
            projection = await self._uow.learning_evidence.get(
                workspace_id,
                item.learning_evidence_id,
            )
            if projection is None:
                raise LessonSuggestionServiceError(
                    LessonSuggestionErrorCode.LESSON_SUGGESTION_INVALID,
                    "learning evidence not found in workspace",
                )

        now = self._clock.now()
        lesson_id = self._id_factory.new_uuid()
        version_id = self._id_factory.new_uuid()

        lesson = Lesson(
            id=lesson_id,
            workspace_id=workspace_id,
            title=resolved_title,
            current_version_id=version_id,
            current_state=LessonState.CURRENT,
            created_at=now,
            created_by=actor_id,
            updated_at=now,
            updated_by=actor_id,
        )
        version = LessonVersion(
            id=version_id,
            lesson_id=lesson_id,
            version=1,
            main_category=resolved_category,
            content=resolved_content,
            created_at=now,
            created_by=actor_id,
        )
        links = tuple(
            LessonEvidenceLink(
                id=self._id_factory.new_uuid(),
                lesson_version_id=version_id,
                learning_evidence_id=item.learning_evidence_id,
                relation=item.relation,
                created_at=now,
                created_by=actor_id,
            )
            for item in evidence
        )
        initial_transition = LessonStateTransition(
            id=self._id_factory.new_uuid(),
            lesson_id=lesson_id,
            from_state=None,
            to_state=LessonState.CURRENT,
            reason="SUGGESTION_CONFIRMED",
            related_lesson_version_id=version_id,
            occurred_at=now,
            occurred_by=actor_id,
        )

        await self._uow.lessons.add(lesson)
        await self._uow.lesson_versions.add(version)
        await self._uow.lesson_evidence_links.add_snapshot(
            version_id,
            links,
        )
        await self._uow.lesson_state_transitions.add(initial_transition)

        changed = await self._uow.lesson_suggestions.confirm(
            suggestion_id=suggestion_id,
            expected_status=LessonSuggestionStatus.SUGGESTED,
            resulting_lesson_id=lesson_id,
            decided_at=now,
            decided_by=actor_id,
        )
        if not changed:
            raise LessonSuggestionServiceError(
                LessonSuggestionErrorCode.LESSON_SUGGESTION_ALREADY_DECIDED,
                "lesson suggestion already decided",
            )

        await self._uow.flush()

        confirmed = LessonSuggestion(
            id=suggestion.id,
            workspace_id=suggestion.workspace_id,
            status=LessonSuggestionStatus.CONFIRMED,
            proposed_title=suggestion.proposed_title,
            proposed_main_category=suggestion.proposed_main_category,
            proposed_content=suggestion.proposed_content,
            created_at=suggestion.created_at,
            created_by=suggestion.created_by,
            decided_at=now,
            decided_by=actor_id,
            resulting_lesson_id=lesson_id,
        )
        return ConfirmSuggestionResult(
            suggestion=confirmed,
            lesson=lesson,
            version=version,
            evidence_links=links,
        )
