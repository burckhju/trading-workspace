"""Presentation-only prioritization for operational workspace actions."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

from app.features.operational_workspace.service.read_model import OperationalAction
from app.features.position_monitoring.service.health import (
    MonitoringHealthStatus,
    PositionMonitoringHealth,
)

PositionHealthReader = Callable[[UUID], Awaitable[PositionMonitoringHealth | None]]

_PRIORITY_ORDER = {"ACTION": 0, "REVIEW": 1, "BLOCKED": 2}
_ACTION_TYPE_ORDER = {
    "POSITION_ALERT": 0,
    "POSITION_DATA_HEALTH": 1,
}


def _health_title(status: MonitoringHealthStatus) -> str:
    if status is MonitoringHealthStatus.STALE:
        return "Monitoring-Daten veraltet"
    if status is MonitoringHealthStatus.MISSING:
        return "Monitoring-Daten fehlen"
    return "Monitoring-Daten prüfen"


def _health_detail(health: PositionMonitoringHealth) -> str:
    if health.status is MonitoringHealthStatus.STALE:
        age = f" ({health.age_days} Tag(e) alt)" if health.age_days is not None else ""
        return (
            "Die letzten completed-daily Underlying-Daten sind zu alt"
            f"{age}. Bis zur Klärung wird daraus kein Stop-/Target-Alert abgeleitet."
        )
    if health.status is MonitoringHealthStatus.MISSING:
        return (
            "Für das Underlying liegen keine completed-daily Marktdaten vor. "
            "Bis zur Klärung wird daraus kein Stop-/Target-Alert abgeleitet."
        )
    return (
        "Die Datenbasis für die Stop-/Target-Überwachung konnte nicht verlässlich ausgewertet "
        "werden. Den technischen Datenzustand im Trade-Management prüfen."
    )


def _sort_key(action: OperationalAction) -> tuple[int, int, datetime, str]:
    occurred_at = action.occurred_at
    if occurred_at is None:
        occurred_at = datetime.max.replace(tzinfo=UTC)
    elif occurred_at.tzinfo is None:
        occurred_at = occurred_at.replace(tzinfo=UTC)
    action_order = _ACTION_TYPE_ORDER.get(action.action_type, 2)
    return (_PRIORITY_ORDER[action.priority], action_order, occurred_at, action.id)


async def prioritize_position_monitoring(
    actions: tuple[OperationalAction, ...],
    *,
    health_reader: PositionHealthReader,
) -> tuple[OperationalAction, ...]:
    """Surface existing alert and data-health facts before normal workspace actions."""

    prioritized: list[OperationalAction] = []
    for action in actions:
        if action.action_type != "OPEN_POSITION_MANAGEMENT" or action.resource_type != "trade":
            prioritized.append(action)
            continue

        health = await health_reader(action.resource_id)
        if health is None or health.status is MonitoringHealthStatus.OK:
            prioritized.append(action)
            continue

        prioritized.append(
            replace(
                action,
                source_feature="Position Monitoring / Data Health",
                action_type="POSITION_DATA_HEALTH",
                title=_health_title(health.status),
                detail=_health_detail(health),
                next_action="Monitoring-Datenzustand prüfen",
                occurred_at=health.market_data_observed_at or action.occurred_at,
            )
        )

    return tuple(sorted(prioritized, key=_sort_key))
