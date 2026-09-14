from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from tests.unit.backend.features.position_monitoring.test_cycle import Subjects
from tests.unit.backend.features.position_monitoring.test_health import (
    LISTING_ID,
    NOW,
    UNDERLYING_ID,
    _daily_result,
)
from tests.unit.backend.features.position_monitoring.test_monitoring_application import (
    AlertRepo,
    StateRepo,
)

from app.features.position_monitoring.domain.evaluator import PositionRuleEvaluator
from app.features.position_monitoring.domain.models import (
    MonitoringRule,
    MonitoringRuleType,
    PriceObservation,
)
from app.features.position_monitoring.service.application import PositionMonitoringService
from app.features.position_monitoring.service.cycle import PositionMonitoringCycleService
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

WARRANT = uuid4()
BINDING = PriceBinding(PriceBasis.WARRANT, WARRANT, "EUR")
RULE = MonitoringRule("CURRENT_TARGET", MonitoringRuleType.TARGET_REACHED, Decimal("2.50"), BINDING)
SUBJECT = MonitoringSubject(
    uuid4(),
    uuid4(),
    uuid4(),
    LISTING_ID,
    uuid4(),
    "UNH",
    (RULE,),
    WARRANT,
    UNDERLYING_ID,
    "DE000VH2LU21",
    "EUR",
)


def valuation(**kwargs):
    value = ProductPositionValuation(
        SUBJECT.trade_id,
        SUBJECT.position_id,
        ProductValuationStatus.LAST_AVAILABLE,
        "MARKET_CLOSED_LAST_AVAILABLE_QUOTE",
        quote_listing_id=uuid4(),
        isin=SUBJECT.warrant_isin,
        currency="EUR",
        monitoring_usable=True,
        reference_price=Decimal("0.24"),
        reference_price_type="BID",
        quote_observed_at=NOW - timedelta(days=1),
        quote_retrieved_at=NOW,
        selected_source="VONTOBEL_MARKETS",
        provider_identity=SUBJECT.warrant_isin,
        analysis_warning="OUTDATED_QUOTE_INDICATIVE_ANALYSIS_ONLY",
    )
    return replace(value, **kwargs)


async def check(rule=RULE, subject=SUBJECT, value=None, daily=None, **kwargs):
    products = AsyncMock()
    products.for_trade.return_value = value or valuation()
    market = AsyncMock()
    market.get_latest_completed_daily_price.return_value = daily or _daily_result(
        trading_date=NOW.date() - timedelta(days=1)
    )
    return await rule_price(
        subject=subject,
        rule=rule,
        products=products,
        market_data=market,
        now=NOW,
        max_age_days=4,
        **kwargs,
    )


@pytest.mark.asyncio
async def test_unh_target_compares_product_bid_and_never_underlying_337():
    products = AsyncMock()
    products.for_trade.return_value = valuation()
    market = AsyncMock()
    states, alerts = StateRepo(), AlertRepo()
    app = PositionMonitoringService(states=states, alerts=alerts, new_id=uuid4, now=lambda: NOW)
    result = await PositionMonitoringCycleService(
        subjects=Subjects(
            (
                MonitoringSubjectResolution(
                    SUBJECT.position_id,
                    replace(
                        SUBJECT,
                        rules=(
                            RULE,
                            replace(
                                RULE,
                                rule_key="CURRENT_STOP",
                                rule_type=MonitoringRuleType.STOP_REACHED,
                                threshold=Decimal("0.16"),
                            ),
                        ),
                    ),
                ),
            )
        ),
        products=products,
        market_data=market,
        processor=type("Processor", (), {"process": app.evaluate})(),
        now=lambda: NOW,
        new_id=uuid4,
    ).run()
    assert result.positions_checked == 1 and result.rules_evaluated == 2
    assert result.alerts_created == 0
    assert result.rule_checks[0]["observed_value"] == "0.24"
    assert result.rule_checks[0]["warning"] == "OUTDATED_QUOTE_INDICATIVE_ANALYSIS_ONLY"
    products.for_trade.assert_awaited_once_with(SUBJECT.trade_id)
    market.get_latest_completed_daily_price.assert_not_awaited()


@pytest.mark.asyncio
async def test_warrant_rules_work_without_any_underlying_mapping():
    result = await check(subject=replace(SUBJECT, listing_id=None, mapping_id=None))
    assert result.observation.value == Decimal("0.24")
    assert result.observation.price_binding == BINDING


@pytest.mark.asyncio
async def test_unconfirmed_legacy_rules_do_not_request_prices_or_create_alerts():
    market, products, processor = AsyncMock(), AsyncMock(), AsyncMock()
    subject = replace(SUBJECT, rules=(replace(RULE, price_binding=None),))
    result = await PositionMonitoringCycleService(
        subjects=Subjects((MonitoringSubjectResolution(subject.position_id, subject),)),
        market_data=market,
        products=products,
        processor=processor,
        new_id=uuid4,
    ).run()
    assert result.blocked_rules == 1 and result.positions_checked == result.rules_evaluated == 0
    assert result.rule_checks[0]["reason"] == "RULE_PRICE_BASIS_UNCONFIRMED"
    market.get_latest_completed_daily_price.assert_not_awaited()
    products.for_trade.assert_not_awaited()
    processor.process.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "field,value",
    [
        ("trade_id", uuid4()),
        ("position_id", uuid4()),
        ("isin", "DE000VH4VNA6"),
        ("currency", "USD"),
        ("quote_listing_id", None),
        ("provider_identity", None),
        ("selected_source", None),
    ],
)
async def test_wrong_warrant_quote_provenance_never_matches(field, value):
    result = await check(value=valuation(**{field: value}))
    assert result.status == "BLOCKED" and result.observation is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "field,value",
    [
        ("quote_observed_at", None),
        ("quote_observed_at", NOW + timedelta(seconds=1)),
        ("monitoring_usable", False),
        ("reference_price", None),
    ],
)
async def test_invalid_or_missing_warrant_quote_is_rejected(field, value):
    result = await check(value=valuation(**{field: value}))
    assert result.observation is None


@pytest.mark.asyncio
async def test_frankfurt_last_trade_retains_reference_semantics():
    result = await check(
        value=valuation(
            selected_source="FRANKFURT_QUOTES",
            reference_price=Decimal("0.231"),
            reference_price_type="LAST_TRADE",
            analysis_warning=None,
        )
    )
    assert result.status == "INDICATIVE"
    assert result.observation.context["price_type"] == "LAST_TRADE"
    assert result.observation.context["execution_usable"] == "false"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "kind,expected",
    [
        (MonitoringRuleType.STOP_REACHED, Decimal("23900")),
        (MonitoringRuleType.TARGET_REACHED, Decimal("24200")),
    ],
)
async def test_confirmed_underlying_rules_use_matching_daily_low_or_high(kind, expected):
    rule = replace(
        RULE,
        rule_type=kind,
        price_binding=PriceBinding(PriceBasis.UNDERLYING, UNDERLYING_ID, "EUR"),
    )
    result = await check(rule=rule)
    assert result.observation.value == expected
    assert (
        result.observation.context["trading_date"] == (NOW.date() - timedelta(days=1)).isoformat()
    )
    assert result.observation.context["observed_at"] == NOW.isoformat()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "change,reason",
    [
        ({"listing_id": uuid4()}, "UNDERLYING_PRICE_IDENTITY_OR_CURRENCY_MISMATCH"),
        ({"currency": "USD"}, "UNDERLYING_PRICE_IDENTITY_OR_CURRENCY_MISMATCH"),
        ({"trading_date": NOW.date()}, "DAILY_SESSION_NOT_COMPLETED"),
        ({"trading_date": NOW.date() - timedelta(days=5)}, "COMPLETED_DAILY_PRICE_STALE"),
        ({"retrieved_at": NOW + timedelta(minutes=1)}, "INVALID_QUOTE_TIMESTAMP"),
    ],
)
async def test_underlying_identity_currency_and_completed_session_guards(change, reason):
    rule = replace(RULE, price_binding=PriceBinding(PriceBasis.UNDERLYING, UNDERLYING_ID, "EUR"))
    daily = _daily_result(trading_date=NOW.date() - timedelta(days=1))
    result = await check(rule=rule, daily=replace(daily, data=replace(daily.data, **change)))
    assert result.observation is None and result.reason == reason


@pytest.mark.parametrize(
    "observation",
    [
        PriceObservation(Decimal("337"), NOW),
        PriceObservation(
            Decimal("337"), NOW, PriceBinding(PriceBasis.UNDERLYING, UNDERLYING_ID, "EUR")
        ),
        PriceObservation(Decimal("3"), NOW, replace(BINDING, currency="USD")),
        PriceObservation(Decimal("3"), NOW, replace(BINDING, instrument_id=uuid4())),
        PriceObservation(Decimal("NaN"), NOW, BINDING),
        PriceObservation(Decimal("-1"), NOW, BINDING),
    ],
)
def test_evaluator_itself_rejects_unbound_or_mismatched_comparisons(observation):
    with pytest.raises(ValueError):
        PositionRuleEvaluator.evaluate(rule=RULE, observation=observation)


@pytest.mark.asyncio
async def test_basis_change_resets_dedup_and_keeps_exact_alert_provenance():
    states, alerts = StateRepo(), AlertRepo()
    app = PositionMonitoringService(states=states, alerts=alerts, new_id=uuid4, now=lambda: NOW)
    context = {
        "provider": "FRANKFURT_QUOTES",
        "price_type": "LAST_TRADE",
        "warning": "INDICATIVE_REFERENCE_PRICE",
    }
    observation = PriceObservation(Decimal("3"), NOW, BINDING, context)
    first = await app.evaluate(
        position_id=SUBJECT.position_id,
        trade_id=SUBJECT.trade_id,
        rule=RULE,
        observation=observation,
    )
    assert first.alert.price_context["basis"] == "WARRANT"
    assert first.alert.price_context["warning"] == "INDICATIVE_REFERENCE_PRICE"
    repeat = await app.evaluate(
        position_id=SUBJECT.position_id,
        trade_id=SUBJECT.trade_id,
        rule=RULE,
        observation=observation,
    )
    assert repeat.alert is None
    other = PriceBinding(PriceBasis.UNDERLYING, UNDERLYING_ID, "EUR")
    second = await app.evaluate(
        position_id=SUBJECT.position_id,
        trade_id=SUBJECT.trade_id,
        rule=replace(RULE, price_binding=other),
        observation=replace(observation, price_binding=other),
    )
    assert second.alert is not None
    assert alerts.values[first.alert.id].status.value == "RESOLVED"
    with pytest.raises(ValueError, match="OUT_OF_ORDER"):
        await app.evaluate(
            position_id=SUBJECT.position_id,
            trade_id=SUBJECT.trade_id,
            rule=replace(RULE, price_binding=other),
            observation=replace(
                observation, price_binding=other, observed_at=NOW - timedelta(days=1)
            ),
        )


@pytest.mark.asyncio
async def test_completed_daily_request_excludes_the_current_session():
    market = AsyncMock()
    market.get_latest_completed_daily_price.return_value = _daily_result(
        trading_date=NOW.date() - timedelta(days=1)
    )
    rule = replace(RULE, price_binding=PriceBinding(PriceBasis.UNDERLYING, UNDERLYING_ID, "EUR"))
    result = await rule_price(
        subject=SUBJECT, rule=rule, market_data=market, products=None, now=NOW, max_age_days=4
    )
    assert result.observation is not None
    assert market.get_latest_completed_daily_price.call_args.args[
        0
    ].as_of_date == NOW.date() - timedelta(days=1)
