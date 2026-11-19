"""Separate review flow on guarded, disposable PostgreSQL with intercepted HTTP.

The synthetic source uses the existing Frankfurt adapter and owner persistence.
Its OPEN point is no real supplier qualification: the production B58 registry
stays empty, and neither these reviews nor their recovery changes strict B04.
"""

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker
from tests.integration.backend.database import test_hebeltrader_loss_postgres as strict
from tests.integration.backend.database.test_product_price_scale_evidence_postgres import (
    engine_for,
)
from tests.integration.backend.test_realized_gross_report_postgres import (
    DECLARATION,
    _client,
    _state,
)
from tests.integration.backend.test_trade_capture_safety import BASE, WORKSPACE
from tests.integration.backend.test_usd_chf_currency_references import _migrate

from app.features.notification.domain.models import DeliveryResult, DeliveryStatus
from app.features.notification.persistence.durable_delivery import (
    SqlAlchemyDurableNotificationDeliveryStore,
)
from app.features.notification.service.creation import AlertNotificationService
from app.features.notification.service.durable_delivery import (
    DurableNotificationDeliveryService,
)
from app.features.position_monitoring.domain.indicative_entry import (
    RULE_SCOPE,
    RULE_VERSION,
)
from app.features.position_monitoring.domain.indicative_policy import V1_POLICY, V2_POLICY
from app.features.position_monitoring.service import indicative_entry as review_commands
from app.features.position_monitoring.service.hebeltrader_b58_sources import (
    QUALIFIED_B58_PATHS,
)
from app.features.position_monitoring.service.indicative_entry import (
    IndicativeEntryService,
)
from app.features.position_monitoring.service.indicative_entry_runtime import (
    IndicativeEntryRuntime,
)
from app.features.position_monitoring.service.product_valuation import (
    ProductPositionValuationService,
)
from app.features.position_monitoring.service.quote_sources import (
    MultiSourceWarrantQuoteResolver,
    NamedWarrantQuoteSource,
)
from app.features.position_monitoring.service.runner import PositionMonitoringRunner
from app.features.position_monitoring.service.runtime import (
    PositionMonitoringRuntimeService,
)
from app.features.trade_position.persistence.models import PositionModel

indicative_database = strict.loss_database
forbid_outbound_http = strict.forbid_outbound_http
ASSESSMENTS = "indicative_entry_assessments"
EPISODES = "indicative_entry_episodes"


async def evaluate(engine, scope, at, *, notifications_enabled=True, policy=V1_POLICY):
    sessions = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with sessions() as session:
        return await IndicativeEntryService(session, policy=policy).evaluate(
            workspace_id=UUID(WORKSPACE),
            trade_id=UUID(scope["capture"]["trade"]["id"]),
            position_id=UUID(scope["capture"]["position"]["id"]),
            notifications_enabled=notifications_enabled,
            now=at,
        )


def assessment(state, result):
    return next(row for row in state[ASSESSMENTS] if row["id"] == result.assessment_id)


def active_episodes(state):
    return {row["kind"]: row for row in state[EPISODES] if row["closed_at"] is None}


def strict_state(state):
    alerts = [row for row in state["alerts"] if row["alert_type"] == "HEBELTRADER_B04_LOSS"]
    alert_ids = {row["id"] for row in alerts}
    notifications = [row for row in state["notifications"] if row["alert_id"] in alert_ids]
    notification_ids = {row["id"] for row in notifications}
    return {
        strict.ASSESSMENTS: state[strict.ASSESSMENTS],
        strict.EPISODES: state[strict.EPISODES],
        "alerts": alerts,
        "notifications": notifications,
        "attempts": [
            row
            for row in state["notification_delivery_attempts"]
            if row["notification_id"] in notification_ids
        ],
    }


def test_v2_transition_preserves_v1_episode_and_outbox_under_parallel_restart_and_sale(
    indicative_database,
):
    _migrate(indicative_database, "head")

    async def exercise():
        engine = engine_for(indicative_database)
        try:
            async with _client(indicative_database) as (client, database):
                scope = await strict.prepare(client, database)
                at, _ = await strict.supply(database, scope)
                first = await evaluate(engine, scope, at)
                before = await _state(engine)
                legacy_episodes = active_episodes(before)
                results = await asyncio.wait_for(
                    asyncio.gather(
                        *(evaluate(engine, scope, at, policy=V2_POLICY) for _ in range(3))
                    ),
                    timeout=30,
                )
                assert {item.outcome for item in results} == {"BELOW_ENTRY"}
                assert len({item.assessment_id for item in results}) == 1
                assert sum(item.alerts_created for item in results) == 0
                assert sum(item.notifications_created for item in results) == 0
                assert sum(item.unchanged for item in results) == 2
                upgraded = await _state(engine)
                assert active_episodes(upgraded) == legacy_episodes
                assert upgraded["alerts"] == before["alerts"]
                assert upgraded["notifications"] == before["notifications"]
                row = assessment(upgraded, results[0])
                assert row["rule_version"] == V2_POLICY.version
                assert row["previous_assessment_id"] == first.assessment_id
                assert row["result"]["loss_evidence_floor"]["price_rank"] == 3
                assert row["result"]["loss_evidence_floor"]["scale_rank"] == 2
                assert assessment(upgraded, first) == assessment(before, first)
                report = await passive_report(client, engine, scope)
                assert report["latest_assessment"]["rule_version"] == V2_POLICY.version
                assert {item["rule_version"] for item in report["active_episodes"]} == {
                    V1_POLICY.version
                }

            async with _client(indicative_database) as (client, database):
                restarted = await evaluate(engine, scope, at, policy=V2_POLICY)
                assert restarted.unchanged and restarted.assessment_id == results[0].assessment_id
                assert await _state(engine) == upgraded
                recovered_at, _ = await strict.supply(database, scope, bid="2.00")
                recovered = await evaluate(engine, scope, recovered_at, policy=V2_POLICY)
                assert (
                    recovered.outcome == "AT_OR_ABOVE_ENTRY" and not recovered.loss_episode_active
                )
                recovered_state = await _state(engine)
                loss = next(row for row in recovered_state[EPISODES] if row["kind"] == "ENTRY_LOSS")
                assert loss["rule_version"] == V1_POLICY.version
                assert loss["closing_assessment_id"] == recovered.assessment_id
                assert set(active_episodes(recovered_state)) == {"REVIEW_DUE"}
                loss_at, _ = await strict.supply(database, scope)
                await evaluate(engine, scope, loss_at, policy=V2_POLICY)
                response = await client.post(
                    f"{BASE}/trades/{scope['capture']['trade']['id']}/sales",
                    json={
                        "quantity": 100,
                        "price_per_unit": "2.00",
                        "executed_on": (scope["anchor"] + timedelta(days=15)).isoformat(),
                        "execution_timezone": "Europe/Berlin",
                        "request_id": str(uuid4()),
                        "currency_confirmation": DECLARATION,
                    },
                )
                assert response.status_code == 201, response.text
                closed = await IndicativeEntryRuntime(database, scope=V2_POLICY.scope).run()
                assert closed.positions_evaluated == 1 and closed.position_errors == 0
                final = await _state(engine)
                assert not active_episodes(final)
                assert not [row for row in final["notifications"] if row["status"] == "PENDING"]
                assert strict_state(final) == strict_state(before)
        finally:
            await engine.dispose()

    asyncio.run(exercise())


async def passive_report(client, engine, scope):
    before = await _state(engine)
    trade = scope["capture"]["trade"]["id"]
    response = await client.get(
        f"/api/v1/position-monitoring/trades/{trade}/indicative-entry",
        params={"position_id": scope["capture"]["position"]["id"]},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["scope"] == RULE_SCOPE
    assert body["definition_version"] == RULE_VERSION
    assert body["activation_status"] == "NOT_ACTIVATED"
    assert body["runner_enabled"] is False
    assert body["notifications_enabled"] is False
    assert body["qualified_b04"] is False
    assert body["full_baseline_activated"] is False
    assert body["read_status"] == "READ_ONLY"
    assert await _state(engine) == before
    return body


def test_adapter_review_gap_recovery_parallel_replay_and_restart(indicative_database, monkeypatch):
    _migrate(indicative_database, "head")

    async def exercise():
        engine = engine_for(indicative_database)
        try:
            async with _client(indicative_database) as (client, database):
                scope = await strict.prepare(client, database)
                at, delivered = await strict.supply(database, scope)
                assert delivered.data.bid == Decimal("1.50")
                assert QUALIFIED_B58_PATHS == ()
                acquired = await _state(engine)
                assert acquired[ASSESSMENTS] == acquired[EPISODES] == []
                strict.assert_no_target_prerequisites(acquired)

                with monkeypatch.context() as patch:
                    patch.setattr(
                        AlertNotificationService,
                        "create_telegram",
                        AsyncMock(side_effect=RuntimeError("Synthetic review outbox failure")),
                    )
                    with pytest.raises(RuntimeError, match="Synthetic review outbox failure"):
                        await evaluate(engine, scope, at)
                assert await _state(engine) == acquired

                results = await asyncio.wait_for(
                    asyncio.gather(*(evaluate(engine, scope, at) for _ in range(3))),
                    timeout=30,
                )
                assert {item.outcome for item in results} == {"BELOW_ENTRY"}
                assert len({item.assessment_id for item in results}) == 1
                assert sum(item.alerts_created for item in results) == 2
                assert sum(item.notifications_created for item in results) == 2
                assert sum(item.unchanged for item in results) == 2
                assert all(item.loss_episode_active and item.review_due for item in results)
                opened = await _state(engine)
                episodes = active_episodes(opened)
                assert set(episodes) == {"ENTRY_LOSS", "REVIEW_DUE"}
                first_loss = episodes["ENTRY_LOSS"]["id"]
                reminder = episodes["REVIEW_DUE"]["id"]
                row = assessment(opened, results[0])
                assert row["result"]["evaluation_mode"] == "SOURCE_BID"
                assert row["result"]["completed_sessions"] == 20
                assert Decimal(row["result"]["gross_entry"]) == Decimal("2.00")
                assert row["result"]["remaining_quantity"] == 100
                assert {item["status"] for item in opened["notifications"]} == {"PENDING"}
                assert opened["notification_delivery_attempts"] == []
                for alert in opened["alerts"]:
                    assert alert["price_context"]["qualified_b04"] == "false"
                    assert alert["price_context"]["scope"] == RULE_SCOPE
                    if alert["alert_type"] == "POSITION_REVIEW_DUE":
                        assert alert["observed_value"] is alert["threshold_value"] is None

                closed_at, retained = await strict.supply(
                    database, scope, bid=None, status="CLOSED"
                )
                assert retained.data.retained is True
                negative = await evaluate(engine, scope, closed_at)
                assert negative.outcome == "UNAVAILABLE"
                assert "REVIEW_LATER_NEGATIVE_STATUS_OBSERVED" in negative.reasons
                assert negative.loss_episode_active and negative.data_problem_active
                after_negative = await _state(engine)
                assert active_episodes(after_negative)["ENTRY_LOSS"]["id"] == first_loss
                assert active_episodes(after_negative)["REVIEW_DUE"]["id"] == reminder
                assert (
                    after_negative["warrant_quote_observations"]
                    == opened["warrant_quote_observations"]
                )
                assert len(after_negative["alerts"]) == len(after_negative["notifications"]) == 3
                data_episode = active_episodes(after_negative)["DATA_UNAVAILABLE"]["id"]

                gap_at, _ = await strict.supply(database, scope, http_error=True)
                gap = await evaluate(engine, scope, gap_at)
                assert gap.outcome == "UNAVAILABLE" and gap.loss_episode_active
                assert "REVIEW_PRICE_SUPPLY_INTERRUPTED" in gap.reasons
                assert gap.alerts_created == gap.notifications_created == 0
                after_gap = await _state(engine)
                assert active_episodes(after_gap)["DATA_UNAVAILABLE"]["id"] == data_episode
                report = await passive_report(client, engine, scope)
                assert report["latest_assessment"]["outcome"] == "UNAVAILABLE"
                assert {item["kind"] for item in report["active_episodes"]} == {
                    "ENTRY_LOSS",
                    "REVIEW_DUE",
                    "DATA_UNAVAILABLE",
                }

                recovered_at, _ = await strict.supply(database, scope, bid="2.00")
                recovered = await evaluate(engine, scope, recovered_at)
                assert recovered.outcome == "AT_OR_ABOVE_ENTRY"
                assert not recovered.loss_episode_active and not recovered.data_problem_active
                recovered_state = await _state(engine)
                assert set(active_episodes(recovered_state)) == {"REVIEW_DUE"}
                assert active_episodes(recovered_state)["REVIEW_DUE"]["id"] == reminder
                assert len(recovered_state["notification_delivery_attempts"]) == 2
                assert {
                    row["error_code"] for row in recovered_state["notification_delivery_attempts"]
                } == {"REVIEW_ALERT_RESOLVED"}

                final_at, _ = await strict.supply(database, scope, bid="1.25")
                reopened = await evaluate(engine, scope, final_at)
                assert reopened.outcome == "BELOW_ENTRY" and reopened.loss_episode_active
                assert reopened.alerts_created == reopened.notifications_created == 1
                final = await _state(engine)
                assert active_episodes(final)["ENTRY_LOSS"]["id"] != first_loss
                assert active_episodes(final)["ENTRY_LOSS"]["episode_number"] == 2
                assert active_episodes(final)["REVIEW_DUE"]["id"] == reminder
                assert len(final[ASSESSMENTS]) == 5
                assert (
                    len(final[EPISODES]) == len(final["alerts"]) == len(final["notifications"]) == 4
                )
                assert strict_state(final) == strict_state(acquired)
                assert final["execution_records"] == acquired["execution_records"]
                assert final["positions"] == acquired["positions"]
                strict.assert_no_target_prerequisites(final)

            async with _client(indicative_database) as (client, _database):
                restarted = await evaluate(engine, scope, final_at)
                assert restarted.unchanged and restarted.assessment_id == reopened.assessment_id
                assert restarted.alerts_created == restarted.notifications_created == 0
                assert await _state(engine) == final
                await passive_report(client, engine, scope)
        finally:
            await engine.dispose()

    asyncio.run(exercise())


def test_changed_priceless_status_updates_assessment_without_duplicate_notice(
    indicative_database,
):
    _migrate(indicative_database, "head")

    async def exercise():
        engine = engine_for(indicative_database)
        try:
            async with _client(indicative_database) as (client, database):
                scope = await strict.prepare(client, database)
                at, _ = await strict.supply(database, scope)
                await evaluate(engine, scope, at)
                closed_at, _ = await strict.supply(database, scope, bid=None, status="CLOSED")
                closed = await evaluate(engine, scope, closed_at)
                baseline = await _state(engine)
                episodes = active_episodes(baseline)
                assert set(episodes) == {"ENTRY_LOSS", "REVIEW_DUE", "DATA_UNAVAILABLE"}

                async with strict.synthetic_source(
                    database, scope, bid=None, status="SUSPENDED"
                ) as (suspended_at, retained, _requests):
                    for repeat in (False, True):
                        # Same original payload, a separate delivery request. The
                        # actual status owner deduplicates the repeated fact.
                        await retained.get_warrant_listing_quote(
                            strict.WarrantQuoteRequest(
                                workspace_id=UUID(WORKSPACE),
                                warrant_listing_id=UUID(scope["listing"]["id"]),
                                correlation_id=uuid4(),
                                as_of=suspended_at,
                                expected_currency="EUR",
                            )
                        )
                        result = await evaluate(engine, scope, suspended_at)
                        assert result.reasons == closed.reasons
                        assert result.unchanged is repeat
                        assert result.alerts_created == result.notifications_created == 0
                        assert result.loss_episode_active and result.data_problem_active
                        assert result.assessment_id != closed.assessment_id
                        current = await _state(engine)
                        assert len(current[ASSESSMENTS]) == 3
                        assert active_episodes(current) == episodes
                        assert current["alerts"] == baseline["alerts"]
                        assert current["notifications"] == baseline["notifications"]
                        assert (
                            current["warrant_quote_observations"]
                            == baseline["warrant_quote_observations"]
                        )
                        report = await passive_report(client, engine, scope)
                        source = report["latest_assessment"]["source"]
                        assert source["source_status_point"] == "SUSPENDED"
                        assert datetime.fromisoformat(source["source_status_observed_at"]) == (
                            suspended_at
                        )
                        assert source["status_validity"] == "NOT_ESTABLISHED"

                # A changed original clock also becomes its own assessment,
                # although the price, status label and problem reason persist.
                revised_at, _ = await strict.supply(database, scope, bid=None, status="SUSPENDED")
                revised = await evaluate(engine, scope, revised_at)
                assert revised.assessment_id != result.assessment_id
                assert revised.reasons == result.reasons and not revised.unchanged
                assert revised.alerts_created == revised.notifications_created == 0
                final = await _state(engine)
                assert len(final[ASSESSMENTS]) == 4
                assert active_episodes(final) == episodes
                assert final["alerts"] == baseline["alerts"]
                assert final["notifications"] == baseline["notifications"]
                report = await passive_report(client, engine, scope)
                assert (
                    datetime.fromisoformat(
                        report["latest_assessment"]["source"]["source_status_observed_at"]
                    )
                    == revised_at
                )
        finally:
            await engine.dispose()

    asyncio.run(exercise())


def test_reminder_uses_current_sessions_but_older_bid_keeps_nineteen(
    indicative_database,
):
    _migrate(indicative_database, "head")

    async def exercise():
        engine = engine_for(indicative_database)
        try:
            async with _client(indicative_database) as (client, database):
                scope = await strict.prepare(client, database)
                close = datetime.now(UTC) - timedelta(seconds=30)
                revision = await strict.install_twentieth_close(client, scope, close)
                older_bid = close - timedelta(seconds=1)
                at, _ = await strict.supply(database, scope, bid_at=older_bid)
                first = await evaluate(engine, scope, at)
                assert first.outcome == "NOT_REACHED"
                assert first.review_due and not first.loss_episode_active
                assert first.alerts_created == first.notifications_created == 1
                before = await _state(engine)
                row = assessment(before, first)
                assert row["result"]["completed_sessions"] == 19
                assert row["result"]["review_completed_sessions"] == 20
                assert datetime.fromisoformat(row["result"]["session_count_at"]) == older_bid
                assert row["inputs"]["comparison_sessions"]["calendar"]["revision_id"] == revision
                assert set(active_episodes(before)) == {"REVIEW_DUE"}
                reminder = active_episodes(before)["REVIEW_DUE"]["id"]
                alert = before["alerts"][0]
                assert alert["alert_type"] == "POSITION_REVIEW_DUE"
                assert alert["observed_value"] is alert["threshold_value"] is None
                assert alert["price_context"]["review_completed_sessions"] == "20"
                assert alert["price_context"]["completed_sessions"] == "19"

                newer_at, _ = await strict.supply(database, scope)
                newer = await evaluate(engine, scope, newer_at)
                assert newer.outcome == "BELOW_ENTRY" and newer.loss_episode_active
                assert newer.alerts_created == newer.notifications_created == 1
                after = await _state(engine)
                assert active_episodes(after)["REVIEW_DUE"]["id"] == reminder
                assert assessment(after, newer)["result"]["completed_sessions"] == 20
                assert assessment(after, first)["inputs"] == row["inputs"]
                assert len(after[ASSESSMENTS]) == len(after[EPISODES]) == 2
                report = await passive_report(client, engine, scope)
                assert report["latest_assessment"]["currency"] == "EUR"
                assert after[strict.ASSESSMENTS] == after[strict.EPISODES] == []
        finally:
            await engine.dispose()

    asyncio.run(exercise())


def test_execution_correction_full_sale_and_late_retry_leave_strict_b04_untouched(
    indicative_database,
):
    _migrate(indicative_database, "head")

    async def exercise():
        engine = engine_for(indicative_database)
        try:
            async with _client(indicative_database) as (client, database):
                scope = await strict.prepare(client, database)
                trade = scope["capture"]["trade"]["id"]
                initial_buy = scope["capture"]["execution"]["id"]
                at, _ = await strict.supply(database, scope)
                # Explicit, invented test dependency seeds an existing B04 loss;
                # the real registry remains empty and the review never invokes it.
                strict_loss = await strict.evaluate(engine, scope, at)
                assert strict_loss.episode_active
                preserved_strict = strict_state(await _state(engine))
                first = await evaluate(engine, scope, at)
                initial = assessment(await _state(engine), first)
                first_loss = active_episodes(await _state(engine))["ENTRY_LOSS"]["id"]
                basis_ids = {initial["owner_basis_id"]}
                executions = [initial_buy]

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
                    executions.append(response.json()["execution"]["id"])
                    at, _ = await strict.supply(database, scope)
                    reviewed = await evaluate(engine, scope, at)
                    state = await _state(engine)
                    row = assessment(state, reviewed)
                    basis_ids.add(row["owner_basis_id"])
                    assert reviewed.outcome == "BELOW_ENTRY"
                    assert active_episodes(state)["ENTRY_LOSS"]["id"] == first_loss
                    assert row["result"]["remaining_quantity"] == remaining
                    assert Decimal(row["result"]["gross_entry"]) == Decimal(entry)
                    assert row["inputs"]["effective_execution_ids"] == executions
                    assert strict_state(state) == preserved_strict

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
                at, _ = await strict.supply(database, scope)
                corrected = await evaluate(engine, scope, at)
                corrected_state = await _state(engine)
                row = assessment(corrected_state, corrected)
                basis_ids.add(row["owner_basis_id"])
                assert len(basis_ids) == 4
                assert Decimal(row["result"]["gross_entry"]) == Decimal("3.40")
                assert row["result"]["remaining_quantity"] == 100
                assert row["inputs"]["effective_execution_ids"] == [
                    replacement,
                    *executions[1:],
                ]
                assert active_episodes(corrected_state)["ENTRY_LOSS"]["id"] == first_loss
                assert assessment(corrected_state, first)["inputs"] == initial["inputs"]
                assert len(corrected_state["product_price_scale_evidence"]) == 1

                # Indicative recovery must not resolve the pre-existing strict loss.
                at, _ = await strict.supply(database, scope, bid="3.40")
                recovered = await evaluate(engine, scope, at)
                assert (
                    recovered.outcome == "AT_OR_ABOVE_ENTRY" and not recovered.loss_episode_active
                )
                assert strict_state(await _state(engine)) == preserved_strict
                at, _ = await strict.supply(database, scope)
                await evaluate(engine, scope, at)
                at, _ = await strict.supply(database, scope, http_error=True)
                gap = await evaluate(engine, scope, at)
                assert gap.data_problem_active and gap.loss_episode_active
                before_sale = await _state(engine)
                active_alert_ids = {
                    row["alert_id"] for row in active_episodes(before_sale).values()
                }
                active_pending = [
                    row
                    for row in before_sale["notifications"]
                    if row["alert_id"] in active_alert_ids and row["status"] == "PENDING"
                ]
                assert len(active_pending) == 3
                store = SqlAlchemyDurableNotificationDeliveryStore(database)
                prepared = await store.prepare(
                    notification_id=active_pending[0]["id"],
                    attempt_id=uuid4(),
                    now=datetime.now(UTC),
                    max_attempts=3,
                    stale_before=datetime.now(UTC) - timedelta(minutes=5),
                )
                assert prepared.attempt is not None

                response = await client.post(
                    f"{BASE}/trades/{trade}/sales",
                    json={
                        "quantity": 100,
                        "price_per_unit": "3.50",
                        "executed_on": (scope["anchor"] + timedelta(days=15)).isoformat(),
                        "execution_timezone": "Europe/Berlin",
                        "request_id": str(uuid4()),
                        "currency_confirmation": DECLARATION,
                    },
                )
                assert response.status_code == 201, response.text
                closed = await IndicativeEntryRuntime(database, scope=RULE_SCOPE).run()
                assert closed.positions_evaluated == 1 and closed.position_errors == 0
                assert closed.alerts_created == closed.notifications_created == 0
                after_sale = await _state(engine)
                assert active_episodes(after_sale) == {}
                assert strict_state(after_sale) == preserved_strict
                for notification in after_sale["notifications"]:
                    if notification["alert_id"] in active_alert_ids:
                        assert notification["status"] == "FAILED"
                terminal = [
                    row
                    for row in after_sale["notification_delivery_attempts"]
                    if row["notification_id"] in {item["id"] for item in active_pending}
                    and row["error_code"] == "REVIEW_POSITION_CLOSED"
                ]
                assert len(terminal) == 3
                await store.complete(
                    notification_id=prepared.notification.id,
                    attempt_id=prepared.attempt.id,
                    result=DeliveryResult(
                        status=DeliveryStatus.FAILED,
                        retryable=True,
                        error_code="SYNTHETIC_LATE_TIMEOUT",
                    ),
                    completed_at=datetime.now(UTC),
                    max_attempts=3,
                )
                adapter = SimpleNamespace(deliver=AsyncMock())
                delivery = DurableNotificationDeliveryService(
                    store=store,
                    adapter=adapter,
                    new_id=uuid4,
                    now=lambda: datetime.now(UTC),
                )
                for item in active_pending:
                    result = await delivery.deliver(item["id"])
                    assert result.status is DeliveryStatus.FAILED
                    assert result.error_code == "REVIEW_POSITION_CLOSED"
                adapter.deliver.assert_not_awaited()
                final = await _state(engine)
                assert strict_state(final) == preserved_strict
                assert all(
                    item["status"] == "FAILED"
                    for item in final["notifications"]
                    if item["alert_id"] in active_alert_ids
                )
                report = await passive_report(client, engine, scope)
                assert report["latest_assessment"]["outcome"] == "CLOSED"
                assert report["active_episodes"] == []
        finally:
            await engine.dispose()

    asyncio.run(exercise())


def test_general_runner_cleans_full_sale_with_review_paused_and_without_adapter(
    indicative_database,
):
    _migrate(indicative_database, "head")

    async def exercise():
        async with _client(indicative_database) as (client, database):
            scope = await strict.prepare(client, database)
            trade = scope["capture"]["trade"]["id"]
            position_id = UUID(scope["capture"]["position"]["id"])
            at, _ = await strict.supply(database, scope)
            assert (await strict.evaluate(database.engine, scope, at)).episode_active
            await evaluate(database.engine, scope, at)
            gap_at, _ = await strict.supply(database, scope, http_error=True)
            assert (await evaluate(database.engine, scope, gap_at)).data_problem_active
            before_sale = await _state(database.engine)
            strict_before = strict_state(before_sale)
            review_alerts = {row["alert_id"] for row in before_sale[EPISODES]}
            pending = {
                row["id"]
                for row in before_sale["notifications"]
                if row["alert_id"] in review_alerts and row["status"] == "PENDING"
            }
            assert len(pending) == 3
            async with database.session_context() as session:
                position = await session.get(PositionModel, position_id)
                earlier_projection = {
                    column.name: getattr(position, column.name)
                    for column in PositionModel.__table__.columns
                    if column.name not in {"id", "trade_id", "product_id"}
                }
            response = await client.post(
                f"{BASE}/trades/{trade}/sales",
                json={
                    "quantity": 100,
                    "price_per_unit": "2.00",
                    "executed_on": (scope["anchor"] + timedelta(days=15)).isoformat(),
                    "execution_timezone": "Europe/Berlin",
                    "request_id": str(uuid4()),
                    "currency_confirmation": DECLARATION,
                },
            )
            assert response.status_code == 201, response.text
            assert response.json()["position"]["open_quantity"] == 0
            # Deliberately restore an internally consistent earlier projection
            # only in this guarded synthetic DB. Effective executions still
            # prove full sale and must control terminal notification handling.
            async with database.session_context() as session:
                await session.execute(
                    update(PositionModel)
                    .where(PositionModel.id == position_id)
                    .values(**earlier_projection)
                )
                await session.commit()
            runtime = PositionMonitoringRuntimeService(
                database=database,
                market_data=None,
                delivery_adapter=None,
                indicative_entry=IndicativeEntryRuntime(database, scope="DISABLED"),
                review_notifications_enabled=False,
            )
            result = await runtime.run()
            assert result.indicative_entry.positions_evaluated == 0
            assert result.notifications_created == result.notifications_delivered == 0
            assert result.notification_failures == 0
            after = await _state(database.engine)
            assert strict_state(after) == strict_before
            assert after[ASSESSMENTS] == before_sale[ASSESSMENTS]
            assert after[EPISODES] == before_sale[EPISODES]
            assert {row["status"] for row in after["notifications"] if row["id"] in pending} == {
                "FAILED"
            }
            terminal = [
                row
                for row in after["notification_delivery_attempts"]
                if row["notification_id"] in pending
            ]
            assert len(terminal) == 3
            assert {row["error_code"] for row in terminal} == {"REVIEW_POSITION_CLOSED"}
            assert all(
                row["provider_message_id"] is None and not row["retryable"] for row in terminal
            )
            repeated = await runtime.run()
            assert repeated.notification_failures == repeated.notifications_delivered == 0
            assert await _state(database.engine) == after

    asyncio.run(exercise())


def test_existing_background_runner_repeats_and_mock_dispatches_without_user_commands(
    indicative_database, monkeypatch
):
    _migrate(indicative_database, "head")

    async def exercise():
        async with _client(indicative_database) as (client, database):
            scope = await strict.prepare(client, database)
            before = await _state(database.engine)
            inactive = await IndicativeEntryRuntime(database).run()
            assert inactive.positions_evaluated == 0
            assert await _state(database.engine) == before
            async with strict.synthetic_source(database, scope) as (
                at,
                retained,
                requests,
            ):

                class SyntheticEvaluationClock(datetime):
                    @classmethod
                    def now(cls, tz=None):
                        return at.astimezone(tz) if tz is not None else at.replace(tzinfo=None)

                with monkeypatch.context() as patch:
                    patch.setattr(review_commands, "datetime", SyntheticEvaluationClock)
                    products = ProductPositionValuationService(
                        database=database,
                        quote_resolver=MultiSourceWarrantQuoteResolver(
                            (NamedWarrantQuoteSource(strict.PROVIDER.value, retained),)
                        ),
                    )
                    adapter = SimpleNamespace(
                        deliver=AsyncMock(
                            return_value=DeliveryResult(
                                status=DeliveryStatus.DELIVERED,
                                retryable=False,
                                provider_message_id="synthetic-no-external-dispatch",
                            )
                        )
                    )
                    review = IndicativeEntryRuntime(
                        database,
                        scope=RULE_SCOPE,
                        products=products,
                        notifications_enabled=True,
                    )
                    runtime = PositionMonitoringRuntimeService(
                        database=database,
                        market_data=None,
                        products=products,
                        delivery_adapter=adapter,
                        indicative_entry=review,
                        review_notifications_enabled=True,
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
                    first, second = (result.indicative_entry for result in completed)
                    assert first.positions_evaluated == second.positions_evaluated == 1
                    assert first.alerts_created == first.notifications_created == 2
                    assert second.alerts_created == second.notifications_created == 0
                    assert first.position_errors == second.position_errors == 0
                    assert [result.notifications_delivered for result in completed] == [
                        2,
                        0,
                    ]
                    assert all(result.notification_failures == 0 for result in completed)
                    assert adapter.deliver.await_count == 2
                    assert runner.status()["last_error"] is None
                    assert runner.status()["last_result"]["review_positions_evaluated"] == 1
                assert len(requests) == 1
            after = await _state(database.engine)
            assert len(after[ASSESSMENTS]) == 1
            assert len(after[EPISODES]) == len(after["notifications"]) == 2
            assert {row["status"] for row in after["notifications"]} == {"DELIVERED"}
            assert len(after["notification_delivery_attempts"]) == 2
            for table in (
                "execution_records",
                "execution_currency_confirmations",
                "positions",
                "market_session_evidence",
                "product_price_scale_evidence",
            ):
                assert after[table] == before[table]
            assert strict_state(after) == strict_state(before)
            assert QUALIFIED_B58_PATHS == ()
            strict.assert_no_target_prerequisites(after)
            await passive_report(client, database.engine, scope)

    asyncio.run(exercise())


def test_review_history_guards_reject_mutation_and_gap_closure(indicative_database):
    _migrate(indicative_database, "head")

    async def exercise():
        engine = engine_for(indicative_database)
        sessions = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
        try:
            async with _client(indicative_database) as (client, database):
                scope = await strict.prepare(client, database)
                at, _ = await strict.supply(database, scope)
                first = await evaluate(engine, scope, at)
                at, _ = await strict.supply(database, scope, http_error=True)
                gap = await evaluate(engine, scope, at)
                preserved = await _state(engine)
                loss = active_episodes(preserved)["ENTRY_LOSS"]
                for statement, parameters, message in (
                    (
                        "UPDATE indicative_entry_assessments SET outcome='CLOSED' WHERE id=:id",
                        {"id": first.assessment_id},
                        "Review assessments are append-only",
                    ),
                    (
                        "DELETE FROM indicative_entry_episodes WHERE id=:id",
                        {"id": loss["id"]},
                        "Review episode history is immutable",
                    ),
                    (
                        "UPDATE indicative_entry_episodes SET closed_at=:at, "
                        "closing_assessment_id=:closing, close_reason='DATA_GAP' WHERE id=:id",
                        {"at": at, "closing": gap.assessment_id, "id": loss["id"]},
                        "Review episode close requires recorded resolution",
                    ),
                ):
                    async with sessions() as session:
                        with pytest.raises(IntegrityError, match=message):
                            await session.execute(text(statement), parameters)
                        await session.rollback()
                    assert await _state(engine) == preserved
        finally:
            await engine.dispose()

    asyncio.run(exercise())
    with pytest.raises(AssertionError, match="Immutable indicative review history exists"):
        _migrate(indicative_database, "20261117_0056", action="downgrade")
