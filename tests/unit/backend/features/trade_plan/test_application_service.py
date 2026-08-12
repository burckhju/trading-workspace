from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.features.trade_plan.domain.enums import (
    EntryType,
    TradeDirection,
    TradePlanOriginType,
    TradePlanStatus,
)
from app.features.trade_plan.domain.models import (
    EntryPlan,
    InvalidationPlan,
    RiskAssumptions,
    Target,
    TradePlan,
    TradePlanVersion,
)
from app.features.trade_plan.service.application import TradePlanService


def payload():
    return dict(
        thesis="Breakout continuation",
        entry=EntryPlan(type=EntryType.PRICE, currency="EUR", price=Decimal("100")),
        invalidation=InvalidationPlan(stop_price=Decimal("95")),
        targets=(Target(sequence=1, price=Decimal("110")),),
        risk_assumptions=RiskAssumptions(thesis_risk="Breakout failure"),
    )


def version(plan_id, actor, status=TradePlanStatus.DRAFT, number=1, previous=None):
    return TradePlanVersion(
        id=uuid4(),
        trade_plan_id=plan_id,
        version=number,
        direction=TradeDirection.LONG,
        status=status,
        created_at=datetime.now(UTC),
        created_by=actor,
        previous_version_id=previous,
        change_reason="changed" if previous else None,
        **payload(),
    )


class FakeUow:
    def __init__(self):
        self.plans = SimpleNamespace(
            add=AsyncMock(), get=AsyncMock(), lock=AsyncMock(return_value=True)
        )
        self.versions = SimpleNamespace(
            add=AsyncMock(),
            get=AsyncMock(),
            list=AsyncMock(return_value=()),
            next_version_number=AsyncMock(return_value=2),
            set_status=AsyncMock(),
        )
        self.events = SimpleNamespace(add=AsyncMock())
        self.approvals = SimpleNamespace(
            add=AsyncMock(), get_for_version=AsyncMock(return_value=None)
        )
        self.commit = AsyncMock()
        self.rollback = AsyncMock()
        self.flush = AsyncMock()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if exc_type:
            await self.rollback()


class FakeOrigins:
    def __init__(self, underlying_id=None):
        self.underlying_id = underlying_id or uuid4()
        self.manual_underlying = AsyncMock(return_value=self.underlying_id)
        self.candidate_origin = AsyncMock(return_value=self.underlying_id)


@pytest.mark.asyncio
async def test_create_manual_persists_durable_plan_and_first_draft_version():
    uow, origins = FakeUow(), FakeOrigins()
    service = TradePlanService(uow=uow, origins=origins)
    workspace_id, underlying_id, actor = uuid4(), origins.underlying_id, uuid4()

    plan, current = await service.create_manual(
        workspace_id=workspace_id, underlying_id=underlying_id, actor=actor, **payload()
    )

    assert plan.origin_type is TradePlanOriginType.MANUAL
    assert current.version == 1 and current.status is TradePlanStatus.DRAFT
    origins.manual_underlying.assert_awaited_once_with(workspace_id, underlying_id)
    uow.plans.add.assert_awaited_once_with(plan)
    uow.versions.add.assert_awaited_once_with(current)
    assert uow.events.add.await_count == 2
    uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_from_candidate_keeps_exact_evaluation_provenance():
    uow, origins = FakeUow(), FakeOrigins()
    service = TradePlanService(uow=uow, origins=origins)
    workspace_id, candidate_id, evaluation_id, actor = (uuid4() for _ in range(4))

    plan, _ = await service.create_from_candidate(
        workspace_id=workspace_id,
        candidate_id=candidate_id,
        candidate_evaluation_id=evaluation_id,
        actor=actor,
        **payload(),
    )

    assert plan.candidate_id == candidate_id
    assert plan.candidate_evaluation_id == evaluation_id
    assert plan.underlying_id == origins.underlying_id
    origins.candidate_origin.assert_awaited_once_with(workspace_id, candidate_id, evaluation_id)


@pytest.mark.asyncio
async def test_submit_and_return_to_draft_are_explicit_audited_transitions():
    uow, origins = FakeUow(), FakeOrigins()
    service = TradePlanService(uow=uow, origins=origins)
    workspace_id, plan_id, actor = uuid4(), uuid4(), uuid4()
    plan = TradePlan(
        plan_id,
        workspace_id,
        origins.underlying_id,
        TradePlanOriginType.MANUAL,
        datetime.now(UTC),
        actor,
    )
    draft = version(plan_id, actor)
    uow.plans.get.return_value = plan
    uow.versions.get.return_value = draft

    ready = await service.submit_for_review(workspace_id, plan_id, draft.id, actor)
    assert ready.status is TradePlanStatus.READY_FOR_REVIEW
    uow.versions.set_status.assert_awaited_once_with(plan_id, draft.id, "READY_FOR_REVIEW")

    uow.versions.get.return_value = ready
    returned = await service.return_to_draft(workspace_id, plan_id, ready.id, actor, "needs work")
    assert returned.status is TradePlanStatus.DRAFT
    assert uow.commit.await_count == 2


@pytest.mark.asyncio
async def test_approve_records_exact_version_and_supersedes_previous_approval():
    uow, origins = FakeUow(), FakeOrigins()
    service = TradePlanService(uow=uow, origins=origins)
    workspace_id, plan_id, actor = uuid4(), uuid4(), uuid4()
    plan = TradePlan(
        plan_id,
        workspace_id,
        origins.underlying_id,
        TradePlanOriginType.MANUAL,
        datetime.now(UTC),
        actor,
    )
    old = version(plan_id, actor, TradePlanStatus.APPROVED, number=1)
    ready = version(plan_id, actor, TradePlanStatus.READY_FOR_REVIEW, number=2, previous=old.id)
    uow.plans.get.return_value = plan
    uow.versions.get.return_value = ready
    uow.versions.list.return_value = (ready, old)

    approved = await service.approve(workspace_id, plan_id, ready.id, actor, "corr-1")

    assert approved.status is TradePlanStatus.APPROVED
    assert uow.versions.set_status.await_args_list[0].args == (
        plan_id,
        ready.id,
        "APPROVED",
    )
    assert uow.versions.set_status.await_args_list[1].args == (
        plan_id,
        old.id,
        "SUPERSEDED",
    )
    approval = uow.approvals.add.await_args.args[0]
    assert approval.trade_plan_version_id == ready.id and approval.version == 2
    assert approval.actor == str(actor) and approval.correlation_id == "corr-1"
    assert uow.events.add.await_count == 2


@pytest.mark.asyncio
async def test_amendment_requires_approved_base_and_creates_new_draft_version():
    uow, origins = FakeUow(), FakeOrigins()
    service = TradePlanService(uow=uow, origins=origins)
    workspace_id, plan_id, actor = uuid4(), uuid4(), uuid4()
    plan = TradePlan(
        plan_id,
        workspace_id,
        origins.underlying_id,
        TradePlanOriginType.MANUAL,
        datetime.now(UTC),
        actor,
    )
    approved = version(plan_id, actor, TradePlanStatus.APPROVED)
    uow.plans.get.return_value = plan
    uow.versions.get.return_value = approved

    amended = await service.amend(
        workspace_id=workspace_id,
        trade_plan_id=plan_id,
        base_version_id=approved.id,
        actor=actor,
        change_reason="raise entry after consolidation",
        **payload(),
    )

    assert amended.version == 2 and amended.status is TradePlanStatus.DRAFT
    assert amended.previous_version_id == approved.id
    assert amended.change_reason == "raise entry after consolidation"
    uow.versions.next_version_number.assert_awaited_once_with(workspace_id, plan_id)
    uow.versions.add.assert_awaited_once_with(amended)


@pytest.mark.asyncio
async def test_amendment_rejects_non_approved_base():
    uow, origins = FakeUow(), FakeOrigins()
    service = TradePlanService(uow=uow, origins=origins)
    workspace_id, plan_id, actor = uuid4(), uuid4(), uuid4()
    plan = TradePlan(
        plan_id,
        workspace_id,
        origins.underlying_id,
        TradePlanOriginType.MANUAL,
        datetime.now(UTC),
        actor,
    )
    draft = version(plan_id, actor)
    uow.plans.get.return_value = plan
    uow.versions.get.return_value = draft

    with pytest.raises(ValueError, match="APPROVED"):
        await service.amend(
            workspace_id=workspace_id,
            trade_plan_id=plan_id,
            base_version_id=draft.id,
            actor=actor,
            change_reason="change",
            **payload(),
        )
    uow.versions.add.assert_not_awaited()


@pytest.mark.asyncio
async def test_approve_is_idempotent_for_already_approved_version_with_record():
    uow, origins = FakeUow(), FakeOrigins()
    service = TradePlanService(uow=uow, origins=origins)
    workspace_id, plan_id, actor = uuid4(), uuid4(), uuid4()
    plan = TradePlan(
        plan_id,
        workspace_id,
        origins.underlying_id,
        TradePlanOriginType.MANUAL,
        datetime.now(UTC),
        actor,
    )
    approved = version(plan_id, actor, TradePlanStatus.APPROVED)
    uow.plans.get.return_value = plan
    uow.versions.get.return_value = approved
    uow.approvals.get_for_version.return_value = SimpleNamespace(id=uuid4())

    result = await service.approve(workspace_id, plan_id, approved.id, actor, "retry")

    assert result is approved
    uow.versions.set_status.assert_not_awaited()
    uow.approvals.add.assert_not_awaited()
    uow.events.add.assert_not_awaited()
    uow.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_approve_fails_closed_when_status_and_approval_record_disagree():
    uow, origins = FakeUow(), FakeOrigins()
    service = TradePlanService(uow=uow, origins=origins)
    workspace_id, plan_id, actor = uuid4(), uuid4(), uuid4()
    plan = TradePlan(
        plan_id,
        workspace_id,
        origins.underlying_id,
        TradePlanOriginType.MANUAL,
        datetime.now(UTC),
        actor,
    )
    approved = version(plan_id, actor, TradePlanStatus.APPROVED)
    uow.plans.get.return_value = plan
    uow.versions.get.return_value = approved

    with pytest.raises(ValueError, match="no approval record"):
        await service.approve(workspace_id, plan_id, approved.id, actor)

    ready = version(plan_id, actor, TradePlanStatus.READY_FOR_REVIEW)
    uow.versions.get.return_value = ready
    uow.approvals.get_for_version.return_value = SimpleNamespace(id=uuid4())
    with pytest.raises(ValueError, match="before APPROVED"):
        await service.approve(workspace_id, plan_id, ready.id, actor)


@pytest.mark.asyncio
async def test_approve_rejects_stale_non_latest_version():
    uow, origins = FakeUow(), FakeOrigins()
    service = TradePlanService(uow=uow, origins=origins)
    workspace_id, plan_id, actor = uuid4(), uuid4(), uuid4()
    plan = TradePlan(
        plan_id,
        workspace_id,
        origins.underlying_id,
        TradePlanOriginType.MANUAL,
        datetime.now(UTC),
        actor,
    )
    ready = version(plan_id, actor, TradePlanStatus.READY_FOR_REVIEW, number=1)
    newer = version(plan_id, actor, TradePlanStatus.DRAFT, number=2, previous=ready.id)
    uow.plans.get.return_value = plan
    uow.versions.get.return_value = ready
    uow.versions.list.return_value = (newer, ready)

    with pytest.raises(ValueError, match="latest"):
        await service.approve(workspace_id, plan_id, ready.id, actor)
    uow.versions.set_status.assert_not_awaited()


@pytest.mark.asyncio
async def test_approve_fails_closed_on_multiple_active_approved_versions():
    uow, origins = FakeUow(), FakeOrigins()
    service = TradePlanService(uow=uow, origins=origins)
    workspace_id, plan_id, actor = uuid4(), uuid4(), uuid4()
    plan = TradePlan(
        plan_id,
        workspace_id,
        origins.underlying_id,
        TradePlanOriginType.MANUAL,
        datetime.now(UTC),
        actor,
    )
    old1 = version(plan_id, actor, TradePlanStatus.APPROVED, number=1)
    old2 = version(plan_id, actor, TradePlanStatus.APPROVED, number=2, previous=old1.id)
    ready = version(plan_id, actor, TradePlanStatus.READY_FOR_REVIEW, number=3, previous=old2.id)
    uow.plans.get.return_value = plan
    uow.versions.get.return_value = ready
    uow.versions.list.return_value = (ready, old2, old1)

    with pytest.raises(ValueError, match="multiple active APPROVED"):
        await service.approve(workspace_id, plan_id, ready.id, actor)
    uow.versions.set_status.assert_not_awaited()


@pytest.mark.asyncio
async def test_amendment_locks_plan_identity_before_reading_base_version():
    uow, origins = FakeUow(), FakeOrigins()
    service = TradePlanService(uow=uow, origins=origins)
    workspace_id, plan_id, actor = uuid4(), uuid4(), uuid4()
    plan = TradePlan(
        plan_id,
        workspace_id,
        origins.underlying_id,
        TradePlanOriginType.MANUAL,
        datetime.now(UTC),
        actor,
    )
    approved = version(plan_id, actor, TradePlanStatus.APPROVED)
    uow.plans.get.return_value = plan
    uow.versions.get.return_value = approved

    await service.amend(
        workspace_id=workspace_id,
        trade_plan_id=plan_id,
        base_version_id=approved.id,
        actor=actor,
        change_reason="hardening",
        **payload(),
    )

    uow.plans.lock.assert_awaited_once_with(workspace_id, plan_id)


@pytest.mark.asyncio
async def test_amendment_rejects_non_monotonic_version_number_against_base():
    uow, origins = FakeUow(), FakeOrigins()
    service = TradePlanService(uow=uow, origins=origins)
    workspace_id, plan_id, actor = uuid4(), uuid4(), uuid4()
    plan = TradePlan(
        plan_id,
        workspace_id,
        origins.underlying_id,
        TradePlanOriginType.MANUAL,
        datetime.now(UTC),
        actor,
    )
    approved = version(plan_id, actor, TradePlanStatus.APPROVED, number=2, previous=uuid4())
    uow.plans.get.return_value = plan
    uow.versions.get.return_value = approved
    uow.versions.next_version_number.return_value = 2

    with pytest.raises(ValueError, match="newer than its base"):
        await service.amend(
            workspace_id=workspace_id,
            trade_plan_id=plan_id,
            base_version_id=approved.id,
            actor=actor,
            change_reason="adjust",
            **payload(),
        )
    uow.versions.add.assert_not_awaited()
