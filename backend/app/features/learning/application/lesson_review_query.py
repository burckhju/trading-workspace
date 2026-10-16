"""Read-only review history and exact evidence source inspection; no new truth owner."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.features.learning.application.lesson_query_service import (
    LessonQueryService,
    LessonVersionProjection,
)
from app.features.learning.application.lesson_review_commands import ReviewCommandError
from app.features.learning.application.lesson_service import Clock
from app.features.learning.domain import (
    ExternalObservationEvidence,
    ExternalObservationJournalVersionEvidence,
    FT011Evidence,
    JournalVersionStatus,
    Lesson,
    LessonReviewSignal,
    LessonStateTransition,
    TradeJournalVersionEvidence,
)
from app.features.learning.persistence.unit_of_work import LearningTradeLinkUnitOfWork
from app.features.post_trade.domain import ExitReviewCurrentness


class Inspector(Protocol):
    async def inspect_version_currentness(
        self, *, workspace_id: UUID, version_id: UUID
    ) -> ExitReviewCurrentness | None: ...


@dataclass(frozen=True, slots=True)
class ReviewSignalView:
    signal: LessonReviewSignal
    trigger_link_ids: tuple[UUID, ...]


@dataclass(frozen=True, slots=True)
class LessonReviewContext:
    lesson: Lesson
    history: tuple[LessonVersionProjection, ...]
    signals: tuple[ReviewSignalView, ...]
    transitions: tuple[LessonStateTransition, ...]
    read_at: datetime


@dataclass(frozen=True, slots=True)
class EvidenceSourceInspection:
    evidence_id: UUID
    source_type: str
    source_version_id: UUID
    source_currentness: str
    review_currentness: str | None
    superseded_by_version_id: UUID | None
    checked_at: datetime


class LessonReviewQuery:
    def __init__(self, *, uow: LearningTradeLinkUnitOfWork, inspector: Inspector, clock: Clock):
        self._uow, self._inspector, self._clock = uow, inspector, clock

    async def context(self, *, workspace_id: UUID, lesson_id: UUID) -> LessonReviewContext:
        lesson = await self._uow.lessons.get(workspace_id, lesson_id)
        if lesson is None:
            raise ReviewCommandError("LESSON_NOT_FOUND", "Lesson not found")
        history = await LessonQueryService(uow=self._uow).history(
            workspace_id=workspace_id, lesson_id=lesson_id
        )
        signals = await self._uow.lesson_review_signals.list_for_lesson(lesson_id)
        views = []
        for signal in signals:
            links = await self._uow.lesson_review_signals.list_trigger_link_ids(signal.id)
            views.append(ReviewSignalView(signal, tuple(links)))
        return LessonReviewContext(
            lesson,
            tuple(sorted(history or (), key=lambda entry: entry.version.version, reverse=True)),
            tuple(views),
            tuple(await self._uow.lesson_state_transitions.list_for_lesson(lesson_id)),
            self._clock.now(),
        )

    async def source(self, *, workspace_id: UUID, evidence_id: UUID) -> EvidenceSourceInspection:
        projection = await self._uow.learning_evidence.get(workspace_id, evidence_id)
        if projection is None:
            raise ReviewCommandError("LEARNING_EVIDENCE_NOT_FOUND", "Evidence not found")
        source = projection.source
        state, review_state, successor = "UNKNOWN", None, None
        if isinstance(source, FT011Evidence):
            version_id = source.exit_review_version_id
            checked = await self._inspector.inspect_version_currentness(
                workspace_id=workspace_id, version_id=version_id
            )
            state = checked.value if checked else "UNKNOWN"
        elif isinstance(source, TradeJournalVersionEvidence):
            version_id = source.trade_journal_version_id
            journal = await self._uow.journals.origin(workspace_id, version_id)
            if journal:
                versions = await self._uow.journals.versions(journal.id)
                version = next((v for v in versions if v.id == version_id), None)
                if version and version.status is JournalVersionStatus.FINALIZED:
                    finals = [
                        v
                        for v in versions
                        if v.status is JournalVersionStatus.FINALIZED
                        and v.version > version.version
                    ]
                    successor = max(finals, key=lambda v: v.version).id if finals else None
                    state = "SUPERSEDED" if successor else "CURRENT"
                    review_state = "UNKNOWN"
                    if version.source_exit_review_version_id:
                        checked = await self._inspector.inspect_version_currentness(
                            workspace_id=workspace_id,
                            version_id=version.source_exit_review_version_id,
                        )
                        review_state = checked.value if checked else "UNKNOWN"
        elif isinstance(source, ExternalObservationEvidence):
            version_id = source.external_observation_version_id
            external_version = await self._uow.external_observation_versions.get(version_id)
            if external_version and await self._uow.external_observations.get(
                workspace_id, external_version.external_observation_id
            ):
                current = await self._uow.external_observation_versions.get_current(
                    external_version.external_observation_id
                )
                if current:
                    state = "CURRENT" if current.id == version_id else "SUPERSEDED"
                    successor = current.id if current.id != version_id else None
        elif isinstance(source, ExternalObservationJournalVersionEvidence):
            version_id = source.external_observation_journal_version_id
            # No qualified current-source reader exists for external journals in this slice.
        else:
            raise RuntimeError("Unknown evidence source type")
        return EvidenceSourceInspection(
            evidence_id,
            projection.evidence.evidence_type.value,
            version_id,
            state,
            review_state,
            successor,
            self._clock.now(),
        )
