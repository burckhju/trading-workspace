from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config.settings import Settings
from app.core.di import ApplicationContainer, get_container
from app.features.market_data.domain.enums import QualityStatus
from app.features.market_data.service.errors import (
    MarketDataMappingError,
    MarketDataNotFoundError,
)
from app.features.market_data.service.types import WarrantQuoteRequest
from app.features.position_monitoring.api import router
from app.features.position_monitoring.service.quote_runtime import (
    build_warrant_quote_resolver,
)
from app.features.position_monitoring.service.quote_sources import (
    MultiSourceWarrantQuoteResolver,
    NamedWarrantQuoteSource,
)
from app.providers.frankfurt_quotes.adapter import FrankfurtWarrantQuoteAdapter
from app.providers.frankfurt_quotes.schema import FrankfurtSnapshot
from tests.unit.backend.providers.frankfurt_quotes.test_client import settings
from tests.unit.backend.providers.frankfurt_quotes.test_schema import NOW, payload


class Database:
    def __init__(self, row):
        self.execute = AsyncMock(return_value=SimpleNamespace(one_or_none=lambda: row))

    @asynccontextmanager
    async def session_context(self):
        yield SimpleNamespace(execute=self.execute)


def context(data=None):
    listing_id = uuid4()
    row = (
        SimpleNamespace(id=listing_id, quotation_currency_code="EUR"),
        SimpleNamespace(isin="DE000VH2LU21", wkn="VH2LU2"),
        SimpleNamespace(
            provider_symbol="DE000VH2LU21",
            provider_exchange_code="XFRA",
            validated_at=NOW,
        ),
        SimpleNamespace(mic="XFRA"),
    )
    snapshots = SimpleNamespace(
        load=AsyncMock(
            return_value=(
                FrankfurtSnapshot.model_validate(data or payload()),
                NOW,
                False,
            )
        ),
        last_success_at=None,
        last_error=None,
    )
    database = Database(row)
    adapter = FrankfurtWarrantQuoteAdapter(
        database=database, settings=settings(), snapshots=snapshots, clock=lambda: NOW
    )
    request = WarrantQuoteRequest(uuid4(), listing_id, uuid4(), NOW)
    return adapter, database, snapshots, request, row


@pytest.mark.asyncio
async def test_existing_provider_port_and_scoped_identity_query():
    adapter, database, snapshots, request, _row = context()
    value = await adapter.get_warrant_listing_quote(request)
    assert value.data.warrant_listing_id == request.warrant_listing_id
    assert value.data.isin == "DE000VH2LU21"
    assert value.data.provider_exchange_code == "XFRA"
    assert value.correlation_id == request.correlation_id
    assert value.quality_status is QualityStatus.VALID
    assert "NOT_EXECUTABLE" in value.warnings
    assert value.provider_call_cost is None
    sql = str(database.execute.call_args.args[0])
    assert "warrant_listings.workspace_id" in sql
    assert "warrants.workspace_id" in sql
    assert "warrant_provider_mappings.workspace_id" in sql
    assert "warrant_listings.lifecycle_status =" in sql
    snapshots.load.assert_awaited_once()


@pytest.mark.asyncio
async def test_unmapped_listing_never_downloads():
    adapter, _database, snapshots, request, _row = context()
    adapter._database = Database(None)
    with pytest.raises(MarketDataNotFoundError):
        await adapter.inspect(request)
    snapshots.load.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "field,value",
    [
        ("provider_symbol", "DE000VH7S657"),
        ("provider_exchange_code", "XSTU"),
        ("validated_at", None),
    ],
)
async def test_inconsistent_existing_mapping_is_error(field, value):
    adapter, _database, snapshots, request, row = context()
    setattr(row[2], field, value)
    with pytest.raises(MarketDataMappingError):
        await adapter.inspect(request)
    snapshots.load.assert_not_awaited()


@pytest.mark.asyncio
async def test_wrong_actual_venue_is_error_even_with_xfra_mapping():
    adapter, _database, snapshots, request, row = context()
    row[3].mic = "XETR"
    with pytest.raises(MarketDataMappingError):
        await adapter.inspect(request)
    snapshots.load.assert_not_awaited()


@pytest.mark.asyncio
async def test_stale_primary_falls_back_and_retains_reason():
    data = payload()
    data["records"][0]["bid_at"] = (NOW - timedelta(seconds=901)).isoformat()
    primary, _db, _snapshots, request, _row = context(data)
    secondary, *_unused = context()
    good = await secondary.get_warrant_listing_quote(request)
    secondary_provider = SimpleNamespace(get_warrant_listing_quote=AsyncMock(return_value=good))
    resolver = MultiSourceWarrantQuoteResolver(
        (
            NamedWarrantQuoteSource("FRANKFURT_QUOTES", primary),
            NamedWarrantQuoteSource("FALLBACK", secondary_provider),
        )
    )
    result = await resolver.resolve(request)
    assert result.selected_source == "FALLBACK"
    assert result.attempts[0].reason == "FRANKFURT_QUOTE_STALE"
    assert result.attempts[0].status == "AVAILABLE"  # retained for indicative analysis


@pytest.mark.asyncio
async def test_post_trade_never_becomes_bid():
    data = payload()
    data["records"][0]["kind"] = "LAST_TRADE"
    adapter, _db, _snapshots, request, _row = context(data)
    result = await adapter.get_warrant_listing_quote(request)
    assert result.data is None
    assert result.reason_code == "FRANKFURT_REFERENCE_PRICE_MISSING"


def test_api_diagnostics_and_disabled_default():
    adapter, database, _snapshots, request, _row = context()
    container = ApplicationContainer(settings=Settings(_env_file=None), database=database)
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_container] = lambda: container
    prefix = "/api/v1/position-monitoring/quote-sources/frankfurt"
    with TestClient(app) as client:
        response = client.get(f"{prefix}/health")
        assert response.status_code == 200
        assert response.json()["reason"] == "FRANKFURT_DISABLED"
        assert response.json()["coverage_verified"] is False
        url = f"{prefix}/listings/{request.warrant_listing_id}?workspace_id={request.workspace_id}"
        assert client.get(url).json()["status"] == "UNAVAILABLE"
        configured = Settings(_env_file=None, market_data={"frankfurt": settings()})
        container = replace(container, settings=configured, frankfurt=adapter)
        body = client.get(url).json()
        assert body["status"] == "AVAILABLE"
        assert body["observation"]["execution_usable"] is False
        assert body["observation"]["record"]["bid_size"] == 1000
        assert "snapshot_url" not in client.get(f"{prefix}/health").text


def test_public_health_and_listing_diagnostic_do_not_claim_bid_ask_capability():
    from app.providers.frankfurt_quotes.public import FrankfurtPublicPrice
    from tests.unit.backend.providers.frankfurt_quotes.test_public import (
        public_settings,
        wire,
    )

    adapter, database, snapshots, request, row = context()
    adapter.settings = public_settings()
    row[2].provider_exchange_code = "XSC"
    snapshots.load_public = AsyncMock(
        return_value=(FrankfurtPublicPrice.model_validate(wire()), NOW, False)
    )
    container = ApplicationContainer(
        settings=Settings(_env_file=None, market_data={"frankfurt": public_settings()}),
        database=database,
        frankfurt=adapter,
    )
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_container] = lambda: container
    prefix = "/api/v1/position-monitoring/quote-sources/frankfurt"
    with TestClient(app) as client:
        health = client.get(f"{prefix}/health").json()
        assert health["source_mode"] == "public_website"
        assert health["schema_version"] == "deutsche-boerse-public-last-trade-v1"
        assert health["bid_ask_supported"] is health["execution_usable"] is False
        assert health["delay_seconds"] is None
        result = client.get(
            f"{prefix}/listings/{request.warrant_listing_id}?workspace_id={request.workspace_id}"
        ).json()
        assert result["reason"] == "FRANKFURT_POST_TRADE_ONLY"
        assert result["observation"]["record"]["last_price"] == "0.231"
        assert result["observation"]["record"]["bid"] is None
        assert result["observation"]["provider_exchange_code"] == "XSC"


@pytest.mark.asyncio
async def test_runtime_uses_public_last_only_source_for_analysis():
    from app.providers.frankfurt_quotes.public import FrankfurtPublicPrice
    from tests.unit.backend.providers.frankfurt_quotes.test_public import (
        public_settings,
        wire,
    )

    adapter, database, snapshots, request, row = context()
    adapter.settings = public_settings()
    row[2].provider_exchange_code = "XSC"
    snapshots.load_public = AsyncMock(
        return_value=(FrankfurtPublicPrice.model_validate(wire()), NOW, False)
    )
    configured = Settings(_env_file=None, market_data={"frankfurt": public_settings()})
    container = ApplicationContainer(settings=configured, database=database, frankfurt=adapter)
    result = await build_warrant_quote_resolver(container).resolve(request)
    assert result.selected_source == "FRANKFURT_QUOTES"
    assert result.result.data.reference_price_type == "LAST_TRADE"
    assert result.result.data.bid is None
    snapshots.load_public.assert_awaited_once_with("DE000VH2LU21")
    snapshots.load.assert_not_awaited()


@pytest.mark.asyncio
async def test_runtime_reuses_process_adapter_and_places_it_first():
    adapter, database, _snapshots, request, _row = context()
    configured = Settings(_env_file=None, market_data={"frankfurt": settings()})
    container = ApplicationContainer(settings=configured, database=database, frankfurt=adapter)
    result = await build_warrant_quote_resolver(container).resolve(request)
    assert result.selected_source == "FRANKFURT_QUOTES"
