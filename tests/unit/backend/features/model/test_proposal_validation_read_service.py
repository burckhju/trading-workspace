from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.features.model.service.proposal_validation_read_service import (
    ProposalValidationReadService,
)


@pytest.mark.asyncio
async def test_lists_workspace_scoped_validations_for_proposal() -> None:
    proposal_id = uuid4()
    workspace_id = uuid4()
    validation = SimpleNamespace(id=uuid4(), proposal_id=proposal_id)
    session = SimpleNamespace(
        scalar=AsyncMock(return_value=proposal_id),
        scalars=AsyncMock(return_value=[validation]),
    )

    result = await ProposalValidationReadService(session).list_for_proposal(
        workspace_id=workspace_id,
        proposal_id=proposal_id,
    )

    assert result == [validation]
    session.scalar.assert_awaited_once()
    session.scalars.assert_awaited_once()


@pytest.mark.asyncio
async def test_rejects_proposal_outside_workspace() -> None:
    session = SimpleNamespace(
        scalar=AsyncMock(return_value=None),
        scalars=AsyncMock(),
    )

    with pytest.raises(ValueError, match="model change proposal not found"):
        await ProposalValidationReadService(session).list_for_proposal(
            workspace_id=uuid4(),
            proposal_id=uuid4(),
        )

    session.scalars.assert_not_awaited()
