from __future__ import annotations

from app.features.position_monitoring.domain.models import (
    MonitoringRule,
    MonitoringRuleType,
    PriceObservation,
    RuleEvaluation,
)


class PositionRuleEvaluator:
    """Pure deterministic evaluator for currently supported price rules."""

    @staticmethod
    def evaluate(*, rule: MonitoringRule, observation: PriceObservation) -> RuleEvaluation:
        if rule.rule_type is MonitoringRuleType.STOP_REACHED:
            triggered = observation.value <= rule.threshold
            comparator = "<="
        elif rule.rule_type is MonitoringRuleType.TARGET_REACHED:
            triggered = observation.value >= rule.threshold
            comparator = ">="
        else:
            raise ValueError(f"unsupported monitoring rule: {rule.rule_type}")

        return RuleEvaluation(
            triggered=triggered,
            reason=(
                f"observed_value={observation.value} {comparator} threshold={rule.threshold}"
                if triggered
                else (
                    f"observed_value={observation.value} does not satisfy "
                    f"{comparator} threshold={rule.threshold}"
                )
            ),
        )
