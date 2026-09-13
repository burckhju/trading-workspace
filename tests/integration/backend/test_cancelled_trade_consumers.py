"""Cancellation excludes holdings and learning targets, not instrument master data."""

import asyncio
from uuid import UUID

import pytest
from tests.integration.backend.test_trade_capture_safety import BASE, WORKSPACE, product, purchase
from tests.integration.backend.test_usd_chf_currency_references import _client, _migrate
from tests.integration.backend.test_usd_chf_currency_references import (
    currency_database as base_database,
)

from app.core.config import Settings
from app.database import DatabaseManager
from app.features.learning.application.read_adapters import SqlAlchemyTradeReader
from app.features.market_data.service.refresh_catalog import read_catalog


@pytest.fixture
def database():
    yield from base_database.__wrapped__()


def test_cancelled_trade_loses_held_priority_and_learning_eligibility(database):
    _migrate(database, "head")

    async def exercise():
        db = DatabaseManager(Settings(_env_file=None, database_url=database))
        try:
            async with _client(database) as client:
                pid = await product(client)
                created = await client.post(BASE + "/purchases/external", json=purchase(pid))
                assert created.status_code == 201, created.text
                tid = created.json()["trade"]["id"]
                url = BASE + f"/trades/{tid}"
                warrants, stocks = await read_catalog(db, UUID(WORKSPACE))
                assert next(w for w in warrants if w.id == UUID(pid)).held
                assert any(s.held for s in stocks)
                async with db.session_context() as session:
                    assert (
                        await SqlAlchemyTradeReader(session).get(
                            workspace_id=UUID(WORKSPACE), trade_id=UUID(tid)
                        )
                        is not None
                    )
                preview = (await client.get(url + "/cancellation")).json()
                response = await client.post(
                    url + "/cancel",
                    json={
                        "expected_product_id": pid,
                        "expected_state_token": preview["state_token"],
                        "reason": "Accidental duplicate capture",
                        "confirmed": True,
                    },
                )
                assert response.status_code == 200, response.text
                warrants, stocks = await read_catalog(db, UUID(WORKSPACE))
                # Master data still participates in ordinary catalog refresh, but
                # cancelled executions no longer confer held-product priority.
                assert next(w for w in warrants if w.id == UUID(pid)).held is False
                assert stocks and not any(s.held for s in stocks)
                async with db.session_context() as session:
                    assert (
                        await SqlAlchemyTradeReader(session).get(
                            workspace_id=UUID(WORKSPACE), trade_id=UUID(tid)
                        )
                        is None
                    )
                history = (await client.get(url)).json()
                position = (await client.get(url + "/position")).json()
                assert history["cancelled_at"] is not None
                assert position["open_quantity"] == 10 and position["is_cancelled"]
        finally:
            await db.dispose()

    asyncio.run(exercise())
