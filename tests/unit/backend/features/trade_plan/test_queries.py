from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from tests.unit.backend.features.trade_plan.test_application_service import version

from app.features.trade_plan.domain.enums import TradePlanOriginType, TradePlanStatus
from app.features.trade_plan.domain.models import TradePlan
from app.features.trade_plan.service.queries import (
    CandidateEvaluationProvenance,
    SqlAlchemyTradePlanProvenanceGateway,
    TradePlanQueryService,
)


class FakeUow:
    def __init__(self):
        self.plans = SimpleNamespace(get=AsyncMock())
        self.versions = SimpleNamespace(
            get=AsyncMock(), get_by_number=AsyncMock(), list=AsyncMock()
        )
        self.events = SimpleNamespace(list_for_version=AsyncMock(return_value=()))
        self.approvals = SimpleNamespace(get_for_version=AsyncMock(return_value=None))

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None


class FakeProvenance:
    def __init__(self, value=None):
        self.value = value
        self.candidate_evaluation = AsyncMock(return_value=value)


@pytest.mark.asyncio
async def test_query_returns_exact_version_with_versionspecific_audit_and_provenance():
    workspace_id, plan_id, underlying_id, actor, candidate_id, evaluation_id = (
        uuid4() for _ in range(6)
    )
    plan = TradePlan(
        id=plan_id,
        workspace_id=workspace_id,
        underlying_id=underlying_id,
        origin_type=TradePlanOriginType.CANDIDATE_EVALUATION,
        created_at=datetime.now(UTC),
        created_by=actor,
        candidate_id=candidate_id,
        candidate_evaluation_id=evaluation_id,
    )
    snapshot = version(plan_id, actor, TradePlanStatus.APPROVED)
    provenance = CandidateEvaluationProvenance(
        candidate_id=candidate_id,
        evaluation_id=evaluation_id,
        evaluation_version=3,
        direction="LONG",
        model_id="candidate-model",
        model_version="1.0",
        qualification="QUALIFIED",
        quality_status="OK",
        evaluated_at=datetime.now(UTC),
        sources=(),
    )
    approval = SimpleNamespace(
        id=uuid4(),
        trade_plan_version_id=snapshot.id,
        version=1,
        actor=str(actor),
        approved_at=datetime.now(UTC),
        correlation_id="corr-7",
    )
    event = SimpleNamespace(
        id=uuid4(),
        event_type="TRADE_PLAN_APPROVED",
        from_status="READY_FOR_REVIEW",
        to_status="APPROVED",
        reason=None,
        actor=str(actor),
        correlation_id="corr-7",
        occurred_at=datetime.now(UTC),
    )
    uow, gateway = FakeUow(), FakeProvenance(provenance)
    uow.plans.get.return_value = plan
    uow.versions.get.return_value = snapshot
    uow.approvals.get_for_version.return_value = approval
    uow.events.list_for_version.return_value = (event,)

    view = await TradePlanQueryService(uow=uow, provenance=gateway).get_version(
        workspace_id, plan_id, snapshot.id
    )

    assert view.version.id == snapshot.id
    assert view.candidate_evaluation is provenance
    assert view.candidate_evaluation.evaluation_id == evaluation_id
    assert view.approval.trade_plan_version_id == snapshot.id
    assert view.events[0].event_type == "TRADE_PLAN_APPROVED"
    gateway.candidate_evaluation.assert_awaited_once_with(plan)


@pytest.mark.asyncio
async def test_query_by_number_does_not_fall_back_to_latest():
    workspace_id, plan_id, underlying_id, actor = (uuid4() for _ in range(4))
    plan = TradePlan(
        id=plan_id,
        workspace_id=workspace_id,
        underlying_id=underlying_id,
        origin_type=TradePlanOriginType.MANUAL,
        created_at=datetime.now(UTC),
        created_by=actor,
    )
    v1 = version(plan_id, actor, number=1)
    uow = FakeUow()
    uow.plans.get.return_value = plan
    uow.versions.get_by_number.return_value = v1

    view = await TradePlanQueryService(uow=uow, provenance=FakeProvenance()).get_version_by_number(
        workspace_id, plan_id, 1
    )

    assert view.version.version == 1
    uow.versions.get_by_number.assert_awaited_once_with(plan_id, 1)


@pytest.mark.asyncio
async def test_manual_plan_has_no_candidate_provenance():
    session = Mock()
    gateway = SqlAlchemyTradePlanProvenanceGateway(session)
    plan = TradePlan(
        id=uuid4(),
        workspace_id=uuid4(),
        underlying_id=uuid4(),
        origin_type=TradePlanOriginType.MANUAL,
        created_at=datetime.now(UTC),
        created_by=uuid4(),
    )
    assert await gateway.candidate_evaluation(plan) is None
    assert not hasattr(session, "execute") or session.execute.call_count == 0


@pytest.mark.asyncio
async def test_candidate_provenance_resolves_only_persisted_exact_evaluation():
    candidate_id, evaluation_id, workspace_id, underlying_id = (uuid4() for _ in range(4))
    plan = TradePlan(
        id=uuid4(),
        workspace_id=workspace_id,
        underlying_id=underlying_id,
        origin_type=TradePlanOriginType.CANDIDATE_EVALUATION,
        created_at=datetime.now(UTC),
        created_by=uuid4(),
        candidate_id=candidate_id,
        candidate_evaluation_id=evaluation_id,
    )
    session = Mock()
    session.execute = AsyncMock()
    session.scalars = AsyncMock()
    evaluation = SimpleNamespace(
        id=evaluation_id,
        version=4,
        direction="LONG",
        model_id="m",
        model_version="1",
        qualification="QUALIFIED",
        quality_status="OK",
        evaluated_at=datetime.now(UTC),
    )
    result = Mock()
    result.one_or_none.return_value = (SimpleNamespace(id=candidate_id), evaluation)
    session.execute.return_value = result
    scalar_result = Mock()
    scalar_result.all.return_value = []
    session.scalars.return_value = scalar_result

    provenance = await SqlAlchemyTradePlanProvenanceGateway(session).candidate_evaluation(plan)

    assert provenance.evaluation_id == evaluation_id
    assert provenance.evaluation_version == 4
    sql = str(session.execute.await_args.args[0])
    assert "candidate_evaluations.id" in sql
    assert "candidates.underlying_id" in sql


@pytest.mark.asyncio
async def test_unresolvable_candidate_provenance_fails_closed():
    plan = TradePlan(
        id=uuid4(),
        workspace_id=uuid4(),
        underlying_id=uuid4(),
        origin_type=TradePlanOriginType.CANDIDATE_EVALUATION,
        created_at=datetime.now(UTC),
        created_by=uuid4(),
        candidate_id=uuid4(),
        candidate_evaluation_id=uuid4(),
    )
    session = Mock()
    session.execute = AsyncMock()
    result = Mock()
    result.one_or_none.return_value = None
    session.execute.return_value = result

    with pytest.raises(ValueError, match="cannot be resolved"):
        await SqlAlchemyTradePlanProvenanceGateway(session).candidate_evaluation(plan)
