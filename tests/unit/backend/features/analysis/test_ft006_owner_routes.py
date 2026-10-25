"""HTTP identity boundaries shared by listing and native reference analyses."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import Environment, Settings
from app.features.analysis.api.dependencies import get_market_analysis_service
from app.features.market.api.dependencies import get_market_reference_analysis_service
from app.main import create_application


def application(service: AsyncMock):
    app = create_application(
        Settings(_env_file=None, environment=Environment.TEST, log_level="CRITICAL")
    )
    app.dependency_overrides[get_market_analysis_service] = lambda: service
    app.dependency_overrides[get_market_reference_analysis_service] = lambda: service
    return app


def run_summary():
    return SimpleNamespace(
        version=1,
        status="COMPLETED",
        quality_status="GOOD",
        model_id="EOD_TREND_MOMENTUM",
        model_version="1.0.1",
        observation_count=200,
        analysis_time=datetime.now(UTC),
        input_hash="a" * 64,
    )


@pytest.mark.parametrize("owner", ["listing", "reference"])
@pytest.mark.parametrize("selected", [None, "1.0.0", "1.0.1"])
def test_new_command_passes_the_fixed_or_explicit_runtime_to_its_owner(owner, selected):
    service = AsyncMock()
    method = service.run if owner == "listing" else service.run_market_reference
    method.return_value = run_summary()
    prefix = (
        "/api/v1/market-analyses"
        if owner == "listing"
        else "/api/v1/top-down-reference-data/market-reference-analyses"
    )
    body = {"start_date": "2025-01-01", "end_date": "2025-12-31"}
    if selected is not None:
        body["model_version"] = selected
    with TestClient(application(service)) as client:
        response = client.post(f"{prefix}/{uuid4()}/runs", json=body)
    assert response.status_code == 201, response.text
    method.assert_awaited_once()
    assert method.await_args.kwargs["model_version"] == (selected or "1.0.1")


@pytest.mark.parametrize("owner", ["listing", "reference"])
def test_unknown_http_version_never_calls_an_owner(owner):
    service = AsyncMock()
    prefix = (
        "/api/v1/market-analyses"
        if owner == "listing"
        else "/api/v1/top-down-reference-data/market-reference-analyses"
    )
    with TestClient(application(service)) as client:
        response = client.post(
            f"{prefix}/{uuid4()}/runs",
            json={
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "model_version": "latest",
            },
        )
    assert response.status_code == 422
    service.run.assert_not_awaited()
    service.run_market_reference.assert_not_awaited()


def test_native_reference_detail_retains_instrument_and_null_listing_identity():
    service = AsyncMock()
    analysis_id, instrument_id = uuid4(), uuid4()
    analysis = SimpleNamespace(
        id=analysis_id,
        underlying_id=None,
        listing_id=None,
        market_data_instrument_id=instrument_id,
        created_at=datetime.now(UTC),
        created_by="synthetic-ft006-http-test",
    )
    run = run_summary()
    run.parameters, run.metrics, run.notes, run.data_sources = {}, {}, [], ["EODHD"]
    service.details.return_value = (analysis, run, (), ())
    with TestClient(application(service)) as client:
        response = client.get(f"/api/v1/market-analyses/{analysis_id}/runs/1")
    assert response.status_code == 200, response.text
    source = response.json()["analysis"]
    assert source["underlying_id"] is None
    assert source["listing_id"] is None
    assert source["market_data_instrument_id"] == str(instrument_id)
    service.run.assert_not_awaited()
    service.run_market_reference.assert_not_awaited()
