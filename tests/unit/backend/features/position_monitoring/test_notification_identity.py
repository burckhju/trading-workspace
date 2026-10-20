"""Product display data survives the monitoring-to-notification handoff."""

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from tests.unit.backend.features.notification.test_creation import Repo
from tests.unit.backend.features.notification.test_warrant_name import ISIN, NAME, WKN, alert
from tests.unit.backend.features.position_monitoring.test_cycle import Subjects
from tests.unit.backend.features.position_monitoring.test_monitoring_application import (
    AlertRepo,
    StateRepo,
)

from app.features.position_monitoring.domain.models import (
    MonitoringRule,
    MonitoringRuleType,
    PriceObservation,
)
from app.features.position_monitoring.service import cycle, runtime
from app.features.position_monitoring.service.application import PositionMonitoringService
from app.features.position_monitoring.service.rule_prices import RulePriceResult
from app.features.position_monitoring.service.subjects import (
    MonitoringSubject,
    MonitoringSubjectResolution,
    SqlAlchemyMonitoringSubjectReader,
)
from app.features.product.persistence.models import WarrantModel
from app.features.trade_position.domain.enums import TradeManagementEventType
from app.features.trade_position.domain.models import TradeManagementEvent
from app.features.trade_position.domain.price_binding import PriceBasis, PriceBinding
from app.features.trade_position.persistence.models import PositionModel, TradeModel

NOW = datetime(2026, 9, 14, 10, tzinfo=UTC)


@pytest.mark.asyncio
async def test_subject_uses_already_loaded_warrant_even_without_stock_listing() -> None:
    workspace, warrant_id, trade_id, position_id = (uuid4() for _ in range(4))
    warrant = WarrantModel(
        id=warrant_id,
        workspace_id=workspace,
        underlying_id=uuid4(),
        display_name=NAME,
        isin=ISIN,
        wkn=WKN,
    )
    trade = TradeModel(id=trade_id, workspace_id=workspace, product_id=warrant_id)
    position = PositionModel(id=position_id, trade_id=trade_id, product_id=warrant_id)
    session = AsyncMock()
    session.scalar.return_value = None  # No underlying listing or mapping.
    reader = SqlAlchemyMonitoringSubjectReader(session, for_rule_evaluation=True)
    reader._management_events = AsyncMock()
    reader._management_events.list_effective_for_trade.return_value = [
        TradeManagementEvent(
            id=uuid4(),
            trade_id=trade_id,
            event_type=TradeManagementEventType.TARGET_CHANGED,
            effective_at=NOW,
            recorded_at=NOW,
            recorded_by=uuid4(),
            numeric_value=Decimal("2.50"),
            price_binding=PriceBinding(PriceBasis.WARRANT, warrant_id, "EUR"),
        )
    ]
    resolved = await reader._resolve(position, trade, warrant)
    assert resolved.subject is not None
    assert resolved.subject.warrant_name == NAME
    assert resolved.subject.warrant_wkn == WKN
    assert resolved.subject.warrant_isin == ISIN
    assert resolved.subject.warrant_id == warrant_id
    assert resolved.subject.mapping_id is None
    assert session.scalar.await_count == 2  # Existing listing/mapping queries only.


@pytest.mark.parametrize("basis", list(PriceBasis))
@pytest.mark.parametrize("kind", list(MonitoringRuleType))
@pytest.mark.asyncio
async def test_two_warrants_on_same_underlying_keep_distinct_names(basis, kind, monkeypatch):
    underlying, workspace = uuid4(), uuid4()
    items = []
    for index in range(2):
        warrant_id = uuid4()
        binding = PriceBinding(
            basis, warrant_id if basis is PriceBasis.WARRANT else underlying, "EUR"
        )
        items.append(
            MonitoringSubject(
                workspace_id=workspace,
                position_id=uuid4(),
                trade_id=uuid4(),
                listing_id=uuid4(),
                mapping_id=uuid4(),
                symbol="SYNTHETIC-STOCK",
                rules=(MonitoringRule("synthetic-rule", kind, Decimal("100"), binding),),
                warrant_id=warrant_id,
                underlying_id=underlying,
                warrant_isin=f"DE000SYN00{index}0",
                warrant_wkn=f"SYN00{index}",
                warrant_name=f"SYNTHETIC Call {index}",
                listing_currency="EUR",
            )
        )

    async def price_for_rule(*, rule, **kwargs):
        value = Decimal("99") if kind is MonitoringRuleType.STOP_REACHED else Decimal("121")
        return RulePriceResult(
            "AVAILABLE",
            "SYNTHETIC",
            PriceObservation(value, NOW, rule.price_binding, {"provider": "SYNTHETIC"}),
        )

    monkeypatch.setattr(cycle, "rule_price", price_for_rule)
    processor = PositionMonitoringService(
        states=StateRepo(), alerts=AlertRepo(), new_id=uuid4, now=lambda: NOW
    )
    service = cycle.PositionMonitoringCycleService(
        subjects=Subjects(tuple(MonitoringSubjectResolution(s.position_id, s) for s in items)),
        market_data=None,
        processor=SimpleNamespace(process=processor.evaluate),
        new_id=uuid4,
        now=lambda: NOW,
    )
    result = await service.run()
    assert result.alerts_created == 2
    for subject, created in zip(items, result.created_alerts, strict=True):
        assert created.alert.trade_id == subject.trade_id
        assert created.warrant_name == subject.warrant_name
        assert created.warrant_isin == subject.warrant_isin
        assert created.warrant_wkn == subject.warrant_wkn
        assert created.symbol == (
            subject.warrant_isin if basis is PriceBasis.WARRANT else subject.symbol
        )
    repeated = await service.run()
    assert repeated.alerts_created == 0 and repeated.alerts_deduplicated == 2


@pytest.mark.asyncio
async def test_runtime_persists_the_name_without_delivery_or_extra_lookup(monkeypatch):
    repo, session = Repo(), AsyncMock()

    @asynccontextmanager
    async def session_context():
        yield session

    monkeypatch.setattr(runtime, "SqlAlchemyNotificationRepository", lambda value: repo)
    service = runtime.PositionMonitoringRuntimeService(
        database=SimpleNamespace(session_context=session_context),
        market_data=None,
        delivery_adapter=None,
    )
    # A structural double also exercises the old runtime without requiring the new DTO fields.
    created = SimpleNamespace(
        alert=alert(),
        symbol="SYNTHETIC-STOCK",
        warrant_name=NAME,
        warrant_isin=ISIN,
        warrant_wkn=WKN,
    )
    await service._create_notification(created)
    assert len(repo.values) == 1
    assert f"Optionsschein: {NAME}" in repo.values[0].body
    assert f"WKN: {WKN} | ISIN: {ISIN}" in repo.values[0].body
    session.commit.assert_awaited_once()
    session.execute.assert_not_awaited()
