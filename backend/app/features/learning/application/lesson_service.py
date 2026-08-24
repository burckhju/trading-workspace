"""FT-012 Lesson application service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from app.features.learning.domain import (
    Lesson,
    LessonEvidenceLink,
    LessonEvidenceRelation,
    LessonState,
    LessonStateTransition,
    LessonTag,
    LessonVersion,
)
from app.features.learning.persistence.unit_of_work import (
    LearningTradeLinkUnitOfWork,
)


class LessonErrorCode(StrEnum):
    LESSON_INVALID = "LESSON_INVALID"
    LESSON_STATE_TRANSITION_INVALID = "LESSON_STATE_TRANSITION_INVALID"
    CONCURRENT_MODIFICATION = "CONCURRENT_MODIFICATION"
    LESSON_NOT_FOUND = "LESSON_NOT_FOUND"
    LESSON_EVIDENCE_REQUIRED = "LESSON_EVIDENCE_REQUIRED"
    LESSON_SUPPORTING_EVIDENCE_REQUIRED = "LESSON_SUPPORTING_EVIDENCE_REQUIRED"
    LEARNING_EVIDENCE_NOT_FOUND = "LEARNING_EVIDENCE_NOT_FOUND"


class LessonServiceError(Exception):
    def __init__(self, code: LessonErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


class Clock(Protocol):
    def now(self) -> datetime: ...


class IdFactory(Protocol):
    def new_uuid(self) -> UUID: ...


@dataclass(frozen=True, slots=True)
class LessonEvidenceInput:
    learning_evidence_id: UUID
    relation: LessonEvidenceRelation


@dataclass(frozen=True, slots=True)
class CreateLessonResult:
    lesson: Lesson
    version: LessonVersion
    evidence_links: tuple[LessonEvidenceLink, ...]


@dataclass(frozen=True, slots=True)
class CreateLessonVersionResult:
    lesson: Lesson
    version: LessonVersion
    evidence_links: tuple[LessonEvidenceLink, ...]


@dataclass(frozen=True, slots=True)
class TransitionLessonStateResult:
    lesson: Lesson
    transition: LessonStateTransition


def _normalize_tag_name(value: str) -> tuple[str, str]:
    display = " ".join(value.strip().split())
    normalized = display.casefold()
    if not normalized:
        raise LessonServiceError(
            LessonErrorCode.LESSON_INVALID,
            "lesson tag must be nonblank",
        )
    return display, normalized


class LessonService:
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

    async def update_title(
        self,
        *,
        workspace_id: UUID,
        lesson_id: UUID,
        title: str,
        actor_id: UUID,
    ) -> Lesson:
        lesson = await self._uow.lessons.get(workspace_id, lesson_id)
        if lesson is None:
            raise LessonServiceError(
                LessonErrorCode.LESSON_NOT_FOUND,
                "lesson not found",
            )

        now = self._clock.now()
        await self._uow.lessons.update_title(
            lesson_id=lesson_id,
            workspace_id=workspace_id,
            title=title,
            updated_at=now,
            updated_by=actor_id,
        )
        await self._uow.flush()

        return Lesson(
            id=lesson.id,
            workspace_id=lesson.workspace_id,
            title=title,
            current_version_id=lesson.current_version_id,
            current_state=lesson.current_state,
            created_at=lesson.created_at,
            created_by=lesson.created_by,
            updated_at=now,
            updated_by=actor_id,
        )

    async def create_new_version(
        self,
        *,
        workspace_id: UUID,
        lesson_id: UUID,
        main_category: str,
        content: str,
        evidence: tuple[LessonEvidenceInput, ...],
        expected_current_version_id: UUID,
        expected_current_state: LessonState,
        actor_id: UUID,
    ) -> CreateLessonVersionResult:
        if not evidence:
            raise LessonServiceError(
                LessonErrorCode.LESSON_EVIDENCE_REQUIRED,
                "lesson version requires evidence",
            )
        if not any(item.relation is LessonEvidenceRelation.SUPPORTS for item in evidence):
            raise LessonServiceError(
                LessonErrorCode.LESSON_SUPPORTING_EVIDENCE_REQUIRED,
                "lesson version requires at least one supporting evidence link",
            )

        locked = await self._uow.lessons.lock(workspace_id, lesson_id)
        if not locked:
            raise LessonServiceError(
                LessonErrorCode.LESSON_NOT_FOUND,
                "lesson not found",
            )

        lesson = await self._uow.lessons.get(workspace_id, lesson_id)
        if lesson is None:
            raise LessonServiceError(
                LessonErrorCode.LESSON_NOT_FOUND,
                "lesson not found",
            )

        if (
            lesson.current_version_id != expected_current_version_id
            or lesson.current_state is not expected_current_state
        ):
            raise LessonServiceError(
                LessonErrorCode.CONCURRENT_MODIFICATION,
                "lesson current projection changed",
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
                raise LessonServiceError(
                    LessonErrorCode.LEARNING_EVIDENCE_NOT_FOUND,
                    "learning evidence not found in workspace",
                )

        next_number = await self._uow.lesson_versions.next_version_number(
            workspace_id,
            lesson_id,
        )
        now = self._clock.now()
        version_id = self._id_factory.new_uuid()

        version = LessonVersion(
            id=version_id,
            lesson_id=lesson_id,
            version=next_number,
            main_category=main_category,
            content=content,
            created_at=now,
            created_by=actor_id,
            supersedes_version_id=expected_current_version_id,
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

        await self._uow.lesson_versions.add(version)
        await self._uow.lesson_evidence_links.add_snapshot(version_id, links)

        advanced = await self._uow.lessons.advance_current(
            lesson_id=lesson_id,
            expected_current_version_id=expected_current_version_id,
            new_current_version_id=version_id,
            expected_current_state=expected_current_state,
            new_current_state=expected_current_state,
            updated_at=now,
            updated_by=actor_id,
        )
        if not advanced:
            raise LessonServiceError(
                LessonErrorCode.CONCURRENT_MODIFICATION,
                "lesson current projection changed",
            )

        await self._uow.flush()

        updated_lesson = Lesson(
            id=lesson.id,
            workspace_id=lesson.workspace_id,
            title=lesson.title,
            current_version_id=version_id,
            current_state=expected_current_state,
            created_at=lesson.created_at,
            created_by=lesson.created_by,
            updated_at=now,
            updated_by=actor_id,
        )
        return CreateLessonVersionResult(
            lesson=updated_lesson,
            version=version,
            evidence_links=links,
        )

    async def transition_state(
        self,
        *,
        workspace_id: UUID,
        lesson_id: UUID,
        expected_state: LessonState,
        new_state: LessonState,
        reason: str,
        related_lesson_version_id: UUID | None,
        actor_id: UUID,
    ) -> TransitionLessonStateResult:
        allowed = {
            (LessonState.CURRENT, LessonState.REVIEW_RECOMMENDED),
            (LessonState.REVIEW_RECOMMENDED, LessonState.CURRENT),
            (LessonState.REVIEW_RECOMMENDED, LessonState.RETIRED),
            (LessonState.RETIRED, LessonState.CURRENT),
        }
        if (expected_state, new_state) not in allowed:
            raise LessonServiceError(
                LessonErrorCode.LESSON_STATE_TRANSITION_INVALID,
                "invalid lesson state transition",
            )
        if (
            expected_state is LessonState.RETIRED
            and new_state is LessonState.CURRENT
            and related_lesson_version_id is None
        ):
            raise LessonServiceError(
                LessonErrorCode.LESSON_STATE_TRANSITION_INVALID,
                "retired lesson requires a new version for reactivation",
            )

        locked = await self._uow.lessons.lock(workspace_id, lesson_id)
        if not locked:
            raise LessonServiceError(
                LessonErrorCode.LESSON_NOT_FOUND,
                "lesson not found",
            )

        lesson = await self._uow.lessons.get(workspace_id, lesson_id)
        if lesson is None:
            raise LessonServiceError(
                LessonErrorCode.LESSON_NOT_FOUND,
                "lesson not found",
            )
        if lesson.current_state is not expected_state:
            raise LessonServiceError(
                LessonErrorCode.CONCURRENT_MODIFICATION,
                "lesson current state changed",
            )

        now = self._clock.now()
        transition = LessonStateTransition(
            id=self._id_factory.new_uuid(),
            lesson_id=lesson_id,
            from_state=expected_state,
            to_state=new_state,
            reason=reason,
            occurred_at=now,
            occurred_by=actor_id,
            related_lesson_version_id=related_lesson_version_id,
        )
        await self._uow.lesson_state_transitions.add(transition)

        changed = await self._uow.lessons.transition_state(
            lesson_id=lesson_id,
            expected_state=expected_state,
            new_state=new_state,
            updated_at=now,
            updated_by=actor_id,
        )
        if not changed:
            raise LessonServiceError(
                LessonErrorCode.CONCURRENT_MODIFICATION,
                "lesson current state changed",
            )

        await self._uow.flush()

        updated_lesson = Lesson(
            id=lesson.id,
            workspace_id=lesson.workspace_id,
            title=lesson.title,
            current_version_id=lesson.current_version_id,
            current_state=new_state,
            created_at=lesson.created_at,
            created_by=lesson.created_by,
            updated_at=now,
            updated_by=actor_id,
        )
        return TransitionLessonStateResult(
            lesson=updated_lesson,
            transition=transition,
        )

    async def replace_tags(
        self,
        *,
        workspace_id: UUID,
        lesson_id: UUID,
        tags: tuple[str, ...],
        actor_id: UUID,
    ) -> tuple[LessonTag, ...]:
        lesson = await self._uow.lessons.get(workspace_id, lesson_id)
        if lesson is None:
            raise LessonServiceError(
                LessonErrorCode.LESSON_NOT_FOUND,
                "lesson not found",
            )

        requested_by_normalized: dict[str, str] = {}
        for raw in tags:
            display, normalized = _normalize_tag_name(raw)
            requested_by_normalized.setdefault(normalized, display)

        now = self._clock.now()
        requested_tags: list[LessonTag] = []
        for normalized in sorted(requested_by_normalized):
            tag = await self._uow.lesson_tags.get_by_normalized_name(
                workspace_id,
                normalized,
            )
            if tag is None:
                tag = LessonTag(
                    id=self._id_factory.new_uuid(),
                    workspace_id=workspace_id,
                    name=requested_by_normalized[normalized],
                    normalized_name=normalized,
                    created_at=now,
                    created_by=actor_id,
                )
                await self._uow.lesson_tags.add(tag)
            requested_tags.append(tag)

        existing = tuple(await self._uow.lesson_tags.list_for_lesson(lesson_id))
        existing_ids = {tag.id for tag in existing}
        requested_ids = {tag.id for tag in requested_tags}

        for tag in requested_tags:
            if tag.id not in existing_ids:
                await self._uow.lesson_tags.assign(
                    lesson_id=lesson_id,
                    tag_id=tag.id,
                    assigned_at=now,
                    assigned_by=actor_id,
                )

        for tag in existing:
            if tag.id not in requested_ids:
                await self._uow.lesson_tags.unassign(
                    lesson_id=lesson_id,
                    tag_id=tag.id,
                )

        await self._uow.flush()
        return tuple(requested_tags)

    async def create(
        self,
        *,
        workspace_id: UUID,
        title: str,
        main_category: str,
        content: str,
        evidence: tuple[LessonEvidenceInput, ...],
        actor_id: UUID,
    ) -> CreateLessonResult:
        if not evidence:
            raise LessonServiceError(
                LessonErrorCode.LESSON_EVIDENCE_REQUIRED,
                "lesson requires evidence",
            )
        if not any(item.relation is LessonEvidenceRelation.SUPPORTS for item in evidence):
            raise LessonServiceError(
                LessonErrorCode.LESSON_SUPPORTING_EVIDENCE_REQUIRED,
                "lesson requires at least one supporting evidence link",
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
                raise LessonServiceError(
                    LessonErrorCode.LEARNING_EVIDENCE_NOT_FOUND,
                    "learning evidence not found in workspace",
                )

        now = self._clock.now()
        lesson_id = self._id_factory.new_uuid()
        version_id = self._id_factory.new_uuid()

        lesson = Lesson(
            id=lesson_id,
            workspace_id=workspace_id,
            title=title,
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
            main_category=main_category,
            content=content,
            created_at=now,
            created_by=actor_id,
            supersedes_version_id=None,
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

        await self._uow.lessons.add(lesson)
        await self._uow.lesson_versions.add(version)
        for link in links:
            await self._uow.lesson_evidence_links.add(link)
        await self._uow.flush()

        return CreateLessonResult(
            lesson=lesson,
            version=version,
            evidence_links=links,
        )
