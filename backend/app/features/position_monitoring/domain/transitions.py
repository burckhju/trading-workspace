from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.features.position_monitoring.domain.models import MonitoringRuleState, RuleEvaluation


class TriggerTransition(StrEnum):
    ENTERED = "ENTERED"
    STAYED_TRIGGERED = "STAYED_TRIGGERED"
    EXITED = "EXITED"
    STAYED_CLEAR = "STAYED_CLEAR"


@dataclass(frozen=True, slots=True)
class TransitionDecision:
    transition: TriggerTransition
    create_alert: bool
    resolve_alert: bool


def decide_transition(
    *, current: MonitoringRuleState | None, evaluation: RuleEvaluation
) -> TransitionDecision:
    was_triggered = current.triggered if current is not None else False
    if not was_triggered and evaluation.triggered:
        return TransitionDecision(TriggerTransition.ENTERED, True, False)
    if was_triggered and evaluation.triggered:
        return TransitionDecision(TriggerTransition.STAYED_TRIGGERED, False, False)
    if was_triggered and not evaluation.triggered:
        return TransitionDecision(TriggerTransition.EXITED, False, True)
    return TransitionDecision(TriggerTransition.STAYED_CLEAR, False, False)
