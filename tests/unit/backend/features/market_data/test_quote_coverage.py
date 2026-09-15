from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import TypeAdapter

from app.core.config import Settings
from app.features.market_data.api.quote_coverage import get_quote_coverage_service
from app.features.market_data.domain.enums import (
    CacheStatus,
    MarketDataCapability,
    MarketDataProvider,
    QualityStatus,
)
from app.features.market_data.domain.models import WarrantQuoteSnapshot
from app.features.market_data.service.quote_coverage import (
    ProductRecord,
    QuoteCoverageService,
    RouteRecord,
)
from app.features.market_data.service.types import MarketDataResult
from app.main import create_application

NOW = datetime(2026, 9, 15, 10, tzinfo=UTC)


def context():
    workspace, listing, product = uuid4(), uuid4(), uuid4()
    quote = WarrantQuoteSnapshot(
        listing,
        Decimal("1.01"),
        Decimal("1.03"),
        "EUR",
        "DE000AB00001",
        "ISSUER",
        NOW - timedelta(seconds=60),
        max_quote_age_seconds=900,
    )
    result = MarketDataResult(
        quote,
        MarketDataProvider.VONTOBEL_MARKETS,
        MarketDataCapability.WARRANT_LISTING_QUOTE,
        uuid4(),
        NOW,
        CacheStatus.MISS,
        QualityStatus.VALID,
        (),
        0,
        1,
    )
    payload = TypeAdapter(MarketDataResult[WarrantQuoteSnapshot | None]).dump_python(
        result, mode="json"
    )
    route = RouteRecord(
        "VONTOBEL_MARKETS",
        listing,
        "XSTU",
        "EUR",
        uuid4(),
        "ACTIVE",
        quote.provider_symbol,
        "ISSUER",
        NOW,
        "ROUTE_IDENTITY_VERIFIED",
        "identity",
        "identity",
        payload,
    )
    record = ProductRecord(
        product,
        "Synthetic warrant",
        quote.provider_symbol,
        None,
        "VONT FINL.",
        True,
        True,
        (route,),
    )
    reader = SimpleNamespace(held_products=AsyncMock(return_value=(record,)))
    service = QuoteCoverageService(reader, (("VONTOBEL_MARKETS", True), ("GETTEX_DELAYED", False)))
    scheduler = {"workspace_id": workspace, "enabled": True, "leader": True, "jobs": []}
    return workspace, route, record, reader, service, scheduler


@pytest.mark.asyncio
async def test_read_reassesses_original_time_but_grants_no_valuation_or_order_permission():
    workspace, route, _, reader, service, scheduler = context()
    before = deepcopy(route.payload)
    result = await service.report(workspace, scheduler, as_of=NOW)
    assert result.items[0].coverage == "BID_WITHIN_AGE_BUDGET"
    assert result.items[0].routes[0].bid == Decimal("1.01")
    assert result.items[0].routes[0].age_seconds == 60
    assert result.execution_usable is False
    assert result.items[0].refresh_status == "NOT_SCHEDULED"
    assert result.configured_sources == ("VONTOBEL_MARKETS",)
    later = await service.report(workspace, scheduler, as_of=NOW + timedelta(minutes=16))
    assert later.items[0].coverage == "HISTORICAL_BID_ONLY"
    assert later.items[0].routes[0].retrieved_at == NOW
    assert route.payload == before
    reader.held_products.assert_awaited_with(workspace)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case",
    [
        "disabled",
        "inactive",
        "unmapped",
        "identity_changed",
        "foreign_listing",
        "wrong_isin",
        "wrong_currency",
        "wrong_provider",
        "wrong_venue",
        "corrupt",
        "crossed",
        "future",
        "no_quote",
    ],
)
async def test_bad_routes_or_payloads_cannot_be_presented_as_available(case):
    workspace, route, record, reader, service, scheduler = context()
    if case == "disabled":
        service.sources = (("VONTOBEL_MARKETS", False),)
    elif case == "inactive":
        record = replace(record, active=False)
    elif case == "unmapped":
        route = replace(route, identity_key=None, route_reason="MAPPING_DISABLED")
    elif case == "identity_changed":
        route = replace(route, observation_identity_key="old")
    elif case == "corrupt":
        route = replace(route, payload={"secret": "DO_NOT_LEAK"})
    else:
        data = route.payload["data"]
        if case == "foreign_listing":
            data["warrant_listing_id"] = str(uuid4())
        elif case == "wrong_isin":
            data["provider_symbol"] = "DE000AB00002"
        elif case == "wrong_currency":
            data["currency"] = "USD"
        elif case == "wrong_provider":
            route.payload["provider"] = "FRANKFURT_QUOTES"
        elif case == "wrong_venue":
            data["venue_mic"] = "XFRA"
        elif case == "crossed":
            data["ask"] = "0.50"
        elif case == "future":
            data["observed_at"] = (NOW + timedelta(days=1)).isoformat()
        elif case == "no_quote":
            route.payload["data"] = None
    reader.held_products.return_value = (replace(record, routes=(route,)),)
    result = await service.report(workspace, scheduler, as_of=NOW)
    assert result.items[0].coverage not in {
        "BID_WITHIN_AGE_BUDGET",
        "HISTORICAL_BID_ONLY",
        "REFERENCE_ONLY",
    }
    assert result.items[0].routes[0].bid is None
    assert "DO_NOT_LEAK" not in str(result)


@pytest.mark.asyncio
async def test_unknown_time_reference_is_never_a_bid_and_error_is_not_hidden():
    workspace, route, record, _, service, scheduler = context()
    data = route.payload["data"]
    data.update(
        bid=None,
        ask=None,
        reference_price="1.11",
        reference_price_type="PREVIOUS_CLOSE",
        observed_at=None,
    )
    scheduler["jobs"] = [
        {
            "job": f"WARRANT_QUOTES:{record.warrant_id}",
            "status": "ERROR",
            "reason": "https://secret.example/token",
            "checked_at": NOW,
            "next_run_at": NOW + timedelta(minutes=5),
        }
    ]
    result = await service.report(workspace, scheduler, as_of=NOW)
    item = result.items[0]
    assert item.coverage == "REFERENCE_ONLY"
    assert item.routes[0].bid is None and item.routes[0].observed_at is None
    assert item.routes[0].age_seconds is None
    assert item.refresh_status == "ERROR" and item.refresh_reason is None
    assert "secret" not in str(result)
    scheduler["workspace_id"] = uuid4()
    other = await service.report(workspace, scheduler, as_of=NOW)
    assert other.items[0].checked_at is None and other.scheduler_enabled is False


@pytest.mark.asyncio
async def test_latest_failed_attempt_does_not_turn_retained_quote_into_fresh_success():
    workspace, route, record, _, service, scheduler = context()
    scheduler["jobs"] = [
        {
            "job": f"WARRANT_QUOTES:{record.warrant_id}",
            "status": "AVAILABLE",
            "source_attempts": [
                {
                    "source": route.provider,
                    "warrant_listing_id": route.listing_id,
                    "status": "AVAILABLE",
                    "refresh_error": "VONTOBEL_QUOTE_TIMEOUT",
                }
            ],
        }
    ]
    result = await service.report(workspace, scheduler, as_of=NOW)
    assert result.items[0].coverage == "HISTORICAL_BID_ONLY"
    assert result.items[0].routes[0].refresh_error == "VONTOBEL_QUOTE_TIMEOUT"


@pytest.mark.asyncio
async def test_missing_routes_discovery_and_running_state_are_separate():
    workspace, _, record, reader, service, scheduler = context()
    reader.held_products.return_value = (replace(record, routes=()),)
    key = f"WARRANT_QUOTES:{record.warrant_id}"
    scheduler["jobs"] = [
        {"job": key, "status": "PENDING"},
        {"job": f"FRANKFURT_MAPPING:{record.warrant_id}", "reason": "FRANKFURT_ISIN_INVALID"},
    ]
    scheduler["current_jobs"] = {"WARRANTS": key}
    result = await service.report(workspace, scheduler, as_of=NOW)
    assert result.items[0].coverage == "NO_USABLE_ROUTE"
    assert result.items[0].refresh_status == "RUNNING"
    assert result.items[0].discovery_reasons == ("FRANKFURT_ISIN_INVALID",)
    with pytest.raises(ValueError, match="AWARE"):
        await service.report(workspace, scheduler, as_of=NOW.replace(tzinfo=None))


def test_api_is_read_only_and_uses_runtime_workspace_not_request_parameter():
    workspace, _, _, _, service, scheduler = context()
    app = create_application(Settings(_env_file=None, environment="test"))
    app.state.market_data_refresh = SimpleNamespace(
        workspace_id=workspace, status=lambda: scheduler
    )
    app.dependency_overrides[get_quote_coverage_service] = lambda: service
    client = TestClient(app)
    response = client.get(
        "/api/v1/market-data/warrants/quote-coverage?workspace_id=" + str(uuid4())
    )
    assert response.status_code == 200, response.text
    assert response.json()["execution_usable"] is False
    service.reader.held_products.assert_awaited_once_with(workspace)
    assert client.post("/api/v1/market-data/warrants/quote-coverage").status_code == 405
