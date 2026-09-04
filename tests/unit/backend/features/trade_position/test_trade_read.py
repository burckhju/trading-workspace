from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.features.trade_position.domain.enums import TradeOrigin
from app.features.trade_position.domain.models import Trade
from app.features.trade_position.service.read import TradeReadService

WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")
TRADE_ID = UUID("10000000-0000-4000-8000-000000000001")
PRODUCT_ID = UUID("20000000-0000-4000-8000-000000000001")
ACTOR_ID = UUID("00000000-0000-4000-8000-000000000002")


class FakeTradeRepository:
    def __init__(self, trade: Trade | None) -> None:
        self.trade = trade
        self.requested: tuple[UUID, UUID] | None = None

    async def add(self, trade: Trade) -> None:
        self.trade = trade

    async def get(self, workspace_id: UUID, trade_id: UUID) -> Trade | None:
        self.requested = (workspace_id, trade_id)
        return self.trade


def external_trade() -> Trade:
    return Trade(
        id=TRADE_ID,
        workspace_id=WORKSPACE_ID,
        product_id=PRODUCT_ID,
        origin=TradeOrigin.EXTERNAL,
        created_at=datetime(2026, 9, 4, 20, 0, tzinfo=UTC),
        created_by=ACTOR_ID,
    )


@pytest.mark.asyncio
async def test_get_trade_returns_persisted_provenance() -> None:
    repository = FakeTradeRepository(external_trade())
    service = TradeReadService(repository)

    result = await service.get_trade(workspace_id=WORKSPACE_ID, trade_id=TRADE_ID)

    assert result == repository.trade
    assert repository.requested == (WORKSPACE_ID, TRADE_ID)


@pytest.mark.asyncio
async def test_get_trade_rejects_unknown_trade() -> None:
    service = TradeReadService(FakeTradeRepository(None))

    with pytest.raises(ValueError, match="trade not found"):
        await service.get_trade(workspace_id=WORKSPACE_ID, trade_id=TRADE_ID)
