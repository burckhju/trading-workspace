from datetime import UTC, date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest
from sqlalchemy.dialects import postgresql

from app.features.trade_plan.service.execution_overview import read_execution_overviews

PLAN = UUID(int=1)
VERSION = UUID(int=2)
WORKSPACE = UUID(int=3)
DAY = date(2026, 8, 17)
TIME = datetime(2026, 8, 17, 10, tzinfo=UTC)


def row(*, quantity=10, closed=False, cancelled=False, bought=True, version=VERSION, number=1):
    trade = SimpleNamespace(
        id=UUID(int=10),
        trade_plan_id=PLAN,
        trade_plan_version_id=version,
        product_id=UUID(int=4),
        cancelled_at=TIME if cancelled else None,
    )
    position = SimpleNamespace(
        open_quantity=quantity,
        closed_at=TIME if closed else None,
        opened_at=TIME,
        opened_on=DAY,
        closed_on=DAY if closed else None,
    )
    return (trade, position, number, "Purchased Call", "DE000TEST1234", "TEST12", bought)


def session_for(rows):
    result = Mock()
    result.all.return_value = rows
    return Mock(execute=AsyncMock(return_value=result))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("rows", "status"),
    [
        ([], "NOT_STARTED"),
        ([row()], "OPEN"),
        ([row(quantity=5)], "OPEN"),
        ([row(quantity=0, closed=True)], "CLOSED"),
        ([row(cancelled=True)], "CANCELLED"),
        ([row(bought=False)], "UNKNOWN"),
        ([row(number=None)], "UNKNOWN"),
        ([row(quantity=0)], "UNKNOWN"),
        ([row(closed=True)], "UNKNOWN"),
    ],
)
async def test_purchase_status_is_not_plan_approval(rows, status):
    session = session_for(rows)
    overview = (
        await read_execution_overviews(
            session, workspace_id=WORKSPACE, current_versions={PLAN: VERSION}
        )
    )[PLAN]
    assert overview.status == status
    assert overview.current_version_status == status
    if rows:
        assert overview.trades[0].product_name == "Purchased Call"
        assert overview.trades[0].purchased_on == (DAY if rows[0][-1] else None)
    statement = session.execute.await_args.args[0].compile(
        dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
    )
    sql = str(statement)
    assert str(WORKSPACE) in sql
    assert "WORKSPACE_SELECTION" in sql
    assert "trades.trade_plan_id IN" in sql
    assert "execution_records.side = 'BUY'" in sql
    assert "supersedes_execution_id = execution_records.id" in sql
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_previous_version_purchase_and_cancelled_duplicate_are_not_hidden():
    rows = [row(version=UUID(int=9)), row(cancelled=True)]
    overview = (
        await read_execution_overviews(
            session_for(rows), workspace_id=WORKSPACE, current_versions={PLAN: VERSION}
        )
    )[PLAN]
    assert overview.status == "OPEN"
    assert overview.current_version_status == "CANCELLED"
    assert len(overview.trades) == 2
    assert overview.trades[0].trade_plan_version_id == UUID(int=9)


@pytest.mark.asyncio
async def test_new_version_is_unbought_but_plan_remains_closed():
    overview = (
        await read_execution_overviews(
            session_for([row(quantity=0, closed=True)]),
            workspace_id=WORKSPACE,
            current_versions={PLAN: UUID(int=8)},
        )
    )[PLAN]
    assert overview.status == "CLOSED"
    assert overview.current_version_status == "NOT_STARTED"


@pytest.mark.asyncio
async def test_missing_projection_is_unknown_and_not_an_unstarted_plan():
    record = list(row())
    record[1] = None
    overview = (
        await read_execution_overviews(
            session_for([tuple(record)]), workspace_id=WORKSPACE, current_versions={PLAN: VERSION}
        )
    )[PLAN]
    assert overview.status == "UNKNOWN"
    assert overview.trades[0].open_quantity is None
    assert overview.trades[0].purchased_at is None


@pytest.mark.asyncio
async def test_empty_overview_needs_no_trade_query():
    session = Mock(execute=AsyncMock())
    assert (
        await read_execution_overviews(session, workspace_id=WORKSPACE, current_versions={}) == {}
    )
    session.execute.assert_not_awaited()
