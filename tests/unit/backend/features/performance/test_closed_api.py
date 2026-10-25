"""New GET response, exact monetary strings and complete-source error contract."""

import asyncio
from dataclasses import replace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import DBAPIError
from tests.unit.backend.features.performance.fixtures import (
    WORKSPACE,
    closed_statistics_snapshot,
    confirmed,
    reference,
    snapshot,
)
from tests.unit.backend.features.performance.test_closed_report import OCTOBER

from app.core.exceptions import register_exception_handlers
from app.features.performance.api.router import (
    WORKSPACE_ID,
    get_closed_trade_service,
    get_realized_gross_service,
    router,
)
from app.features.performance.domain.report import ReportLimitExceeded
from app.features.performance.service.application import (
    ClosedTradeReportService,
    RealizedGrossReportService,
)
from app.features.performance.service.reader import RealizedGrossSnapshotReader

URL = "/api/v1/performance/closed-trades"
QUERY = {
    "from_date": "2026-10-01",
    "to_date": "2026-10-31",
    "report_currency": "EUR",
    "report_timezone": "Europe/Berlin",
}


def application(reader: AsyncMock) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    register_exception_handlers(app)
    app.dependency_overrides[get_closed_trade_service] = lambda: ClosedTradeReportService(reader)
    app.dependency_overrides[get_realized_gross_service] = lambda: RealizedGrossReportService(
        reader
    )
    return app


def test_response_is_one_full_trade_with_exact_owner_total_and_all_lifetime_sources() -> None:
    reader = AsyncMock(spec=RealizedGrossSnapshotReader)
    facts = reference()
    reader.read.return_value = snapshot(confirmations=(confirmed(facts[0]),))

    async def exercise() -> None:
        async with AsyncClient(
            transport=ASGITransport(app=application(reader)), base_url="http://test"
        ) as client:
            response = await client.get(URL, params=QUERY)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["definition_version"] == "closed-trade-gross-v1"
        assert body["filters"] == QUERY
        assert body["interval_start_at"] == "2026-09-30T22:00:00Z"
        assert body["interval_end_at"] == "2026-10-31T23:00:00Z"
        assert body["summary"]["total"] == body["summary"]["total_display"] == "50.00"
        assert body["summary"]["subtotal"] is None
        assert (
            body["counts"]["examined"]
            == body["counts"]["qualified"]
            == body["counts"]["positive"]
            == 1
        )
        assert len(body["items"]) == 1
        item = body["items"][0]
        assert item["group"] == "QUALIFIED"
        assert item["classification"] == "POSITIVE"
        assert item["realized_gross_pnl"] == "50.00"
        assert item["closing_execution_id"] == str(facts[-1].id)
        assert item["closing_time"]["executed_at"] is None
        assert item["closing_time"]["executed_on"] == "2026-10-03"
        assert item["closing_time"]["time_precision"] == "DATE_ONLY"
        assert (
            item["execution_ids"]
            == item["effective_execution_ids"]
            == [str(fact.id) for fact in facts]
        )
        assert item["currency_confirmation_ids"] == [str(confirmed(facts[0]).id)]
        assert [part["realized_gross_pnl_delta"] for part in item["sell_contributions"]] == [
            "10.00",
            "30.00",
            "-20.00",
            "30.00",
        ]
        assert [part["period_status"] for part in item["sell_contributions"]] == [
            "OUTSIDE_PERIOD"
        ] * 3 + ["IN_PERIOD"]
        assert item["sell_contributions"][-1]["cost_basis_before"] == "180.00"
        assert len(body["sources"]) == 6
        assert body["sources"][0]["currency_history"][0]["id"] == str(confirmed(facts[0]).id)
        assert body["sources"][-1]["currency_resolution"]["source"] == "PRIOR_BUYS"
        assert body["sources"][-1]["currency_confirmation"] is None
        assert body["basis"]["knowledge"] == "CURRENT_EFFECTIVE_FACTS"
        assert len(body["basis"]["id"]) == 64
        assert body["currency"]["rounding"] == "ROUND_HALF_EVEN"
        assert body["statistics"] == {
            "definition_version": "closed-trade-statistics-v1",
            "report_basis_id": body["basis"]["id"],
            "report_status": "COMPLETE",
            "population": 1,
            "win_rate": {"raw": "100", "display": "100.00", "reason": None},
            "average_gross_pnl": {"raw": "50.00", "display": "50.00", "reason": None},
            "median_gross_pnl": {"raw": "50.00", "display": "50.00", "reason": None},
            "gross_profit_factor": {
                "raw": None,
                "display": None,
                "reason": "Nicht definiert: keine Verlusttrades",
            },
        }

    asyncio.run(exercise())
    reader.read.assert_awaited_once_with(WORKSPACE_ID, "EUR")


def test_existing_sell_response_remains_separate_on_the_same_router() -> None:
    reader = AsyncMock(spec=RealizedGrossSnapshotReader)
    reader.read.return_value = snapshot()

    async def exercise() -> None:
        async with AsyncClient(
            transport=ASGITransport(app=application(reader)), base_url="http://test"
        ) as client:
            closed = await client.get(URL, params=QUERY)
            sells = await client.get("/api/v1/performance/realized-gross", params=QUERY)
            forbidden_write = await client.post(URL, json={})
        assert closed.json()["summary"]["total"] == "50.00"
        assert sells.status_code == 200
        assert sells.json()["definition_version"] == "realized-gross-sell-v2"
        assert sells.json()["summary"]["total"] == "30.00"
        assert len(sells.json()["items"]) == 4
        assert "statistics" not in sells.json()
        assert forbidden_write.status_code == 405

    asyncio.run(exercise())
    assert reader.read.await_count == 2


@pytest.mark.parametrize(
    "change",
    [
        {"from_date": "invalid"},
        {"from_date": "2026-11-01"},
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
def test_read_failures_never_return_truncated_money_or_database_details(
    error: Exception, status: int, code: str
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


def test_service_materializes_one_reader_snapshot_only() -> None:
    reader = AsyncMock(spec=RealizedGrossSnapshotReader)
    reader.read.return_value = snapshot()
    report = asyncio.run(ClosedTradeReportService(reader).report(WORKSPACE, OCTOBER))
    assert report.summary.total == "50.00"
    assert report.statistics.report_basis_id == report.basis.id
    assert report.statistics.population == 1
    assert report.statistics.average_gross_pnl.raw == "50.00"
    reader.read.assert_awaited_once_with(WORKSPACE, "EUR")


@pytest.mark.parametrize("status", ["COMPLETE", "PARTIAL", "NOT_COMPUTABLE", "EMPTY"])
def test_additive_statistics_contract_serializes_strings_or_explicit_unavailable_reasons(
    status: str,
) -> None:
    reader = AsyncMock(spec=RealizedGrossSnapshotReader)
    basis = closed_statistics_snapshot()
    query = QUERY.copy()
    if status == "PARTIAL":
        basis = replace(basis, confirmations=basis.confirmations[:1])
    elif status == "NOT_COMPUTABLE":
        basis = replace(basis, confirmations=())
    elif status == "EMPTY":
        query.update(from_date="2026-09-01", to_date="2026-09-30")
    reader.read.return_value = basis

    async def exercise() -> None:
        async with AsyncClient(
            transport=ASGITransport(app=application(reader)), base_url="http://test"
        ) as client:
            response = await client.get(URL, params=query)
        assert response.status_code == 200, response.text
        body = response.json()
        stats = body["statistics"]
        assert body["definition_version"] == "closed-trade-gross-v1"
        assert stats["definition_version"] == "closed-trade-statistics-v1"
        assert stats["report_basis_id"] == body["basis"]["id"]
        assert stats["report_status"] == body["summary"]["status"] == status
        names = ("win_rate", "average_gross_pnl", "median_gross_pnl", "gross_profit_factor")
        if status == "COMPLETE":
            assert stats["population"] == 4
            assert body["summary"]["total"] == "250"
            for name, raw, display in zip(
                names, ("50.0", "62.5", "50", "6"), ("50.00", "62.50", "50.00", "6.00"), strict=True
            ):
                assert stats[name] == {"raw": raw, "display": display, "reason": None}
        else:
            assert stats["population"] == (0 if status == "EMPTY" else None)
            reason = (
                "Keine abgeschlossenen Trades in der Auswahl"
                if status == "EMPTY"
                else "Berichtsgrundlage unvollständig"
            )
            for name in names:
                assert stats[name] == {"raw": None, "display": None, "reason": reason}
            if status == "PARTIAL":
                assert body["summary"]["subtotal"] == "100"
                assert body["counts"]["positive"] == body["counts"]["qualified"] == 1
            elif status == "EMPTY":
                assert body["summary"]["total"] == "0"

    asyncio.run(exercise())
    reader.read.assert_awaited_once_with(WORKSPACE_ID, "EUR")
