from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.features.trade_plan.persistence import repositories as repositories_module
from app.features.trade_plan.persistence.repositories import (
    SqlAlchemyTradePlanApprovalRepository,
    SqlAlchemyTradePlanEventRepository,
    SqlAlchemyTradePlanRepository,
    SqlAlchemyTradePlanVersionRepository,
)


def _session():
    session = Mock()
    session.scalar = AsyncMock()
    session.scalars = AsyncMock()
    session.flush = AsyncMock()
    session.add = Mock()
    session.add_all = Mock()
    return session


@pytest.mark.asyncio
async def test_version_add_flushes_parent_before_staging_targets(monkeypatch) -> None:
    session = _session()
    plans = Mock()
    repo = SqlAlchemyTradePlanVersionRepository(session, plans)
    version = object()
    version_model = object()
    target_models = (object(), object())
    calls: list[str] = []

    monkeypatch.setattr(
        repositories_module,
        "trade_plan_version_to_models",
        lambda _version: (version_model, target_models),
    )
    session.add.side_effect = lambda model: calls.append(
        "add-version" if model is version_model else "add-other"
    )
    session.add_all.side_effect = lambda models: calls.append(
        "add-targets" if tuple(models) == target_models else "add-all-other"
    )

    async def record_flush() -> None:
        calls.append("flush")

    session.flush.side_effect = record_flush

    await repo.add(version)  # type: ignore[arg-type]

    assert calls == ["add-version", "flush", "add-targets", "flush"]


@pytest.mark.asyncio
async def test_next_version_number_locks_plan_identity_before_counting() -> None:
    session = _session()
    plans = Mock()
    plans.lock = AsyncMock(return_value=True)
    repo = SqlAlchemyTradePlanVersionRepository(session, plans)
    workspace_id, plan_id = uuid4(), uuid4()
    session.scalar.return_value = 4

    assert await repo.next_version_number(workspace_id, plan_id) == 5
    plans.lock.assert_awaited_once_with(workspace_id, plan_id)


@pytest.mark.asyncio
async def test_next_version_number_rejects_unknown_plan() -> None:
    session = _session()
    plans = Mock()
    plans.lock = AsyncMock(return_value=False)
    repo = SqlAlchemyTradePlanVersionRepository(session, plans)

    with pytest.raises(LookupError, match="trade plan not found"):
        await repo.next_version_number(uuid4(), uuid4())
    session.scalar.assert_not_awaited()


@pytest.mark.asyncio
async def test_plan_event_and_approval_repository_query_helpers() -> None:
    session = _session()
    plan_repo = SqlAlchemyTradePlanRepository(session)
    event_repo = SqlAlchemyTradePlanEventRepository(session)
    approval_repo = SqlAlchemyTradePlanApprovalRepository(session)
    workspace_id, plan_id, underlying_id, version_id = (uuid4() for _ in range(4))

    session.scalar.return_value = None
    assert await plan_repo.get(workspace_id, plan_id) is None
    assert not await plan_repo.lock(workspace_id, plan_id)

    rows = Mock()
    rows.all.return_value = []
    session.scalars.return_value = rows
    assert await plan_repo.list_for_underlying(workspace_id, underlying_id) == ()
    assert await event_repo.list_for_version(version_id) == ()

    marker = object()
    session.scalar.return_value = marker
    assert await approval_repo.get_for_version(version_id) is marker
    await event_repo.add(marker)
    await approval_repo.add(marker)
    assert session.add.call_count == 2
