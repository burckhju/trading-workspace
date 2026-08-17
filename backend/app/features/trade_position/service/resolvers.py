"""Read-only consumer adapters for FT-009 upstream feature contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.product.persistence.models import WarrantModel
from app.features.product.service.errors import WarrantNotFound
from app.features.product_selection.persistence.models import (
    ProductEvaluationModel,
    ProductSelectionModel,
    ProductSelectionRunModel,
)


@dataclass(frozen=True, slots=True)
class ResolvedWorkspaceSelection:
    workspace_id: UUID
    product_id: UUID
    trade_plan_id: UUID
    trade_plan_version_id: UUID
    product_selection_id: UUID
    product_evaluation_id: UUID


@dataclass(frozen=True, slots=True)
class ResolvedProduct:
    workspace_id: UUID
    product_id: UUID


class WarrantReader(Protocol):
    async def get(
        self,
        workspace_id: UUID,
        warrant_id: UUID,
    ) -> WarrantModel: ...


class SqlAlchemyWorkspaceSelectionResolver:
    """Resolve one exact FT-008 selection without changing FT-008 repositories."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def resolve(
        self,
        workspace_id: UUID,
        product_selection_id: UUID,
    ) -> ResolvedWorkspaceSelection | None:
        selection = await self._session.scalar(
            select(ProductSelectionModel).where(
                ProductSelectionModel.id == product_selection_id,
            )
        )
        if selection is None:
            return None

        run = await self._session.scalar(
            select(ProductSelectionRunModel).where(
                ProductSelectionRunModel.id == selection.run_id,
                ProductSelectionRunModel.workspace_id == workspace_id,
            )
        )
        if run is None or run.workspace_id != workspace_id:
            return None

        evaluation = await self._session.scalar(
            select(ProductEvaluationModel).where(
                ProductEvaluationModel.id == selection.product_evaluation_id,
                ProductEvaluationModel.run_id == selection.run_id,
            )
        )
        if evaluation is None:
            return None

        return ResolvedWorkspaceSelection(
            workspace_id=run.workspace_id,
            product_id=evaluation.warrant_id,
            trade_plan_id=run.trade_plan_id,
            trade_plan_version_id=run.trade_plan_version_id,
            product_selection_id=selection.id,
            product_evaluation_id=evaluation.id,
        )


class WarrantProductResolver:
    """Resolve an existing FT-004 warrant for an external FT-009 trade."""

    def __init__(self, warrants: WarrantReader) -> None:
        self._warrants = warrants

    async def resolve(
        self,
        workspace_id: UUID,
        product_id: UUID,
    ) -> ResolvedProduct | None:
        try:
            warrant = await self._warrants.get(
                workspace_id,
                product_id,
            )
        except WarrantNotFound:
            return None

        return ResolvedProduct(
            workspace_id=warrant.workspace_id,
            product_id=warrant.id,
        )
