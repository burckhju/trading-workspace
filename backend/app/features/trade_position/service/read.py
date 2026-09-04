"""Read service for persisted trade provenance."""

from uuid import UUID

from app.features.trade_position.domain.models import Trade
from app.features.trade_position.persistence.repositories import TradeRepository


class TradeReadService:
    def __init__(self, trades: TradeRepository) -> None:
        self._trades = trades

    async def get_trade(self, *, workspace_id: UUID, trade_id: UUID) -> Trade:
        trade = await self._trades.get(workspace_id, trade_id)
        if trade is None:
            raise ValueError("trade not found")
        return trade
