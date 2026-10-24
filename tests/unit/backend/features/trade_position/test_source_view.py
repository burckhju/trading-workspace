"""HTTP and read boundaries. These tests do not claim PostgreSQL qualification."""

import asyncio
from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ApplicationError, register_exception_handlers
from app.features.post_trade.application.read_adapters import (
    SqlAlchemyHistoricalPlanningContextReader,
    SqlAlchemyHistoricalProductContextReader,
    SqlAlchemyTradeExitContextReader,
)
from app.features.trade_position.api.source_router import WORKSPACE_ID, get_source_reader, router
from app.features.trade_position.domain.enums import ExecutionSide, TradeOrigin
from app.features.trade_position.domain.models import Trade
from app.features.trade_position.domain.timeline import TradeTimelineEntry, TradeTimelineEntryKind
from app.features.trade_position.persistence.models import TradeModel
from app.features.trade_position.persistence.repositories import (
    SqlAlchemyReadOnlyTradeRepository,
    SqlAlchemyTradeRepository,
)
from app.features.trade_position.service.source_view import (
    JournalSources,
    ReviewSources,
    SourceSnapshot,
    TradeSourceCore,
    TradeSourceReader,
    select_version,
    source_error,
)

TRADE = uuid4()
NOW = datetime(2026, 10, 21, 12, tzinfo=UTC)
BASE = f"/api/v1/trade-position/trades/{TRADE}/sources"
SECTIONS = [
    ("", "core"),
    ("/plan", "plan"),
    ("/reviews", "reviews"),
    ("/journal", "journal"),
    ("/evidence", "evidence"),
]


def application(reader):
    app = FastAPI()
    app.include_router(router)
    register_exception_handlers(app)
    app.dependency_overrides[get_source_reader] = lambda: reader
    return app


def read(reader, path=BASE, method="GET"):
    async def exercise():
        async with AsyncClient(
            transport=ASGITransport(app=application(reader)), base_url="http://test"
        ) as client:
            return await client.request(method, path)

    return asyncio.run(exercise())


def test_core_serialization_preserves_decimal_and_date_precision_without_money_total():
    reader = AsyncMock(spec=TradeSourceReader)
    trade = Trade(TRADE, WORKSPACE_ID, uuid4(), TradeOrigin.EXTERNAL, NOW, uuid4())
    entry = TradeTimelineEntry(
        id=uuid4(),
        trade_id=TRADE,
        occurred_at=datetime(2026, 8, 4, 22, tzinfo=UTC),
        recorded_at=NOW,
        kind=TradeTimelineEntryKind.EXECUTION,
        execution_side=ExecutionSide.BUY,
        quantity=100,
        price_per_unit=Decimal("2.0000000001"),
        executed_on=date(2026, 8, 5),
        execution_timezone="Europe/Berlin",
    )
    reader.core.return_value = SourceSnapshot(
        TradeSourceCore(trade, "Synthetic", "OPEN", 100, (entry,), ()), NOW, NOW
    )
    response = read(reader)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["data"]["trade"]["id"] == str(TRADE)
    assert body["data"]["timeline"][0]["price_per_unit"] == "2.0000000001"
    assert body["data"]["timeline"][0]["executed_on"] == "2026-08-05"
    assert "realized_gross_pnl" not in response.text
    assert "total" not in body["data"]
    assert body["read_started_at"] == body["read_completed_at"] == "2026-10-21T12:00:00Z"
    reader.core.assert_awaited_once_with(WORKSPACE_ID, TRADE)


@pytest.mark.parametrize("suffix,method", SECTIONS)
def test_database_errors_are_not_empty_sources_and_do_not_leak_private_details(suffix, method):
    reader = AsyncMock(spec=TradeSourceReader)
    getattr(reader, method).side_effect = DBAPIError("PRIVATE SQL", {}, Exception("private-token"))
    response = read(reader, BASE + suffix)
    assert response.status_code == 503
    assert response.json()["code"] == "SOURCE_READ_UNAVAILABLE"
    assert "private-token" not in response.text and "PRIVATE SQL" not in response.text
    assert "data" not in response.json()


@pytest.mark.parametrize("suffix,method", SECTIONS)
def test_unknown_or_foreign_trade_remains_a_blocking_error(suffix, method):
    reader = AsyncMock(spec=TradeSourceReader)
    getattr(reader, method).side_effect = source_error(
        "TRADE_NOT_FOUND", "Trade nicht gefunden.", 404
    )
    response = read(reader, BASE + suffix)
    assert response.status_code == 404
    assert response.json()["code"] == "TRADE_NOT_FOUND"


@pytest.mark.parametrize("suffix,method", SECTIONS)
def test_get_only_endpoints_do_not_offer_commands(suffix, method):
    reader = AsyncMock(spec=TradeSourceReader)
    assert read(reader, BASE + suffix, "POST").status_code == 405
    getattr(reader, method).assert_not_awaited()


@pytest.mark.parametrize("suffix,method", [("/reviews", "reviews"), ("/journal", "journal")])
def test_explicit_pin_is_forwarded_exactly_and_never_silently_replaced(suffix, method):
    reader = AsyncMock(spec=TradeSourceReader)
    pin = uuid4()
    getattr(reader, method).side_effect = source_error("SOURCE_VERSION_NOT_FOUND", "Unbekannt", 404)
    response = read(reader, BASE + suffix + f"?version_id={pin}")
    assert response.status_code == 404
    getattr(reader, method).assert_awaited_once_with(WORKSPACE_ID, TRADE, pin)


@pytest.mark.parametrize("section", ["reviews", "journal"])
def test_duplicate_pin_rejected_before_read(section):
    reader = AsyncMock(spec=TradeSourceReader)
    response = read(reader, f"{BASE}/{section}?version_id={uuid4()}&version_id={uuid4()}")
    assert response.status_code == 422
    assert response.json()["code"] == "SOURCE_VERSION_INVALID"
    assert not reader.mock_calls


@pytest.mark.parametrize(
    "path",
    [
        BASE.replace(str(TRADE), "invalid"),
        BASE + "/reviews?version_id=bad",
        BASE + "/journal?version_id=",
    ],
)
def test_bad_uuid_rejected_before_source_reads(path):
    reader = AsyncMock(spec=TradeSourceReader)
    assert read(reader, path).status_code == 422
    assert not reader.mock_calls


def test_empty_optional_contracts_are_distinct_successful_snapshots():
    reader = AsyncMock(spec=TradeSourceReader)
    reader.plan.return_value = SourceSnapshot(None, NOW, NOW)
    reader.reviews.return_value = SourceSnapshot(ReviewSources((), None, "UNKNOWN", NOW), NOW, NOW)
    reader.journal.return_value = SourceSnapshot(JournalSources((), None, "UNKNOWN", NOW), NOW, NOW)
    reader.evidence.return_value = SourceSnapshot((), NOW, NOW)
    assert read(reader, BASE + "/plan").json()["data"] is None
    for section in ("reviews", "journal"):
        result = read(reader, BASE + "/" + section)
        assert result.status_code == 200
        assert result.json()["data"]["history"] == []
        assert result.json()["data"]["selected"] is None
        assert result.json()["data"]["source_currentness"] == "UNKNOWN"
    assert read(reader, BASE + "/evidence").json()["data"] == []


def test_exact_selection_and_empty_history_do_not_fallback():
    old, new, foreign = uuid4(), uuid4(), uuid4()
    assert select_version((new, old), None, lambda v: v) == new
    assert select_version((new, old), old, lambda v: v) == old
    assert select_version((), None, lambda v: v) is None
    for values in ((), (new, old)):
        with pytest.raises(ApplicationError) as error:
            select_version(values, foreign, lambda v: v)
        assert error.value.code == "SOURCE_VERSION_NOT_FOUND"


@pytest.mark.parametrize("size,exceeded", [(0, False), (3, False), (4, True)])
def test_complete_read_boundary_probes_one_extra_and_rejects_truncation(size, exceeded):
    session = AsyncMock(spec=AsyncSession)
    result = Mock()
    result.all.return_value = [uuid4() for _ in range(size)]
    session.scalars.return_value = result

    async def exercise():
        await TradeSourceReader._bounded(session, select(TradeModel.id), 3)

    if exceeded:
        with pytest.raises(ApplicationError) as error:
            asyncio.run(exercise())
        assert error.value.code == "SOURCE_RESOURCE_LIMIT"
        assert error.value.status_code == 413
    else:
        asyncio.run(exercise())
    statement = session.scalars.await_args.args[0]
    assert statement.compile().params["param_1"] == 4


@pytest.mark.parametrize(
    "repository,locked",
    [(SqlAlchemyTradeRepository, True), (SqlAlchemyReadOnlyTradeRepository, False)],
)
def test_command_lock_is_preserved_and_source_query_has_no_lock(repository, locked):
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = None
    assert asyncio.run(repository(session).get(WORKSPACE_ID, TRADE)) is None
    statement = session.scalar.await_args.args[0]
    sql = str(statement.compile(dialect=postgresql.dialect()))
    assert ("FOR UPDATE" in sql) == locked
    assert statement.compile().params == {"workspace_id_1": WORKSPACE_ID, "id_1": TRADE}


@pytest.mark.parametrize(
    "adapter",
    [
        SqlAlchemyTradeExitContextReader,
        SqlAlchemyHistoricalPlanningContextReader,
        SqlAlchemyHistoricalProductContextReader,
    ],
)
def test_optional_inspector_uses_injected_read_port_instead_of_locking_trade_repository(adapter):
    session = AsyncMock(spec=AsyncSession)
    trades = AsyncMock(spec=SqlAlchemyReadOnlyTradeRepository)
    trades.get.return_value = None
    asyncio.run(adapter(session, trades=trades).get(workspace_id=WORKSPACE_ID, trade_id=TRADE))
    trades.get.assert_awaited_once_with(WORKSPACE_ID, TRADE)
    session.scalar.assert_not_awaited()
