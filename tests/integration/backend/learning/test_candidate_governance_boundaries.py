"""Native owner boundaries; explicit source fixtures are not a browser handoff.

The existing learning_session enforces the migrated disposable PostgreSQL test
database and rolls back each test. The browser journey separately creates its
complete LearningEvidence/analyses through their real owners.
"""

from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.learning.persistence.models import LearningEvidenceModel
from app.features.market.persistence.models import WorkspaceModel
from app.features.model.api.proposal_validation_router import _response
from app.features.model.api.router import _validation
from app.features.model.domain.enums import ValidationConclusion
from app.features.model.service.application import ModelGovernanceService
from app.features.model.service.lesson_hypothesis_handoff import LessonHypothesisHandoffService
from app.features.model.service.proposal_validation_read_service import (
    ProposalValidationReadService,
)
from app.features.model.service.runtime_activation_service import RuntimeActivationService

NOW = datetime(2026, 10, 24, 10, 0, tzinfo=UTC)
POLICY_A: dict[str, object] = {
    "schema": "TOP_DOWN_CANDIDATE/2.0",
    "direction": "LONG",
    "market_context_allowed": ["FAVORABLE", "CAUTIOUS"],
}
POLICY_B: dict[str, object] = {
    "schema": "TOP_DOWN_CANDIDATE/2.0",
    "direction": "LONG",
    "market_context_allowed": ["FAVORABLE"],
}


async def _workspace(session: AsyncSession) -> UUID:
    workspace_id = uuid4()
    session.add(
        WorkspaceModel(
            id=workspace_id, name="Synthetic Candidate governance boundary", created_at=NOW
        )
    )
    await session.flush()
    return workspace_id


async def _evidence(session: AsyncSession, workspace_id: UUID, created_at: datetime = NOW) -> UUID:
    evidence_id = uuid4()
    # Deliberate boundary fixture, not a claim of owner-created FT011 evidence.
    session.add(
        LearningEvidenceModel(
            id=evidence_id,
            workspace_id=workspace_id,
            evidence_type="FT011",
            created_at=created_at,
        )
    )
    await session.flush()
    return evidence_id


async def _facts(session: AsyncSession) -> dict[str, str]:
    result = {}
    for table in (
        "governed_models",
        "governed_model_versions",
        "model_hypotheses",
        "model_hypothesis_evidence",
        "model_change_proposals",
        "model_validations",
        "model_validation_evidence",
        "model_approvals",
        "model_runtime_activations",
    ):
        result[table] = await session.scalar(
            text(
                "SELECT COALESCE(jsonb_agg(to_jsonb(snapshot) ORDER BY to_jsonb(snapshot)::text), "
                f"'[]'::jsonb)::text FROM {table} AS snapshot"
            )
        )
    return result


async def _draft(session: AsyncSession, workspace_id: UUID, evidence_id: UUID):
    governance = ModelGovernanceService(session)
    actor_id = uuid4()
    model, base = await governance.create_model(
        workspace_id=workspace_id,
        model_key="TOP_DOWN_CANDIDATE",
        name="Synthetic Candidate boundary",
        purpose="Verify explicit governance; no economic claim",
        initial_definition=POLICY_A,
        actor=actor_id,
    )
    await governance.approve_initial_version(
        workspace_id=workspace_id,
        model_id=model.id,
        version_id=base.id,
        actor=actor_id,
        correlation_id="synthetic-initial-approval",
    )
    hypothesis = await governance.create_hypothesis(
        workspace_id=workspace_id,
        title="Synthetic explicit hypothesis",
        statement="Exercise the existing policy transition only.",
        evidence_ids=(evidence_id,),
        source_lesson_version_id=None,
        actor=actor_id,
    )
    proposal = await governance.create_proposal(
        workspace_id=workspace_id,
        model_id=model.id,
        base_model_version_id=base.id,
        hypothesis_id=hypothesis.id,
        proposed_definition=POLICY_B,
        rationale="Synthetic controllability qualification.",
        actor=actor_id,
    )
    return governance, actor_id, model, base, hypothesis, proposal


async def test_hypothesis_scope_rejection_and_exact_historical_lesson(
    learning_session: AsyncSession,
) -> None:
    workspace = await _workspace(learning_session)
    other_workspace = await _workspace(learning_session)
    lesson_id, l1, l2, actor = (uuid4() for _ in range(4))
    # Minimal Lesson rows isolate source-scope enforcement, not Lesson creation.
    await learning_session.execute(
        text("""
            INSERT INTO lessons (id, workspace_id, title, current_version_id,
                current_state, created_at, created_by, updated_at, updated_by)
            VALUES (:id, :workspace, 'Synthetic source scope', :current, 'CURRENT',
                :now, :actor, :now, :actor)
        """),
        {"id": lesson_id, "workspace": workspace, "current": l2, "now": NOW, "actor": actor},
    )
    for number, version_id, previous in ((1, l1, None), (2, l2, l1)):
        await learning_session.execute(
            text("""
                INSERT INTO lesson_versions (id, lesson_id, version, main_category,
                    content, created_at, created_by, supersedes_version_id)
                VALUES (:id, :lesson, :version, 'PROCESS', 'Synthetic source',
                    :now, :actor, :previous)
            """),
            {
                "id": version_id,
                "lesson": lesson_id,
                "version": number,
                "now": NOW,
                "actor": actor,
                "previous": previous,
            },
        )
    await learning_session.commit()
    governance = ModelGovernanceService(learning_session)
    before = await _facts(learning_session)
    for source_id in (l1, uuid4()):
        with pytest.raises(ValueError, match="source lesson version not found"):
            await governance.create_hypothesis(
                workspace_id=other_workspace,
                title="Rejected foreign or unknown lesson",
                statement="No source from another workspace may be bound.",
                evidence_ids=(),
                source_lesson_version_id=source_id,
                actor=actor,
            )
        assert await _facts(learning_session) == before
    with pytest.raises(ValueError, match="source lesson version not found"):
        await LessonHypothesisHandoffService(learning_session).create_from_lesson_version(
            workspace_id=other_workspace,
            lesson_version_id=l1,
            title="Rejected handoff",
            statement="The specialized route has the same source boundary.",
            actor=actor,
        )
    assert await _facts(learning_session) == before
    hypothesis = await governance.create_hypothesis(
        workspace_id=workspace,
        title="Deliberately selected L1",
        statement="Current L2 does not replace the explicit historical L1 source.",
        evidence_ids=(),
        source_lesson_version_id=l1,
        actor=actor,
    )
    historical = await LessonHypothesisHandoffService(learning_session).list_for_lesson_version(
        workspace_id=workspace, lesson_version_id=l1
    )
    assert [item.id for item in historical] == [hypothesis.id]
    assert historical[0].source_lesson_version_id == l1
    assert (
        await LessonHypothesisHandoffService(learning_session).list_for_lesson_version(
            workspace_id=workspace, lesson_version_id=l2
        )
        == []
    )


async def test_validation_cutoff_scope_readback_and_non_supporting_approval(
    learning_session: AsyncSession,
) -> None:
    workspace = await _workspace(learning_session)
    other_workspace = await _workspace(learning_session)
    e1 = await _evidence(learning_session, workspace)
    later = await _evidence(learning_session, workspace, NOW + timedelta(microseconds=1))
    foreign = await _evidence(learning_session, other_workspace)
    governance, actor, model, base, _, proposal = await _draft(learning_session, workspace, e1)
    runtime = RuntimeActivationService(learning_session)
    await runtime.activate(
        workspace_id=workspace,
        model_id=model.id,
        model_version_id=base.id,
        actor=actor,
        correlation_id="synthetic-active-A",
    )
    before = await _facts(learning_session)
    for ids, cutoff, message in (
        ((e1,), NOW - timedelta(microseconds=1), "evidence cutoff"),
        ((e1, later), NOW, "evidence cutoff"),
        ((foreign,), NOW, "learning evidence anchors were not found"),
    ):
        with pytest.raises(ValueError, match=message):
            await governance.validate_proposal(
                workspace_id=workspace,
                proposal_id=proposal.id,
                evidence_ids=ids,
                evidence_cutoff_at=cutoff,
                conclusion=ValidationConclusion.INCONCLUSIVE,
                metrics={},
                notes="Rejected synthetic boundary command.",
                actor=actor,
            )
        assert await _facts(learning_session) == before
    validation = await governance.validate_proposal(
        workspace_id=workspace,
        proposal_id=proposal.id,
        evidence_ids=(e1, e1),
        evidence_cutoff_at=NOW.astimezone(timezone(timedelta(hours=2))),
        conclusion=ValidationConclusion.CONTRADICTS,
        metrics={},
        notes="Synthetic contrary finding retained; no financial conclusion.",
        actor=actor,
    )
    read_service = ProposalValidationReadService(learning_session)
    before_read = await _facts(learning_session)
    stored = await read_service.list_for_proposal(workspace_id=workspace, proposal_id=proposal.id)
    assert len(stored) == 1
    assert stored[0].evidence_ids == (e1,)
    assert stored[0].evidence_cutoff_at == NOW
    assert stored[0].conclusion is ValidationConclusion.CONTRADICTS
    assert stored[0].metrics == {}
    assert _response(stored[0]).model_dump() == _validation(validation).model_dump()
    with pytest.raises(ValueError, match="model change proposal not found"):
        await read_service.list_for_proposal(workspace_id=other_workspace, proposal_id=proposal.id)
    assert await _facts(learning_session) == before_read
    approved, approval = await governance.approve_proposal(
        workspace_id=workspace,
        proposal_id=proposal.id,
        actor=actor,
        correlation_id="synthetic-explicit-approval",
    )
    assert approval.model_version_id == approved.id
    assert approved.previous_version_id == base.id
    current = await runtime.get_current(workspace_id=workspace, model_id=model.id)
    assert current is not None and current[0].model_version_id == base.id
    assert stored[0].conclusion is ValidationConclusion.CONTRADICTS


async def test_stale_proposal_and_activation_identity_rejections_leave_no_partial_facts(
    learning_session: AsyncSession,
) -> None:
    workspace = await _workspace(learning_session)
    other_workspace = await _workspace(learning_session)
    e1 = await _evidence(learning_session, workspace)
    governance, actor, model, base, hypothesis, first = await _draft(
        learning_session, workspace, e1
    )
    second = await governance.create_proposal(
        workspace_id=workspace,
        model_id=model.id,
        base_model_version_id=base.id,
        hypothesis_id=hypothesis.id,
        proposed_definition=POLICY_B,
        rationale="A second explicit proposal retains the same exact base.",
        actor=actor,
    )
    for proposal in (first, second):
        await governance.validate_proposal(
            workspace_id=workspace,
            proposal_id=proposal.id,
            evidence_ids=(e1,),
            evidence_cutoff_at=NOW,
            conclusion=ValidationConclusion.INCONCLUSIVE,
            metrics={},
            notes="Synthetic inconclusive finding.",
            actor=actor,
        )
    approved, _ = await governance.approve_proposal(
        workspace_id=workspace, proposal_id=first.id, actor=actor, correlation_id=None
    )
    before = await _facts(learning_session)
    with pytest.raises(ValueError, match="base version is stale"):
        await governance.approve_proposal(
            workspace_id=workspace, proposal_id=second.id, actor=actor, correlation_id=None
        )
    assert await _facts(learning_session) == before
    assert (await governance.get_proposal(workspace, second.id)).base_model_version_id == base.id
    other_model, draft = await governance.create_model(
        workspace_id=other_workspace,
        model_key="TOP_DOWN_CANDIDATE",
        name="Separate synthetic workspace",
        purpose="Verify existing scope and status boundary",
        initial_definition=POLICY_A,
        actor=actor,
    )
    runtime = RuntimeActivationService(learning_session)
    for ws, mid, vid, message in (
        (workspace, model.id, draft.id, "model version not found"),
        (workspace, other_model.id, draft.id, "governed model not found"),
        (other_workspace, other_model.id, draft.id, "only APPROVED"),
    ):
        before = await _facts(learning_session)
        with pytest.raises(ValueError, match=message):
            await runtime.activate(
                workspace_id=ws,
                model_id=mid,
                model_version_id=vid,
                actor=actor,
                correlation_id=None,
            )
        assert await _facts(learning_session) == before
    versions = await governance.list_versions(workspace, model.id)
    assert [(item.id, item.definition) for item in versions] == [
        (base.id, POLICY_A),
        (approved.id, POLICY_B),
    ]
