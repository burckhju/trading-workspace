"""Execution-owner currency reads and inserts in the caller's transaction."""

from uuid import UUID

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.trade_position.domain.currency import (
    ExecutionCurrencyConfirmation,
    ExecutionCurrencySource,
)
from app.features.trade_position.persistence.currency_models import (
    ExecutionCurrencyConfirmationModel,
)


class SqlAlchemyExecutionCurrencyConfirmationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, confirmation: ExecutionCurrencyConfirmation) -> None:
        self._session.add(
            ExecutionCurrencyConfirmationModel(
                id=confirmation.id,
                workspace_id=confirmation.workspace_id,
                trade_id=confirmation.trade_id,
                execution_id=confirmation.execution_id,
                currency_code=confirmation.currency_code,
                source=confirmation.source.value,
                note=confirmation.note,
                confirmed_at=confirmation.confirmed_at,
                confirmed_by=confirmation.confirmed_by,
                supersedes_confirmation_id=confirmation.supersedes_confirmation_id,
                request_id=confirmation.request_id,
                request_fingerprint=confirmation.request_fingerprint,
            )
        )
        await self._session.flush()

    async def find_request(
        self, workspace_id: UUID, request_id: UUID
    ) -> ExecutionCurrencyConfirmation | None:
        model = await self._session.scalar(
            select(ExecutionCurrencyConfirmationModel).where(
                ExecutionCurrencyConfirmationModel.workspace_id == workspace_id,
                ExecutionCurrencyConfirmationModel.request_id == request_id,
            )
        )
        return None if model is None else self._to_domain(model)

    async def history(
        self, workspace_id: UUID, trade_id: UUID, execution_id: UUID
    ) -> tuple[ExecutionCurrencyConfirmation, ...]:
        models = await self._session.scalars(
            select(ExecutionCurrencyConfirmationModel)
            .where(
                ExecutionCurrencyConfirmationModel.workspace_id == workspace_id,
                ExecutionCurrencyConfirmationModel.trade_id == trade_id,
                ExecutionCurrencyConfirmationModel.execution_id == execution_id,
            )
            .order_by(
                ExecutionCurrencyConfirmationModel.confirmed_at,
                ExecutionCurrencyConfirmationModel.id,
            )
        )
        return tuple(self._to_domain(model) for model in models)

    async def current_for_trade(
        self, workspace_id: UUID, trade_id: UUID
    ) -> dict[UUID, ExecutionCurrencyConfirmation]:
        replacement = ExecutionCurrencyConfirmationModel.__table__.alias("currency_replacement")
        models = await self._session.scalars(
            select(ExecutionCurrencyConfirmationModel).where(
                ExecutionCurrencyConfirmationModel.workspace_id == workspace_id,
                ExecutionCurrencyConfirmationModel.trade_id == trade_id,
                ~exists(
                    select(1)
                    .select_from(replacement)
                    .where(
                        replacement.c.supersedes_confirmation_id
                        == ExecutionCurrencyConfirmationModel.id
                    )
                ),
            )
        )
        return {model.execution_id: self._to_domain(model) for model in models}

    @staticmethod
    def _to_domain(model: ExecutionCurrencyConfirmationModel) -> ExecutionCurrencyConfirmation:
        return ExecutionCurrencyConfirmation(
            id=model.id,
            workspace_id=model.workspace_id,
            trade_id=model.trade_id,
            execution_id=model.execution_id,
            currency_code=model.currency_code,
            source=ExecutionCurrencySource(model.source),
            note=model.note,
            confirmed_at=model.confirmed_at,
            confirmed_by=model.confirmed_by,
            supersedes_confirmation_id=model.supersedes_confirmation_id,
            request_id=model.request_id,
            request_fingerprint=model.request_fingerprint,
        )
