"""FT-012 historical evidence inventory, independent of today's handoff readiness."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.features.learning.application.ft011_materialization_service import Clock
from app.features.learning.domain import FT011Evidence
from app.features.learning.persistence.ft011_materialization_repository import (
    Ft011MaterializationRepository,
)
from app.features.learning.persistence.lesson_evidence_read_repository import (
    HistoricalLessonEvidenceReference,
)
from app.features.post_trade.application.exit_review_service import Ft011SourceInspection


class SourceInspector(Protocol):
    async def inspect_materialized_source(
        self,
        *,
        workspace_id: UUID,
        trade_id: UUID,
        observation_id: UUID,
        review_id: UUID,
        version_id: UUID,
    ) -> Ft011SourceInspection: ...


class HistoricalLessonReader(Protocol):
    async def list_version_references_for_evidence(
        self, *, workspace_id: UUID, learning_evidence_id: UUID
    ) -> tuple[HistoricalLessonEvidenceReference, ...]: ...


@dataclass(frozen=True, slots=True)
class Ft011EvidenceHistoryItem:
    learning_evidence_id: UUID
    evidence_type: str
    materialized_at: datetime
    trade_id: UUID
    post_trade_observation_id: UUID
    exit_review_id: UUID
    exit_review_version_id: UUID
    review_version: int | None
    review_status: str | None
    stored_review_currentness: str | None
    source_currentness: str
    superseded_by_version_id: UUID | None
    checked_at: datetime
    lesson_links: tuple[HistoricalLessonEvidenceReference, ...]


class Ft011EvidenceHistoryService:
    def __init__(
        self,
        *,
        repository: Ft011MaterializationRepository,
        inspector: SourceInspector,
        lessons: HistoricalLessonReader,
        clock: Clock,
    ) -> None:
        self._repository, self._inspector = repository, inspector
        self._lessons, self._clock = lessons, clock

    async def get(
        self, *, workspace_id: UUID, trade_id: UUID
    ) -> tuple[Ft011EvidenceHistoryItem, ...]:
        values = await self._repository.list_for_trade(workspace_id=workspace_id, trade_id=trade_id)
        items = []
        for value in values:
            source = value.source
            if not isinstance(source, FT011Evidence):
                raise RuntimeError("FT-011 history resolved non-FT011 evidence")
            inspection = await self._inspector.inspect_materialized_source(
                workspace_id=workspace_id,
                trade_id=source.trade_id,
                observation_id=source.post_trade_observation_id,
                review_id=source.exit_review_id,
                version_id=source.exit_review_version_id,
            )
            checked_at = self._clock.now()
            links = await self._lessons.list_version_references_for_evidence(
                workspace_id=workspace_id, learning_evidence_id=value.evidence.id
            )
            items.append(
                Ft011EvidenceHistoryItem(
                    value.evidence.id,
                    value.evidence.evidence_type.value,
                    value.evidence.created_at,
                    source.trade_id,
                    source.post_trade_observation_id,
                    source.exit_review_id,
                    source.exit_review_version_id,
                    inspection.version_number,
                    inspection.review_status,
                    inspection.stored_currentness,
                    inspection.source_currentness,
                    inspection.superseded_by_version_id,
                    checked_at,
                    links,
                )
            )
        return tuple(items)
