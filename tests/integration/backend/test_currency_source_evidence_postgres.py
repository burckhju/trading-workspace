"""Real source commands and database invariants on disposable PostgreSQL only."""

import asyncio
import json
from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from tests.integration.backend.learning.test_journal_write_postgres import (
    journal_database as guarded_database,
)
from tests.integration.backend.test_trade_capture_safety import (
    BASE,
    product,
    purchase,
    sql,
)
from tests.integration.backend.test_usd_chf_currency_references import _client, _migrate

from app.features.performance.domain.models import ReportFilters
from app.features.performance.domain.report import build_report
from app.features.performance.service.reader import RealizedGrossSnapshotReader
from app.features.trade_position.domain.currency_evidence import (
    CurrencyEvidenceLimitExceeded,
)
from app.features.trade_position.persistence.currency_evidence import (
    SqlAlchemyCurrencyEvidenceRepository,
)


@pytest.fixture
def evidence_database() -> Iterator[str]:
    yield from guarded_database.__wrapped__()


@pytest.fixture(autouse=True)
def forbid_external_http(monkeypatch):
    asynchronous = AsyncMock(side_effect=AssertionError("External HTTP forbidden"))
    synchronous = Mock(side_effect=AssertionError("External HTTP forbidden"))
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", asynchronous)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", synchronous)
    yield
    asynchronous.assert_not_awaited()
    synchronous.assert_not_called()


def evidence_url(product_id):
    return f"/api/v1/warrants/{product_id}/currency-evidence"


def historical(venue_id, **changes):
    return {
        "kind": "HISTORICAL_LISTINGS",
        "source_reference": "Synthetic exchange archive p. 7",
        "request_id": str(uuid4()),
        "confirmation": "CONFIRM_SOURCE_REVIEW",
        "valid_from": "2026-08-01T00:00:00+02:00",
        "valid_to": "2026-09-01T00:00:00+02:00",
        "listings": [{"trading_venue_id": venue_id, "currency_code": "EUR"}],
        "complete_listing_set": True,
        **changes,
    }


async def venue(client):
    response = await client.get("/api/v1/market-reference-data/trading-venues")
    assert response.status_code == 200, response.text
    return next(item["id"] for item in response.json()["items"] if item["mic"] == "XETR")


async def another_product(client, original_id):
    existing = (await client.get(f"/api/v1/warrants/{original_id}")).json()
    response = await client.post(
        "/api/v1/warrants",
        json={
            "issuer_id": existing["issuer_id"],
            "underlying_id": existing["underlying_id"],
            "display_name": "Second synthetic currency product",
            "option_direction": "CALL",
            "strike": "500",
            "maturity_date": "2099-12-31",
            "ratio": "0.1",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def business_rows(database):
    return [
        await sql(database, "SELECT * FROM execution_records ORDER BY id"),
        await sql(database, "SELECT * FROM positions ORDER BY id"),
        await sql(database, "SELECT * FROM execution_currency_confirmations ORDER BY id"),
    ]


def test_migration_preserves_legacy_unknowns_and_no_evidence_is_backfilled(
    evidence_database,
):
    _migrate(evidence_database, "head")

    async def seed():
        async with _client(evidence_database) as client:
            pid = await product(client)
            bought = await client.post(BASE + "/purchases/external", json=purchase(pid))
            assert bought.status_code == 201, bought.text
            return pid, await business_rows(evidence_database)

    pid, before = asyncio.run(seed())
    _migrate(evidence_database, "20261017_0047", action="downgrade")
    _migrate(evidence_database, "head")
    assert asyncio.run(business_rows(evidence_database)) == before
    assert asyncio.run(sql(evidence_database, "SELECT * FROM currency_source_evidence")) == []

    async def read():
        async with _client(evidence_database) as client:
            response = await client.get(evidence_url(pid))
            assert response.status_code == 200 and response.json() == {"history": []}

    asyncio.run(read())


def test_sources_retry_correct_revoke_restore_and_preserve_business_rows(
    evidence_database,
):
    _migrate(evidence_database, "head")

    async def exercise():
        async with _client(evidence_database) as client:
            pid = await product(client)
            bought = await client.post(BASE + "/purchases/external", json=purchase(pid))
            assert bought.status_code == 201, bought.text
            before = await business_rows(evidence_database)
            endpoint = evidence_url(pid)
            body = historical(await venue(client))
            replies = await asyncio.gather(*[client.post(endpoint, json=body) for _ in range(3)])
            assert [reply.status_code for reply in replies] == [201, 201, 201], [
                r.text for r in replies
            ]
            original = replies[0].json()
            assert {reply.json()["id"] for reply in replies} == {original["id"]}
            assert original["verification"] == "USER_VERIFIED_SOURCE"
            assert original["request_id"] == body["request_id"]
            changed_retry = await client.post(
                endpoint, json={**body, "complete_listing_set": False}
            )
            assert changed_retry.status_code == 409
            assert changed_retry.json()["code"] == "CURRENCY_EVIDENCE_REQUEST_CONFLICT"
            revoked_body = {
                **body,
                "request_id": str(uuid4()),
                "supersedes_evidence_id": original["id"],
                "revoked": True,
            }
            revoked = await client.post(endpoint, json=revoked_body)
            assert revoked.status_code == 201, revoked.text
            stale = await client.post(endpoint, json={**revoked_body, "request_id": str(uuid4())})
            assert stale.status_code == 409 and stale.json()["code"] == "CURRENCY_EVIDENCE_CONFLICT"
            restored = await client.post(
                endpoint,
                json={
                    **body,
                    "request_id": str(uuid4()),
                    "supersedes_evidence_id": revoked.json()["id"],
                },
            )
            assert restored.status_code == 201, restored.text
            doc = {
                "kind": "EXECUTION_DOCUMENT",
                "source_reference": "Synthetic broker receipt",
                "request_id": str(uuid4()),
                "confirmation": "CONFIRM_SOURCE_REVIEW",
                "trade_id": bought.json()["trade"]["id"],
                "execution_id": bought.json()["execution"]["id"],
                "currency_code": "EUR",
            }
            document = await client.post(endpoint, json=doc)
            assert document.status_code == 201, document.text
            history = (await client.get(endpoint)).json()["history"]
            assert [item["id"] for item in history] == [
                original["id"],
                revoked.json()["id"],
                restored.json()["id"],
                document.json()["id"],
            ]
            assert history[1]["revoked"] and not history[2]["revoked"]
            assert await business_rows(evidence_database) == before
            assert (
                len(
                    await sql(
                        evidence_database,
                        "SELECT * FROM currency_source_evidence_listing_refs",
                    )
                )
                == 3
            )
            with pytest.raises(
                AssertionError,
                match="Refusing downgrade: currency source evidence would be lost",
            ):
                await asyncio.to_thread(
                    _migrate, evidence_database, "20261017_0047", action="downgrade"
                )
            engine = create_async_engine(evidence_database, poolclass=NullPool)
            try:
                async with async_sessionmaker(engine)() as session:
                    repository = SqlAlchemyCurrencyEvidenceRepository(session)
                    with pytest.raises(CurrencyEvidenceLimitExceeded):
                        await repository.list_for_product(
                            UUID(original["workspace_id"]), UUID(pid), limit=1
                        )
            finally:
                await engine.dispose()

    asyncio.run(exercise())


async def clone_row(database, original, **changes):
    values = {**original, "id": uuid4(), "request_id": uuid4(), **changes}
    values["listings"] = json.dumps(values["listings"])
    columns = ",".join(values)
    parameters = ",".join(
        "CAST(:listings AS JSON)" if name == "listings" else f":{name}" for name in values
    )
    await sql(
        database,
        f"INSERT INTO currency_source_evidence({columns}) VALUES({parameters})",
        values,
    )


def test_database_guards_scope_immutability_reference_integrity_and_deletion(
    evidence_database,
):
    _migrate(evidence_database, "head")

    async def exercise():
        async with _client(evidence_database) as client:
            pid = await product(client)
            second_pid = await another_product(client, pid)
            endpoint = evidence_url(pid)
            body = historical(await venue(client))
            saved = await client.post(endpoint, json=body)
            assert saved.status_code == 201, saved.text
            row = dict((await sql(evidence_database, "SELECT * FROM currency_source_evidence"))[0])
            for statement in (
                "UPDATE currency_source_evidence SET complete_listing_set=false",
                "DELETE FROM currency_source_evidence",
                "DELETE FROM currency_source_evidence_listing_refs",
                "UPDATE currency_source_evidence_listing_refs SET currency_code='USD'",
            ):
                with pytest.raises(IntegrityError, match="immutable"):
                    await sql(evidence_database, statement)
            with pytest.raises(IntegrityError, match="product/workspace"):
                await clone_row(evidence_database, row, workspace_id=uuid4())
            with pytest.raises(IntegrityError, match="predecessor scope"):
                await clone_row(
                    evidence_database,
                    row,
                    product_id=second_pid,
                    supersedes_evidence_id=row["id"],
                )
            with pytest.raises(IntegrityError, match="duplicate venue"):
                await clone_row(evidence_database, row, listings=row["listings"] * 2)
            with pytest.raises(IntegrityError):
                await clone_row(
                    evidence_database,
                    row,
                    listings=[{"trading_venue_id": str(uuid4()), "currency_code": "EUR"}],
                )
            with pytest.raises(IntegrityError):
                await clone_row(
                    evidence_database,
                    row,
                    listings=[
                        {
                            "trading_venue_id": row["listings"][0]["trading_venue_id"],
                            "currency_code": "ZZZ",
                        }
                    ],
                )
            rejected = await client.delete(f"/api/v1/warrants/{pid}?version=1")
            assert rejected.status_code == 409, rejected.text
            assert len((await client.get(endpoint)).json()["history"]) == 1
            unknown = await client.post(
                endpoint,
                json={
                    **body,
                    "request_id": str(uuid4()),
                    "listings": [{"trading_venue_id": str(uuid4()), "currency_code": "EUR"}],
                },
            )
            assert (
                unknown.status_code == 422 and unknown.json()["code"] == "TRADING_VENUE_NOT_FOUND"
            )
            missing_review = await client.post(
                endpoint,
                json={key: value for key, value in body.items() if key != "confirmation"},
            )
            assert missing_review.status_code == 422

    asyncio.run(exercise())


def test_document_does_not_cross_product_or_execution_scope(evidence_database):
    _migrate(evidence_database, "head")

    async def exercise():
        async with _client(evidence_database) as client:
            pid = await product(client)
            other = await another_product(client, pid)
            bought = await client.post(BASE + "/purchases/external", json=purchase(pid))
            assert bought.status_code == 201, bought.text
            doc = {
                "kind": "EXECUTION_DOCUMENT",
                "source_reference": "Synthetic exact receipt",
                "request_id": str(uuid4()),
                "confirmation": "CONFIRM_SOURCE_REVIEW",
                "trade_id": bought.json()["trade"]["id"],
                "execution_id": bought.json()["execution"]["id"],
                "currency_code": "EUR",
            }
            foreign = await client.post(evidence_url(other), json=doc)
            assert foreign.status_code == 404 and foreign.json()["code"] == "EXECUTION_NOT_FOUND"
            missing = await client.post(
                evidence_url(pid), json={**doc, "execution_id": str(uuid4())}
            )
            assert missing.status_code == 404 and missing.json()["code"] == "EXECUTION_NOT_FOUND"
            assert (await client.get(evidence_url(pid))).json()["history"] == []
            document = await client.post(evidence_url(pid), json=doc)
            assert document.status_code == 201, document.text
            before = await business_rows(evidence_database)
            row = dict((await sql(evidence_database, "SELECT * FROM currency_source_evidence"))[0])
            with pytest.raises(IntegrityError, match="execution scope"):
                await clone_row(evidence_database, row, execution_id=uuid4())
            assert await business_rows(evidence_database) == before

    asyncio.run(exercise())


async def capture_unconfirmed_cycle(client):
    pid = await product(client)
    bought = await client.post(BASE + "/purchases/external", json=purchase(pid))
    assert bought.status_code == 201, bought.text
    trade_id = bought.json()["trade"]["id"]
    sale = await client.post(
        BASE + f"/trades/{trade_id}/sales",
        json={
            "quantity": 4,
            "price_per_unit": "0.90",
            "executed_on": "2026-08-18",
            "execution_timezone": "Europe/Berlin",
            "request_id": str(uuid4()),
        },
    )
    assert sale.status_code == 201, sale.text
    return pid, bought.json(), sale.json()


async def read_report(engine):
    snapshot = await RealizedGrossSnapshotReader(engine).read(
        UUID("00000000-0000-4000-8000-000000000001"), "EUR"
    )
    return build_report(
        snapshot,
        ReportFilters(date(2026, 8, 1), date(2026, 8, 31), "EUR", "Europe/Berlin"),
    )


def test_historical_sources_feed_real_report_without_confirmations_or_read_writes(
    evidence_database,
):
    _migrate(evidence_database, "head")

    async def exercise():
        engine = create_async_engine(evidence_database, poolclass=NullPool)
        try:
            async with _client(evidence_database) as client:
                pid, bought, sale = await capture_unconfirmed_cycle(client)
                before = await business_rows(evidence_database)
                missing = await read_report(engine)
                assert missing.counts.usable == 0 and missing.counts.unresolved == 1
                venue_id = await venue(client)
                listing = await client.post(
                    f"/api/v1/warrants/{pid}/listings",
                    json={
                        "trading_venue_id": venue_id,
                        "symbol": "SYNTHETIC-EVIDENCE",
                        "quotation_currency_code": "EUR",
                    },
                )
                assert listing.status_code == 201, listing.text
                current_only = await read_report(engine)
                assert current_only.counts.usable == 0
                assert current_only.basis.id == missing.basis.id
                body = historical(venue_id)
                evidence = await client.post(evidence_url(pid), json=body)
                assert evidence.status_code == 201, evidence.text
                eid = evidence.json()["id"]
                evidenced = await read_report(engine)
                assert evidenced.counts.usable == 1 and evidenced.counts.unresolved == 0
                assert Decimal(evidenced.summary.total) == Decimal("1.40")
                assert Decimal(evidenced.items[0].average_cost_per_unit) == Decimal("0.55")
                assert Decimal(evidenced.items[0].cost_basis_after) == Decimal("3.30")
                assert evidenced.items[0].execution_id == UUID(sale["execution"]["id"])
                assert {item.execution_id for item in evidenced.sources} == {
                    UUID(bought["execution"]["id"]),
                    UUID(sale["execution"]["id"]),
                }
                assert all(
                    item.currency_confirmation is None and not item.currency_history
                    for item in evidenced.sources
                )
                assert all(
                    item.currency_resolution.evidence_ids == (UUID(eid),)
                    for item in evidenced.sources
                )
                again = await read_report(engine)
                assert (
                    again.basis.id == evidenced.basis.id
                    and again.items == evidenced.items
                    and again.sources == evidenced.sources
                )
                assert await business_rows(evidence_database) == before
                correction = await client.post(
                    evidence_url(pid),
                    json={
                        **body,
                        "request_id": str(uuid4()),
                        "supersedes_evidence_id": eid,
                        "listings": [{"trading_venue_id": venue_id, "currency_code": "USD"}],
                    },
                )
                assert correction.status_code == 201, correction.text
                foreign = await read_report(engine)
                assert foreign.counts.usable == 0 and foreign.counts.excluded == 1
                assert foreign.summary.status == "EMPTY" and foreign.summary.total == "0"
                assert foreign.items[0].realized_gross_pnl_delta is None
                assert "OTHER_CURRENCY" in foreign.items[0].reasons
                assert foreign.basis.id != evidenced.basis.id
                revoked = await client.post(
                    evidence_url(pid),
                    json={
                        **body,
                        "request_id": str(uuid4()),
                        "supersedes_evidence_id": correction.json()["id"],
                        "revoked": True,
                    },
                )
                assert revoked.status_code == 201, revoked.text
                withdrawn = await read_report(engine)
                assert withdrawn.counts.usable == 0 and withdrawn.counts.unresolved == 1
                assert withdrawn.summary.total is None and withdrawn.basis.id != foreign.basis.id
                assert await business_rows(evidence_database) == before
        finally:
            await engine.dispose()

    asyncio.run(exercise())


def test_snapshot_does_not_mix_a_concurrently_committed_source_revocation(
    evidence_database, monkeypatch
):
    _migrate(evidence_database, "head")

    async def exercise():
        engine = create_async_engine(evidence_database, poolclass=NullPool)
        try:
            async with _client(evidence_database) as client:
                pid, _, _ = await capture_unconfirmed_cycle(client)
                body = historical(await venue(client))
                posted = await client.post(evidence_url(pid), json=body)
                assert posted.status_code == 201, posted.text
                before = await read_report(engine)
                entered, resume = asyncio.Event(), asyncio.Event()
                original = RealizedGrossSnapshotReader._read_confirmations
                pause_once = True

                async def paused(reader, session, workspace_id):
                    nonlocal pause_once
                    if pause_once:
                        pause_once = False
                        entered.set()
                        await asyncio.wait_for(resume.wait(), timeout=15)
                    return await original(reader, session, workspace_id)

                monkeypatch.setattr(RealizedGrossSnapshotReader, "_read_confirmations", paused)
                pending = asyncio.create_task(read_report(engine))
                await asyncio.wait_for(entered.wait(), timeout=10)
                try:
                    revoked = await asyncio.wait_for(
                        client.post(
                            evidence_url(pid),
                            json={
                                **body,
                                "request_id": str(uuid4()),
                                "supersedes_evidence_id": posted.json()["id"],
                                "revoked": True,
                            },
                        ),
                        timeout=5,
                    )
                    assert revoked.status_code == 201, revoked.text
                finally:
                    resume.set()
                    overlapping = await asyncio.wait_for(pending, timeout=15)
                assert overlapping.basis.id == before.basis.id
                assert overlapping.items == before.items and overlapping.counts.usable == 1
                after = await read_report(engine)
                assert after.basis.id != before.basis.id and after.counts.usable == 0
                assert after.counts.unresolved == 1
        finally:
            await engine.dispose()

    asyncio.run(exercise())


def test_concurrent_source_corrections_have_one_current_successor(evidence_database):
    _migrate(evidence_database, "head")

    async def exercise():
        async with _client(evidence_database) as client:
            pid = await product(client)
            endpoint = evidence_url(pid)
            body = historical(await venue(client))
            original = await client.post(endpoint, json=body)
            assert original.status_code == 201, original.text
            replies = await asyncio.gather(
                *[
                    client.post(
                        endpoint,
                        json={
                            **body,
                            "request_id": str(uuid4()),
                            "supersedes_evidence_id": original.json()["id"],
                            "source_reference": f"Synthetic corrected source {index}",
                        },
                    )
                    for index in range(2)
                ]
            )
            assert sorted(reply.status_code for reply in replies) == [201, 409], [
                reply.text for reply in replies
            ]
            assert (
                next(reply for reply in replies if reply.status_code == 409).json()["code"]
                == "CURRENCY_EVIDENCE_CONFLICT"
            )
            assert len((await client.get(endpoint)).json()["history"]) == 2

    asyncio.run(exercise())
