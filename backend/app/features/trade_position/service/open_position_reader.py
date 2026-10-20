"""Public read/serialization boundary for monitoring consumers of open positions."""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.trade_position.persistence.models import PositionModel, TradeModel


@dataclass(frozen=True, slots=True)
class OpenPositionReference:
    workspace_id: UUID
    trade_id: UUID
    position_id: UUID
    warrant_id: UUID


class OpenPositionReader:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def read(
        self, *, workspace_id: UUID, trade_id: UUID, lock: bool = False
    ) -> OpenPositionReference | None:
        statement = (
            select(TradeModel, PositionModel)
            .join(PositionModel, PositionModel.trade_id == TradeModel.id)
            .where(
                TradeModel.workspace_id == workspace_id,
                TradeModel.id == trade_id,
                TradeModel.cancelled_at.is_(None),
                PositionModel.closed_at.is_(None),
                PositionModel.open_quantity > 0,
            )
        )
        if lock:
            statement = statement.with_for_update(of=PositionModel)
        row = (await self._session.execute(statement)).one_or_none()
        if row is None:
            return None
        trade, position = row
        return OpenPositionReference(workspace_id, trade.id, position.id, trade.product_id)

    async def list_open(self) -> tuple[OpenPositionReference, ...]:
        rows = (
            await self._session.execute(
                select(TradeModel, PositionModel)
                .join(PositionModel, PositionModel.trade_id == TradeModel.id)
                .where(
                    TradeModel.cancelled_at.is_(None),
                    PositionModel.closed_at.is_(None),
                    PositionModel.open_quantity > 0,
                )
                .order_by(PositionModel.id)
            )
        ).all()
        return tuple(
            OpenPositionReference(t.workspace_id, t.id, p.id, t.product_id) for t, p in rows
        )
