"""One short, local PostgreSQL snapshot; no command repositories or providers."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.features.market.persistence.models import CurrencyModel
from app.features.performance.domain.models import (
    Confirmation,
    CurrencyReference,
    ExecutionFact,
    ReportSnapshot,
    TradeFact,
)
from app.features.performance.domain.report import ReportLimitExceeded
from app.features.product.persistence.models import WarrantModel
from app.features.trade_position.domain.enums import TradeOrigin
from app.features.trade_position.domain.models import Trade
from app.features.trade_position.persistence.currency_models import (
    ExecutionCurrencyConfirmationModel,
)
from app.features.trade_position.persistence.models import (
    ExecutionRecordModel,
    PositionModel,
    TradeModel,
)

MAX_TRADES = 2_000
MAX_EXECUTIONS = 20_000
MAX_CONFIRMATIONS = 40_000


class RealizedGrossSnapshotReader:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def read(self, workspace_id: UUID, currency_code: str) -> ReportSnapshot:
        started = datetime.now(UTC)
        async with (
            AsyncSession(self._engine, expire_on_commit=False, autoflush=False) as session,
            session.begin(),
        ):
            # Set before the first data statement. This does not change the
            # engine, pooled connections' defaults, or any other request.
            await session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
            await session.execute(text("SET LOCAL statement_timeout = '10000ms'"))
            currency = await session.get(CurrencyModel, currency_code)
            if currency is None:
                raise ValueError("Unknown report currency")
            reference = CurrencyReference(
                currency.code, currency.minor_unit, currency.reference_version
            )
            trades = await self._read_trades(session, workspace_id)
            executions = await self._read_executions(session, workspace_id)
            confirmations = await self._read_confirmations(session, workspace_id)
            result = ReportSnapshot(
                workspace_id=workspace_id,
                trades=trades,
                executions=executions,
                confirmations=confirmations,
                currency=reference,
                read_started_at=started,
                read_completed_at=datetime.now(UTC),
            )
        return result

    async def _read_trades(
        self, session: AsyncSession, workspace_id: UUID
    ) -> tuple[TradeFact, ...]:
        rows = (
            await session.execute(
                select(TradeModel, WarrantModel.display_name, PositionModel.id)
                .outerjoin(
                    WarrantModel,
                    (WarrantModel.id == TradeModel.product_id)
                    & (WarrantModel.workspace_id == workspace_id),
                )
                .outerjoin(PositionModel, PositionModel.trade_id == TradeModel.id)
                .where(TradeModel.workspace_id == workspace_id)
                .order_by(TradeModel.id)
                .limit(MAX_TRADES + 1)
            )
        ).all()
        if len(rows) > MAX_TRADES:
            raise ReportLimitExceeded("Report exceeds the complete trade limit")
        return tuple(
            TradeFact(
                trade=Trade(
                    id=row.id,
                    workspace_id=row.workspace_id,
                    product_id=row.product_id,
                    origin=TradeOrigin(row.origin),
                    created_at=row.created_at,
                    created_by=row.created_by,
                    trade_plan_id=row.trade_plan_id,
                    trade_plan_version_id=row.trade_plan_version_id,
                    product_selection_id=row.product_selection_id,
                    product_evaluation_id=row.product_evaluation_id,
                    cancelled_at=row.cancelled_at,
                    cancelled_by=row.cancelled_by,
                    cancellation_reason=row.cancellation_reason,
                    duplicate_of_trade_id=row.duplicate_of_trade_id,
                ),
                product_name=name,
                position_id=position_id,
            )
            for row, name, position_id in rows
        )

    async def _read_executions(
        self, session: AsyncSession, workspace_id: UUID
    ) -> tuple[ExecutionFact, ...]:
        rows = (
            await session.scalars(
                select(ExecutionRecordModel)
                .join(TradeModel, TradeModel.id == ExecutionRecordModel.trade_id)
                .where(TradeModel.workspace_id == workspace_id)
                .order_by(
                    ExecutionRecordModel.executed_at,
                    ExecutionRecordModel.recorded_at,
                    ExecutionRecordModel.id,
                )
                .limit(MAX_EXECUTIONS + 1)
            )
        ).all()
        if len(rows) > MAX_EXECUTIONS:
            raise ReportLimitExceeded("Report exceeds the complete execution limit")
        return tuple(
            ExecutionFact(
                id=row.id,
                trade_id=row.trade_id,
                product_id=row.product_id,
                side=row.side,
                quantity=row.quantity,
                price_per_unit=row.price_per_unit,
                executed_at=row.executed_at,
                recorded_at=row.recorded_at,
                recorded_by=row.recorded_by,
                supersedes_execution_id=row.supersedes_execution_id,
                executed_on=row.executed_on,
                execution_timezone=row.execution_timezone,
            )
            for row in rows
        )

    async def _read_confirmations(
        self, session: AsyncSession, workspace_id: UUID
    ) -> tuple[Confirmation, ...]:
        model = ExecutionCurrencyConfirmationModel
        rows = (
            await session.scalars(
                select(model)
                .where(model.workspace_id == workspace_id)
                .order_by(model.confirmed_at, model.id)
                .limit(MAX_CONFIRMATIONS + 1)
            )
        ).all()
        if len(rows) > MAX_CONFIRMATIONS:
            raise ReportLimitExceeded("Report exceeds the complete confirmation limit")
        return tuple(
            Confirmation(
                id=row.id,
                workspace_id=row.workspace_id,
                trade_id=row.trade_id,
                execution_id=row.execution_id,
                currency_code=row.currency_code,
                source=row.source,
                note=row.note,
                confirmed_at=row.confirmed_at,
                confirmed_by=row.confirmed_by,
                supersedes_confirmation_id=row.supersedes_confirmation_id,
                request_id=row.request_id,
            )
            for row in rows
        )
