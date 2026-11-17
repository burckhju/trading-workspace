"""Actual scoped last-success reads in an identified, synthetic disposable DB."""

import asyncio
import base64
import hashlib
import json
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import httpx
import pytest
from pydantic import TypeAdapter
from sqlalchemy import insert, select, text, update
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from tests.integration.backend.learning.test_journal_write_postgres import (
    journal_database as guarded_database,
)
from tests.integration.backend.test_realized_gross_report_postgres import (
    DECLARATION,
    _client,
    _state,
)
from tests.integration.backend.test_trade_capture_safety import BASE, WORKSPACE, purchase
from tests.integration.backend.test_usd_chf_currency_references import _migrate, _product_payload

from app.features.market_data.domain.enums import (
    CacheStatus,
    MappingStatus,
    MarketDataCapability,
    MarketDataProvider,
    QualityStatus,
)
from app.features.market_data.domain.models import WarrantQuoteSnapshot
from app.features.market_data.domain.original_market_status_evidence import (
    OriginalMarketStatusEvidence,
)
from app.features.market_data.domain.original_quote_evidence import (
    OriginalQuoteEvidence,
    OriginalQuoteSideEvidence,
)
from app.features.market_data.domain.session_evidence import SessionEvidenceImportCommand
from app.features.market_data.persistence.models import (
    WarrantProviderMappingModel,
    WarrantQuoteObservationModel,
)
from app.features.market_data.persistence.position_quote_source import (
    PositionQuoteSourceSelectionRepository,
)
from app.features.market_data.service.position_quote_source import PositionQuoteSourceSelector
from app.features.market_data.service.retained_quotes import RetainedWarrantQuoteProvider
from app.features.market_data.service.risk_read import RiskMarketDataReader
from app.features.market_data.service.types import MarketDataResult, WarrantQuoteRequest
from app.features.position_monitoring.service import hebeltrader_original_bid as monitoring
from app.features.product.persistence.models import WarrantModel

RESULT = TypeAdapter(MarketDataResult[WarrantQuoteSnapshot | None])


@pytest.fixture
def quote_database():
    # Checks exact parent name, then creates/drops only a generated UUID database.
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


def quote_result(listing, now):
    bid_at, ask_at = now - timedelta(seconds=60), now - timedelta(seconds=120)
    evidence = OriginalQuoteEvidence(
        version="original-quote-evidence-v1",
        source_contract="frankfurt-quotes-v1",
        source_reference="Synthetic imported snapshot for PostgreSQL test",
        generated_at=now - timedelta(seconds=5),
        isin="DE000AB00001",
        currency="EUR",
        venue_mic="XFRA",
        bid=OriginalQuoteSideEvidence(Decimal("2.1"), bid_at, bid_at.isoformat(), "bid_at"),
        ask=OriginalQuoteSideEvidence(Decimal("2.2"), ask_at, ask_at.isoformat(), "ask_at"),
    )
    return MarketDataResult(
        WarrantQuoteSnapshot(
            listing,
            Decimal("2.1"),
            Decimal("2.2"),
            "EUR",
            evidence.isin,
            "XFRA",
            ask_at,
            isin=evidence.isin,
            venue_mic=evidence.venue_mic,
            source_mode="FRANKFURT_REALTIME_MONITORING",
            trading_status="OPEN",
            original_evidence=evidence,
        ),
        MarketDataProvider.FRANKFURT_QUOTES,
        MarketDataCapability.WARRANT_LISTING_QUOTE,
        uuid4(),
        now,
        CacheStatus.MISS,
        QualityStatus.VALID,
        ("Synthetic original-source warning",),
        0,
        0,
    )


def calendar_import(*, kind, instrument_id, listing_id, venue_id, mic, zone, anchor, start, end):
    """Complete synthetic source bytes describe every explicit calendar row."""
    days = []
    day = start
    timezone = ZoneInfo(zone)
    while day <= end:
        session = kind == "WARRANT" or 1 <= (day - anchor).days <= 20
        opening = datetime.combine(day, time.min if kind == "WARRANT" else time(9), timezone)
        closing = (
            datetime.combine(day + timedelta(days=1), time.min, timezone)
            if kind == "WARRANT"
            else datetime.combine(day, time(17), timezone)
        )
        days.append(
            {
                "session_date": day.isoformat(),
                "status": "SESSION" if session else "CLOSED",
                "intervals": (
                    [{"opens_at": opening.isoformat(), "closes_at": closing.isoformat()}]
                    if session
                    else []
                ),
                "source_reference": f"Synthetic complete original calendar / row {day}",
            }
        )
        day += timedelta(days=1)
    binding = {
        "instrument_kind": kind,
        "instrument_id": str(instrument_id),
        "listing_id": str(listing_id),
        "trading_venue_id": str(venue_id),
        "venue_mic": mic,
        "timezone": zone,
        "market_segment": "Explicit synthetic sessions, no real exchange assertion",
        "valid_from": start.isoformat(),
        "valid_through": end.isoformat(),
    }
    document = json.dumps(
        {"synthetic_original_source": True, "binding": binding, "days": days}, indent=2
    ).encode()
    document_hash = hashlib.sha256(document).hexdigest()
    manifest = (
        json.dumps(
            {
                "schema_version": "session-evidence-manifest-v1",
                "calendar_id": f"synthetic-original-bid-{kind.lower()}",
                "calendar_version": "synthetic-v1",
                "binding": binding,
                "coverage_start": start.isoformat(),
                "coverage_end": end.isoformat(),
                "days": days,
                "source_publisher": "Synthetic calendar author, no provider request",
                "source_reference": "https://example.invalid/synthetic-complete-calendar",
                "source_document_sha256": document_hash,
                "source_published_on": anchor.isoformat(),
            },
            indent=2,
        )
        + "\n"
    )
    command = SessionEvidenceImportCommand(
        request_id=uuid4(),
        supersedes_revision_id=None,
        manifest_json=manifest,
        manifest_sha256=hashlib.sha256(manifest.encode()).hexdigest(),
        document_filename=f"synthetic-{kind.lower()}-original.json",
        document_media_type="application/json",
        document_base64=base64.b64encode(document).decode(),
        document_sha256=document_hash,
        reviewed_at=datetime.now(UTC) - timedelta(seconds=1),
        review_reference="Explicit synthetic review against every original row",
    )
    return {
        **TypeAdapter(SessionEvidenceImportCommand).dump_python(command, mode="json"),
        "confirmation": "CONFIRM_OFFICIAL_SESSION_DOCUMENT_REVIEW",
    }


def test_actual_last_success_restart_scopes_and_read_only_snapshot_without_history_fallback(
    quote_database,
    monkeypatch,
):
    _migrate(quote_database, "head")

    async def exercise():
        assert make_url(quote_database).database.startswith("tw_currency_ref_test_")
        engine = create_async_engine(quote_database, poolclass=NullPool)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with _client(quote_database) as (client, _):
                body = await _product_payload(client)
                underlying = UUID(body["underlying_id"])
                body["isin"] = "DE000AB00001"
                response = await client.post("/api/v1/warrants", json=body)
                assert response.status_code == 201, response.text
                warrant = UUID(response.json()["id"])
                response = await client.get("/api/v1/market-reference-data/trading-venues")
                assert response.status_code == 200, response.text
                venue = next(
                    (item for item in response.json()["items"] if item["mic"] == "XFRA"), None
                )
                if venue is None:
                    response = await client.post(
                        "/api/v1/market-reference-data/trading-venues",
                        json={
                            "mic": "XFRA",
                            "name": "Synthetic Frankfurt session evidence fixture",
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
                listing = UUID(response.json()["id"])
                mapping = uuid4()
                now = datetime.now(UTC)
                async with sessions() as session:
                    await session.execute(
                        insert(WarrantProviderMappingModel).values(
                            id=mapping,
                            workspace_id=UUID(WORKSPACE),
                            warrant_listing_id=listing,
                            provider=MarketDataProvider.FRANKFURT_QUOTES,
                            provider_symbol=body["isin"],
                            provider_exchange_code="XFRA",
                            status=MappingStatus.ACTIVE,
                            validated_at=now,
                            version=1,
                            created_at=now,
                            updated_at=now,
                        )
                    )
                    await session.commit()
                anchor = datetime.now(UTC).astimezone(ZoneInfo("Europe/Berlin")).date() - timedelta(
                    days=40
                )
                response = await client.post(
                    BASE + "/purchases/external",
                    json={
                        **purchase(str(warrant), day=anchor.isoformat()),
                        "currency_confirmation": DECLARATION,
                    },
                )
                assert response.status_code == 201, response.text
                position = UUID(response.json()["position"]["id"])
                trade = UUID(response.json()["trade"]["id"])
                execution = UUID(response.json()["execution"]["id"])
                response = await client.post(
                    "/api/v1/warrants",
                    json={
                        **body,
                        "isin": "DE000CD00001",
                        "display_name": "Synthetic other held instrument",
                    },
                )
                assert response.status_code == 201, response.text
                response = await client.post(
                    BASE + "/purchases/external",
                    json=purchase(response.json()["id"], day=anchor.isoformat()),
                )
                assert response.status_code == 201, response.text
                foreign_trade = response.json()["trade"]["id"]
                foreign_position = response.json()["position"]["id"]

            async with sessions() as session:
                selector = PositionQuoteSourceSelector(
                    PositionQuoteSourceSelectionRepository(session),
                    (MarketDataProvider.FRANKFURT_QUOTES,),
                )
                reconciled = await selector.reconcile(
                    workspace_id=UUID(WORKSPACE),
                    position_id=position,
                    warrant_id=warrant,
                    selected_at=datetime.now(UTC),
                )
                selected = reconciled.selection
                assert selected is not None and selected.selection_status == "SELECTED"
                await session.commit()
                selection_id, selected_at, identity_key = (
                    selected.id,
                    selected.selected_at,
                    selected.identity_key,
                )
                now = datetime.now(UTC)
                original = quote_result(listing, now)
                payload = RESULT.dump_python(original, mode="json")
                session.add(
                    WarrantQuoteObservationModel(
                        workspace_id=UUID(WORKSPACE),
                        warrant_listing_id=listing,
                        provider=MarketDataProvider.FRANKFURT_QUOTES.value,
                        identity_key=identity_key,
                        payload=payload,
                    )
                )
                await session.commit()

            arguments = {
                "workspace_id": UUID(WORKSPACE),
                "position_id": position,
                "as_of": now,
                "expected_warrant_id": warrant,
            }

            async def read(*, pending_edit=False, **overrides):
                # A new session/reader models restart; no retaining provider is involved.
                async with sessions() as session:
                    await session.execute(
                        text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                    )
                    assert await session.scalar(text("SHOW transaction_read_only")) == "on"
                    assert (
                        await session.scalar(text("SHOW transaction_isolation"))
                        == "repeatable read"
                    )
                    if pending_edit:
                        product = await session.scalar(
                            select(WarrantModel).where(WarrantModel.id == warrant)
                        )
                        product.display_name = "Synthetic pending edit must not autoflush"
                        assert product in session.dirty
                    result = await RiskMarketDataReader(session).saved_quote(
                        **(arguments | overrides)
                    )
                    if pending_edit:
                        assert product in session.dirty
                    await session.rollback()
                    return result

            before = await _state(engine)
            first = await read(pending_edit=True)
            restarted = await read()
            assert restarted == first
            assert first.quote == original.data
            assert first.quote.original_evidence.bid.observed_at != first.quote.observed_at
            assert first.route.selection_id == selection_id
            assert first.route.selected_at == selected_at
            assert first.route.warrant_id == warrant and first.route.warrant_listing_id == listing
            assert first.route.trading_venue_id == UUID(venue["id"])
            assert first.provenance.warnings == original.warnings
            assert first.provenance.stored_at is None
            assert first.provenance.mutable and not first.provenance.historical_read
            assert (
                await read(expected_warrant_id=uuid4())
            ).reason == "SAVED_QUOTE_HELD_INSTRUMENT_MISMATCH"
            assert (await read(workspace_id=uuid4())).quote is None
            assert (await read(position_id=uuid4())).quote is None
            assert await _state(engine) == before

            owner_read = monitoring.read_hebeltrader_monitoring_basis
            snapshots = []

            async def checked_owner(session, **scope):
                assert await session.scalar(text("SHOW transaction_read_only")) == "on"
                assert await session.scalar(text("SHOW transaction_isolation")) == "repeatable read"
                snapshots.append(session)
                return await owner_read(session, **scope)

            monkeypatch.setattr(monitoring, "read_hebeltrader_monitoring_basis", checked_owner)
            endpoint = f"/api/v1/position-monitoring/trades/{trade}/hebeltrader-original-bid"
            async with _client(quote_database) as (client, database):
                response = await client.get(endpoint, params={"position_id": str(position)})
                assert response.status_code == 200, response.text
                partial = response.json()
                checks = {check["key"]: check["status"] for check in partial["checks"]}
                assert len(checks) == 8 and partial["coverage_status"] == "PARTIAL"
                assert partial["bid"]["status"] == "AVAILABLE"
                assert (
                    checks["HELD_INSTRUMENT"] == checks["ORIGINAL_BID_TIME_AND_AGE"] == "SATISFIED"
                )
                assert checks["EXECUTION_CURRENCY"] == "SATISFIED"
                assert (
                    checks["PRODUCT_SESSION_AT_BID"]
                    == checks["PRODUCT_SESSION_AT_READ"]
                    == "MISSING"
                )
                assert checks["TWENTY_UNDERLYING_SESSIONS_AT_BID"] == "MISSING"
                assert checks["PRICE_SCALE"] == checks["VERIFIED_LIVE_MARKET_STATUS"] == "MISSING"
                assert partial["economic_basis"]["position"]["product_id"] == str(warrant)
                assert partial["economic_basis"]["effective_execution_ids"] == [str(execution)]
                assert partial["economic_basis"]["cost_basis_currency"] == "EUR"
                assert partial["read_status"] == "READ_ONLY"
                assert partial["operation_status"] == "NOT_ACTIVATED"
                assert partial["rule_evaluation_status"] == "B04_B05_B06_B58_NOT_EVALUATED"
                legacy_status = partial["live_market_status"]
                assert legacy_status["reported_status"] == "OPEN"
                assert legacy_status["original_evidence"] is None
                assert legacy_status["status"] == "MISSING"
                assert legacy_status["at_bid"]["relation"] == "NO_ORIGINAL_STATUS_TIME"
                assert legacy_status["at_read"]["relation"] == "NO_ORIGINAL_STATUS_TIME"
                for path, target_position in (
                    (endpoint, foreign_position),
                    (
                        f"/api/v1/position-monitoring/trades/{foreign_trade}/hebeltrader-original-bid",
                        str(position),
                    ),
                    (endpoint, str(uuid4())),
                ):
                    rejected = await client.get(path, params={"position_id": target_position})
                    assert rejected.status_code == 404, rejected.text
                assert len(snapshots) == 4
                assert await _state(engine) == before

                async with engine.connect() as connection:
                    underlying_listing = (
                        (
                            await connection.execute(
                                text(
                                    "SELECT l.id, l.trading_venue_id, v.mic, v.timezone "
                                    "FROM listings l "
                                    "JOIN trading_venues v ON v.id=l.trading_venue_id "
                                    "WHERE l.workspace_id=:workspace "
                                    "AND l.underlying_id=:underlying "
                                    "AND l.is_primary"
                                ),
                                {"workspace": UUID(WORKSPACE), "underlying": underlying},
                            )
                        )
                        .mappings()
                        .one()
                    )
                local_day = datetime.now(UTC).astimezone(ZoneInfo(venue["timezone"])).date()
                imports = (
                    calendar_import(
                        kind="WARRANT",
                        instrument_id=warrant,
                        listing_id=listing,
                        venue_id=venue["id"],
                        mic=venue["mic"],
                        zone=venue["timezone"],
                        anchor=anchor,
                        start=local_day - timedelta(days=2),
                        end=local_day + timedelta(days=1),
                    ),
                    calendar_import(
                        kind="UNDERLYING",
                        instrument_id=underlying,
                        listing_id=underlying_listing["id"],
                        venue_id=underlying_listing["trading_venue_id"],
                        mic=underlying_listing["mic"],
                        zone=underlying_listing["timezone"],
                        anchor=anchor,
                        start=anchor,
                        end=local_day + timedelta(days=1),
                    ),
                )
                revisions = []
                for imported in imports:
                    response = await client.post(
                        "/api/v1/market-data/session-evidence/imports", json=imported
                    )
                    assert response.status_code == 201, response.text
                    revisions.append(response.json()["id"])
                after_imports = await _state(engine)
                response = await client.get(endpoint, params={"position_id": str(position)})
                assert response.status_code == 200, response.text
                documented = response.json()
                assert documented["coverage_status"] == "PARTIAL"
                checks = {check["key"]: check["status"] for check in documented["checks"]}
                assert len(checks) == 8
                assert {key for key, status in checks.items() if status == "MISSING"} == {
                    "PRICE_SCALE",
                    "VERIFIED_LIVE_MARKET_STATUS",
                }
                assert sum(status == "SATISFIED" for status in checks.values()) == 6
                assert documented["product_sessions"]["calendar"]["revision_id"] == revisions[0]
                assert documented["underlying_sessions"]["calendar"]["revision_id"] == revisions[1]
                count = documented["underlying_sessions"]["count"]
                assert count["status"] == "AVAILABLE" and count["completed_sessions"] == 20
                assert count["threshold_reached"]
                assert count["evaluated_at"] == documented["bid"]["original_bid_at"]
                assert documented["rule_evaluation_status"] == "B04_B05_B06_B58_NOT_EVALUATED"
                assert documented["operation_status"] == "NOT_ACTIVATED"
                assert documented["saved_quote"]["provenance"]["stored_at"] is None
                assert await _state(engine) == after_imports

                # Persist a separately timed source status through the real price
                # owner, then read it from fresh sessions and the production API.
                source = original.data.original_evidence
                status_at = source.bid.observed_at
                status = OriginalMarketStatusEvidence(
                    version="original-market-status-evidence-v1",
                    source_contract=source.source_contract,
                    source_reference=source.source_reference,
                    generated_at=source.generated_at,
                    isin=source.isin,
                    venue_mic=source.venue_mic,
                    status="OPEN",
                    original_status_text="OPEN",
                    source_status_field="trading_status",
                    observed_at=status_at,
                    original_time_text=status_at.astimezone(ZoneInfo("Europe/Berlin")).isoformat(),
                    source_time_field="status_observed_at",
                )
                with_status = replace(
                    original, data=replace(original.data, original_market_status=status)
                )
                upstream = Mock()
                upstream.get_warrant_listing_quote = AsyncMock(return_value=with_status)
                retained = RetainedWarrantQuoteProvider(
                    database, upstream, MarketDataProvider.FRANKFURT_QUOTES
                )
                request = WarrantQuoteRequest(
                    UUID(WORKSPACE), listing, uuid4(), now, expected_currency="EUR"
                )
                assert await retained.get_warrant_listing_quote(request) == with_status
                upstream.get_warrant_listing_quote.assert_awaited_once_with(request)
                status_payload = RESULT.dump_python(with_status, mode="json")
                after_status = await _state(engine)
                status_snapshot = await read(pending_edit=True)
                assert await read() == status_snapshot
                assert status_snapshot.quote.original_market_status == status
                assert first.quote.original_market_status is None
                assert (
                    status_snapshot.provenance.raw_payload_fingerprint
                    != first.provenance.raw_payload_fingerprint
                )
                response = await client.get(endpoint, params={"position_id": str(position)})
                assert response.status_code == 200, response.text
                reported = response.json()
                live = reported["live_market_status"]
                assert reported["implementation_status"] == "F207_3_MARKET_STATUS_EVIDENCE_ONLY"
                assert live["definition_version"] == "hebeltrader-live-market-status-v1"
                assert live["status"] == "MISSING" and live["reported_status"] == "OPEN"
                assert live["original_evidence"] == status_payload["data"]["original_market_status"]
                assert live["at_bid"]["relation"] == "AT_SOURCE_POINT"
                assert live["at_read"]["relation"] == "AFTER_SOURCE_POINT"
                assert live["at_bid"]["status"] == live["at_read"]["status"] == "NOT_ASSESSABLE"
                assert live["evidence_scope"] == "SAVED_QUOTE_LAST_SUCCESS_ONLY"
                assert live["source_qualification"] == "NOT_INDEPENDENTLY_VERIFIED"
                assert live["status_validity_interval"] == "NOT_ESTABLISHED"
                assert live["newer_status_observations"] == "NOT_OBSERVED_BY_SAVED_QUOTE_READER"
                assert {
                    "MARKET_STATUS_POINT_IS_NOT_VALIDITY_INTERVAL",
                    "MARKET_STATUS_SOURCE_SEMANTICS_NOT_VERIFIED",
                    "MARKET_STATUS_NEWER_OBSERVATIONS_NOT_COVERED",
                }.issubset(live["reasons"])
                assert reported["coverage_status"] == "PARTIAL"
                assert reported["rule_evaluation_status"] == "B04_B05_B06_B58_NOT_EVALUATED"
                assert reported["operation_status"] == "NOT_ACTIVATED"
                assert await _state(engine) == after_status

                async def replace_payload(value):
                    # Deliberately damaged stored JSON only in this guarded DB;
                    # this is not an application write path or a recovery action.
                    async with sessions() as session:
                        await session.execute(
                            update(WarrantQuoteObservationModel)
                            .where(
                                WarrantQuoteObservationModel.workspace_id == UUID(WORKSPACE),
                                WarrantQuoteObservationModel.warrant_listing_id == listing,
                                WarrantQuoteObservationModel.provider
                                == MarketDataProvider.FRANKFURT_QUOTES.value,
                            )
                            .values(payload=value)
                        )
                        await session.commit()

                # The actual typed saved reader rejects foreign scope, source
                # revisions, contradictory status and invented/unknown clocks.
                for field, invalid in (
                    ("isin", "DE000CD00001"),
                    ("venue_mic", "XSTU"),
                    ("source_contract", "unrelated-source-v2"),
                    ("source_reference", "Synthetic different source revision"),
                    ("original_status_text", "CLOSED"),
                    ("original_time_text", status_at.replace(tzinfo=None).isoformat()),
                ):
                    damaged = deepcopy(status_payload)
                    damaged["data"]["original_market_status"][field] = invalid
                    await replace_payload(damaged)
                    rejected = await read()
                    assert rejected.quote is None, field
                    assert rejected.reason == "SAVED_QUOTE_PAYLOAD_INVALID", field

                # Equality at the actual read clock is allowed; one microsecond
                # before retrieval is not. No grace period or status TTL exists.
                boundary = deepcopy(status_payload)
                for key in ("original_evidence", "original_market_status"):
                    boundary["data"][key]["generated_at"] = now.isoformat()
                boundary["data"]["original_market_status"].update(
                    observed_at=now.isoformat(), original_time_text=now.isoformat()
                )
                await replace_payload(boundary)
                assert (await read()).quote.original_market_status.observed_at == now
                assert (await read(as_of=now - timedelta(microseconds=1))).quote is None
                future = deepcopy(boundary)
                # With no separate price-side envelope, only the newly added
                # original-status clock guard can reject this future generation.
                future["data"]["original_evidence"] = None
                future["data"]["original_market_status"]["generated_at"] = (
                    now + timedelta(microseconds=1)
                ).isoformat()
                await replace_payload(future)
                assert (await read()).reason == "SAVED_QUOTE_IDENTITY_OR_TIME_INVALID"
                await replace_payload(status_payload)
                assert await _state(engine) == after_status

                # A later CLOSED observation without a valid price is not a new
                # last-success. Exercise the real retention owner: its returned
                # fallback marks the error, while this passive saved-price read
                # cannot see that later attempt or claim a current OPEN market.
                closed_at = datetime.now(UTC)
                closed = replace(
                    status,
                    generated_at=closed_at,
                    observed_at=closed_at,
                    original_time_text=closed_at.isoformat(),
                    status="CLOSED",
                    original_status_text="CLOSED",
                )
                status_only = replace(
                    with_status,
                    retrieved_at=closed_at,
                    data=replace(
                        with_status.data,
                        bid=None,
                        ask=None,
                        observed_at=closed_at,
                        trading_status="CLOSED",
                        original_evidence=None,
                        original_market_status=closed,
                    ),
                )
                upstream.get_warrant_listing_quote.reset_mock()
                upstream.get_warrant_listing_quote.return_value = status_only
                request = replace(request, correlation_id=uuid4(), as_of=closed_at)
                fallback = await retained.get_warrant_listing_quote(request)
                upstream.get_warrant_listing_quote.assert_awaited_once_with(request)
                assert fallback.data.retained
                assert fallback.data.refresh_error == "WARRANT_QUOTE_NOT_VALIDATED"
                assert fallback.data.original_market_status == status
                assert fallback.retrieved_at == original.retrieved_at
                after_attempt = await _state(engine)
                saved_again = await read(as_of=closed_at)
                assert saved_again.quote.original_market_status == status
                assert saved_again.quote.refresh_error is None
                assert (
                    saved_again.provenance.raw_payload_fingerprint
                    == status_snapshot.provenance.raw_payload_fingerprint
                )
                response = await client.get(endpoint, params={"position_id": str(position)})
                assert response.status_code == 200, response.text
                live_after_attempt = response.json()["live_market_status"]
                assert live_after_attempt["status"] == "MISSING"
                assert live_after_attempt["reported_status"] == "OPEN"
                assert live_after_attempt["original_evidence"] == live["original_evidence"]
                assert (
                    live_after_attempt["newer_status_observations"]
                    == "NOT_OBSERVED_BY_SAVED_QUOTE_READER"
                )
                assert live_after_attempt["status_validity_interval"] == "NOT_ESTABLISHED"
                assert all(
                    item["status"] != "SATISFIED"
                    for item in response.json()["checks"]
                    if item["key"] == "VERIFIED_LIVE_MARKET_STATUS"
                )
                assert await _state(engine) == after_attempt

                # A priced CLOSED point can be stored by the existing price
                # owner. It is unsuitable OPEN evidence, not a claim that the
                # market remained closed up to this later passive read.
                priced_closed = replace(
                    with_status,
                    retrieved_at=closed_at,
                    data=replace(
                        with_status.data,
                        trading_status="CLOSED",
                        original_evidence=replace(source, generated_at=closed_at),
                        original_market_status=closed,
                    ),
                )
                upstream.get_warrant_listing_quote.return_value = priced_closed
                assert await retained.get_warrant_listing_quote(request) == priced_closed
                after_priced_closed = await _state(engine)
                response = await client.get(endpoint, params={"position_id": str(position)})
                assert response.status_code == 200, response.text
                closed_report = response.json()["live_market_status"]
                assert closed_report["status"] == "UNSUITABLE"
                assert closed_report["reported_status"] == "CLOSED"
                assert "MARKET_STATUS_SOURCE_REPORTED_NOT_OPEN" in closed_report["reasons"]
                assert closed_report["at_bid"]["relation"] == "BEFORE_SOURCE_POINT"
                assert closed_report["at_read"]["relation"] == "AFTER_SOURCE_POINT"
                assert closed_report["at_read"]["status"] == "NOT_ASSESSABLE"
                assert closed_report["status_validity_interval"] == "NOT_ESTABLISHED"
                assert await _state(engine) == after_priced_closed

            # This existing table is intentionally mutable. New payload replaces
            # the last-success, while a previously returned snapshot stays intact.
            later = now + timedelta(seconds=10)
            replacement = replace(
                original,
                retrieved_at=later,
                data=replace(original.data, bid=Decimal("1.9"), original_evidence=None),
            )
            async with sessions() as session:
                await session.execute(
                    update(WarrantQuoteObservationModel)
                    .where(WarrantQuoteObservationModel.warrant_listing_id == listing)
                    .values(payload=RESULT.dump_python(replacement, mode="json"))
                )
                await session.commit()
            after_replace = await _state(engine)
            latest = await read(as_of=later)
            assert latest.quote.bid == Decimal("1.9")
            assert latest.quote.original_evidence is None
            assert first.quote.bid == Decimal("2.1")
            assert (
                latest.provenance.raw_payload_fingerprint
                != first.provenance.raw_payload_fingerprint
            )
            earlier = await read()
            assert (
                earlier.quote is None and earlier.reason == "SAVED_QUOTE_IDENTITY_OR_TIME_INVALID"
            )
            assert await _state(engine) == after_replace

            # A current mapping revision invalidates the old selected route. The
            # passive reader must not repair/reselect it or reuse the saved value.
            async with sessions() as session:
                await session.execute(
                    update(WarrantProviderMappingModel)
                    .where(WarrantProviderMappingModel.id == mapping)
                    .values(version=2, updated_at=later)
                )
                await session.commit()
            after_mapping = await _state(engine)
            assert (await read(as_of=later)).reason == "SAVED_QUOTE_ROUTE_IDENTITY_CHANGED"
            assert await _state(engine) == after_mapping
        finally:
            await engine.dispose()

    asyncio.run(exercise())
