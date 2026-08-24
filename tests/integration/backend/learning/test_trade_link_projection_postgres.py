from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from test_trade_link_application_postgres import (
    _seed_external_trade,
    _seed_observation,
    _seed_parents,
)
from test_trade_link_application_transitions_postgres import (
    _create_initial_link,
)

from app.features.learning.application.read_adapters import (
    SqlAlchemyProductReader,
    SqlAlchemyTradeReader,
)
from app.features.learning.application.trade_link_projection_service import (
    TradeLinkCurrentSourceCompatibility,
    TradeLinkProjectionService,
    TradeLinkSourceState,
)
from app.features.learning.persistence.unit_of_work import (
    SqlAlchemyLearningTradeLinkUnitOfWork,
)


@pytest.mark.asyncio
async def test_projection_reads_current_source_and_compatibility_from_postgres(
    learning_session: AsyncSession,
) -> None:
    workspace_id, _, underlying_id, product_id = await _seed_parents(learning_session)
    trade_id = await _seed_external_trade(
        learning_session,
        workspace_id=workspace_id,
        product_id=product_id,
    )
    observation_id, _ = await _seed_observation(
        learning_session,
        workspace_id=workspace_id,
        underlying_id=underlying_id,
        product_id=product_id,
    )
    link_id, _ = await _create_initial_link(
        learning_session,
        workspace_id=workspace_id,
        observation_id=observation_id,
        trade_id=trade_id,
    )

    projection = await TradeLinkProjectionService(
        uow=SqlAlchemyLearningTradeLinkUnitOfWork(learning_session),
        trade_reader=SqlAlchemyTradeReader(learning_session),
        product_reader=SqlAlchemyProductReader(learning_session),
    ).get(
        workspace_id=workspace_id,
        trade_link_id=link_id,
    )

    assert projection is not None
    assert projection.link.id == link_id
    assert projection.version.trade_id == trade_id
    assert projection.source_state is TradeLinkSourceState.CURRENT_SOURCE
    assert projection.current_source_compatibility is TradeLinkCurrentSourceCompatibility.COMPATIBLE


@pytest.mark.asyncio
async def test_projection_returns_none_for_unknown_link(
    learning_session: AsyncSession,
) -> None:
    projection = await TradeLinkProjectionService(
        uow=SqlAlchemyLearningTradeLinkUnitOfWork(learning_session),
        trade_reader=SqlAlchemyTradeReader(learning_session),
        product_reader=SqlAlchemyProductReader(learning_session),
    ).get(
        workspace_id=uuid4(),
        trade_link_id=uuid4(),
    )

    assert projection is None
