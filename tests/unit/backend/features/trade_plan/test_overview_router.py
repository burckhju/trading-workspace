from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest

from app.features.trade_plan.api.overview_router import list_trade_plans


@pytest.mark.asyncio
async def test_list_trade_plans_returns_latest_workspace_rows() -> None:
    plan_id = UUID("11111111-1111-4111-8111-111111111111")
    underlying_id = UUID("22222222-2222-4222-8222-222222222222")
    version_id = UUID("33333333-3333-4333-8333-333333333333")
    created_at = datetime(2026, 9, 5, 6, 0, tzinfo=UTC)
    plan = SimpleNamespace(
        id=plan_id,
        underlying_id=underlying_id,
        origin_type="MANUAL",
        created_at=created_at,
    )
    version = SimpleNamespace(
        id=version_id,
        version=2,
        status="READY_FOR_REVIEW",
    )
    result = Mock()
    result.all.return_value = [(plan, version)]
    session = Mock()
    session.execute = AsyncMock(return_value=result)

    items = await list_trade_plans(session=session)

    assert len(items) == 1
    assert items[0].id == plan_id
    assert items[0].underlying_id == underlying_id
    assert items[0].latest_version_id == version_id
    assert items[0].latest_version == 2
    assert items[0].status.value == "READY_FOR_REVIEW"
    session.execute.assert_awaited_once()
