"""FT-012 Lesson -> FT-013 Hypothesis handoff without automatic activation."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.learning.persistence.models import LessonModel, LessonVersionModel
from app.features.model.domain.models import Hypothesis
from app.features.model.persistence.models import HypothesisRecord
from app.features.model.service.application import ModelGovernanceService


class LessonHypothesisHandoffService:
    """Validate FT-012 provenance and delegate creation to FT-013 governance."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._governance = ModelGovernanceService(session)

    async def list_for_lesson_version(
        self,
        *,
        workspace_id: UUID,
        lesson_version_id: UUID,
    ) -> list[HypothesisRecord]:
        await self._require_lesson_version(workspace_id, lesson_version_id)
        result = await self._session.scalars(
            select(HypothesisRecord)
            .where(
                HypothesisRecord.workspace_id == workspace_id,
                HypothesisRecord.source_lesson_version_id == lesson_version_id,
            )
            .order_by(HypothesisRecord.created_at, HypothesisRecord.id)
        )
        return list(result)

    async def create_from_lesson_version(
        self,
        *,
        workspace_id: UUID,
        lesson_version_id: UUID,
        title: str,
        statement: str,
        actor: UUID,
    ) -> Hypothesis:
        await self._require_lesson_version(workspace_id, lesson_version_id)
        return await self._governance.create_hypothesis(
            workspace_id=workspace_id,
            title=title,
            statement=statement,
            evidence_ids=(),
            source_lesson_version_id=lesson_version_id,
            actor=actor,
        )

    async def _require_lesson_version(
        self,
        workspace_id: UUID,
        lesson_version_id: UUID,
    ) -> None:
        value = await self._session.scalar(
            select(LessonVersionModel.id)
            .join(LessonModel, LessonModel.id == LessonVersionModel.lesson_id)
            .where(
                LessonVersionModel.id == lesson_version_id,
                LessonModel.workspace_id == workspace_id,
            )
        )
        if value is None:
            raise ValueError("source lesson version not found")
