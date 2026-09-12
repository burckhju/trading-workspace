"""Real wire field names through adapter, source selection and valuation API."""

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.di import get_container
from app.features.market_data.domain.errors import InvalidMarketDataValue
from app.features.position_monitoring.service.product_valuation import (
    ProductPositionValuationService,
)
from app.features.position_monitoring.service.quote_sources import (
    MultiSourceWarrantQuoteResolver,
    NamedWarrantQuoteSource,
)
from app.providers.frankfurt_quotes.public import FrankfurtPublicPrice
from tests.unit.backend.features.position_monitoring.test_product_valuation import (
    _context,
    _Database,
    _Provider,
    _quote_result,
    _Session,
    monitoring_api,
)
from tests.unit.backend.providers.frankfurt_quotes.test_adapter_api import context
from tests.unit.backend.providers.frankfurt_quotes.test_public import (
    assess,
    public_settings,
    wire,
)
from tests.unit.backend.providers.frankfurt_quotes.test_schema import (
    NOW,
    payload,
)
from tests.unit.backend.providers.frankfurt_quotes.test_schema import (
    assess as assess_normalized,
)


@pytest.mark.parametrize(
    "changes,kind,age,warning",
    [
        ({}, "LAST_TRADE", 10, "REFERENCE_PRICE_INDICATIVE_ANALYSIS_ONLY"),
        (
            {"timestampLastPrice": (NOW - timedelta(days=90)).isoformat()},
            "LAST_TRADE",
            90 * 86400,
            "OUTDATED_QUOTE_INDICATIVE_ANALYSIS_ONLY",
        ),
        (
            {"lastPrice": None, "closingPricePrevTradingDay": "0.231"},
            "PREVIOUS_CLOSE",
            None,
            "QUOTE_TIMESTAMP_UNKNOWN_INDICATIVE_ANALYSIS_ONLY",
        ),
        (
            {"timestampLastPrice": None},
            "LAST_TRADE",
            None,
            "QUOTE_TIMESTAMP_UNKNOWN_INDICATIVE_ANALYSIS_ONLY",
        ),
    ],
)
def test_reference_price_reaches_trade_api_without_invented_bid_or_timestamp(
    monkeypatch, changes, kind, age, warning
):
    adapter, _database, snapshots, _request, row = context()
    adapter.settings = public_settings()
    row[2].provider_exchange_code = "XSC"
    snapshots.load_public = AsyncMock(
        return_value=(FrankfurtPublicPrice.model_validate(wire(**changes)), NOW, False)
    )
    trade, position, evaluation, listing = _context()
    position.open_quantity, position.cost_basis = 2000, Decimal("1020")
    listing.id = evaluation.warrant_listing_id = row[0].id
    listing.symbol = None
    service = ProductPositionValuationService(
        database=_Database(
            _Session(trade=trade, position=position, evaluation=evaluation, listing=listing)
        ),
        quote_resolver=MultiSourceWarrantQuoteResolver(
            (NamedWarrantQuoteSource("FRANKFURT_QUOTES", adapter),)
        ),
    )
    monkeypatch.setattr(monitoring_api, "ProductPositionValuationService", lambda **_kw: service)
    monkeypatch.setattr(monitoring_api, "build_warrant_quote_resolver", lambda _container: None)
    app = FastAPI()
    app.include_router(monitoring_api.router)
    app.dependency_overrides[get_container] = lambda: SimpleNamespace(database=None)
    with TestClient(app) as http:
        response = http.get(f"/api/v1/position-monitoring/trades/{trade.id}/product-valuation")
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["status"] == "INDICATIVE"
    assert result["analysis_usable"] is result["monitoring_usable"] is True
    assert result["analysis_market_value"] == "462.000"
    assert Decimal(result["analysis_unrealized_gross_pnl"]) == Decimal("-558")
    assert result["analysis_warning"] == warning
    assert result["reference_price_type"] == kind
    assert result["reference_price"] == "0.231"
    assert result["quote_age_seconds"] == age
    assert result["quote_observed_at"] is None if age is None else result["quote_observed_at"]
    assert (
        result["quote_retrieved_at"]
        == result["quote_assessed_at"]
        == NOW.isoformat().replace("+00:00", "Z")
    )
    assert result["bid"] is result["ask"] is result["market_value"] is None
    assert result["quote_provider"] == "FRANKFURT_QUOTES"
    assert result["provider_identity"] == result["isin"] == "DE000VH2LU21"
    assert result["provider_exchange_code"] == "XSC"
    assert result["quote_venue_mic"] == "XFRA"
    assert result["quote_delay_seconds"] is result["wkn"] is None
    assert result["execution_usable"] is result["valuation_usable"] is False
    assert result["source_attempts"][0]["reference_price_type"] == kind
    assert result["source_attempts"][0]["bid_available"] is False


def test_previous_close_never_inherits_last_trade_timestamp():
    value = assess(lastPrice=None, closingPricePrevTradingDay="0.231")
    assert value.analysis_usable is True
    assert value.record.close_price == Decimal("0.231")
    assert value.record.last_price is value.record.last_at is value.record.close_at is None
    assert value.observed_at is value.age_seconds is None
    assert value.source_mode == "OFFICIAL_WEBSITE_PREVIOUS_CLOSE"


@pytest.mark.parametrize("patch", [{"wkn": "WRONG1"}, {"currency": "USD"}, {"ask": "0.01"}])
def test_old_snapshot_or_delay_never_masks_invalid_identity_or_crossed_quote(patch):
    data = payload()
    data["generated_at"] = (NOW - timedelta(days=5)).isoformat()
    data["delay_seconds"] = 1200
    data["records"][0].update(patch)
    result = assess_normalized(data)
    assert result.status == "ERROR"
    assert result.analysis_usable is False


@pytest.mark.asyncio
async def test_cached_reference_age_is_assessed_now_and_wide_spread_is_not_corrected():
    trade, position, evaluation, listing = _context()
    value = _quote_result(listing_id=listing.id, bid=Decimal("0.24"), ask=Decimal("2.40"))
    value = replace(
        value,
        data=replace(value.data, assessed_at=value.retrieved_at + timedelta(days=3)),
    )
    result = await ProductPositionValuationService(
        database=_Database(
            _Session(trade=trade, position=position, evaluation=evaluation, listing=listing)
        ),
        quote_provider=_Provider(value),
    ).for_trade(trade.id)
    assert result.quote_age_seconds == 3 * 86400
    assert result.analysis_usable is result.monitoring_usable is True
    assert result.spread_absolute == Decimal("2.16")
    assert result.spread_percent == Decimal("900")
    assert result.ask == Decimal("2.40")
    assert result.execution_usable is False


@pytest.mark.asyncio
async def test_invalid_currency_does_not_shadow_valid_fallback():
    listing_id = uuid4()
    first = _Provider(_quote_result(listing_id=listing_id, currency="USD"))
    second = _Provider(_quote_result(listing_id=listing_id))
    _, _, _, request, _ = context()
    request = replace(request, warrant_listing_id=listing_id, expected_currency="EUR")
    result = await MultiSourceWarrantQuoteResolver(
        (
            NamedWarrantQuoteSource("WRONG", first),
            NamedWarrantQuoteSource("RIGHT", second),
        )
    ).resolve(request)
    assert result.selected_source == "RIGHT"
    assert result.attempts[0].reason == "WARRANT_QUOTE_CURRENCY_MISMATCH"


@pytest.mark.parametrize(
    "patch",
    [
        {"reference_price": Decimal("0.1")},
        {"reference_price_type": "LAST_TRADE"},
        {"reference_price": Decimal("0.1"), "reference_price_type": "LAST_TRADE"},
        {"observed_at": None},
        {"max_quote_age_seconds": -1},
        {"feed_delay_seconds": -1},
    ],
)
def test_snapshot_rejects_untyped_prices_mixed_bid_and_reference_and_missing_bid_time(
    patch,
):
    with pytest.raises(InvalidMarketDataValue):
        replace(_quote_result(listing_id=uuid4()).data, **patch)
