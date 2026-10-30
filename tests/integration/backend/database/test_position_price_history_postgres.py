"""Real owner captures and chart GETs over migrated, disposable PostgreSQL.

Economic facts are written only through registered owner APIs. Synthetic stored
quotes stand in for previously captured evidence; all outbound HTTP is forbidden.
"""

import asyncio
from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import event, text
from tests.integration.backend.learning.test_journal_write_postgres import (
    journal_database as guarded_database,
)
from tests.integration.backend.test_execution_currency_reuse_postgres import _book, _payload, _post
from tests.integration.backend.test_realized_gross_report_postgres import (
    DECLARATION,
    _client,
    _state,
)
from tests.integration.backend.test_trade_capture_safety import BASE, WORKSPACE
from tests.integration.backend.test_usd_chf_currency_references import _migrate, _product_payload

from app.features.market_data.domain.enums import (
    CacheStatus,
    MarketDataCapability,
    MarketDataProvider,
    QualityStatus,
)
from app.features.market_data.domain.models import WarrantQuoteSnapshot
from app.features.market_data.persistence.models import (
    WarrantQuoteObservationModel,
    WarrantQuoteSampleModel,
)
from app.features.market_data.service.quote_history import QUOTE, QuoteHistoryReader
from app.features.market_data.service.types import MarketDataResult
from app.features.market_data.service.warrant_price_history import RESULT

SOURCE_AT = datetime(2026, 9, 1, 10, tzinfo=UTC)
CAPTURE_AT = datetime(2026, 10, 1, 10, tzinfo=UTC)
ISIN = "DE000VH2LU21"


@pytest.fixture
def history_database() -> Iterator[str]:
    yield from guarded_database.__wrapped__()


@pytest.fixture(autouse=True)
def forbid_external_calls(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    async_transport = AsyncMock(side_effect=AssertionError("History must not call external HTTP"))
    sync_transport = Mock(side_effect=AssertionError("History must not call external HTTP"))
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", async_transport)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", sync_transport)
    yield
    async_transport.assert_not_awaited()
    sync_transport.assert_not_called()


async def seed_stored_evidence(database, product_id, listing_id, *, sampled):
    quote = WarrantQuoteSnapshot(
        warrant_listing_id=UUID(listing_id),
        bid=None,
        ask=None,
        currency="EUR",
        provider_symbol=ISIN,
        provider_exchange_code="XETR",
        observed_at=SOURCE_AT,
        isin=ISIN,
        reference_price=Decimal("0.231"),
        reference_price_type="LAST_TRADE",
        source_mode="OFFICIAL_WEBSITE_LAST_TRADE",
        venue_mic="XETR",
    )
    result = MarketDataResult(
        data=quote,
        provider=MarketDataProvider.FRANKFURT_QUOTES,
        capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
        correlation_id=uuid4(),
        retrieved_at=CAPTURE_AT,
        cache_status=CacheStatus.MISS,
        quality_status=QualityStatus.VALID,
        warnings=(),
        retry_count=0,
        provider_call_cost=0,
    )
    async with database.session_context() as session:
        session.add(
            WarrantQuoteObservationModel(
                workspace_id=UUID(WORKSPACE),
                warrant_listing_id=UUID(listing_id),
                provider="FRANKFURT_QUOTES",
                identity_key="a" * 64,
                payload=RESULT.dump_python(result, mode="json"),
            )
        )
        if sampled:
            for index, (provider, key, data, status) in enumerate(
                (
                    ("FRANKFURT_QUOTES", "a", quote, "REFERENCE_ONLY"),
                    ("FRANKFURT_QUOTES", "a", quote, "REFERENCE_ONLY"),
                    ("VONTOBEL_MARKETS", "b", replace(quote, currency="USD"), "REFERENCE_ONLY"),
                    (
                        "FRANKFURT_QUOTES",
                        "c",
                        replace(quote, observed_at=None),
                        "TIMESTAMP_UNKNOWN",
                    ),
                )
            ):
                captured = CAPTURE_AT + timedelta(minutes=index * 5)
                session.add(
                    WarrantQuoteSampleModel(
                        id=uuid4(),
                        workspace_id=UUID(WORKSPACE),
                        warrant_id=UUID(product_id),
                        warrant_listing_id=UUID(listing_id),
                        provider=provider,
                        identity_key=key * 64,
                        isin=ISIN,
                        captured_at=captured,
                        slot_at=captured,
                        day_utc=captured.date(),
                        status=status,
                        reason=None,
                        quote_fingerprint=None,
                        payload={
                            "quote": QUOTE.dump_python(data, mode="json"),
                            "retrieved_at": CAPTURE_AT.isoformat(),
                        },
                    )
                )
        await session.commit()


@pytest.mark.parametrize("sampled", [False, True], ids=["legacy-retained-only", "sampled-history"])
def test_registered_history_get_preserves_evidence_and_corrected_position_facts(
    history_database: str, sampled: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    _migrate(history_database, "head")
    actual_prices = QuoteHistoryReader.prices
    snapshots = []

    async def inspected_prices(reader, *args, **kwargs):
        snapshots.append(
            (
                await reader.session.scalar(text("SHOW transaction_isolation")),
                await reader.session.scalar(text("SHOW transaction_read_only")),
            )
        )
        return await actual_prices(reader, *args, **kwargs)

    monkeypatch.setattr(QuoteHistoryReader, "prices", inspected_prices)

    async def exercise():
        async with _client(history_database) as (client, database):
            common = await _product_payload(client)
            warrant = await _post(client, "/api/v1/warrants", common | {"isin": ISIN})
            venues = (await client.get("/api/v1/market-reference-data/trading-venues")).json()[
                "items"
            ]
            venue = next(item for item in venues if item["mic"] == "XETR")
            listing = await _post(
                client,
                f"/api/v1/warrants/{warrant['id']}/listings",
                {"trading_venue_id": venue["id"], "quotation_currency_code": "EUR"},
            )
            initial = await _post(
                client,
                BASE + "/purchases/external",
                {
                    "product_id": warrant["id"],
                    "quantity": 10,
                    "price_per_unit": "0.20",
                    "executed_at": "2026-08-01T10:30:00Z",
                    "currency_confirmation": DECLARATION,
                    "request_id": str(uuid4()),
                },
            )
            trade = initial["trade"]["id"]
            corrected = await _book(
                client,
                trade,
                f"executions/{initial['execution']['id']}/corrections",
                {
                    "side": "BUY",
                    "quantity": 12,
                    "price_per_unit": "0.21",
                    "executed_at": "2026-08-02T11:45:00Z",
                },
            )
            sale = await _book(client, trade, "sales", _payload(2, "0.25", "2026-08-05"))
            await seed_stored_evidence(database, warrant["id"], listing["id"], sampled=sampled)
            before = await _state(database.engine)
            statements = []

            def record_sql(_connection, _cursor, statement, _parameters, _context, _executemany):
                statements.append(statement)

            event.listen(database.engine.sync_engine, "before_cursor_execute", record_sql)
            try:
                url = f"{BASE}/trades/{trade}/price-history"
                response = await client.get(url)
                assert response.status_code == 200, response.text
                body = response.json()
                again = await client.get(url)
                assert again.status_code == 200, again.text
                assert again.json()["series"] == body["series"]
                missing = await client.get(f"{BASE}/trades/{uuid4()}/price-history")
                assert missing.status_code == 404
                recent = await client.get(url, params={"days": 1})
                assert recent.status_code == 200, recent.text
                assert recent.json()["series"] == []
            finally:
                event.remove(database.engine.sync_engine, "before_cursor_execute", record_sql)
            assert statements and not any(
                statement.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
                for statement in statements
            )
            assert await _state(database.engine) == before
            assert snapshots == [("repeatable read", "on")] * 3
            assert body["trade_id"] == trade and body["position_id"] == initial["position"]["id"]
            assert body["samples_available"] == (4 if sampled else 0)
            assert body["collection_started_at"] == ("2026-10-01T10:00:00Z" if sampled else None)
            assert body["truncated"] is False
            assert len(body["series"]) == (2 if sampled else 1)
            euro = next(item for item in body["series"] if item["currency"] == "EUR")
            assert euro["provider_exchange_code"] == "XETR"
            assert euro["venue_mic"] == "XETR"
            assert len(euro["points"]) == 1
            point = euro["points"][0]
            assert point["observed_at"] == "2026-09-01T10:00:00Z"
            assert point["retrieved_at"] == "2026-10-01T10:00:00Z"
            assert point["price"] == "0.231"
            assert point["storage"] == ("SAMPLE" if sampled else "RETAINED")
            assert point["captured_at"] == ("2026-10-01T10:00:00Z" if sampled else None)
            if sampled:
                assert body["excluded"] == {"DUPLICATE_OBSERVATION": 2, "TIMESTAMP_UNKNOWN": 1}
                foreign = next(item for item in body["series"] if item["currency"] == "USD")
                assert foreign["provider"] == "VONTOBEL_MARKETS"
                assert foreign["identity_key"] == "b" * 64
                assert foreign["points"][0]["price"] == "0.231"
            else:
                assert body["excluded"] == {}
            events = {item["id"]: item for item in body["events"]}
            assert set(events) == {corrected["id"], sale["id"]}
            purchase = events[corrected["id"]]
            assert Decimal(purchase["price"]) == Decimal("0.21")
            assert purchase["quantity"] == 12
            assert purchase["occurred_at"] == "2026-08-02T11:45:00Z"
            assert purchase["currency"] == "EUR" and purchase["plottable"] is True
            assert purchase["currency_source"] == "REPLACED_EXECUTION"
            assert events[sale["id"]]["executed_on"] == "2026-08-05"
            assert events[sale["id"]]["occurred_at"] is None
            assert events[sale["id"]]["plottable"] is False
            assert events[sale["id"]]["reason"] == "DATE_ONLY"
            position = await client.get(f"{BASE}/trades/{trade}/position")
            assert position.status_code == 200
            assert position.json()["open_quantity"] == 10
            assert Decimal(position.json()["realized_gross_pnl"]) == Decimal("0.08")

            final_sale = await _book(
                client,
                trade,
                "sales",
                {
                    "quantity": 10,
                    "price_per_unit": "0.30",
                    "executed_at": "2026-09-02T12:00:00Z",
                    "request_id": str(uuid4()),
                },
            )
            closed = await client.get(f"{BASE}/trades/{trade}/position")
            assert closed.status_code == 200, closed.text
            assert closed.json()["id"] == initial["position"]["id"]
            assert closed.json()["open_quantity"] == 0
            assert closed.json()["closed_at"] == "2026-09-02T12:00:00Z"
            assert Decimal(closed.json()["realized_gross_pnl"]) == Decimal("0.98")
            after_closing = await _state(database.engine)
            response = await client.get(url)
            assert response.status_code == 200, response.text
            closed_history = response.json()
            assert closed_history["trade_id"] == trade
            assert closed_history["position_id"] == initial["position"]["id"]
            assert closed_history["series"] == body["series"]
            closed_events = {item["id"]: item for item in closed_history["events"]}
            assert set(closed_events) == {corrected["id"], sale["id"], final_sale["id"]}
            assert closed_events[final_sale["id"]]["side"] == "SELL"
            assert closed_events[final_sale["id"]]["quantity"] == 10
            assert Decimal(closed_events[final_sale["id"]]["price"]) == Decimal("0.30")
            assert closed_events[final_sale["id"]]["currency"] == "EUR"
            assert closed_events[final_sale["id"]]["currency_source"] == "PRIOR_BUYS"
            assert closed_events[final_sale["id"]]["plottable"] is True
            assert snapshots[-1] == ("repeatable read", "on")
            assert await _state(database.engine) == after_closing

    asyncio.run(exercise())
