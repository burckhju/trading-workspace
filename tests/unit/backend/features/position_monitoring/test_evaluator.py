from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from app.features.position_monitoring.domain.evaluator import PositionRuleEvaluator
from app.features.position_monitoring.domain.models import (
    MonitoringRule,
    MonitoringRuleState,
    MonitoringRuleType,
    PriceObservation,
)
from app.features.position_monitoring.domain.transitions import TriggerTransition, decide_transition
from app.features.trade_position.domain.price_binding import PriceBasis, PriceBinding

BINDING = PriceBinding(PriceBasis.UNDERLYING, UUID("00000000-0000-4000-8000-000000000099"), "EUR")


def test_stop_rule_enters_once_stays_deduplicated_and_resets() -> None:
    rule = MonitoringRule(
        "stop:100", MonitoringRuleType.STOP_REACHED, Decimal("100"), price_binding=BINDING
    )
    obs = PriceObservation(Decimal("99"), datetime(2026, 9, 3, tzinfo=UTC), price_binding=BINDING)
    evaluation = PositionRuleEvaluator.evaluate(rule=rule, observation=obs)

    first = decide_transition(current=None, evaluation=evaluation)
    assert first.transition is TriggerTransition.ENTERED
    assert first.create_alert is True

    state = MonitoringRuleState(
        position_id=uuid4(),
        rule_key=rule.rule_key,
        triggered=True,
        first_seen_at=obs.observed_at,
        last_seen_at=obs.observed_at,
        last_observed_value=obs.value,
        threshold_value=rule.threshold,
        active_alert_id=uuid4(),
    )
    repeated = decide_transition(current=state, evaluation=evaluation)
    assert repeated.transition is TriggerTransition.STAYED_TRIGGERED
    assert repeated.create_alert is False

    clear = PositionRuleEvaluator.evaluate(
        rule=rule,
        observation=PriceObservation(
            Decimal("101"), datetime(2026, 9, 4, tzinfo=UTC), price_binding=BINDING
        ),
    )
    exited = decide_transition(current=state, evaluation=clear)
    assert exited.transition is TriggerTransition.EXITED
    assert exited.resolve_alert is True


def test_target_rule_only_triggers_at_or_above_threshold() -> None:
    rule = MonitoringRule(
        "target:120", MonitoringRuleType.TARGET_REACHED, Decimal("120"), price_binding=BINDING
    )
    below = PositionRuleEvaluator.evaluate(
        rule=rule,
        observation=PriceObservation(
            Decimal("119.99"), datetime(2026, 9, 3, tzinfo=UTC), price_binding=BINDING
        ),
    )
    reached = PositionRuleEvaluator.evaluate(
        rule=rule,
        observation=PriceObservation(
            Decimal("120"), datetime(2026, 9, 3, tzinfo=UTC), price_binding=BINDING
        ),
    )
    assert below.triggered is False
    assert reached.triggered is True
