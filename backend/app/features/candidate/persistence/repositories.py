"""Persistence adapters for FT-005 candidate application services."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.candidate.persistence.models import (
    CandidateCriterionModel,
    CandidateEvaluationModel,
    CandidateModel,
)
from app.features.market.persistence.models import UnderlyingModel


class SqlAlchemyCandidateRepository:
    """Encapsulate Candidate persistence queries behind the persistence boundary."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def underlying_exists(self, workspace_id: UUID, underlying_id: UUID) -> bool:
        value = await self._session.scalar(
            select(UnderlyingModel.id).where(
                UnderlyingModel.id == underlying_id,
                UnderlyingModel.workspace_id == workspace_id,
            )
        )
        return value is not None

    async def get_by_underlying(
        self, workspace_id: UUID, underlying_id: UUID
    ) -> CandidateModel | None:
        value = await self._session.scalar(
            select(CandidateModel).where(
                CandidateModel.workspace_id == workspace_id,
                CandidateModel.underlying_id == underlying_id,
            )
        )
        return value

    async def get(self, workspace_id: UUID, candidate_id: UUID) -> CandidateModel | None:
        value = await self._session.scalar(
            select(CandidateModel).where(
                CandidateModel.workspace_id == workspace_id,
                CandidateModel.id == candidate_id,
            )
        )
        return value

    async def list(self, workspace_id: UUID) -> tuple[CandidateModel, ...]:
        return tuple(
            (
                await self._session.scalars(
                    select(CandidateModel)
                    .where(CandidateModel.workspace_id == workspace_id)
                    .order_by(CandidateModel.created_at.desc())
                )
            ).all()
        )

    async def next_evaluation_version(self, candidate_id: UUID) -> int:
        latest = await self._session.scalar(
            select(func.max(CandidateEvaluationModel.version)).where(
                CandidateEvaluationModel.candidate_id == candidate_id
            )
        )
        return int(latest or 0) + 1

    async def list_evaluations(self, candidate_id: UUID) -> tuple[CandidateEvaluationModel, ...]:
        return tuple(
            (
                await self._session.scalars(
                    select(CandidateEvaluationModel)
                    .where(CandidateEvaluationModel.candidate_id == candidate_id)
                    .order_by(CandidateEvaluationModel.version.desc())
                )
            ).all()
        )

    async def list_criteria(self, evaluation_id: UUID) -> tuple[CandidateCriterionModel, ...]:
        return tuple(
            (
                await self._session.scalars(
                    select(CandidateCriterionModel)
                    .where(CandidateCriterionModel.evaluation_id == evaluation_id)
                    .order_by(
                        CandidateCriterionModel.criterion_group,
                        CandidateCriterionModel.criterion_id,
                    )
                )
            ).all()
        )

    def add(self, model: object) -> None:
        self._session.add(model)

    def add_all(self, models: Sequence[object]) -> None:
        self._session.add_all(models)

    async def flush(self) -> None:
        await self._session.flush()

    async def commit(self) -> None:
        await self._session.commit()
