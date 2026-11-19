"""Real owners and migrations in UUID-isolated synthetic PostgreSQL only.

Original-shaped PDF/HTML bytes, explicit personal exit choice, documented
calendar import, actual BUY/SELL/corrections and the durable outbox are composed
without any quote. All HTTP transports are intercepted; nothing is delivered.
"""

import asyncio
import base64
import hashlib
import json
from datetime import UTC, date, datetime, time, timedelta
from unittest.mock import AsyncMock
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import httpx
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from tests.integration.backend.database import test_saved_quote_evidence_postgres as saved
from tests.integration.backend.database.test_product_price_scale_evidence_postgres import engine_for
from tests.integration.backend.test_realized_gross_report_postgres import _client, _state
from tests.integration.backend.test_trade_capture_safety import BASE, WORKSPACE
from tests.integration.backend.test_usd_chf_currency_references import _migrate
from tests.unit.backend.providers.product_review_document_fixture import synthetic_kid_pdf

from app.core.config import Environment, Settings
from app.database import DatabaseManager
from app.features.market_data.service import review_calendars
from app.features.notification.persistence.durable_delivery import (
    SqlAlchemyDurableNotificationDeliveryStore,
)
from app.features.notification.service.creation import AlertNotificationService
from app.features.position_monitoring.domain.product_deadline_review import RULE_SCOPE
from app.features.position_monitoring.service.product_deadline_review import (
    ProductDeadlineReviewService,
)
from app.features.position_monitoring.service.product_deadline_review_runtime import (
    ProductDeadlineReviewRuntime,
)
from app.features.product.service.review_evidence import record_original_kid

deadline_database = saved.quote_database
forbid_outbound_http = saved.forbid_outbound_http
ISIN, WKN, UNDERLYING = "DE000TEST124", "TEST12", "US00SYNTH011"
ZONE = ZoneInfo("Europe/Berlin")
ASSESSMENTS, EPISODES = "product_deadline_assessments", "product_deadline_episodes"


def listing_html(day, *, label="Letzter Börsenhandelstag", conflict=False):
    rows = f"<tr><td>{label}</td><td>{day:%d.%m.%Y}</td></tr>"
    if conflict:
        rows += f"<tr><td>{label}</td><td>{day - timedelta(days=1):%d.%m.%Y}</td></tr>"
    return (
        f"<html><head><title>Synthetic deadline product - {WKN} - Börse Stuttgart (XSTU)</title>"
        '<link rel="canonical" href="https://www.boerse-stuttgart.de/de-de/produkte/'
        f'hebelprodukte/optionsscheine/stuttgart/{WKN.lower()}/"></head><body>'
        "<section><h1>Synthetic stock/OS/Call [100]/Synthetic issuer</h1>"
        f"WKN {WKN} ISIN {ISIN}</section>"
        f'<div id="MasterDataBlock-synthetic">Stammdaten WKN {WKN} ISIN {ISIN}'
        f"<table>{rows}</table></div></body></html>"
    ).encode()


async def post(client, path, payload, status=201):
    response = await client.post(path, json=payload)
    assert response.status_code == status, response.text
    return response.json()


async def prepare(client, database, *, with_calendar=True, product_term=None):
    today = datetime.now(UTC).astimezone(ZONE).date()
    term = product_term or today + timedelta(days=21)
    venues = (await client.get("/api/v1/market-reference-data/trading-venues")).json()["items"]
    primary = next(row for row in venues if row["mic"] == "XETR")
    venue = next((row for row in venues if row["mic"] == "XSTU"), None)
    if venue is None:
        venue = await post(
            client,
            "/api/v1/market-reference-data/trading-venues",
            {
                "mic": "XSTU",
                "name": "Synthetic product deadline fixture venue",
                "country_code": "DE",
                "timezone": "Europe/Berlin",
            },
        )
    issuer = await post(
        client,
        "/api/v1/market-reference-data/issuers",
        {
            "legal_name": "BNP Paribas",
            "display_name": "Synthetic deadline document issuer fixture",
        },
    )
    underlying = await post(
        client,
        "/api/v1/underlyings",
        {
            "name": "Synthetic deadline stock",
            "type": "STOCK",
            "isin": UNDERLYING,
            "primary_listing": {
                "trading_venue_id": primary["id"],
                "ticker": "SYNTHDEADLINE",
                "currency_code": "EUR",
            },
        },
    )
    product = await post(
        client,
        "/api/v1/warrants",
        {
            "issuer_id": issuer["id"],
            "underlying_id": underlying["id"],
            "display_name": "Synthetic original product deadline test",
            "isin": ISIN,
            "wkn": WKN,
            "option_direction": "CALL",
            "strike": "100",
            "maturity_date": term.isoformat(),
            "ratio": "0.1",
        },
    )
    listing = await post(
        client,
        f"/api/v1/warrants/{product['id']}/listings",
        {
            "trading_venue_id": venue["id"],
            "quotation_currency_code": "EUR",
        },
    )
    anchor = today - timedelta(days=40)
    capture = await post(
        client,
        BASE + "/purchases/external",
        {
            "product_id": product["id"],
            "quantity": 100,
            "price_per_unit": "2.00",
            "executed_on": anchor.isoformat(),
            "execution_timezone": "Europe/Berlin",
            "request_id": str(uuid4()),
        },
    )
    document = synthetic_kid_pdf(
        f"Basisinformationsblatt Optionsschein {ISIN} Basiswert {UNDERLYING} "
        "Währung des Produkts: EUR Kursnotierung: Stücknotiz "
        "Referenzstelle: New York Stock Exchange Bewertungstag Der Ausübungstag bzw. der "
        f"{term:%d.%m.%Y}"
    )
    async with async_sessionmaker(database.engine, expire_on_commit=False)() as session:
        now = datetime.now(UTC)
        await record_original_kid(
            session,
            workspace_id=UUID(WORKSPACE),
            warrant_id=UUID(product["id"]),
            source_reference=f"https://kid.bnpparibas.com/{ISIN}_DE.pdf",
            document=document,
            retrieved_at=now,
            now=now,
        )
        await session.commit()
    source_url = f"/api/v1/warrants/{product['id']}/deadline-listing-terms"
    imported = await post(
        client,
        source_url + "/imports",
        {
            "document_base64": base64.b64encode(listing_html(term)).decode(),
        },
    )
    assert imported["status"] == "AVAILABLE"
    choice_url = f"/api/v1/warrants/{product['id']}/deadline-exit-listing"
    choice = (await client.get(choice_url)).json()
    assert choice["status"] == "MISSING" and choice["selected_listing_id"] is None
    selected = next(
        row for row in choice["available_listings"] if row["listing_id"] == listing["id"]
    )
    body = {
        "listing_id": selected["listing_id"],
        "expected_revision_number": choice["revision_number"],
        "expected_terms_id": choice["terms_id"],
        "expected_listing_version": selected["listing_version"],
        "expected_venue_version": selected["venue_version"],
    }
    response = await client.put(choice_url, json=body)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "AVAILABLE"
    scope = {
        "product": product,
        "listing": listing,
        "venue": venue,
        "capture": capture,
        "today": today,
        "term": term,
        "anchor": anchor,
        "source_url": source_url,
        "choice_url": choice_url,
        "choice_body": body,
    }
    if with_calendar:
        await import_calendar(client, scope)
    return scope


async def import_calendar(client, scope):
    return await post(
        client,
        "/api/v1/market-data/session-evidence/imports",
        saved.calendar_import(
            kind="WARRANT",
            instrument_id=scope["product"]["id"],
            listing_id=scope["listing"]["id"],
            venue_id=scope["venue"]["id"],
            mic="XSTU",
            zone="Europe/Berlin",
            anchor=scope["anchor"],
            start=min(scope["today"] - timedelta(days=10), scope["term"] - timedelta(days=40)),
            end=scope["term"] - timedelta(days=1),
        ),
    )


async def evaluate(engine, scope, *, now=None, notifications=True):
    async with async_sessionmaker(engine, expire_on_commit=False, autoflush=False)() as session:
        return await ProductDeadlineReviewService(session).evaluate(
            workspace_id=UUID(WORKSPACE),
            trade_id=UUID(scope["capture"]["trade"]["id"]),
            position_id=UUID(scope["capture"]["position"]["id"]),
            notifications_enabled=notifications,
            now=now,
        )


def active(state):
    return {row["kind"]: row for row in state[EPISODES] if row["closed_at"] is None}


def test_real_originals_to_durable_hint_gap_recovery_parallel_restart_and_passive_read(
    deadline_database,
    monkeypatch,
):
    _migrate(deadline_database, "head")

    async def exercise():
        engine = engine_for(deadline_database)
        try:
            async with _client(deadline_database) as (client, database):
                scope = await prepare(client, database)
                before = await _state(engine)
                with monkeypatch.context() as patch:
                    patch.setattr(
                        AlertNotificationService,
                        "create_telegram",
                        AsyncMock(side_effect=RuntimeError("Synthetic outbox failure")),
                    )
                    with pytest.raises(RuntimeError, match="Synthetic outbox failure"):
                        await evaluate(engine, scope)
                assert await _state(engine) == before
                results = await asyncio.wait_for(
                    asyncio.gather(
                        *(evaluate(engine, scope) for _ in range(3)),
                    ),
                    timeout=30,
                )
                state = await _state(engine)
                assert len(state[ASSESSMENTS]) == len(state[EPISODES]) == 1
                assert sum(row.alerts_created for row in results) == 1
                assert {row.outcome for row in results} == {"WARNING_DUE"}
                assert len(state["notifications"]) == 1
                assert state["product_price_scale_evidence"] == []
                assert state["warrant_quote_observations"] == []
                assert state["position_baseline_evidence"] == []
                assert state["hebeltrader_loss_assessments"] == []
                original = active(state)["DEADLINE_REVIEW"]
                alert = next(row for row in state["alerts"] if row["id"] == original["alert_id"])
                assert alert["observed_value"] is None and alert["threshold_value"] is None
                assert alert["price_context"]["qualified_b05"] == "false"
                assert alert["price_context"]["product_cutoff_status"] == "UNVERIFIED"
                trade = scope["capture"]["trade"]["id"]
                read_url = f"/api/v1/position-monitoring/trades/{trade}/product-deadline-review"
                response = await client.get(
                    read_url, params={"position_id": scope["capture"]["position"]["id"]}
                )
                assert response.status_code == 200, response.text
                assert response.json()["read_status"] == "READ_ONLY"
                assert response.json()["activation_status"] == "NOT_ACTIVATED"
                assert response.json()["scope"] == RULE_SCOPE
                assert await _state(engine) == state
                gap_source = await post(
                    client,
                    scope["source_url"] + "/imports",
                    {
                        "document_base64": base64.b64encode(
                            listing_html(scope["term"], conflict=True)
                        ).decode(),
                    },
                )
                assert gap_source["status"] == "UNSUITABLE"
                gap = await evaluate(engine, scope)
                assert gap.outcome == "UNAVAILABLE" and gap.data_problem_active
                state = await _state(engine)
                assert active(state)["DEADLINE_REVIEW"]["id"] == original["id"]
                assert "DATA_UNAVAILABLE" in active(state)
                pending = next(
                    row for row in state["notifications"] if row["alert_id"] == original["alert_id"]
                )
                prepared = await SqlAlchemyDurableNotificationDeliveryStore(
                    database, deadline_delivery_enabled=True
                ).prepare(
                    notification_id=pending["id"],
                    attempt_id=uuid4(),
                    now=datetime.now(UTC),
                    max_attempts=3,
                    stale_before=datetime.now(UTC) - timedelta(minutes=5),
                )
                assert prepared.attempt is None
                assert prepared.terminal_result.error_code == "REVIEW_DEADLINE_INPUTS_UNAVAILABLE"
                assert prepared.terminal_result.retryable is True
                paused = await _state(engine)
                assert (
                    next(row for row in paused["notifications"] if row["id"] == pending["id"])[
                        "status"
                    ]
                    == "PENDING"
                )
                assert not any(
                    row["notification_id"] == pending["id"]
                    for row in paused["notification_delivery_attempts"]
                )
                await post(
                    client,
                    scope["source_url"] + "/imports",
                    {
                        "document_base64": base64.b64encode(listing_html(scope["term"])).decode(),
                    },
                )
                recovered = await evaluate(engine, scope)
                state = await _state(engine)
                assert recovered.outcome == "WARNING_DUE" and recovered.alerts_created == 0
                assert active(state)["DEADLINE_REVIEW"]["id"] == original["id"]
                assert "DATA_UNAVAILABLE" not in active(state)
                single_connection = DatabaseManager(
                    Settings(
                        _env_file=None,
                        environment=Environment.TEST,
                        database_url=deadline_database,
                        database_pool_size=1,
                        database_max_overflow=0,
                    )
                )
                try:
                    restored = await asyncio.wait_for(
                        SqlAlchemyDurableNotificationDeliveryStore(
                            single_connection, deadline_delivery_enabled=True
                        ).prepare(
                            notification_id=pending["id"],
                            attempt_id=uuid4(),
                            now=datetime.now(UTC),
                            max_attempts=3,
                            stale_before=datetime.now(UTC) - timedelta(minutes=5),
                        ),
                        timeout=20,
                    )
                    assert restored.notification.id == pending["id"]
                    assert restored.attempt is not None and restored.attempt.attempt_number == 1
                finally:
                    await single_connection.dispose()
                restarted = create_async_engine(deadline_database, pool_size=1, max_overflow=0)
                try:
                    replay = await asyncio.wait_for(evaluate(restarted, scope), timeout=20)
                    assert (
                        replay.unchanged
                        and replay.alerts_created == replay.notifications_created == 0
                    )
                finally:
                    await restarted.dispose()
        finally:
            await engine.dispose()

    asyncio.run(exercise())


def test_owner_corrections_preserve_event_and_full_sale_cancels_pending_without_quote(
    deadline_database,
):
    _migrate(deadline_database, "head")

    async def exercise():
        engine = engine_for(deadline_database)
        try:
            async with _client(deadline_database) as (client, database):
                scope = await prepare(client, database)
                first = await evaluate(engine, scope)
                initial = await _state(engine)
                event_id = active(initial)["DEADLINE_REVIEW"]["id"]
                trade = scope["capture"]["trade"]["id"]
                for action, quantity in (("sales", 30), ("purchases", 30)):
                    await post(
                        client,
                        f"{BASE}/trades/{trade}/{action}",
                        {
                            "quantity": quantity,
                            "price_per_unit": "3.00",
                            "executed_on": (scope["anchor"] + timedelta(days=5)).isoformat(),
                            "execution_timezone": "Europe/Berlin",
                            "request_id": str(uuid4()),
                        },
                    )
                    result = await evaluate(engine, scope)
                    assert result.outcome == first.outcome and not result.unchanged
                    assert result.alerts_created == 0
                    assert active(await _state(engine))["DEADLINE_REVIEW"]["id"] == event_id
                buy = scope["capture"]["execution"]["id"]
                await post(
                    client,
                    f"{BASE}/trades/{trade}/executions/{buy}/corrections",
                    {
                        "side": "BUY",
                        "quantity": 100,
                        "price_per_unit": "4.00",
                        "executed_on": scope["anchor"].isoformat(),
                        "execution_timezone": "Europe/Berlin",
                    },
                )
                corrected = await evaluate(engine, scope)
                state = await _state(engine)
                assert corrected.alerts_created == 0 and len(state[ASSESSMENTS]) == 4
                assert len({row["owner_basis_id"] for row in state[ASSESSMENTS]}) == 4
                assert (
                    next(row for row in state[ASSESSMENTS] if row["id"] == first.assessment_id)
                    == initial[ASSESSMENTS][0]
                )
                await post(
                    client,
                    f"{BASE}/trades/{trade}/sales",
                    {
                        "quantity": 100,
                        "price_per_unit": "3.00",
                        "executed_on": (scope["anchor"] + timedelta(days=10)).isoformat(),
                        "execution_timezone": "Europe/Berlin",
                        "request_id": str(uuid4()),
                    },
                )
                pending = next(row for row in state["notifications"] if row["status"] == "PENDING")
                preparation = await SqlAlchemyDurableNotificationDeliveryStore(
                    database, deadline_delivery_enabled=True
                ).prepare(
                    notification_id=pending["id"],
                    attempt_id=uuid4(),
                    now=datetime.now(UTC),
                    max_attempts=3,
                    stale_before=datetime.now(UTC) - timedelta(minutes=5),
                )
                assert preparation.attempt is None
                assert preparation.terminal_result.error_code == "REVIEW_POSITION_CLOSED"
                finished = await ProductDeadlineReviewRuntime(
                    database, scope="INDICATIVE_ENTRY_V2"
                ).run()
                assert finished.positions_evaluated == 1 and finished.position_errors == 0
                assert finished.alerts_created == finished.notifications_created == 0
                state = await _state(engine)
                assert active(state) == {}
                assert len(state[EPISODES]) == 1
                assert all(row["status"] != "PENDING" for row in state["notifications"])
                assert state["hebeltrader_loss_assessments"] == []
        finally:
            await engine.dispose()

    asyncio.run(exercise())


def test_late_first_read_and_corrected_deadline_do_not_invent_earlier_deliveries(deadline_database):
    _migrate(deadline_database, "head")

    async def exercise():
        engine = engine_for(deadline_database)
        try:
            async with _client(deadline_database) as (client, database):
                scope = await prepare(client, database)
                at = datetime.combine(scope["today"] + timedelta(days=3), time(12), ZONE)
                first = await evaluate(engine, scope, now=at)
                assert first.outcome == "CALENDAR_SESSION_ENDED"
                state = await _state(engine)
                assert (
                    len(state[ASSESSMENTS])
                    == len(state[EPISODES])
                    == len(state["notifications"])
                    == 1
                )
                assert state["alerts"][0]["detected_at"] == at
                context = state["alerts"][0]["price_context"]
                assert datetime.fromisoformat(context["scheduled_at"]) < at
                assert context["deadline_stage"] == "CALENDAR_SESSION_ENDED"
                # Corrected original last-exchange day changes the effective
                # Product premise. It does not rewrite the already-recorded event.
                await post(
                    client,
                    scope["source_url"] + "/imports",
                    {
                        "document_base64": base64.b64encode(
                            listing_html(scope["term"] - timedelta(days=1))
                        ).decode(),
                    },
                )
                revised = await evaluate(engine, scope, now=at + timedelta(seconds=1))
                assert revised.alerts_created == 1
                state = await _state(engine)
                assert len(state[ASSESSMENTS]) == len(state[EPISODES]) == 2
                assert len(active(state)) == 1
                assert sum(row["status"] == "PENDING" for row in state["notifications"]) == 1
                assert len([row for row in state[EPISODES] if row["close_reason"]]) == 1
        finally:
            await engine.dispose()

    asyncio.run(exercise())


def test_day_only_original_calendar_flows_without_invented_hours_and_cannot_bypass_withdrawal(
    deadline_database,
    monkeypatch,
):
    _migrate(deadline_database, "head")

    async def exercise():
        engine = engine_for(deadline_database)
        try:
            async with _client(deadline_database) as (client, database):
                scope = await prepare(
                    client, database, with_calendar=False, product_term=date(2026, 12, 18)
                )
                # Synthetic pin and intercepted bytes exercise the actual
                # acquisition/integrity owner; they qualify no real provider.
                raw = json.dumps(
                    {"synthetic_original": True, "days": review_calendars.xstu_day_rows()}
                ).encode()
                monkeypatch.setattr(
                    review_calendars, "XSTU_DAY_URL", "https://synthetic.example.invalid/calendar"
                )
                monkeypatch.setattr(
                    review_calendars, "XSTU_DAY_SHA256", hashlib.sha256(raw).hexdigest()
                )
                requests = []

                def respond(request):
                    requests.append(request)
                    assert str(request.url) == review_calendars.XSTU_DAY_URL
                    return httpx.Response(200, content=raw)

                async with (
                    httpx.AsyncClient(
                        transport=httpx.MockTransport(respond), trust_env=False
                    ) as http,
                    async_sessionmaker(database.engine, expire_on_commit=False)() as session,
                ):
                    await review_calendars.acquire_xstu_day_calendar(
                        session,
                        http,
                        workspace_id=UUID(WORKSPACE),
                        now=datetime.now(UTC),
                    )
                    await session.commit()
                assert len(requests) == 1
                at = max(datetime.now(UTC), datetime(2026, 12, 19, 12, tzinfo=UTC))
                reviewed = await evaluate(engine, scope, now=at)
                assert reviewed.outcome == "DEADLINE_DAY_PASSED"
                state = await _state(engine)
                context = state["alerts"][0]["price_context"]
                assert context["calendar_precision"] == "DAY_ONLY"
                assert context["calendar_calculation_scope"] == "DAY_ONLY_CALENDAR_REVIEW"
                assert context["scheduled_on"] is not None and context["scheduled_at"] is None
                assert (
                    context["exit_session_opens_at"]
                    is context["calendar_session_closes_at"]
                    is None
                )
                assert context["product_cutoff_status"] == "UNVERIFIED"
                strict = await import_calendar(client, scope)
                body = saved.calendar_import(
                    kind="WARRANT",
                    instrument_id=scope["product"]["id"],
                    listing_id=scope["listing"]["id"],
                    venue_id=scope["venue"]["id"],
                    mic="XSTU",
                    zone="Europe/Berlin",
                    anchor=scope["anchor"],
                    start=scope["term"] - timedelta(days=40),
                    end=scope["term"] - timedelta(days=1),
                )
                manifest = json.loads(body["manifest_json"])
                manifest["evidence_status"] = "WITHDRAWN"
                manifest["calendar_version"] = "synthetic-withdrawn-v2"
                body["supersedes_revision_id"] = strict["id"]
                body["manifest_json"] = json.dumps(manifest)
                body["manifest_sha256"] = hashlib.sha256(body["manifest_json"].encode()).hexdigest()
                await post(client, "/api/v1/market-data/session-evidence/imports", body)
                forbidden_fallback = AsyncMock(
                    side_effect=AssertionError("Withdrawal must not fall back")
                )
                monkeypatch.setattr(
                    review_calendars, "read_review_deadline_calendar", forbidden_fallback
                )
                unavailable = await evaluate(engine, scope, now=at + timedelta(seconds=1))
                assert unavailable.outcome == "UNAVAILABLE" and unavailable.reminder_active
                assert "SESSION_EVIDENCE_WITHDRAWN" in unavailable.reasons
                forbidden_fallback.assert_not_awaited()
        finally:
            await engine.dispose()

    asyncio.run(exercise())


def test_recurring_runtime_creates_one_workspace_hint_with_delivery_disabled(deadline_database):
    _migrate(deadline_database, "head")

    async def exercise():
        engine = engine_for(deadline_database)
        try:
            async with _client(deadline_database) as (client, database):
                await prepare(client, database)
                before = await _state(engine)
                paused = await ProductDeadlineReviewRuntime(
                    database, scope="INDICATIVE_ENTRY_V1"
                ).run()
                assert paused.positions_evaluated == 0 and await _state(engine) == before
                runner = ProductDeadlineReviewRuntime(database, scope="INDICATIVE_ENTRY_V2")
                first, repeat = await runner.run(), await runner.run()
                assert first.positions_evaluated == repeat.positions_evaluated == 1
                assert first.position_errors == repeat.position_errors == 0
                assert first.alerts_created == 1 and repeat.alerts_created == 0
                assert first.notifications_created == repeat.notifications_created == 0
                state = await _state(engine)
                assert len(state[ASSESSMENTS]) == len(state[EPISODES]) == 1
                assert state["notifications"] == [] and state["warrant_quote_observations"] == []
        finally:
            await engine.dispose()

    asyncio.run(exercise())
