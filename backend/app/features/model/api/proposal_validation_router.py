"""Read-only FT-013 ModelChangeProposal -> ModelValidation API."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_database_session
from app.features.model.api.dtos import ValidationResponse
from app.features.model.api.errors import translate_model_governance_error
from app.features.model.domain.enums import ValidationConclusion, ValidationMethod
from app.features.model.persistence.models import ModelValidationRecord
from app.features.model.service.proposal_validation_read_service import (
    ProposalValidationReadService,
)

router = APIRouter(prefix="/api/v1/model-governance", tags=["model-governance"])
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")


async def get_proposal_validation_read_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> AsyncIterator[ProposalValidationReadService]:
    yield ProposalValidationReadService(session)


def _raise(error: ValueError) -> NoReturn:
    raise translate_model_governance_error(error) from error


def _response(value: ModelValidationRecord) -> ValidationResponse:
    return ValidationResponse(
        id=value.id,
        proposal_id=value.proposal_id,
        method=ValidationMethod(value.method),
        evidence_cutoff_at=value.evidence_cutoff_at,
        conclusion=ValidationConclusion(value.conclusion),
        metrics=value.metrics,
        notes=value.notes,
        created_at=value.created_at,
        created_by=value.created_by,
    )


@router.get(
    "/proposals/{proposal_id}/validations",
    response_model=list[ValidationResponse],
)
async def list_proposal_validations(
    proposal_id: UUID,
    service: Annotated[
        ProposalValidationReadService,
        Depends(get_proposal_validation_read_service),
    ],
) -> list[ValidationResponse]:
    try:
        values = await service.list_for_proposal(
            workspace_id=WORKSPACE_ID,
            proposal_id=proposal_id,
        )
        return [_response(value) for value in values]
    except ValueError as exc:
        _raise(exc)
