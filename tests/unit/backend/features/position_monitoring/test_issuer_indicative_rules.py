import importlib
from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text

from app.features.alert.api.dtos import AlertResponse
from app.features.market_data.domain.enums import MarketDataProvider
from app.features.market_data.service.types import WarrantQuoteRequest
from app.features.notification.service.formatter import format_position_alert
from app.features.position_monitoring.domain.models import (
    MonitoringRule,
    MonitoringRuleType,
)
from app.features.position_monitoring.domain.transitions import TriggerTransition
from app.features.position_monitoring.service.application import (
    PositionMonitoringService,
)
from app.features.position_monitoring.service.cycle import (
    PositionMonitoringCycleService,
)
from app.features.position_monitoring.service.product_valuation import (
    ProductPositionValuation,
    ProductValuationStatus,
)
from app.features.position_monitoring.service.rule_prices import rule_price
from app.features.position_monitoring.service.subjects import (
    MonitoringSubject,
    MonitoringSubjectResolution,
)
from app.features.trade_position.domain.price_binding import PriceBasis, PriceBinding

NOW = datetime(2026, 9, 22, 18, 20, 8, tzinfo=UTC)
BINDING = PriceBinding(PriceBasis.WARRANT, uuid4(), "EUR")
RULE = MonitoringRule("CURRENT_STOP", MonitoringRuleType.STOP_REACHED, Decimal(1), BINDING)
SUBJECT = MonitoringSubject(
    uuid4(),
    uuid4(),
    uuid4(),
    None,
    None,
    "TEST",
    (RULE,),
    warrant_id=BINDING.instrument_id,
    warrant_isin="DE000JE7KTY8",
)


def valuation(provider="JPMORGAN", **changes):
    # Start with each real adapter: venue_mic is absent; ISSUER is the provider code.
    module = "jpmorgan" if provider == "JPMORGAN" else "morganstanley"
    adapter = importlib.import_module(f"app.providers.{module}.adapter")
    stream = importlib.import_module(f"app.providers.{module}.stream")
    fields = {"bid": "0.9400", "ask": "0.0000", "bidsize": "125000", "asksize": "0"}
    fields["quotetime" if module == "jpmorgan" else "lastquotetimestamp"] = (
        "20:18:16" if module == "jpmorgan" else "22/09/2026 20:18:16.99"
    )
    request = WarrantQuoteRequest(SUBJECT.workspace_id, uuid4(), uuid4(), NOW)
    quote = adapter.parse_item(
        stream.StreamItem(fields, NOW),
        request,
        SimpleNamespace(isin=SUBJECT.warrant_isin, currency="EUR", wkn=None),
    )
    value = ProductPositionValuation(
        SUBJECT.trade_id,
        SUBJECT.position_id,
        ProductValuationStatus.INDICATIVE,
        "INDICATIVE",
        quote_listing_id=quote.warrant_listing_id,
        isin=quote.isin,
        currency=quote.currency,
        monitoring_usable=True,
        bid=quote.bid,
        ask=quote.ask,
        reference_price=quote.bid,
        reference_price_type="BID",
        quote_observed_at=quote.observed_at,
        quote_retrieved_at=NOW,
        quote_time_text=quote.quote_time_text,
        quote_time_basis=quote.quote_time_basis,
        selected_source=provider,
        quote_provider=MarketDataProvider(provider),
        provider_identity=quote.provider_symbol,
        provider_exchange_code=quote.provider_exchange_code,
        quote_venue_mic=quote.venue_mic,
        source_mode=quote.source_mode,
        source_selection_status="SELECTED",
        source_selection_policy_version=provider + "_ISSUER_INDICATION_V1",
    )
    return replace(value, **changes)


async def check(value=None, rule=RULE, **kwargs):
    return await rule_price(
        subject=SUBJECT,
        rule=rule,
        market_data=None,
        products=SimpleNamespace(for_trade=AsyncMock(return_value=value or valuation())),
        now=NOW,
        max_age_days=4,
        **kwargs,
    )


class States:
    value = None

    async def get(self, **kwargs):
        return self.value

    async def put(self, value):
        self.value = value


class Alerts:
    def __init__(self):
        self.items = []
        self.resolved = []

    async def add(self, value):
        self.items.append(value)

    async def resolve(self, alert_id, **kwargs):
        self.resolved.append(alert_id)


@pytest.mark.parametrize("provider", ["JPMORGAN", "MORGAN_STANLEY"])
@pytest.mark.asyncio
async def test_real_adapter_indication_reaches_alert_dedup_resolution_and_api(provider):
    value = valuation(provider)
    result = await check(value)
    assert result.status == "INDICATIVE"
    observation = result.observation
    assert observation.observed_at is None
    assert observation.ordering_at == NOW
    assert observation.context["source_freshness"] == "UNKNOWN"
    assert observation.context["quote_time_text"] == value.quote_time_text
    states, alerts = States(), Alerts()
    app = PositionMonitoringService(states=states, alerts=alerts, new_id=uuid4, now=lambda: NOW)

    async def evaluate(obs):
        return await app.evaluate(
            position_id=SUBJECT.position_id,
            trade_id=SUBJECT.trade_id,
            rule=RULE,
            observation=obs,
        )

    first = await evaluate(observation)
    repeat = await evaluate(observation)
    assert first.alert.market_data_observed_at is None
    assert repeat.transition is TriggerTransition.STAYED_TRIGGERED
    assert len(alerts.items) == 1
    assert states.value.time_basis == "RECEIPT_TIMESTAMP"
    assert states.value.last_seen_at == NOW
    payload = AlertResponse.model_validate(asdict(first.alert) | {"notifications": []})
    assert payload.model_dump(mode="json")["market_data_observed_at"] is None
    formatted = format_position_alert(first.alert, symbol=SUBJECT.warrant_isin)
    assert "indikative Prüfung" in formatted and value.quote_time_text in formatted
    assert "Kurszeitpunkt: —" in formatted and "Keine Orderfreigabe" in formatted
    with pytest.raises(ValueError, match="OUT_OF_ORDER"):
        await evaluate(replace(observation, received_at=NOW - timedelta(seconds=1)))
    reset = await evaluate(
        replace(observation, value=Decimal("1.2"), received_at=NOW + timedelta(seconds=1))
    )
    assert reset.transition is TriggerTransition.EXITED
    assert alerts.resolved == [first.alert.id]
    retrigger = await evaluate(replace(observation, received_at=NOW + timedelta(seconds=2)))
    assert retrigger.alert is not None and len(alerts.items) == 2


@pytest.mark.parametrize(
    "change",
    [
        {"source_selection_status": None},
        {"source_selection_policy_version": "unverified"},
        {"quote_provider": MarketDataProvider.FRANKFURT_QUOTES},
        {"source_mode": "public_website"},
        {"provider_exchange_code": "XETR"},
        {"provider_identity": "WRONG"},
        {"quote_time_basis": "UNKNOWN"},
        {"quote_time_text": None},
        {"quote_retrieved_at": None},
        {"quote_retrieved_at": NOW.replace(tzinfo=None)},
        {"quote_retrieved_at": NOW + timedelta(seconds=1)},
        {"quote_retrieved_at": NOW - timedelta(seconds=301)},
        {"quote_retained": True},
        {"quote_refresh_error": "TIMEOUT"},
        {"reference_price_type": "LAST_TRADE"},
        {"bid": None},
        {"reference_price": Decimal(9)},
        {"currency": "USD"},
        {"position_id": uuid4()},
        {"monitoring_usable": False},
        {"quote_observed_at": NOW + timedelta(seconds=1)},
    ],
)
@pytest.mark.asyncio
async def test_unverified_failed_or_old_indications_cannot_change_rule_state(change):
    assert (await check(valuation(**change))).observation is None


@pytest.mark.asyncio
async def test_receipt_after_cycle_start_is_accepted_but_not_future_receipt():
    fetched = NOW + timedelta(seconds=40)
    result = await check(valuation(quote_retrieved_at=fetched), checked_at=lambda: fetched)
    assert result.observation.observed_at is None
    assert result.observation.received_at == fetched
    assert (
        await check(valuation(quote_retrieved_at=fetched), checked_at=lambda: NOW)
    ).observation is None


@pytest.mark.asyncio
async def test_cycle_caches_one_price_for_stop_and_target_and_unbound_rules_stay_blocked():
    rules = (
        RULE,
        replace(RULE, rule_key="CURRENT_TARGET", rule_type=MonitoringRuleType.TARGET_REACHED),
        replace(RULE, rule_key="UNBOUND", price_binding=None),
    )
    products = SimpleNamespace(for_trade=AsyncMock(return_value=valuation()))
    processor = SimpleNamespace(
        process=AsyncMock(
            return_value=SimpleNamespace(alert=None, transition=TriggerTransition.STAYED_CLEAR)
        )
    )
    subjects = SimpleNamespace(
        list_resolutions=AsyncMock(
            return_value=(
                MonitoringSubjectResolution(SUBJECT.position_id, replace(SUBJECT, rules=rules)),
            )
        )
    )
    result = await PositionMonitoringCycleService(
        subjects=subjects,
        market_data=None,
        products=products,
        processor=processor,
        now=lambda: NOW,
        new_id=uuid4,
    ).run()
    assert result.rules_evaluated == 2 and result.blocked_rules == 1
    assert result.position_errors == result.market_data_errors == 0
    assert all(c["observed_at"] is None for c in result.rule_checks[:2])
    products.for_trade.assert_awaited_once()


def test_migration_preserves_old_clocks_and_accepts_unknown_alert_times(monkeypatch):
    module = importlib.import_module("migrations.versions.20260922_0041_indicative_rule_time")
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE alerts (id INTEGER PRIMARY KEY, "
                "market_data_observed_at DATETIME NOT NULL)"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE monitoring_rule_states (id INTEGER PRIMARY KEY, "
                "last_seen_at DATETIME NOT NULL)"
            )
        )
        conn.execute(text("INSERT INTO alerts VALUES (1, '2026-09-21 10:00:00')"))
        conn.execute(text("INSERT INTO monitoring_rule_states VALUES (1, '2026-09-21 10:00:00')"))
        monkeypatch.setattr(module, "op", Operations(MigrationContext.configure(conn)))
        module.upgrade()
        assert (
            conn.scalar(text("SELECT time_basis FROM monitoring_rule_states")) == "SOURCE_TIMESTAMP"
        )
        assert (
            conn.scalar(text("SELECT market_data_observed_at FROM alerts")) == "2026-09-21 10:00:00"
        )
        conn.execute(text("INSERT INTO alerts VALUES (2, NULL)"))
        with pytest.raises(RuntimeError, match="unknown source timestamps"):
            module.downgrade()
        conn.execute(text("DELETE FROM alerts WHERE id=2"))
        conn.execute(text("UPDATE monitoring_rule_states SET time_basis='RECEIPT_TIMESTAMP'"))
        with pytest.raises(RuntimeError, match="receipt-ordered"):
            module.downgrade()
        conn.execute(text("UPDATE monitoring_rule_states SET time_basis='SOURCE_TIMESTAMP'"))
        module.downgrade()


@pytest.mark.asyncio
async def test_clock_basis_changes_keep_alert_dedup_but_do_not_compare_different_clocks():
    observation = (await check()).observation
    states, alerts = States(), Alerts()
    app = PositionMonitoringService(states=states, alerts=alerts, new_id=uuid4, now=lambda: NOW)

    async def evaluate(obs):
        return await app.evaluate(
            position_id=SUBJECT.position_id,
            trade_id=SUBJECT.trade_id,
            rule=RULE,
            observation=obs,
        )

    await evaluate(replace(observation, observed_at=NOW - timedelta(days=1)))
    await evaluate(observation)
    assert states.value.time_basis == "RECEIPT_TIMESTAMP"
    await evaluate(replace(observation, observed_at=NOW - timedelta(hours=1)))
    assert states.value.time_basis == "SOURCE_TIMESTAMP"
    assert states.value.first_seen_at == NOW - timedelta(hours=1)
    assert len(alerts.items) == 1 and not alerts.resolved


def test_background_evidence_does_not_treat_leadership_as_success_for_all_targets():
    from app.tools.audit_issuer_monitoring import summarize_background

    value = summarize_background(
        {"enabled": True, "running": True, "last_cycle_completed_at": NOW.isoformat()},
        {
            "enabled": True,
            "leader": True,
            "last_scan_at": NOW.isoformat(),
            "jobs": [
                {
                    "isin": SUBJECT.warrant_isin,
                    "lane": "WARRANTS",
                    "last_success_at": NOW.isoformat(),
                    "quotes": [
                        {
                            "provider": "FRANKFURT_QUOTES",
                            "bid": "1",
                            "retrieved_at": NOW.isoformat(),
                        }
                    ],
                }
            ],
        },
    )
    assert value["scheduler_cycle_evidenced"] and value["quote_refresh_leader_evidenced"]
    assert value["issuer_refresh_success_count"] == 0


def test_postgresql_migration_sql_drops_only_timestamp_requirement(monkeypatch):
    from io import StringIO

    module = importlib.import_module("migrations.versions.20260922_0041_indicative_rule_time")
    output = StringIO()
    context = MigrationContext.configure(
        dialect_name="postgresql", opts={"as_sql": True, "output_buffer": output}
    )
    monkeypatch.setattr(module, "op", Operations(context))
    module.upgrade()
    sql = output.getvalue()
    assert "ALTER COLUMN market_data_observed_at DROP NOT NULL" in sql
    assert "ADD COLUMN time_basis VARCHAR(24) DEFAULT 'SOURCE_TIMESTAMP' NOT NULL" in sql
    assert "UPDATE" not in sql and "DELETE" not in sql


@pytest.mark.asyncio
async def test_real_repositories_persist_null_source_time_and_receipt_clock():
    from sqlalchemy.orm import Session

    from app.features.alert.persistence.models import AlertModel
    from app.features.alert.persistence.repositories import SqlAlchemyAlertRepository
    from app.features.position_monitoring.persistence.models import (
        MonitoringRuleStateModel,
    )
    from app.features.position_monitoring.persistence.repositories import (
        SqlAlchemyMonitoringRuleStateRepository,
    )

    engine = create_engine("sqlite://")
    try:
        with engine.begin() as connection:
            AlertModel.__table__.create(connection)
            MonitoringRuleStateModel.__table__.create(connection)
        with Session(engine, expire_on_commit=False) as session:
            # Use real SQLite SQL without introducing an optional async DB driver.
            bridge = SimpleNamespace(
                scalar=AsyncMock(side_effect=session.scalar),
                get=AsyncMock(side_effect=session.get),
                add=session.add,
            )
            states = SqlAlchemyMonitoringRuleStateRepository(bridge)
            alerts = SqlAlchemyAlertRepository(bridge)
            app = PositionMonitoringService(
                states=states, alerts=alerts, new_id=uuid4, now=lambda: NOW
            )
            result = await app.evaluate(
                position_id=SUBJECT.position_id,
                trade_id=SUBJECT.trade_id,
                rule=RULE,
                observation=(await check()).observation,
            )
            session.commit()
            session.expunge_all()
            saved = await alerts.get(result.alert.id)
            state = await states.get(position_id=SUBJECT.position_id, rule_key=RULE.rule_key)
            assert saved.market_data_observed_at is None
            assert saved.price_context["observed_at"] is None
            assert saved.price_context["retrieved_at"] == NOW.isoformat()
            assert state.time_basis == "RECEIPT_TIMESTAMP"
    finally:
        engine.dispose()
