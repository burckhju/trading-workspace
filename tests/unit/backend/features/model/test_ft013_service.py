from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.features.model.domain.enums import ValidationConclusion
from app.features.model.service.application import ModelGovernanceService

NOW = datetime(2026, 8, 25, 10, 0, tzinfo=UTC)


def _session() -> SimpleNamespace:
    return SimpleNamespace(
        add=Mock(),
        commit=AsyncMock(),
        rollback=AsyncMock(),
        scalar=AsyncMock(),
        scalars=AsyncMock(),
        get=AsyncMock(),
    )


@pytest.mark.asyncio
async def test_create_model_starts_with_unapproved_draft() -> None:
    session = _session()
    service = ModelGovernanceService(session)
    model, version = await service.create_model(
        workspace_id=uuid4(),
        model_key="TOP_DOWN_CANDIDATE",
        name="Top-down candidate",
        purpose="Qualify candidates",
        initial_definition={"min_relative_strength": 1.0},
        actor=uuid4(),
    )
    assert model.model_key == "TOP_DOWN_CANDIDATE"
    assert version.version == 1
    assert version.status.value == "DRAFT"
    assert session.add.call_count == 2
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_hypothesis_requires_learning_source() -> None:
    service = ModelGovernanceService(_session())
    with pytest.raises(ValueError, match="requires evidence"):
        await service.create_hypothesis(
            workspace_id=uuid4(),
            title="Gap-up",
            statement="Avoid extreme gap-ups",
            evidence_ids=(),
            source_lesson_version_id=None,
            actor=uuid4(),
        )


@pytest.mark.asyncio
async def test_validation_rejects_look_ahead_evidence() -> None:
    session = _session()
    workspace_id = uuid4()
    proposal_id = uuid4()
    session.scalar.return_value = SimpleNamespace(
        id=proposal_id,
        workspace_id=workspace_id,
        status="DRAFT",
    )
    session.scalars.return_value = [
        SimpleNamespace(id=uuid4(), workspace_id=workspace_id, created_at=NOW + timedelta(days=1))
    ]
    service = ModelGovernanceService(session)
    with pytest.raises(ValueError, match="evidence cutoff"):
        await service.validate_proposal(
            workspace_id=workspace_id,
            proposal_id=proposal_id,
            evidence_ids=(session.scalars.return_value[0].id,),
            evidence_cutoff_at=NOW,
            conclusion=ValidationConclusion.INCONCLUSIVE,
            metrics={},
            notes=None,
            actor=uuid4(),
        )


@pytest.mark.asyncio
async def test_proposal_approval_rejects_stale_base() -> None:
    session = _session()
    workspace_id = uuid4()
    model_id = uuid4()
    base_id = uuid4()
    proposal_id = uuid4()
    proposal = SimpleNamespace(
        id=proposal_id,
        workspace_id=workspace_id,
        status="VALIDATED",
        model_id=model_id,
        base_model_version_id=base_id,
        proposed_definition={"threshold": 7},
        rationale="Improve selectivity",
        hypothesis_id=uuid4(),
    )
    validation = SimpleNamespace(id=uuid4(), proposal_id=proposal_id)
    latest = SimpleNamespace(id=uuid4(), model_id=model_id, version=2)
    session.scalar.side_effect = [proposal, validation, latest]
    service = ModelGovernanceService(session)
    with pytest.raises(ValueError, match="stale"):
        await service.approve_proposal(
            workspace_id=workspace_id,
            proposal_id=proposal_id,
            actor=uuid4(),
            correlation_id="test",
        )
