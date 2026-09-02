from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.analysis.domain.enums import (
    AnalysisQualityStatus,
    CriterionClassification,
)
from app.features.analysis.domain.top_down import ContextClassification, TradingDirection
from app.features.candidate.domain.models import AnalysisReference, CandidateEvaluationInput
from app.features.candidate.service.application import CandidateService
from app.features.candidate.service.runtime_readiness import (
    RuntimeAwareCandidateLiveWorkflowService,
)
from app.features.learning.persistence.models import LearningEvidenceModel
from app.features.market.persistence.models import WorkspaceModel
from app.features.model.domain.enums import ValidationConclusion
from app.features.model.service.application import ModelGovernanceService
from app.features.model.service.runtime_activation_service import RuntimeActivationService

NOW = datetime(2026, 9, 2, 15, 30, tzinfo=UTC)


def _candidate_input() -> CandidateEvaluationInput:
    return CandidateEvaluationInput(
        direction=TradingDirection.LONG,
        market_context=ContextClassification.CAUTIOUS,
        market_quality=AnalysisQualityStatus.GOOD,
        sector_trend=CriterionClassification.POSITIVE,
        sector_relative_strength=CriterionClassification.POSITIVE,
        sector_quality=AnalysisQualityStatus.GOOD,
        underlying_long_trend=CriterionClassification.POSITIVE,
        underlying_medium_trend=CriterionClassification.POSITIVE,
        underlying_short_trend=CriterionClassification.POSITIVE,
        underlying_relative_strength=CriterionClassification.POSITIVE,
        underlying_quality=AnalysisQualityStatus.GOOD,
    )


def _sources() -> dict[str, AnalysisReference]:
    return {
        role: AnalysisReference(
            analysis_id=uuid4(),
            version=1,
            model_id=f"{role}_ANALYSIS",
            model_version="1.0.0",
        )
        for role in ("MARKET", "SECTOR", "UNDERLYING")
    }


async def test_governance_activation_changes_candidate_semantics_with_truthful_provenance(
    learning_session: AsyncSession,
) -> None:
    workspace_id = uuid4()
    underlying_id = uuid4()
    candidate_id = uuid4()
    actor_id = uuid4()
    evidence_id = uuid4()

    learning_session.add(
        WorkspaceModel(
            id=workspace_id,
            name="FT-019 governed Candidate semantics",
            created_at=NOW,
        )
    )
    await learning_session.flush()
    await learning_session.execute(
        text(
            """
            INSERT INTO underlyings (
                id, workspace_id, type, name, isin, wkn, lifecycle_status,
                quality_status, version, created_at, updated_at, data_origin
            ) VALUES (
                :id, :workspace_id, 'STOCK', 'FT-019 Fixture', NULL, NULL, 'ACTIVE',
                'GOOD', 1, :created_at, :updated_at, 'MANUAL'
            )
            """
        ),
        {
            "id": underlying_id,
            "workspace_id": workspace_id,
            "created_at": NOW,
            "updated_at": NOW,
        },
    )
    await learning_session.execute(
        text(
            """
            INSERT INTO candidates (
                id, workspace_id, underlying_id, status, created_at, created_by
            ) VALUES (
                :id, :workspace_id, :underlying_id, 'IDENTIFIED', :created_at, 'ft019-test'
            )
            """
        ),
        {
            "id": candidate_id,
            "workspace_id": workspace_id,
            "underlying_id": underlying_id,
            "created_at": NOW,
        },
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

    governance = ModelGovernanceService(learning_session)
    runtime = RuntimeActivationService(learning_session)
    candidate_service = CandidateService(learning_session)
    readiness = RuntimeAwareCandidateLiveWorkflowService(learning_session)

    model, permissive_version = await governance.create_model(
        workspace_id=workspace_id,
        model_key="TOP_DOWN_CANDIDATE",
        name="Top-down candidate model",
        purpose="Qualify candidates with governed market-context semantics",
        initial_definition={
            "schema": "TOP_DOWN_CANDIDATE/2.0",
            "direction": "LONG",
            "market_context_allowed": ["FAVORABLE", "CAUTIOUS"],
        },
        actor=actor_id,
    )
    await governance.approve_initial_version(
        workspace_id=workspace_id,
        model_id=model.id,
        version_id=permissive_version.id,
        actor=actor_id,
        correlation_id="ft019-initial",
    )
    await runtime.activate(
        workspace_id=workspace_id,
        model_id=model.id,
        model_version_id=permissive_version.id,
        actor=actor_id,
        correlation_id="ft019-activate-permissive",
    )

    permissive_readiness = await readiness._runtime_step(workspace_id)
    first = await candidate_service.evaluate(
        workspace_id,
        candidate_id,
        _candidate_input(),
        _sources(),
    )

    assert permissive_readiness.status == "COMPLETE"
    assert first.version == 1
    assert first.qualification == "QUALIFIED"
    assert first.model_id == "TOP_DOWN_CANDIDATE"
    assert first.model_version == "1"

    hypothesis = await governance.create_hypothesis(
        workspace_id=workspace_id,
        title="Require a favorable market for Candidate qualification",
        statement="CAUTIOUS should no longer satisfy the required market gate.",
        evidence_ids=(evidence_id,),
        source_lesson_version_id=None,
        actor=actor_id,
    )
    proposal = await governance.create_proposal(
        workspace_id=workspace_id,
        model_id=model.id,
        base_model_version_id=permissive_version.id,
        hypothesis_id=hypothesis.id,
        proposed_definition={
            "schema": "TOP_DOWN_CANDIDATE/2.0",
            "direction": "LONG",
            "market_context_allowed": ["FAVORABLE"],
        },
        rationale="Make the existing market gate stricter through governed configuration.",
        actor=actor_id,
    )
    await governance.validate_proposal(
        workspace_id=workspace_id,
        proposal_id=proposal.id,
        evidence_ids=(evidence_id,),
        evidence_cutoff_at=NOW,
        conclusion=ValidationConclusion.SUPPORTS,
        metrics={"evidence_count": 1},
        notes="FT-019 retrospective validation fixture.",
        actor=actor_id,
    )
    strict_version, _ = await governance.approve_proposal(
        workspace_id=workspace_id,
        proposal_id=proposal.id,
        actor=actor_id,
        correlation_id="ft019-approve-strict",
    )

    resolved_before_activation = await runtime.resolve_by_key(
        workspace_id=workspace_id,
        model_key="TOP_DOWN_CANDIDATE",
    )
    assert resolved_before_activation is not None
    assert resolved_before_activation.model_version_id == permissive_version.id

    await runtime.activate(
        workspace_id=workspace_id,
        model_id=model.id,
        model_version_id=strict_version.id,
        actor=actor_id,
        correlation_id="ft019-activate-strict",
    )

    strict_readiness = await readiness._runtime_step(workspace_id)
    second = await candidate_service.evaluate(
        workspace_id,
        candidate_id,
        _candidate_input(),
        _sources(),
    )

    assert strict_readiness.status == "COMPLETE"
    assert second.version == 2
    assert second.qualification == "NOT_QUALIFIED"
    assert second.model_version == "2"
    assert first.model_version == "1"
    assert first.qualification == "QUALIFIED"

    strict_criteria = await candidate_service.list_criteria(second.id)
    market_criterion = next(
        item for item in strict_criteria if item.criterion_id == "TD-MARKET-001"
    )
    assert market_criterion.evaluation == "NOT_FULFILLED"
    assert market_criterion.actual_value == "CAUTIOUS"
    assert market_criterion.expected_value == "FAVORABLE"
    assert "CAUTIOUS is not allowed" in market_criterion.explanation

    await runtime.activate(
        workspace_id=workspace_id,
        model_id=model.id,
        model_version_id=permissive_version.id,
        actor=actor_id,
        correlation_id="ft019-reactivate-permissive",
    )
    third = await candidate_service.evaluate(
        workspace_id,
        candidate_id,
        _candidate_input(),
        _sources(),
    )

    assert third.version == 3
    assert third.qualification == "QUALIFIED"
    assert third.model_version == "1"

    history = await candidate_service.list_evaluations(candidate_id)
    by_version = {item.version: item for item in history}
    assert by_version[1].qualification == "QUALIFIED"
    assert by_version[1].model_version == "1"
    assert by_version[2].qualification == "NOT_QUALIFIED"
    assert by_version[2].model_version == "2"
    assert by_version[3].qualification == "QUALIFIED"
    assert by_version[3].model_version == "1"
