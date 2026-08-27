from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.learning.persistence.models import LearningEvidenceModel
from app.features.market.persistence.models import WorkspaceModel
from app.features.model.domain.enums import (
    HypothesisStatus,
    ModelVersionStatus,
    ProposalStatus,
    ValidationConclusion,
)
from app.features.model.service.application import ModelGovernanceService

NOW = datetime(2026, 8, 27, 12, 30, tzinfo=UTC)


async def test_learning_evidence_drives_controlled_model_governance(
    learning_session: AsyncSession,
) -> None:
    workspace_id = uuid4()
    actor_id = uuid4()
    evidence_id = uuid4()

    learning_session.add(
        WorkspaceModel(
            id=workspace_id,
            name="Golden Path Extension 08",
            created_at=NOW,
        )
    )
    learning_session.add(
        LearningEvidenceModel(
            id=evidence_id,
            workspace_id=workspace_id,
            evidence_type="FT011",
            created_at=NOW,
        )
    )
    await learning_session.commit()

    service = ModelGovernanceService(learning_session)

    model, initial_version = await service.create_model(
        workspace_id=workspace_id,
        model_key="TOP_DOWN_CANDIDATE",
        name="Top-down candidate model",
        purpose="Qualify candidates with governed thresholds",
        initial_definition={"min_relative_strength": 1.0},
        actor=actor_id,
    )
    assert initial_version.status is ModelVersionStatus.DRAFT

    initial_approval = await service.approve_initial_version(
        workspace_id=workspace_id,
        model_id=model.id,
        version_id=initial_version.id,
        actor=actor_id,
        correlation_id="golden-path-extension-08-initial",
    )
    assert initial_approval.model_version_id == initial_version.id

    hypothesis = await service.create_hypothesis(
        workspace_id=workspace_id,
        title="Raise relative-strength threshold",
        statement="FT-012 evidence supports a stricter relative-strength threshold.",
        evidence_ids=(evidence_id,),
        source_lesson_version_id=None,
        actor=actor_id,
    )
    assert hypothesis.status is HypothesisStatus.OPEN

    proposal = await service.create_proposal(
        workspace_id=workspace_id,
        model_id=model.id,
        base_model_version_id=initial_version.id,
        hypothesis_id=hypothesis.id,
        proposed_definition={"min_relative_strength": 1.2},
        rationale="Apply the learning evidence through explicit governance.",
        actor=actor_id,
    )
    assert proposal.status is ProposalStatus.DRAFT
    assert proposal.base_model_version_id == initial_version.id

    validation = await service.validate_proposal(
        workspace_id=workspace_id,
        proposal_id=proposal.id,
        evidence_ids=(evidence_id,),
        evidence_cutoff_at=NOW + timedelta(hours=1),
        conclusion=ValidationConclusion.SUPPORTS,
        metrics={"evidence_count": 1},
        notes="Golden-path retrospective validation.",
        actor=actor_id,
    )
    assert validation.conclusion is ValidationConclusion.SUPPORTS

    approved_version, proposal_approval = await service.approve_proposal(
        workspace_id=workspace_id,
        proposal_id=proposal.id,
        actor=actor_id,
        correlation_id="golden-path-extension-08-proposal",
    )

    assert approved_version.version == 2
    assert approved_version.status is ModelVersionStatus.APPROVED
    assert approved_version.previous_version_id == initial_version.id
    assert approved_version.definition == {"min_relative_strength": 1.2}
    assert proposal_approval.model_version_id == approved_version.id
    assert proposal_approval.proposal_id == proposal.id

    stored_proposal = await service.get_proposal(workspace_id, proposal.id)
    assert stored_proposal.status == ProposalStatus.APPROVED.value

    versions = await service.list_versions(workspace_id, model.id)
    assert [version.id for version in versions] == [initial_version.id, approved_version.id]
    assert [version.status for version in versions] == ["APPROVED", "APPROVED"]
