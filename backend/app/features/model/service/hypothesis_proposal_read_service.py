"""Readback for ModelChangeProposals sourced from one FT-013 Hypothesis."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.model.persistence.models import HypothesisRecord, ModelChangeProposalRecord


class HypothesisProposalReadService:
    """Project proposals for one workspace-owned hypothesis without changing governance state."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_hypothesis(
        self,
        *,
        workspace_id: UUID,
        hypothesis_id: UUID,
    ) -> list[ModelChangeProposalRecord]:
        hypothesis = await self._session.scalar(
            select(HypothesisRecord.id).where(
                HypothesisRecord.id == hypothesis_id,
                HypothesisRecord.workspace_id == workspace_id,
            )
        )
        if hypothesis is None:
            raise ValueError("hypothesis not found")

        result = await self._session.scalars(
            select(ModelChangeProposalRecord)
            .where(
                ModelChangeProposalRecord.workspace_id == workspace_id,
                ModelChangeProposalRecord.hypothesis_id == hypothesis_id,
            )
            .order_by(ModelChangeProposalRecord.created_at, ModelChangeProposalRecord.id)
        )
        return list(result)
