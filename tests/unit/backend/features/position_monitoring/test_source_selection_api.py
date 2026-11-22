"""Regression: selection provenance must survive the public valuation response."""

import importlib
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.features.market_data.domain.enums import MarketDataProvider
from app.features.position_monitoring.backend_valuations import BackendProductValuations
from app.features.position_monitoring.service.product_valuation import (
    ProductPositionValuation,
    ProductValuationStatus,
)
from app.features.position_monitoring.service.quote_sources import (
    QuoteSourceAttempt,
    QuoteSourceAttemptStatus,
)

api = importlib.import_module("app.features.position_monitoring.api.router")


@pytest.mark.parametrize(
    ("selection", "reason", "policy"),
    [
        ("SELECTED", "VERIFIED_JPMORGAN_ISSUER_INDICATION", "JPMORGAN_ISSUER_INDICATION_V1"),
        ("NO_VERIFIED_QUOTE_SOURCE", "NO_VERIFIED_QUOTE_SOURCE", "POSITION_QUOTE_SOURCE_POLICY_V1"),
        (None, None, None),
    ],
)
def test_valuation_json_preserves_selection_metadata(monkeypatch, selection, reason, policy):
    selected = selection == "SELECTED"
    trade_id = uuid4()
    value = ProductPositionValuation(
        trade_id=trade_id,
        position_id=uuid4(),
        status=(
            ProductValuationStatus.INDICATIVE if selected else ProductValuationStatus.UNAVAILABLE
        ),
        reason="QUOTE_TIMESTAMP_UNKNOWN_INDICATIVE_ANALYSIS_ONLY" if selected else "NO_QUOTE",
        source_selection_status=selection,
        source_selection_reason=reason,
        source_selection_policy_version=policy,
        quote_provider=MarketDataProvider.JPMORGAN if selected else None,
        bid=Decimal("0.2300") if selected else None,
        ask=None,
        currency="EUR" if selected else None,
        quote_time_text="20:11:25" if selected else None,
        quote_time_basis="DATE_AND_TIMEZONE_UNKNOWN" if selected else None,
        monitoring_usable=selected,
    )
    for_trade = AsyncMock(return_value=value)
    monkeypatch.setattr(
        api,
        "ProductPositionValuationService",
        lambda **kwargs: SimpleNamespace(for_trade=for_trade),
    )
    monkeypatch.setattr(api, "build_warrant_quote_resolver", lambda container: None)
    application = FastAPI()
    application.include_router(api.router)
    application.dependency_overrides[api.get_container] = lambda: SimpleNamespace(database=None)
    with TestClient(application) as client:
        response = client.get(f"/api/v1/position-monitoring/trades/{trade_id}/product-valuation")
    assert response.status_code == 200
    data = response.json()
    assert data["source_selection_status"] == selection
    assert data["source_selection_reason"] == reason
    assert data["source_selection_policy_version"] == policy
    assert data["bid"] == ("0.2300" if selected else None)
    assert data["ask"] is None
    assert data["quote_time_text"] == value.quote_time_text
    assert data["quote_time_basis"] == value.quote_time_basis
    assert data["quote_observed_at"] is None
    assert data["execution_usable"] is False
    for_trade.assert_awaited_once_with(trade_id)


async def test_bidless_refresh_diagnostics_survive_api_and_backend_reader(monkeypatch):
    trade_id = uuid4()
    attempt = QuoteSourceAttempt(
        source="JPMORGAN",
        status=QuoteSourceAttemptStatus.INSUFFICIENT,
        reason="BID_MISSING",
        delayed=False,
        warrant_listing_id=uuid4(),
        currency="EUR",
        refresh_error="JPMORGAN_SNAPSHOT_TIMEOUT",
        retained=True,
        provider_reason="QUOTE_TIMESTAMP_UNKNOWN_INDICATIVE_ANALYSIS_ONLY",
        quote_time_basis="DATE_AND_TIMEZONE_UNKNOWN",
    )
    value = ProductPositionValuation(
        trade_id=trade_id,
        position_id=uuid4(),
        status=ProductValuationStatus.MISSING,
        reason="NO_USABLE_WARRANT_QUOTE",
        source_attempts=(attempt,),
    )
    for_trade = AsyncMock(return_value=value)
    monkeypatch.setattr(
        api,
        "ProductPositionValuationService",
        lambda **kwargs: SimpleNamespace(for_trade=for_trade),
    )
    monkeypatch.setattr(api, "build_warrant_quote_resolver", lambda container: None)
    application = FastAPI()
    application.include_router(api.router)
    application.dependency_overrides[api.get_container] = lambda: SimpleNamespace(database=None)
    diagnostics = []
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=application), base_url="http://test"
    ) as client:
        reader = BackendProductValuations(client, diagnostics=diagnostics)
        restored = await reader.for_trade(trade_id)

    assert restored is not None
    assert restored.status is ProductValuationStatus.MISSING
    assert restored.bid is None
    assert restored.monitoring_usable is False
    assert restored.execution_usable is False
    assert restored.source_attempts == (attempt,)
    exposed = diagnostics[0]["source_attempts"][0]
    assert exposed["reason"] == "BID_MISSING"
    assert exposed["refresh_error"] == "JPMORGAN_SNAPSHOT_TIMEOUT"
    assert exposed["retained"] is True
    assert exposed["provider_reason"] == "QUOTE_TIMESTAMP_UNKNOWN_INDICATIVE_ANALYSIS_ONLY"
    assert exposed["quote_time_basis"] == "DATE_AND_TIMEZONE_UNKNOWN"
    assert exposed["observed_at"] is None
    for_trade.assert_awaited_once_with(trade_id)
