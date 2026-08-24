from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from test_trade_link_application_postgres import _seed_parents

from app.features.learning.application.external_trade_creator import (
    SqlAlchemyExternalTradeCreator,
)
from app.features.trade_position.domain.enums import TradeOrigin


@pytest.mark.asyncio
async def test_creator_flushes_trade_execution_and_position_without_commit(
    learning_session: AsyncSession,
) -> None:
    workspace_id, _, _, product_id = await _seed_parents(learning_session)

    trade, execution, position = await SqlAlchemyExternalTradeCreator(learning_session).create(
        workspace_id=workspace_id,
        product_id=product_id,
        quantity=3,
        price_per_unit=Decimal("12.50"),
        executed_at=datetime(2026, 8, 23, tzinfo=UTC),
        actor_id=uuid4(),
    )

    assert trade.origin is TradeOrigin.EXTERNAL
    assert execution.trade_id == trade.id
    assert position.trade_id == trade.id
    assert position.open_quantity == 3

    trade_count = await learning_session.scalar(
        text("select count(*) from trades where id = :id"),
        {"id": trade.id},
    )
    execution_count = await learning_session.scalar(
        text("select count(*) from execution_records where id = :id"),
        {"id": execution.id},
    )
    position_count = await learning_session.scalar(
        text("select count(*) from positions where id = :id"),
        {"id": position.id},
    )

    assert trade_count == 1
    assert execution_count == 1
    assert position_count == 1


@pytest.mark.asyncio
async def test_creator_changes_are_rolled_back_with_caller_transaction(
    learning_test_engine: AsyncEngine,
) -> None:
    async with learning_test_engine.connect() as connection:
        outer = await connection.begin()
        session = AsyncSession(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            workspace_id, _, _, product_id = await _seed_parents(session)
            trade, _, _ = await SqlAlchemyExternalTradeCreator(session).create(
                workspace_id=workspace_id,
                product_id=product_id,
                quantity=1,
                price_per_unit=Decimal("10.00"),
                executed_at=datetime(2026, 8, 23, tzinfo=UTC),
                actor_id=uuid4(),
            )
            await session.close()
            await outer.rollback()
        finally:
            if outer.is_active:
                await outer.rollback()

    async with learning_test_engine.connect() as verification:
        count = await verification.scalar(
            text("select count(*) from trades where id = :id"),
            {"id": trade.id},
        )
    assert count == 0
