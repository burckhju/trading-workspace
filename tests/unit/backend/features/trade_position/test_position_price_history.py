"""Position charts reuse exact owner facts without valuing or changing a position."""

from dataclasses import asdict, replace
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.unit.backend.features.trade_position.currency_evidence_fixtures import document
from tests.unit.backend.features.trade_position.test_application import FakeUow
from tests.unit.backend.features.trade_position.test_currency_resolution import (
    AT,
    TRADE,
    confirmed,
    execution,
)

from app.database.dependencies import get_database_session
from app.features.market_data.service.quote_history import QuoteHistoryReader
from app.features.market_data.service.warrant_price_history import (
    HistoricalPricePoint,
    HistoricalPriceSeries,
    WarrantPriceHistory,
)
from app.features.trade_position.api.dependencies import get_trade_position_service
from app.features.trade_position.api.router import WORKSPACE_ID, router
from app.features.trade_position.domain.currency import ExecutionCurrencyResolution
from app.features.trade_position.domain.models import Position
from app.features.trade_position.service.application import TradePositionService
from app.features.trade_position.service.price_history import compose_price_history

POSITION = Position.from_execution(id=UUID(int=5500), trade=TRADE, execution=execution(10))
END = AT + timedelta(days=75)


def history(*, currency="EUR", series=True, **kwargs):
    values = dict(
        warrant_id=TRADE.product_id,
        isin="DE000VH2LU21",
        window_start=None,
        window_end=END,
        collection_started_at=AT + timedelta(days=20),
        samples_considered=1,
        samples_available=1,
        truncated=False,
        excluded={},
        series=(
            (
                HistoricalPriceSeries(
                    id="historical-source",
                    provider="FRANKFURT_QUOTES",
                    identity_key="a" * 64,
                    warrant_listing_id=UUID(int=6000),
                    isin="DE000VH2LU21",
                    currency=currency,
                    price_kind="BID",
                    source_mode="OFFICIAL_WEBSITE",
                    provider_exchange_code="XSC",
                    venue_mic="XFRA",
                    points=(
                        HistoricalPricePoint(
                            id="source-point",
                            observed_at=AT + timedelta(days=20),
                            price=Decimal("2.25"),
                            captured_at=AT + timedelta(days=21),
                            retrieved_at=AT + timedelta(days=21),
                            status="STALE",
                            storage="SAMPLE",
                            quote_time_basis=None,
                        ),
                    ),
                ),
            )
            if series
            else ()
        ),
    )
    values.update(kwargs)
    return WarrantPriceHistory(**values)


def service_context(facts, *, trade=TRADE, position=POSITION, confirmations=(), evidence=()):
    uow = FakeUow()
    read_only = SimpleNamespace(get=AsyncMock(return_value=trade))
    uow.trades.get.side_effect = AssertionError("History must not acquire a command lock")
    uow.positions.get_for_trade.return_value = position
    uow.executions.list_for_trade = AsyncMock(return_value=list(facts))
    declarations = SimpleNamespace(
        current_for_trade=AsyncMock(
            return_value={item.execution_id: item for item in confirmations}
        ),
        capture=AsyncMock(),
    )
    sources = SimpleNamespace(list_for_product=AsyncMock(return_value=tuple(evidence)))
    selection = SimpleNamespace(resolve=AsyncMock())
    quotes = SimpleNamespace(select_once=AsyncMock())
    service = TradePositionService(
        uow=uow,
        workspace_selections=selection,
        quote_source_selector=quotes,
        currency_confirmations=declarations,
        currency_evidence=sources,
        trade_reader=read_only,
    )
    return service, uow, declarations, sources, selection, quotes, read_only


@pytest.mark.asyncio
async def test_effective_corrected_executions_use_existing_currency_resolver_without_writes():
    old = execution(10)
    first_correction = replace(old, id=UUID(int=100), supersedes_execution_id=old.id)
    correction = replace(
        first_correction,
        id=UUID(int=101),
        supersedes_execution_id=first_correction.id,
        executed_at=old.executed_at + timedelta(days=1),
        price_per_unit=Decimal("2.2"),
    )
    sale = execution(15, "SELL")
    facts = (old, first_correction, correction, sale)
    original = tuple(asdict(fact) for fact in facts)
    service, uow, declarations, sources, selection, quotes, read_only = service_context(
        facts, confirmations=(confirmed(old),)
    )
    position, effective = await service.get_price_history_context(
        workspace_id=TRADE.workspace_id, trade_id=TRADE.id
    )
    assert position == POSITION
    assert [fact.id for fact in effective] == [correction.id, sale.id]
    assert effective[0].price_per_unit == Decimal("2.2")
    assert effective[0].executed_at == correction.executed_at
    assert effective[0].currency_resolution.source == "REPLACED_EXECUTION"
    assert effective[1].currency_resolution.source == "PRIOR_BUYS"
    assert [fact.currency_resolution.currency_code for fact in effective] == ["EUR", "EUR"]
    chart = compose_price_history(position, effective, history())
    assert [event.id for event in chart.events] == [correction.id, sale.id]
    assert all(event.plottable for event in chart.events)
    assert tuple(asdict(fact) for fact in facts) == original
    read_only.get.assert_awaited_once_with(TRADE.workspace_id, TRADE.id)
    uow.trades.get.assert_not_awaited()
    uow.positions.get_for_trade.assert_awaited_once_with(TRADE.workspace_id, TRADE.id)
    uow.executions.list_for_trade.assert_awaited_once_with(TRADE.id)
    uow.executions.list_effective_for_trade.assert_not_awaited()
    declarations.current_for_trade.assert_awaited_once_with(TRADE.workspace_id, TRADE.id)
    sources.list_for_product.assert_awaited_once_with(TRADE.workspace_id, TRADE.product_id)
    for mutation in (
        uow.commit,
        uow.flush,
        uow.positions.replace,
        uow.positions.add,
        uow.executions.add,
        uow.trades.add,
        declarations.capture,
        selection.resolve,
        quotes.select_once,
    ):
        mutation.assert_not_awaited()


@pytest.mark.asyncio
async def test_historical_document_currency_is_reused_and_unproven_currency_stays_unknown():
    buy, sale = execution(10), execution(11, "SELL")
    source = document(TRADE, buy.id, code="USD")
    service, *_ = service_context((buy, sale), evidence=(source,))
    position, facts = await service.get_price_history_context(
        workspace_id=TRADE.workspace_id, trade_id=TRADE.id
    )
    assert facts[0].currency_resolution.source == "EXECUTION_DOCUMENT"
    assert facts[0].currency_resolution.evidence_ids == (source.id,)
    assert facts[0].currency_resolution.currency_code == "USD"
    chart = compose_price_history(position, facts, history(currency="USD"))
    assert chart.events[0].plottable is True
    assert chart.events[0].currency_source == "EXECUTION_DOCUMENT"
    assert chart.events[1].plottable is False
    assert chart.events[1].reason == "CURRENCY_UNKNOWN"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case", ["missing_trade", "cancelled", "missing_position", "wrong_product", "wrong_fact"]
)
async def test_context_refuses_missing_cancelled_and_unrelated_owners(case):
    trade, position = TRADE, POSITION
    fact = execution(10)
    expected = "position history identity mismatch"
    if case == "missing_trade":
        trade, expected = None, "trade not found"
    elif case == "cancelled":
        trade = replace(TRADE, cancelled_at=END)
        expected = "trade not found"
    elif case == "missing_position":
        position, expected = None, "position not found"
    elif case == "wrong_product":
        position = replace(POSITION, product_id=uuid4())
    else:
        fact = replace(fact, trade_id=uuid4())
    service, uow, declarations, *_ = service_context((fact,), trade=trade, position=position)
    with pytest.raises(ValueError, match=expected):
        await service.get_price_history_context(workspace_id=TRADE.workspace_id, trade_id=TRADE.id)
    uow.commit.assert_not_awaited()
    declarations.current_for_trade.assert_not_awaited()


def test_date_only_execution_stays_a_calendar_date_through_dst_without_midnight_marker():
    zone = ZoneInfo("Europe/Berlin")
    day = date(2026, 10, 25)  # Twenty-five-hour local day.
    date_only = replace(
        execution(10),
        executed_on=day,
        execution_timezone="Europe/Berlin",
        executed_at=datetime.combine(day, time.min, tzinfo=zone).astimezone(UTC),
        recorded_at=datetime(2026, 10, 27, tzinfo=UTC),
        currency_resolution=ExecutionCurrencyResolution("EUR", "USER_CONFIRMED"),
    )
    result = compose_price_history(
        POSITION,
        (date_only,),
        history(
            window_start=datetime(2026, 10, 25, 8, tzinfo=UTC),
            window_end=datetime(2026, 10, 25, 22, tzinfo=UTC),
        ),
    )
    assert len(result.events) == 1
    event = result.events[0]
    assert event.executed_on == day
    assert event.execution_timezone == "Europe/Berlin"
    assert event.occurred_at is None
    assert event.currency == "EUR" and event.reason == "DATE_ONLY"
    assert event.plottable is False


@pytest.mark.parametrize("source", ["UNKNOWN", "MIXED", "CONFLICT"])
def test_unknown_execution_currency_is_not_assumed_from_quote_currency(source):
    fact = replace(execution(10), currency_resolution=ExecutionCurrencyResolution(None, source))
    result = compose_price_history(POSITION, (fact,), history())
    assert result.events[0].currency is None
    assert result.events[0].reason == "CURRENCY_UNKNOWN"
    assert result.events[0].plottable is False
    assert result.series == history().series


@pytest.mark.parametrize("with_quotes", [True, False])
def test_proven_foreign_currency_and_missing_quotes_do_not_get_converted(with_quotes):
    fact = replace(
        execution(10), currency_resolution=ExecutionCurrencyResolution("USD", "USER_CONFIRMED")
    )
    result = compose_price_history(POSITION, (fact,), history(series=with_quotes))
    event = result.events[0]
    assert event.price == fact.price_per_unit
    assert event.currency == "USD" and event.currency_source == "USER_CONFIRMED"
    assert event.reason == "NO_MATCHING_QUOTE_CURRENCY" and event.plottable is False


def test_time_window_excludes_old_and_future_executions_without_changing_price_evidence():
    facts = (execution(9), execution(10), execution(11, "SELL"), execution(12))
    evidence = history(window_start=AT + timedelta(days=10), window_end=AT + timedelta(days=11))
    result = compose_price_history(POSITION, facts, evidence)
    assert [item.id for item in result.events] == [facts[1].id, facts[2].id]
    assert result.series == evidence.series


@pytest.mark.parametrize("offset", [-1, 1])
def test_calendar_execution_outside_requested_local_day_is_excluded(offset):
    zone = ZoneInfo("Europe/Berlin")
    day = date(2026, 10, 25) + timedelta(days=offset)
    fact = replace(
        execution(10),
        executed_on=day,
        execution_timezone="Europe/Berlin",
        executed_at=datetime.combine(day, time.min, tzinfo=zone).astimezone(UTC),
        recorded_at=datetime(2026, 10, 27, tzinfo=UTC),
    )
    result = compose_price_history(
        POSITION,
        (fact,),
        history(
            window_start=datetime(2026, 10, 25, 7, tzinfo=UTC),
            window_end=datetime(2026, 10, 25, 20, tzinfo=UTC),
        ),
    )
    assert result.events == ()


@pytest.mark.parametrize("wrong", ["product", "execution_product", "execution_trade"])
def test_chart_never_combines_facts_from_different_positions_or_products(wrong):
    evidence, fact = history(), execution(10)
    if wrong == "product":
        evidence = replace(evidence, warrant_id=uuid4())
    elif wrong == "execution_product":
        fact = replace(fact, product_id=uuid4())
    else:
        fact = replace(fact, trade_id=uuid4())
    with pytest.raises(ValueError, match="identity mismatch"):
        compose_price_history(POSITION, (fact,), evidence)


def client_for(service, session):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_trade_position_service] = lambda: service
    app.dependency_overrides[get_database_session] = lambda: session
    return TestClient(app, raise_server_exceptions=False)


def test_registered_get_autoloads_all_available_with_decimal_strings_and_original_times(
    monkeypatch,
):
    fact = replace(
        execution(10), currency_resolution=ExecutionCurrencyResolution("EUR", "USER_CONFIRMED")
    )
    service = SimpleNamespace(get_price_history_context=AsyncMock(return_value=(POSITION, (fact,))))
    session = AsyncMock(spec=AsyncSession)
    reader = AsyncMock(return_value=history())
    monkeypatch.setattr(QuoteHistoryReader, "prices", reader)
    with client_for(service, session) as client:
        response = client.get(f"/api/v1/trade-position/trades/{TRADE.id}/price-history")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["trade_id"] == str(TRADE.id) and body["position_id"] == str(POSITION.id)
    assert body["window_start"] is None
    assert body["series"][0]["points"][0]["price"] == "2.25"
    assert body["series"][0]["provider_exchange_code"] == "XSC"
    assert body["series"][0]["venue_mic"] == "XFRA"
    assert body["series"][0]["points"][0]["observed_at"].startswith("2026-08-21T00:00:00")
    assert body["events"][0]["plottable"] is True
    assert body["events"][0]["price"] == "2"
    service.get_price_history_context.assert_awaited_once_with(
        workspace_id=WORKSPACE_ID, trade_id=TRADE.id
    )
    assert reader.await_args.args == (WORKSPACE_ID, TRADE.product_id)
    assert reader.await_args.kwargs["days"] is None
    assert [str(call.args[0]) for call in session.execute.await_args_list] == [
        "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY",
        "SET LOCAL statement_timeout = '10000ms'",
    ]
    assert reader.await_args.kwargs["now"].utcoffset() == timedelta(0)


@pytest.mark.parametrize("days", [1, 7, 31, 366])
def test_get_accepts_bounded_optional_range(monkeypatch, days):
    service = SimpleNamespace(get_price_history_context=AsyncMock(return_value=(POSITION, ())))
    reader = AsyncMock(return_value=history())
    monkeypatch.setattr(QuoteHistoryReader, "prices", reader)
    with client_for(service, AsyncMock(spec=AsyncSession)) as client:
        response = client.get(f"/api/v1/trade-position/trades/{TRADE.id}/price-history?days={days}")
    assert response.status_code == 200
    assert reader.await_args.kwargs["days"] == days


@pytest.mark.parametrize("days", ["0", "367", "nope", "-1"])
def test_invalid_range_is_not_misreported_as_no_data(monkeypatch, days):
    service = SimpleNamespace(get_price_history_context=AsyncMock())
    reader = AsyncMock()
    monkeypatch.setattr(QuoteHistoryReader, "prices", reader)
    with client_for(service, AsyncMock(spec=AsyncSession)) as client:
        response = client.get(f"/api/v1/trade-position/trades/{TRADE.id}/price-history?days={days}")
    assert response.status_code == 422
    service.get_price_history_context.assert_not_awaited()
    reader.assert_not_awaited()


@pytest.mark.parametrize(
    "message,status",
    [
        ("trade not found", 404),
        ("position not found", 404),
        ("position history identity mismatch", 409),
    ],
)
def test_context_failure_does_not_query_unrelated_market_evidence(monkeypatch, message, status):
    service = SimpleNamespace(get_price_history_context=AsyncMock(side_effect=ValueError(message)))
    reader = AsyncMock()
    monkeypatch.setattr(QuoteHistoryReader, "prices", reader)
    with client_for(service, AsyncMock(spec=AsyncSession)) as client:
        response = client.get(f"/api/v1/trade-position/trades/{TRADE.id}/price-history")
    assert response.status_code == status
    reader.assert_not_awaited()


def test_missing_product_is_404_and_storage_failure_is_not_an_empty_success(monkeypatch):
    service = SimpleNamespace(get_price_history_context=AsyncMock(return_value=(POSITION, ())))
    reader = AsyncMock(return_value=None)
    monkeypatch.setattr(QuoteHistoryReader, "prices", reader)
    with client_for(service, AsyncMock(spec=AsyncSession)) as client:
        url = f"/api/v1/trade-position/trades/{TRADE.id}/price-history"
        assert client.get(url).status_code == 404
        reader.side_effect = RuntimeError("database unavailable")
        assert client.get(url).status_code == 500


@pytest.mark.asyncio
async def test_history_context_without_explicit_read_only_reader_fails_closed():
    uow = FakeUow()
    service = TradePositionService(
        uow=uow, workspace_selections=SimpleNamespace(resolve=AsyncMock())
    )
    with pytest.raises(ValueError, match="read"):
        await service.get_price_history_context(workspace_id=TRADE.workspace_id, trade_id=TRADE.id)
    uow.trades.get.assert_not_awaited()
    uow.positions.get_for_trade.assert_not_awaited()
    uow.commit.assert_not_awaited()
