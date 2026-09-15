"""Owner-API captures and durable source evidence on a disposable migrated database."""

import asyncio
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from tests.integration.backend.test_usd_chf_currency_references import _migrate, _product_payload
from tests.integration.backend.test_usd_chf_currency_references import (
    currency_database as base_database,
)

from app.core.config import Settings
from app.features.market_data.domain.enums import (
    CacheStatus,
    MarketDataCapability,
    MarketDataProvider,
    QualityStatus,
)
from app.features.market_data.domain.models import WarrantQuoteSnapshot
from app.features.market_data.service.retained_quotes import RetainedWarrantQuoteProvider
from app.features.market_data.service.types import MarketDataResult, WarrantQuoteRequest
from app.main import create_application
from app.providers.vontobel_markets.configure import configure_warrant


@pytest.fixture
def database():
    yield from base_database.__wrapped__()


def test_owner_flow_read_only_coverage_and_closed_position_exclusion(database):
    _migrate(database, "head")

    async def exercise():
        app = create_application(
            Settings(
                _env_file=None, environment="test", database_url=database, log_level="CRITICAL"
            )
        )
        # No lifespan tasks: neither quote sources nor notifications are activated.
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                payload = await _product_payload(client)
                issuer = await client.post(
                    "/api/v1/market-reference-data/issuers",
                    json={"legal_name": "VONT FINL.", "display_name": "Synthetic coverage issuer"},
                )
                assert issuer.status_code == 201, issuer.text
                payload.update(
                    issuer_id=issuer.json()["id"],
                    isin="DE000ZZ00001",
                    display_name="Synthetic coverage warrant",
                    strike_currency_code="EUR",
                )
                created = await client.post("/api/v1/warrants", json=payload)
                assert created.status_code == 201, created.text
                warrant = created.json()
                # Fresh migrations seed XETR, not every venue in the user's catalog.
                # Create this fixture explicitly through the reference-data owner API.
                venue_response = await client.post(
                    "/api/v1/market-reference-data/trading-venues",
                    json={
                        "mic": "XSTU",
                        "name": "Synthetic coverage venue",
                        "country_code": "DE",
                        "timezone": "Europe/Berlin",
                    },
                )
                assert venue_response.status_code == 201, venue_response.text
                venue = venue_response.json()
                listed = await client.post(
                    f'/api/v1/warrants/{warrant["id"]}/listings',
                    json={"trading_venue_id": venue["id"], "quotation_currency_code": "EUR"},
                )
                assert listed.status_code == 201, listed.text
                listing = listed.json()
                bought = await client.post(
                    "/api/v1/trade-position/purchases/external",
                    json={
                        "product_id": warrant["id"],
                        "quantity": 10,
                        "price_per_unit": "1.00",
                        "executed_on": "2026-08-17",
                        "execution_timezone": "Europe/Berlin",
                        "request_id": str(uuid4()),
                    },
                )
                assert bought.status_code == 201, bought.text
                trade_id = bought.json()["trade"]["id"]
                workspace = UUID(warrant["workspace_id"])
                now = datetime.now(UTC)
                quote = WarrantQuoteSnapshot(
                    UUID(listing["id"]),
                    Decimal("1.25"),
                    Decimal("1.28"),
                    "EUR",
                    warrant["isin"],
                    "ISSUER",
                    now,
                    isin=warrant["isin"],
                    max_quote_age_seconds=900,
                )
                adapter = SimpleNamespace(probe=AsyncMock(return_value=(quote, now, False)))
                container = app.state.container
                async with container.database.session_context() as session:
                    await configure_warrant(
                        session, adapter, workspace_id=workspace, warrant_id=UUID(warrant["id"])
                    )
                result = MarketDataResult(
                    quote,
                    MarketDataProvider.VONTOBEL_MARKETS,
                    MarketDataCapability.WARRANT_LISTING_QUOTE,
                    uuid4(),
                    now,
                    CacheStatus.MISS,
                    QualityStatus.VALID,
                    (),
                    0,
                    1,
                )
                provider = SimpleNamespace(get_warrant_listing_quote=AsyncMock(return_value=result))
                await RetainedWarrantQuoteProvider(
                    container.database, provider, result.provider
                ).get_warrant_listing_quote(
                    WarrantQuoteRequest(workspace, quote.warrant_listing_id, uuid4(), now)
                )
                provider.get_warrant_listing_quote.reset_mock()
                # The diagnostics see an existing enabled route; no provider is contacted by GET.
                app.state.container = replace(container, vontobel=provider)
                original_position = (
                    await client.get(f"/api/v1/trade-position/trades/{trade_id}/position")
                ).json()
                original_timeline = (
                    await client.get(f"/api/v1/trade-position/trades/{trade_id}/timeline")
                ).json()
                for _ in range(2):
                    response = await client.get("/api/v1/market-data/warrants/quote-coverage")
                    assert response.status_code == 200, response.text
                    report = response.json()
                    assert (
                        report["execution_usable"] is False and report["scheduler_enabled"] is False
                    )
                    assert len(report["items"]) == 1
                    item = report["items"][0]
                    assert item["warrant_id"] == warrant["id"] and item["issuer"] == "VONT FINL."
                    assert item["coverage"] == "BID_WITHIN_AGE_BUDGET"
                    route = next(r for r in item["routes"] if r["provider"] == "VONTOBEL_MARKETS")
                    assert (
                        Decimal(route["bid"]) == Decimal("1.25")
                        and route["provider_exchange_code"] == "ISSUER"
                    )
                    assert (
                        datetime.fromisoformat(route["observed_at"].replace("Z", "+00:00")) == now
                    )
                    assert route["mapping_status"] == "ACTIVE"
                provider.get_warrant_listing_quote.assert_not_awaited()
                assert (
                    await client.get(f"/api/v1/trade-position/trades/{trade_id}/position")
                ).json() == original_position
                assert (
                    await client.get(f"/api/v1/trade-position/trades/{trade_id}/timeline")
                ).json() == original_timeline
                sold = await client.post(
                    f"/api/v1/trade-position/trades/{trade_id}/sales",
                    json={
                        "quantity": 10,
                        "price_per_unit": "1.25",
                        "executed_on": "2026-08-20",
                        "execution_timezone": "Europe/Berlin",
                        "request_id": str(uuid4()),
                    },
                )
                assert sold.status_code == 201, sold.text
                assert (await client.get("/api/v1/market-data/warrants/quote-coverage")).json()[
                    "items"
                ] == []
        finally:
            await app.state.container.database.dispose()

    asyncio.run(exercise())
