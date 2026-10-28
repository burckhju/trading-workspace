"""Reviewed source commands qualify the actual PostgreSQL open-position basis.

The quote boundary is cached synthetic data. Economic facts and source revisions
use their registered owner APIs in a newly generated disposable database.
"""

import asyncio
from collections.abc import Iterator
from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import text
from tests.integration.backend.learning.test_journal_write_postgres import (
    journal_database as guarded_database,
)
from tests.integration.backend.test_currency_source_evidence_postgres import (
    evidence_url,
    historical,
    venue,
)
from tests.integration.backend.test_execution_currency_reuse_postgres import (
    _book,
    _payload,
    _post,
)
from tests.integration.backend.test_position_valuation_currency_postgres import (
    _create_position,
    _install_cached_quotes,
    _positions,
    _valuation,
)
from tests.integration.backend.test_realized_gross_report_postgres import _client, _state
from tests.integration.backend.test_usd_chf_currency_references import _migrate, _product_payload

from app.features.trade_position.domain.currency import RESOLVER_VERSION
from app.features.trade_position.persistence.currency_evidence import (
    SqlAlchemyCurrencyEvidenceRepository,
)


@pytest.fixture
def source_valuation_database() -> Iterator[str]:
    yield from guarded_database.__wrapped__()


@pytest.fixture(autouse=True)
def forbid_external_calls(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    asynchronous = AsyncMock(side_effect=AssertionError("External HTTP forbidden"))
    synchronous = Mock(side_effect=AssertionError("External HTTP forbidden"))
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", asynchronous)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", synchronous)
    yield
    asynchronous.assert_not_awaited()
    synchronous.assert_not_called()


def _business(state):
    return {
        name: state[name]
        for name in ("execution_records", "positions", "trades", "execution_currency_confirmations")
    }


def _document(capture, execution_id, code):
    return {
        "kind": "EXECUTION_DOCUMENT",
        "source_reference": f"Synthetic exact execution receipt {code}",
        "request_id": str(uuid4()),
        "confirmation": "CONFIRM_SOURCE_REVIEW",
        "trade_id": capture["trade"]["id"],
        "execution_id": execution_id,
        "currency_code": code,
    }


def test_one_historical_source_qualifies_open_buys_and_revisions_requalify_without_writes(
    source_valuation_database, monkeypatch
):
    _migrate(source_valuation_database, "head")
    quotes = _install_cached_quotes(monkeypatch)

    async def exercise():
        async with _client(source_valuation_database) as (client, database):
            capture = await _create_position(
                client,
                database,
                quotes,
                await _product_payload(client),
                currency=None,
                quantity=5,
            )
            trade_id = capture["trade"]["id"]
            await _book(client, trade_id, "purchases", _payload(5, "2", "2026-08-06"))
            business = _business(await _state(database.engine))
            assert business["execution_currency_confirmations"] == []
            unknown = await _valuation(client, trade_id)
            # _create_position installed today's EUR listing and a valid EUR
            # quote route. Neither proves the historical purchase currency.
            assert unknown["position_basis"]["currency_status"] == "UNKNOWN"
            assert unknown["unrealized_gross_pnl"] is None
            assert Decimal(unknown["market_value"]) == 25
            endpoint = evidence_url(capture["trade"]["product_id"])
            body = historical(await venue(client))
            source = await _post(client, endpoint, body)
            stored = await _state(database.engine)
            assert _business(stored) == business
            known = await _valuation(client, trade_id)
            basis = known["position_basis"]
            assert basis["currency_status"] == "KNOWN"
            assert basis["cost_basis_currency"] == "EUR"
            assert Decimal(known["unrealized_gross_pnl"]) == 5
            assert len(basis["buy_currency_evidence"]) == 2
            for buy in basis["buy_currency_evidence"]:
                assert buy["source"] == "HISTORICAL_LISTINGS"
                assert buy["confirmation_ids"] == []
                assert buy["evidence_ids"] == [source["id"]]
                assert buy["resolver_version"] == RESOLVER_VERSION
                assert buy["reason"] is None
                reference = buy["evidence"][0]
                assert reference["verification"] == "USER_VERIFIED_SOURCE"
                assert reference["source_fingerprint"] == source["request_fingerprint"]
                assert reference["source_reference"] == body["source_reference"]
                assert reference["valid_from"] == source["valid_from"]
                assert reference["valid_to"] == source["valid_to"]
            assert (await _valuation(client, trade_id))["position_basis"] == basis
            assert (await _positions(client))["positions"][0]["position_basis"] == basis
            assert await _state(database.engine) == stored

            revision_body = body | {
                "request_id": str(uuid4()),
                "source_reference": "Synthetic corrected archive reference, same EUR facts",
                "supersedes_evidence_id": source["id"],
            }
            revision = await _post(client, endpoint, revision_body)
            revised = await _valuation(client, trade_id)
            revised_basis = revised["position_basis"]
            assert revised_basis["basis_id"] != basis["basis_id"]
            assert revised["unrealized_gross_pnl"] == known["unrealized_gross_pnl"]
            assert all(
                buy["evidence_ids"] == [revision["id"]]
                for buy in revised_basis["buy_currency_evidence"]
            )
            await _post(
                client,
                endpoint,
                revision_body
                | {
                    "request_id": str(uuid4()),
                    "supersedes_evidence_id": revision["id"],
                    "revoked": True,
                },
            )
            stored = await _state(database.engine)
            assert _business(stored) == business
            revoked = await _valuation(client, trade_id)
            revoked_basis = revoked["position_basis"]
            assert revoked_basis["currency_status"] == "UNKNOWN"
            assert revoked["unrealized_gross_pnl"] is None
            assert revoked_basis["basis_id"] not in {
                unknown["position_basis"]["basis_id"],
                basis["basis_id"],
                revised_basis["basis_id"],
            }
            assert (await _valuation(client, trade_id))["position_basis"] == revoked_basis
            assert await _state(database.engine) == stored

    asyncio.run(exercise())


def test_later_buy_document_overrides_prior_buy_reuse_and_conflicting_documents_stay_blocked(
    source_valuation_database, monkeypatch
):
    _migrate(source_valuation_database, "head")
    quotes = _install_cached_quotes(monkeypatch)

    async def exercise():
        async with _client(source_valuation_database) as (client, database):
            capture = await _create_position(
                client, database, quotes, await _product_payload(client), quantity=5
            )
            trade_id = capture["trade"]["id"]
            added = await _book(client, trade_id, "purchases", _payload(5, "2", "2026-08-06"))
            prior = await _valuation(client, trade_id)
            assert prior["position_basis"]["buy_currency_evidence"][1]["source"] == "PRIOR_BUYS"
            assert Decimal(prior["unrealized_gross_pnl"]) == 5
            business = _business(await _state(database.engine))
            endpoint = evidence_url(capture["trade"]["product_id"])
            usd = await _post(client, endpoint, _document(capture, added["id"], "USD"))
            mixed = await _valuation(client, trade_id)
            basis = mixed["position_basis"]
            assert basis["currency_status"] == "MIXED"
            assert basis["cost_basis_currency"] is None
            assert mixed["unrealized_pnl_reason"] == "COST_BASIS_CURRENCY_MIXED"
            assert mixed["unrealized_gross_pnl"] is None
            assert Decimal(mixed["market_value"]) == 25
            first, later = basis["buy_currency_evidence"]
            assert first["source"] == "USER_CONFIRMED" and first["currency_code"] == "EUR"
            assert later["source"] == "EXECUTION_DOCUMENT" and later["currency_code"] == "USD"
            assert later["evidence_ids"] == [usd["id"]]
            eur = await _post(client, endpoint, _document(capture, added["id"], "EUR"))
            stored = await _state(database.engine)
            conflict = await _valuation(client, trade_id)
            proof = conflict["position_basis"]["buy_currency_evidence"][1]
            assert conflict["position_basis"]["currency_status"] == "UNKNOWN"
            assert conflict["unrealized_gross_pnl"] is None
            assert proof["source"] == "CONFLICT" and proof["reason"] == "DOCUMENT_CONFLICT"
            assert set(proof["evidence_ids"]) == {usd["id"], eur["id"]}
            assert proof["confirmation_ids"] == []
            assert {item["id"] for item in proof["evidence"]} == {usd["id"], eur["id"]}
            assert (await _positions(client))["positions"][0]["position_basis"] == conflict[
                "position_basis"
            ]
            assert _business(stored) == business
            assert await _state(database.engine) == stored

    asyncio.run(exercise())


def test_open_position_source_read_shares_snapshot_during_concurrent_revocation(
    source_valuation_database, monkeypatch
):
    _migrate(source_valuation_database, "head")
    quotes = _install_cached_quotes(monkeypatch)

    async def exercise():
        async with _client(source_valuation_database) as (client, database):
            capture = await _create_position(
                client, database, quotes, await _product_payload(client), currency=None
            )
            trade_id = capture["trade"]["id"]
            endpoint = evidence_url(capture["trade"]["product_id"])
            body = historical(await venue(client))
            source = await _post(client, endpoint, body)
            before = await _valuation(client, trade_id)
            entered, resume = asyncio.Event(), asyncio.Event()
            original = SqlAlchemyCurrencyEvidenceRepository.list_for_product
            pause_once = True

            async def paused(repository, workspace_id, product_id, limit=1000):
                nonlocal pause_once
                if pause_once:
                    pause_once = False
                    session = repository._session
                    assert (
                        await session.execute(text("SHOW transaction_isolation"))
                    ).scalar_one() == "repeatable read"
                    assert (
                        await session.execute(text("SHOW transaction_read_only"))
                    ).scalar_one() == "on"
                    entered.set()
                    await asyncio.wait_for(resume.wait(), timeout=15)
                return await original(repository, workspace_id, product_id, limit)

            monkeypatch.setattr(SqlAlchemyCurrencyEvidenceRepository, "list_for_product", paused)
            pending = asyncio.create_task(_valuation(client, trade_id))
            await asyncio.wait_for(entered.wait(), timeout=10)
            try:
                await asyncio.wait_for(
                    _post(
                        client,
                        endpoint,
                        body
                        | {
                            "request_id": str(uuid4()),
                            "supersedes_evidence_id": source["id"],
                            "revoked": True,
                        },
                    ),
                    timeout=5,
                )
                assert not pending.done()
            finally:
                resume.set()
            stable = await asyncio.wait_for(pending, timeout=10)
            assert stable["position_basis"] == before["position_basis"]
            assert Decimal(stable["unrealized_gross_pnl"]) == 5
            committed = await _state(database.engine)
            current = await _valuation(client, trade_id)
            assert current["position_basis"]["basis_id"] != before["position_basis"]["basis_id"]
            assert current["position_basis"]["currency_status"] == "UNKNOWN"
            assert current["unrealized_gross_pnl"] is None
            assert Decimal(current["market_value"]) == 25
            assert await _state(database.engine) == committed

    asyncio.run(exercise())
