"""Explicit append-only currency commands beside the immutable execution facts."""

import hashlib
import json
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions.types import ApplicationError
from app.features.market.persistence.repositories import SqlAlchemyReferenceDataRepository
from app.features.trade_position.domain.currency import (
    ExecutionCurrencyConfirmation,
    ExecutionCurrencyDeclaration,
    ExecutionCurrencyResolution,
)
from app.features.trade_position.domain.currency_resolution import resolve_execution_currencies
from app.features.trade_position.domain.models import ExecutionRecord
from app.features.trade_position.persistence.currency_repository import (
    SqlAlchemyExecutionCurrencyConfirmationRepository,
)
from app.features.trade_position.persistence.models import ExecutionRecordModel, TradeModel
from app.features.trade_position.persistence.unit_of_work import SqlAlchemyTradePositionUnitOfWork
from app.features.trade_position.service.errors import capture_conflict


def confirmation_fingerprint(
    *,
    trade_id: UUID,
    execution_id: UUID,
    declaration: ExecutionCurrencyDeclaration,
    supersedes_confirmation_id: UUID | None,
) -> str:
    payload = {
        "trade_id": str(trade_id),
        "execution_id": str(execution_id),
        "declaration": declaration.payload(),
        "supersedes_confirmation_id": (
            str(supersedes_confirmation_id) if supersedes_confirmation_id is not None else None
        ),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


class ExecutionCurrencyConfirmationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = SqlAlchemyExecutionCurrencyConfirmationRepository(session)
        self._currencies = SqlAlchemyReferenceDataRepository(session)

    async def _validate_currency(self, declaration: ExecutionCurrencyDeclaration) -> None:
        # Existing historical currencies remain valid provenance even if inactive today.
        if await self._currencies.get_currency(declaration.currency_code) is None:
            raise ApplicationError(
                code="CURRENCY_NOT_FOUND",
                message="Die angegebene Währung ist im Währungskatalog nicht bekannt.",
                status_code=422,
            )

    async def _require_execution(
        self, workspace_id: UUID, trade_id: UUID, execution_id: UUID
    ) -> None:
        found = await self._session.scalar(
            select(ExecutionRecordModel.id)
            .join(TradeModel, TradeModel.id == ExecutionRecordModel.trade_id)
            .where(
                TradeModel.workspace_id == workspace_id,
                TradeModel.id == trade_id,
                ExecutionRecordModel.id == execution_id,
            )
        )
        if found is None:
            raise ApplicationError(
                code="EXECUTION_NOT_FOUND",
                message="Die Ausführung wurde in diesem Workspace und Trade nicht gefunden.",
                status_code=404,
            )

    async def current_for_trade(
        self, workspace_id: UUID, trade_id: UUID
    ) -> dict[UUID, ExecutionCurrencyConfirmation]:
        return await self._repository.current_for_trade(workspace_id, trade_id)

    async def history(
        self, workspace_id: UUID, trade_id: UUID, execution_id: UUID
    ) -> tuple[ExecutionCurrencyConfirmation | None, tuple[ExecutionCurrencyConfirmation, ...]]:
        await self._require_execution(workspace_id, trade_id, execution_id)
        history = await self._repository.history(workspace_id, trade_id, execution_id)
        # Both output parts use this one immutable query result, including during a correction.
        superseded = {item.supersedes_confirmation_id for item in history}
        current = next((item for item in history if item.id not in superseded), None)
        return current, history

    async def history_with_resolution(
        self, workspace_id: UUID, trade_id: UUID, execution_id: UUID
    ) -> tuple[
        ExecutionCurrencyConfirmation | None,
        tuple[ExecutionCurrencyConfirmation, ...],
        ExecutionCurrencyResolution,
    ]:
        # Capture, correction and confirmation commands already lock this trade.
        # This short owner read uses that same boundary so history and derivation
        # cannot observe different confirmation/correction states. No commit/write.
        async with SqlAlchemyTradePositionUnitOfWork(self._session) as uow:
            trade = await uow.trades.get(workspace_id, trade_id)
            if trade is None:
                raise ApplicationError(
                    code="EXECUTION_NOT_FOUND", message="Trade nicht gefunden.", status_code=404
                )
            current, history = await self.history(workspace_id, trade_id, execution_id)
            executions = await uow.executions.list_for_trade(trade_id)
            confirmations = await self.current_for_trade(workspace_id, trade_id)
            resolutions = resolve_execution_currencies(
                trade=trade, executions=executions, current=confirmations
            )
            return current, history, resolutions[execution_id]

    async def capture(
        self,
        *,
        workspace_id: UUID,
        execution: ExecutionRecord,
        declaration: ExecutionCurrencyDeclaration,
        actor: UUID,
    ) -> ExecutionRecord:
        """Bind a new declaration atomically; the surrounding capture owns commit/rollback."""
        await self._validate_currency(declaration)
        await self._session.flush()  # Make the new execution FK visible in the same transaction.
        confirmation = self._new_confirmation(
            workspace_id=workspace_id,
            trade_id=execution.trade_id,
            execution_id=execution.id,
            declaration=declaration,
            actor=actor,
            request_id=execution.id,
            supersedes_confirmation_id=None,
        )
        await self._repository.add(confirmation)
        return replace(execution, currency_confirmation=confirmation)

    async def confirm(
        self,
        *,
        workspace_id: UUID,
        trade_id: UUID,
        execution_id: UUID,
        declaration: ExecutionCurrencyDeclaration,
        actor: UUID,
        request_id: UUID,
        supersedes_confirmation_id: UUID | None,
    ) -> ExecutionCurrencyConfirmation:
        fingerprint = confirmation_fingerprint(
            trade_id=trade_id,
            execution_id=execution_id,
            declaration=declaration,
            supersedes_confirmation_id=supersedes_confirmation_id,
        )
        try:
            async with SqlAlchemyTradePositionUnitOfWork(self._session) as uow:
                trade = await uow.trades.get(
                    workspace_id, trade_id
                )  # Existing per-trade command lock.
                if trade is None:
                    raise ApplicationError(
                        code="EXECUTION_NOT_FOUND", message="Trade nicht gefunden.", status_code=404
                    )
                if trade.cancelled_at is not None:
                    raise capture_conflict("TRADE_CANCELLED", "Dieser Trade wurde storniert.")
                await self._require_execution(workspace_id, trade_id, execution_id)
                replay = await self._repository.find_request(workspace_id, request_id)
                if replay is not None:
                    if replay.request_fingerprint != fingerprint:
                        raise capture_conflict(
                            "EXECUTION_CURRENCY_REQUEST_CONFLICT",
                            "Diese Vorgangskennung gehört zu einer anderen Währungsbestätigung.",
                        )
                    return replay
                current = (await self.current_for_trade(workspace_id, trade_id)).get(execution_id)
                if supersedes_confirmation_id != (current.id if current is not None else None):
                    raise capture_conflict(
                        "EXECUTION_CURRENCY_CONFLICT",
                        "Die Währungsbestätigung hat sich geändert. "
                        "Bitte den aktuellen Stand laden.",
                    )
                await self._validate_currency(declaration)
                confirmation = self._new_confirmation(
                    workspace_id=workspace_id,
                    trade_id=trade_id,
                    execution_id=execution_id,
                    declaration=declaration,
                    actor=actor,
                    request_id=request_id,
                    supersedes_confirmation_id=supersedes_confirmation_id,
                )
                await self._repository.add(confirmation)
                await uow.commit()
                return confirmation
        except IntegrityError as error:
            constraint = getattr(getattr(error.orig, "__cause__", None), "constraint_name", None)
            if constraint == "uq_execution_currency_request":
                raise capture_conflict(
                    "EXECUTION_CURRENCY_REQUEST_CONFLICT",
                    "Diese Vorgangskennung wurde bereits für eine andere Bestätigung verwendet.",
                ) from error
            if constraint in {"uq_execution_currency_root", "uq_execution_currency_successor"}:
                raise capture_conflict(
                    "EXECUTION_CURRENCY_CONFLICT", "Die Währungsbestätigung wurde bereits ersetzt."
                ) from error
            raise

    @staticmethod
    def _new_confirmation(
        *,
        workspace_id: UUID,
        trade_id: UUID,
        execution_id: UUID,
        declaration: ExecutionCurrencyDeclaration,
        actor: UUID,
        request_id: UUID,
        supersedes_confirmation_id: UUID | None,
    ) -> ExecutionCurrencyConfirmation:
        return ExecutionCurrencyConfirmation(
            id=uuid4(),
            workspace_id=workspace_id,
            trade_id=trade_id,
            execution_id=execution_id,
            currency_code=declaration.currency_code,
            source=declaration.source,
            note=declaration.note,
            confirmed_at=datetime.now(UTC),
            confirmed_by=actor,
            supersedes_confirmation_id=supersedes_confirmation_id,
            request_id=request_id,
            request_fingerprint=confirmation_fingerprint(
                trade_id=trade_id,
                execution_id=execution_id,
                declaration=declaration,
                supersedes_confirmation_id=supersedes_confirmation_id,
            ),
        )
