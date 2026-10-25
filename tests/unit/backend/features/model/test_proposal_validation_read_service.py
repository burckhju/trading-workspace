from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.features.model.service.proposal_validation_read_service import (
    ProposalValidationReadService,
)

NOW = datetime(2026, 10, 24, 10, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_lists_workspace_scoped_validations_for_proposal() -> None:
    proposal_id = uuid4()
    workspace_id = uuid4()
    validation = SimpleNamespace(
        id=uuid4(),
        proposal_id=proposal_id,
        method="RETROSPECTIVE",
        evidence_cutoff_at=NOW,
        conclusion="INCONCLUSIVE",
        metrics={},
        notes="Synthetic recorded finding, no performance claim.",
        created_at=NOW,
        created_by=uuid4(),
    )
    evidence_id = uuid4()
    link = SimpleNamespace(validation_id=validation.id, learning_evidence_id=evidence_id)
    session = SimpleNamespace(
        scalar=AsyncMock(return_value=proposal_id),
        scalars=AsyncMock(side_effect=[[validation], [link]]),
    )

    result = await ProposalValidationReadService(session).list_for_proposal(
        workspace_id=workspace_id,
        proposal_id=proposal_id,
    )

    assert len(result) == 1
    assert result[0].id == validation.id
    assert result[0].evidence_ids == (evidence_id,)
    assert result[0].evidence_cutoff_at == NOW
    assert result[0].conclusion.value == "INCONCLUSIVE"
    assert result[0].metrics == {}
    assert result[0].notes == validation.notes
    session.scalar.assert_awaited_once()
    assert session.scalars.await_count == 2


@pytest.mark.asyncio
async def test_empty_validation_history_does_not_query_other_evidence() -> None:
    session = SimpleNamespace(
        scalar=AsyncMock(return_value=uuid4()),
        scalars=AsyncMock(return_value=[]),
    )
    assert (
        await ProposalValidationReadService(session).list_for_proposal(
            workspace_id=uuid4(), proposal_id=uuid4()
        )
        == []
    )
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
