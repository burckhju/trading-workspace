"""Scheduled official discovery -> audited mapping -> persisted EOD with real DB guards."""

import asyncio
import json
from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from tests.integration.backend.database.test_market_data_instrument_workspace_postgres import (
    _test_database_url,
)
from tests.unit.backend.providers.eodhd.test_adapter import make_adapter
from tests.unit.backend.providers.eodhd.test_stock_catalog import EXCHANGES, stock

from app.core.config import Settings
from app.core.di import ApplicationContainer
from app.features.market_data.service.refresh import MarketDataRefreshRuntime
from app.providers.eodhd.persistence import SqlAlchemyListingCurrencyReader, SqlAlchemyMappingReader


@pytest.mark.asyncio
async def test_scheduler_bootstraps_several_venues_imports_eod_and_preserves_disabled_mapping(
    monkeypatch,
):
    engine = create_async_engine(_test_database_url())
    workspace = uuid4()
    now = datetime.now(UTC)
    day = now.date() - timedelta(days=1)
    while day.weekday() > 4:
        day -= timedelta(days=1)
    payloads = {"/exchanges-list/": EXCHANGES}
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            try:
                await connection.execute(
                    text(
                        "INSERT INTO workspaces (id,name,created_at) VALUES (:id,'Catalog "
                        "test',:now)"
                    ),
                    {"id": workspace, "now": now},
                )
                listing_ids = []
                for index, (mic, label, code, currency) in enumerate(
                    [
                        ("XNAS", "NASDAQ", "US", "USD"),
                        ("XNYS", "NYSE", "US", "USD"),
                        ("XPAR", "PA", "PA", "EUR"),
                        ("XSWX", "SW", "SW", "CHF"),
                    ]
                ):
                    venue_id, underlying_id, listing_id = uuid4(), uuid4(), uuid4()
                    isin, symbol = f"US000000000{index}", f"EXAMPLE{index}"
                    listing_ids.append(listing_id)
                    await connection.execute(
                        text(
                            "INSERT INTO currencies "
                            "(code,name,minor_unit,is_active,reference_version,created_at,updated_at)"
                            " VALUES (:code,:code,2,true,'test',:now,:now) ON CONFLICT (code) DO "
                            "NOTHING"
                        ),
                        {"code": currency, "now": now},
                    )
                    await connection.execute(
                        text(
                            "INSERT INTO trading_venues "
                            "(id,mic,name,country_code,timezone,is_active,reference_version,version,created_at,updated_at)"
                            " VALUES (:id,:mic,:mic,'US','UTC',true,'test',1,:now,:now) ON "
                            "CONFLICT (mic) DO NOTHING"
                        ),
                        {"id": venue_id, "mic": mic, "now": now},
                    )
                    venue_id = await connection.scalar(
                        text("SELECT id FROM trading_venues WHERE mic=:mic"), {"mic": mic}
                    )
                    await connection.execute(
                        text(
                            "INSERT INTO underlyings "
                            "(id,workspace_id,type,name,isin,lifecycle_status,quality_status,version,created_at,updated_at,data_origin)"
                            " VALUES "
                            "(:id,:ws,'STOCK',:symbol,:isin,'ACTIVE','VERIFIED',1,:now,:now,'MANUAL')"
                        ),
                        {
                            "id": underlying_id,
                            "ws": workspace,
                            "symbol": symbol,
                            "isin": isin,
                            "now": now,
                        },
                    )
                    await connection.execute(
                        text(
                            "INSERT INTO listings "
                            "(id,workspace_id,underlying_id,trading_venue_id,ticker,currency_code,lifecycle_status,is_primary,version,created_at,updated_at,data_origin)"
                            " VALUES "
                            "(:id,:ws,:underlying,:venue,:symbol,:currency,'ACTIVE',true,1,:now,:now,'MANUAL')"
                        ),
                        {
                            "id": listing_id,
                            "ws": workspace,
                            "underlying": underlying_id,
                            "venue": venue_id,
                            "symbol": symbol,
                            "currency": currency,
                            "now": now,
                        },
                    )
                    payloads[f"/exchange-symbol-list/{label}"] = [
                        stock(Code=symbol, Exchange=label, Currency=currency, Isin=isin)
                    ]
                    payloads[f"/eod/{symbol}.{code}"] = [
                        {
                            "date": day.isoformat(),
                            "open": "10",
                            "high": "12",
                            "low": "9",
                            "close": "11",
                        }
                    ]

                @asynccontextmanager
                async def session_context():
                    async with AsyncSession(
                        bind=connection,
                        expire_on_commit=False,
                        join_transaction_mode="create_savepoint",
                    ) as session:
                        yield session

                database = SimpleNamespace(session_context=session_context)
                adapter, client, _ = make_adapter()
                adapter._clock.now = now
                # This test qualifies DB orchestration. Limiter/quota behavior has
                # dedicated unit tests; the helper's zero-yield fake sleeper can
                # stall at sub-ULP refill delays after several transport calls.
                monkeypatch.setattr(type(adapter._rate_limiter), "acquire", AsyncMock())
                adapter._mappings = SqlAlchemyMappingReader(database)
                adapter._currencies = SqlAlchemyListingCurrencyReader(database)
                client.get_json = AsyncMock(side_effect=lambda path, **_: payloads[path])
                settings = Settings(
                    environment="test",
                    market_data={"refresh": {"enabled": True, "workspace_id": workspace}},
                )
                container = replace(
                    ApplicationContainer.build(settings),
                    database=database,
                    eodhd=SimpleNamespace(adapter=adapter),
                )
                runtime = MarketDataRefreshRuntime(container)
                runtime._pace = AsyncMock()
                await asyncio.wait_for(runtime.run_once(), timeout=30)
                assert runtime.last_error is None
                assert all(
                    job["status"] == "AVAILABLE" for job in runtime.jobs.values()
                ), runtime.jobs
                mappings = (
                    await connection.execute(
                        text(
                            "SELECT id,status,validation_message,market_data_instrument_id,"
                            "provider_symbol,provider_exchange_code FROM "
                            "provider_instrument_mappings WHERE workspace_id=:ws"
                        ),
                        {"ws": workspace},
                    )
                ).all()
                assert len(mappings) == 4 and all(row.status == "ACTIVE" for row in mappings)
                assert all(row.market_data_instrument_id for row in mappings)
                assert {json.loads(row.validation_message)["mic"] for row in mappings} == {
                    "XNAS",
                    "XNYS",
                    "XPAR",
                    "XSWX",
                }
                assert (
                    await connection.scalar(
                        text(
                            "SELECT count(*) FROM daily_prices WHERE workspace_id=:ws AND "
                            "market_data_instrument_id IS NOT NULL"
                        ),
                        {"ws": workspace},
                    )
                    == 4
                )
                assert (
                    await connection.scalar(
                        text(
                            "SELECT count(*) FROM audit_events WHERE workspace_id=:ws AND "
                            "aggregate_type='PROVIDER_MAPPING'"
                        ),
                        {"ws": workspace},
                    )
                    == 8
                )
                calls = client.get_json.await_count
                await connection.execute(
                    text("UPDATE provider_instrument_mappings SET status='DISABLED' WHERE id=:id"),
                    {"id": mappings[0].id},
                )
                runtime._due.clear()
                await asyncio.wait_for(runtime.run_once(), timeout=30)
                # The second import intentionally uses a shorter correction window,
                # so it has a new cache key. Catalogs stay cached; only the three
                # active mappings may request that EOD window.
                disabled = mappings[0]
                disabled_path = f"/eod/{disabled.provider_symbol}.{disabled.provider_exchange_code}"
                expected = {path for path in payloads if path.startswith("/eod/")} - {disabled_path}
                assert client.get_json.await_count == calls + len(expected)
                assert {
                    call.args[0] for call in client.get_json.await_args_list[calls:]
                } == expected
                assert (
                    await connection.scalar(
                        text("SELECT count(*) FROM daily_prices WHERE workspace_id=:ws"),
                        {"ws": workspace},
                    )
                    == 4
                )
                assert (
                    await connection.scalar(
                        text("SELECT status FROM provider_instrument_mappings WHERE id=:id"),
                        {"id": mappings[0].id},
                    )
                    == "DISABLED"
                )
                assert any(
                    j["reason"] == "VALIDATED_EODHD_MAPPING_REQUIRED" for j in runtime.jobs.values()
                )
            finally:
                await transaction.rollback()
    finally:
        await engine.dispose()
