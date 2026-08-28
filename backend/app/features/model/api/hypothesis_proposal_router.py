"""Read-only FT-013 Hypothesis -> ModelChangeProposal API."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_database_session
from app.features.model.api.dtos import ProposalResponse
from app.features.model.api.errors import translate_model_governance_error
from app.features.model.domain.enums import ProposalStatus
from app.features.model.persistence.models import ModelChangeProposalRecord
from app.features.model.service.hypothesis_proposal_read_service import (
    HypothesisProposalReadService,
)

router = APIRouter(prefix="/api/v1/model-governance", tags=["model-governance"])
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")


async def get_hypothesis_proposal_read_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> AsyncIterator[HypothesisProposalReadService]:
    yield HypothesisProposalReadService(session)


def _raise(error: ValueError) -> NoReturn:
    raise translate_model_governance_error(error) from error


def _response(value: ModelChangeProposalRecord) -> ProposalResponse:
    return ProposalResponse(
        id=value.id,
        model_id=value.model_id,
        base_model_version_id=value.base_model_version_id,
        hypothesis_id=value.hypothesis_id,
        status=ProposalStatus(value.status),
        proposed_definition=value.proposed_definition,
        rationale=value.rationale,
        created_at=value.created_at,
        created_by=value.created_by,
    )


@router.get(
    "/hypotheses/{hypothesis_id}/proposals",
    response_model=list[ProposalResponse],
)
async def list_hypothesis_proposals(
    hypothesis_id: UUID,
    service: Annotated[
        HypothesisProposalReadService,
        Depends(get_hypothesis_proposal_read_service),
    ],
) -> list[ProposalResponse]:
    try:
        values = await service.list_for_hypothesis(
            workspace_id=WORKSPACE_ID,
            hypothesis_id=hypothesis_id,
        )
        return [_response(value) for value in values]
    except ValueError as exc:
        _raise(exc)
