"""The existing status API exposes actual attempts without running work on GET."""

import asyncio
from copy import deepcopy
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.features.market_data.service import refresh as refresh_module
from app.features.market_data.service.refresh_catalog import RefreshInstrument
from app.main import create_application


@pytest.mark.asyncio
async def test_status_serializes_failures_retry_and_recovery_without_triggering_work(monkeypatch):
    app = create_application(Settings(_env_file=None, environment="test", log_level="CRITICAL"))
    runtime = app.state.market_data_refresh
    runtime.settings.enabled = True
    runtime.timer = lambda: 1000
    listing_id = uuid4()
    item = RefreshInstrument(uuid4(), "Synthetic warrant", None)
    key = f"WARRANT_QUOTES:{item.id}"
    monkeypatch.setattr(refresh_module, "read_catalog", AsyncMock(return_value=([item], [])))
    runtime._warrant = AsyncMock(
        return_value={
            "status": "MISSING",
            "reason": "NO_USABLE_WARRANT_QUOTE",
            "source_attempts": [
                {
                    "source": "GETTEX_DELAYED",
                    "warrant_listing_id": listing_id,
                    "status": "ERROR",
                    "reason": "MarketDataUnavailableError",
                }
            ],
        }
    )
    entered, release = asyncio.Event(), asyncio.Event()

    async def recover(_item):
        entered.set()
        await release.wait()
        now = datetime.now(UTC)
        return {
            "status": "AVAILABLE",
            "reason": "QUOTE_OBSERVATIONS_AVAILABLE",
            "source_attempts": [
                {
                    "source": "GETTEX_DELAYED",
                    "warrant_listing_id": listing_id,
                    "status": "AVAILABLE",
                    "reason": "VALID_BID_AVAILABLE",
                }
            ],
            "quotes": [
                {
                    "provider": "GETTEX_DELAYED",
                    "warrant_listing_id": listing_id,
                    "bid": Decimal("2.40"),
                    "ask": Decimal("2.45"),
                    "currency": "EUR",
                    "provider_symbol": "DE000VH2LU21",
                    "provider_exchange_code": "MUND",
                    "observed_at": now,
                    "retrieved_at": now,
                }
            ],
        }

    try:
        await runtime.run_once()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            before = deepcopy(runtime.jobs)
            deadlines = dict(runtime._due)
            for _ in range(2):
                response = await client.get("/api/v1/market-data/refresh/status")
                assert response.status_code == 200
                job = response.json()["jobs"][0]
                assert job["status"] == "MISSING"
                assert job["execution"]["running"] is False
                assert job["diagnostics"]["scope"] == "PROCESS_LOCAL"
                source = next(c for c in job["diagnostics"]["checks"] if c["kind"] == "SOURCE")
                assert source["listing_id"] == str(listing_id)
                assert source["reason"] == "MARKET_DATA_UNAVAILABLE_ERROR"
                assert source["consecutive_failures"] == 1
                assert source["first_failure_at"] == job["checked_at"]
            runtime._warrant.assert_awaited_once()
            assert runtime.jobs == before
            assert runtime._due == deadlines
            assert not runtime.wake.is_set()

            runtime._warrant = AsyncMock(side_effect=recover)
            runtime.timer = lambda: 1300
            await runtime.run_once(wait_for_completion=False)
            await asyncio.wait_for(entered.wait(), timeout=1)
            runtime.timer = lambda: 1312
            response = await client.get("/api/v1/market-data/refresh/status")
            running = response.json()["jobs"][0]
            assert running["execution"]["running"] is True
            assert running["execution"]["elapsed_seconds"] == 12
            assert running["checked_at"] == job["checked_at"]
            assert running["diagnostics"] == job["diagnostics"]
            assert response.json()["current_jobs"]["WARRANTS"] == key

            release.set()
            await asyncio.gather(*runtime._lane_tasks.values())
            response = await client.get("/api/v1/market-data/refresh/status")
            recovered = response.json()["jobs"][0]
            assert recovered["status"] == "AVAILABLE"
            assert recovered["execution"]["running"] is False
            assert all(c["consecutive_failures"] == 0 for c in recovered["diagnostics"]["checks"])
            assert all(
                c["recovered_at"] == recovered["checked_at"]
                for c in recovered["diagnostics"]["checks"]
            )
            runtime._warrant.assert_awaited_once()
            source = next(c for c in recovered["diagnostics"]["checks"] if c["kind"] == "SOURCE")
            assert source["qualified_success"] is True
            assert source["quote_status"] == "FRESH"
            assert source["last_success_at"] == source["quote_retrieved_at"]
    finally:
        release.set()
        await runtime.stop()
        await app.state.container.close()
