"""Real services/constraints: stage, import, validate, then audit a primary switch."""

from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from tests.integration.backend.database.test_market_data_instrument_workspace_postgres import (
    _test_database_url,
)
from tests.unit.backend.providers.eodhd.test_adapter import make_adapter
from tests.unit.backend.providers.eodhd.test_stock_catalog import stock

from app.core.config import Settings
from app.core.di import ApplicationContainer
from app.features.market.persistence.models import (
    CurrencyModel,
    ListingModel,
    TradingVenueModel,
    UnderlyingModel,
    WorkspaceModel,
)
from app.features.market.service.listing_service import ListingService
from app.features.market_data.persistence.models import (
    DailyPriceModel,
    ProviderInstrumentMappingModel,
)
from app.features.market_data.service.errors import MarketDataMappingError
from app.providers.eodhd.persistence import (
    SqlAlchemyListingCurrencyReader,
    SqlAlchemyMappingReader,
)
from app.tools.switch_underlying_venue import VenueSwitchError, apply_plan, prepare

ISIN = "US0378331005"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "scenario",
    [
        "success",
        "target_before_source",
        "empty",
        "stale",
        "invalid",
        "source_changed",
        "promotion_failure",
    ],
)
async def test_verified_switch_preserves_history_and_fails_before_primary_change(
    monkeypatch, scenario
):
    engine = create_async_engine(_test_database_url())
    workspace, underlying_id, source_id = uuid4(), uuid4(), uuid4()
    seeded_target_id = UUID(int=1) if scenario == "target_before_source" else None
    if scenario == "promotion_failure":
        original_audit = ListingService._audit

        async def fail_promotion(self, after, actor_id, actor_name, change_type, before):
            if change_type.value == "PRIMARY_CHANGED":
                raise VenueSwitchError("TEST_PROMOTION_FAILURE")
            await original_audit(self, after, actor_id, actor_name, change_type, before)

        monkeypatch.setattr(ListingService, "_audit", fail_promotion)
    now = datetime.now(UTC)
    day = now.date() - timedelta(days=1)
    while day.weekday() > 4:
        day -= timedelta(days=1)
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            try:

                @asynccontextmanager
                async def session_context():
                    async with AsyncSession(
                        bind=connection,
                        expire_on_commit=False,
                        join_transaction_mode="create_savepoint",
                    ) as session:
                        yield session

                async with session_context() as session:
                    session.add(
                        WorkspaceModel(id=workspace, name="Venue switch test", created_at=now)
                    )
                    if await session.get(CurrencyModel, "EUR") is None:
                        session.add(
                            CurrencyModel(
                                code="EUR",
                                name="Euro",
                                minor_unit=2,
                                is_active=True,
                                reference_version="test",
                                created_at=now,
                                updated_at=now,
                            )
                        )
                    venues = {}
                    for mic in ("XETR", "XFRA"):
                        venue = await session.scalar(
                            select(TradingVenueModel).where(TradingVenueModel.mic == mic)
                        )
                        if venue is None:
                            venue = TradingVenueModel(
                                id=uuid4(),
                                mic=mic,
                                name=mic,
                                country_code="DE",
                                timezone="Europe/Berlin",
                                is_active=True,
                                reference_version="test",
                                version=1,
                                created_at=now,
                                updated_at=now,
                            )
                            session.add(venue)
                        venues[mic] = venue.id
                    await session.flush()
                    session.add(
                        UnderlyingModel(
                            id=underlying_id,
                            workspace_id=workspace,
                            type="STOCK",
                            name="Example stock",
                            isin=ISIN,
                            lifecycle_status="ACTIVE",
                            quality_status="VERIFIED",
                            version=1,
                            created_at=now,
                            updated_at=now,
                            data_origin="MANUAL",
                        )
                    )
                    await session.flush()
                    session.add(
                        ListingModel(
                            id=source_id,
                            workspace_id=workspace,
                            underlying_id=underlying_id,
                            trading_venue_id=venues["XETR"],
                            ticker="OLD",
                            currency_code="EUR",
                            is_primary=True,
                            lifecycle_status="ACTIVE",
                            version=1,
                            created_at=now,
                            updated_at=now,
                            data_origin="MANUAL",
                        )
                    )
                    await session.flush()
                    if seeded_target_id is not None:
                        session.add(
                            ListingModel(
                                id=seeded_target_id,
                                workspace_id=workspace,
                                underlying_id=underlying_id,
                                trading_venue_id=venues["XFRA"],
                                ticker="APC",
                                currency_code="EUR",
                                is_primary=False,
                                lifecycle_status="ACTIVE",
                                version=1,
                                created_at=now,
                                updated_at=now,
                                data_origin="MANUAL",
                            )
                        )
                    session.add(
                        DailyPriceModel(
                            id=uuid4(),
                            workspace_id=workspace,
                            listing_id=source_id,
                            trading_date=day,
                            open=10,
                            high=12,
                            low=9,
                            close=11,
                            currency="EUR",
                            provider="EODHD",
                            provider_symbol="OLD",
                            retrieved_at=now,
                            quality_status="VALID",
                            price_type="EOD",
                            created_at=now,
                            updated_at=now,
                        )
                    )
                    await session.commit()

                database = SimpleNamespace(session_context=session_context)
                adapter, client, _ = make_adapter()
                adapter._clock.now = now
                monkeypatch.setattr(type(adapter._rate_limiter), "acquire", AsyncMock())
                adapter._mappings = SqlAlchemyMappingReader(database)
                adapter._currencies = SqlAlchemyListingCurrencyReader(database)
                payloads = {
                    "/exchanges-list/": [{"Code": "F", "OperatingMIC": "XFRA"}],
                    "/exchange-symbol-list/F": [
                        stock(Code="APC", Exchange="F", Currency="EUR", Isin=ISIN)
                    ],
                    "/eod/APC.F": [
                        {
                            "date": day.isoformat(),
                            "open": "10",
                            "high": "12",
                            "low": "9",
                            "close": "11",
                        }
                    ],
                }
                if scenario == "empty":
                    payloads["/eod/APC.F"] = []
                if scenario == "stale":
                    payloads["/eod/APC.F"][0]["date"] = (day - timedelta(days=20)).isoformat()
                if scenario == "invalid":
                    payloads["/eod/APC.F"][0]["close"] = "1000"

                async def get_json(path, **_):
                    if path.startswith("/eod/") and scenario == "source_changed":
                        await connection.execute(
                            text("UPDATE listings SET version=version+1 WHERE id=:id"),
                            {"id": source_id},
                        )
                    return payloads[path]

                client.get_json = AsyncMock(side_effect=get_json)
                container = replace(
                    ApplicationContainer.build(Settings(environment="test")),
                    database=database,
                    eodhd=SimpleNamespace(adapter=adapter),
                )
                kwargs = dict(
                    workspace_id=workspace,
                    isin=ISIN,
                    from_mic="XETR",
                    to_mic="XFRA",
                    currency="EUR",
                )
                plan = await prepare(container, **kwargs)
                assert plan.target_id == seeded_target_id
                assert await connection.scalar(
                    text("SELECT count(*) FROM listings WHERE workspace_id=:ws"),
                    {"ws": workspace},
                ) == (2 if seeded_target_id else 1)
                assert (
                    await connection.scalar(
                        text(
                            "SELECT count(*) FROM provider_instrument_mappings "
                            "WHERE workspace_id=:ws"
                        ),
                        {"ws": workspace},
                    )
                    == 0
                )
                if scenario in {"success", "target_before_source"}:
                    result = await apply_plan(container, plan)
                    assert result["status"] == "APPLIED" and result["data_verified"]
                    assert result["close"] == 11 and result["trading_date"] == day
                    assert result["target_mic"] == "XFRA" and result["currency"] == "EUR"
                    target_id = result["target_listing_id"]
                    before_audit = await connection.scalar(
                        text("SELECT count(*) FROM audit_events WHERE workspace_id=:ws"),
                        {"ws": workspace},
                    )
                    repeated = await apply_plan(container, await prepare(container, **kwargs))
                    assert (
                        repeated["status"] == "ALREADY_PRIMARY" and not repeated["primary_changed"]
                    )
                    assert repeated["target_listing_id"] == target_id
                    assert (
                        await connection.scalar(
                            text("SELECT count(*) FROM audit_events WHERE workspace_id=:ws"),
                            {"ws": workspace},
                        )
                        == before_audit
                    )
                    assert before_audit == (
                        4 if seeded_target_id else 5
                    )  # listing creation, mapping creation/validation, two primary flags
                    async with session_context() as session:
                        mapping = await session.get(
                            ProviderInstrumentMappingModel, result["mapping_id"]
                        )
                        assert mapping.market_data_instrument_id is not None
                        price = await session.scalar(
                            select(DailyPriceModel).where(DailyPriceModel.listing_id == target_id)
                        )
                        assert price.market_data_instrument_id == mapping.market_data_instrument_id
                    # Explicitly disabled mappings are preserved, including on reruns.
                    await connection.execute(
                        text(
                            "UPDATE provider_instrument_mappings SET status='DISABLED' WHERE id=:id"
                        ),
                        {"id": result["mapping_id"]},
                    )
                    with pytest.raises(VenueSwitchError, match="VALIDATED_TARGET_MAPPING_REQUIRED"):
                        await prepare(container, **kwargs)
                else:
                    with pytest.raises((VenueSwitchError, MarketDataMappingError)):
                        await apply_plan(container, plan)
                    target_id = source_id
                async with session_context() as session:
                    listings = list(
                        await session.scalars(
                            select(ListingModel).where(ListingModel.workspace_id == workspace)
                        )
                    )
                    assert len(listings) == 2
                    assert [row.id for row in listings if row.is_primary] == [target_id]
                    old = next(row for row in listings if row.id == source_id)
                    assert old.ticker == "OLD" and old.currency_code == "EUR"
                    assert (
                        old.trading_venue_id == venues["XETR"] and old.lifecycle_status == "ACTIVE"
                    )
                    old_price = await session.scalar(
                        select(DailyPriceModel).where(DailyPriceModel.listing_id == source_id)
                    )
                    assert old_price.close == 11 and old_price.retrieved_at == now
                    assert old_price.provider_symbol == "OLD"
            finally:
                await transaction.rollback()
    finally:
        await engine.dispose()
