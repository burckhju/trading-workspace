"""Owner captures -> one PostgreSQL valuation basis -> depot/browser contract.

Each test owns a newly generated migrated database. All executions, corrections
and confirmations use registered owner APIs. Only verified synthetic quote-route
metadata and the cached quote boundary are supplied by fixtures. No lifespan,
scheduler, provider transport or user database is used.
"""

import asyncio
import hashlib
import json
import os
import re
from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from importlib import import_module
from pathlib import Path
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import httpx
import pytest
from app.database import DatabaseManager
from app.features.market_data.domain.enums import (
    CacheStatus,
    MappingStatus,
    MarketDataCapability,
    MarketDataProvider,
    QualityStatus,
)
from app.features.market_data.domain.models import WarrantQuoteSnapshot
from app.features.market_data.persistence.models import WarrantProviderMappingModel
from app.features.market_data.service.types import MarketDataResult, WarrantQuoteRequest
from app.features.operational_workspace.service.position_snapshot import (
    OperationalPositionSnapshotService,
)
from app.features.position_monitoring.service.quote_sources import (
    MultiSourceWarrantQuoteResolver,
    NamedWarrantQuoteSource,
)
from app.features.trade_position.domain.models import Trade
from app.features.trade_position.persistence.models import TradeModel
from app.features.trade_position.service.valuation_basis import PositionValuationBasis
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration.backend.learning.test_journal_write_postgres import (
    journal_database as guarded_database,
)
from tests.integration.backend.test_execution_currency_reuse_postgres import (
    _book,
    _correct,
    _payload,
    _post,
)
from tests.integration.backend.test_realized_gross_report_postgres import (
    DECLARATION,
    _client,
    _state,
)
from tests.integration.backend.test_trade_capture_safety import BASE, WORKSPACE
from tests.integration.backend.test_usd_chf_currency_references import _migrate, _product_payload

valuation_module = import_module("app.features.position_monitoring.service.product_valuation")
monitoring_api = import_module("app.features.position_monitoring.api.router")
workspace_api = import_module("app.features.operational_workspace.api.router")
capture_dependencies = import_module("app.features.trade_position.api.dependencies")

NOW = datetime(2026, 10, 28, 12, tzinfo=UTC)
POSITIONS = "/api/v1/operational-workspace/positions"
VALUATION = "/api/v1/position-monitoring/trades/{trade_id}/product-valuation"
FIXTURE = Path(__file__).resolve().parents[2] / "fixtures/position_currency_qualification.json"
UUID_PATTERN = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}")


@pytest.fixture
def valuation_database() -> Iterator[str]:
    yield from guarded_database.__wrapped__()


@pytest.fixture(autouse=True)
def forbid_external_calls(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    external_async = AsyncMock(side_effect=AssertionError("External HTTP forbidden"))
    external_sync = Mock(side_effect=AssertionError("External HTTP forbidden"))
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", external_async)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", external_sync)
    yield
    external_async.assert_not_awaited()
    external_sync.assert_not_called()


class CachedQuotes:
    def __init__(self) -> None:
        self.quotes: dict[UUID, WarrantQuoteSnapshot] = {}
        self.calls: list[UUID] = []
        self.before_read: AsyncMock | None = None

    async def get_warrant_listing_quote(
        self, request: WarrantQuoteRequest
    ) -> MarketDataResult[WarrantQuoteSnapshot]:
        if self.before_read is not None:
            await self.before_read()
        self.calls.append(request.warrant_listing_id)
        return MarketDataResult(
            data=self.quotes[request.warrant_listing_id],
            provider=MarketDataProvider.EODHD,
            capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
            correlation_id=request.correlation_id,
            retrieved_at=NOW,
            cache_status=CacheStatus.HIT,
            quality_status=QualityStatus.VALID,
            warnings=(),
            retry_count=0,
            provider_call_cost=0,
        )


def _install_cached_quotes(monkeypatch: pytest.MonkeyPatch) -> CachedQuotes:
    provider = CachedQuotes()
    resolver = MultiSourceWarrantQuoteResolver((NamedWarrantQuoteSource("EODHD", provider),))
    monkeypatch.setattr(monitoring_api, "build_warrant_quote_resolver", lambda _: resolver)
    monkeypatch.setattr(workspace_api, "build_warrant_quote_resolver", lambda _: resolver)
    # This controlled route is the only allowed route. Real identity, persistence
    # and automatic source selection still run inside the existing owner command.
    monkeypatch.setattr(
        capture_dependencies,
        "_allowed_warrant_quote_providers",
        lambda _: frozenset({MarketDataProvider.EODHD}),
    )
    return provider


async def _create_position(
    client: AsyncClient,
    database: DatabaseManager,
    quotes: CachedQuotes,
    common: dict,
    *,
    index: int = 1,
    name: str = "Currency gain",
    currency: str | None = "EUR",
    quantity: int = 10,
    bid: str = "2.50",
) -> dict:
    isin = f"DE000CV{index:05d}"
    warrant = await _post(
        client,
        "/api/v1/warrants",
        common | {"display_name": name, "isin": isin, "strike_currency_code": "EUR"},
    )
    venues = (await client.get("/api/v1/market-reference-data/trading-venues")).json()["items"]
    venue = next(item for item in venues if item["mic"] == "XETR")
    listing = await _post(
        client,
        f"/api/v1/warrants/{warrant['id']}/listings",
        {
            "trading_venue_id": venue["id"],
            "quotation_currency_code": "EUR",
            "symbol": f"CV{index:05d}",
        },
    )
    listing_id = UUID(listing["id"])
    # Synthetic reference evidence only; never insert economic executions or
    # confirmations directly. The production source selector validates this row.
    async with database.session_context() as session:
        session.add(
            WarrantProviderMappingModel(
                id=uuid4(),
                workspace_id=UUID(WORKSPACE),
                warrant_listing_id=listing_id,
                provider=MarketDataProvider.EODHD,
                provider_symbol=isin,
                provider_exchange_code="XETR",
                status=MappingStatus.ACTIVE,
                validated_at=NOW,
                created_at=NOW,
                updated_at=NOW,
                version=1,
            )
        )
        await session.commit()
    quotes.quotes[listing_id] = WarrantQuoteSnapshot(
        warrant_listing_id=listing_id,
        bid=Decimal(bid),
        ask=Decimal(bid) + Decimal("0.05"),
        currency="EUR",
        provider_symbol=isin,
        provider_exchange_code="XETR",
        observed_at=NOW,
        isin=isin,
    )
    return await _post(
        client,
        BASE + "/purchases/external",
        {"product_id": warrant["id"]} | _payload(quantity, "2.00", "2026-08-05", currency),
    )


async def _valuation(client: AsyncClient, trade_id: str) -> dict:
    response = await client.get(VALUATION.format(trade_id=trade_id))
    assert response.status_code == 200, response.text
    return response.json()


async def _positions(client: AsyncClient) -> dict:
    response = await client.get(POSITIONS)
    assert response.status_code == 200, response.text
    return response.json()


def _browser_fixture(payload: dict, valuations: dict[str, dict]) -> dict:
    """Stabilize opaque identities/read time only; never alter financial fields.

    Owner IDs and source basis hashes are random between isolated databases.
    Stable one-to-one UUID remapping preserves every relation, including routes.
    The committed fixture is otherwise the actual complete REST response.
    """
    identities: dict[str, str] = {}

    def stable_uuid(match: re.Match[str]) -> str:
        value = match.group(0)
        if value not in identities:
            identities[value] = str(UUID(int=1000 + len(identities)))
        return identities[value]

    def normalize(value: object, *, name: str = "", key: str = "") -> object:
        if isinstance(value, dict):
            return {k: normalize(v, name=name, key=k) for k, v in value.items()}
        if isinstance(value, list):
            return [normalize(v, name=name, key=key) for v in value]
        if isinstance(value, str):
            if key == "basis_id":
                return hashlib.sha256(f"synthetic fixture basis {name}".encode()).hexdigest()
            return UUID_PATTERN.sub(stable_uuid, value)
        return value

    ordered = sorted(payload["positions"], key=lambda item: item["product_name"])
    positions_response = {
        "generated_at": NOW.isoformat().replace("+00:00", "Z"),
        "positions": [normalize(row, name=row["product_name"]) for row in ordered],
    }
    return {
        "positions_response": positions_response,
        "valuations": {
            identities[row["trade_id"]]: normalize(
                valuations[row["trade_id"]], name=row["product_name"]
            )
            for row in ordered
        },
    }


def test_owner_to_depot_preserves_market_value_and_excludes_unqualified_pnl(
    valuation_database: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    _migrate(valuation_database, "head")
    quotes = _install_cached_quotes(monkeypatch)

    async def exercise() -> None:
        async with _client(valuation_database) as (client, database):
            common = await _product_payload(client)
            cases = (
                ("Currency unknown", None, "2.50", "COST_BASIS_CURRENCY_UNKNOWN", None),
                ("Currency mismatch", "USD", "2.50", "COST_BASIS_CURRENCY_MISMATCH", None),
                ("Currency mixed", "EUR", "2.50", "COST_BASIS_CURRENCY_MIXED", None),
                ("Currency gain", "EUR", "2.50", "COST_BASIS_CURRENCY_MATCHED", "5"),
                ("Currency loss", "EUR", "1.50", "COST_BASIS_CURRENCY_MATCHED", "-5"),
                ("Currency neutral", "EUR", "2.00", "COST_BASIS_CURRENCY_MATCHED", "0"),
            )
            captures = {}
            for index, (name, currency, bid, _reason, _pnl) in enumerate(cases, 1):
                capture = await _create_position(
                    client,
                    database,
                    quotes,
                    common,
                    index=index,
                    name=name,
                    currency=currency,
                    quantity=5 if name == "Currency mixed" else 10,
                    bid=bid,
                )
                captures[name] = capture
                if name == "Currency mixed":
                    await _book(
                        client,
                        capture["trade"]["id"],
                        "purchases",
                        _payload(5, "2.00", "2026-08-06", "USD"),
                    )
            assert quotes.calls == []  # Booking/source selection needs no quote repair.
            before = await _state(database.engine)
            valuations = {}
            for name, _currency, bid, reason, pnl in cases:
                value = await _valuation(client, captures[name]["trade"]["id"])
                valuations[captures[name]["trade"]["id"]] = value
                assert value["source_selection_status"] == "SELECTED"
                assert value["selected_source"] == "EODHD"
                assert value["status"] == "AVAILABLE"
                assert Decimal(value["market_value"]) == Decimal(bid) * 10
                assert value["analysis_market_value"] == value["market_value"]
                assert value["unrealized_pnl_reason"] == reason
                assert value["analysis_unrealized_pnl_reason"] == reason
                assert value["unrealized_pnl_usable"] is (pnl is not None)
                assert value["analysis_unrealized_pnl_usable"] is (pnl is not None)
                if pnl is None:
                    assert value["unrealized_gross_pnl"] is None
                    assert value["analysis_unrealized_gross_pnl"] is None
                else:
                    assert Decimal(value["unrealized_gross_pnl"]) == Decimal(pnl)
                    assert value["analysis_unrealized_gross_pnl"] == value["unrealized_gross_pnl"]
                assert (
                    value["position_basis"]["definition_version"] == "position-unrealized-gross-v1"
                )
            depot = await _positions(client)
            rows = {row["product_name"]: row for row in depot["positions"]}
            assert len(rows) == 6
            for name, _currency, bid, reason, pnl in cases:
                row = rows[name]
                assert row["open_quantity"] == 10
                assert Decimal(row["cost_basis"]) == Decimal("20")
                assert Decimal(row["market_value"]) == Decimal(bid) * 10
                assert row["unrealized_pnl_usable"] is (pnl is not None)
                assert row["unrealized_pnl_reason"] == reason
                assert row["position_basis"]["position"]["open_quantity"] == row["open_quantity"]
                assert row["position_basis"]["position"]["cost_basis"] == row["cost_basis"]
                if pnl is None:
                    assert row["unrealized_gross_pnl"] is None
                else:
                    assert Decimal(row["unrealized_gross_pnl"]) == Decimal(pnl)
            assert len(quotes.calls) == 12  # One existing quote read per valuation, no repair.
            assert await _state(database.engine) == before
            normalized = _browser_fixture(depot, valuations)
            output = os.environ.get("POSITION_CURRENCY_FIXTURE_OUTPUT")
            if output:
                Path(output).write_text(json.dumps(normalized, indent=2) + "\n")
            assert normalized == json.loads(FIXTURE.read_text())

    asyncio.run(exercise())


def test_additions_partial_sales_and_corrections_keep_exact_cost_evidence(
    valuation_database: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    _migrate(valuation_database, "head")
    quotes = _install_cached_quotes(monkeypatch)

    async def exercise() -> None:
        async with _client(valuation_database) as (client, database):
            capture = await _create_position(
                client, database, quotes, await _product_payload(client)
            )
            trade_id = capture["trade"]["id"]
            first = capture["execution"]
            confirmation = first["currency_confirmation"]["id"]
            additional = await _book(client, trade_id, "purchases", _payload(10, "4", "2026-08-06"))
            sale = await _book(client, trade_id, "sales", _payload(5, "5", "2026-08-07", "USD"))
            initial = await _valuation(client, trade_id)
            assert initial["unrealized_pnl_usable"] is True
            assert Decimal(initial["unrealized_gross_pnl"]) == Decimal("-7.5")
            basis = initial["position_basis"]
            assert basis["effective_execution_ids"] == [first["id"], additional["id"], sale["id"]]
            assert basis["cost_basis_currency"] == "EUR"
            assert [buy["source"] for buy in basis["buy_currency_evidence"]] == [
                "USER_CONFIRMED",
                "PRIOR_BUYS",
            ]
            assert all(
                buy["confirmation_ids"] == [confirmation] for buy in basis["buy_currency_evidence"]
            )
            replacement = await _correct(
                client, trade_id, first["id"], "BUY", 10, "1", "2026-08-05"
            )
            corrected = await _valuation(client, trade_id)
            assert Decimal(corrected["unrealized_gross_pnl"]) == 0
            assert corrected["position_basis"]["basis_id"] != basis["basis_id"]
            assert corrected["position_basis"]["effective_execution_ids"] == [
                replacement["id"],
                additional["id"],
                sale["id"],
            ]
            inherited = corrected["position_basis"]["buy_currency_evidence"][0]
            assert inherited["source"] == "REPLACED_EXECUTION"
            assert inherited["source_execution_ids"] == [first["id"]]
            assert inherited["confirmation_ids"] == [confirmation]
            # Move the only directly confirmed ancestor's replacement behind the
            # unconfirmed additional BUY. Later known costs cannot heal that BUY.
            moved = await _correct(
                client, trade_id, replacement["id"], "BUY", 10, "1", "2026-08-06"
            )
            unresolved = await _valuation(client, trade_id)
            assert unresolved["unrealized_gross_pnl"] is None
            assert unresolved["unrealized_pnl_reason"] == "COST_BASIS_CURRENCY_UNKNOWN"
            assert Decimal(unresolved["market_value"]) == Decimal("37.5")
            assert unresolved["position_basis"]["effective_execution_ids"] == [
                additional["id"],
                moved["id"],
                sale["id"],
            ]
            stored = await _state(database.engine)
            assert len(stored["execution_currency_confirmations"]) == 2
            await _positions(client)
            assert await _state(database.engine) == stored

    asyncio.run(exercise())


@pytest.mark.parametrize("change", ["currency", "price", "quantity"])
def test_repeatable_read_preserves_old_basis_while_owner_correction_commits(
    valuation_database: str, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    _migrate(valuation_database, "head")
    quotes = _install_cached_quotes(monkeypatch)

    async def exercise() -> None:
        async with _client(valuation_database) as (client, database):
            capture = await _create_position(
                client, database, quotes, await _product_payload(client)
            )
            trade_id = capture["trade"]["id"]
            execution = capture["execution"]
            before = await _valuation(client, trade_id)
            entered, resume = asyncio.Event(), asyncio.Event()
            original = valuation_module.read_position_valuation_basis
            pause_once = True
            basis_session: AsyncSession | None = None

            async def paused(
                session: AsyncSession, *, trade: Trade, position_id: UUID
            ) -> PositionValuationBasis:
                nonlocal pause_once, basis_session
                basis_session = session
                if pause_once:
                    pause_once = False
                    assert (
                        await session.execute(text("SHOW transaction_isolation"))
                    ).scalar_one() == "repeatable read"
                    assert (
                        await session.execute(text("SHOW transaction_read_only"))
                    ).scalar_one() == "on"
                    entered.set()
                    await asyncio.wait_for(resume.wait(), timeout=15)
                return await original(session, trade=trade, position_id=position_id)

            async def ensure_basis_transaction_closed() -> None:
                assert basis_session is not None
                assert not basis_session.in_transaction()

            monkeypatch.setattr(valuation_module, "read_position_valuation_basis", paused)
            quotes.before_read = AsyncMock(side_effect=ensure_basis_transaction_closed)
            pending = asyncio.create_task(_valuation(client, trade_id))
            await asyncio.wait_for(entered.wait(), timeout=10)
            try:
                if change == "currency":
                    writer = await asyncio.wait_for(
                        _post(
                            client,
                            f"{BASE}/trades/{trade_id}/executions/{execution['id']}/currency-confirmations",
                            DECLARATION
                            | {
                                "currency_code": "USD",
                                "request_id": str(uuid4()),
                                "supersedes_confirmation_id": execution["currency_confirmation"][
                                    "id"
                                ],
                            },
                        ),
                        timeout=5,
                    )
                else:
                    writer = await asyncio.wait_for(
                        _correct(
                            client,
                            trade_id,
                            execution["id"],
                            "BUY",
                            20 if change == "quantity" else 10,
                            "3" if change == "price" else "2",
                            "2026-08-05",
                        ),
                        timeout=5,
                    )
                assert writer["id"] != execution["id"]
                assert not pending.done()  # Writer committed; reader did not lock it out.
            finally:
                resume.set()
            old = await asyncio.wait_for(pending, timeout=10)
            assert old["position_basis"] == before["position_basis"]
            assert Decimal(old["unrealized_gross_pnl"]) == 5
            committed = await _state(database.engine)
            current = await _valuation(client, trade_id)
            assert current["position_basis"]["basis_id"] != before["position_basis"]["basis_id"]
            if change == "currency":
                assert current["unrealized_gross_pnl"] is None
                assert current["unrealized_pnl_reason"] == "COST_BASIS_CURRENCY_MISMATCH"
                assert current["position_basis"]["buy_currency_evidence"][0][
                    "confirmation_ids"
                ] == [writer["id"]]
                assert Decimal(current["market_value"]) == 25
            elif change == "price":
                assert Decimal(current["unrealized_gross_pnl"]) == -5
                assert Decimal(current["market_value"]) == 25
            else:
                assert current["position_basis"]["position"]["open_quantity"] == 20
                assert Decimal(current["unrealized_gross_pnl"]) == 10
                assert Decimal(current["market_value"]) == 50
            depot = (await _positions(client))["positions"][0]
            assert depot["position_basis"] == current["position_basis"]
            assert depot["open_quantity"] == current["position_basis"]["position"]["open_quantity"]
            assert await _state(database.engine) == committed
            assert quotes.before_read.await_count == 3

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "availability", ["available", "provider_unavailable", "source_unavailable"]
)
def test_depot_replaces_earlier_quantity_with_its_actual_valuation_basis(
    valuation_database: str, monkeypatch: pytest.MonkeyPatch, availability: str
) -> None:
    _migrate(valuation_database, "head")
    quotes = _install_cached_quotes(monkeypatch)
    if availability == "provider_unavailable":
        monkeypatch.setattr(workspace_api, "build_warrant_quote_resolver", lambda _: None)
    elif availability == "source_unavailable":
        monkeypatch.setattr(
            capture_dependencies, "_allowed_warrant_quote_providers", lambda _: frozenset()
        )

    async def exercise() -> None:
        async with _client(valuation_database) as (client, database):
            capture = await _create_position(
                client, database, quotes, await _product_payload(client)
            )
            trade_id = capture["trade"]["id"]
            before = (await _positions(client))["positions"][0]
            assert before["open_quantity"] == 10
            original = OperationalPositionSnapshotService._current_stop_target
            changed = False
            committed_state = None

            async def correct_after_initial_position_read(
                service: OperationalPositionSnapshotService, trade: TradeModel
            ) -> tuple[Decimal | None, Decimal | None]:
                nonlocal changed, committed_state
                if not changed:
                    changed = True
                    # list_positions has already materialized the old row. This
                    # independent real writer commits before the valuation read.
                    await _correct(
                        client, trade_id, capture["execution"]["id"], "BUY", 20, "2", "2026-08-05"
                    )
                    committed_state = await _state(database.engine)
                return await original(service, trade)

            monkeypatch.setattr(
                OperationalPositionSnapshotService,
                "_current_stop_target",
                correct_after_initial_position_read,
            )
            current = (await _positions(client))["positions"][0]
            assert changed and committed_state is not None
            assert current["open_quantity"] == 20
            assert Decimal(current["cost_basis"]) == 40
            if availability == "available":
                assert Decimal(current["market_value"]) == 50
                assert Decimal(current["unrealized_gross_pnl"]) == 10
                assert current["unrealized_pnl_usable"] is True
            else:
                assert current["market_value"] is None
                assert current["unrealized_gross_pnl"] is None
                assert current["unrealized_pnl_usable"] is False
                assert current["valuation_status"] == "UNAVAILABLE"
                assert current["unrealized_pnl_reason"] == (
                    "WARRANT_QUOTE_PROVIDER_UNAVAILABLE"
                    if availability == "provider_unavailable"
                    else "NO_ALLOWED_VERIFIED_QUOTE_SOURCE"
                )
                assert quotes.calls == []
            assert (
                current["position_basis"]["position"]["open_quantity"] == current["open_quantity"]
            )
            assert current["position_basis"]["position"]["cost_basis"] == current["cost_basis"]
            assert current["position_basis"]["basis_id"] != before["position_basis"]["basis_id"]
            assert await _state(database.engine) == committed_state

    asyncio.run(exercise())
