"""PostgreSQL qualification for explicit user-owned TradePlan deletion."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.features.trade_plan.service.hard_delete import TradePlanHardDeleteService


def _test_database_url() -> str:
    url = os.environ.get("TRADING_WORKSPACE_TEST_DATABASE_URL", "")
    if not url:
        pytest.skip("TRADING_WORKSPACE_TEST_DATABASE_URL is not configured")
    if url.split("?", 1)[0].rsplit("/", 1)[-1] != "trading_workspace_test":
        pytest.fail("TradePlan hard-delete test may run only against trading_workspace_test")
    return url


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["DRAFT", "APPROVED"])
async def test_hard_delete_removes_plan_history_but_preserves_shared_underlying(
    status: str,
) -> None:
    engine = create_async_engine(_test_database_url())
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    workspace_id = uuid4()
    underlying_id = uuid4()
    trade_plan_id = uuid4()
    version_id = uuid4()
    now = datetime.now(UTC)

    async with engine.begin() as connection:
        await connection.execute(
            text("INSERT INTO workspaces (id, name, created_at) VALUES (:id, :name, :now)"),
            {"id": workspace_id, "name": f"Hard delete {status}", "now": now},
        )
        await connection.execute(
            text(
                "INSERT INTO underlyings "
                "(id, workspace_id, type, name, isin, wkn, lifecycle_status, quality_status, "
                "version, created_at, updated_at, data_origin) VALUES "
                "(:id, :workspace_id, 'STOCK', :name, NULL, NULL, 'ACTIVE', 'VERIFIED', "
                "1, :now, :now, 'MANUAL')"
            ),
            {"id": underlying_id, "workspace_id": workspace_id, "name": "Delete Test", "now": now},
        )
        await connection.execute(
            text(
                "INSERT INTO trade_plans "
                "(id, workspace_id, underlying_id, origin_type, candidate_id, "
                "candidate_evaluation_id, created_at, created_by) VALUES "
                "(:id, :workspace_id, :underlying_id, 'MANUAL', NULL, NULL, :now, 'test')"
            ),
            {
                "id": trade_plan_id,
                "workspace_id": workspace_id,
                "underlying_id": underlying_id,
                "now": now,
            },
        )
        await connection.execute(
            text(
                "INSERT INTO trade_plan_versions "
                "(id, trade_plan_id, version, direction, thesis, entry_type, entry_currency, "
                "entry_price, risk_thesis, status, created_at, created_by) VALUES "
                "(:id, :trade_plan_id, 1, 'LONG', 'Delete qualification', 'PRICE', 'EUR', "
                "100, 'Qualification risk', :status, :now, 'test')"
            ),
            {
                "id": version_id,
                "trade_plan_id": trade_plan_id,
                "status": status,
                "now": now,
            },
        )
        await connection.execute(
            text(
                "INSERT INTO trade_plan_targets "
                "(id, trade_plan_version_id, sequence, price, rationale) "
                "VALUES (:id, :version_id, 1, 110, NULL)"
            ),
            {"id": uuid4(), "version_id": version_id},
        )
        await connection.execute(
            text(
                "INSERT INTO trade_plan_events "
                "(id, trade_plan_id, trade_plan_version_id, event_type, from_status, to_status, "
                "reason, actor, correlation_id, occurred_at) VALUES "
                "(:id, :trade_plan_id, :version_id, 'CREATED', NULL, :status, NULL, "
                "'test', NULL, :now)"
            ),
            {
                "id": uuid4(),
                "trade_plan_id": trade_plan_id,
                "version_id": version_id,
                "status": status,
                "now": now,
            },
        )
        if status == "APPROVED":
            await connection.execute(
                text(
                    "INSERT INTO trade_plan_approvals "
                    "(id, trade_plan_id, trade_plan_version_id, version, actor, approved_at, "
                    "correlation_id) VALUES "
                    "(:id, :trade_plan_id, :version_id, 1, 'test', :now, NULL)"
                ),
                {
                    "id": uuid4(),
                    "trade_plan_id": trade_plan_id,
                    "version_id": version_id,
                    "now": now,
                },
            )

    async with session_factory() as session:
        summary = await TradePlanHardDeleteService(session).delete(
            workspace_id=workspace_id,
            trade_plan_id=trade_plan_id,
        )

    assert summary.trade_plan_versions == 1
    assert summary.trades == 0

    async with engine.begin() as connection:
        remaining_plan = await connection.scalar(
            text("SELECT count(*) FROM trade_plans WHERE id = :id"), {"id": trade_plan_id}
        )
        remaining_underlying = await connection.scalar(
            text("SELECT count(*) FROM underlyings WHERE id = :id"), {"id": underlying_id}
        )
        assert remaining_plan == 0
        assert remaining_underlying == 1
        await connection.execute(
            text("DELETE FROM underlyings WHERE id = :id"), {"id": underlying_id}
        )
        await connection.execute(
            text("DELETE FROM workspaces WHERE id = :id"), {"id": workspace_id}
        )

    await engine.dispose()
