from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest

from app.features.trade_plan.api.overview_router import list_trade_plans


def session_with_rows(rows):
    result = Mock()
    result.all.return_value = rows
    trades = Mock()
    trades.all.return_value = []
    return Mock(execute=AsyncMock(side_effect=[result, trades]))


@pytest.mark.asyncio
async def test_list_trade_plans_returns_latest_workspace_rows() -> None:
    plan_id = UUID("11111111-1111-4111-8111-111111111111")
    underlying_id = UUID("22222222-2222-4222-8222-222222222222")
    version_id = UUID("33333333-3333-4333-8333-333333333333")
    created_at = datetime(2026, 9, 5, 6, 0, tzinfo=UTC)
    plan = SimpleNamespace(
        id=plan_id, underlying_id=underlying_id, origin_type="MANUAL", created_at=created_at
    )
    version = SimpleNamespace(id=version_id, version=2, status="READY_FOR_REVIEW")
    session = session_with_rows(
        [
            (
                plan,
                version,
                SimpleNamespace(name="DAX", isin="DE0008469008", wkn="846900"),
                None,
                None,
                None,
                None,
            )
        ]
    )
    items = await list_trade_plans(session=session)
    assert len(items) == 1
    assert items[0].id == plan_id
    assert items[0].underlying_id == underlying_id
    assert items[0].latest_version_id == version_id
    assert items[0].latest_version == 2
    assert items[0].status.value == "READY_FOR_REVIEW"
    assert items[0].execution.status == "NOT_STARTED"
    assert items[0].model_dump(mode="json")["execution"]["trades"] == []
    assert session.execute.await_count == 2


@pytest.mark.asyncio
async def test_overview_displays_exact_selected_product_and_current_underlying() -> None:
    plan = SimpleNamespace(
        id=UUID(int=1),
        underlying_id=UUID(int=2),
        origin_type="MANUAL",
        created_at=datetime.now(UTC),
    )
    version = SimpleNamespace(id=UUID(int=3), version=1, status="APPROVED")
    product = SimpleNamespace(display_name="DAX Call", isin="DE000TEST1234", wkn="TEST12")
    session = session_with_rows(
        [(plan, version, None, UUID(int=4), UUID(int=5), UUID(int=6), product)]
    )
    (item,) = await list_trade_plans(session=session)
    assert item.underlying_name is None
    assert item.selected_product.display_name == "DAX Call"
    assert item.selected_product.warrant_id == UUID(int=6)
    assert item.selected_product.run_id == UUID(int=4)
    assert item.execution.status == "NOT_STARTED"
    statement = str(session.execute.await_args_list[0].args[0])
    assert "row_number() OVER" in statement
    assert "product_selections.selected_at DESC" in statement
    assert "trade_plan_versions.id" in statement
    assert session.execute.await_count == 2


@pytest.mark.asyncio
async def test_overview_never_invents_a_missing_selected_product_name() -> None:
    plan = SimpleNamespace(
        id=UUID(int=1),
        underlying_id=UUID(int=2),
        origin_type="MANUAL",
        created_at=datetime.now(UTC),
    )
    version = SimpleNamespace(id=UUID(int=3), version=1, status="APPROVED")
    session = session_with_rows(
        [(plan, version, None, UUID(int=4), UUID(int=5), UUID(int=6), None)]
    )
    (item,) = await list_trade_plans(session=session)
    assert item.selected_product is not None
    assert item.selected_product.display_name is None
    assert item.selected_product.warrant_id == UUID(int=6)
