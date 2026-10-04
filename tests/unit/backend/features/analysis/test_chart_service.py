from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from tests.unit.backend.features.analysis.test_time_series import DAY, END, identity, observation

from app.core.config import Environment, Settings
from app.features.analysis.api.charts import get_chart_service
from app.features.analysis.domain.enums import PriceField
from app.features.analysis.service.charts import ChartService
from app.features.market.service.chart_contracts import SectorChartContext, UnderlyingChartContext
from app.features.market_data.service.time_series import SeriesCoverage
from app.main import create_application


def service():
    item = identity(mapping_status="ACTIVE")
    context = SimpleNamespace(
        resolve=AsyncMock(return_value=item),
        references=AsyncMock(return_value=(item,)),
        reference_proxies=AsyncMock(return_value=()),
        sectors=AsyncMock(return_value=()),
        underlying=AsyncMock(),
    )
    prices = SimpleNamespace(
        observations=AsyncMock(return_value=(observation(), observation(1, "110"))),
        coverage=AsyncMock(return_value={item.instrument_id: SeriesCoverage(2, DAY, DAY)}),
    )
    return ChartService(context, prices, today=lambda: END), context, prices, item


@pytest.mark.asyncio
async def test_no_identity_does_not_read_prices_and_all_query_dates_bounded():
    value, context, prices, item = service()
    workspace = uuid4()
    result = await value.series(workspace, (item.key,), None, END, PriceField.CLOSE)
    assert result.series[0].points[1].normalized == 110
    prices.observations.assert_awaited_once_with(
        workspace, item.instrument_id, date(1900, 1, 1), END
    )
    from dataclasses import replace

    context.resolve.return_value = replace(item, instrument_id=None)
    prices.observations.reset_mock()
    result = await value.series(workspace, (item.key,), DAY, END, PriceField.CLOSE)
    assert result.comparison_status == "SERIES_UNAVAILABLE"
    prices.observations.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "start,end,keys",
    [
        (DAY, date(2099, 1, 1), ("a",)),
        (END, DAY, ("a",)),
        (date(1800, 1, 1), END, ("a",)),
        (None, date(1800, 1, 1), ("a",)),
        (DAY, END, ()),
        (DAY, END, ("a", "a")),
        (DAY, END, tuple("abcde")),
    ],
)
async def test_rejects_request_before_any_io(start, end, keys):
    value, context, prices, _ = service()
    with pytest.raises(ValueError):
        await value.series(uuid4(), keys, start, end, PriceField.CLOSE)
    context.resolve.assert_not_awaited()
    prices.observations.assert_not_awaited()


@pytest.mark.asyncio
async def test_catalog_includes_every_sector_empty_history_and_proxies_without_series_reads():
    value, context, prices, item = service()
    first = SectorChartContext(
        uuid4(), "10", "Energy", "GICS", "v1", True, item, item, "CONFIGURED", "/chart-setup"
    )
    second = SectorChartContext(
        uuid4(),
        "15",
        "Materials",
        "GICS",
        "v1",
        True,
        None,
        None,
        "MISSING_REFERENCE",
        "/chart-setup",
    )
    context.sectors.return_value = (first, second)
    context.reference_proxies.return_value = (item,)
    result = await value.catalog(uuid4(), END)
    assert len(result.sectors) == 2
    assert result.sectors[0].proxy_history.count == 2
    assert result.sectors[1].reference_history.count == 0
    assert result.proxies[0].identity == item
    prices.observations.assert_not_awaited()
    context.sectors.return_value = ()
    assert (await value.catalog(uuid4(), END)).taxonomy_status == "NO_SECTOR_TAXONOMY"
    expected = UnderlyingChartContext(uuid4(), item, None, None, ("NO_UNAMBIGUOUS_BENCHMARK",), END)
    context.underlying.return_value = expected
    assert await value.underlying(uuid4(), expected.underlying_id, END) == expected


def client():
    value, context, prices, item = service()
    app = create_application(
        Settings(_env_file=None, environment=Environment.TEST, log_level="CRITICAL")
    )
    app.dependency_overrides[get_chart_service] = lambda: value
    return TestClient(app), context, prices, item


def test_http_contract_preserves_decimal_strings_dates_and_source_times():
    http, _, prices, item = client()
    response = http.get(
        "/api/v1/market-charts/series",
        params={"target": item.key, "start_date": str(DAY), "end_date": str(END)},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert response.headers["Cache-Control"] == "private, max-age=30"
    assert data["series"][0]["points"][1]["normalized"] == "110.00000000"
    assert data["series"][0]["points"][0]["trading_date"] == "2026-09-01"
    assert data["series"][0]["points"][0]["observed_at"] is None
    assert data["series"][0]["points"][0]["source_updated_at"] is None
    assert data["model_version"] == "TIME_SERIES_COMPARISON/1.0.0"
    assert data["fx_adjusted"] is False
    assert len(prices.observations.await_args_list) == 1
    assert http.get("/api/v1/market-charts/catalog", params={"as_of": str(END)}).status_code == 200


@pytest.mark.parametrize(
    "params",
    [
        {},
        {"target": ["a"] * 5},
        {"target": "a", "price_field": "OPEN"},
        {"target": "a", "end_date": "2099-01-01"},
        {"target": "a", "start_date": "bad"},
    ],
)
def test_invalid_http_requests_are_explained(params):
    http, _, _, _ = client()
    assert http.get("/api/v1/market-charts/series", params=params).status_code == 422


def test_foreign_workspace_unknown_owner_returns_not_found():
    http, context, _, _ = client()
    context.resolve.side_effect = ValueError("listing not found in workspace")
    assert (
        http.get(
            "/api/v1/market-charts/series?target=listing:unknown&end_date=2026-10-01"
        ).status_code
        == 404
    )
    context.underlying.side_effect = ValueError("underlying not found in workspace")
    assert (
        http.get(f"/api/v1/market-charts/underlyings/{uuid4()}?as_of=2026-10-01").status_code == 404
    )
    assert http.get("/api/v1/market-charts/catalog?as_of=2099-01-01").status_code == 422
