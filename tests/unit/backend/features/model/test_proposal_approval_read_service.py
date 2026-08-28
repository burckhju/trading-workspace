from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.features.model.service.proposal_approval_read_service import (
    ProposalApprovalReadService,
)


@pytest.mark.asyncio
async def test_reads_workspace_scoped_proposal_approval_and_version() -> None:
    proposal_id = uuid4()
    workspace_id = uuid4()
    version = SimpleNamespace(id=uuid4())
    approval = SimpleNamespace(model_version_id=version.id)
    session = SimpleNamespace(
        scalar=AsyncMock(side_effect=[SimpleNamespace(id=proposal_id), approval, version])
    )

    result = await ProposalApprovalReadService(session).get_for_proposal(
        workspace_id=workspace_id,
        proposal_id=proposal_id,
    )

    assert result == (approval, version)
    assert session.scalar.await_count == 3


@pytest.mark.asyncio
async def test_returns_none_when_proposal_has_no_approval() -> None:
    session = SimpleNamespace(scalar=AsyncMock(side_effect=[SimpleNamespace(id=uuid4()), None]))

    result = await ProposalApprovalReadService(session).get_for_proposal(
        workspace_id=uuid4(),
        proposal_id=uuid4(),
    )

    assert result is None


@pytest.mark.asyncio
async def test_rejects_proposal_outside_workspace() -> None:
    session = SimpleNamespace(scalar=AsyncMock(return_value=None))

    with pytest.raises(ValueError, match="model change proposal not found"):
        await ProposalApprovalReadService(session).get_for_proposal(
            workspace_id=uuid4(),
            proposal_id=uuid4(),
        )
