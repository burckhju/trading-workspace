"""Catalog -> verified mappings -> quote reads with actual PostgreSQL constraints."""

import asyncio
import os
from contextlib import asynccontextmanager
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import insert, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from tests.integration.backend.database.conftest import _run_alembic
from tests.unit.backend.providers.frankfurt_quotes.test_public import public_settings, wire
from tests.unit.backend.providers.frankfurt_quotes.test_schema import NOW
from tests.unit.backend.providers.vontobel_markets.test_adapter import _html

from app.core.config import Settings
from app.core.di import ApplicationContainer
from app.features.market_data.service.refresh import MarketDataRefreshRuntime
from app.features.market_data.service.refresh_catalog import read_catalog
from app.features.market_data.service.types import WarrantQuoteRequest
from app.features.trade_position.persistence.models import PositionModel, TradeModel
from app.providers.frankfurt_quotes.adapter import FrankfurtWarrantQuoteAdapter
from app.providers.frankfurt_quotes.client import FrankfurtSnapshotClient
from app.providers.vontobel_markets.adapter import VontobelMarketsWarrantQuoteAdapter


@pytest.fixture
def current_database_url():
    base = os.environ.get("TRADING_WORKSPACE_TEST_DATABASE_URL", "")
    if not base:
        pytest.skip("TRADING_WORKSPACE_TEST_DATABASE_URL is not configured")
    parsed = make_url(base)
    assert parsed.database == "trading_workspace_test"
    database_name = "trading_workspace_refresh_test_" + uuid4().hex
    isolated_url = parsed.set(database=database_name).render_as_string(hide_password=False)

    async def manage(action):
        engine = create_async_engine(base, isolation_level="AUTOCOMMIT", poolclass=NullPool)
        try:
            async with engine.connect() as connection:
                if action == "create":
                    await connection.execute(text(f'CREATE DATABASE "{database_name}"'))
                else:
                    await connection.execute(text(f'DROP DATABASE "{database_name}" WITH (FORCE)'))
        finally:
            await engine.dispose()

    asyncio.run(manage("create"))
    try:
        _run_alembic("upgrade", "20260912_0035", isolated_url)
        yield isolated_url
    finally:
        asyncio.run(manage("drop"))


@pytest.mark.asyncio
async def test_catalog_automatically_maps_bnp_and_vontobel_without_position_or_instrument_overrides(
    current_database_url,
):
    engine = create_async_engine(current_database_url)
    workspace, underlying, issuer_v, issuer_b, warrant_v, warrant_b = (uuid4() for _ in range(6))
    settings = Settings(
        environment="test",
        market_data={
            "refresh": {"enabled": True, "workspace_id": workspace},
            "vontobel_markets": {"enabled": True},
            "frankfurt": public_settings().model_dump(),
        },
    )
    calls = []

    def respond(request):
        isin = request.url.path.rsplit("/", 1)[-1]
        calls.append(str(request.url))
        return httpx.Response(200, text=_html(isin=isin))

    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            try:
                await connection.execute(
                    text(
                        "INSERT INTO workspaces (id,name,created_at) VALUES (:id,'Refresh "
                        "test',:now)"
                    ),
                    {"id": workspace, "now": NOW},
                )
                for issuer, name in [(issuer_v, "Vontobel Test"), (issuer_b, "BNP Test")]:
                    await connection.execute(
                        text(
                            "INSERT INTO issuers "
                            "(id,legal_name,display_name,is_active,version,created_at,updated_at) "
                            "VALUES (:id,:name,:name,true,1,:now,:now)"
                        ),
                        {"id": issuer, "name": f"{name} {issuer}", "now": NOW},
                    )
                await connection.execute(
                    text(
                        "INSERT INTO underlyings "
                        "(id,workspace_id,type,name,lifecycle_status,quality_status,version,"
                        "created_at,updated_at,data_origin) "
                        "VALUES (:id,:workspace,'STOCK','Refresh "
                        "stock','ACTIVE','VERIFIED',1,:now,:now,'MANUAL')"
                    ),
                    {"id": underlying, "workspace": workspace, "now": NOW},
                )
                for warrant, issuer, isin in [
                    (warrant_v, issuer_v, "DE000VV00123"),
                    (warrant_b, issuer_b, "DE000BN00012"),
                ]:
                    await connection.execute(
                        text(
                            "INSERT INTO warrants "
                            "(id,workspace_id,issuer_id,underlying_id,product_family,display_name,"
                            "isin,lifecycle_status,version,created_at,updated_at) "
                            "VALUES "
                            "(:id,:workspace,:issuer,:underlying,'WARRANT',:isin,:isin,'ACTIVE',1,:now,:now)"
                        ),
                        {
                            "id": warrant,
                            "workspace": workspace,
                            "issuer": issuer,
                            "underlying": underlying,
                            "isin": isin,
                            "now": NOW,
                        },
                    )

                # Held products outrank UUID order; closed and foreign-workspace
                # positions do not confer priority, and duplicate trades add no jobs.
                held, unheld = sorted([warrant_v, warrant_b], reverse=True)
                foreign_workspace = uuid4()
                await connection.execute(
                    text("INSERT INTO workspaces (id,name,created_at) VALUES (:id,'Other',:now)"),
                    {"id": foreign_workspace, "now": NOW},
                )
                for product, trade_workspace, quantity in [
                    (held, workspace, 10),
                    (held, workspace, 20),
                    (unheld, workspace, 0),
                    (unheld, foreign_workspace, 10),
                ]:
                    trade_id = uuid4()
                    await connection.execute(
                        insert(TradeModel).values(
                            id=trade_id,
                            workspace_id=trade_workspace,
                            product_id=product,
                            origin="EXTERNAL",
                            created_at=NOW,
                            created_by=uuid4(),
                        )
                    )
                    await connection.execute(
                        insert(PositionModel).values(
                            id=uuid4(),
                            trade_id=trade_id,
                            product_id=product,
                            open_quantity=quantity,
                            cost_basis=quantity,
                            average_entry_price=1,
                            opened_at=NOW,
                            last_execution_at=NOW,
                            realized_gross_pnl=0,
                            closed_at=NOW if quantity == 0 else None,
                        )
                    )

                # These deliberate legacy anomalies were possible before 0036. Commit
                # them in this disposable database, then run the real upgrade. Never
                # disable the runtime guard to manufacture new invalid trades.
                await transaction.commit()
                await asyncio.to_thread(_run_alembic, "upgrade", "head", current_database_url)
                transaction = await connection.begin()

                @asynccontextmanager
                async def session_context():
                    async with AsyncSession(
                        bind=connection,
                        expire_on_commit=False,
                        join_transaction_mode="create_savepoint",
                    ) as session:
                        yield session

                database = SimpleNamespace(session_context=session_context)
                snapshots = FrankfurtSnapshotClient(
                    settings.market_data.frankfurt, cache_seconds=300
                )

                async def read(isin):
                    import json

                    return json.dumps(wire(isin=isin)).encode()

                snapshots._read = AsyncMock(side_effect=read)
                async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
                    container = replace(
                        ApplicationContainer.build(settings),
                        database=database,
                        frankfurt=FrankfurtWarrantQuoteAdapter(
                            database=database,
                            settings=settings.market_data.frankfurt,
                            snapshots=snapshots,
                        ),
                        vontobel=VontobelMarketsWarrantQuoteAdapter(
                            database=database,
                            settings=settings.market_data.vontobel_markets,
                            client=http,
                            cache_seconds=300,
                        ),
                    )
                    runtime = MarketDataRefreshRuntime(container, timer=lambda: 1000)

                    # Transport pacing is covered with a controlled clock in the unit tests.
                    async def paced():
                        snapshots._next_fetch = 0

                    runtime._pace = paced
                    await runtime.run_once()
                    assert runtime.last_error is None
                    quote_jobs = [
                        j for j in runtime.jobs.values() if j["job"].startswith("WARRANT_QUOTES:")
                    ]
                    assert len(quote_jobs) == 2
                    assert {j["status"] for j in quote_jobs} == {"AVAILABLE"}
                    rows = (
                        await connection.execute(
                            text(
                                "SELECT "
                                "w.isin,m.provider,m.provider_symbol,"
                                "m.provider_exchange_code,m.warrant_listing_id "
                                "FROM warrant_provider_mappings m JOIN warrant_listings l ON "
                                "l.id=m.warrant_listing_id JOIN warrants w ON w.id=l.warrant_id "
                                "WHERE w.workspace_id=:workspace"
                            ),
                            {"workspace": workspace},
                        )
                    ).all()
                    assert len(rows) == 3
                    assert {(row[0], row[1]) for row in rows} == {
                        ("DE000VV00123", "FRANKFURT_QUOTES"),
                        ("DE000BN00012", "FRANKFURT_QUOTES"),
                        ("DE000VV00123", "VONTOBEL_MARKETS"),
                    }
                    assert all(row[0] == row[2] for row in rows)
                    before = snapshots._read.await_count, len(calls)
                    await runtime.run_once()
                    assert (snapshots._read.await_count, len(calls)) == before
                    assert len(calls) == 1 and calls[0].endswith("DE000VV00123")
                    # Legacy duplicates add no jobs, and foreign-workspace positions
                    # do not confer priority after the current migration is applied.
                    warrants, stocks = await read_catalog(database, workspace)
                    assert [(w.id, w.held) for w in warrants] == [(held, True), (unheld, False)]
                    assert len(stocks) == 1 and stocks[0].held is True
                    await runtime.run_once()
                    assert [
                        j["instrument_id"]
                        for j in runtime.jobs.values()
                        if j["job"].startswith("WARRANT_QUOTES:")
                    ] == [held, unheld]
                    assert (snapshots._read.await_count, len(calls)) == before
                    # Disabling the mapping immediately prevents a cached issuer quote being served.
                    issuer_listing = next(row[4] for row in rows if row[1] == "VONTOBEL_MARKETS")
                    await connection.execute(
                        text(
                            "UPDATE warrant_provider_mappings SET status='DISABLED' WHERE "
                            "warrant_listing_id=:listing AND provider='VONTOBEL_MARKETS'"
                        ),
                        {"listing": issuer_listing},
                    )
                    from app.features.market_data.service.errors import MarketDataNotFoundError

                    with pytest.raises(MarketDataNotFoundError):
                        await container.vontobel.get_warrant_listing_quote(
                            WarrantQuoteRequest(workspace, issuer_listing, uuid4(), NOW)
                        )
            finally:
                await transaction.rollback()
    finally:
        await engine.dispose()
