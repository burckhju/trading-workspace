"""Atomic write orchestration for FT-008 historical Product Selection snapshots."""

from __future__ import annotations

from types import TracebackType
from typing import Protocol, Self

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.product_selection.domain.models import ProductSelection
from app.features.product_selection.persistence.repositories import (
    SqlAlchemyProductEvaluationRepository,
    SqlAlchemyProductSelectionRepository,
    SqlAlchemyProductSelectionRunRepository,
    SqlAlchemyProductUniverseOmissionRepository,
)
from app.features.product_selection.persistence.unit_of_work import (
    SqlAlchemyProductSelectionUnitOfWork,
)
from app.features.product_selection.service.application import ProductSelectionRunResult


class ProductSelectionWriteUnitOfWork(Protocol):
    runs: SqlAlchemyProductSelectionRunRepository
    evaluations: SqlAlchemyProductEvaluationRepository
    omissions: SqlAlchemyProductUniverseOmissionRepository
    selections: SqlAlchemyProductSelectionRepository

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    async def flush(self) -> None: ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...


class ProductSelectionPersistenceService:
    """Persist complete immutable run snapshots and explicit later user selections."""

    def __init__(self, uow: ProductSelectionWriteUnitOfWork) -> None:
        self._uow = uow

    async def persist_run(self, result: ProductSelectionRunResult) -> None:
        async with self._uow:
            await self._uow.runs.add(result.run)
            for evaluation in result.evaluations:
                await self._uow.evaluations.add(evaluation)
            await self._uow.omissions.add_all(result.run.id, result.universe_omissions)
            await self._uow.flush()
            await self._uow.commit()

    async def persist_selection(self, selection: ProductSelection) -> None:
        """Persist a domain-approved user decision.

        Override policy is intentionally not decided here.
        """
        async with self._uow:
            await self._uow.selections.add(selection)
            await self._uow.flush()
            await self._uow.commit()


def sqlalchemy_persistence_service(
    session: AsyncSession,
) -> ProductSelectionPersistenceService:
    return ProductSelectionPersistenceService(SqlAlchemyProductSelectionUnitOfWork(session))
