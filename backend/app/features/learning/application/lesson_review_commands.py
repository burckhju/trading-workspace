"""Explicit FT-012 review commands composing existing owners in one transaction."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import StrEnum
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.features.learning.application.lesson_review_service import LessonReviewService
from app.features.learning.application.lesson_service import (
    Clock,
    IdFactory,
    LessonEvidenceInput,
    LessonService,
)
from app.features.learning.domain import IdempotencyRecord, IdempotencyStatus, LessonState
from app.features.learning.persistence.unit_of_work import LearningTradeLinkUnitOfWork


class ReviewOperation(StrEnum):
    OPEN_SOURCE_REVIEW = "OPEN_SOURCE_REVIEW"
    OPEN_CONTRADICTION_REVIEW = "OPEN_CONTRADICTION_REVIEW"
    CONFIRM_UNCHANGED = "CONFIRM_UNCHANGED"
    NEW_VERSION = "NEW_VERSION"
    RETIRE = "RETIRE"


class ReviewCommandError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class LessonReviewCommand:
    operation: ReviewOperation
    expected_current_version_id: UUID
    expected_current_state: LessonState
    expected_open_signal_id: UUID | None
    reason: str
    reviewed_evidence_ids: tuple[UUID, ...] = ()
    contradiction_link_ids: tuple[UUID, ...] = ()
    main_category: str | None = None
    content: str | None = None
    evidence: tuple[LessonEvidenceInput, ...] = ()


@dataclass(frozen=True, slots=True)
class LessonReviewReceipt:
    lesson_id: UUID
    result_id: UUID
    result_type: str
    replayed: bool


class LessonReviewCommands:
    def __init__(
        self, *, uow: LearningTradeLinkUnitOfWork, clock: Clock, id_factory: IdFactory
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._ids = id_factory
        self._lessons = LessonService(uow=uow, clock=clock, id_factory=id_factory)
        self._reviews = LessonReviewService(uow=uow, clock=clock, id_factory=id_factory)

    async def execute(
        self,
        *,
        workspace_id: UUID,
        lesson_id: UUID,
        actor_id: UUID,
        idempotency_key: str,
        command: LessonReviewCommand,
    ) -> LessonReviewReceipt:
        if (
            not idempotency_key.strip()
            or len(idempotency_key) > 240
            or not command.reason.strip()
            or len(command.reason) > 200
        ):
            raise ReviewCommandError(
                "LESSON_REVIEW_INVALID", "Key and explicit reason (1-200 characters) required"
            )
        payload = {
            "workspace": workspace_id,
            "lesson": lesson_id,
            "actor": actor_id,
            **asdict(command),
        }
        fingerprint = hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode()
        ).hexdigest()
        command_type = f"LESSON_REVIEW_{command.operation.value}"
        async with self._uow:
            if not await self._uow.lessons.lock(workspace_id, lesson_id):
                raise ReviewCommandError("LESSON_NOT_FOUND", "Lesson not found in workspace")
            receipt = await self._uow.idempotency_records.get(
                workspace_id, command_type, idempotency_key
            )
            if receipt:
                if receipt.request_fingerprint != fingerprint:
                    raise ReviewCommandError("IDEMPOTENCY_KEY_REUSED", "Different command input")
                if receipt.status is not IdempotencyStatus.SUCCEEDED:
                    raise ReviewCommandError("LESSON_REVIEW_CONFLICT", "Command not completed")
                if receipt.result_id is None or receipt.result_type is None:
                    raise RuntimeError("Incomplete lesson review receipt")
                # Original result identity, never a new currentness promise or a silent rebase.
                return LessonReviewReceipt(lesson_id, receipt.result_id, receipt.result_type, True)
            lesson = await self._uow.lessons.get(workspace_id, lesson_id)
            signal = await self._uow.lesson_review_signals.get_open_for_lesson(lesson_id)
            if lesson is None or (
                lesson.current_version_id != command.expected_current_version_id
                or lesson.current_state is not command.expected_current_state
                or (signal.id if signal else None) != command.expected_open_signal_id
            ):
                raise ReviewCommandError(
                    "LESSON_REVIEW_CONFLICT", "Displayed review context changed"
                )
            try:
                result_id, result_type = await self._apply(
                    workspace_id, lesson_id, actor_id, command
                )
                record = IdempotencyRecord(
                    id=self._ids.new_uuid(),
                    workspace_id=workspace_id,
                    command_type=command_type,
                    idempotency_key=idempotency_key,
                    request_fingerprint=fingerprint,
                    status=IdempotencyStatus.IN_PROGRESS,
                    created_at=self._clock.now(),
                )
                await self._uow.idempotency_records.add(record)
                await self._uow.flush()
                await self._uow.idempotency_records.mark_succeeded(
                    record_id=record.id,
                    result_type=result_type,
                    result_id=result_id,
                    completed_at=self._clock.now(),
                )
                await self._uow.commit()
            except IntegrityError as exc:
                raise ReviewCommandError(
                    "LESSON_REVIEW_CONFLICT", "Concurrent or invalid review change"
                ) from exc
        return LessonReviewReceipt(lesson_id, result_id, result_type, False)

    async def _apply(
        self,
        workspace_id: UUID,
        lesson_id: UUID,
        actor_id: UUID,
        command: LessonReviewCommand,
    ) -> tuple[UUID, str]:
        base = dict(workspace_id=workspace_id, lesson_id=lesson_id, actor_id=actor_id)
        op = command.operation
        opening = op in {
            ReviewOperation.OPEN_SOURCE_REVIEW,
            ReviewOperation.OPEN_CONTRADICTION_REVIEW,
        }
        required = LessonState.CURRENT if opening else LessonState.REVIEW_RECOMMENDED
        if command.expected_current_state is not required:
            raise ReviewCommandError(
                "LESSON_REVIEW_CONFLICT", "Operation not allowed in this state"
            )
        if opening and command.expected_open_signal_id is not None:
            raise ReviewCommandError("LESSON_REVIEW_CONFLICT", "Review already open")
        if op is ReviewOperation.OPEN_CONTRADICTION_REVIEW:
            result = await self._reviews.open_signal(
                **base,
                contradiction_link_ids=command.contradiction_link_ids,
                review_note=command.reason,
            )
            return result.signal.id, "LESSON_REVIEW_SIGNAL"
        if op is ReviewOperation.OPEN_SOURCE_REVIEW:
            links = await self._uow.lesson_evidence_links.list_for_version(
                command.expected_current_version_id
            )
            ids = command.reviewed_evidence_ids
            if (
                not ids
                or len(set(ids)) != len(ids)
                or set(ids) != {link.learning_evidence_id for link in links}
            ):
                raise ReviewCommandError("LESSON_REVIEW_INVALID", "Select exact current evidence")
            result_state = await self._lessons.transition_state(
                **base,
                expected_state=LessonState.CURRENT,
                new_state=LessonState.REVIEW_RECOMMENDED,
                related_lesson_version_id=command.expected_current_version_id,
                reason=f"SOURCE_REVIEW_OPENED: {command.reason}",
            )
            return result_state.transition.id, "LESSON_STATE_TRANSITION"
        signal_id = command.expected_open_signal_id
        if op is ReviewOperation.NEW_VERSION:
            if command.content is None or command.main_category is None:
                raise ReviewCommandError(
                    "LESSON_REVIEW_INVALID", "Explicit interpretation required"
                )
            if signal_id is not None:
                result_version = await self._reviews.resolve_with_new_version(
                    **base,
                    signal_id=signal_id,
                    main_category=command.main_category,
                    content=command.content,
                    evidence=command.evidence,
                    review_note=command.reason,
                )
                return result_version.version.id, "LESSON_VERSION"
            created = await self._lessons.create_new_version(
                **base,
                main_category=command.main_category,
                content=command.content,
                evidence=command.evidence,
                expected_current_version_id=command.expected_current_version_id,
                expected_current_state=LessonState.REVIEW_RECOMMENDED,
            )
            await self._lessons.transition_state(
                **base,
                expected_state=LessonState.REVIEW_RECOMMENDED,
                new_state=LessonState.CURRENT,
                related_lesson_version_id=created.version.id,
                reason=f"SOURCE_REVIEW_NEW_VERSION_CREATED: {command.reason}",
            )
            return created.version.id, "LESSON_VERSION"
        if op not in {ReviewOperation.CONFIRM_UNCHANGED, ReviewOperation.RETIRE}:
            raise ReviewCommandError("LESSON_REVIEW_INVALID", "Unknown review operation")
        if signal_id is not None:
            resolve = (
                self._reviews.resolve_unchanged
                if op is ReviewOperation.CONFIRM_UNCHANGED
                else self._reviews.resolve_retired
            )
            resolved = await resolve(**base, signal_id=signal_id, review_note=command.reason)
            return resolved.id, "LESSON_REVIEW_SIGNAL"
        state = await self._lessons.transition_state(
            **base,
            expected_state=LessonState.REVIEW_RECOMMENDED,
            new_state=(
                LessonState.CURRENT
                if op is ReviewOperation.CONFIRM_UNCHANGED
                else LessonState.RETIRED
            ),
            related_lesson_version_id=command.expected_current_version_id,
            reason=f"SOURCE_REVIEW_{op.value}: {command.reason}",
        )
        return state.transition.id, "LESSON_STATE_TRANSITION"
