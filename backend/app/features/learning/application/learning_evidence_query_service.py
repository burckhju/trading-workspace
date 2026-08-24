"""Read/query service for FT-012 Learning Evidence."""

from __future__ import annotations

from uuid import UUID

from app.features.learning.persistence.repositories import (
    LearningEvidenceProjection,
)
from app.features.learning.persistence.unit_of_work import (
    LearningTradeLinkUnitOfWork,
)


class LearningEvidenceQueryService:
    def __init__(self, *, uow: LearningTradeLinkUnitOfWork) -> None:
        self._uow = uow

    async def get(
        self,
        *,
        workspace_id: UUID,
        evidence_id: UUID,
    ) -> LearningEvidenceProjection | None:
        return await self._uow.learning_evidence.get(
            workspace_id,
            evidence_id,
        )

    async def list(
        self,
        *,
        workspace_id: UUID,
    ) -> tuple[LearningEvidenceProjection, ...]:
        return tuple(
            await self._uow.learning_evidence.list_for_workspace(
                workspace_id,
            )
        )
