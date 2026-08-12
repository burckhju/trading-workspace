"""TradePlan lifecycle invariants."""

from app.features.trade_plan.domain.enums import TradePlanStatus

_ALLOWED = {
    TradePlanStatus.DRAFT: frozenset({TradePlanStatus.READY_FOR_REVIEW, TradePlanStatus.ABANDONED}),
    TradePlanStatus.READY_FOR_REVIEW: frozenset(
        {TradePlanStatus.DRAFT, TradePlanStatus.APPROVED, TradePlanStatus.ABANDONED}
    ),
    TradePlanStatus.APPROVED: frozenset({TradePlanStatus.SUPERSEDED}),
    TradePlanStatus.ABANDONED: frozenset(),
    TradePlanStatus.SUPERSEDED: frozenset(),
}


def ensure_transition(current: TradePlanStatus, target: TradePlanStatus) -> None:
    if current == target:
        return
    if target not in _ALLOWED[current]:
        raise ValueError(f"invalid trade plan transition: {current.value} -> {target.value}")
