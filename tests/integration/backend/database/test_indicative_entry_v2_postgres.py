"""Real V2 owner composition in guarded disposable PostgreSQL; all HTTP intercepted.

The original-document and calendar bytes below are explicitly synthetic test
dependencies. They do not qualify any production provider or historical unit.
"""

import asyncio
import hashlib
from dataclasses import replace
from datetime import UTC, date, datetime, time, timedelta
from io import BytesIO
from uuid import UUID, uuid4

import httpx
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from sqlalchemy.ext.asyncio import async_sessionmaker
from tests.integration.backend.database import test_indicative_entry_postgres as existing
from tests.integration.backend.database.test_product_price_scale_evidence_postgres import (
    RESULT,
    engine_for,
)
from tests.integration.backend.test_realized_gross_report_postgres import (
    DECLARATION,
    _client,
    _state,
)
from tests.integration.backend.test_trade_capture_safety import BASE, WORKSPACE, purchase
from tests.integration.backend.test_usd_chf_currency_references import _migrate

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
from app.features.position_monitoring.domain.indicative_policy import V2_POLICY
from app.features.position_monitoring.service import indicative_entry_sessions as sessions
from app.features.position_monitoring.service.indicative_entry_read import IndicativeEntryReader
from app.features.position_monitoring.service.indicative_entry_runtime import IndicativeEntryRuntime
from app.features.product.service.review_evidence import record_original_kid
from app.providers.product_review_documents import fetch_original, kid_url

indicative_database = existing.indicative_database
forbid_outbound_http = existing.forbid_outbound_http


def synthetic_kid() -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
            NameObject("/Encoding"): NameObject("/WinAnsiEncoding"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
    )
    stream = DecodedStreamObject()
    lines = (
        "Synthetic test document. Basisinformationsblatt Optionsschein DE000JY557T1",
        "Basiswert ISIN US0028241000",
        "Festgelegte Währung: EUR",
        "Kursnotierung: Stücknotiz",
        "Referenzstelle: New York Stock Exchange",
    )
    stream.set_data(
        (
            "BT /F1 10 Tf 12 TL 40 730 Td " + " T* ".join(f"({line}) Tj" for line in lines) + " ET"
        ).encode("cp1252")
    )
    page[NameObject("/Contents")] = stream
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


async def prepare_scope(client):
    venues = (await client.get("/api/v1/market-reference-data/trading-venues")).json()["items"]
    selected = {}
    for mic, zone, country in (("XNYS", "America/New_York", "US"), ("XSTU", "Europe/Berlin", "DE")):
        venue = next((item for item in venues if item["mic"] == mic), None)
        if venue is None:
            response = await client.post(
                "/api/v1/market-reference-data/trading-venues",
                json={
                    "mic": mic,
                    "name": f"Synthetic {mic}",
                    "country_code": country,
                    "timezone": zone,
                },
            )
            assert response.status_code == 201, response.text
            venue = response.json()
        selected[mic] = venue
    issuer = await client.post(
        "/api/v1/market-reference-data/issuers",
        json={"legal_name": "J.P. Morgan Synthetic Test", "display_name": "Synthetic issuer"},
    )
    assert issuer.status_code == 201, issuer.text
    underlying = await client.post(
        "/api/v1/underlyings",
        json={
            "name": "Synthetic reference asset",
            "isin": "US0028241000",
            "type": "STOCK",
            "primary_listing": {
                "trading_venue_id": selected["XNYS"]["id"],
                "ticker": "SYNTHETIC",
                "currency_code": "USD",
            },
        },
    )
    assert underlying.status_code == 201, underlying.text
    product = await client.post(
        "/api/v1/warrants",
        json={
            "issuer_id": issuer.json()["id"],
            "underlying_id": underlying.json()["id"],
            "display_name": "Synthetic V2 current-unit review warrant",
            "isin": "DE000JY557T1",
            "option_direction": "CALL",
            "strike": "135",
            "maturity_date": "2099-12-31",
            "ratio": "0.1",
        },
    )
    assert product.status_code == 201, product.text
    warrant = product.json()
    listing = await client.post(
        f"/api/v1/warrants/{warrant['id']}/listings",
        json={"trading_venue_id": selected["XSTU"]["id"], "quotation_currency_code": "EUR"},
    )
    assert listing.status_code == 201, listing.text
    anchor = datetime.now(UTC).date() - timedelta(days=50)
    captured = await client.post(
        BASE + "/purchases/external",
        json={
            **purchase(warrant["id"], day=anchor.isoformat(), quantity=100),
            "price_per_unit": "2.00",
            "currency_confirmation": DECLARATION,
        },
    )
    assert captured.status_code == 201, captured.text
    return {
        "product": warrant,
        "capture": captured.json(),
        "listing": listing.json(),
        "anchor": anchor,
    }


async def store_delayed_quote(database, scope):
    at = datetime.now(UTC)
    provider = MarketDataProvider.BOERSE_STUTTGART_DELAYED
    listing = UUID(scope["listing"]["id"])
    factory = async_sessionmaker(database.engine, expire_on_commit=False)
    async with factory() as session:
        session.add(
            WarrantProviderMappingModel(
                id=uuid4(),
                workspace_id=UUID(WORKSPACE),
                warrant_listing_id=listing,
                provider=provider,
                provider_symbol=scope["product"]["isin"],
                provider_exchange_code="XSTU",
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
        # The purchase already saved a missing-source decision before this
        # synthetic mapping existed. Initial selection must preserve that fact;
        # the existing reconciliation owner adds the newly verified successor.
        previous = await selector.select_once(
            workspace_id=UUID(WORKSPACE),
            position_id=UUID(scope["capture"]["position"]["id"]),
            warrant_id=UUID(scope["product"]["id"]),
            selected_at=at,
        )
        assert previous.selection_status == "NO_VERIFIED_QUOTE_SOURCE"
        reconciled = await selector.reconcile(
            workspace_id=UUID(WORKSPACE),
            position_id=UUID(scope["capture"]["position"]["id"]),
            warrant_id=UUID(scope["product"]["id"]),
            selected_at=at,
        )
        selected = reconciled.selection
        assert reconciled.changed and selected is not None
        assert selected.selection_status == "SELECTED"
        assert selected.provider == provider.value and selected.warrant_listing_id == listing
        assert selected.evidence["previous_selection_id"] == str(previous.id)
        assert (
            previous.superseded_at == at and previous.selection_status == "NO_VERIFIED_QUOTE_SOURCE"
        )
        await session.commit()
        result = MarketDataResult(
            data=WarrantQuoteSnapshot(
                warrant_listing_id=listing,
                bid="1.50",
                ask="1.60",
                currency="EUR",
                provider_symbol=scope["product"]["isin"],
                provider_exchange_code="XSTU",
                observed_at=at - timedelta(seconds=900),
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
                workspace_id=UUID(WORKSPACE),
                warrant_listing_id=listing,
                provider=provider.value,
                identity_key=selected.identity_key,
                payload=RESULT.dump_python(result, mode="json"),
            )
        )
        await session.commit()
    return at


def test_automatic_v2_current_document_reference_calendar_to_durable_notice(
    indicative_database, monkeypatch
):
    _migrate(indicative_database, "head")

    async def exercise():
        engine = engine_for(indicative_database)
        try:
            async with _client(indicative_database) as (client, database):
                scope = await prepare_scope(client)
                now = datetime.now(UTC)
                original_calendar = b"Synthetic test: weekdays 09:30-16:00 New York; no exceptions."
                definition = replace(
                    NYSE_CALENDAR,
                    source_version="synthetic-v2-calendar-owner-contract",
                    binding=replace(
                        NYSE_CALENDAR.binding,
                        valid_from=date(now.year - 1, 1, 1),
                        valid_through=date(now.year, 12, 31),
                    ),
                    closed_dates=(),
                    early_closes=(),
                    opens_at=time(9, 30),
                    closes_at=time(16),
                    sources=(
                        (
                            "https://example.invalid/synthetic-calendar",
                            hashlib.sha256(original_calendar).hexdigest(),
                        ),
                    ),
                )
                monkeypatch.setattr(calendars, "NYSE_CALENDAR", definition)
                monkeypatch.setattr(sessions, "NYSE_CALENDAR", definition)
                source = kid_url("J.P. Morgan Synthetic Test", scope["product"]["isin"])
                document = synthetic_kid()
                requests = []

                def transport(request):
                    requests.append(str(request.url))
                    assert str(request.url) in {source, definition.sources[0][0]}
                    return httpx.Response(
                        200, content=document if str(request.url) == source else original_calendar
                    )

                async with httpx.AsyncClient(
                    transport=httpx.MockTransport(transport), trust_env=False
                ) as http:
                    factory = async_sessionmaker(database.engine, expire_on_commit=False)
                    async with factory() as session:
                        original = await fetch_original(http, source)
                        await record_original_kid(
                            session,
                            workspace_id=UUID(WORKSPACE),
                            warrant_id=UUID(scope["product"]["id"]),
                            source_reference=source,
                            document=original,
                            retrieved_at=now,
                            now=now,
                        )
                        await calendars.acquire_nyse_calendar(
                            session, http, workspace_id=UUID(WORKSPACE), now=now
                        )
                        await session.commit()
                assert len(requests) == 2
                await store_delayed_quote(database, scope)
                at = datetime.now(UTC)
                before = await _state(engine)
                assert not before["product_price_scale_evidence"]
                assert not before["market_session_evidence"]
                first = await existing.evaluate(
                    engine, scope, at, policy=V2_POLICY, notifications_enabled=False
                )
                assert (
                    first.outcome == "BELOW_ENTRY"
                    and first.loss_episode_active
                    and first.review_due
                )
                assert not first.data_problem_active and first.alerts_created == 2
                state = await _state(engine)
                row = existing.assessment(state, first)
                assert row["result"]["original_bid_at"] is None
                assert row["result"]["evaluation_mode"] == "DELAYED_SOURCE_BID"
                assert row["inputs"]["product_scale"]["quality"] == "CURRENT_UNIT_HISTORY_ASSUMED"
                assert (
                    row["inputs"]["comparison_sessions"]["calendar"]["entry_day_precision"]
                    == "CONSERVATIVE_DATE_BOUND"
                )
                assert row["inputs"]["product_scale"]["owner_assessment"]["status"] == "MISSING"
                for _ in range(2):
                    restarted = await IndicativeEntryRuntime(database, scope=V2_POLICY.scope).run()
                    assert restarted.positions_evaluated == 1 and restarted.position_errors == 0
                    assert restarted.alerts_created == restarted.notifications_created == 0
                assert await _state(engine) == state
                report = await IndicativeEntryReader(engine, scope=V2_POLICY.scope).read(
                    UUID(WORKSPACE),
                    UUID(scope["capture"]["trade"]["id"]),
                    UUID(scope["capture"]["position"]["id"]),
                )
                assert report.latest_assessment.history_continuity_assumed
                assert report.latest_assessment.session_day_precision == "CONSERVATIVE_DATE_BOUND"
                assert report.qualified_b04 is report.full_baseline_activated is False
                assert await _state(engine) == state
                assert state["execution_records"] == before["execution_records"]
                assert state["positions"] == before["positions"]
                assert state["notifications"] == []
        finally:
            await engine.dispose()

    asyncio.run(exercise())
