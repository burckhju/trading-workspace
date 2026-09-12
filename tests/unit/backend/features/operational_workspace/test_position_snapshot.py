from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import app.features.operational_workspace.service.position_snapshot as snapshot_module
from app.features.operational_workspace.service.position_snapshot import (
    OperationalPositionSnapshotService,
)
from app.features.position_monitoring.service.health import (
    MonitoringHealthStatus,
    PositionMonitoringHealth,
)
from app.features.position_monitoring.service.product_valuation import (
    ProductPositionValuation,
    ProductValuationStatus,
)


class _Rows:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def all(self) -> list[Any]:
        return self._rows


class _ManagementEvents:
    def __init__(self, _session: AsyncSession) -> None:
        pass

    async def list_effective_for_trade(self, _trade_id):
        return []


@pytest.mark.asyncio
async def test_composes_alert_first_snapshot_with_plan_rules_and_current_valuation(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        snapshot_module,
        "SqlAlchemyTradeManagementEventRepository",
        _ManagementEvents,
    )
    workspace_id = uuid4()
    trade_id = uuid4()
    position_id = uuid4()
    plan_version_id = uuid4()
    opened_at = datetime(2026, 9, 8, 8, 0, tzinfo=UTC)
    position = SimpleNamespace(
        id=position_id,
        opened_at=opened_at,
        opened_on=None,
        open_quantity=10,
        average_entry_price=Decimal("2.00"),
        cost_basis=Decimal("20.00"),
        realized_gross_pnl=Decimal("1.50"),
    )
    trade = SimpleNamespace(id=trade_id, trade_plan_version_id=plan_version_id)
    warrant = SimpleNamespace(display_name="Test Warrant")
    alert = SimpleNamespace(alert_type="STOP_REACHED")
    plan_version = SimpleNamespace(id=plan_version_id, stop_price=Decimal("19000"))

    session = AsyncMock(spec=AsyncSession)
    session.execute.return_value = _Rows([(position, trade, warrant)])
    session.scalars.return_value = _Rows([alert])
    session.scalar.side_effect = [plan_version, Decimal("20500")]

    async def health_reader(requested_trade_id):
        assert requested_trade_id == trade_id
        return PositionMonitoringHealth(
            trade_id=trade_id,
            position_id=position_id,
            status=MonitoringHealthStatus.OK,
            reason="COMPLETED_DAILY_PRICE_CURRENT",
            symbol="DAX.INDX",
        )

    async def valuation_reader(requested_trade_id):
        assert requested_trade_id == trade_id
        return ProductPositionValuation(
            trade_id=trade_id,
            position_id=position_id,
            status=ProductValuationStatus.AVAILABLE,
            reason="WARRANT_QUOTE_AVAILABLE",
            symbol="TEST12.STU",
            currency="EUR",
            market_value=Decimal("25.00"),
            unrealized_gross_pnl=Decimal("5.00"),
        )

    service = OperationalPositionSnapshotService(
        cast(AsyncSession, session),
        health_reader=health_reader,
        valuation_reader=valuation_reader,
    )

    result = await service.list_positions(workspace_id=workspace_id)

    assert len(result) == 1
    item = result[0]
    assert item.trade_id == trade_id
    assert item.stop_price == Decimal("19000")
    assert item.target_price == Decimal("20500")
    assert item.market_value == Decimal("25.00")
    assert item.unrealized_gross_pnl == Decimal("5.00")
    assert item.monitoring_status == "OK"
    assert item.valuation_status == "AVAILABLE"
    assert item.open_alert_types == ("STOP_REACHED",)
    assert item.attention_state == "ALERT"
    assert item.target == f"/trade-management?trade_id={trade_id}"


@pytest.mark.asyncio
async def test_fails_closed_for_unhealthy_or_missing_snapshot_reads(monkeypatch) -> None:
    monkeypatch.setattr(
        snapshot_module,
        "SqlAlchemyTradeManagementEventRepository",
        _ManagementEvents,
    )
    workspace_id = uuid4()
    trade_id = uuid4()
    position_id = uuid4()
    position = SimpleNamespace(
        id=position_id,
        opened_at=datetime(2026, 9, 8, 8, 0, tzinfo=UTC),
        opened_on=None,
        open_quantity=5,
        average_entry_price=Decimal("3.00"),
        cost_basis=Decimal("15.00"),
        realized_gross_pnl=Decimal("0"),
    )
    trade = SimpleNamespace(id=trade_id, trade_plan_version_id=None)
    warrant = SimpleNamespace(display_name="External Warrant")

    session = AsyncMock(spec=AsyncSession)
    session.execute.return_value = _Rows([(position, trade, warrant)])
    session.scalars.return_value = _Rows([])

    async def health_reader(_trade_id):
        return PositionMonitoringHealth(
            trade_id=trade_id,
            position_id=position_id,
            status=MonitoringHealthStatus.STALE,
            reason="COMPLETED_DAILY_PRICE_STALE",
            symbol="DAX.INDX",
        )

    async def valuation_reader(_trade_id):
        return ProductPositionValuation(
            trade_id=trade_id,
            position_id=position_id,
            status=ProductValuationStatus.STALE,
            reason="WARRANT_QUOTE_STALE",
            symbol="OLD.STU",
            currency="EUR",
            market_value=None,
            unrealized_gross_pnl=None,
        )

    service = OperationalPositionSnapshotService(
        cast(AsyncSession, session),
        health_reader=health_reader,
        valuation_reader=valuation_reader,
    )

    result = await service.list_positions(workspace_id=workspace_id)

    item = result[0]
    assert item.stop_price is None
    assert item.target_price is None
    assert item.market_value is None
    assert item.unrealized_gross_pnl is None
    assert item.attention_state == "DATA_HEALTH"
    assert item.open_alert_count == 0
    assert item.monitoring_status == "STALE"
    assert item.valuation_status == "STALE"


def test_attention_state_is_ok_only_without_alerts_and_with_healthy_data() -> None:
    assert (
        OperationalPositionSnapshotService._attention_state(
            alert_types=(),
            monitoring_status="OK",
            valuation_status="AVAILABLE",
        )
        == "OK"
    )
    assert (
        OperationalPositionSnapshotService._attention_state(
            alert_types=("TARGET_REACHED",),
            monitoring_status="ERROR",
            valuation_status="ERROR",
        )
        == "ALERT"
    )


@pytest.mark.asyncio
async def test_workspace_shows_frankfurt_analysis_values_with_warning_and_provenance(monkeypatch):
    monkeypatch.setattr(
        snapshot_module, "SqlAlchemyTradeManagementEventRepository", _ManagementEvents
    )
    trade_id, position_id = uuid4(), uuid4()
    position = SimpleNamespace(
        id=position_id,
        opened_at=datetime(2026, 9, 8, tzinfo=UTC),
        opened_on=None,
        open_quantity=2000,
        average_entry_price=Decimal("0.51"),
        cost_basis=Decimal("1020"),
        realized_gross_pnl=Decimal("0"),
    )
    session = AsyncMock(spec=AsyncSession)
    session.execute.return_value = _Rows(
        [
            (
                position,
                SimpleNamespace(id=trade_id, trade_plan_version_id=None),
                SimpleNamespace(display_name="BNP Call"),
            )
        ]
    )
    session.scalars.return_value = _Rows([])
    valuation = ProductPositionValuation(
        trade_id=trade_id,
        position_id=position_id,
        status=ProductValuationStatus.INDICATIVE,
        reason="REFERENCE_PRICE_AVAILABLE_FOR_ANALYSIS",
        currency="EUR",
        analysis_usable=True,
        analysis_warning="OUTDATED_QUOTE_INDICATIVE_ANALYSIS_ONLY",
        analysis_market_value=Decimal("462"),
        analysis_unrealized_gross_pnl=Decimal("-558"),
        selected_source="FRANKFURT_QUOTES",
        quote_observed_at=datetime(2026, 9, 11, 17, 43, tzinfo=UTC),
    )
    service = OperationalPositionSnapshotService(
        session,
        health_reader=AsyncMock(return_value=None),
        valuation_reader=AsyncMock(return_value=valuation),
    )
    (item,) = await service.list_positions(workspace_id=uuid4())
    assert item.market_value == Decimal("462") and item.unrealized_gross_pnl == Decimal("-558")
    assert item.valuation_status == "INDICATIVE" and item.attention_state == "DATA_HEALTH"
    assert (
        item.quote_source == "FRANKFURT_QUOTES"
        and item.analysis_warning == valuation.analysis_warning
    )
