"""Regression: selection provenance must survive the public valuation response."""

import importlib
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.features.market_data.domain.enums import MarketDataProvider
from app.features.position_monitoring.service.product_valuation import (
    ProductPositionValuation,
    ProductValuationStatus,
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
