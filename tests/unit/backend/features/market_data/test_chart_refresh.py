"""Explicit chart setup resumes independently of UI and the global discovery switch."""

from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from tests.unit.backend.features.market_data.test_refresh import runtime, session_context

from app.core.di import ApplicationContainer
from app.features.market_data.domain.enums import MappingStatus
from app.features.market_data.service import refresh as module
from app.features.market_data.service.refresh_catalog import RefreshInstrument


@pytest.mark.asyncio
async def test_explicit_chart_jobs_run_in_existing_lane_with_auto_discovery_disabled(monkeypatch):
    value = runtime(auto_configure=False)
    pending = RefreshInstrument(uuid4(), "One ETF", "US0000000001", setup_code="ETF_US_ONE")
    reference = RefreshInstrument(uuid4(), "S&P 500", None, reference_id=uuid4())
    monkeypatch.setattr(module, "read_catalog", AsyncMock(return_value=([], [pending, reference])))
    value._setup_chart = AsyncMock(return_value={"reason": "CHART_SETUP_COMPLETE"})
    value._reference = AsyncMock(return_value={"reason": "COMPLETED_EOD_IMPORTED"})
    value._configure_underlying = AsyncMock()
    await value.run_once()
    await value.run_once()
    value._setup_chart.assert_awaited_once_with(pending)
    value._reference.assert_awaited_once_with(reference)
    value._configure_underlying.assert_not_awaited()
    assert {job["lane"] for job in value.jobs.values()} == {"UNDERLYINGS"}
    assert value.jobs[f"REFERENCE_EOD:{reference.reference_id}"]["listing_id"] is None


@pytest.mark.asyncio
async def test_setup_owner_success_wakes_next_catalog_without_a_browser(monkeypatch):
    value = runtime(auto_configure=False)
    item = RefreshInstrument(uuid4(), "One ETF", None, setup_code="ETF_US_ONE")
    service = SimpleNamespace(
        configure_item=AsyncMock(
            return_value=SimpleNamespace(
                setup_status="CONFIGURED",
                setup_reason=None,
                target_key=f"listing:{uuid4()}",
            )
        )
    )

    @asynccontextmanager
    async def factory(_container, workspace_id):
        assert workspace_id == value.workspace_id
        yield service

    monkeypatch.setattr(ApplicationContainer, "chart_watchlist_service", factory)
    result = await value._setup_chart(item)
    assert result["status"] == "AVAILABLE" and value.wake.is_set()
    assert service.configure_item.call_args.args == ("ETF_US_ONE",)


@pytest.mark.asyncio
@pytest.mark.parametrize("last_offset", [None, 2, 30])
async def test_direct_index_uses_existing_import_owner_and_completed_eod_window(
    monkeypatch, last_offset
):
    value = runtime()
    end = datetime.now(UTC).date() - timedelta(days=1)
    last_day = end - timedelta(days=last_offset) if last_offset is not None else None
    mapping = SimpleNamespace(
        id=uuid4(),
        version=4,
        status=MappingStatus.ACTIVE,
        validated_at=datetime.now(UTC),
        market_data_instrument_id=uuid4(),
        provider_symbol="GSPC",
        provider_exchange_code="INDX",
    )
    session = SimpleNamespace(scalar=AsyncMock(side_effect=[mapping, last_day]))
    value.container = replace(
        value.container,
        eodhd=SimpleNamespace(),
        database=SimpleNamespace(session_context=lambda: session_context(session)),
    )
    importer = SimpleNamespace(
        import_daily_prices=AsyncMock(
            return_value=SimpleNamespace(
                inserted=1,
                updated=0,
                unchanged=5,
            )
        )
    )

    @asynccontextmanager
    async def factory(_container):
        yield importer

    monkeypatch.setattr(ApplicationContainer, "reference_market_data_service", factory)
    reference_id = uuid4()
    result = await value._reference(
        RefreshInstrument(reference_id, "S&P 500", None, reference_id=reference_id)
    )
    request = importer.import_daily_prices.call_args.kwargs
    assert request["market_reference_id"] == reference_id
    assert request["expected_mapping"].id == mapping.id
    assert request["expected_mapping"].version == 4
    assert request["expected_mapping"].provider_symbol == "GSPC"
    assert request["expected_mapping"].provider_exchange_code == "INDX"
    assert request["end_date"] == end
    assert request["start_date"] == (
        max(end - timedelta(days=400), last_day - timedelta(days=7))
        if last_day
        else end - timedelta(days=400)
    )
    assert result["processed"] == 6 and result["execution_usable"] is False
    assert result["provider_exchange_code"] == "INDX"


@pytest.mark.asyncio
async def test_disabled_reference_provider_is_not_silently_activated():
    value = runtime()
    result = await value._reference(
        RefreshInstrument(uuid4(), "S&P 500", None, reference_id=uuid4())
    )
    assert result == {"status": "BLOCKED", "reason": "EODHD_DISABLED"}
