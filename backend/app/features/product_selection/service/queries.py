"""Read-side queries for immutable FT-008 Product Selection snapshots."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.product_selection.domain.models import (
    ProductEvaluation,
    ProductSelection,
    ProductSelectionRun,
)
from app.features.product_selection.persistence.repositories import (
    SqlAlchemyProductEvaluationRepository,
    SqlAlchemyProductSelectionRepository,
    SqlAlchemyProductSelectionRunRepository,
    SqlAlchemyProductUniverseOmissionRepository,
)
from app.features.product_selection.service.universe import UniverseOmission


@dataclass(frozen=True, slots=True)
class ProductSelectionRunView:
    run: ProductSelectionRun
    evaluations: tuple[ProductEvaluation, ...]
    universe_omissions: tuple[UniverseOmission, ...]
    selection: ProductSelection | None


class ProductSelectionQueryService:
    def __init__(self, session: AsyncSession) -> None:
        self._runs = SqlAlchemyProductSelectionRunRepository(session)
        self._evaluations = SqlAlchemyProductEvaluationRepository(session)
        self._omissions = SqlAlchemyProductUniverseOmissionRepository(session)
        self._selections = SqlAlchemyProductSelectionRepository(session)

    async def get_run(
        self,
        workspace_id: UUID,
        run_id: UUID,
    ) -> ProductSelectionRunView:
        run = await self._runs.get(workspace_id, run_id)
        if run is None:
            raise ValueError("product selection run not found")
        return ProductSelectionRunView(
            run=run,
            evaluations=tuple(await self._evaluations.list_for_run(run.id)),
            universe_omissions=tuple(await self._omissions.list_for_run(run.id)),
            selection=await self._selections.get_for_run(run.id),
        )

    async def list_for_trade_plan_version(
        self,
        workspace_id: UUID,
        version_id: UUID,
    ) -> Sequence[ProductSelectionRun]:
        return await self._runs.list_for_trade_plan_version(workspace_id, version_id)

    async def get_evaluation(
        self,
        workspace_id: UUID,
        run_id: UUID,
        evaluation_id: UUID,
    ) -> ProductEvaluation:
        run = await self._runs.get(workspace_id, run_id)
        if run is None:
            raise ValueError("product selection run not found")
        evaluation = await self._evaluations.get(run.id, evaluation_id)
        if evaluation is None:
            raise ValueError("product evaluation not found for run")
        return evaluation
