"""Current listing originals in a guarded, UUID-isolated PostgreSQL database."""

import asyncio
import gzip
import hashlib
from dataclasses import replace
from datetime import UTC, date, datetime, time, timedelta
from io import BytesIO
from types import SimpleNamespace
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from tests.integration.backend.database import test_indicative_entry_postgres as indicative
from tests.integration.backend.database import test_saved_quote_evidence_postgres as saved
from tests.integration.backend.database.test_product_document_reparse_postgres import (
    END,
    ISIN,
    PAYMENT,
    SOURCE,
    UNDERLYING_ISIN,
    open_position,
    post,
)
from tests.integration.backend.database.test_product_price_scale_evidence_postgres import (
    RESULT,
    engine_for,
    import_body,
    scale_url,
)
from tests.integration.backend.test_realized_gross_report_postgres import _client, _state
from tests.integration.backend.test_trade_capture_safety import WORKSPACE
from tests.integration.backend.test_usd_chf_currency_references import _migrate
from tests.unit.backend.providers.product_review_document_fixture import synthetic_kid_pdf

from app.features.market_data.domain.enums import (
    CacheStatus,
    MappingStatus,
    MarketDataCapability,
    MarketDataProvider,
    QualityStatus,
)
from app.features.market_data.domain.models import WarrantQuoteSnapshot
from app.features.market_data.domain.review_calendars import NYSE_CALENDAR
from app.features.market_data.persistence.models import (
    WarrantProviderMappingModel,
    WarrantQuoteObservationModel,
)
from app.features.market_data.persistence.position_quote_source import (
    PositionQuoteSourceSelectionRepository,
)
from app.features.market_data.service import review_calendars as calendars
from app.features.market_data.service.position_quote_source import PositionQuoteSourceSelector
from app.features.market_data.service.types import MarketDataResult
from app.features.position_monitoring.domain.indicative_policy import V1_POLICY, V2_POLICY
from app.features.position_monitoring.service import indicative_entry_sessions as sessions
from app.features.position_monitoring.service.hebeltrader_b58_sources import QUALIFIED_B58_PATHS
from app.features.position_monitoring.service.indicative_entry_inputs import read_indicative_inputs
from app.features.position_monitoring.service.indicative_entry_read import IndicativeEntryReader
from app.features.product.domain.listing_unit_evidence import (
    ListingUnitImportCommand,
    ListingUnitRoute,
    ListingUnitRuleDocumentSpec,
    ListingUnitRuleOriginal,
    ListingUnitRuleSet,
)
from app.features.product.service import listing_unit_evidence as listing_service
from app.features.product.service.listing_unit_sources import qualify_gettex_listing_source
from app.features.product.service.review_evidence import (
    ProductReviewEvidenceReader,
    record_original_kid,
)

listing_unit_database = saved.quote_database
forbid_outbound_http = saved.forbid_outbound_http
TABLE = "product_listing_unit_evidence"
ACTOR = UUID(int=1701)
ROLES = ("EXCHANGE_RULES", "OPEN_MARKET_RULES", "EXECUTION_RULES", "PRODUCT_CLASSIFICATION")


def kid_document(*, number=1, underlying=UNDERLYING_ISIN):
    return synthetic_kid_pdf(
        "Synthetisches Basisinformationsblatt PRODUKT "
        f"Call Optionsschein bezogen auf eine Aktie ISIN {ISIN} "
        f"Basiswert {underlying} Währung des Produkts: EUR "
        "Referenzstelle: New York Stock Exchange "
        f"Bewertungstag Der Ausübungstag bzw. der {END:%d.%m.%Y} "
        f"Fälligkeitstag {PAYMENT:%d.%m.%Y} Originalrevision {number}"
    )


def synthetic_sources(now):
    originals = tuple(
        ListingUnitRuleOriginal(
            role,
            f"synthetic-{role.lower()}.pdf",
            "application/pdf",
            synthetic_kid_pdf(f"SYNTHETIC TEST ONLY {role}: price per warrant in EUR"),
            now - timedelta(days=1),
        )
        for role in ROLES
    )
    rule_set = ListingUnitRuleSet(
        version="synthetic-postgres-unit-v1",
        observed_at=now - timedelta(days=1),
        effective_from=now - timedelta(days=2),
        documents=tuple(
            ListingUnitRuleDocumentSpec(
                item.role,
                f"https://example.invalid/{item.filename}",
                hashlib.sha256(item.document).hexdigest(),
                item.media_type,
            )
            for item in originals
        ),
    )
    return (rule_set,), originals


def qualified_source(scope, *, now, bid="2.10"):
    end = now.replace(minute=now.minute // 15 * 15, second=0, microsecond=0)
    observed = end - timedelta(minutes=1)
    file_name = f"pretrade.{end:%Y%m%d.%H.%M}.mund.csv.gz"
    rows = (
        "DE000OTHER00,"
        + observed.strftime("%H:%M:%S.%f")
        + ",EUR,1.00,5,1.01,5\n"
        + f"{ISIN},{observed:%H:%M:%S.%f},EUR,{bid},10,2.50,10\n"
    )
    # The actual full-stream qualifier issues the internal capability. No
    # caller-supplied JSON, hash or Boolean substitutes for this scan.
    original = gzip.compress(rows.encode(), mtime=0)
    source = qualify_gettex_listing_source(
        source=BytesIO(original),
        file_name=file_name,
        target_isin=ISIN,
        rules=scope.originals,
        known_at=now,
        retrieved_at=now,
        registry=scope.registry,
    )
    assert source.pretrade.file_sha256 == hashlib.sha256(original).hexdigest()
    return source


async def prepare(client, database):
    product, capture, terms = await open_position(client)
    response = await client.get("/api/v1/market-reference-data/trading-venues")
    assert response.status_code == 200, response.text
    venue = next(row for row in response.json()["items"] if row["mic"] == "MUND")
    listing = await post(
        client,
        f"/api/v1/warrants/{product['id']}/listings",
        {"trading_venue_id": venue["id"], "quotation_currency_code": "EUR"},
    )
    now = datetime.now(UTC)
    workspace, warrant = UUID(WORKSPACE), UUID(product["id"])
    async with database.session_context() as session:
        kid_id = await record_original_kid(
            session,
            workspace_id=workspace,
            warrant_id=warrant,
            source_reference=SOURCE,
            document=kid_document(),
            retrieved_at=now - timedelta(minutes=1),
            now=now,
        )
        await session.commit()
    registry, originals = synthetic_sources(now)
    route = ListingUnitRoute(UUID(listing["id"]), "GETTEX_DELAYED", "MUND", "EUR")
    scope = SimpleNamespace(
        workspace_id=workspace,
        warrant_id=warrant,
        kid_id=kid_id,
        product=product,
        capture=capture,
        terms=terms,
        route=route,
        now=now,
        registry=registry,
        originals=originals,
    )
    scope.command = ListingUnitImportCommand(
        request_id=uuid4(),
        expected_revision_id=None,
        route=route,
        kid_revision_id=kid_id,
        reviewed_at=now,
        review_reference="Synthetic reviewed originals for isolated PostgreSQL test",
    )
    scope.source = qualified_source(scope, now=now)
    return scope


async def preview(database, scope, *, command=None, source=None, now=None):
    async with database.session_context() as session:
        return await listing_service.ListingUnitImportService(
            session, registry=scope.registry
        ).preview(
            workspace_id=scope.workspace_id,
            warrant_id=scope.warrant_id,
            command=command or scope.command,
            source=source or scope.source,
            now=now or scope.now,
        )


async def record(database, scope, checked, *, command=None, source=None, now=None):
    async with database.session_context() as session:
        result = await listing_service.ListingUnitImportService(
            session, registry=scope.registry
        ).record(
            workspace_id=scope.workspace_id,
            warrant_id=scope.warrant_id,
            actor_id=ACTOR,
            command=command or scope.command,
            source=source or scope.source,
            expected_preview_fingerprint=checked.fingerprint,
            now=now or scope.now,
        )
        return result


async def read(database, scope, *, known_at):
    async with database.session_context() as session:
        return await listing_service.ListingUnitEvidenceReader(
            session, registry=scope.registry
        ).current(
            workspace_id=scope.workspace_id,
            warrant_id=scope.warrant_id,
            route=scope.route,
            known_at=known_at,
        )


async def store_gettex_quote(database, scope):
    """Persist an exact-route synthetic delayed observation, without original BID/OPEN."""
    provider = MarketDataProvider.GETTEX_DELAYED
    at = datetime.now(UTC)
    async with database.session_context() as session:
        session.add(
            WarrantProviderMappingModel(
                id=uuid4(),
                workspace_id=scope.workspace_id,
                warrant_listing_id=scope.route.listing_id,
                provider=provider,
                provider_symbol=ISIN,
                provider_exchange_code="MUND",
                status=MappingStatus.ACTIVE,
                validated_at=at,
                version=1,
                created_at=at,
                updated_at=at,
            )
        )
        await session.commit()
        selector = PositionQuoteSourceSelector(
            PositionQuoteSourceSelectionRepository(session), (provider,)
        )
        selected = await selector.reconcile(
            workspace_id=scope.workspace_id,
            position_id=UUID(scope.capture["position"]["id"]),
            warrant_id=scope.warrant_id,
            selected_at=at,
        )
        assert selected.changed and selected.selection is not None
        assert selected.selection.selection_status == "SELECTED"
        assert selected.selection.provider == "GETTEX_DELAYED"
        assert selected.selection.warrant_listing_id == scope.route.listing_id
        await session.commit()
        observation = MarketDataResult(
            data=WarrantQuoteSnapshot(
                warrant_listing_id=scope.route.listing_id,
                bid="0.40",
                ask="2.50",
                currency="EUR",
                provider_symbol=ISIN,
                provider_exchange_code="MUND",
                isin=ISIN,
                observed_at=scope.source.pretrade.observed_at,
                source_mode="OFFICIAL_DELAYED_PRETRADE",
                venue_mic="MUND",
                trading_status="UNKNOWN",
            ),
            provider=provider,
            capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
            correlation_id=uuid4(),
            retrieved_at=at,
            cache_status=CacheStatus.BYPASS,
            quality_status=QualityStatus.VALID,
            warnings=(),
            retry_count=0,
            provider_call_cost=0,
        )
        session.add(
            WarrantQuoteObservationModel(
                workspace_id=scope.workspace_id,
                warrant_listing_id=scope.route.listing_id,
                provider=provider.value,
                identity_key=selected.selection.identity_key,
                payload=RESULT.dump_python(observation, mode="json"),
            )
        )
        await session.commit()


async def store_reference_calendar(database, scope, monkeypatch):
    original = b"Synthetic test: weekdays 09:30-16:00 New York; no exceptions."
    definition = replace(
        NYSE_CALENDAR,
        source_version="synthetic-listing-unit-consumer-calendar",
        binding=replace(
            NYSE_CALENDAR.binding,
            valid_from=date(scope.now.year - 1, 1, 1),
            valid_through=date(scope.now.year, 12, 31),
        ),
        closed_dates=(),
        early_closes=(),
        opens_at=time(9, 30),
        closes_at=time(16),
        sources=(
            ("https://example.invalid/listing-calendar", hashlib.sha256(original).hexdigest()),
        ),
    )
    monkeypatch.setattr(calendars, "NYSE_CALENDAR", definition)
    monkeypatch.setattr(sessions, "NYSE_CALENDAR", definition)
    requests = []

    def transport(request):
        requests.append(str(request.url))
        assert str(request.url) == definition.sources[0][0]
        return httpx.Response(200, content=original)

    async with (
        httpx.AsyncClient(transport=httpx.MockTransport(transport), trust_env=False) as http,
        database.session_context() as session,
    ):
        await calendars.acquire_nyse_calendar(
            session, http, workspace_id=scope.workspace_id, now=scope.now
        )
        await session.commit()
    assert requests == [definition.sources[0][0]]


@pytest.mark.parametrize("concurrent", [False, True], ids=["sequential", "concurrent"])
def test_preview_and_repeated_import_preserve_owner_facts_and_append_only_history(
    listing_unit_database, concurrent
):
    _migrate(listing_unit_database, "head")

    async def exercise():
        engine = engine_for(listing_unit_database)
        try:
            async with _client(listing_unit_database) as (client, database):
                scope = await prepare(client, database)
                before = await _state(engine)
                checked = await preview(database, scope)
                assert checked.operation_status == "READ_ONLY_PREVIEW"
                assert checked.kid_revision_id == scope.kid_id
                assert await _state(engine) == before

                if concurrent:
                    imported = await asyncio.gather(
                        *(record(database, scope, checked) for _ in range(3))
                    )
                else:
                    imported = [await record(database, scope, checked) for _ in range(3)]
                assert len({item.id for item in imported}) == 1
                after = await _state(engine)
                assert len(after[TABLE]) == 1
                assert {key: rows for key, rows in after.items() if key != TABLE} == {
                    key: rows for key, rows in before.items() if key != TABLE
                }
                only = after[TABLE][0]
                assert only["revision_number"] == 1 and only["previous_revision_id"] is None
                assert only["kid_revision_id"] == scope.kid_id
                assert only["source"]["pretrade"]["file_sha256"] == (
                    scope.source.pretrade.file_sha256
                )
                assert before["product_review_documents"][0]["facts"]["unit"] is None
                value = await read(database, scope, known_at=scope.now)
                assert value.status == "AVAILABLE" and value.reasons == ()
                assert value.quality == "CURRENT_UNIT_HISTORY_ASSUMED"
                assert (
                    value.imported_kid_revision_id == value.current_kid_revision_id == scope.kid_id
                )
                assert await _state(engine) == after

                for sql in (
                    "UPDATE product_listing_unit_evidence "
                    "SET review_reference='synthetic overwrite'",
                    "DELETE FROM product_listing_unit_evidence",
                    "TRUNCATE product_listing_unit_evidence CASCADE",
                ):
                    async with database.session_context() as session:
                        with pytest.raises(IntegrityError, match=r"append.only"):
                            await session.execute(text(sql))
                        await session.rollback()
                    assert await _state(engine) == after
        finally:
            await engine.dispose()

    asyncio.run(exercise())


def test_revisions_are_time_bound_and_daily_kid_rotation_needs_no_manual_reimport(
    listing_unit_database, monkeypatch
):
    _migrate(listing_unit_database, "head")

    async def exercise():
        engine = engine_for(listing_unit_database)
        try:
            async with _client(listing_unit_database) as (client, database):
                scope = await prepare(client, database)
                monkeypatch.setattr(listing_service, "SUPPORTED_RULE_SETS", scope.registry)
                missing = await read(database, scope, known_at=scope.now)
                assert missing.status == "MISSING" and missing.revision_id is None
                original = await record(database, scope, await preview(database, scope))
                earlier = await read(
                    database, scope, known_at=scope.now - timedelta(microseconds=1)
                )
                assert earlier.status == "MISSING" and earlier.revision_id is None
                first = await read(database, scope, known_at=scope.now)
                assert first.status == "AVAILABLE" and first.revision_id == original.id

                later = scope.now + timedelta(days=1)
                async with database.session_context() as session:
                    newer_kid = await record_original_kid(
                        session,
                        workspace_id=scope.workspace_id,
                        warrant_id=scope.warrant_id,
                        source_reference=SOURCE,
                        document=kid_document(number=2),
                        retrieved_at=later,
                        now=later,
                    )
                    await session.commit()
                current = await read(database, scope, known_at=later)
                assert current.status == "AVAILABLE"
                assert current.revision_id == original.id
                assert current.imported_kid_revision_id == scope.kid_id
                assert current.current_kid_revision_id == newer_kid != scope.kid_id
                assert len((await _state(engine))[TABLE]) == 1
                async with database.session_context() as session:
                    combined = await ProductReviewEvidenceReader(session).current_for_review(
                        workspace_id=scope.workspace_id,
                        warrant_id=scope.warrant_id,
                        known_at=later,
                        listing_unit_route=scope.route,
                    )
                assert combined.status == "AVAILABLE"
                assert combined.unit_source_kind == "LISTING_ORIGINAL"
                assert combined.revision_id == newer_kid
                assert combined.listing_unit_evidence.revision_id == original.id

                second_time = later + timedelta(minutes=1)
                second_source = qualified_source(scope, now=second_time, bid="2.20")
                second_command = replace(
                    scope.command,
                    request_id=uuid4(),
                    expected_revision_id=original.id,
                    kid_revision_id=newer_kid,
                    reviewed_at=second_time,
                )
                checked = await preview(
                    database, scope, command=second_command, source=second_source, now=second_time
                )
                second = await record(
                    database,
                    scope,
                    checked,
                    command=second_command,
                    source=second_source,
                    now=second_time,
                )
                assert second.id != original.id
                assert second.previous_revision_id == original.id and second.revision_number == 2
                assert (await read(database, scope, known_at=scope.now)).revision_id == original.id
                assert (await read(database, scope, known_at=second_time)).revision_id == second.id
                unchanged = await _state(engine)
                assert len(unchanged[TABLE]) == 2

                contradiction_time = second_time + timedelta(minutes=1)
                async with database.session_context() as session:
                    await record_original_kid(
                        session,
                        workspace_id=scope.workspace_id,
                        warrant_id=scope.warrant_id,
                        source_reference=SOURCE,
                        document=kid_document(number=3, underlying="US00SYNTH029"),
                        retrieved_at=contradiction_time,
                        now=contradiction_time,
                    )
                    await session.commit()
                before_read = await _state(engine)
                blocked = await read(database, scope, known_at=contradiction_time)
                assert blocked.status == "UNSUITABLE"
                assert "PRODUCT_DOCUMENT_UNDERLYING_MISMATCH" in blocked.reasons
                assert blocked.revision_id == second.id
                assert await _state(engine) == before_read
                assert before_read[TABLE] == unchanged[TABLE]
        finally:
            await engine.dispose()

    asyncio.run(exercise())


def test_v2_persists_listing_original_assumption_without_qualifying_v1_or_b58(
    listing_unit_database, monkeypatch
):
    _migrate(listing_unit_database, "head")

    async def exercise():
        engine = engine_for(listing_unit_database)
        try:
            async with _client(listing_unit_database) as (client, database):
                scope = await prepare(client, database)
                scope.source = qualified_source(scope, now=scope.now, bid="0.40")
                imported = await record(database, scope, await preview(database, scope))
                # Only the Python test dependency supplies reviewed synthetic pins.
                monkeypatch.setattr(listing_service, "SUPPORTED_RULE_SETS", scope.registry)
                await store_gettex_quote(database, scope)
                await store_reference_calendar(database, scope, monkeypatch)
                at = datetime.now(UTC)
                arguments = {
                    "workspace_id": scope.workspace_id,
                    "trade_id": UUID(scope.capture["trade"]["id"]),
                    "position_id": UUID(scope.capture["position"]["id"]),
                    "now": at,
                }
                baseline = await _state(engine)
                assert not baseline["product_price_scale_evidence"]
                assert not baseline["market_session_evidence"]
                assert baseline["product_review_documents"][0]["facts"]["unit"] is None
                assert not QUALIFIED_B58_PATHS
                async with database.session_context() as session:
                    v1 = await read_indicative_inputs(session, **arguments, policy=V1_POLICY)
                assert not v1.quote.usable
                assert v1.material["product_scale"]["quality"] == "UNAVAILABLE"
                assert "current_unit_evidence" not in v1.material["product_scale"]
                assert await _state(engine) == baseline

                consumer_scope = {"capture": scope.capture}
                first = await indicative.evaluate(
                    engine, consumer_scope, at, policy=V2_POLICY, notifications_enabled=False
                )
                assert first.outcome == "BELOW_ENTRY" and not first.data_problem_active
                state = await _state(engine)
                row = indicative.assessment(state, first)
                scale = row["inputs"]["product_scale"]
                current = scale["current_unit_evidence"]
                listing = current["listing_unit_evidence"]
                assert scale["quality"] == "CURRENT_UNIT_HISTORY_ASSUMED"
                assert scale["history_continuity_assumed"] is True
                assert scale["owner_assessment"]["status"] == "MISSING"
                assert current["unit_source_kind"] == "LISTING_ORIGINAL"
                assert current["revision_id"] == str(scope.kid_id)
                assert current["source_document_sha256"] == imported.kid_document_sha256
                assert listing["revision_id"] == str(imported.id)
                assert listing["imported_kid_revision_id"] == str(scope.kid_id)
                assert listing["pretrade_file_sha256"] == scope.source.pretrade.file_sha256
                assert listing["rule_sources"][0]["document_sha256"] == (
                    scope.source.rule_originals[0].document_sha256
                )
                assert listing["route"] == {
                    "listing_id": str(scope.route.listing_id),
                    "provider": "GETTEX_DELAYED",
                    "venue_mic": "MUND",
                    "currency": "EUR",
                }
                assert row["result"]["original_bid_at"] is None
                assert row["result"]["evaluation_mode"] == "DELAYED_SOURCE_BID"
                assert row["result"]["source_time_basis"] == "SHARED_QUOTE_TIME"
                assert row["inputs"]["saved_quote"]["quote"]["original_market_status"] is None
                assert row["inputs"]["entry"]["time_precision"] == "DATE_ONLY"
                calendar = row["inputs"]["comparison_sessions"]["calendar"]
                assert calendar["entry_day_precision"] == "CONSERVATIVE_DATE_BOUND"
                assert calendar["historical_listing_binding_verified"] is False
                assert calendar["calendar_quality"] == "CURRENT_DOCUMENT_REFERENCE_MARKET_ASSUMED"
                report = await IndicativeEntryReader(engine, scope=V2_POLICY.scope).read(
                    scope.workspace_id, arguments["trade_id"], arguments["position_id"]
                )
                assert report.latest_assessment.history_continuity_assumed
                assert report.qualified_b04 is report.full_baseline_activated is False
                assert indicative.strict_state(state) == indicative.strict_state(baseline)
                assert state["execution_records"] == baseline["execution_records"]
                assert state["positions"] == baseline["positions"]
                assert state["product_review_documents"] == baseline["product_review_documents"]
                assert state[TABLE] == baseline[TABLE]
                assert state["notifications"] == []

                # A real historical contradiction wins over the still valid current
                # listing unit. Neither an adjustment nor a withdrawal becomes a
                # missing interval that V2 may bridge with its continuity assumption.
                history_scope = {
                    "product": scope.product,
                    "terms": scope.terms[0],
                    "anchor": date(2026, 8, 17),
                }
                previous = None
                for status in ("ADJUSTMENT_REQUIRED", "WITHDRAWN"):
                    body = import_body(
                        history_scope,
                        supersedes=previous,
                        status=status,
                        version=f"synthetic-current-listing-{status.lower()}",
                    )
                    response = await client.post(scale_url(history_scope) + "/imports", json=body)
                    assert response.status_code == 201, response.text
                    previous = response.json()["id"]
                    blocked = await indicative.evaluate(
                        engine,
                        consumer_scope,
                        datetime.now(UTC),
                        policy=V2_POLICY,
                        notifications_enabled=False,
                    )
                    assert blocked.outcome == "UNAVAILABLE" and blocked.data_problem_active
                    after = await _state(engine)
                    rejected = indicative.assessment(after, blocked)
                    rejected_scale = rejected["inputs"]["product_scale"]
                    assert f"PRODUCT_PRICE_SCALE_{status}" in rejected["result"]["reasons"]
                    assert rejected_scale["quality"] == "UNAVAILABLE"
                    assert rejected_scale["history_continuity_assumed"] is False
                    assert rejected_scale["current_unit_evidence"]["status"] == "AVAILABLE"
                    assert rejected_scale["current_unit_evidence"]["unit_source_kind"] == (
                        "LISTING_ORIGINAL"
                    )
                    assert after[TABLE] == baseline[TABLE]
                    assert after["execution_records"] == baseline["execution_records"]
                    assert after["positions"] == baseline["positions"]
                    assert indicative.strict_state(after) == indicative.strict_state(baseline)
                    assert after["notifications"] == []
        finally:
            await engine.dispose()

    asyncio.run(exercise())
