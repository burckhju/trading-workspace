from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.features.model.service.hypothesis_proposal_read_service import (
    HypothesisProposalReadService,
)


@pytest.mark.asyncio
async def test_lists_workspace_scoped_proposals_for_hypothesis() -> None:
    hypothesis_id = uuid4()
    workspace_id = uuid4()
    proposal = SimpleNamespace(id=uuid4(), hypothesis_id=hypothesis_id, workspace_id=workspace_id)
    session = SimpleNamespace(
        scalar=AsyncMock(return_value=hypothesis_id),
        scalars=AsyncMock(return_value=[proposal]),
    )

    result = await HypothesisProposalReadService(session).list_for_hypothesis(
        workspace_id=workspace_id,
        hypothesis_id=hypothesis_id,
    )

    assert result == [proposal]
    session.scalar.assert_awaited_once()
    session.scalars.assert_awaited_once()


@pytest.mark.asyncio
async def test_rejects_hypothesis_outside_workspace() -> None:
    session = SimpleNamespace(
        scalar=AsyncMock(return_value=None),
        scalars=AsyncMock(),
    )

    with pytest.raises(ValueError, match="hypothesis not found"):
        await HypothesisProposalReadService(session).list_for_hypothesis(
            workspace_id=uuid4(),
            hypothesis_id=uuid4(),
        )

    session.scalars.assert_not_awaited()
