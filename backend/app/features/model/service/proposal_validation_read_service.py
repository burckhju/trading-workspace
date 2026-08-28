"""Readback for validations attached to one workspace-owned FT-013 proposal."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.model.persistence.models import (
    ModelChangeProposalRecord,
    ModelValidationRecord,
)


class ProposalValidationReadService:
    """Project validations for one proposal without changing governance state."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_proposal(
        self,
        *,
        workspace_id: UUID,
        proposal_id: UUID,
    ) -> list[ModelValidationRecord]:
        proposal = await self._session.scalar(
            select(ModelChangeProposalRecord.id).where(
                ModelChangeProposalRecord.id == proposal_id,
                ModelChangeProposalRecord.workspace_id == workspace_id,
            )
        )
        if proposal is None:
            raise ValueError("model change proposal not found")

        result = await self._session.scalars(
            select(ModelValidationRecord)
            .where(ModelValidationRecord.proposal_id == proposal_id)
            .order_by(ModelValidationRecord.created_at, ModelValidationRecord.id)
        )
        return list(result)
