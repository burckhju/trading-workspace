"""SQLAlchemy repositories for durable FT-008 selection snapshots."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.product_selection.domain.models import (
    ProductEvaluation,
    ProductSelection,
    ProductSelectionRun,
)
from app.features.product_selection.persistence.mapping import (
    evaluation_from_models,
    evaluation_to_models,
    omission_from_model,
    omission_to_model,
    run_from_model,
    run_to_model,
    selection_from_model,
    selection_to_model,
)
from app.features.product_selection.persistence.models import (
    ProductEvaluationCriterionModel,
    ProductEvaluationInputModel,
    ProductEvaluationMetricModel,
    ProductEvaluationModel,
    ProductEvaluationReasonModel,
    ProductSelectionModel,
    ProductSelectionRunModel,
    ProductUniverseOmissionModel,
)
from app.features.product_selection.service.universe import UniverseOmission


class SqlAlchemyProductSelectionRunRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add(self, run: ProductSelectionRun) -> None:
        self._session.add(run_to_model(run))

    async def get(self, workspace_id: UUID, run_id: UUID) -> ProductSelectionRun | None:
        model = await self._session.scalar(
            select(ProductSelectionRunModel).where(
                ProductSelectionRunModel.id == run_id,
                ProductSelectionRunModel.workspace_id == workspace_id,
            )
        )
        return run_from_model(model) if model else None

    async def list_for_trade_plan_version(
        self, workspace_id: UUID, version_id: UUID
    ) -> Sequence[ProductSelectionRun]:
        rows = (
            await self._session.scalars(
                select(ProductSelectionRunModel)
                .where(
                    ProductSelectionRunModel.workspace_id == workspace_id,
                    ProductSelectionRunModel.trade_plan_version_id == version_id,
                )
                .order_by(ProductSelectionRunModel.evaluated_at.desc(), ProductSelectionRunModel.id)
            )
        ).all()
        return tuple(run_from_model(x) for x in rows)


class SqlAlchemyProductEvaluationRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add(self, evaluation: ProductEvaluation) -> None:
        root, inputs, criteria, metrics, reasons = evaluation_to_models(evaluation)
        self._session.add(root)
        self._session.add_all([*inputs, *criteria, *metrics, *reasons])

    async def _hydrate(
        self,
        model: ProductEvaluationModel,
    ) -> ProductEvaluation:
        inputs = (
            await self._session.scalars(
                select(ProductEvaluationInputModel)
                .where(ProductEvaluationInputModel.product_evaluation_id == model.id)
                .order_by(ProductEvaluationInputModel.sequence)
            )
        ).all()

        criteria = (
            await self._session.scalars(
                select(ProductEvaluationCriterionModel)
                .where(ProductEvaluationCriterionModel.product_evaluation_id == model.id)
                .order_by(ProductEvaluationCriterionModel.sequence)
            )
        ).all()

        metrics = (
            await self._session.scalars(
                select(ProductEvaluationMetricModel)
                .where(ProductEvaluationMetricModel.product_evaluation_id == model.id)
                .order_by(ProductEvaluationMetricModel.sequence)
            )
        ).all()

        reasons = (
            await self._session.scalars(
                select(ProductEvaluationReasonModel)
                .where(ProductEvaluationReasonModel.product_evaluation_id == model.id)
                .order_by(ProductEvaluationReasonModel.sequence)
            )
        ).all()

        return evaluation_from_models(
            model,
            inputs,
            criteria,
            metrics,
            reasons,
        )

    async def get(self, run_id: UUID, evaluation_id: UUID) -> ProductEvaluation | None:
        model = await self._session.scalar(
            select(ProductEvaluationModel).where(
                ProductEvaluationModel.id == evaluation_id, ProductEvaluationModel.run_id == run_id
            )
        )
        return await self._hydrate(model) if model else None

    async def list_for_run(self, run_id: UUID) -> Sequence[ProductEvaluation]:
        models = (
            await self._session.scalars(
                select(ProductEvaluationModel)
                .where(ProductEvaluationModel.run_id == run_id)
                .order_by(ProductEvaluationModel.id)
            )
        ).all()
        return tuple([await self._hydrate(x) for x in models])


class SqlAlchemyProductUniverseOmissionRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add_all(self, run_id: UUID, omissions: Sequence[UniverseOmission]) -> None:
        self._session.add_all([omission_to_model(run_id, x) for x in omissions])

    async def list_for_run(self, run_id: UUID) -> Sequence[UniverseOmission]:
        rows = (
            await self._session.scalars(
                select(ProductUniverseOmissionModel)
                .where(ProductUniverseOmissionModel.run_id == run_id)
                .order_by(
                    ProductUniverseOmissionModel.warrant_id, ProductUniverseOmissionModel.reason
                )
            )
        ).all()
        return tuple(omission_from_model(x) for x in rows)


class SqlAlchemyProductSelectionRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add(self, selection: ProductSelection) -> None:
        self._session.add(selection_to_model(selection))

    async def get_for_run(self, run_id: UUID) -> ProductSelection | None:
        model = await self._session.scalar(
            select(ProductSelectionModel).where(ProductSelectionModel.run_id == run_id)
        )
        return selection_from_model(model) if model else None
