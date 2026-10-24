"""Native service boundary for the FT-020 proposal-form context regression."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.learning.persistence.models import LearningEvidenceModel
from app.features.market.persistence.models import WorkspaceModel
from app.features.model.domain.enums import ProposalStatus
from app.features.model.persistence.models import (
    GovernedModelRecord,
    HypothesisRecord,
    ModelApprovalRecord,
    ModelChangeProposalRecord,
    ModelValidationRecord,
    ModelVersionRecord,
)
from app.features.model.persistence.runtime_activation_models import ModelRuntimeActivationRecord
from app.features.model.service.application import ModelGovernanceService

NOW = datetime(2026, 10, 24, 10, 0, tzinfo=UTC)


async def _governance_facts(session: AsyncSession, workspace_id: UUID) -> dict[str, object]:
    proposal_ids = select(ModelChangeProposalRecord.id).where(
        ModelChangeProposalRecord.workspace_id == workspace_id
    )
    version_ids = (
        select(ModelVersionRecord.id)
        .join(GovernedModelRecord, GovernedModelRecord.id == ModelVersionRecord.model_id)
        .where(GovernedModelRecord.workspace_id == workspace_id)
    )
    versions = await session.execute(
        select(
            ModelVersionRecord.id,
            ModelVersionRecord.model_id,
            ModelVersionRecord.version,
            ModelVersionRecord.status,
            ModelVersionRecord.definition,
            ModelVersionRecord.change_summary,
            ModelVersionRecord.created_at,
            ModelVersionRecord.created_by,
            ModelVersionRecord.previous_version_id,
        )
        .where(ModelVersionRecord.id.in_(version_ids))
        .order_by(ModelVersionRecord.id)
    )
    return {
        "versions": versions.all(),
        "proposals": list(
            await session.scalars(proposal_ids.order_by(ModelChangeProposalRecord.id))
        ),
        "validations": list(
            await session.scalars(
                select(ModelValidationRecord.id)
                .where(ModelValidationRecord.proposal_id.in_(proposal_ids))
                .order_by(ModelValidationRecord.id)
            )
        ),
        "approvals": list(
            await session.scalars(
                select(ModelApprovalRecord.id)
                .where(ModelApprovalRecord.model_version_id.in_(version_ids))
                .order_by(ModelApprovalRecord.id)
            )
        ),
        "activations": list(
            await session.scalars(
                select(ModelRuntimeActivationRecord.id)
                .where(ModelRuntimeActivationRecord.workspace_id == workspace_id)
                .order_by(ModelRuntimeActivationRecord.id)
            )
        ),
    }


async def test_foreign_proposal_base_is_rejected_without_partial_governance_facts(
    learning_session: AsyncSession,
) -> None:
    workspace_id, actor_id, evidence_id = uuid4(), uuid4(), uuid4()
    learning_session.add(
        WorkspaceModel(id=workspace_id, name="FT-020 synthetic proposal context", created_at=NOW)
    )
    await learning_session.flush()
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
    model, base = await service.create_model(
        workspace_id=workspace_id,
        model_key="TOP_DOWN_CANDIDATE",
        name="FT-020 synthetic Candidate",
        purpose="Check explicit proposal identity without activating a model",
        initial_definition={
            "schema": "TOP_DOWN_CANDIDATE/1.0",
            "direction": "LONG",
            "market_context_allowed": ["FAVORABLE", "CAUTIOUS"],
        },
        actor=actor_id,
    )
    other_model, other_base = await service.create_model(
        workspace_id=workspace_id,
        model_key="FT020_SYNTHETIC_OTHER",
        name="FT-020 separate synthetic model",
        purpose="A distinct model identity for the deliberately mismatched command",
        initial_definition={"fixture_parameter": 1},
        actor=actor_id,
    )
    for model_id, version_id in ((model.id, base.id), (other_model.id, other_base.id)):
        await service.approve_initial_version(
            workspace_id=workspace_id,
            model_id=model_id,
            version_id=version_id,
            actor=actor_id,
            correlation_id="ft020-synthetic-base-approval",
        )
    hypothesis = await service.create_hypothesis(
        workspace_id=workspace_id,
        title="FT-020 synthetic proposal binding",
        statement="An explicit proposal must retain its model and approved base identity.",
        evidence_ids=(evidence_id,),
        source_lesson_version_id=None,
        actor=actor_id,
    )
    before = await _governance_facts(learning_session, workspace_id)
    assert before["proposals"] == before["validations"] == before["activations"] == []
    proposed_definition = {
        "schema": "TOP_DOWN_CANDIDATE/2.0",
        "direction": "LONG",
        "market_context_allowed": ["FAVORABLE"],
    }

    with pytest.raises(ValueError, match="model version not found"):
        await service.create_proposal(
            workspace_id=workspace_id,
            model_id=model.id,
            base_model_version_id=other_base.id,
            hypothesis_id=hypothesis.id,
            proposed_definition=proposed_definition,
            rationale="This synthetic mismatched command must not be persisted.",
            actor=actor_id,
        )

    assert await _governance_facts(learning_session, workspace_id) == before
    assert (
        await learning_session.scalar(
            select(HypothesisRecord.status).where(HypothesisRecord.id == hypothesis.id)
        )
        == "OPEN"
    )

    proposal = await service.create_proposal(
        workspace_id=workspace_id,
        model_id=model.id,
        base_model_version_id=base.id,
        hypothesis_id=hypothesis.id,
        proposed_definition=proposed_definition,
        rationale="Explicit synthetic Candidate policy proposal.",
        actor=actor_id,
    )

    assert proposal.status is ProposalStatus.DRAFT
    assert (proposal.model_id, proposal.base_model_version_id, proposal.hypothesis_id) == (
        model.id,
        base.id,
        hypothesis.id,
    )
    stored = await service.get_proposal(workspace_id, proposal.id)
    assert stored.status == "DRAFT"
    assert stored.proposed_definition == proposed_definition
    assert stored.rationale == "Explicit synthetic Candidate policy proposal."
    # Exactly one DRAFT is new. Both approved bases remain unchanged field-for-field;
    # neither validation, another approval nor runtime activation occurs on Create.
    assert await _governance_facts(learning_session, workspace_id) == {
        **before,
        "proposals": [proposal.id],
    }
    assert (
        await learning_session.scalar(
            select(HypothesisRecord.status).where(HypothesisRecord.id == hypothesis.id)
        )
        == "PROPOSED"
    )
