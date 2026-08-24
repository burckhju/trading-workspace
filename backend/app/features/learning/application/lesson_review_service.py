from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from app.features.learning.application.lesson_service import (
    LessonEvidenceInput,
)
from app.features.learning.domain import (
    LessonEvidenceLink,
    LessonEvidenceRelation,
    LessonReviewResolution,
    LessonReviewSignal,
    LessonReviewSignalEvidence,
    LessonReviewSignalStatus,
    LessonState,
    LessonStateTransition,
    LessonVersion,
)
from app.features.learning.persistence.unit_of_work import (
    LearningTradeLinkUnitOfWork,
)


class Clock(Protocol):
    def now(self) -> datetime: ...


class IdFactory(Protocol):
    def new_uuid(self) -> UUID: ...


class LessonReviewErrorCode(StrEnum):
    LESSON_NOT_FOUND = "LESSON_NOT_FOUND"
    REVIEW_SIGNAL_ALREADY_OPEN = "REVIEW_SIGNAL_ALREADY_OPEN"
    REVIEW_SIGNAL_NOT_FOUND = "REVIEW_SIGNAL_NOT_FOUND"
    REVIEW_SIGNAL_NOT_OPEN = "REVIEW_SIGNAL_NOT_OPEN"
    INVALID_REVIEW_TRIGGER = "INVALID_REVIEW_TRIGGER"
    CONCURRENT_MODIFICATION = "CONCURRENT_MODIFICATION"


class LessonReviewServiceError(Exception):
    def __init__(self, code: LessonReviewErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class ResolveReviewWithNewVersionResult:
    signal: LessonReviewSignal
    version: LessonVersion
    evidence_links: tuple[LessonEvidenceLink, ...]


@dataclass(frozen=True, slots=True)
class OpenReviewSignalResult:
    signal: LessonReviewSignal


class LessonReviewService:
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

    async def open_signal(
        self,
        *,
        workspace_id: UUID,
        lesson_id: UUID,
        contradiction_link_ids: tuple[UUID, ...],
        actor_id: UUID,
    ) -> OpenReviewSignalResult:
        locked = await self._uow.lessons.lock(workspace_id, lesson_id)
        if not locked:
            raise LessonReviewServiceError(
                LessonReviewErrorCode.LESSON_NOT_FOUND,
                "lesson not found",
            )

        lesson = await self._uow.lessons.get(workspace_id, lesson_id)
        if lesson is None:
            raise LessonReviewServiceError(
                LessonReviewErrorCode.LESSON_NOT_FOUND,
                "lesson not found",
            )

        if await self._uow.lesson_review_signals.get_open_for_lesson(lesson_id):
            raise LessonReviewServiceError(
                LessonReviewErrorCode.REVIEW_SIGNAL_ALREADY_OPEN,
                "open lesson review signal already exists",
            )

        current_links = tuple(
            await self._uow.lesson_evidence_links.list_for_version(lesson.current_version_id)
        )
        by_id = {link.id: link for link in current_links}

        if not contradiction_link_ids:
            raise LessonReviewServiceError(
                LessonReviewErrorCode.INVALID_REVIEW_TRIGGER,
                "at least one contradiction trigger is required",
            )

        now = self._clock.now()
        signal_id = self._id_factory.new_uuid()
        signal = LessonReviewSignal(
            id=signal_id,
            lesson_id=lesson_id,
            lesson_version_id=lesson.current_version_id,
            status=LessonReviewSignalStatus.OPEN,
            raised_at=now,
            opened_by=actor_id,
        )

        provenance: list[LessonReviewSignalEvidence] = []
        for link_id in contradiction_link_ids:
            link = by_id.get(link_id)
            if link is None or link.relation is not LessonEvidenceRelation.CONTRADICTS:
                raise LessonReviewServiceError(
                    LessonReviewErrorCode.INVALID_REVIEW_TRIGGER,
                    "review trigger must reference current CONTRADICTS evidence",
                )
            provenance.append(
                LessonReviewSignalEvidence(
                    lesson_review_signal_id=signal_id,
                    lesson_evidence_link_id=link.id,
                    lesson_version_id=lesson.current_version_id,
                )
            )

        await self._uow.lesson_review_signals.add_open(
            signal,
            tuple(provenance),
        )

        if lesson.current_state is LessonState.CURRENT:
            transition = LessonStateTransition(
                id=self._id_factory.new_uuid(),
                lesson_id=lesson_id,
                from_state=LessonState.CURRENT,
                to_state=LessonState.REVIEW_RECOMMENDED,
                reason="REVIEW_SIGNAL_OPENED",
                related_lesson_version_id=lesson.current_version_id,
                occurred_at=now,
                occurred_by=actor_id,
            )
            await self._uow.lesson_state_transitions.add(transition)
            changed = await self._uow.lessons.transition_state(
                lesson_id=lesson_id,
                expected_state=LessonState.CURRENT,
                new_state=LessonState.REVIEW_RECOMMENDED,
                updated_at=now,
                updated_by=actor_id,
            )
            if not changed:
                raise LessonReviewServiceError(
                    LessonReviewErrorCode.CONCURRENT_MODIFICATION,
                    "lesson current state changed",
                )

        await self._uow.flush()
        return OpenReviewSignalResult(signal=signal)

    async def resolve_unchanged(
        self,
        *,
        workspace_id: UUID,
        lesson_id: UUID,
        signal_id: UUID,
        actor_id: UUID,
    ) -> LessonReviewSignal:
        locked = await self._uow.lessons.lock(workspace_id, lesson_id)
        if not locked:
            raise LessonReviewServiceError(
                LessonReviewErrorCode.LESSON_NOT_FOUND,
                "lesson not found",
            )

        lesson = await self._uow.lessons.get(workspace_id, lesson_id)
        signal = await self._uow.lesson_review_signals.get(signal_id)
        if signal is None or signal.lesson_id != lesson_id:
            raise LessonReviewServiceError(
                LessonReviewErrorCode.REVIEW_SIGNAL_NOT_FOUND,
                "review signal not found",
            )
        if signal.status is not LessonReviewSignalStatus.OPEN:
            raise LessonReviewServiceError(
                LessonReviewErrorCode.REVIEW_SIGNAL_NOT_OPEN,
                "review signal is not open",
            )
        if lesson is None or lesson.current_version_id != signal.lesson_version_id:
            raise LessonReviewServiceError(
                LessonReviewErrorCode.CONCURRENT_MODIFICATION,
                "lesson current version changed",
            )

        now = self._clock.now()
        resolved = await self._uow.lesson_review_signals.resolve(
            signal_id=signal_id,
            expected_status=LessonReviewSignalStatus.OPEN,
            resolution=LessonReviewResolution.UNCHANGED_CONFIRMED,
            resolved_at=now,
            resolved_by=actor_id,
            resulting_lesson_version_id=None,
        )
        if not resolved:
            raise LessonReviewServiceError(
                LessonReviewErrorCode.CONCURRENT_MODIFICATION,
                "review signal changed",
            )

        if lesson.current_state is LessonState.REVIEW_RECOMMENDED:
            transition = LessonStateTransition(
                id=self._id_factory.new_uuid(),
                lesson_id=lesson_id,
                from_state=LessonState.REVIEW_RECOMMENDED,
                to_state=LessonState.CURRENT,
                reason="REVIEW_UNCHANGED_CONFIRMED",
                related_lesson_version_id=lesson.current_version_id,
                occurred_at=now,
                occurred_by=actor_id,
            )
            await self._uow.lesson_state_transitions.add(transition)
            changed = await self._uow.lessons.transition_state(
                lesson_id=lesson_id,
                expected_state=LessonState.REVIEW_RECOMMENDED,
                new_state=LessonState.CURRENT,
                updated_at=now,
                updated_by=actor_id,
            )
            if not changed:
                raise LessonReviewServiceError(
                    LessonReviewErrorCode.CONCURRENT_MODIFICATION,
                    "lesson current state changed",
                )

        await self._uow.flush()
        return LessonReviewSignal(
            id=signal.id,
            lesson_id=signal.lesson_id,
            lesson_version_id=signal.lesson_version_id,
            status=LessonReviewSignalStatus.RESOLVED,
            raised_at=signal.raised_at,
            opened_by=signal.opened_by,
            resolution=LessonReviewResolution.UNCHANGED_CONFIRMED,
            resolved_at=now,
            resolved_by=actor_id,
            resulting_lesson_version_id=None,
        )

    async def resolve_with_new_version(
        self,
        *,
        workspace_id: UUID,
        lesson_id: UUID,
        signal_id: UUID,
        main_category: str,
        content: str,
        evidence: tuple[LessonEvidenceInput, ...],
        actor_id: UUID,
    ) -> ResolveReviewWithNewVersionResult:
        locked = await self._uow.lessons.lock(workspace_id, lesson_id)
        if not locked:
            raise LessonReviewServiceError(
                LessonReviewErrorCode.LESSON_NOT_FOUND,
                "lesson not found",
            )

        lesson = await self._uow.lessons.get(workspace_id, lesson_id)
        signal = await self._uow.lesson_review_signals.get(signal_id)
        if lesson is None or signal is None or signal.lesson_id != lesson_id:
            raise LessonReviewServiceError(
                LessonReviewErrorCode.REVIEW_SIGNAL_NOT_FOUND,
                "review signal not found",
            )
        if signal.status is not LessonReviewSignalStatus.OPEN:
            raise LessonReviewServiceError(
                LessonReviewErrorCode.REVIEW_SIGNAL_NOT_OPEN,
                "review signal is not open",
            )
        if (
            lesson.current_version_id != signal.lesson_version_id
            or lesson.current_state is not LessonState.REVIEW_RECOMMENDED
        ):
            raise LessonReviewServiceError(
                LessonReviewErrorCode.CONCURRENT_MODIFICATION,
                "lesson current projection changed",
            )

        if not evidence or not any(
            item.relation is LessonEvidenceRelation.SUPPORTS for item in evidence
        ):
            raise LessonReviewServiceError(
                LessonReviewErrorCode.INVALID_REVIEW_TRIGGER,
                "new lesson version requires supporting evidence",
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
                raise LessonReviewServiceError(
                    LessonReviewErrorCode.INVALID_REVIEW_TRIGGER,
                    "learning evidence not found in workspace",
                )

        next_number = await self._uow.lesson_versions.next_version_number(
            workspace_id,
            lesson_id,
        )
        now = self._clock.now()
        new_version_id = self._id_factory.new_uuid()

        version = LessonVersion(
            id=new_version_id,
            lesson_id=lesson_id,
            version=next_number,
            main_category=main_category,
            content=content,
            created_at=now,
            created_by=actor_id,
            supersedes_version_id=lesson.current_version_id,
        )
        links = tuple(
            LessonEvidenceLink(
                id=self._id_factory.new_uuid(),
                lesson_version_id=new_version_id,
                learning_evidence_id=item.learning_evidence_id,
                relation=item.relation,
                created_at=now,
                created_by=actor_id,
            )
            for item in evidence
        )

        await self._uow.lesson_versions.add(version)
        await self._uow.lesson_evidence_links.add_snapshot(
            new_version_id,
            links,
        )

        transition = LessonStateTransition(
            id=self._id_factory.new_uuid(),
            lesson_id=lesson_id,
            from_state=LessonState.REVIEW_RECOMMENDED,
            to_state=LessonState.CURRENT,
            reason="REVIEW_NEW_VERSION_CREATED",
            related_lesson_version_id=new_version_id,
            occurred_at=now,
            occurred_by=actor_id,
        )
        await self._uow.lesson_state_transitions.add(transition)

        advanced = await self._uow.lessons.advance_current(
            lesson_id=lesson_id,
            expected_current_version_id=lesson.current_version_id,
            new_current_version_id=new_version_id,
            expected_current_state=LessonState.REVIEW_RECOMMENDED,
            new_current_state=LessonState.CURRENT,
            updated_at=now,
            updated_by=actor_id,
        )
        if not advanced:
            raise LessonReviewServiceError(
                LessonReviewErrorCode.CONCURRENT_MODIFICATION,
                "lesson current projection changed",
            )

        resolved = await self._uow.lesson_review_signals.resolve(
            signal_id=signal_id,
            expected_status=LessonReviewSignalStatus.OPEN,
            resolution=LessonReviewResolution.NEW_VERSION_CREATED,
            resolved_at=now,
            resolved_by=actor_id,
            resulting_lesson_version_id=new_version_id,
        )
        if not resolved:
            raise LessonReviewServiceError(
                LessonReviewErrorCode.CONCURRENT_MODIFICATION,
                "review signal changed",
            )

        await self._uow.flush()
        resolved_signal = LessonReviewSignal(
            id=signal.id,
            lesson_id=signal.lesson_id,
            lesson_version_id=signal.lesson_version_id,
            status=LessonReviewSignalStatus.RESOLVED,
            raised_at=signal.raised_at,
            opened_by=signal.opened_by,
            resolution=LessonReviewResolution.NEW_VERSION_CREATED,
            resolved_at=now,
            resolved_by=actor_id,
            resulting_lesson_version_id=new_version_id,
        )

        return ResolveReviewWithNewVersionResult(
            signal=resolved_signal,
            version=version,
            evidence_links=links,
        )

    async def resolve_retired(
        self,
        *,
        workspace_id: UUID,
        lesson_id: UUID,
        signal_id: UUID,
        actor_id: UUID,
    ) -> LessonReviewSignal:
        locked = await self._uow.lessons.lock(workspace_id, lesson_id)
        if not locked:
            raise LessonReviewServiceError(
                LessonReviewErrorCode.LESSON_NOT_FOUND,
                "lesson not found",
            )

        lesson = await self._uow.lessons.get(workspace_id, lesson_id)
        signal = await self._uow.lesson_review_signals.get(signal_id)
        if lesson is None or signal is None or signal.lesson_id != lesson_id:
            raise LessonReviewServiceError(
                LessonReviewErrorCode.REVIEW_SIGNAL_NOT_FOUND,
                "review signal not found",
            )
        if signal.status is not LessonReviewSignalStatus.OPEN:
            raise LessonReviewServiceError(
                LessonReviewErrorCode.REVIEW_SIGNAL_NOT_OPEN,
                "review signal is not open",
            )
        if (
            lesson.current_version_id != signal.lesson_version_id
            or lesson.current_state is not LessonState.REVIEW_RECOMMENDED
        ):
            raise LessonReviewServiceError(
                LessonReviewErrorCode.CONCURRENT_MODIFICATION,
                "lesson current projection changed",
            )

        now = self._clock.now()
        transition = LessonStateTransition(
            id=self._id_factory.new_uuid(),
            lesson_id=lesson_id,
            from_state=LessonState.REVIEW_RECOMMENDED,
            to_state=LessonState.RETIRED,
            reason="REVIEW_LESSON_RETIRED",
            related_lesson_version_id=lesson.current_version_id,
            occurred_at=now,
            occurred_by=actor_id,
        )
        await self._uow.lesson_state_transitions.add(transition)

        changed = await self._uow.lessons.transition_state(
            lesson_id=lesson_id,
            expected_state=LessonState.REVIEW_RECOMMENDED,
            new_state=LessonState.RETIRED,
            updated_at=now,
            updated_by=actor_id,
        )
        if not changed:
            raise LessonReviewServiceError(
                LessonReviewErrorCode.CONCURRENT_MODIFICATION,
                "lesson current state changed",
            )

        resolved = await self._uow.lesson_review_signals.resolve(
            signal_id=signal_id,
            expected_status=LessonReviewSignalStatus.OPEN,
            resolution=LessonReviewResolution.LESSON_RETIRED,
            resolved_at=now,
            resolved_by=actor_id,
            resulting_lesson_version_id=None,
        )
        if not resolved:
            raise LessonReviewServiceError(
                LessonReviewErrorCode.CONCURRENT_MODIFICATION,
                "review signal changed",
            )

        await self._uow.flush()
        return LessonReviewSignal(
            id=signal.id,
            lesson_id=signal.lesson_id,
            lesson_version_id=signal.lesson_version_id,
            status=LessonReviewSignalStatus.RESOLVED,
            raised_at=signal.raised_at,
            opened_by=signal.opened_by,
            resolution=LessonReviewResolution.LESSON_RETIRED,
            resolved_at=now,
            resolved_by=actor_id,
            resulting_lesson_version_id=None,
        )
