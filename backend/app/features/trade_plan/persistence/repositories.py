"""Repository contracts and SQLAlchemy adapters for FT-007 TradePlan persistence."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.trade_plan.domain.models import TradePlan, TradePlanVersion
from app.features.trade_plan.persistence.mapping import (
    trade_plan_from_model,
    trade_plan_to_model,
    trade_plan_version_from_models,
    trade_plan_version_to_models,
)
from app.features.trade_plan.persistence.models import (
    TradePlanApprovalModel,
    TradePlanEventModel,
    TradePlanModel,
    TradePlanTargetModel,
    TradePlanVersionModel,
)


class TradePlanRepository(Protocol):
    async def add(self, plan: TradePlan) -> None: ...
    async def get(self, workspace_id: UUID, trade_plan_id: UUID) -> TradePlan | None: ...
    async def list_for_underlying(
        self, workspace_id: UUID, underlying_id: UUID
    ) -> Sequence[TradePlan]: ...
    async def lock(self, workspace_id: UUID, trade_plan_id: UUID) -> bool: ...


class TradePlanVersionRepository(Protocol):
    async def add(self, version: TradePlanVersion) -> None: ...
    async def get(self, trade_plan_id: UUID, version_id: UUID) -> TradePlanVersion | None: ...
    async def get_by_number(self, trade_plan_id: UUID, version: int) -> TradePlanVersion | None: ...
    async def latest(self, trade_plan_id: UUID) -> TradePlanVersion | None: ...
    async def list(self, trade_plan_id: UUID) -> Sequence[TradePlanVersion]: ...
    async def next_version_number(self, workspace_id: UUID, trade_plan_id: UUID) -> int: ...
    async def set_status(self, trade_plan_id: UUID, version_id: UUID, status: str) -> None: ...


class TradePlanEventRepository(Protocol):
    async def add(self, event: TradePlanEventModel) -> None: ...
    async def list_for_version(self, version_id: UUID) -> Sequence[TradePlanEventModel]: ...


class TradePlanApprovalRepository(Protocol):
    async def add(self, approval: TradePlanApprovalModel) -> None: ...
    async def get_for_version(self, version_id: UUID) -> TradePlanApprovalModel | None: ...


class SqlAlchemyTradePlanRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, plan: TradePlan) -> None:
        self._session.add(trade_plan_to_model(plan))
        # Materialize the durable parent identity before any dependent TradePlanVersion
        # or lifecycle event rows are staged. SQLAlchemy has no ORM relationship graph
        # between these independently-mapped models, so relying on commit-time ordering
        # can otherwise emit child INSERTs before their FK parent exists.
        await self._session.flush()

    async def get(self, workspace_id: UUID, trade_plan_id: UUID) -> TradePlan | None:
        model = await self._session.scalar(
            select(TradePlanModel).where(
                TradePlanModel.id == trade_plan_id,
                TradePlanModel.workspace_id == workspace_id,
            )
        )
        return trade_plan_from_model(model) if model is not None else None

    async def list_for_underlying(
        self, workspace_id: UUID, underlying_id: UUID
    ) -> Sequence[TradePlan]:
        models = (
            await self._session.scalars(
                select(TradePlanModel)
                .where(
                    TradePlanModel.workspace_id == workspace_id,
                    TradePlanModel.underlying_id == underlying_id,
                )
                .order_by(TradePlanModel.created_at.desc())
            )
        ).all()
        return tuple(trade_plan_from_model(model) for model in models)

    async def lock(self, workspace_id: UUID, trade_plan_id: UUID) -> bool:
        value = await self._session.scalar(
            select(TradePlanModel.id)
            .where(
                TradePlanModel.id == trade_plan_id,
                TradePlanModel.workspace_id == workspace_id,
            )
            .with_for_update()
        )
        return value is not None


class SqlAlchemyTradePlanVersionRepository:
    def __init__(self, session: AsyncSession, plans: TradePlanRepository) -> None:
        self._session = session
        self._plans = plans

    async def add(self, version: TradePlanVersion) -> None:
        version_model, target_models = trade_plan_version_to_models(version)
        self._session.add(version_model)
        self._session.add_all(list(target_models))
        # Events and targets reference the immutable version identity. Flush the version
        # (and its targets) before callers stage lifecycle events so FK ordering remains
        # deterministic for both initial creation and later amendments.
        await self._session.flush()

    async def _hydrate(self, model: TradePlanVersionModel) -> TradePlanVersion:
        targets = tuple(
            (
                await self._session.scalars(
                    select(TradePlanTargetModel)
                    .where(TradePlanTargetModel.trade_plan_version_id == model.id)
                    .order_by(TradePlanTargetModel.sequence)
                )
            ).all()
        )
        return trade_plan_version_from_models(model, targets)

    async def get(self, trade_plan_id: UUID, version_id: UUID) -> TradePlanVersion | None:
        model = await self._session.scalar(
            select(TradePlanVersionModel).where(
                TradePlanVersionModel.trade_plan_id == trade_plan_id,
                TradePlanVersionModel.id == version_id,
            )
        )
        return await self._hydrate(model) if model is not None else None

    async def get_by_number(self, trade_plan_id: UUID, version: int) -> TradePlanVersion | None:
        model = await self._session.scalar(
            select(TradePlanVersionModel).where(
                TradePlanVersionModel.trade_plan_id == trade_plan_id,
                TradePlanVersionModel.version == version,
            )
        )
        return await self._hydrate(model) if model is not None else None

    async def latest(self, trade_plan_id: UUID) -> TradePlanVersion | None:
        model = await self._session.scalar(
            select(TradePlanVersionModel)
            .where(TradePlanVersionModel.trade_plan_id == trade_plan_id)
            .order_by(TradePlanVersionModel.version.desc())
            .limit(1)
        )
        return await self._hydrate(model) if model is not None else None

    async def list(self, trade_plan_id: UUID) -> Sequence[TradePlanVersion]:
        models = (
            await self._session.scalars(
                select(TradePlanVersionModel)
                .where(TradePlanVersionModel.trade_plan_id == trade_plan_id)
                .order_by(TradePlanVersionModel.version.desc())
            )
        ).all()
        return tuple([await self._hydrate(model) for model in models])

    async def next_version_number(self, workspace_id: UUID, trade_plan_id: UUID) -> int:
        # Lock the durable plan identity before deriving MAX(version)+1. All writers must
        # use this method in the same Unit-of-Work transaction to serialize amendments.
        if not await self._plans.lock(workspace_id, trade_plan_id):
            raise LookupError("trade plan not found")
        latest = await self._session.scalar(
            select(func.max(TradePlanVersionModel.version)).where(
                TradePlanVersionModel.trade_plan_id == trade_plan_id
            )
        )
        return int(latest or 0) + 1

    async def set_status(self, trade_plan_id: UUID, version_id: UUID, status: str) -> None:
        model = await self._session.scalar(
            select(TradePlanVersionModel).where(
                TradePlanVersionModel.trade_plan_id == trade_plan_id,
                TradePlanVersionModel.id == version_id,
            )
        )
        if model is None:
            raise LookupError("trade plan version not found")
        model.status = status


class SqlAlchemyTradePlanEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, event: TradePlanEventModel) -> None:
        self._session.add(event)

    async def list_for_version(self, version_id: UUID) -> Sequence[TradePlanEventModel]:
        return tuple(
            (
                await self._session.scalars(
                    select(TradePlanEventModel)
                    .where(TradePlanEventModel.trade_plan_version_id == version_id)
                    .order_by(TradePlanEventModel.occurred_at, TradePlanEventModel.id)
                )
            ).all()
        )


class SqlAlchemyTradePlanApprovalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, approval: TradePlanApprovalModel) -> None:
        self._session.add(approval)

    async def get_for_version(self, version_id: UUID) -> TradePlanApprovalModel | None:
        value = await self._session.scalar(
            select(TradePlanApprovalModel).where(
                TradePlanApprovalModel.trade_plan_version_id == version_id
            )
        )
        return value
