"""TradeLink repository foundation for FT-012 Learning."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol, cast
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.learning.domain import (
    ExternalObservation,
    ExternalObservationEvidence,
    ExternalObservationJournalVersionEvidence,
    ExternalObservationTradeLink,
    ExternalObservationTradeLinkVersion,
    ExternalObservationVersion,
    FT011Evidence,
    IdempotencyRecord,
    IdempotencyStatus,
    LearningEvidence,
    LearningEvidenceType,
    Lesson,
    LessonEvidenceLink,
    LessonReviewResolution,
    LessonReviewSignal,
    LessonReviewSignalEvidence,
    LessonReviewSignalStatus,
    LessonState,
    LessonStateTransition,
    LessonSuggestion,
    LessonSuggestionStatus,
    LessonTag,
    LessonVersion,
    TradeJournalVersionEvidence,
    TradeLinkStatus,
)
from app.features.learning.persistence.mapping import (
    external_observation_from_model,
    external_observation_trade_link_from_model,
    external_observation_trade_link_to_model,
    external_observation_trade_link_version_from_model,
    external_observation_trade_link_version_to_model,
    external_observation_version_from_model,
    lesson_evidence_link_from_model,
    lesson_evidence_link_to_model,
    lesson_from_model,
    lesson_review_signal_evidence_to_model,
    lesson_review_signal_from_model,
    lesson_review_signal_to_model,
    lesson_state_transition_to_model,
    lesson_suggestion_from_model,
    lesson_to_model,
    lesson_version_from_model,
    lesson_version_to_model,
)
from app.features.learning.persistence.models import (
    ExternalObservationEvidenceModel,
    ExternalObservationJournalVersionEvidenceModel,
    ExternalObservationModel,
    ExternalObservationTradeLinkRecordModel,
    ExternalObservationTradeLinkVersionRecordModel,
    ExternalObservationVersionModel,
    FT011EvidenceModel,
    IdempotencyRecordModel,
    LearningEvidenceModel,
    LessonEvidenceLinkModel,
    LessonModel,
    LessonReviewSignalEvidenceRecordModel,
    LessonReviewSignalRecordModel,
    LessonSuggestionRecordModel,
    LessonTagAssignmentRecordModel,
    LessonTagRecordModel,
    LessonVersionModel,
    TradeJournalVersionEvidenceModel,
)


class LearningPersistenceError(Exception):
    """Base persistence error for FT-012."""


class PersistenceNotFoundError(LearningPersistenceError):
    """Requested root does not exist."""


class PersistenceStateConflictError(LearningPersistenceError):
    """Expected persistence state no longer matches."""


class PersistenceUniquenessConflictError(LearningPersistenceError):
    """A fachlicher uniqueness rule conflicts with existing state."""


class ExternalObservationRepository(Protocol):
    async def get(
        self,
        workspace_id: UUID,
        observation_id: UUID,
    ) -> ExternalObservation | None: ...

    async def lock(
        self,
        workspace_id: UUID,
        observation_id: UUID,
    ) -> bool: ...


class ExternalObservationVersionRepository(Protocol):
    async def get(
        self,
        version_id: UUID,
    ) -> ExternalObservationVersion | None: ...

    async def get_current(
        self,
        observation_id: UUID,
    ) -> ExternalObservationVersion | None: ...


@dataclass(frozen=True, slots=True)
class LearningEvidenceProjection:
    evidence: LearningEvidence
    source: (
        FT011Evidence
        | TradeJournalVersionEvidence
        | ExternalObservationEvidence
        | ExternalObservationJournalVersionEvidence
    )


class LessonRepository(Protocol):
    async def add(self, lesson: Lesson) -> None: ...

    async def get(
        self,
        workspace_id: UUID,
        lesson_id: UUID,
    ) -> Lesson | None: ...

    async def list_for_workspace(
        self,
        workspace_id: UUID,
    ) -> Sequence[Lesson]: ...

    async def update_title(
        self,
        *,
        lesson_id: UUID,
        workspace_id: UUID,
        title: str,
        updated_at: datetime,
        updated_by: UUID,
    ) -> None: ...

    async def lock(
        self,
        workspace_id: UUID,
        lesson_id: UUID,
    ) -> bool: ...

    async def advance_current(
        self,
        *,
        lesson_id: UUID,
        expected_current_version_id: UUID,
        new_current_version_id: UUID,
        expected_current_state: LessonState,
        new_current_state: LessonState,
        updated_at: datetime,
        updated_by: UUID,
    ) -> bool: ...

    async def transition_state(
        self,
        *,
        lesson_id: UUID,
        expected_state: LessonState,
        new_state: LessonState,
        updated_at: datetime,
        updated_by: UUID,
    ) -> bool: ...


class LessonVersionRepository(Protocol):
    async def add(self, version: LessonVersion) -> None: ...

    async def get(self, version_id: UUID) -> LessonVersion | None: ...

    async def list_for_lesson(
        self,
        lesson_id: UUID,
    ) -> Sequence[LessonVersion]: ...

    async def next_version_number(
        self,
        workspace_id: UUID,
        lesson_id: UUID,
    ) -> int: ...


class LessonEvidenceLinkRepository(Protocol):
    async def add(self, link: LessonEvidenceLink) -> None: ...

    async def list_for_version(
        self,
        lesson_version_id: UUID,
    ) -> Sequence[LessonEvidenceLink]: ...

    async def add_snapshot(
        self,
        lesson_version_id: UUID,
        links: Sequence[LessonEvidenceLink],
    ) -> None: ...


class LessonStateTransitionRepository(Protocol):
    async def add(
        self,
        transition: LessonStateTransition,
    ) -> None: ...


class LessonReviewSignalRepository(Protocol):
    async def get(
        self,
        signal_id: UUID,
    ) -> LessonReviewSignal | None: ...

    async def get_open_for_lesson(
        self,
        lesson_id: UUID,
    ) -> LessonReviewSignal | None: ...

    async def list_for_lesson(
        self,
        lesson_id: UUID,
    ) -> Sequence[LessonReviewSignal]: ...

    async def add_open(
        self,
        signal: LessonReviewSignal,
        trigger_links: Sequence[LessonReviewSignalEvidence],
    ) -> None: ...

    async def resolve(
        self,
        *,
        signal_id: UUID,
        expected_status: LessonReviewSignalStatus,
        resolution: LessonReviewResolution,
        resolved_at: datetime,
        resolved_by: UUID,
        resulting_lesson_version_id: UUID | None,
    ) -> bool: ...

    async def list_trigger_link_ids(
        self,
        signal_id: UUID,
    ) -> Sequence[UUID]: ...


class LessonSuggestionRepository(Protocol):
    async def get(
        self,
        workspace_id: UUID,
        suggestion_id: UUID,
    ) -> LessonSuggestion | None: ...

    async def lock(
        self,
        workspace_id: UUID,
        suggestion_id: UUID,
    ) -> bool: ...

    async def reject(
        self,
        *,
        suggestion_id: UUID,
        expected_status: LessonSuggestionStatus,
        decided_at: datetime,
        decided_by: UUID,
    ) -> bool: ...

    async def confirm(
        self,
        *,
        suggestion_id: UUID,
        expected_status: LessonSuggestionStatus,
        resulting_lesson_id: UUID,
        decided_at: datetime,
        decided_by: UUID,
    ) -> bool: ...

    async def list_for_workspace(
        self,
        workspace_id: UUID,
    ) -> Sequence[LessonSuggestion]: ...


class LessonTagRepository(Protocol):
    async def add(self, tag: LessonTag) -> None: ...

    async def get_by_normalized_name(
        self,
        workspace_id: UUID,
        normalized_name: str,
    ) -> LessonTag | None: ...

    async def list_for_lesson(
        self,
        lesson_id: UUID,
    ) -> Sequence[LessonTag]: ...

    async def list_for_workspace(
        self,
        workspace_id: UUID,
    ) -> Sequence[LessonTag]: ...

    async def assign(
        self,
        *,
        lesson_id: UUID,
        tag_id: UUID,
        assigned_at: datetime,
        assigned_by: UUID,
    ) -> None: ...

    async def unassign(
        self,
        *,
        lesson_id: UUID,
        tag_id: UUID,
    ) -> None: ...


class LearningEvidenceRepository(Protocol):
    async def get(
        self,
        workspace_id: UUID,
        evidence_id: UUID,
    ) -> LearningEvidenceProjection | None: ...

    async def list_for_workspace(
        self,
        workspace_id: UUID,
    ) -> Sequence[LearningEvidenceProjection]: ...


class IdempotencyRecordRepository(Protocol):
    async def get(
        self,
        workspace_id: UUID,
        command_type: str,
        idempotency_key: str,
    ) -> IdempotencyRecord | None: ...

    async def add(self, record: IdempotencyRecord) -> None: ...

    async def mark_succeeded(
        self,
        *,
        record_id: UUID,
        result_type: str,
        result_id: UUID,
        completed_at: datetime,
    ) -> None: ...

    async def mark_failed_final(
        self,
        *,
        record_id: UUID,
        completed_at: datetime,
        error_code: str,
    ) -> None: ...


class ExternalObservationTradeLinkRepository(Protocol):
    async def add(self, link: ExternalObservationTradeLink) -> None: ...

    async def get(
        self,
        workspace_id: UUID,
        link_id: UUID,
    ) -> ExternalObservationTradeLink | None: ...

    async def lock(
        self,
        workspace_id: UUID,
        link_id: UUID,
    ) -> bool: ...

    async def list_for_observation(
        self,
        workspace_id: UUID,
        observation_id: UUID,
    ) -> Sequence[ExternalObservationTradeLink]: ...

    async def advance_current(
        self,
        *,
        link_id: UUID,
        expected_current_version_id: UUID,
        new_current_version_id: UUID,
    ) -> None: ...

    async def exists_current_active_pair(
        self,
        *,
        external_observation_id: UUID,
        trade_id: UUID,
        exclude_link_id: UUID | None = None,
    ) -> bool: ...


class ExternalObservationTradeLinkVersionRepository(Protocol):
    async def add(
        self,
        version: ExternalObservationTradeLinkVersion,
    ) -> None: ...

    async def get(
        self,
        version_id: UUID,
    ) -> ExternalObservationTradeLinkVersion | None: ...

    async def list_for_link(
        self,
        link_id: UUID,
    ) -> Sequence[ExternalObservationTradeLinkVersion]: ...

    async def get_current(
        self,
        link_id: UUID,
    ) -> ExternalObservationTradeLinkVersion | None: ...

    async def get_latest(
        self,
        link_id: UUID,
    ) -> ExternalObservationTradeLinkVersion | None: ...

    async def next_version_number(
        self,
        workspace_id: UUID,
        link_id: UUID,
    ) -> int: ...


class SqlAlchemyExternalObservationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(
        self,
        workspace_id: UUID,
        observation_id: UUID,
    ) -> ExternalObservation | None:
        model = await self._session.scalar(
            select(ExternalObservationModel).where(
                ExternalObservationModel.workspace_id == workspace_id,
                ExternalObservationModel.id == observation_id,
            )
        )
        return external_observation_from_model(model) if model else None

    async def lock(
        self,
        workspace_id: UUID,
        observation_id: UUID,
    ) -> bool:
        model = await self._session.scalar(
            select(ExternalObservationModel)
            .where(
                ExternalObservationModel.workspace_id == workspace_id,
                ExternalObservationModel.id == observation_id,
            )
            .with_for_update()
        )
        return model is not None


class SqlAlchemyExternalObservationVersionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(
        self,
        version_id: UUID,
    ) -> ExternalObservationVersion | None:
        model = await self._session.get(
            ExternalObservationVersionModel,
            version_id,
        )
        return external_observation_version_from_model(model) if model else None

    async def get_current(
        self,
        observation_id: UUID,
    ) -> ExternalObservationVersion | None:
        model = await self._session.scalar(
            select(ExternalObservationVersionModel)
            .join(
                ExternalObservationModel,
                ExternalObservationModel.current_version_id == ExternalObservationVersionModel.id,
            )
            .where(
                ExternalObservationModel.id == observation_id,
                ExternalObservationVersionModel.external_observation_id == observation_id,
            )
        )
        return external_observation_version_from_model(model) if model else None


class SqlAlchemyLessonRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, lesson: Lesson) -> None:
        self._session.add(lesson_to_model(lesson))

    async def get(
        self,
        workspace_id: UUID,
        lesson_id: UUID,
    ) -> Lesson | None:
        model = await self._session.scalar(
            select(LessonModel).where(
                LessonModel.workspace_id == workspace_id,
                LessonModel.id == lesson_id,
            )
        )
        return lesson_from_model(model) if model is not None else None

    async def list_for_workspace(
        self,
        workspace_id: UUID,
    ) -> Sequence[Lesson]:
        models = (
            await self._session.scalars(
                select(LessonModel)
                .where(LessonModel.workspace_id == workspace_id)
                .order_by(LessonModel.updated_at.desc(), LessonModel.id)
            )
        ).all()
        return tuple(lesson_from_model(model) for model in models)

    async def update_title(
        self,
        *,
        lesson_id: UUID,
        workspace_id: UUID,
        title: str,
        updated_at: datetime,
        updated_by: UUID,
    ) -> None:
        model = await self._session.scalar(
            select(LessonModel).where(
                LessonModel.id == lesson_id,
                LessonModel.workspace_id == workspace_id,
            )
        )
        if model is None:
            return
        model.title = title
        model.updated_at = updated_at
        model.updated_by = updated_by

    async def lock(
        self,
        workspace_id: UUID,
        lesson_id: UUID,
    ) -> bool:
        model = await self._session.scalar(
            select(LessonModel)
            .where(
                LessonModel.workspace_id == workspace_id,
                LessonModel.id == lesson_id,
            )
            .with_for_update()
        )
        return model is not None

    async def advance_current(
        self,
        *,
        lesson_id: UUID,
        expected_current_version_id: UUID,
        new_current_version_id: UUID,
        expected_current_state: LessonState,
        new_current_state: LessonState,
        updated_at: datetime,
        updated_by: UUID,
    ) -> bool:
        model = await self._session.scalar(
            select(LessonModel)
            .where(
                LessonModel.id == lesson_id,
                LessonModel.current_version_id == expected_current_version_id,
                LessonModel.current_state == expected_current_state,
            )
            .with_for_update()
        )
        if model is None:
            return False
        model.current_version_id = new_current_version_id
        model.current_state = new_current_state
        model.updated_at = updated_at
        model.updated_by = updated_by
        return True

    async def transition_state(
        self,
        *,
        lesson_id: UUID,
        expected_state: LessonState,
        new_state: LessonState,
        updated_at: datetime,
        updated_by: UUID,
    ) -> bool:
        model = await self._session.scalar(
            select(LessonModel)
            .where(
                LessonModel.id == lesson_id,
                LessonModel.current_state == expected_state,
            )
            .with_for_update()
        )
        if model is None:
            return False
        model.current_state = new_state
        model.updated_at = updated_at
        model.updated_by = updated_by
        return True


class SqlAlchemyLessonVersionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, version: LessonVersion) -> None:
        self._session.add(lesson_version_to_model(version))

    async def get(self, version_id: UUID) -> LessonVersion | None:
        model = await self._session.get(LessonVersionModel, version_id)
        return lesson_version_from_model(model) if model is not None else None

    async def list_for_lesson(
        self,
        lesson_id: UUID,
    ) -> Sequence[LessonVersion]:
        models = (
            await self._session.scalars(
                select(LessonVersionModel)
                .where(LessonVersionModel.lesson_id == lesson_id)
                .order_by(
                    LessonVersionModel.version,
                    LessonVersionModel.id,
                )
            )
        ).all()
        return tuple(lesson_version_from_model(model) for model in models)

    async def next_version_number(
        self,
        workspace_id: UUID,
        lesson_id: UUID,
    ) -> int:
        lesson = await self._session.scalar(
            select(LessonModel).where(
                LessonModel.workspace_id == workspace_id,
                LessonModel.id == lesson_id,
            )
        )
        if lesson is None:
            return 1
        versions = (
            await self._session.scalars(
                select(LessonVersionModel).where(LessonVersionModel.lesson_id == lesson_id)
            )
        ).all()
        return max((model.version for model in versions), default=0) + 1


class SqlAlchemyLessonEvidenceLinkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, link: LessonEvidenceLink) -> None:
        self._session.add(lesson_evidence_link_to_model(link))

    async def list_for_version(
        self,
        lesson_version_id: UUID,
    ) -> Sequence[LessonEvidenceLink]:
        models = (
            await self._session.scalars(
                select(LessonEvidenceLinkModel)
                .where(LessonEvidenceLinkModel.lesson_version_id == lesson_version_id)
                .order_by(
                    LessonEvidenceLinkModel.created_at,
                    LessonEvidenceLinkModel.id,
                )
            )
        ).all()
        return tuple(lesson_evidence_link_from_model(model) for model in models)

    async def add_snapshot(
        self,
        lesson_version_id: UUID,
        links: Sequence[LessonEvidenceLink],
    ) -> None:
        for link in links:
            if link.lesson_version_id != lesson_version_id:
                raise ValueError("LessonEvidenceLink snapshot version mismatch")
            self._session.add(lesson_evidence_link_to_model(link))


class SqlAlchemyLessonStateTransitionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self,
        transition: LessonStateTransition,
    ) -> None:
        self._session.add(lesson_state_transition_to_model(transition))


class SqlAlchemyLessonReviewSignalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(
        self,
        signal_id: UUID,
    ) -> LessonReviewSignal | None:
        model = await self._session.get(
            LessonReviewSignalRecordModel,
            signal_id,
        )
        return lesson_review_signal_from_model(model) if model is not None else None

    async def get_open_for_lesson(
        self,
        lesson_id: UUID,
    ) -> LessonReviewSignal | None:
        model = await self._session.scalar(
            select(LessonReviewSignalRecordModel).where(
                LessonReviewSignalRecordModel.lesson_id == lesson_id,
                LessonReviewSignalRecordModel.status == LessonReviewSignalStatus.OPEN.value,
            )
        )
        return lesson_review_signal_from_model(model) if model is not None else None

    async def list_for_lesson(
        self,
        lesson_id: UUID,
    ) -> Sequence[LessonReviewSignal]:
        models = (
            await self._session.scalars(
                select(LessonReviewSignalRecordModel)
                .where(LessonReviewSignalRecordModel.lesson_id == lesson_id)
                .order_by(
                    LessonReviewSignalRecordModel.raised_at,
                    LessonReviewSignalRecordModel.id,
                )
            )
        ).all()
        return tuple(lesson_review_signal_from_model(model) for model in models)

    async def add_open(
        self,
        signal: LessonReviewSignal,
        trigger_links: Sequence[LessonReviewSignalEvidence],
    ) -> None:
        self._session.add(lesson_review_signal_to_model(signal))
        for link in trigger_links:
            self._session.add(lesson_review_signal_evidence_to_model(link))

    async def resolve(
        self,
        *,
        signal_id: UUID,
        expected_status: LessonReviewSignalStatus,
        resolution: LessonReviewResolution,
        resolved_at: datetime,
        resolved_by: UUID,
        resulting_lesson_version_id: UUID | None,
    ) -> bool:
        model = await self._session.scalar(
            select(LessonReviewSignalRecordModel)
            .where(
                LessonReviewSignalRecordModel.id == signal_id,
                LessonReviewSignalRecordModel.status == expected_status.value,
            )
            .with_for_update()
        )
        if model is None:
            return False

        model.status = LessonReviewSignalStatus.RESOLVED.value
        model.resolution = resolution.value
        model.resolved_at = resolved_at
        model.resolved_by = resolved_by
        model.resulting_lesson_version_id = resulting_lesson_version_id
        return True

    async def list_trigger_link_ids(
        self,
        signal_id: UUID,
    ) -> Sequence[UUID]:
        values = (
            await self._session.scalars(
                select(LessonReviewSignalEvidenceRecordModel.lesson_evidence_link_id)
                .where(LessonReviewSignalEvidenceRecordModel.lesson_review_signal_id == signal_id)
                .order_by(LessonReviewSignalEvidenceRecordModel.lesson_evidence_link_id)
            )
        ).all()
        return tuple(values)


class SqlAlchemyLessonSuggestionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(
        self,
        workspace_id: UUID,
        suggestion_id: UUID,
    ) -> LessonSuggestion | None:
        model = await self._session.scalar(
            select(LessonSuggestionRecordModel).where(
                LessonSuggestionRecordModel.workspace_id == workspace_id,
                LessonSuggestionRecordModel.id == suggestion_id,
            )
        )
        return lesson_suggestion_from_model(model) if model is not None else None

    async def lock(
        self,
        workspace_id: UUID,
        suggestion_id: UUID,
    ) -> bool:
        model = await self._session.scalar(
            select(LessonSuggestionRecordModel)
            .where(
                LessonSuggestionRecordModel.workspace_id == workspace_id,
                LessonSuggestionRecordModel.id == suggestion_id,
            )
            .with_for_update()
        )
        return model is not None

    async def reject(
        self,
        *,
        suggestion_id: UUID,
        expected_status: LessonSuggestionStatus,
        decided_at: datetime,
        decided_by: UUID,
    ) -> bool:
        model = await self._session.scalar(
            select(LessonSuggestionRecordModel)
            .where(
                LessonSuggestionRecordModel.id == suggestion_id,
                LessonSuggestionRecordModel.status == expected_status.value,
            )
            .with_for_update()
        )
        if model is None:
            return False
        model.status = LessonSuggestionStatus.REJECTED.value
        model.decided_at = decided_at
        model.decided_by = decided_by
        model.resulting_lesson_id = None
        return True

    async def confirm(
        self,
        *,
        suggestion_id: UUID,
        expected_status: LessonSuggestionStatus,
        resulting_lesson_id: UUID,
        decided_at: datetime,
        decided_by: UUID,
    ) -> bool:
        model = await self._session.scalar(
            select(LessonSuggestionRecordModel)
            .where(
                LessonSuggestionRecordModel.id == suggestion_id,
                LessonSuggestionRecordModel.status == expected_status.value,
            )
            .with_for_update()
        )
        if model is None:
            return False
        model.status = LessonSuggestionStatus.CONFIRMED.value
        model.decided_at = decided_at
        model.decided_by = decided_by
        model.resulting_lesson_id = resulting_lesson_id
        return True

    async def list_for_workspace(
        self,
        workspace_id: UUID,
    ) -> Sequence[LessonSuggestion]:
        models = (
            await self._session.scalars(
                select(LessonSuggestionRecordModel)
                .where(LessonSuggestionRecordModel.workspace_id == workspace_id)
                .order_by(
                    LessonSuggestionRecordModel.created_at.desc(),
                    LessonSuggestionRecordModel.id.desc(),
                )
            )
        ).all()
        return tuple(lesson_suggestion_from_model(model) for model in models)


class SqlAlchemyLessonTagRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, tag: LessonTag) -> None:
        self._session.add(
            LessonTagRecordModel(
                id=tag.id,
                workspace_id=tag.workspace_id,
                name=tag.name,
                normalized_name=tag.normalized_name,
                created_at=tag.created_at,
                created_by=tag.created_by,
            )
        )

    async def get_by_normalized_name(
        self,
        workspace_id: UUID,
        normalized_name: str,
    ) -> LessonTag | None:
        model = await self._session.scalar(
            select(LessonTagRecordModel).where(
                LessonTagRecordModel.workspace_id == workspace_id,
                LessonTagRecordModel.normalized_name == normalized_name,
            )
        )
        if model is None:
            return None
        return LessonTag(
            id=model.id,
            workspace_id=model.workspace_id,
            name=model.name,
            normalized_name=model.normalized_name,
            created_at=model.created_at,
            created_by=model.created_by,
        )

    async def list_for_lesson(
        self,
        lesson_id: UUID,
    ) -> Sequence[LessonTag]:
        models = (
            await self._session.scalars(
                select(LessonTagRecordModel)
                .join(
                    LessonTagAssignmentRecordModel,
                    LessonTagAssignmentRecordModel.lesson_tag_id == LessonTagRecordModel.id,
                )
                .where(LessonTagAssignmentRecordModel.lesson_id == lesson_id)
                .order_by(
                    LessonTagRecordModel.normalized_name,
                    LessonTagRecordModel.id,
                )
            )
        ).all()
        return tuple(
            LessonTag(
                id=model.id,
                workspace_id=model.workspace_id,
                name=model.name,
                normalized_name=model.normalized_name,
                created_at=model.created_at,
                created_by=model.created_by,
            )
            for model in models
        )

    async def assign(
        self,
        *,
        lesson_id: UUID,
        tag_id: UUID,
        assigned_at: datetime,
        assigned_by: UUID,
    ) -> None:
        current = await self._session.get(
            LessonTagAssignmentRecordModel,
            {"lesson_id": lesson_id, "lesson_tag_id": tag_id},
        )
        if current is None:
            self._session.add(
                LessonTagAssignmentRecordModel(
                    lesson_id=lesson_id,
                    lesson_tag_id=tag_id,
                    assigned_at=assigned_at,
                    assigned_by=assigned_by,
                )
            )

    async def unassign(
        self,
        *,
        lesson_id: UUID,
        tag_id: UUID,
    ) -> None:
        current = await self._session.get(
            LessonTagAssignmentRecordModel,
            {"lesson_id": lesson_id, "lesson_tag_id": tag_id},
        )
        if current is not None:
            await self._session.delete(current)

    async def list_for_workspace(
        self,
        workspace_id: UUID,
    ) -> Sequence[LessonTag]:
        models = (
            await self._session.scalars(
                select(LessonTagRecordModel)
                .where(LessonTagRecordModel.workspace_id == workspace_id)
                .order_by(
                    LessonTagRecordModel.normalized_name,
                    LessonTagRecordModel.id,
                )
            )
        ).all()

        return tuple(
            LessonTag(
                id=model.id,
                workspace_id=model.workspace_id,
                name=model.name,
                normalized_name=model.normalized_name,
                created_at=model.created_at,
                created_by=model.created_by,
            )
            for model in models
        )


class SqlAlchemyLearningEvidenceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(
        self,
        workspace_id: UUID,
        evidence_id: UUID,
    ) -> LearningEvidenceProjection | None:
        model = await self._session.scalar(
            select(LearningEvidenceModel).where(
                LearningEvidenceModel.workspace_id == workspace_id,
                LearningEvidenceModel.id == evidence_id,
            )
        )
        return await self._project(model) if model is not None else None

    async def list_for_workspace(
        self,
        workspace_id: UUID,
    ) -> Sequence[LearningEvidenceProjection]:
        models = (
            await self._session.scalars(
                select(LearningEvidenceModel)
                .where(LearningEvidenceModel.workspace_id == workspace_id)
                .order_by(
                    LearningEvidenceModel.created_at.desc(),
                    LearningEvidenceModel.id,
                )
            )
        ).all()
        return tuple([await self._project(model) for model in models])

    async def _project(
        self,
        model: LearningEvidenceModel,
    ) -> LearningEvidenceProjection:
        evidence = LearningEvidence(
            id=model.id,
            workspace_id=model.workspace_id,
            evidence_type=LearningEvidenceType(model.evidence_type),
            created_at=model.created_at,
        )

        if evidence.evidence_type is LearningEvidenceType.FT011:
            ft011_model = await self._session.get(
                FT011EvidenceModel,
                evidence.id,
            )
            if ft011_model is None:
                raise RuntimeError("FT011 evidence source row missing")

            ft011_source = FT011Evidence(
                learning_evidence_id=ft011_model.learning_evidence_id,
                trade_id=ft011_model.trade_id,
                post_trade_observation_id=ft011_model.post_trade_observation_id,
                exit_review_id=ft011_model.exit_review_id,
                exit_review_version_id=ft011_model.exit_review_version_id,
            )
            return LearningEvidenceProjection(
                evidence=evidence,
                source=ft011_source,
            )

        if evidence.evidence_type is LearningEvidenceType.TRADE_JOURNAL_VERSION:
            journal_model = await self._session.get(
                TradeJournalVersionEvidenceModel,
                evidence.id,
            )
            if journal_model is None:
                raise RuntimeError("trade journal evidence source row missing")

            journal_source = TradeJournalVersionEvidence(
                learning_evidence_id=journal_model.learning_evidence_id,
                trade_journal_version_id=journal_model.trade_journal_version_id,
            )
            return LearningEvidenceProjection(
                evidence=evidence,
                source=journal_source,
            )

        if evidence.evidence_type is LearningEvidenceType.EXTERNAL_OBSERVATION:
            observation_model = await self._session.get(
                ExternalObservationEvidenceModel,
                evidence.id,
            )
            if observation_model is None:
                raise RuntimeError("external observation evidence source row missing")

            observation_source = ExternalObservationEvidence(
                learning_evidence_id=observation_model.learning_evidence_id,
                external_observation_version_id=(observation_model.external_observation_version_id),
            )
            return LearningEvidenceProjection(
                evidence=evidence,
                source=observation_source,
            )

        journal_observation_model = await self._session.get(
            ExternalObservationJournalVersionEvidenceModel,
            evidence.id,
        )
        if journal_observation_model is None:
            raise RuntimeError("external journal evidence source row missing")

        journal_observation_source = ExternalObservationJournalVersionEvidence(
            learning_evidence_id=(journal_observation_model.learning_evidence_id),
            external_observation_journal_version_id=(
                journal_observation_model.external_observation_journal_version_id
            ),
        )
        return LearningEvidenceProjection(
            evidence=evidence,
            source=journal_observation_source,
        )


class SqlAlchemyIdempotencyRecordRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(
        self,
        workspace_id: UUID,
        command_type: str,
        idempotency_key: str,
    ) -> IdempotencyRecord | None:
        model = await self._session.scalar(
            select(IdempotencyRecordModel).where(
                IdempotencyRecordModel.workspace_id == workspace_id,
                IdempotencyRecordModel.command_type == command_type,
                IdempotencyRecordModel.idempotency_key == idempotency_key,
            )
        )
        if model is None:
            return None
        return IdempotencyRecord(
            id=model.id,
            workspace_id=model.workspace_id,
            command_type=model.command_type,
            idempotency_key=model.idempotency_key,
            request_fingerprint=model.request_fingerprint,
            status=IdempotencyStatus(model.status),
            created_at=model.created_at,
            result_type=model.result_type,
            result_id=model.result_id,
            error_code=model.error_code,
            completed_at=model.completed_at,
        )

    async def add(self, record: IdempotencyRecord) -> None:
        self._session.add(
            IdempotencyRecordModel(
                id=record.id,
                workspace_id=record.workspace_id,
                command_type=record.command_type,
                idempotency_key=record.idempotency_key,
                request_fingerprint=record.request_fingerprint,
                status=record.status.value,
                result_type=record.result_type,
                result_id=record.result_id,
                error_code=record.error_code,
                created_at=record.created_at,
                completed_at=record.completed_at,
            )
        )

    async def mark_succeeded(
        self,
        *,
        record_id: UUID,
        result_type: str,
        result_id: UUID,
        completed_at: datetime,
    ) -> None:
        model = await self._session.get(IdempotencyRecordModel, record_id)
        if model is None:
            raise LookupError("idempotency record not found")
        model.status = IdempotencyStatus.SUCCEEDED.value
        model.result_type = result_type
        model.result_id = result_id
        model.error_code = None
        model.completed_at = completed_at

    async def mark_failed_final(
        self,
        *,
        record_id: UUID,
        completed_at: datetime,
        error_code: str,
    ) -> None:
        model = await self._session.get(IdempotencyRecordModel, record_id)
        if model is None:
            raise LookupError("idempotency record not found")
        model.status = IdempotencyStatus.FAILED_FINAL.value
        model.result_type = None
        model.result_id = None
        model.error_code = error_code
        model.completed_at = completed_at


class SqlAlchemyExternalObservationTradeLinkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, link: ExternalObservationTradeLink) -> None:
        self._session.add(external_observation_trade_link_to_model(link))

    async def get(
        self,
        workspace_id: UUID,
        link_id: UUID,
    ) -> ExternalObservationTradeLink | None:
        model = await self._session.scalar(
            select(ExternalObservationTradeLinkRecordModel).where(
                ExternalObservationTradeLinkRecordModel.workspace_id == workspace_id,
                ExternalObservationTradeLinkRecordModel.id == link_id,
            )
        )
        return external_observation_trade_link_from_model(model) if model is not None else None

    async def lock(
        self,
        workspace_id: UUID,
        link_id: UUID,
    ) -> bool:
        model = await self._session.scalar(
            select(ExternalObservationTradeLinkRecordModel)
            .where(
                ExternalObservationTradeLinkRecordModel.workspace_id == workspace_id,
                ExternalObservationTradeLinkRecordModel.id == link_id,
            )
            .with_for_update()
        )
        return model is not None

    async def list_for_observation(
        self,
        workspace_id: UUID,
        observation_id: UUID,
    ) -> Sequence[ExternalObservationTradeLink]:
        models = (
            await self._session.scalars(
                select(ExternalObservationTradeLinkRecordModel)
                .where(
                    ExternalObservationTradeLinkRecordModel.workspace_id == workspace_id,
                    ExternalObservationTradeLinkRecordModel.external_observation_id
                    == observation_id,
                )
                .order_by(
                    ExternalObservationTradeLinkRecordModel.created_at,
                    ExternalObservationTradeLinkRecordModel.id,
                )
            )
        ).all()
        return tuple(external_observation_trade_link_from_model(model) for model in models)

    async def advance_current(
        self,
        *,
        link_id: UUID,
        expected_current_version_id: UUID,
        new_current_version_id: UUID,
    ) -> None:
        result = await self._session.execute(
            update(ExternalObservationTradeLinkRecordModel)
            .where(
                ExternalObservationTradeLinkRecordModel.id == link_id,
                ExternalObservationTradeLinkRecordModel.current_version_id
                == expected_current_version_id,
            )
            .values(current_version_id=new_current_version_id)
        )
        if cast(CursorResult[Any], result).rowcount != 1:
            raise PersistenceStateConflictError("trade link current version changed concurrently")

    async def exists_current_active_pair(
        self,
        *,
        external_observation_id: UUID,
        trade_id: UUID,
        exclude_link_id: UUID | None = None,
    ) -> bool:
        statement = (
            select(ExternalObservationTradeLinkRecordModel.id)
            .join(
                ExternalObservationTradeLinkVersionRecordModel,
                ExternalObservationTradeLinkVersionRecordModel.id
                == ExternalObservationTradeLinkRecordModel.current_version_id,
            )
            .where(
                ExternalObservationTradeLinkRecordModel.external_observation_id
                == external_observation_id,
                ExternalObservationTradeLinkVersionRecordModel.trade_id == trade_id,
                ExternalObservationTradeLinkVersionRecordModel.status
                == TradeLinkStatus.ACTIVE.value,
            )
            .limit(1)
        )
        if exclude_link_id is not None:
            statement = statement.where(
                ExternalObservationTradeLinkRecordModel.id != exclude_link_id
            )
        return await self._session.scalar(statement) is not None


class SqlAlchemyExternalObservationTradeLinkVersionRepository:
    def __init__(
        self,
        session: AsyncSession,
        links: ExternalObservationTradeLinkRepository,
    ) -> None:
        self._session = session
        self._links = links

    async def add(
        self,
        version: ExternalObservationTradeLinkVersion,
    ) -> None:
        self._session.add(external_observation_trade_link_version_to_model(version))

    async def get(
        self,
        version_id: UUID,
    ) -> ExternalObservationTradeLinkVersion | None:
        model = await self._session.get(
            ExternalObservationTradeLinkVersionRecordModel,
            version_id,
        )
        return (
            external_observation_trade_link_version_from_model(model) if model is not None else None
        )

    async def list_for_link(
        self,
        link_id: UUID,
    ) -> Sequence[ExternalObservationTradeLinkVersion]:
        models = (
            await self._session.scalars(
                select(ExternalObservationTradeLinkVersionRecordModel)
                .where(
                    ExternalObservationTradeLinkVersionRecordModel.external_observation_trade_link_id
                    == link_id
                )
                .order_by(
                    ExternalObservationTradeLinkVersionRecordModel.version,
                    ExternalObservationTradeLinkVersionRecordModel.id,
                )
            )
        ).all()
        return tuple(external_observation_trade_link_version_from_model(model) for model in models)

    async def get_current(
        self,
        link_id: UUID,
    ) -> ExternalObservationTradeLinkVersion | None:
        model = await self._session.scalar(
            select(ExternalObservationTradeLinkVersionRecordModel)
            .join(
                ExternalObservationTradeLinkRecordModel,
                ExternalObservationTradeLinkRecordModel.current_version_id
                == ExternalObservationTradeLinkVersionRecordModel.id,
            )
            .where(
                ExternalObservationTradeLinkRecordModel.id == link_id,
                ExternalObservationTradeLinkVersionRecordModel.external_observation_trade_link_id
                == link_id,
            )
        )
        return (
            external_observation_trade_link_version_from_model(model) if model is not None else None
        )

    async def get_latest(
        self,
        link_id: UUID,
    ) -> ExternalObservationTradeLinkVersion | None:
        model = await self._session.scalar(
            select(ExternalObservationTradeLinkVersionRecordModel)
            .where(
                ExternalObservationTradeLinkVersionRecordModel.external_observation_trade_link_id
                == link_id
            )
            .order_by(
                ExternalObservationTradeLinkVersionRecordModel.version.desc(),
                ExternalObservationTradeLinkVersionRecordModel.id,
            )
            .limit(1)
        )
        return (
            external_observation_trade_link_version_from_model(model) if model is not None else None
        )

    async def next_version_number(
        self,
        workspace_id: UUID,
        link_id: UUID,
    ) -> int:
        if not await self._links.lock(workspace_id, link_id):
            raise PersistenceNotFoundError("trade link not found")

        latest = await self._session.scalar(
            select(func.max(ExternalObservationTradeLinkVersionRecordModel.version)).where(
                ExternalObservationTradeLinkVersionRecordModel.external_observation_trade_link_id
                == link_id
            )
        )
        return int(latest or 0) + 1
