"""Readback service for FT-013 proposal approvals."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.model.persistence.models import (
    ModelApprovalRecord,
    ModelChangeProposalRecord,
    ModelVersionRecord,
)


class ProposalApprovalReadService:
    """Read one proposal approval and its immutable approved model version."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_for_proposal(
        self, *, workspace_id: UUID, proposal_id: UUID
    ) -> tuple[ModelApprovalRecord, ModelVersionRecord] | None:
        proposal = await self._session.scalar(
            select(ModelChangeProposalRecord).where(
                ModelChangeProposalRecord.id == proposal_id,
                ModelChangeProposalRecord.workspace_id == workspace_id,
            )
        )
        if proposal is None:
            raise ValueError("model change proposal not found")

        approval = await self._session.scalar(
            select(ModelApprovalRecord).where(ModelApprovalRecord.proposal_id == proposal_id)
        )
        if approval is None:
            return None

        version = await self._session.scalar(
            select(ModelVersionRecord).where(ModelVersionRecord.id == approval.model_version_id)
        )
        if version is None:
            raise ValueError("approved model version not found")
        return approval, version
