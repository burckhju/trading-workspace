"""Read-side query models for FT-007 TradePlan provenance and history.

The query service deliberately resolves provenance by exact persisted identifiers. It never
asks FT-005 for a "latest" evaluation, so later Candidate re-evaluations cannot alter the
meaning of an existing TradePlan.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.candidate.persistence.models import (
    CandidateEvaluationModel,
    CandidateEvaluationSourceModel,
    CandidateModel,
)
from app.features.trade_plan.domain.enums import TradePlanOriginType
from app.features.trade_plan.domain.models import TradePlan, TradePlanVersion
from app.features.trade_plan.persistence.models import (
    TradePlanApprovalModel,
    TradePlanEventModel,
)
from app.features.trade_plan.service.unit_of_work import (
    SqlAlchemyTradePlanUnitOfWork,
    TradePlanUnitOfWork,
)


@dataclass(frozen=True, slots=True)
class CandidateEvaluationSourceProvenance:
    role: str
    source_type: str
    source_id: UUID
    source_version: int
    model_id: str
    model_version: str


@dataclass(frozen=True, slots=True)
class CandidateEvaluationProvenance:
    candidate_id: UUID
    evaluation_id: UUID
    evaluation_version: int
    direction: str
    model_id: str
    model_version: str
    qualification: str
    quality_status: str
    evaluated_at: datetime
    sources: tuple[CandidateEvaluationSourceProvenance, ...]


@dataclass(frozen=True, slots=True)
class ApprovalProvenance:
    approval_id: UUID
    trade_plan_version_id: UUID
    version: int
    actor: str
    approved_at: datetime
    correlation_id: str | None


@dataclass(frozen=True, slots=True)
class LifecycleEventView:
    id: UUID
    event_type: str
    from_status: str | None
    to_status: str
    reason: str | None
    actor: str
    correlation_id: str | None
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class TradePlanVersionView:
    plan: TradePlan
    version: TradePlanVersion
    candidate_evaluation: CandidateEvaluationProvenance | None
    approval: ApprovalProvenance | None
    events: tuple[LifecycleEventView, ...]


class TradePlanProvenanceGateway:
    async def candidate_evaluation(
        self, plan: TradePlan
    ) -> CandidateEvaluationProvenance | None:
        raise NotImplementedError


class SqlAlchemyTradePlanProvenanceGateway(TradePlanProvenanceGateway):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def candidate_evaluation(
        self, plan: TradePlan
    ) -> CandidateEvaluationProvenance | None:
        if plan.origin_type is TradePlanOriginType.MANUAL:
            return None
        if plan.candidate_id is None or plan.candidate_evaluation_id is None:
            raise ValueError(
                "candidate-originated trade plan has incomplete provenance"
            )

        row = (
            await self._session.execute(
                select(CandidateModel, CandidateEvaluationModel)
                .join(
                    CandidateEvaluationModel,
                    CandidateEvaluationModel.candidate_id == CandidateModel.id,
                )
                .where(
                    CandidateModel.workspace_id == plan.workspace_id,
                    CandidateModel.id == plan.candidate_id,
                    CandidateModel.underlying_id == plan.underlying_id,
                    CandidateEvaluationModel.id == plan.candidate_evaluation_id,
                )
            )
        ).one_or_none()
        if row is None:
            raise ValueError(
                "persisted CandidateEvaluation provenance cannot be resolved"
            )
        _, evaluation = row

        source_rows = (
            await self._session.scalars(
                select(CandidateEvaluationSourceModel)
                .where(CandidateEvaluationSourceModel.evaluation_id == evaluation.id)
                .order_by(
                    CandidateEvaluationSourceModel.role,
                    CandidateEvaluationSourceModel.id,
                )
            )
        ).all()
        sources = tuple(
            CandidateEvaluationSourceProvenance(
                role=item.role,
                source_type=item.source_type,
                source_id=item.source_id,
                source_version=item.source_version,
                model_id=item.model_id,
                model_version=item.model_version,
            )
            for item in source_rows
        )
        return CandidateEvaluationProvenance(
            candidate_id=plan.candidate_id,
            evaluation_id=evaluation.id,
            evaluation_version=evaluation.version,
            direction=evaluation.direction,
            model_id=evaluation.model_id,
            model_version=evaluation.model_version,
            qualification=evaluation.qualification,
            quality_status=evaluation.quality_status,
            evaluated_at=evaluation.evaluated_at,
            sources=sources,
        )


class TradePlanQueryService:
    """Versionspecific read side for future REST DTO mapping."""

    def __init__(
        self,
        session: AsyncSession | None = None,
        *,
        uow: TradePlanUnitOfWork | None = None,
        provenance: TradePlanProvenanceGateway | None = None,
    ) -> None:
        if uow is None:
            if session is None:
                raise ValueError(
                    "session or explicit uow/provenance dependencies are required"
                )
            uow = SqlAlchemyTradePlanUnitOfWork(session)
        if provenance is None:
            if session is None:
                raise ValueError(
                    "session or explicit uow/provenance dependencies are required"
                )
            provenance = SqlAlchemyTradePlanProvenanceGateway(session)
        self._uow = uow
        self._provenance = provenance

    async def get_version(
        self, workspace_id: UUID, trade_plan_id: UUID, version_id: UUID
    ) -> TradePlanVersionView:
        async with self._uow as uow:
            plan = await uow.plans.get(workspace_id, trade_plan_id)
            if plan is None:
                raise ValueError("trade plan not found")
            version = await uow.versions.get(trade_plan_id, version_id)
            if version is None:
                raise ValueError("trade plan version not found")
            return await self._view(uow, plan, version)

    async def get_version_by_number(
        self, workspace_id: UUID, trade_plan_id: UUID, version: int
    ) -> TradePlanVersionView:
        if version < 1:
            raise ValueError("trade plan version must be positive")
        async with self._uow as uow:
            plan = await uow.plans.get(workspace_id, trade_plan_id)
            if plan is None:
                raise ValueError("trade plan not found")
            snapshot = await uow.versions.get_by_number(trade_plan_id, version)
            if snapshot is None:
                raise ValueError("trade plan version not found")
            return await self._view(uow, plan, snapshot)

    async def list_versions(
        self, workspace_id: UUID, trade_plan_id: UUID
    ) -> tuple[TradePlanVersionView, ...]:
        async with self._uow as uow:
            plan = await uow.plans.get(workspace_id, trade_plan_id)
            if plan is None:
                raise ValueError("trade plan not found")
            return tuple(
                [
                    await self._view(uow, plan, item)
                    for item in await uow.versions.list(trade_plan_id)
                ]
            )

    async def _view(
        self, uow: TradePlanUnitOfWork, plan: TradePlan, version: TradePlanVersion
    ) -> TradePlanVersionView:
        approval_model = await uow.approvals.get_for_version(version.id)
        event_models = await uow.events.list_for_version(version.id)
        candidate_evaluation = await self._provenance.candidate_evaluation(plan)
        return TradePlanVersionView(
            plan=plan,
            version=version,
            candidate_evaluation=candidate_evaluation,
            approval=self._approval(approval_model),
            events=tuple(self._event(item) for item in event_models),
        )

    @staticmethod
    def _approval(model: TradePlanApprovalModel | None) -> ApprovalProvenance | None:
        if model is None:
            return None
        return ApprovalProvenance(
            approval_id=model.id,
            trade_plan_version_id=model.trade_plan_version_id,
            version=model.version,
            actor=model.actor,
            approved_at=model.approved_at,
            correlation_id=model.correlation_id,
        )

    @staticmethod
    def _event(model: TradePlanEventModel) -> LifecycleEventView:
        return LifecycleEventView(
            id=model.id,
            event_type=model.event_type,
            from_status=model.from_status,
            to_status=model.to_status,
            reason=model.reason,
            actor=model.actor,
            correlation_id=model.correlation_id,
            occurred_at=model.occurred_at,
        )
