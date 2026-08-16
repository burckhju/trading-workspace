"""Explicit user commands for FT-008 Product Selection."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.features.product_selection.domain.models import ProductSelection
from app.features.product_selection.persistence.unit_of_work import (
    SqlAlchemyProductSelectionUnitOfWork,
)


class ProductSelectionCommandService:
    """Create an explicit V1 user selection atomically from persisted run state."""

    def __init__(self, uow: SqlAlchemyProductSelectionUnitOfWork) -> None:
        self._uow = uow

    async def select_product(
        self,
        *,
        workspace_id: UUID,
        run_id: UUID,
        evaluation_id: UUID,
        actor: UUID,
        rationale: str | None = None,
        selected_at: datetime | None = None,
    ) -> ProductSelection:
        async with self._uow:
            run = await self._uow.runs.get(workspace_id, run_id)
            if run is None:
                raise ValueError("product selection run not found")

            existing = await self._uow.selections.get_for_run(run.id)
            if existing is not None:
                raise ValueError("product selection run already has a user selection")

            evaluation = await self._uow.evaluations.get(run.id, evaluation_id)
            if evaluation is None:
                raise ValueError("product evaluation not found for run")

            selection = ProductSelection.from_user_decision(
                id=uuid4(),
                run=run,
                evaluation=evaluation,
                selected_at=selected_at or datetime.now(UTC),
                selected_by=actor,
                rationale=rationale,
            )
            await self._uow.selections.add(selection)
            await self._uow.flush()
            await self._uow.commit()
            return selection
