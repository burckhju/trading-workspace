"""Read-only FT-013 ModelChangeProposal -> Approval API."""

from collections.abc import AsyncIterator
from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_database_session
from app.features.model.api.dtos import ApprovalResponse, ModelVersionResponse, ProposalApprovalResponse
from app.features.model.api.errors import translate_model_governance_error
from app.features.model.domain.enums import ModelVersionStatus
from app.features.model.service.proposal_approval_read_service import ProposalApprovalReadService

router = APIRouter(prefix="/api/v1/model-governance", tags=["model-governance"])
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")


async def get_proposal_approval_read_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> AsyncIterator[ProposalApprovalReadService]:
    yield ProposalApprovalReadService(session)


def _raise(error: ValueError) -> NoReturn:
    raise translate_model_governance_error(error) from error


@router.get(
    "/proposals/{proposal_id}/approval",
    response_model=ProposalApprovalResponse | None,
)
async def get_proposal_approval(
    proposal_id: UUID,
    service: Annotated[ProposalApprovalReadService, Depends(get_proposal_approval_read_service)],
) -> ProposalApprovalResponse | None:
    try:
        result = await service.get_for_proposal(workspace_id=WORKSPACE_ID, proposal_id=proposal_id)
        if result is None:
            return None
        approval, version = result
        return ProposalApprovalResponse(
            model_version=ModelVersionResponse(
                id=version.id,
                model_id=version.model_id,
                version=version.version,
                status=ModelVersionStatus(version.status),
                definition=version.definition,
                change_summary=version.change_summary,
                created_at=version.created_at,
                created_by=version.created_by,
                previous_version_id=version.previous_version_id,
            ),
            approval=ApprovalResponse(
                id=approval.id,
                proposal_id=approval.proposal_id,
                model_version_id=approval.model_version_id,
                approved_at=approval.approved_at,
                approved_by=approval.approved_by,
                correlation_id=approval.correlation_id,
            ),
        )
    except ValueError as exc:
        _raise(exc)
