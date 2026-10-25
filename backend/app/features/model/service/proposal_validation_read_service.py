"""Readback for validations attached to one workspace-owned FT-013 proposal."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.model.domain.enums import ValidationConclusion, ValidationMethod
from app.features.model.domain.models import ModelValidation
from app.features.model.persistence.models import (
    ModelChangeProposalRecord,
    ModelValidationEvidenceRecord,
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
    ) -> list[ModelValidation]:
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
        records = list(result)
        if not records:
            return []
        links = await self._session.scalars(
            select(ModelValidationEvidenceRecord)
            .where(ModelValidationEvidenceRecord.validation_id.in_([item.id for item in records]))
            .order_by(
                ModelValidationEvidenceRecord.validation_id,
                ModelValidationEvidenceRecord.learning_evidence_id,
            )
        )
        evidence_by_validation: dict[UUID, list[UUID]] = {item.id: [] for item in records}
        for link in links:
            evidence_by_validation[link.validation_id].append(link.learning_evidence_id)
        return [
            ModelValidation(
                id=item.id,
                proposal_id=item.proposal_id,
                method=ValidationMethod(item.method),
                evidence_cutoff_at=item.evidence_cutoff_at,
                conclusion=ValidationConclusion(item.conclusion),
                metrics=dict(item.metrics),
                notes=item.notes,
                created_at=item.created_at,
                created_by=item.created_by,
                evidence_ids=tuple(evidence_by_validation[item.id]),
            )
            for item in records
        ]
