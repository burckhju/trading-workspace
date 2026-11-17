"""Synthetic B04 owner flow on actual, guarded, disposable PostgreSQL.

The production Frankfurt parser/adapter and retention journal consume only
intercepted HTTP. BUY/SELL/corrections, currency, product and calendar evidence
use their existing owners. The explicit registry below is a test dependency;
neither its invented supplier nor its simultaneous status point qualifies a
real provider or activates any installed monitoring scope.
"""

import asyncio
import base64
import hashlib
import json
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import httpx
import pytest
from app.core.config.frankfurt import FrankfurtQuoteSettings
from app.features.market_data.domain.enums import MarketDataProvider
from app.features.market_data.service.retained_quotes import RetainedWarrantQuoteProvider
from app.features.market_data.service.types import WarrantQuoteRequest
from app.features.notification.service.creation import AlertNotificationService
from app.features.position_monitoring.domain.hebeltrader_loss import RULE_SCOPE, RULE_VERSION
from app.features.position_monitoring.service import hebeltrader_loss as loss_commands
from app.features.position_monitoring.service.hebeltrader_b58_sources import (
    QUALIFIED_B58_PATHS,
    B58SourcePath,
    B58SourceRegistry,
)
from app.features.position_monitoring.service.hebeltrader_loss import HebeltraderLossService
from app.features.position_monitoring.service.hebeltrader_loss_runtime import HebeltraderLossRuntime
from app.features.position_monitoring.service.product_valuation import (
    ProductPositionValuationService,
)
from app.features.position_monitoring.service.quote_sources import (
    MultiSourceWarrantQuoteResolver,
    NamedWarrantQuoteSource,
)
from app.features.position_monitoring.service.runner import PositionMonitoringRunner
from app.features.position_monitoring.service.runtime import PositionMonitoringRuntimeService
from app.providers.frankfurt_quotes.adapter import FrankfurtWarrantQuoteAdapter
from app.providers.frankfurt_quotes.client import FrankfurtSnapshotClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tests.integration.backend.database import test_saved_quote_evidence_postgres as saved
from tests.integration.backend.database.test_product_price_scale_evidence_postgres import (
    engine_for,
    import_body,
    scale_url,
    seed_scope,
    store_quote_and_calendars,
)
from tests.integration.backend.database.test_product_price_scale_evidence_postgres import (
    state as read_database_state,
)
from tests.integration.backend.test_realized_gross_report_postgres import (
    DECLARATION,
    _client,
    _state,
)
from tests.integration.backend.test_trade_capture_safety import BASE, WORKSPACE
from tests.integration.backend.test_usd_chf_currency_references import _migrate

loss_database = saved.quote_database
forbid_outbound_http = saved.forbid_outbound_http

PROVIDER = MarketDataProvider.FRANKFURT_QUOTES
SOURCE = "synthetic-b04-postgres-only"
QUALIFICATION = "Synthetic test fixture; no independently verified real B58 supplier"
ASSESSMENTS = "hebeltrader_loss_assessments"
EPISODES = "hebeltrader_loss_episodes"
STATUS = "warrant_market_status_observations"


def synthetic_registry(scope):
    assert QUALIFIED_B58_PATHS == ()
    return B58SourceRegistry(
        (
            B58SourcePath(
                provider=PROVIDER.value,
                isin=scope["product"]["isin"],
                venue_mic="XFRA",
                source_contract="frankfurt-quotes-v1",
                source_reference=SOURCE,
                qualification_reference=QUALIFICATION,
                qualification_sha256=hashlib.sha256(QUALIFICATION.encode()).hexdigest(),
                bid_time_field="bid_at",
                status_field="trading_status",
                status_time_field="status_observed_at",
            ),
        )
    )


async def prepare(client, database):
    scope = await seed_scope(client)
    # Existing helper seeds the real mapping/selection and documented calendars.
    # Its initial last-success is replaced by the actual adapter below before
    # any B04 evaluation; it cannot match this test-only source registry.
    await store_quote_and_calendars(client, database, scope)
    response = await client.post(scale_url(scope) + "/imports", json=import_body(scope))
    assert response.status_code == 201, response.text
    scope["scale_revision"] = response.json()["id"]
    return scope


@asynccontextmanager
async def synthetic_source(
    database, scope, *, bid="1.50", status="OPEN", bid_at=None, http_error=False
):
    """Actual adapter -> retained price/status owners, never a mocked quote result."""
    at = datetime.now(UTC)
    original_bid_at = bid_at or at
    settings = FrankfurtQuoteSettings(
        enabled=True,
        usage_approved=True,
        contract_verified=True,
        source_name=SOURCE,
        snapshot_url="https://synthetic-b04.example.invalid/quotes",
        allowed_host="synthetic-b04.example.invalid",
    )
    payload = {
        "schema_version": "frankfurt-quotes-v1",
        "source": SOURCE,
        "generated_at": at.isoformat(),
        "delay_seconds": 0,
        "records": [
            {
                "isin": scope["product"]["isin"],
                "wkn": scope["product"]["wkn"],
                "mic": "XFRA",
                "currency": "EUR",
                "kind": "BID_ASK",
                "bid": bid,
                "ask": str(Decimal(bid) + Decimal("0.10")) if bid is not None else None,
                "bid_at": original_bid_at.isoformat() if bid is not None else None,
                "ask_at": original_bid_at.isoformat() if bid is not None else None,
                "trading_status": status,
                "status_observed_at": at.isoformat(),
            }
        ],
    }
    requests = []

    def respond(request):
        assert str(request.url) == settings.snapshot_url
        requests.append(request)
        return httpx.Response(503) if http_error else httpx.Response(200, json=payload)

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond), trust_env=False) as http:
        snapshots = FrankfurtSnapshotClient(settings, client=http, clock=lambda: at)
        provider = FrankfurtWarrantQuoteAdapter(
            database=database, settings=settings, snapshots=snapshots, clock=lambda: at
        )
        retained = RetainedWarrantQuoteProvider(
            database, provider, PROVIDER, capture_clock=lambda: at
        )
        yield at, retained, requests


async def supply(database, scope, **kwargs):
    async with synthetic_source(database, scope, **kwargs) as (at, retained, requests):
        result = await retained.get_warrant_listing_quote(
            WarrantQuoteRequest(
                workspace_id=UUID(WORKSPACE),
                warrant_listing_id=UUID(scope["listing"]["id"]),
                correlation_id=uuid4(),
                as_of=at,
                expected_currency="EUR",
            )
        )
    assert len(requests) == 1
    return at, result


async def evaluate(engine, scope, at, *, sources=None):
    sessions = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with sessions() as session:
        return await HebeltraderLossService(
            session, sources=sources or synthetic_registry(scope)
        ).evaluate(
            workspace_id=UUID(WORKSPACE),
            trade_id=UUID(scope["capture"]["trade"]["id"]),
            position_id=UUID(scope["capture"]["position"]["id"]),
            notifications_enabled=True,
            now=at,
        )


def assessment(state, result):
    return next(row for row in state[ASSESSMENTS] if row["id"] == result.assessment_id)


def assert_no_target_prerequisites(state):
    assert state["position_baseline_evidence"] == []
    assert state["position_baseline_execution_refs"] == []
    assert state["hebeltrader_target_assessments"] == []
    assert state["hebeltrader_target_requests"] == []


async def passive_report(client, engine, scope):
    before = await _state(engine)
    trade = scope["capture"]["trade"]["id"]
    url = f"/api/v1/position-monitoring/trades/{trade}/hebeltrader-loss"
    response = await client.get(url, params={"position_id": scope["capture"]["position"]["id"]})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["read_status"] == "READ_ONLY"
    assert body["activation_status"] == "NOT_ACTIVATED"
    assert body["runner_enabled"] is False
    assert body["full_baseline_activated"] is False
    assert body["definition_version"] == RULE_VERSION
    assert body["rule_scope"] == RULE_SCOPE
    assert body["source_qualification_references"] == []
    assert "B05" in body["remaining_scope"]
    assert await _state(engine) == before
    return body


def test_adapter_loss_gap_recovery_new_episode_atomicity_parallel_replay_and_restart(
    loss_database, monkeypatch
):
    _migrate(loss_database, "head")

    async def exercise():
        # An independent NullPool permits concurrent real trade-lock contenders
        # and their read-only snapshots without exhausting the tiny ASGI pool.
        engine = engine_for(loss_database)
        try:
            async with _client(loss_database) as (client, database):
                scope = await prepare(client, database)
                at, delivered = await supply(database, scope)
                assert delivered.data.bid == Decimal("1.50")
                assert delivered.data.original_evidence.source_reference == SOURCE
                assert delivered.data.original_evidence.bid.observed_at == at
                assert delivered.data.original_market_status.observed_at == at
                acquired = await _state(engine)
                assert len(acquired[STATUS]) == 1
                assert acquired[ASSESSMENTS] == acquired[EPISODES] == []
                assert_no_target_prerequisites(acquired)

                # An error after assessment+alert insertion must leave no partial
                # logical notice. Acquisition belongs to its separate owner.
                with monkeypatch.context() as patch:
                    patch.setattr(
                        AlertNotificationService,
                        "create_telegram",
                        AsyncMock(side_effect=RuntimeError("Synthetic outbox failure")),
                    )
                    with pytest.raises(RuntimeError, match="Synthetic outbox failure"):
                        await evaluate(engine, scope, at)
                assert await _state(engine) == acquired

                concurrent = await asyncio.gather(*(evaluate(engine, scope, at) for _ in range(3)))
                assert {result.outcome for result in concurrent} == {"LOSS"}
                assert len({result.assessment_id for result in concurrent}) == 1
                assert len({result.episode_id for result in concurrent}) == 1
                assert sum(result.alert_created for result in concurrent) == 1
                assert sum(result.notification_created for result in concurrent) == 1
                assert sum(result.unchanged for result in concurrent) == 2
                first = concurrent[0]
                opened = await _state(engine)
                assert len(opened[ASSESSMENTS]) == len(opened[EPISODES]) == 1
                assert len(opened["alerts"]) == len(opened["notifications"]) == 1
                assert opened["notifications"][0]["status"] == "PENDING"
                assert opened["notification_delivery_attempts"] == []
                original = assessment(opened, first)
                assert original["inputs"]["source_qualification"]["status"] == "QUALIFIED"
                assert original["result"]["completed_sessions_at_bid"] == 20
                assert Decimal(original["result"]["gross_entry"]) == Decimal("2.00")
                assert (
                    original["inputs"]["product_scale"]["evidence"]["revision_id"]
                    == scope["scale_revision"]
                )
                assert_no_target_prerequisites(opened)

                # A later price-less negative event survives the older price
                # last-success and the sampling slot; it does not end the loss.
                closed_at, closed_supply = await supply(database, scope, bid=None, status="CLOSED")
                assert closed_supply.data.retained is True
                closed = await evaluate(engine, scope, closed_at)
                assert closed.outcome == "NOT_ASSESSABLE"
                assert closed.episode_id == first.episode_id and closed.episode_active
                after_closed = await _state(engine)
                assert (
                    after_closed["warrant_quote_observations"]
                    == opened["warrant_quote_observations"]
                )
                status_inputs = assessment(after_closed, closed)["inputs"]["status_observations"]
                assert status_inputs["observed_status"] == "CLOSED"
                assert (
                    datetime.fromisoformat(
                        status_inputs["point_observations"][0]["original"]["observed_at"]
                    )
                    == closed_at
                )

                gap_at, gap_supply = await supply(database, scope, http_error=True)
                assert gap_supply.data.retained is True
                gap = await evaluate(engine, scope, gap_at)
                assert gap.outcome == "NOT_ASSESSABLE"
                assert gap.episode_id == first.episode_id and gap.episode_active
                after_gap = await _state(engine)
                gap_inputs = assessment(after_gap, gap)["inputs"]["status_observations"]
                assert gap_inputs["point_verdict"] == "NO_POINT_AT_EVENT"
                assert gap_inputs["latest_gap"]["original"] is None
                assert gap_inputs["latest_gap"]["reason"] == "FRANKFURT_HTTP_503"
                assert gap_inputs["latest_observations"][0]["original"]["status"] == "CLOSED"
                assert len(after_gap["alerts"]) == len(after_gap["notifications"]) == 1
                assert after_gap["notification_delivery_attempts"] == []
                gap_report = await passive_report(client, engine, scope)
                assert gap_report["latest_assessment"]["outcome"] == "NOT_ASSESSABLE"
                assert gap_report["active_episode"]["id"] == str(first.episode_id)

                recovered_at, _ = await supply(database, scope, bid="2.00")
                recovered = await evaluate(engine, scope, recovered_at)
                assert recovered.outcome == "RECOVERED" and not recovered.episode_active
                assert recovered.episode_id == first.episode_id
                recovery = await _state(engine)
                assert recovery[EPISODES][0]["closing_assessment_id"] == recovered.assessment_id
                assert recovery["alerts"][0]["resolved_at"] == recovered_at
                assert recovery["notifications"][0]["status"] == "FAILED"
                attempts = recovery["notification_delivery_attempts"]
                assert len(attempts) == 1 and attempts[0]["error_code"] == "B04_ALERT_RESOLVED"
                assert attempts[0]["provider_message_id"] is None
                assert attempts[0]["retryable"] is False

                final_at, _ = await supply(database, scope, bid="1.25")
                reopened = await evaluate(engine, scope, final_at)
                assert reopened.outcome == "LOSS" and reopened.episode_active
                assert reopened.episode_id != first.episode_id
                assert reopened.alert_created and reopened.notification_created
                final = await _state(engine)
                assert (
                    len(final[EPISODES]) == len(final["alerts"]) == len(final["notifications"]) == 2
                )
                assert {row["episode_number"] for row in final[EPISODES]} == {1, 2}
                assert len(final[ASSESSMENTS]) == 5
                assert (
                    len(final["execution_records"])
                    == len(final["execution_currency_confirmations"])
                    == 1
                )
                assert final["execution_records"] == acquired["execution_records"]
                assert final["positions"] == acquired["positions"]
                assert_no_target_prerequisites(final)
                report = await passive_report(client, engine, scope)
                assert report["active_episode"]["id"] == str(reopened.episode_id)
                assert report["assessment_count"] == 5 and report["episode_count"] == 2

            # New application, pool, sessions and service: current last-success
            # cannot manufacture an earlier evaluation or a delivered message.
            async with _client(loss_database) as (client, _database):
                restart = await evaluate(engine, scope, final_at)
                assert restart.unchanged and restart.assessment_id == reopened.assessment_id
                assert restart.episode_id == reopened.episode_id
                assert not restart.alert_created and not restart.notification_created
                assert await _state(engine) == final
                report = await passive_report(client, engine, scope)
                assert report["active_episode"]["episode_number"] == 2
        finally:
            await engine.dispose()

    asyncio.run(exercise())


def test_partial_sale_additional_buy_and_correction_keep_execution_owner_and_episode(loss_database):
    _migrate(loss_database, "head")

    async def exercise():
        engine = engine_for(loss_database)
        try:
            async with _client(loss_database) as (client, database):
                scope = await prepare(client, database)
                trade = scope["capture"]["trade"]["id"]
                initial_buy = scope["capture"]["execution"]["id"]
                at, _ = await supply(database, scope)
                first = await evaluate(engine, scope, at)
                assert first.outcome == "LOSS"
                initial = assessment(await _state(engine), first)
                basis_ids = {initial["owner_basis_id"]}
                execution_ids = [initial_buy]

                for action, quantity, price, offset, remaining, entry in (
                    ("sales", 40, "3.00", 5, 60, "2.00"),
                    ("purchases", 40, "4.00", 10, 100, "2.80"),
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
                    execution_ids.append(response.json()["execution"]["id"])
                    at, _ = await supply(database, scope)
                    result = await evaluate(engine, scope, at)
                    assert result.outcome == "LOSS" and result.episode_id == first.episode_id
                    assert not result.alert_created and not result.notification_created
                    row = assessment(await _state(engine), result)
                    basis_ids.add(row["owner_basis_id"])
                    assert row["result"]["remaining_quantity"] == remaining
                    assert Decimal(row["result"]["gross_entry"]) == Decimal(entry)
                    assert row["inputs"]["effective_execution_ids"] == execution_ids
                    assert row["inputs"]["entry"]["execution_id"] == initial_buy
                    assert (
                        row["inputs"]["product_scale"]["evidence"]["revision_id"]
                        == scope["scale_revision"]
                    )

                response = await client.post(
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
                assert response.status_code == 201, response.text
                replacement = response.json()["execution"]["id"]
                at, _ = await supply(database, scope)
                corrected = await evaluate(engine, scope, at)
                final = await _state(engine)
                row = assessment(final, corrected)
                basis_ids.add(row["owner_basis_id"])
                assert len(basis_ids) == 4
                assert corrected.outcome == "LOSS" and corrected.episode_id == first.episode_id
                assert not corrected.alert_created and not corrected.notification_created
                assert row["inputs"]["effective_execution_ids"] == [replacement, *execution_ids[1:]]
                assert row["inputs"]["entry"]["execution_id"] == replacement
                assert row["inputs"]["entry"]["executed_on"] == scope["anchor"].isoformat()
                assert row["result"]["remaining_quantity"] == 100
                assert Decimal(row["result"]["gross_entry"]) == Decimal("3.40")
                assert row["result"]["completed_sessions_at_bid"] == 20
                assert row["inputs"]["economic_basis"]["cost_basis_currency"] == "EUR"
                assert (
                    len(final["execution_records"])
                    == len(final["execution_currency_confirmations"])
                    == 4
                )
                assert len(final["product_price_scale_evidence"]) == 1
                assert len(final[ASSESSMENTS]) == 4
                assert (
                    len(final[EPISODES]) == len(final["alerts"]) == len(final["notifications"]) == 1
                )
                assert_no_target_prerequisites(final)
                assert assessment(final, first)["inputs"] == initial["inputs"]
                await passive_report(client, engine, scope)
        finally:
            await engine.dispose()

    asyncio.run(exercise())


async def install_twentieth_close(client, scope, closes_at):
    """A revised original calendar with 19 previous sessions and today's close."""
    response = await client.get(
        "/api/v1/market-data/session-evidence/current",
        params={
            "instrument_kind": "UNDERLYING",
            "instrument_id": scope["product"]["underlying_id"],
            "known_at": datetime.now(UTC).isoformat(),
        },
    )
    assert response.status_code == 200, response.text
    current = response.json()
    assert current["status"] == "AVAILABLE"
    binding = current["binding"]
    zone = ZoneInfo(binding["timezone"])
    closing_day = closes_at.astimezone(zone).date()
    body = saved.calendar_import(
        kind="UNDERLYING",
        instrument_id=binding["instrument_id"],
        listing_id=binding["listing_id"],
        venue_id=binding["trading_venue_id"],
        mic=binding["venue_mic"],
        zone=binding["timezone"],
        anchor=scope["anchor"],
        start=scope["anchor"],
        end=closing_day + timedelta(days=1),
    )
    manifest = json.loads(body["manifest_json"])
    manifest["calendar_version"] = "synthetic-twentieth-close-v2"
    for day in manifest["days"]:
        day_date = date.fromisoformat(day["session_date"])
        is_session = closing_day - timedelta(days=19) <= day_date <= closing_day
        day["status"] = "SESSION" if is_session else "CLOSED"
        if is_session:
            opening = datetime.combine(day_date, time.min, zone)
            closing = (
                closes_at if day_date == closing_day else datetime.combine(day_date, time(17), zone)
            )
            day["intervals"] = [{"opens_at": opening.isoformat(), "closes_at": closing.isoformat()}]
        else:
            day["intervals"] = []
    document = json.dumps(
        {
            "synthetic_original_source": True,
            "binding": manifest["binding"],
            "days": manifest["days"],
        },
        indent=2,
    ).encode()
    document_hash = hashlib.sha256(document).hexdigest()
    manifest["source_document_sha256"] = document_hash
    manifest_json = json.dumps(manifest, indent=2) + "\n"
    body.update(
        supersedes_revision_id=current["revision_id"],
        manifest_json=manifest_json,
        manifest_sha256=hashlib.sha256(manifest_json.encode()).hexdigest(),
        document_base64=base64.b64encode(document).decode(),
        document_sha256=document_hash,
    )
    response = await client.post("/api/v1/market-data/session-evidence/imports", json=body)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_twentieth_session_completed_between_bid_and_read_never_qualifies_older_bid(loss_database):
    _migrate(loss_database, "head")

    async def exercise():
        engine = engine_for(loss_database)
        try:
            async with _client(loss_database) as (client, database):
                scope = await prepare(client, database)
                close = datetime.now(UTC) - timedelta(seconds=30)
                revision = await install_twentieth_close(client, scope, close)
                older_bid = close - timedelta(seconds=1)
                at, _ = await supply(database, scope, bid_at=older_bid)
                assert older_bid < close < at
                first = await evaluate(engine, scope, at)
                assert first.outcome == "NOT_REACHED"
                assert first.reasons == ("TWENTIETH_SESSION_NOT_COMPLETED_AT_BID",)
                assert first.episode_id is None and not first.alert_created
                before = await _state(engine)
                row = assessment(before, first)
                assert row["result"]["completed_sessions_at_bid"] == 19
                assert row["inputs"]["underlying_sessions"]["calendar"]["revision_id"] == revision
                assert row["inputs"]["source_qualification"]["status"] == "QUALIFIED"
                assert before[EPISODES] == before["alerts"] == before["notifications"] == []

                newer_at, _ = await supply(database, scope)
                second = await evaluate(engine, scope, newer_at)
                assert (
                    second.outcome == "LOSS"
                    and second.alert_created
                    and second.notification_created
                )
                after = await _state(engine)
                assert assessment(after, second)["result"]["completed_sessions_at_bid"] == 20
                assert len(after[ASSESSMENTS]) == 2 and len(after[EPISODES]) == 1
                assert assessment(after, first)["inputs"] == row["inputs"]
                assert_no_target_prerequisites(after)
        finally:
            await engine.dispose()

    asyncio.run(exercise())


def test_existing_background_runner_acquires_and_repeats_without_user_commands(
    loss_database, monkeypatch
):
    _migrate(loss_database, "head")

    async def exercise():
        async with _client(loss_database) as (client, database):
            scope = await prepare(client, database)
            before = await _state(database.engine)
            async with synthetic_source(database, scope) as (at, retained, requests):
                # Only a synthetic clock can coincide with this test supplier's
                # point status. No TTL or open interval is invented, and this
                # fixture makes no assertion about real acquisition latency.
                class SyntheticEvaluationClock(datetime):
                    @classmethod
                    def now(cls, tz=None):
                        return at.astimezone(tz) if tz is not None else at.replace(tzinfo=None)

                with monkeypatch.context() as patch:
                    patch.setattr(loss_commands, "datetime", SyntheticEvaluationClock)
                    products = ProductPositionValuationService(
                        database=database,
                        quote_resolver=MultiSourceWarrantQuoteResolver(
                            (NamedWarrantQuoteSource(PROVIDER.value, retained),)
                        ),
                    )
                    loss = HebeltraderLossRuntime(
                        database,
                        scope="B04_B57_V1",
                        products=products,
                        notifications_enabled=True,
                        sources=synthetic_registry(scope),
                    )
                    runtime = PositionMonitoringRuntimeService(
                        database=database,
                        market_data=None,
                        products=products,
                        delivery_adapter=None,
                        hebeltrader_loss=loss,
                    )
                    completed = []

                    class TwoCycles:
                        async def run(self):
                            result = await runtime.run()
                            completed.append(result)
                            if len(completed) == 2:
                                runner.stop()
                            return result

                    runner = PositionMonitoringRunner(runtime=TwoCycles(), interval_seconds=0.01)
                    await asyncio.wait_for(runner.run_forever(), timeout=30)
                    assert len(completed) == 2
                    first, second = (result.hebeltrader_loss for result in completed)
                    assert first.positions_evaluated == second.positions_evaluated == 1
                    assert first.alerts_created == first.notifications_created == 1
                    assert second.alerts_created == second.notifications_created == 0
                    assert first.position_errors == second.position_errors == 0
                    assert first.data_problems == second.data_problems == 0
                    assert runner.status()["last_error"] is None
                    assert runner.status()["last_result"]["b04_positions_evaluated"] == 1
                    assert all(result.notifications_delivered == 0 for result in completed)
                assert len(requests) == 1  # Shared snapshot/cache; no daily confirmation.

            after = await _state(database.engine)
            assert len(after[EPISODES]) == len(after["alerts"]) == len(after["notifications"]) == 1
            assert len(after[STATUS]) == 1
            assert after["notifications"][0]["status"] == "PENDING"
            assert after["notification_delivery_attempts"] == []
            assert after["execution_records"] == before["execution_records"]
            assert after["positions"] == before["positions"]
            assert after["market_session_evidence"] == before["market_session_evidence"]
            assert after["product_price_scale_evidence"] == before["product_price_scale_evidence"]
            assert_no_target_prerequisites(after)
            await passive_report(client, database.engine, scope)

    asyncio.run(exercise())


def test_parallel_replay_with_one_connection_and_no_pool_overflow(loss_database):
    """The read-only snapshot must not wait for the locked owner's sole connection."""
    _migrate(loss_database, "head")

    async def exercise():
        assert make_url(loss_database).database.startswith("tw_currency_ref_test_")
        engine = create_async_engine(loss_database, pool_size=1, max_overflow=0, pool_timeout=5)
        try:
            async with _client(loss_database) as (client, database):
                scope = await prepare(client, database)
                at, _ = await supply(database, scope)
                results = await asyncio.wait_for(
                    asyncio.gather(*(evaluate(engine, scope, at) for _ in range(3))),
                    timeout=20,
                )
                assert {result.outcome for result in results} == {"LOSS"}
                assert len({result.assessment_id for result in results}) == 1
                assert len({result.episode_id for result in results}) == 1
                assert sum(result.unchanged for result in results) == 2
                assert sum(result.alert_created for result in results) == 1
                assert sum(result.notification_created for result in results) == 1
                state = await _state(engine)
                assert len(state[ASSESSMENTS]) == len(state[EPISODES]) == 1
                assert len(state["alerts"]) == len(state["notifications"]) == 1
                assert state["notifications"][0]["status"] == "PENDING"
                assert state["notification_delivery_attempts"] == []
                assert engine.pool.checkedout() == 0
        finally:
            await engine.dispose()

    asyncio.run(exercise())


def test_loss_history_guards_reject_mutation_unqualified_close_and_destructive_downgrade(
    loss_database,
):
    _migrate(loss_database, "head")

    async def exercise():
        engine = engine_for(loss_database)
        sessions = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)

        async def rejected(statement, parameters, message, expected_state):
            async with sessions() as session:
                with pytest.raises(IntegrityError, match=message):
                    await session.execute(text(statement), parameters)
                await session.rollback()
            assert await _state(engine) == expected_state

        try:
            async with _client(loss_database) as (client, database):
                scope = await prepare(client, database)
                at, _ = await supply(database, scope)
                opening = await evaluate(engine, scope, at)
                assert opening.outcome == "LOSS" and opening.episode_active
                opened = await _state(engine)

                for statement in (
                    "UPDATE hebeltrader_loss_assessments SET outcome='RECOVERED' WHERE id=:id",
                    "DELETE FROM hebeltrader_loss_assessments WHERE id=:id",
                    "TRUNCATE hebeltrader_loss_assessments CASCADE",
                ):
                    await rejected(
                        statement,
                        {"id": opening.assessment_id},
                        "B04 assessments are append-only",
                        opened,
                    )
                for statement in (
                    "UPDATE hebeltrader_loss_episodes SET episode_number=2 WHERE id=:id",
                    "DELETE FROM hebeltrader_loss_episodes WHERE id=:id",
                    "TRUNCATE hebeltrader_loss_episodes",
                ):
                    await rejected(
                        statement,
                        {"id": opening.episode_id},
                        "B04 episode history is immutable",
                        opened,
                    )

                gap_at, _ = await supply(database, scope, bid=None, status="CLOSED")
                gap = await evaluate(engine, scope, gap_at)
                assert gap.outcome == "NOT_ASSESSABLE" and gap.episode_active
                after_gap = await _state(engine)
                await rejected(
                    "UPDATE hebeltrader_loss_episodes "
                    "SET closed_at=:at, closing_assessment_id=:closing, close_reason='DATA_GAP' "
                    "WHERE id=:id",
                    {"at": gap_at, "closing": gap.assessment_id, "id": opening.episode_id},
                    "B04 episode close requires qualified recovery or sale",
                    after_gap,
                )

                # The guard still permits the one owner-commanded, qualified
                # recovery transition, then protects its recorded closure.
                recovery_at, _ = await supply(database, scope, bid="2.00")
                recovered = await evaluate(engine, scope, recovery_at)
                assert recovered.outcome == "RECOVERED" and not recovered.episode_active
                final = await _state(engine)
                assert len(final[ASSESSMENTS]) == 3 and len(final[EPISODES]) == 1
                assert final[EPISODES][0]["closing_assessment_id"] == recovered.assessment_id
                assert final[EPISODES][0]["closed_at"] == recovery_at
                await rejected(
                    "UPDATE hebeltrader_loss_episodes "
                    "SET closed_at=NULL, closing_assessment_id=NULL, close_reason=NULL "
                    "WHERE id=:id",
                    {"id": opening.episode_id},
                    "B04 episode history is immutable",
                    final,
                )
                assert assessment(final, opening)["inputs"] == assessment(opened, opening)["inputs"]
                return final
        finally:
            await engine.dispose()

    preserved = asyncio.run(exercise())
    with pytest.raises(AssertionError, match="B04 history or new alert types exist"):
        _migrate(loss_database, "20261117_0054", action="downgrade")
    assert asyncio.run(read_database_state(loss_database)) == preserved
