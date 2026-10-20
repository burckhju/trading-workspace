"""HTTP serialization and failures; transaction proof lives in PostgreSQL tests."""

import asyncio
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import DBAPIError
from tests.unit.backend.features.performance.fixtures import SEPTEMBER, WORKSPACE, snapshot

from app.core.exceptions import register_exception_handlers
from app.features.performance.api.router import get_realized_gross_service, router
from app.features.performance.domain.report import ReportLimitExceeded
from app.features.performance.service.application import RealizedGrossReportService
from app.features.performance.service.reader import RealizedGrossSnapshotReader

URL = "/api/v1/performance/realized-gross"
QUERY = {
    "from_date": "2026-09-01",
    "to_date": "2026-09-30",
    "report_currency": "EUR",
    "report_timezone": "Europe/Berlin",
}


def application(reader: AsyncMock) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    register_exception_handlers(app)
    app.dependency_overrides[get_realized_gross_service] = lambda: RealizedGrossReportService(
        reader
    )
    return app


def test_response_transmits_complete_exact_strings_sources_and_definition() -> None:
    reader = AsyncMock(spec=RealizedGrossSnapshotReader)
    reader.read.return_value = snapshot()

    async def exercise() -> None:
        async with AsyncClient(
            transport=ASGITransport(app=application(reader)), base_url="http://test"
        ) as client:
            response = await client.get(URL, params=QUERY)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["filters"] == QUERY
        assert body["interval_start_at"] == "2026-08-31T22:00:00Z"
        assert body["interval_end_at"] == "2026-09-30T22:00:00Z"
        assert body["summary"]["total"] == body["summary"]["total_display"] == "10.00"
        assert len(body["items"]) == 4
        assert len(body["sources"]) == 6
        assert body["items"][2]["realized_gross_pnl_delta"] == "-20.00"
        assert body["items"][2]["cost_basis_before"] == "300.00"
        assert body["items"][2]["executed_at"] is None
        assert body["items"][2]["executed_on"] == "2026-09-12"
        assert body["items"][2]["cost_basis_execution_ids"] == [
            source["execution_id"] for source in body["sources"][:4]
        ]
        assert body["sources"][0]["currency_confirmation"]["currency_code"] == "EUR"
        assert (
            body["sources"][0]["currency_history"][0]["id"]
            == body["sources"][0]["currency_confirmation"]["id"]
        )
        assert body["definition_version"] == "realized-gross-sell-v2"
        assert body["basis"]["knowledge"] == "CURRENT_EFFECTIVE_FACTS"
        assert len(body["basis"]["id"]) == 64
        assert body["currency"] == {
            "code": "EUR",
            "minor_unit": 2,
            "reference_version": "SYNTHETIC-REFERENCE-v1",
            "rounding": "ROUND_HALF_EVEN",
        }

    asyncio.run(exercise())
    reader.read.assert_awaited_once()


@pytest.mark.parametrize(
    "change",
    [
        {"from_date": "invalid"},
        {"from_date": "2026-10-01"},
        {"to_date": "9999-12-31"},
        {"report_timezone": "Imaginary/Zone"},
        {"report_timezone": ""},
        {"report_currency": "eur"},
        {"from_date": "2011-12-30", "to_date": "2011-12-30", "report_timezone": "Pacific/Apia"},
    ],
)
def test_invalid_filters_fail_before_reading_sources(change: dict[str, str]) -> None:
    reader = AsyncMock(spec=RealizedGrossSnapshotReader)

    async def exercise() -> None:
        async with AsyncClient(
            transport=ASGITransport(app=application(reader)), base_url="http://test"
        ) as client:
            response = await client.get(URL, params=QUERY | change)
            assert response.status_code == 422, response.text
            assert "summary" not in response.json()

    asyncio.run(exercise())
    reader.read.assert_not_awaited()


@pytest.mark.parametrize(
    "error,status,code",
    [
        (ValueError("Unknown report currency"), 422, "REPORT_INPUT_INVALID"),
        (ReportLimitExceeded("Complete source limit exceeded"), 413, "REPORT_RESOURCE_LIMIT"),
        (
            DBAPIError("SELECT", {}, Exception("private-database-detail")),
            503,
            "REPORT_READ_UNAVAILABLE",
        ),
    ],
)
def test_report_failures_never_return_truncated_money_or_database_details(
    error: Exception,
    status: int,
    code: str,
) -> None:
    reader = AsyncMock(spec=RealizedGrossSnapshotReader)
    reader.read.side_effect = error

    async def exercise() -> None:
        async with AsyncClient(
            transport=ASGITransport(app=application(reader)), base_url="http://test"
        ) as client:
            response = await client.get(URL, params=QUERY)
        assert response.status_code == status
        assert response.json()["code"] == code
        assert "summary" not in response.json()
        assert "private-database-detail" not in response.text

    asyncio.run(exercise())


def test_service_uses_only_one_snapshot_and_validates_first() -> None:
    reader = AsyncMock(spec=RealizedGrossSnapshotReader)
    reader.read.return_value = snapshot()
    report = asyncio.run(RealizedGrossReportService(reader).report(WORKSPACE, SEPTEMBER))
    assert report.summary.total == "10.00"
    reader.read.assert_awaited_once_with(WORKSPACE, "EUR")
