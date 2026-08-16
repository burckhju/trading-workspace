"""Unit of work for durable FT-008 snapshots."""

from __future__ import annotations

from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.product_selection.persistence.repositories import (
    SqlAlchemyProductEvaluationRepository,
    SqlAlchemyProductSelectionRepository,
    SqlAlchemyProductSelectionRunRepository,
    SqlAlchemyProductUniverseOmissionRepository,
)


class SqlAlchemyProductSelectionUnitOfWork:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.runs = SqlAlchemyProductSelectionRunRepository(session)
        self.evaluations = SqlAlchemyProductEvaluationRepository(session)
        self.omissions = SqlAlchemyProductUniverseOmissionRepository(session)
        self.selections = SqlAlchemyProductSelectionRepository(session)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()

    async def flush(self) -> None:
        await self._session.flush()

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
