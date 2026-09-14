"""Real persistence of quarantine, immutable confirmation and product rule resolution."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import insert, select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from tests.integration.backend.database.test_market_data_instrument_workspace_postgres import (
    _test_database_url,
)

from app.features.alert.persistence.models import AlertModel
from app.features.position_monitoring.persistence.models import MonitoringRuleStateModel
from app.features.position_monitoring.service.legacy_alerts import invalidate_unbound_alerts
from app.features.position_monitoring.service.subjects import SqlAlchemyMonitoringSubjectReader
from app.features.trade_position.domain.price_binding import PriceBasis, PriceBinding
from app.features.trade_position.persistence.models import (
    PositionModel,
    TradeManagementEventModel,
    TradeModel,
)
from app.features.trade_position.persistence.unit_of_work import SqlAlchemyTradePositionUnitOfWork
from app.features.trade_position.service.application import TradePositionService
from app.features.trade_position.service.resolvers import ResolvedProduct


@pytest.mark.asyncio
async def test_confirmation_and_quarantine_preserve_history_and_do_not_require_stock_mapping():
    engine = create_async_engine(_test_database_url())
    now = datetime.now(UTC)
    workspace, underlying, issuer, warrant, trade, position, actor, old_event, old_alert, state = (
        uuid4() for _ in range(10)
    )
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            try:
                await connection.execute(
                    text(
                        "INSERT INTO workspaces(id,name,created_at) VALUES (:id,'Price bin"
                        "ding test',:now)"
                    ),
                    {"id": workspace, "now": now},
                )
                await connection.execute(
                    text(
                        "INSERT INTO issuers(id,legal_name,display_name,is_active,version,"
                        "created_at,updated_at) VALUES (:id,:name,:name,true,1,:now,:now)"
                    ),
                    {"id": issuer, "name": str(issuer), "now": now},
                )
                await connection.execute(
                    text(
                        "INSERT INTO underlyings(id,workspace_id,type,name,lifecycle_statu"
                        "s,quality_status,version,created_at,updated_at,data_origin) VALUE"
                        "S (:id,:workspace,'STOCK','UNH test','ACTIVE','VERIFIED',1,:now,:"
                        "now,'MANUAL')"
                    ),
                    {"id": underlying, "workspace": workspace, "now": now},
                )
                await connection.execute(
                    text(
                        "INSERT INTO warrants(id,workspace_id,issuer_id,underlying_id,prod"
                        "uct_family,display_name,isin,lifecycle_status,version,created_at,"
                        "updated_at) VALUES (:id,:workspace,:issuer,:underlying,'WARRANT',"
                        "'UNH test','DE000VH2LU21','ACTIVE',1,:now,:now)"
                    ),
                    {
                        "id": warrant,
                        "workspace": workspace,
                        "issuer": issuer,
                        "underlying": underlying,
                        "now": now,
                    },
                )
                await connection.execute(
                    insert(TradeModel).values(
                        id=trade,
                        workspace_id=workspace,
                        product_id=warrant,
                        origin="EXTERNAL",
                        created_at=now,
                        created_by=actor,
                    )
                )
                await connection.execute(
                    insert(PositionModel).values(
                        id=position,
                        trade_id=trade,
                        product_id=warrant,
                        open_quantity=2000,
                        cost_basis=1020,
                        average_entry_price=Decimal(".51"),
                        opened_at=now,
                        last_execution_at=now,
                        realized_gross_pnl=0,
                    )
                )
                await connection.execute(
                    insert(TradeManagementEventModel).values(
                        id=old_event,
                        trade_id=trade,
                        event_type="TARGET_CHANGED",
                        effective_at=now,
                        recorded_at=now,
                        recorded_by=actor,
                        numeric_value=Decimal("2.50"),
                    )
                )
                await connection.execute(
                    insert(AlertModel).values(
                        id=old_alert,
                        position_id=position,
                        trade_id=trade,
                        alert_type="TARGET_REACHED",
                        severity="INFO",
                        rule_key="CURRENT_TARGET",
                        reason="observed_value=337 >= threshold=2.50",
                        observed_value=337,
                        threshold_value=Decimal("2.50"),
                        market_data_observed_at=now,
                        detected_at=now,
                        status="OPEN",
                    )
                )
                await connection.execute(
                    insert(MonitoringRuleStateModel).values(
                        id=state,
                        position_id=position,
                        rule_key="CURRENT_TARGET",
                        triggered=True,
                        first_seen_at=now,
                        last_seen_at=now,
                        last_observed_value=337,
                        threshold_value=Decimal("2.50"),
                        active_alert_id=old_alert,
                    )
                )
                async with AsyncSession(
                    bind=connection,
                    expire_on_commit=False,
                    join_transaction_mode="create_savepoint",
                ) as session:
                    reader = SqlAlchemyMonitoringSubjectReader(session, for_rule_evaluation=True)
                    before = next(
                        r for r in await reader.list_resolutions() if r.position_id == position
                    )
                    assert before.subject.rules[0].price_binding is None
                    assert before.subject.mapping_id is None
                    assert await invalidate_unbound_alerts(session, now=now) == 1
                    assert await invalidate_unbound_alerts(session, now=now) == 0
                    alert = await session.get(AlertModel, old_alert)
                    assert alert.status == "INVALIDATED" and alert.resolved_at is None
                    assert alert.observed_value == 337 and alert.threshold_value == Decimal("2.50")
                    assert alert.reason == "observed_value=337 >= threshold=2.50"
                    assert alert.invalidation_reason == "LEGACY_RULE_PRICE_BASIS_UNCONFIRMED"
                    products = AsyncMock()
                    products.resolve.return_value = ResolvedProduct(workspace, warrant, underlying)
                    service = TradePositionService(
                        uow=SqlAlchemyTradePositionUnitOfWork(session),
                        workspace_selections=AsyncMock(),
                        products=products,
                    )
                    binding = PriceBinding(PriceBasis.WARRANT, warrant, "EUR")
                    await service.change_target(
                        workspace_id=workspace,
                        trade_id=trade,
                        target_price=Decimal("2.50"),
                        price_binding=binding,
                        effective_at=now,
                        actor=actor,
                    )
                    after = next(
                        r for r in await reader.list_resolutions() if r.position_id == position
                    )
                    assert after.subject.rules[0].price_binding == binding
                    assert after.subject.mapping_id is None
                    original = await session.get(TradeManagementEventModel, old_event)
                    assert original.price_binding is None and original.numeric_value == Decimal(
                        "2.50"
                    )
                    with pytest.raises(ValueError, match="does not match"):
                        await service.change_stop(
                            workspace_id=workspace,
                            trade_id=trade,
                            stop_price=Decimal(".16"),
                            price_binding=PriceBinding(PriceBasis.WARRANT, uuid4(), "EUR"),
                            effective_at=now,
                            actor=actor,
                        )
                    assert (
                        len(
                            (
                                await session.scalars(
                                    select(TradeManagementEventModel).where(
                                        TradeManagementEventModel.trade_id == trade
                                    )
                                )
                            ).all()
                        )
                        == 2
                    )
            finally:
                await transaction.rollback()
    finally:
        await engine.dispose()
