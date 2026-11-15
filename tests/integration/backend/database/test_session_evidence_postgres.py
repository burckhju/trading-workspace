"""Actual session-ledger guards in freshly generated, synthetic PostgreSQL databases.

The designated test parent is checked before creating a UUID database. No
provider, scheduler or notification runs; existing business facts are captured
through the real REST owner and remain unchanged by calendar evidence imports.
"""

import asyncio
import base64
import json
from contextlib import asynccontextmanager
from copy import deepcopy
from datetime import UTC, datetime, time, timedelta
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import httpx
import pytest
from pydantic import TypeAdapter
from sqlalchemy import insert, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool
from tests.integration.backend.database.test_position_baseline_evidence_postgres import seed
from tests.integration.backend.learning.test_journal_write_postgres import (
    journal_database as guarded_database,
)
from tests.integration.backend.test_realized_gross_report_postgres import (
    _client as real_client,
)
from tests.integration.backend.test_realized_gross_report_postgres import _state
from tests.integration.backend.test_trade_capture_safety import (
    BASE,
    WORKSPACE,
    product,
    purchase,
    sql,
)
from tests.integration.backend.test_usd_chf_currency_references import _migrate
from tests.unit.backend.features.market_data import test_session_evidence_service as examples

from app.features.market_data.api import session_evidence as api
from app.features.market_data.domain.session_evidence import SessionEvidenceImportCommand
from app.features.market_data.persistence.session_evidence import SessionEvidenceModel
from app.features.position_monitoring.service.hebeltrader_sessions import HebeltraderSessionReader

URL = "/api/v1/market-data/session-evidence"
PREVIOUS = "20261114_0051"
CONFIRMATION = "CONFIRM_OFFICIAL_SESSION_DOCUMENT_REVIEW"


@pytest.fixture
def session_database():
    # Exact parent name, then create/drop only the generated database, never the parent.
    yield from guarded_database.__wrapped__()


@pytest.fixture(autouse=True)
def forbid_outbound_http(monkeypatch):
    asynchronous = AsyncMock(side_effect=AssertionError("External HTTP forbidden"))
    synchronous = Mock(side_effect=AssertionError("External HTTP forbidden"))
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", asynchronous)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", synchronous)
    yield
    asynchronous.assert_not_awaited()
    synchronous.assert_not_called()


def engine_for(url):
    assert make_url(url).database.startswith("tw_currency_ref_test_")
    return create_async_engine(url, poolclass=NullPool)


async def state(url):
    engine = engine_for(url)
    try:
        return await _state(engine)
    finally:
        await engine.dispose()


async def seed_scope(client, url, *, purchased_on=None):
    if purchased_on is None:
        data, underlying_id = await seed(client)
    else:
        product_id = await product(client)
        bought = await client.post(
            BASE + "/purchases/external", json=purchase(product_id, day=purchased_on.isoformat())
        )
        assert bought.status_code == 201, bought.text
        data = bought.json()
        details = await client.get(f"/api/v1/warrants/{product_id}")
        assert details.status_code == 200, details.text
        underlying_id = UUID(details.json()["underlying_id"])
    rows = await sql(
        url,
        "SELECT l.id AS listing_id, l.trading_venue_id, v.mic, v.timezone "
        "FROM listings l JOIN trading_venues v ON v.id=l.trading_venue_id "
        "WHERE l.workspace_id=:workspace AND l.underlying_id=:underlying AND l.is_primary",
        {"workspace": WORKSPACE, "underlying": underlying_id},
    )
    assert len(rows) == 1
    return data, underlying_id, dict(rows[0])


def import_body(underlying, binding, *, value=None, **overrides):
    original = examples.manifest() if value is None else value
    original["binding"].update(
        instrument_id=str(underlying),
        listing_id=str(binding["listing_id"]),
        trading_venue_id=str(binding["trading_venue_id"]),
        venue_mic=binding["mic"],
        timezone=binding["timezone"],
    )
    now = datetime.now(UTC)
    command = examples.command(
        original,
        reviewed_at=now - timedelta(minutes=1),
        retrieved_at=now - timedelta(minutes=2),
        **overrides,
    )
    return {
        **TypeAdapter(SessionEvidenceImportCommand).dump_python(command, mode="json"),
        "confirmation": CONFIRMATION,
    }


def read_query(underlying, binding, **overrides):
    result = {
        "instrument_kind": "UNDERLYING",
        "instrument_id": str(underlying),
        "start_date": examples.START.isoformat(),
        "end_date": examples.END.isoformat(),
        "known_at": datetime.now(UTC).isoformat(),
        "expected_listing_id": str(binding["listing_id"]),
    }
    result.update(overrides)
    return result


def test_migration_preserves_business_rows_and_only_allows_empty_downgrade(session_database):
    _migrate(session_database, PREVIOUS)

    async def prepare():
        async with real_client(session_database) as (client, _):
            return await seed_scope(client, session_database)

    _, underlying, binding = asyncio.run(prepare())
    before = asyncio.run(state(session_database))
    _migrate(session_database, "head")
    migrated = asyncio.run(state(session_database))
    assert migrated["market_session_evidence"] == []
    assert {name: migrated[name] for name in before if name != "alembic_version"} == {
        name: rows for name, rows in before.items() if name != "alembic_version"
    }
    _migrate(session_database, PREVIOUS, action="downgrade")
    assert "market_session_evidence" not in asyncio.run(state(session_database))
    _migrate(session_database, "head")

    async def record():
        async with real_client(session_database) as (client, _):
            body = import_body(underlying, binding)
            response = await client.post(URL + "/imports", json=body)
            assert response.status_code in (200, 201), response.text
            return response.json(), body

    original, body = asyncio.run(record())
    assert original["manifest_json"] == body["manifest_json"]
    assert original["document_base64"] == body["document_base64"]
    preserved = asyncio.run(state(session_database))
    with pytest.raises(AssertionError, match="immutable session evidence exists"):
        _migrate(session_database, PREVIOUS, action="downgrade")
    assert asyncio.run(state(session_database)) == preserved


def test_real_import_replay_cas_and_snapshot_reads_keep_exact_originals_and_no_other_writes(
    session_database,
    monkeypatch,
):
    _migrate(session_database, "head")
    snapshot_settings = []
    original_snapshot = api.read_snapshot

    @asynccontextmanager
    async def checked_snapshot(engine):
        async with original_snapshot(engine) as session:
            observed = (
                await session.execute(
                    text(
                        "SELECT current_setting('transaction_isolation'), "
                        "current_setting('transaction_read_only')"
                    )
                )
            ).one()
            snapshot_settings.append(tuple(observed))
            assert tuple(observed) == ("repeatable read", "on")
            yield session

    monkeypatch.setattr(api, "read_snapshot", checked_snapshot)

    async def exercise():
        async with real_client(session_database) as (client, _):
            _, underlying, binding = await seed_scope(client, session_database)
            before = await state(session_database)
            body = import_body(underlying, binding)
            first_reply = await client.post(URL + "/imports", json=body)
            assert first_reply.status_code in (200, 201), first_reply.text
            first = first_reply.json()
            first_time = datetime.fromisoformat(first["recorded_at"].replace("Z", "+00:00"))
            assert first["manifest_json"] == body["manifest_json"]
            assert first["document_base64"] == body["document_base64"]
            assert first["source"]["manifest_sha256"] == body["manifest_sha256"]
            assert first["source"]["document_sha256"] == body["document_sha256"]
            after_first = await state(session_database)
            assert {k: v for k, v in after_first.items() if k != "market_session_evidence"} == {
                k: v for k, v in before.items() if k != "market_session_evidence"
            }

            replay = await client.post(URL + "/imports", json=body)
            assert replay.status_code == first_reply.status_code, replay.text
            assert replay.json() == first
            assert await state(session_database) == after_first

            changed_key = {**body, "review_reference": "Different synthetic review statement"}
            conflict = await client.post(URL + "/imports", json=changed_key)
            assert conflict.status_code == 409, conflict.text
            assert conflict.json()["code"] == "SESSION_EVIDENCE_REQUEST_CONFLICT"

            current = await client.get(URL, params=read_query(underlying, binding))
            assert current.status_code == 200, current.text
            assert current.json()["status"] == "COMPLETE"
            assert current.json()["revision_id"] == first["id"]
            assert current.json()["operation_status"] == "READ_ONLY"
            earlier = await client.get(
                URL,
                params=read_query(
                    underlying,
                    binding,
                    known_at=(first_time - timedelta(microseconds=1)).isoformat(),
                ),
            )
            assert earlier.status_code == 200, earlier.text
            assert earlier.json()["status"] == "MISSING"
            assert earlier.json()["revision_id"] is None
            assert await state(session_database) == after_first

            replacement = json.loads(body["manifest_json"])
            replacement["calendar_version"] = "synthetic-v2"
            replacement["days"] = [
                *replacement["days"][:1],
                {
                    "session_date": "2026-11-11",
                    "status": "UNKNOWN",
                    "intervals": [],
                    "source_reference": "Synthetic original document / uncertain closure",
                },
            ]
            second_body = import_body(
                underlying,
                binding,
                value=replacement,
                supersedes_revision_id=UUID(first["id"]),
            )
            second_reply = await client.post(URL + "/imports", json=second_body)
            assert second_reply.status_code in (200, 201), second_reply.text
            second = second_reply.json()
            assert second["supersedes_revision_id"] == first["id"]
            after_second = await state(session_database)

            latest = await client.get(URL, params=read_query(underlying, binding))
            assert latest.status_code == 200, latest.text
            assert latest.json()["status"] == "INCOMPLETE"
            assert latest.json()["revision_id"] == second["id"]
            assert "2026-11-10" in latest.json()["missing_dates"]
            assert not any(d["session_date"] == "2026-11-10" for d in latest.json()["days"])
            assert latest.json()["days"][-1]["status"] == "UNKNOWN"
            historical = await client.get(
                URL, params=read_query(underlying, binding, known_at=first["recorded_at"])
            )
            assert historical.status_code == 200, historical.text
            assert historical.json()["status"] == "COMPLETE"
            assert historical.json()["revision_id"] == first["id"]
            assert await state(session_database) == after_second

            stale = {**second_body, "request_id": str(uuid4())}
            rejected = await client.post(URL + "/imports", json=stale)
            assert rejected.status_code == 409, rejected.text
            assert rejected.json()["code"] == "SESSION_EVIDENCE_REVISION_CONFLICT"
            assert await state(session_database) == after_second

        # A fresh application/database pool reads originals after restart, not an ORM cache.
        async with real_client(session_database) as (client, _):
            replay_after_revision = await client.post(URL + "/imports", json=body)
            assert replay_after_revision.status_code == first_reply.status_code
            assert replay_after_revision.json() == first
            original = await client.get(
                URL + f"/revisions/{first['id']}", params=read_query(underlying, binding)
            )
            assert original.status_code == 200, original.text
            assert original.json() == first
            assert await state(session_database) == after_second

    asyncio.run(exercise())
    assert len(snapshot_settings) == 5


async def raw_append(url, value):
    engine = engine_for(url)
    try:
        async with engine.begin() as connection:
            await connection.execute(insert(SessionEvidenceModel).values(**value))
    finally:
        await engine.dispose()


def clone_for_append(original, **changes):
    result = deepcopy(original)
    result.update(
        id=uuid4(),
        request_id=uuid4(),
        revision_number=original["revision_number"] + 1,
        supersedes_revision_id=original["id"],
        recorded_at=original["recorded_at"] + timedelta(seconds=1),
    )
    result.update(changes)
    return result


def rebind_row(original, **binding_changes):
    """Keep the hashes internally valid, leaving SQL ownership checks as the decisive guard."""
    value = clone_for_append(original)
    manifest = json.loads(value["manifest_json"])
    manifest["binding"].update({key: str(item) for key, item in binding_changes.items()})
    value["manifest_json"] = json.dumps(manifest, indent=2) + "\n"
    value["manifest_sha256"] = examples.digest(value["manifest_json"].encode())
    value["source"]["manifest_sha256"] = value["manifest_sha256"]
    for key in ("instrument_id", "listing_id", "trading_venue_id"):
        if key in binding_changes:
            value[key] = binding_changes[key]
    if "instrument_id" in binding_changes:
        value["underlying_id"] = binding_changes["instrument_id"]
    return value


def test_postgres_rejects_rewrites_truncate_forged_originals_and_cross_scope_revisions(
    session_database,
):
    _migrate(session_database, "head")

    async def exercise():
        async with real_client(session_database) as (client, _):
            _, underlying, binding = await seed_scope(client, session_database)
            response = await client.post(URL + "/imports", json=import_body(underlying, binding))
            assert response.status_code == 201, response.text
            original_id = UUID(response.json()["id"])
            foreign = await client.post(
                "/api/v1/underlyings",
                json={
                    "name": "Synthetic separate session instrument",
                    "type": "STOCK",
                    "primary_listing": {
                        "trading_venue_id": str(binding["trading_venue_id"]),
                        "ticker": "OTHERSESSIONS",
                        "currency_code": "EUR",
                    },
                },
            )
            assert foreign.status_code == 201, foreign.text
            foreign_instrument = UUID(foreign.json()["id"])
            foreign_rows = await sql(
                session_database,
                "SELECT id FROM listings "
                "WHERE workspace_id=:workspace AND underlying_id=:underlying",
                {"workspace": WORKSPACE, "underlying": foreign_instrument},
            )
            assert len(foreign_rows) == 1
            foreign_binding = {**binding, "listing_id": foreign_rows[0]["id"]}
            second = await client.post(
                URL + "/imports", json=import_body(foreign_instrument, foreign_binding)
            )
            assert second.status_code == 201, second.text
            foreign_revision = UUID(second.json()["id"])
            foreign_get = await client.get(
                URL + f"/revisions/{original_id}",
                params=read_query(foreign_instrument, foreign_binding),
            )
            assert foreign_get.status_code == 404, foreign_get.text

        before = await state(session_database)
        original = next(
            row for row in before["market_session_evidence"] if row["id"] == original_id
        )
        for statement in (
            "UPDATE market_session_evidence SET manifest_json=manifest_json WHERE id=:id",
            "DELETE FROM market_session_evidence WHERE id=:id",
            "TRUNCATE TABLE market_session_evidence",
        ):
            with pytest.raises(IntegrityError, match="append-only"):
                await sql(session_database, statement, {"id": original_id})
            assert await state(session_database) == before

        wrong_source = deepcopy(original["source"])
        wrong_source["recorded_by"] = str(uuid4())
        bad_rows = (
            clone_for_append(original, document_bytes=b"changed source bytes"),
            clone_for_append(original, manifest_json=original["manifest_json"] + " "),
            clone_for_append(original, source=wrong_source),
            clone_for_append(original, workspace_id=uuid4()),
            rebind_row(original, instrument_id=foreign_instrument),
            rebind_row(original, listing_id=foreign_binding["listing_id"]),
            rebind_row(original, trading_venue_id=uuid4()),
            clone_for_append(original, supersedes_revision_id=foreign_revision),
            clone_for_append(original, revision_number=3),
            clone_for_append(
                original, recorded_at=original["recorded_at"] - timedelta(microseconds=1)
            ),
        )
        for value in bad_rows:
            with pytest.raises(IntegrityError, match="Session evidence"):
                await raw_append(session_database, value)
            assert await state(session_database) == before

    asyncio.run(exercise())


def test_concurrent_replays_and_revisions_serialize_on_existing_instrument_owner(session_database):
    _migrate(session_database, "head")

    async def exercise():
        async with real_client(session_database) as (client, _):
            _, underlying, binding = await seed_scope(client, session_database)
            incoming = import_body(underlying, binding)
            replies = await asyncio.gather(
                *[client.post(URL + "/imports", json=incoming) for _ in range(3)]
            )
            assert [response.status_code for response in replies] == [201, 201, 201], [
                response.text for response in replies
            ]
            assert len({response.json()["id"] for response in replies}) == 1
            first = replies[0].json()
            before = await state(session_database)
            assert len(before["market_session_evidence"]) == 1
            commands = [
                import_body(
                    underlying,
                    binding,
                    value=examples.manifest(calendar_version=f"synthetic-contender-{number}"),
                    supersedes_revision_id=UUID(first["id"]),
                )
                for number in (1, 2)
            ]
            competing = await asyncio.gather(
                *[client.post(URL + "/imports", json=command) for command in commands]
            )
            assert sorted(response.status_code for response in competing) == [201, 409], [
                response.text for response in competing
            ]
            conflict = next(response for response in competing if response.status_code == 409)
            assert conflict.json()["code"] == "SESSION_EVIDENCE_REVISION_CONFLICT"
            after = await state(session_database)
            assert len(after["market_session_evidence"]) == 2
            assert {k: v for k, v in after.items() if k != "market_session_evidence"} == {
                k: v for k, v in before.items() if k != "market_session_evidence"
            }
            current = await client.get(URL, params=read_query(underlying, binding))
            assert current.status_code == 200, current.text
            winner = next(response.json() for response in competing if response.status_code == 201)
            assert current.json()["revision_id"] == winner["id"]
            assert current.json()["supersedes_revision_id"] == first["id"]
            assert current.json()["revision_number"] == 2

    asyncio.run(exercise())


def test_real_position_session_reader_counts_documented_twentieth_without_any_writes(
    session_database, monkeypatch
):
    _migrate(session_database, "head")
    original_snapshot = HebeltraderSessionReader._snapshot
    snapshots = []

    @asynccontextmanager
    async def checked_snapshot(reader):
        async with original_snapshot(reader) as session:
            settings = (
                await session.execute(
                    text(
                        "SELECT current_setting('transaction_isolation'), "
                        "current_setting('transaction_read_only')"
                    )
                )
            ).one()
            assert tuple(settings) == ("repeatable read", "on")
            snapshots.append(tuple(settings))
            yield session

    monkeypatch.setattr(HebeltraderSessionReader, "_snapshot", checked_snapshot)

    async def exercise():
        zone = ZoneInfo("Europe/Berlin")
        today = datetime.now(UTC).astimezone(zone).date()
        anchor = today - timedelta(days=40)
        while anchor.weekday() >= 5:
            anchor -= timedelta(days=1)
        # Explicit synthetic fixture rows, not production calendar generation.
        end = today + timedelta(days=1)
        days = []
        sessions_after_entry = []
        for offset in range((end - anchor).days + 1):
            day = anchor + timedelta(days=offset)
            session = day.weekday() < 5
            intervals = (
                [
                    {
                        "opens_at": datetime.combine(day, time(9), zone).isoformat(),
                        "closes_at": datetime.combine(day, time(17, 30), zone).isoformat(),
                    }
                ]
                if session
                else []
            )
            days.append(
                {
                    "session_date": day.isoformat(),
                    "status": "SESSION" if session else "CLOSED",
                    "intervals": intervals,
                    "source_reference": f"Synthetic complete original document / {day.isoformat()}",
                }
            )
            if session and day > anchor:
                sessions_after_entry.append(day)
        twentieth = sessions_after_entry[19]
        assert twentieth < today
        document = (
            "SYNTHETIC ORIGINAL SESSION DOCUMENT; no actual exchange or provider.\n"
            + json.dumps(days, indent=2)
        ).encode()

        async with real_client(session_database) as (client, _):
            data, underlying, binding = await seed_scope(
                client, session_database, purchased_on=anchor
            )
            value = examples.manifest(
                coverage_start=anchor.isoformat(),
                coverage_end=end.isoformat(),
                days=days,
                source_published_on=(anchor - timedelta(days=1)).isoformat(),
                source_document_sha256=examples.digest(document),
            )
            value["binding"].update(valid_from=anchor.isoformat(), valid_through=end.isoformat())
            imported = await client.post(
                URL + "/imports",
                json=import_body(
                    underlying,
                    binding,
                    value=value,
                    document_base64=base64.b64encode(document).decode(),
                    document_sha256=examples.digest(document),
                ),
            )
            assert imported.status_code == 201, imported.text
            before = await state(session_database)
            path = (
                "/api/v1/position-monitoring/trades/"
                + data["trade"]["id"]
                + "/hebeltrader-sessions"
            )
            for _ in range(2):
                response = await client.get(path, params={"position_id": data["position"]["id"]})
                assert response.status_code == 200, response.text
                report = response.json()
                assert report["entry"]["execution_id"] == data["execution"]["id"]
                assert report["entry"]["time_precision"] == "DATE_ONLY"
                assert report["entry"]["executed_at"] is None
                assert report["count"]["anchor_date"] == anchor.isoformat()
                assert report["count"]["status"] == "AVAILABLE"
                assert report["count"]["threshold_reached"] is True
                assert report["count"]["completed_sessions"] >= 20
                assert report["count"]["twentieth_session_date"] == twentieth.isoformat()
                assert report["calendar"]["revision_id"] == imported.json()["id"]
                assert report["period"]["status"] == "COMPLETE"
                assert report["read_status"] == "READ_ONLY"
                assert report["operation_status"] == "NOT_ACTIVATED"
                assert report["rule_evaluation_status"] == "B04_B05_B06_B58_NOT_EVALUATED"
                assert await state(session_database) == before
            foreign = await client.get(path, params={"position_id": str(uuid4())})
            assert foreign.status_code == 404, foreign.text
            assert await state(session_database) == before

    asyncio.run(exercise())
    assert len(snapshots) == 3
