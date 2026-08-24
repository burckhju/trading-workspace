from __future__ import annotations

import asyncio
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from test_trade_link_repositories_postgres import _seed_trade_link_graph

import app.features.learning.persistence.models
import app.features.market.persistence.models
import app.features.product.persistence.models
import app.features.product_selection.persistence.models
import app.features.trade_plan.persistence.models
import app.features.trade_position.persistence.models  # noqa: F401
from app.features.learning.persistence.repositories import (
    SqlAlchemyExternalObservationTradeLinkRepository,
)


async def _session_for_engine(engine: AsyncEngine) -> AsyncSession:
    return AsyncSession(
        bind=engine,
        expire_on_commit=False,
    )


@pytest.mark.asyncio
async def test_trade_link_lock_blocks_second_session_until_release(
    learning_test_engine: AsyncEngine,
) -> None:
    seed_session = await _session_for_engine(learning_test_engine)
    try:
        workspace_id, _, _, link_id = await _seed_trade_link_graph(seed_session)
        await seed_session.commit()
    finally:
        await seed_session.close()

    first = await _session_for_engine(learning_test_engine)
    second = await _session_for_engine(learning_test_engine)

    first_repo = SqlAlchemyExternalObservationTradeLinkRepository(first)
    second_repo = SqlAlchemyExternalObservationTradeLinkRepository(second)

    second_started = asyncio.Event()
    second_acquired = asyncio.Event()

    async def acquire_in_second_session(
        workspace_id: UUID,
        link_id: UUID,
    ) -> None:
        second_started.set()
        acquired = await second_repo.lock(workspace_id, link_id)
        assert acquired is True
        second_acquired.set()

    try:
        assert await first_repo.lock(workspace_id, link_id) is True

        task = asyncio.create_task(acquire_in_second_session(workspace_id, link_id))

        await asyncio.wait_for(second_started.wait(), timeout=1.0)
        await asyncio.sleep(0.1)
        assert not second_acquired.is_set()

        await first.commit()

        await asyncio.wait_for(second_acquired.wait(), timeout=2.0)
        await task
    finally:
        await first.rollback()
        await second.rollback()
        await first.close()
        await second.close()


@pytest.mark.asyncio
async def test_next_version_number_holds_stable_root_lock(
    learning_test_engine: AsyncEngine,
) -> None:
    seed_session = await _session_for_engine(learning_test_engine)
    try:
        workspace_id, _, _, link_id = await _seed_trade_link_graph(seed_session)
        await seed_session.commit()
    finally:
        await seed_session.close()

    first = await _session_for_engine(learning_test_engine)
    second = await _session_for_engine(learning_test_engine)

    first_links = SqlAlchemyExternalObservationTradeLinkRepository(first)
    second_links = SqlAlchemyExternalObservationTradeLinkRepository(second)

    from app.features.learning.persistence.repositories import (
        SqlAlchemyExternalObservationTradeLinkVersionRepository,
    )

    first_versions = SqlAlchemyExternalObservationTradeLinkVersionRepository(
        first,
        first_links,
    )
    second_started = asyncio.Event()
    second_acquired = asyncio.Event()

    async def second_lock() -> None:
        second_started.set()
        acquired = await second_links.lock(workspace_id, link_id)
        assert acquired is True
        second_acquired.set()

    try:
        assert (
            await first_versions.next_version_number(
                workspace_id,
                link_id,
            )
            == 2
        )

        task = asyncio.create_task(second_lock())

        await asyncio.wait_for(second_started.wait(), timeout=1.0)
        await asyncio.sleep(0.1)
        assert not second_acquired.is_set()

        await first.commit()

        await asyncio.wait_for(second_acquired.wait(), timeout=2.0)
        await task
    finally:
        await first.rollback()
        await second.rollback()
        await first.close()
        await second.close()
