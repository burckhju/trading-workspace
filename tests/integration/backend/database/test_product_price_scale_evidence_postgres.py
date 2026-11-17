"""Actual document imports and execution-owner reads in guarded disposable PostgreSQL.

Original document bytes, revision guards and passive monitoring are exercised
through production routes. All executions are synthetic real owner commands;
the test creates no scheduler, live provider request or delivery.
"""

import asyncio
import base64
import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import httpx
import pytest
from pydantic import TypeAdapter
from sqlalchemy import insert, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from tests.integration.backend.database.test_saved_quote_evidence_postgres import (
    RESULT,
    calendar_import,
    quote_result,
)
from tests.integration.backend.learning.test_journal_write_postgres import (
    journal_database as guarded_database,
)
from tests.integration.backend.test_realized_gross_report_postgres import (
    DECLARATION,
    _client,
    _state,
)
from tests.integration.backend.test_trade_capture_safety import (
    BASE,
    WORKSPACE,
    purchase,
    sql,
)
from tests.integration.backend.test_usd_chf_currency_references import (
    _migrate,
    _product_payload,
)

from app.core.exceptions import ApplicationError
from app.features.market_data.domain.enums import MappingStatus, MarketDataProvider
from app.features.market_data.persistence.models import (
    WarrantProviderMappingModel,
    WarrantQuoteObservationModel,
)
from app.features.market_data.persistence.position_quote_source import (
    PositionQuoteSourceSelectionRepository,
)
from app.features.market_data.service.position_quote_source import (
    PositionQuoteSourceSelector,
)
from app.features.position_monitoring.service import (
    hebeltrader_original_bid as monitoring,
)
from app.features.product.domain.price_scale_evidence import ProductPriceScaleImportCommand
from app.features.product.persistence.models import WarrantModel
from app.features.product.persistence.price_scale_evidence import (
    ProductPriceScaleEvidenceModel,
    request_fingerprint,
)
from app.features.product.service.price_scale_evidence import ProductPriceScaleEvidenceReader

TABLE = "product_price_scale_evidence"
PREVIOUS = "20261115_0052"
CONFIRMATION = "CONFIRM_PRODUCT_PRICE_SCALE_DOCUMENT_REVIEW"


@pytest.fixture
def price_scale_database():
    # The shared guard permits only the designated parent and a generated UUID DB.
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


async def seed_scope(client):
    payload = await _product_payload(client)
    payload["isin"] = "DE000AB00001"
    response = await client.post("/api/v1/warrants", json=payload)
    assert response.status_code == 201, response.text
    product = response.json()
    warrant = product["id"]
    response = await client.post(
        "/api/v1/warrants",
        json={
            **payload,
            "isin": "DE000CD00001",
            "display_name": "Synthetic foreign price scale instrument",
        },
    )
    assert response.status_code == 201, response.text
    foreign_warrant = response.json()["id"]
    response = await client.get(f"/api/v1/warrants/{warrant}/terms")
    assert response.status_code == 200, response.text
    terms = max(response.json(), key=lambda item: item["version_no"])
    response = await client.get("/api/v1/market-reference-data/trading-venues")
    assert response.status_code == 200, response.text
    venue = next((row for row in response.json()["items"] if row["mic"] == "XFRA"), None)
    if venue is None:
        response = await client.post(
            "/api/v1/market-reference-data/trading-venues",
            json={
                "mic": "XFRA",
                "name": "Synthetic product scale fixture venue",
                "country_code": "DE",
                "timezone": "Europe/Berlin",
            },
        )
        assert response.status_code == 201, response.text
        venue = response.json()
    response = await client.post(
        f"/api/v1/warrants/{warrant}/listings",
        json={"trading_venue_id": venue["id"], "quotation_currency_code": "EUR"},
    )
    assert response.status_code == 201, response.text
    listing = response.json()
    anchor = datetime.now(UTC).astimezone(ZoneInfo("Europe/Berlin")).date() - timedelta(days=40)
    response = await client.post(
        BASE + "/purchases/external",
        json={
            **purchase(warrant, day=anchor.isoformat(), quantity=100),
            "price_per_unit": "2.00",
            "currency_confirmation": DECLARATION,
        },
    )
    assert response.status_code == 201, response.text
    return {
        "product": product,
        "foreign_warrant": foreign_warrant,
        "terms": terms,
        "listing": listing,
        "venue": venue,
        "anchor": anchor,
        "capture": response.json(),
    }


def import_body(scope, *, supersedes=None, status="UNCHANGED_ORIGINAL", version="synthetic-v1"):
    product = scope["product"]
    binding = {
        "warrant_id": product["id"],
        "isin": product["isin"],
        "issuer_id": product["issuer_id"],
        "underlying_id": product["underlying_id"],
        "current_terms_id": scope["terms"]["id"],
    }
    zone = ZoneInfo("Europe/Berlin")
    valid_from = datetime.combine(scope["anchor"], time.min, zone)
    valid_until = datetime.now(UTC) + timedelta(days=1)
    source = {
        "synthetic_original_source": True,
        "binding": binding,
        "axis": "WARRANT",
        "currency": "EUR",
        "unit": "CURRENCY_PER_WARRANT",
        "valid_from": valid_from.isoformat(),
        "valid_until": valid_until.isoformat(),
        "status": status,
        "source_version": version,
    }
    document = (json.dumps(source, indent=2) + "\n").encode()
    document_hash = hashlib.sha256(document).hexdigest()
    manifest = (
        json.dumps(
            {
                **{
                    key: value
                    for key, value in source.items()
                    if key != "synthetic_original_source"
                },
                "schema_version": "product-price-scale-evidence-v1",
                "scale_id": "synthetic-eur-per-warrant-original",
                "source_publisher": "Synthetic document author; no real issuer assertion",
                "source_reference": "https://example.invalid/synthetic-product-price-scale",
                "source_document_sha256": document_hash,
                "source_published_on": scope["anchor"].isoformat(),
            },
            indent=2,
        )
        + "\n"
    )
    return {
        "request_id": str(uuid4()),
        "supersedes_revision_id": supersedes,
        "manifest_json": manifest,
        "manifest_sha256": hashlib.sha256(manifest.encode()).hexdigest(),
        "document_filename": "synthetic-original-product-price-scale.json",
        "document_media_type": "application/json",
        "document_base64": base64.b64encode(document).decode(),
        "document_sha256": document_hash,
        "reviewed_at": (datetime.now(UTC) - timedelta(seconds=1)).isoformat(),
        "review_reference": "Explicit synthetic review of original price units and period",
        "retrieved_at": (datetime.now(UTC) - timedelta(seconds=2)).isoformat(),
        "confirmation": CONFIRMATION,
    }


def scale_url(scope):
    return f"/api/v1/warrants/{scope['product']['id']}/price-scale-evidence"


def append_row(original, **changes):
    row = deepcopy(original)
    row.update(
        id=uuid4(),
        request_id=uuid4(),
        revision_number=2,
        supersedes_revision_id=original["id"],
        recorded_at=datetime.now(UTC),
    )
    row.update(changes)
    command = TypeAdapter(ProductPriceScaleImportCommand).validate_python(
        {
            "request_id": row["request_id"],
            "supersedes_revision_id": row["supersedes_revision_id"],
            "manifest_json": row["manifest_json"],
            "manifest_sha256": row["manifest_sha256"],
            "document_filename": row["source"]["document_filename"],
            "document_media_type": row["source"]["document_media_type"],
            "document_base64": base64.b64encode(row["document_bytes"]).decode(),
            "document_sha256": row["document_sha256"],
            "reviewed_at": row["source"]["reviewed_at"],
            "review_reference": row["source"]["review_reference"],
            "retrieved_at": row["source"]["retrieved_at"],
        }
    )
    # Keep request identity valid so malformed originals/scopes are decisive.
    row["request_fingerprint"] = request_fingerprint(
        command, row["workspace_id"], row["recorded_by"]
    )
    return row


async def store_quote_and_calendars(client, database, scope):
    sessions = async_sessionmaker(database.engine, expire_on_commit=False)
    position = UUID(scope["capture"]["position"]["id"])
    product = UUID(scope["product"]["id"])
    listing = UUID(scope["listing"]["id"])
    now = datetime.now(UTC)
    async with sessions() as session:
        await session.execute(
            insert(WarrantProviderMappingModel).values(
                id=uuid4(),
                workspace_id=UUID(WORKSPACE),
                warrant_listing_id=listing,
                provider=MarketDataProvider.FRANKFURT_QUOTES,
                provider_symbol=scope["product"]["isin"],
                provider_exchange_code="XFRA",
                status=MappingStatus.ACTIVE,
                validated_at=now,
                version=1,
                created_at=now,
                updated_at=now,
            )
        )
        await session.commit()
        selector = PositionQuoteSourceSelector(
            PositionQuoteSourceSelectionRepository(session),
            (MarketDataProvider.FRANKFURT_QUOTES,),
        )
        selected = (
            await selector.reconcile(
                workspace_id=UUID(WORKSPACE),
                position_id=position,
                warrant_id=product,
                selected_at=datetime.now(UTC),
            )
        ).selection
        assert selected is not None and selected.selection_status == "SELECTED"
        await session.commit()
        original = quote_result(listing, datetime.now(UTC))
        session.add(
            WarrantQuoteObservationModel(
                workspace_id=UUID(WORKSPACE),
                warrant_listing_id=listing,
                provider=MarketDataProvider.FRANKFURT_QUOTES.value,
                identity_key=selected.identity_key,
                payload=RESULT.dump_python(original, mode="json"),
            )
        )
        await session.commit()
    async with database.engine.connect() as connection:
        underlying_listing = (
            (
                await connection.execute(
                    text(
                        "SELECT l.id, l.trading_venue_id, v.mic, v.timezone FROM listings l "
                        "JOIN trading_venues v ON v.id=l.trading_venue_id "
                        "WHERE l.workspace_id=:workspace AND l.underlying_id=:underlying "
                        "AND l.is_primary"
                    ),
                    {
                        "workspace": UUID(WORKSPACE),
                        "underlying": UUID(scope["product"]["underlying_id"]),
                    },
                )
            )
            .mappings()
            .one()
        )
    local_day = datetime.now(UTC).astimezone(ZoneInfo("Europe/Berlin")).date()
    for kind, instrument, listing_id, venue_id, mic, zone, start in (
        (
            "WARRANT",
            product,
            listing,
            scope["venue"]["id"],
            scope["venue"]["mic"],
            scope["venue"]["timezone"],
            local_day - timedelta(days=2),
        ),
        (
            "UNDERLYING",
            scope["product"]["underlying_id"],
            underlying_listing["id"],
            underlying_listing["trading_venue_id"],
            underlying_listing["mic"],
            underlying_listing["timezone"],
            scope["anchor"],
        ),
    ):
        body = calendar_import(
            kind=kind,
            instrument_id=instrument,
            listing_id=listing_id,
            venue_id=venue_id,
            mic=mic,
            zone=zone,
            anchor=scope["anchor"],
            start=start,
            end=local_day + timedelta(days=1),
        )
        response = await client.post("/api/v1/market-data/session-evidence/imports", json=body)
        assert response.status_code == 201, response.text


def test_migration_preserves_owner_rows_and_original_evidence_prevents_destructive_downgrade(
    price_scale_database,
):
    _migrate(price_scale_database, PREVIOUS)

    async def prepare():
        async with _client(price_scale_database) as (client, _):
            return await seed_scope(client)

    scope = asyncio.run(prepare())
    before = asyncio.run(state(price_scale_database))
    _migrate(price_scale_database, "head")
    migrated = asyncio.run(state(price_scale_database))
    assert migrated[TABLE] == []
    assert {key: migrated[key] for key in before if key != "alembic_version"} == {
        key: value for key, value in before.items() if key != "alembic_version"
    }
    _migrate(price_scale_database, PREVIOUS, action="downgrade")
    assert TABLE not in asyncio.run(state(price_scale_database))
    _migrate(price_scale_database, "head")

    async def record():
        async with _client(price_scale_database) as (client, _):
            body = import_body(scope)
            response = await client.post(scale_url(scope) + "/imports", json=body)
            assert response.status_code == 201, response.text
            original = response.json()
            assert original["manifest_json"] == body["manifest_json"]
            assert original["document_base64"] == body["document_base64"]
            return original

    original = asyncio.run(record())
    preserved = asyncio.run(state(price_scale_database))
    with pytest.raises(AssertionError, match="immutable product price scale evidence exists"):
        _migrate(price_scale_database, PREVIOUS, action="downgrade")
    assert asyncio.run(state(price_scale_database)) == preserved

    async def protect():
        for statement in (
            f"UPDATE {TABLE} SET manifest_json=manifest_json WHERE id=:id",
            f"DELETE FROM {TABLE} WHERE id=:id",
            f"TRUNCATE TABLE {TABLE}",
        ):
            with pytest.raises(IntegrityError, match="append-only"):
                await sql(price_scale_database, statement, {"id": original["id"]})
            assert await state(price_scale_database) == preserved

        original_row = preserved[TABLE][0]
        # Raw inserts exercise PostgreSQL guards independently of API validation.
        invalid_rows = (
            {"document_bytes": b"forged synthetic original bytes"},
            {"manifest_json": original_row["manifest_json"] + " "},
            {"workspace_id": uuid4()},
            {"terms_id": uuid4()},
            {"supersedes_revision_id": uuid4()},
            {"revision_number": 3},
            {"recorded_at": original_row["recorded_at"] - timedelta(microseconds=1)},
        )
        for changes in invalid_rows:
            row = append_row(original_row, **changes)
            engine = engine_for(price_scale_database)
            try:
                with pytest.raises(IntegrityError):
                    async with engine.begin() as connection:
                        await connection.execute(
                            insert(ProductPriceScaleEvidenceModel).values(**row)
                        )
            finally:
                await engine.dispose()
            assert await state(price_scale_database) == preserved
        # Positive control: the otherwise same append shape is valid and readable.
        valid = append_row(original_row)
        engine = engine_for(price_scale_database)
        try:
            async with engine.begin() as connection:
                await connection.execute(insert(ProductPriceScaleEvidenceModel).values(**valid))
        finally:
            await engine.dispose()
        after_append = await state(price_scale_database)
        assert len(after_append[TABLE]) == 2
        assert {key: rows for key, rows in after_append.items() if key != TABLE} == {
            key: rows for key, rows in preserved.items() if key != TABLE
        }
        async with _client(price_scale_database) as (client, _):
            current = await client.get(scale_url(scope) + "/current")
            assert current.status_code == 200, current.text
            assert current.json()["status"] == "AVAILABLE"
            assert current.json()["revision_id"] == str(valid["id"])

            # An otherwise deletable product has no trade/execution FK to mask this guard.
            foreign = await client.get(f"/api/v1/warrants/{scope['foreign_warrant']}")
            assert foreign.status_code == 200, foreign.text
            foreign_product = foreign.json()
            terms = await client.get(f"/api/v1/warrants/{scope['foreign_warrant']}/terms")
            assert terms.status_code == 200, terms.text
            foreign_scope = {
                **scope,
                "product": foreign_product,
                "terms": max(terms.json(), key=lambda row: row["version_no"]),
            }
            listed = await client.post(
                f"/api/v1/warrants/{scope['foreign_warrant']}/listings",
                json={
                    "trading_venue_id": scope["venue"]["id"],
                    "quotation_currency_code": "EUR",
                },
            )
            assert listed.status_code == 201, listed.text
            imported = await client.post(
                scale_url(foreign_scope) + "/imports", json=import_body(foreign_scope)
            )
            assert imported.status_code == 201, imported.text
            before_delete = await state(price_scale_database)
            foreign_id = UUID(scope["foreign_warrant"])
            assert not any(
                row["product_id"] == foreign_id for row in before_delete["execution_records"]
            )
            assert not any(row["product_id"] == foreign_id for row in before_delete["trades"])
            deleted = await client.delete(
                f"/api/v1/warrants/{scope['foreign_warrant']}",
                params={"version": foreign_product["version"]},
            )
            assert deleted.status_code == 409, deleted.text
            assert deleted.json()["code"] == "WARRANT_DELETE_BLOCKED"
            # Listing deletion precedes the terms FK failure; the full transaction rolls back.
            assert await state(price_scale_database) == before_delete
            retained_original = await client.get(
                scale_url(foreign_scope) + f"/revisions/{imported.json()['id']}"
            )
            assert retained_original.status_code == 200, retained_original.text
            assert retained_original.json() == imported.json()

    asyncio.run(protect())


async def read_report(client, scope):
    trade = scope["capture"]["trade"]["id"]
    position = scope["capture"]["position"]["id"]
    response = await client.get(
        f"/api/v1/position-monitoring/trades/{trade}/hebeltrader-original-bid",
        params={"position_id": position},
    )
    assert response.status_code == 200, response.text
    report = response.json()
    assert report["read_status"] == "READ_ONLY"
    assert report["operation_status"] == "NOT_ACTIVATED"
    assert report["rule_evaluation_status"] == "B04_B05_B06_B58_NOT_EVALUATED"
    assert report["implementation_status"] == "F207_3_MARKET_STATUS_EVIDENCE_ONLY"
    assert report["product_price_scale"]["adjustment_applied"] is False
    assert (
        report["product_price_scale"]["execution_basis_id"] == report["economic_basis"]["basis_id"]
    )
    return report


def test_real_import_replay_correction_restart_and_withdrawal_preserve_owner_facts(
    price_scale_database,
    monkeypatch,
):
    _migrate(price_scale_database, "head")
    owner_read = monitoring.read_hebeltrader_monitoring_basis
    snapshots = []

    async def checked_owner(session, **scope):
        assert await session.scalar(text("SHOW transaction_read_only")) == "on"
        assert await session.scalar(text("SHOW transaction_isolation")) == "repeatable read"
        snapshots.append(session)
        return await owner_read(session, **scope)

    monkeypatch.setattr(monitoring, "read_hebeltrader_monitoring_basis", checked_owner)

    async def exercise():
        async with _client(price_scale_database) as (client, database):
            scope = await seed_scope(client)
            await store_quote_and_calendars(client, database, scope)
            trade = scope["capture"]["trade"]["id"]
            initial_buy = scope["capture"]["execution"]["id"]
            ids = [initial_buy]
            for action, quantity, price, offset in (
                ("sales", 40, "3.00", 5),
                ("purchases", 40, "4.00", 10),
            ):
                response = await client.post(
                    f"{BASE}/trades/{trade}/{action}",
                    json={
                        "quantity": quantity,
                        "price_per_unit": price,
                        "executed_on": (scope["anchor"] + timedelta(days=offset)).isoformat(),
                        "execution_timezone": "Europe/Berlin",
                        "request_id": str(uuid4()),
                        "currency_confirmation": DECLARATION,
                    },
                )
                assert response.status_code == 201, response.text
                ids.append(response.json()["execution"]["id"])
            baseline = await _state(database.engine)
            before = await read_report(client, scope)
            assert before["product_price_scale"]["status"] == "MISSING"
            assert before["economic_basis"]["position"]["open_quantity"] == 100
            assert Decimal(before["economic_basis"]["position"]["cost_basis"]) == 280
            assert Decimal(before["economic_basis"]["position"]["average_entry_price"]) == Decimal(
                "2.8"
            )
            assert before["economic_basis"]["effective_execution_ids"] == ids
            assert await _state(database.engine) == baseline

            body = import_body(scope)
            initial_replies = await asyncio.gather(
                *[client.post(scale_url(scope) + "/imports", json=body) for _ in range(3)]
            )
            assert [reply.status_code for reply in initial_replies] == [201, 201, 201], [
                reply.text for reply in initial_replies
            ]
            first = initial_replies[0].json()
            assert all(reply.json() == first for reply in initial_replies)
            assert first["manifest_json"] == body["manifest_json"]
            assert first["document_base64"] == body["document_base64"]
            assert first["source"]["manifest_sha256"] == body["manifest_sha256"]
            assert first["source"]["document_sha256"] == body["document_sha256"]
            assert first["verification"] == "MANUAL_DOCUMENT_REVIEW_NOT_INDEPENDENT_VERIFICATION"
            after_import = await _state(database.engine)
            assert {key: rows for key, rows in after_import.items() if key != TABLE} == {
                key: rows for key, rows in baseline.items() if key != TABLE
            }

            # Actual concurrent retries serialize without appending duplicate evidence.
            replays = await asyncio.gather(
                *[client.post(scale_url(scope) + "/imports", json=body) for _ in range(3)]
            )
            assert [reply.status_code for reply in replays] == [201, 201, 201]
            assert all(reply.json() == first for reply in replays)
            changed = await client.post(
                scale_url(scope) + "/imports",
                json={
                    **body,
                    "review_reference": "Changed synthetic review on reused key",
                },
            )
            assert changed.status_code == 409, changed.text
            assert changed.json()["code"] == "PRODUCT_PRICE_SCALE_REQUEST_CONFLICT"
            stale = await client.post(
                scale_url(scope) + "/imports", json={**body, "request_id": str(uuid4())}
            )
            assert stale.status_code == 409, stale.text
            assert stale.json()["code"] == "PRODUCT_PRICE_SCALE_REVISION_CONFLICT"

            current = await client.get(scale_url(scope) + "/current")
            assert current.status_code == 200, current.text
            assert current.json()["status"] == "AVAILABLE"
            assert current.json()["revision_id"] == first["id"]
            assert current.json()["operation_status"] == "READ_ONLY"
            foreign_path = f"/api/v1/warrants/{scope['foreign_warrant']}/price-scale-evidence"
            foreign_original = await client.get(foreign_path + f"/revisions/{first['id']}")
            assert foreign_original.status_code == 404, foreign_original.text
            foreign_import = await client.post(foreign_path + "/imports", json=body)
            assert foreign_import.status_code == 422, foreign_import.text
            assert foreign_import.json()["code"] == "PRODUCT_PRICE_SCALE_BINDING_MISMATCH"
            foreign_current = await client.get(foreign_path + "/current")
            assert foreign_current.status_code == 200, foreign_current.text
            assert foreign_current.json()["status"] == "MISSING"
            historical_parameter = await client.get(
                scale_url(scope) + "/current", params={"known_at": first["recorded_at"]}
            )
            assert historical_parameter.status_code == 422, historical_parameter.text

            documented = await read_report(client, scope)
            assessment = documented["product_price_scale"]
            assert assessment["status"] == "DOCUMENTED"
            assert assessment["bid_status"] == "COVERED"
            assert assessment["evidence"]["revision_id"] == first["id"]
            assert assessment["execution_basis_id"] == before["economic_basis"]["basis_id"]
            contributions = assessment["purchases"]
            assert [item["execution_id"] for item in contributions] == [ids[0], ids[2]]
            assert [Decimal(item["remaining_quantity"]) for item in contributions] == [
                60,
                40,
            ]
            assert [item["original_quantity"] for item in contributions] == [100, 40]
            assert all(item["status"] == "COVERED" for item in contributions)
            assert all(item["executed_at"] is None for item in contributions)
            assert all(item["executed_on"] is not None for item in contributions)
            assert all(item["possible_from"] and item["possible_until"] for item in contributions)
            assert documented["economic_basis"] == before["economic_basis"]
            checks = {item["key"]: item["status"] for item in documented["checks"]}
            assert len(checks) == 8 and checks["PRICE_SCALE"] == "SATISFIED"
            assert checks["VERIFIED_LIVE_MARKET_STATUS"] == "MISSING"
            assert sum(value == "SATISFIED" for value in checks.values()) == 7
            assert documented["coverage_status"] == "PARTIAL"
            assert await _state(database.engine) == after_import

            correction = await client.post(
                f"{BASE}/trades/{trade}/executions/{initial_buy}/corrections",
                json={
                    "side": "BUY",
                    "quantity": 100,
                    "price_per_unit": "3.00",
                    "executed_on": scope["anchor"].isoformat(),
                    "execution_timezone": "Europe/Berlin",
                    "currency_confirmation": DECLARATION,
                },
            )
            assert correction.status_code == 201, correction.text
            corrected_id = correction.json()["execution"]["id"]
            after_correction = await _state(database.engine)
            corrected = await read_report(client, scope)
            economic = corrected["economic_basis"]
            assert economic["effective_execution_ids"] == [corrected_id, ids[1], ids[2]]
            assert economic["basis_id"] != before["economic_basis"]["basis_id"]
            assert economic["cost_basis_currency"] == "EUR"
            assert economic["position"]["open_quantity"] == 100
            assert Decimal(economic["position"]["cost_basis"]) == 340
            assert Decimal(economic["position"]["average_entry_price"]) == Decimal("3.4")
            assert corrected["product_price_scale"]["status"] == "DOCUMENTED"
            assert corrected["product_price_scale"]["evidence"]["revision_id"] == first["id"]
            replacement_buy = corrected["product_price_scale"]["purchases"][0]
            assert replacement_buy["execution_id"] == corrected_id
            assert replacement_buy["supersedes_execution_id"] == initial_buy
            assert Decimal(replacement_buy["price_per_unit"]) == 3
            assert Decimal(replacement_buy["remaining_quantity"]) == 60
            assert len(after_correction["execution_records"]) == 4
            assert len(after_correction[TABLE]) == 1
            assert await _state(database.engine) == after_correction

            # An explicitly documented adjustment never becomes a guessed scale factor.
            replacement = import_body(
                scope,
                supersedes=first["id"],
                status="ADJUSTMENT_REQUIRED",
                version="synthetic-v2",
            )
            response = await client.post(scale_url(scope) + "/imports", json=replacement)
            assert response.status_code == 201, response.text
            second = response.json()
            assert second["supersedes_revision_id"] == first["id"]
            after_second = await _state(database.engine)
            unavailable = await read_report(client, scope)
            assert unavailable["product_price_scale"]["status"] == "UNSUITABLE"
            assert unavailable["product_price_scale"]["evidence"]["revision_id"] == second["id"]
            assert unavailable["economic_basis"] == economic
            assert all(
                item["status"] == "UNSUITABLE"
                for item in unavailable["product_price_scale"]["purchases"]
            )
            assert await _state(database.engine) == after_second

            withdrawn_body = import_body(
                scope,
                supersedes=second["id"],
                status="WITHDRAWN",
                version="synthetic-v3",
            )
            response = await client.post(scale_url(scope) + "/imports", json=withdrawn_body)
            assert response.status_code == 201, response.text
            third = response.json()
            final_state = await _state(database.engine)
            withdrawn = await read_report(client, scope)
            assert withdrawn["product_price_scale"]["status"] == "UNSUITABLE"
            assert withdrawn["product_price_scale"]["evidence"]["revision_id"] == third["id"]
            assert withdrawn["economic_basis"] == economic
            assert len(final_state[TABLE]) == 3
            assert await _state(database.engine) == final_state

        # New application/pool proves original history and replay survive restart.
        async with _client(price_scale_database) as (client, database):
            replay = await client.post(scale_url(scope) + "/imports", json=body)
            assert replay.status_code == 201, replay.text
            assert replay.json() == first
            original = await client.get(scale_url(scope) + f"/revisions/{first['id']}")
            assert original.status_code == 200, original.text
            assert original.json() == first
            current = await client.get(scale_url(scope) + "/current")
            assert current.status_code == 200, current.text
            assert current.json()["revision_id"] == third["id"]
            assert current.json()["status"] == "UNSUITABLE"
            stale = await client.post(
                scale_url(scope) + "/imports",
                json={**replacement, "request_id": str(uuid4())},
            )
            assert stale.status_code == 409, stale.text
            assert stale.json()["code"] == "PRODUCT_PRICE_SCALE_REVISION_CONFLICT"
            for suffix in ("current", f"revisions/{first['id']}"):
                foreign = await client.get(
                    f"/api/v1/warrants/{uuid4()}/price-scale-evidence/{suffix}"
                )
                assert foreign.status_code == 404, foreign.text
            foreign_position = await client.get(
                f"/api/v1/position-monitoring/trades/{trade}/hebeltrader-original-bid",
                params={"position_id": str(uuid4())},
            )
            assert foreign_position.status_code == 404, foreign_position.text

            # A foreign workspace cannot obtain even this existing product's evidence.
            sessions = async_sessionmaker(database.engine, expire_on_commit=False)
            async with sessions() as session:
                await session.execute(
                    text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                )
                reader = ProductPriceScaleEvidenceReader(session)
                with pytest.raises(ApplicationError) as rejected:
                    await reader.current(
                        workspace_id=uuid4(),
                        warrant_id=UUID(scope["product"]["id"]),
                        known_at=datetime.now(UTC),
                    )
                assert rejected.value.status_code == 404
                await session.rollback()
            async with sessions() as session:
                await session.execute(
                    text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                )
                product = await session.scalar(
                    select(WarrantModel).where(WarrantModel.id == UUID(scope["product"]["id"]))
                )
                product.display_name = "Synthetic unflushed edit must remain local"
                assert product in session.dirty
                reader = ProductPriceScaleEvidenceReader(session)
                restored = await reader.current(
                    workspace_id=UUID(WORKSPACE),
                    warrant_id=UUID(scope["product"]["id"]),
                    known_at=datetime.now(UTC),
                )
                assert str(restored.revision_id) == third["id"]
                assert product in session.dirty
                earlier = await reader.current(
                    workspace_id=UUID(WORKSPACE),
                    warrant_id=UUID(scope["product"]["id"]),
                    known_at=datetime.fromisoformat(first["recorded_at"].replace("Z", "+00:00")),
                )
                assert str(earlier.revision_id) == first["id"]
                assert earlier.status == "AVAILABLE"
                await session.rollback()
            assert await _state(database.engine) == final_state

            # Current terms invalidate an old binding without rewriting its originals.
            terms = scope["terms"]
            amended = await client.post(
                f"/api/v1/warrants/{scope['product']['id']}/terms",
                json={
                    "expected_version": scope["product"]["version"],
                    "option_direction": terms["option_direction"],
                    "strike": terms["strike"],
                    "strike_currency_code": terms["strike_currency_code"],
                    "maturity_date": terms["maturity_date"],
                    "ratio": "0.2",
                },
            )
            assert amended.status_code == 201, amended.text
            after_terms = await _state(database.engine)
            assert after_terms[TABLE] == final_state[TABLE]
            current = await client.get(scale_url(scope) + "/current")
            assert current.status_code == 200, current.text
            assert "PRODUCT_PRICE_SCALE_BINDING_CHANGED" in current.json()["reasons"]
            assert current.json()["binding"]["current_terms_id"] == terms["id"]
            historical = await client.get(scale_url(scope) + f"/revisions/{first['id']}")
            assert historical.status_code == 200, historical.text
            assert historical.json() == first
            after_binding = await read_report(client, scope)
            assert after_binding["product_price_scale"]["status"] == "UNSUITABLE"
            assert after_binding["economic_basis"] == economic
            assert await _state(database.engine) == after_terms

    asyncio.run(exercise())
    assert len(snapshots) == 7
