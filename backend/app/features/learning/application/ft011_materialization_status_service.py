"""Read-only status projection for FT-011 -> FT-012 materialization."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.features.learning.application.ft011_materialization_service import (
    Ft011HandoffReader,
)
from app.features.learning.domain import FT011Evidence
from app.features.learning.persistence.ft011_materialization_repository import (
    Ft011MaterializationRepository,
)


@dataclass(frozen=True, slots=True)
class Ft011MaterializationStatus:
    ready: bool
    reason: str
    materialized: bool
    learning_evidence_id: UUID | None = None
    exit_review_version_id: UUID | None = None


class Ft011MaterializationStatusService:
    """Project current FT-011 handoff eligibility and FT-012 materialization state."""

    def __init__(
        self,
        *,
        repository: Ft011MaterializationRepository,
        handoff_reader: Ft011HandoffReader,
    ) -> None:
        self._repository = repository
        self._handoff_reader = handoff_reader

    async def get(
        self,
        *,
        workspace_id: UUID,
        trade_id: UUID,
    ) -> Ft011MaterializationStatus:
        handoff = await self._handoff_reader.get(
            workspace_id=workspace_id,
            trade_id=trade_id,
        )
        if not handoff.ready:
            return Ft011MaterializationStatus(
                ready=False,
                reason=handoff.reason,
                materialized=False,
            )
        if handoff.exit_review_version_id is None:
            raise RuntimeError("READY FT-011 handoff requires exit_review_version_id")

        projection = await self._repository.get_by_source(
            workspace_id=workspace_id,
            exit_review_version_id=handoff.exit_review_version_id,
        )
        if projection is None:
            return Ft011MaterializationStatus(
                ready=True,
                reason=handoff.reason,
                materialized=False,
                exit_review_version_id=handoff.exit_review_version_id,
            )
        if not isinstance(projection.source, FT011Evidence):
            raise RuntimeError("FT-011 status resolved non-FT011 evidence")

        return Ft011MaterializationStatus(
            ready=True,
            reason=handoff.reason,
            materialized=True,
            learning_evidence_id=projection.evidence.id,
            exit_review_version_id=projection.source.exit_review_version_id,
        )
