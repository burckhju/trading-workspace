"""Application service for FT-007 TradePlan commands and user decisions."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.candidate.persistence.models import (
    CandidateEvaluationModel,
    CandidateModel,
)
from app.features.market.domain.enums import LifecycleStatus
from app.features.market.persistence.models import UnderlyingModel
from app.features.trade_plan.domain.enums import (
    TradeDirection,
    TradePlanOriginType,
    TradePlanStatus,
)
from app.features.trade_plan.domain.lifecycle import ensure_transition
from app.features.trade_plan.domain.models import (
    EntryPlan,
    InvalidationPlan,
    RiskAssumptions,
    Target,
    TradePlan,
    TradePlanVersion,
)
from app.features.trade_plan.persistence.models import (
    TradePlanApprovalModel,
    TradePlanEventModel,
)
from app.features.trade_plan.service.unit_of_work import (
    SqlAlchemyTradePlanUnitOfWork,
    TradePlanUnitOfWork,
)


class TradePlanOriginGateway(Protocol):
    async def manual_underlying(self, workspace_id: UUID, underlying_id: UUID) -> UUID: ...
    async def candidate_origin(
        self, workspace_id: UUID, candidate_id: UUID, evaluation_id: UUID
    ) -> UUID: ...


class SqlAlchemyTradePlanOriginGateway:
    """Read-only validation gateway into FT-001/FT-005 ownership boundaries."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def manual_underlying(self, workspace_id: UUID, underlying_id: UUID) -> UUID:
        model = await self._session.scalar(
            select(UnderlyingModel).where(
                UnderlyingModel.workspace_id == workspace_id,
                UnderlyingModel.id == underlying_id,
            )
        )
        if model is None:
            raise ValueError("underlying does not exist in workspace")
        if model.lifecycle_status is not LifecycleStatus.ACTIVE:
            raise ValueError("underlying is not active")
        return model.id

    async def candidate_origin(
        self, workspace_id: UUID, candidate_id: UUID, evaluation_id: UUID
    ) -> UUID:
        row = (
            await self._session.execute(
                select(CandidateModel, CandidateEvaluationModel)
                .join(
                    CandidateEvaluationModel,
                    CandidateEvaluationModel.candidate_id == CandidateModel.id,
                )
                .where(
                    CandidateModel.workspace_id == workspace_id,
                    CandidateModel.id == candidate_id,
                    CandidateEvaluationModel.id == evaluation_id,
                )
            )
        ).one_or_none()
        if row is None:
            raise ValueError("candidate evaluation does not belong to candidate/workspace")
        candidate, evaluation = row
        if evaluation.direction != TradeDirection.LONG.value:
            raise ValueError("TradePlan V1 requires a LONG candidate evaluation")
        if evaluation.version < 1:
            raise ValueError("candidate evaluation version is invalid")
        return UUID(str(candidate.underlying_id))


class TradePlanService:
    def __init__(
        self,
        session: AsyncSession | None = None,
        *,
        uow: TradePlanUnitOfWork | None = None,
        origins: TradePlanOriginGateway | None = None,
    ) -> None:
        if uow is None:
            if session is None:
                raise ValueError("session or explicit uow/origins dependencies are required")
            uow = SqlAlchemyTradePlanUnitOfWork(session)
        if origins is None:
            if session is None:
                raise ValueError("session or explicit uow/origins dependencies are required")
            origins = SqlAlchemyTradePlanOriginGateway(session)
        self._uow = uow
        self._origins = origins

    async def create_manual(
        self,
        *,
        workspace_id: UUID,
        underlying_id: UUID,
        actor: UUID,
        thesis: str,
        entry: EntryPlan,
        invalidation: InvalidationPlan,
        targets: tuple[Target, ...],
        risk_assumptions: RiskAssumptions,
        correlation_id: str | None = None,
    ) -> tuple[TradePlan, TradePlanVersion]:
        await self._origins.manual_underlying(workspace_id, underlying_id)
        return await self._create(
            workspace_id=workspace_id,
            underlying_id=underlying_id,
            actor=actor,
            thesis=thesis,
            entry=entry,
            invalidation=invalidation,
            targets=targets,
            risk_assumptions=risk_assumptions,
            origin_type=TradePlanOriginType.MANUAL,
            candidate_id=None,
            candidate_evaluation_id=None,
            correlation_id=correlation_id,
        )

    async def create_from_candidate(
        self,
        *,
        workspace_id: UUID,
        candidate_id: UUID,
        candidate_evaluation_id: UUID,
        actor: UUID,
        thesis: str,
        entry: EntryPlan,
        invalidation: InvalidationPlan,
        targets: tuple[Target, ...],
        risk_assumptions: RiskAssumptions,
        correlation_id: str | None = None,
    ) -> tuple[TradePlan, TradePlanVersion]:
        underlying_id = await self._origins.candidate_origin(
            workspace_id, candidate_id, candidate_evaluation_id
        )
        return await self._create(
            workspace_id=workspace_id,
            underlying_id=underlying_id,
            actor=actor,
            thesis=thesis,
            entry=entry,
            invalidation=invalidation,
            targets=targets,
            risk_assumptions=risk_assumptions,
            origin_type=TradePlanOriginType.CANDIDATE_EVALUATION,
            candidate_id=candidate_id,
            candidate_evaluation_id=candidate_evaluation_id,
            correlation_id=correlation_id,
        )

    async def _create(
        self,
        *,
        workspace_id: UUID,
        underlying_id: UUID,
        actor: UUID,
        thesis: str,
        entry: EntryPlan,
        invalidation: InvalidationPlan,
        targets: tuple[Target, ...],
        risk_assumptions: RiskAssumptions,
        origin_type: TradePlanOriginType,
        candidate_id: UUID | None,
        candidate_evaluation_id: UUID | None,
        correlation_id: str | None,
    ) -> tuple[TradePlan, TradePlanVersion]:
        now = datetime.now(UTC)
        plan = TradePlan(
            id=uuid4(),
            workspace_id=workspace_id,
            underlying_id=underlying_id,
            origin_type=origin_type,
            candidate_id=candidate_id,
            candidate_evaluation_id=candidate_evaluation_id,
            created_at=now,
            created_by=actor,
        )
        version = TradePlanVersion(
            id=uuid4(),
            trade_plan_id=plan.id,
            version=1,
            direction=TradeDirection.LONG,
            thesis=thesis,
            entry=entry,
            invalidation=invalidation,
            targets=targets,
            risk_assumptions=risk_assumptions,
            status=TradePlanStatus.DRAFT,
            created_at=now,
            created_by=actor,
        )
        async with self._uow as uow:
            await uow.plans.add(plan)
            await uow.versions.add(version)
            await self._add_event(
                uow,
                plan=plan,
                version=version,
                event_type="TRADE_PLAN_CREATED",
                from_status=None,
                to_status=TradePlanStatus.DRAFT,
                actor=actor,
                correlation_id=correlation_id,
            )
            await self._add_event(
                uow,
                plan=plan,
                version=version,
                event_type="TRADE_PLAN_VERSION_CREATED",
                from_status=None,
                to_status=TradePlanStatus.DRAFT,
                actor=actor,
                correlation_id=correlation_id,
            )
            await uow.commit()
        return plan, version

    async def amend(
        self,
        *,
        workspace_id: UUID,
        trade_plan_id: UUID,
        base_version_id: UUID,
        actor: UUID,
        change_reason: str,
        thesis: str,
        entry: EntryPlan,
        invalidation: InvalidationPlan,
        targets: tuple[Target, ...],
        risk_assumptions: RiskAssumptions,
        correlation_id: str | None = None,
    ) -> TradePlanVersion:
        if not change_reason.strip():
            raise ValueError("amendment change reason is required")
        async with self._uow as uow:
            if not await uow.plans.lock(workspace_id, trade_plan_id):
                raise ValueError("trade plan not found")
            plan = await uow.plans.get(workspace_id, trade_plan_id)
            if plan is None:
                raise ValueError("trade plan not found")
            base = await uow.versions.get(trade_plan_id, base_version_id)
            if base is None:
                raise ValueError("base trade plan version not found")
            if base.status is not TradePlanStatus.APPROVED:
                raise ValueError("amendment requires an APPROVED base version")
            number = await uow.versions.next_version_number(workspace_id, trade_plan_id)
            if number <= base.version:
                raise ValueError("amendment version number must be newer than its base version")
            version = TradePlanVersion(
                id=uuid4(),
                trade_plan_id=trade_plan_id,
                version=number,
                direction=TradeDirection.LONG,
                thesis=thesis,
                entry=entry,
                invalidation=invalidation,
                targets=targets,
                risk_assumptions=risk_assumptions,
                status=TradePlanStatus.DRAFT,
                created_at=datetime.now(UTC),
                created_by=actor,
                previous_version_id=base.id,
                change_reason=change_reason,
            )
            await uow.versions.add(version)
            await self._add_event(
                uow,
                plan=plan,
                version=version,
                event_type="TRADE_PLAN_AMENDED",
                from_status=None,
                to_status=TradePlanStatus.DRAFT,
                actor=actor,
                reason=change_reason,
                correlation_id=correlation_id,
            )
            await uow.commit()
            return version

    async def submit_for_review(
        self,
        workspace_id: UUID,
        trade_plan_id: UUID,
        version_id: UUID,
        actor: UUID,
        correlation_id: str | None = None,
    ) -> TradePlanVersion:
        return await self._transition(
            workspace_id,
            trade_plan_id,
            version_id,
            TradePlanStatus.READY_FOR_REVIEW,
            actor,
            "TRADE_PLAN_READY_FOR_REVIEW",
            None,
            correlation_id,
        )

    async def return_to_draft(
        self,
        workspace_id: UUID,
        trade_plan_id: UUID,
        version_id: UUID,
        actor: UUID,
        reason: str | None = None,
        correlation_id: str | None = None,
    ) -> TradePlanVersion:
        return await self._transition(
            workspace_id,
            trade_plan_id,
            version_id,
            TradePlanStatus.DRAFT,
            actor,
            "TRADE_PLAN_RETURNED_TO_DRAFT",
            reason,
            correlation_id,
        )

    async def abandon(
        self,
        workspace_id: UUID,
        trade_plan_id: UUID,
        version_id: UUID,
        actor: UUID,
        reason: str | None = None,
        correlation_id: str | None = None,
    ) -> TradePlanVersion:
        return await self._transition(
            workspace_id,
            trade_plan_id,
            version_id,
            TradePlanStatus.ABANDONED,
            actor,
            "TRADE_PLAN_ABANDONED",
            reason,
            correlation_id,
        )

    async def approve(
        self,
        workspace_id: UUID,
        trade_plan_id: UUID,
        version_id: UUID,
        actor: UUID,
        correlation_id: str | None = None,
    ) -> TradePlanVersion:
        async with self._uow as uow:
            if not await uow.plans.lock(workspace_id, trade_plan_id):
                raise ValueError("trade plan not found")
            plan, version = await self._load(uow, workspace_id, trade_plan_id, version_id)
            approval = await uow.approvals.get_for_version(version.id)
            if version.status is TradePlanStatus.APPROVED:
                if approval is None:
                    raise ValueError("approved trade plan version has no approval record")
                return version
            if approval is not None:
                raise ValueError("trade plan version has approval record before APPROVED status")
            version.ensure_approvable()
            versions = tuple(await uow.versions.list(trade_plan_id))
            latest_number = max((item.version for item in versions), default=version.version)
            if version.version != latest_number:
                raise ValueError("only the latest trade plan version can be approved")
            previous_approved = self._single_previous_approved(versions, exclude=version.id)
            now = datetime.now(UTC)
            await uow.versions.set_status(trade_plan_id, version.id, TradePlanStatus.APPROVED.value)
            approved = replace(version, status=TradePlanStatus.APPROVED)
            await uow.approvals.add(
                TradePlanApprovalModel(
                    id=uuid4(),
                    trade_plan_id=trade_plan_id,
                    trade_plan_version_id=version.id,
                    version=version.version,
                    actor=str(actor),
                    approved_at=now,
                    correlation_id=correlation_id,
                )
            )
            await self._add_event(
                uow,
                plan=plan,
                version=approved,
                event_type="TRADE_PLAN_APPROVED",
                from_status=TradePlanStatus.READY_FOR_REVIEW,
                to_status=TradePlanStatus.APPROVED,
                actor=actor,
                correlation_id=correlation_id,
                occurred_at=now,
            )
            if previous_approved is not None:
                await uow.versions.set_status(
                    trade_plan_id,
                    previous_approved.id,
                    TradePlanStatus.SUPERSEDED.value,
                )
                await self._add_event(
                    uow,
                    plan=plan,
                    version=replace(previous_approved, status=TradePlanStatus.SUPERSEDED),
                    event_type="TRADE_PLAN_SUPERSEDED",
                    from_status=TradePlanStatus.APPROVED,
                    to_status=TradePlanStatus.SUPERSEDED,
                    actor=actor,
                    correlation_id=correlation_id,
                    occurred_at=now,
                )
            await uow.commit()
            return approved

    async def _transition(
        self,
        workspace_id: UUID,
        trade_plan_id: UUID,
        version_id: UUID,
        target: TradePlanStatus,
        actor: UUID,
        event_type: str,
        reason: str | None,
        correlation_id: str | None,
    ) -> TradePlanVersion:
        async with self._uow as uow:
            if not await uow.plans.lock(workspace_id, trade_plan_id):
                raise ValueError("trade plan not found")
            plan, version = await self._load(uow, workspace_id, trade_plan_id, version_id)
            ensure_transition(version.status, target)
            if version.status is target:
                return version
            await uow.versions.set_status(trade_plan_id, version.id, target.value)
            changed = replace(version, status=target)
            await self._add_event(
                uow,
                plan=plan,
                version=changed,
                event_type=event_type,
                from_status=version.status,
                to_status=target,
                actor=actor,
                reason=reason,
                correlation_id=correlation_id,
            )
            await uow.commit()
            return changed

    async def _load(
        self,
        uow: TradePlanUnitOfWork,
        workspace_id: UUID,
        trade_plan_id: UUID,
        version_id: UUID,
    ) -> tuple[TradePlan, TradePlanVersion]:
        plan = await uow.plans.get(workspace_id, trade_plan_id)
        if plan is None:
            raise ValueError("trade plan not found")
        version = await uow.versions.get(trade_plan_id, version_id)
        if version is None:
            raise ValueError("trade plan version not found")
        return plan, version

    @staticmethod
    def _single_previous_approved(
        versions: tuple[TradePlanVersion, ...],
        *,
        exclude: UUID,
    ) -> TradePlanVersion | None:
        approved = tuple(
            item
            for item in versions
            if item.id != exclude and item.status is TradePlanStatus.APPROVED
        )
        if len(approved) > 1:
            raise ValueError("multiple active APPROVED trade plan versions detected")
        return approved[0] if approved else None

    async def _add_event(
        self,
        uow: TradePlanUnitOfWork,
        *,
        plan: TradePlan,
        version: TradePlanVersion,
        event_type: str,
        from_status: TradePlanStatus | None,
        to_status: TradePlanStatus,
        actor: UUID,
        reason: str | None = None,
        correlation_id: str | None = None,
        occurred_at: datetime | None = None,
    ) -> None:
        await uow.events.add(
            TradePlanEventModel(
                id=uuid4(),
                trade_plan_id=plan.id,
                trade_plan_version_id=version.id,
                event_type=event_type,
                from_status=from_status.value if from_status else None,
                to_status=to_status.value,
                reason=reason,
                actor=str(actor),
                correlation_id=correlation_id,
                occurred_at=occurred_at or datetime.now(UTC),
            )
        )
