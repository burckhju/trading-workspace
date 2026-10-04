"""Serialization and immutable risk snapshots on the disposable PostgreSQL schema."""

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import insert, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from tests.integration.backend.database.test_market_data_instrument_workspace_postgres import (
    _test_database_url,
)
from tests.integration.backend.test_position_risk import ControlledInputs

from app.features.position_monitoring.domain.risk_signals import RiskParameters
from app.features.position_monitoring.service.risk import (
    PositionRiskService,
    RiskConfigurationConflict,
)
from app.features.trade_position.persistence.models import PositionModel, TradeModel
from app.features.trade_position.service.open_position_reader import OpenPositionReference


@pytest.mark.asyncio
async def test_parallel_evaluation_and_configuration_are_serialized_and_restart_deduplicates():
    engine = create_async_engine(_test_database_url())
    workspace, issuer, underlying, warrant, trade, position = (uuid4() for _ in range(6))
    now = datetime.now(UTC)
    ref = OpenPositionReference(workspace, trade, position, warrant)
    inputs = ControlledInputs(ref)
    try:
        async with engine.begin() as connection:
            statements = [
                (
                    "INSERT INTO workspaces(id,name,created_at) VALUES (:id,'Risk concurrency test',:now)",
                    {"id": workspace},
                ),
                (
                    "INSERT INTO issuers(id,legal_name,display_name,is_active,version,created_at,updated_at) VALUES (:id,:name,:name,true,1,:now,:now)",
                    {"id": issuer, "name": str(issuer)},
                ),
                (
                    "INSERT INTO underlyings(id,workspace_id,type,name,lifecycle_status,quality_status,version,created_at,updated_at,data_origin) VALUES (:id,:workspace,'STOCK','Synthetic risk','ACTIVE','VERIFIED',1,:now,:now,'MANUAL')",
                    {"id": underlying, "workspace": workspace},
                ),
                (
                    "INSERT INTO warrants(id,workspace_id,issuer_id,underlying_id,product_family,display_name,lifecycle_status,version,created_at,updated_at) VALUES (:id,:workspace,:issuer,:underlying,'WARRANT','Synthetic risk','ACTIVE',1,:now,:now)",
                    {
                        "id": warrant,
                        "workspace": workspace,
                        "issuer": issuer,
                        "underlying": underlying,
                    },
                ),
            ]
            for sql, values in statements:
                await connection.execute(text(sql), {**values, "now": now})
            await connection.execute(
                insert(TradeModel).values(
                    id=trade,
                    workspace_id=workspace,
                    product_id=warrant,
                    origin="EXTERNAL",
                    created_at=now,
                    created_by=uuid4(),
                )
            )
            await connection.execute(
                insert(PositionModel).values(
                    id=position,
                    trade_id=trade,
                    product_id=warrant,
                    open_quantity=10,
                    cost_basis=20,
                    average_entry_price=2,
                    opened_at=now,
                    last_execution_at=now,
                    realized_gross_pnl=0,
                )
            )

        async def evaluate():
            async with AsyncSession(engine, expire_on_commit=False, autoflush=False) as session:
                return await PositionRiskService(session, inputs).evaluate(
                    workspace_id=workspace, trade_id=trade, now=inputs.now()
                )

        a, b = await asyncio.gather(evaluate(), evaluate())
        assert a[0].snapshot_id == b[0].snapshot_id

        async def configure():
            async with AsyncSession(engine, expire_on_commit=False, autoflush=False) as session:
                return await PositionRiskService(session, inputs).configure(
                    workspace_id=workspace,
                    trade_id=trade,
                    now=inputs.now(),
                    parameters=RiskParameters(),
                    enabled=True,
                    expected_revision=0,
                    actor=uuid4(),
                    correlation_id="parallel-test",
                )

        configs = await asyncio.gather(configure(), configure(), return_exceptions=True)
        assert sum(isinstance(c, RiskConfigurationConflict) for c in configs) == 1
        assert sum(getattr(c, "revision", None) == 1 for c in configs) == 1
        restarted, alerts = await evaluate()
        assert (
            restarted.configuration.revision == 1
            and restarted.assessment.transition == "INITIALIZED"
        )
        assert not alerts
        async with engine.connect() as connection:
            count = await connection.scalar(
                text("SELECT count(*) FROM position_risk_snapshots WHERE position_id=:position"),
                {"position": position},
            )
            assert count == 2
    finally:
        async with engine.begin() as connection:
            for table in (
                "monitoring_rule_states",
                "alerts",
                "position_risk_snapshots",
                "position_risk_configurations",
            ):
                await connection.execute(
                    text(f"DELETE FROM {table} WHERE position_id=:id"), {"id": position}
                )
            for table, value in [
                ("positions", position),
                ("trades", trade),
                ("warrants", warrant),
                ("underlyings", underlying),
                ("issuers", issuer),
                ("workspaces", workspace),
            ]:
                await connection.execute(text(f"DELETE FROM {table} WHERE id=:id"), {"id": value})
        await engine.dispose()
