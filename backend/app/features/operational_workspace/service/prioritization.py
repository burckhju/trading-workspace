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
from app.features.position_monitoring.service.product_valuation import (
    ProductPositionValuation,
    ProductValuationStatus,
)

PositionHealthReader = Callable[[UUID], Awaitable[PositionMonitoringHealth | None]]
ProductValuationReader = Callable[[UUID], Awaitable[ProductPositionValuation | None]]

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


def _product_title(status: ProductValuationStatus) -> str:
    if status is ProductValuationStatus.STALE:
        return "Produktkurs veraltet"
    if status is ProductValuationStatus.MISSING:
        return "Produktkurs fehlt"
    if status is ProductValuationStatus.UNAVAILABLE:
        return "Produktbewertung nicht verfügbar"
    return "Produktbewertung prüfen"


def _product_detail(value: ProductPositionValuation) -> str:
    if value.status is ProductValuationStatus.STALE:
        age = (
            f" ({value.quote_age_seconds} Sek. alt)"
            if value.quote_age_seconds is not None
            else ""
        )
        return (
            "Der letzte Kurs des gehaltenen Produkts ist zu alt"
            f"{age}. Daraus werden kein aktueller Marktwert und kein unrealized P&L abgeleitet."
        )
    if value.status is ProductValuationStatus.MISSING:
        return (
            "Für das gehaltene Produkt liegt kein belastbarer Bid vor. "
            "Marktwert und unrealized P&L werden nicht geschätzt."
        )
    if value.status is ProductValuationStatus.UNAVAILABLE:
        return (
            "Die Produktbewertung ist für das dokumentierte WarrantListing derzeit nicht "
            "verfügbar. Das System rät keinen Ersatzkurs oder Börsenplatz."
        )
    return (
        "Die Datenbasis für die Produktbewertung konnte nicht verlässlich ausgewertet werden. "
        "Marktwert und unrealized P&L werden nicht als aktuell dargestellt."
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
    valuation_reader: ProductValuationReader | None = None,
) -> tuple[OperationalAction, ...]:
    """Surface existing alert and data-health facts before normal workspace actions."""

    prioritized: list[OperationalAction] = []
    for action in actions:
        if (
            action.action_type != "OPEN_POSITION_MANAGEMENT"
            or action.resource_type != "trade"
        ):
            prioritized.append(action)
            continue

        health = await health_reader(action.resource_id)
        valuation = (
            await valuation_reader(action.resource_id) if valuation_reader else None
        )
        underlying_problem = (
            health is not None and health.status is not MonitoringHealthStatus.OK
        )
        product_problem = (
            valuation is not None
            and valuation.status is not ProductValuationStatus.AVAILABLE
        )

        if not underlying_problem and not product_problem:
            prioritized.append(action)
            continue

        if underlying_problem and product_problem:
            assert health is not None
            assert valuation is not None
            prioritized.append(
                replace(
                    action,
                    source_feature="Position Monitoring / Data Health",
                    action_type="POSITION_DATA_HEALTH",
                    title="Positionsdaten prüfen",
                    detail=(
                        f"Underlying-Monitoring: {_health_detail(health)} "
                        f"Produktbewertung: {_product_detail(valuation)}"
                    ),
                    next_action="Positionsdatenzustand prüfen",
                    occurred_at=(
                        health.market_data_observed_at
                        or valuation.quote_observed_at
                        or action.occurred_at
                    ),
                )
            )
            continue

        if underlying_problem:
            assert health is not None
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
            continue

        assert valuation is not None
        prioritized.append(
            replace(
                action,
                source_feature="Position Monitoring / Product Data Health",
                action_type="POSITION_DATA_HEALTH",
                title=_product_title(valuation.status),
                detail=_product_detail(valuation),
                next_action="Produktdatenzustand prüfen",
                occurred_at=valuation.quote_observed_at or action.occurred_at,
            )
        )

    return tuple(sorted(prioritized, key=_sort_key))
