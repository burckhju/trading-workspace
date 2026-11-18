"""No network: the review sweep enumerates all owner positions and durable episodes."""

from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest

from app.features.position_monitoring.service import indicative_entry_runtime as module


@pytest.mark.asyncio
@pytest.mark.parametrize("scope", ["INDICATIVE_ENTRY_V1", "INDICATIVE_ENTRY_V2"])
@pytest.mark.parametrize("preparation_fails", [False, True])
async def test_repeated_sweep_prepares_only_v2_without_manual_input_or_skipping_evaluation(
    monkeypatch, scope, preparation_fails
):
    position = SimpleNamespace(
        workspace_id=UUID(int=1), trade_id=UUID(int=2), position_id=UUID(int=3)
    )
    session = SimpleNamespace(execute=AsyncMock(return_value=SimpleNamespace(all=lambda: [])))

    @asynccontextmanager
    async def context():
        yield session

    monkeypatch.setattr(
        module,
        "OpenPositionReader",
        Mock(return_value=SimpleNamespace(list_open=AsyncMock(return_value=[position]))),
    )
    evaluate = AsyncMock(
        return_value=SimpleNamespace(
            alerts_created=0, notifications_created=0, data_problem_active=False
        )
    )
    service = Mock(return_value=SimpleNamespace(evaluate=evaluate))
    monkeypatch.setattr(module, "IndicativeEntryService", service)
    readiness = SimpleNamespace(
        prepare_for_review=AsyncMock(
            side_effect=(
                RuntimeError("Intercepted synthetic preparation failure")
                if preparation_fails
                else None
            )
        )
    )
    runtime = module.IndicativeEntryRuntime(
        SimpleNamespace(session_context=context), scope=scope, readiness=readiness
    )
    for _ in range(2):
        assert (await runtime.run()).positions_evaluated == 1
    assert evaluate.await_count == 2
    assert readiness.prepare_for_review.await_count == (2 if scope.endswith("V2") else 0)
    assert service.call_args.kwargs["policy"].scope == scope


@pytest.mark.asyncio
async def test_default_disabled_does_not_read_refresh_or_evaluate():
    database, products = Mock(), Mock()
    result = await module.IndicativeEntryRuntime(database, products=products).run()
    assert result == module.IndicativeRunResult()
    assert database.mock_calls == products.mock_calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["exception", "retained", "empty"])
async def test_sweep_includes_positions_without_price_rules_and_closed_pending_episode(
    monkeypatch,
    failure,
):
    opened = SimpleNamespace(
        workspace_id=UUID(int=1), trade_id=UUID(int=2), position_id=UUID(int=3)
    )
    closed = SimpleNamespace(
        workspace_id=UUID(int=1), trade_id=UUID(int=4), position_id=UUID(int=5)
    )
    session = SimpleNamespace(
        execute=AsyncMock(return_value=SimpleNamespace(all=lambda: [opened, closed]))
    )

    @asynccontextmanager
    async def context():
        yield session

    database = SimpleNamespace(session_context=context)
    monkeypatch.setattr(
        module,
        "OpenPositionReader",
        Mock(return_value=SimpleNamespace(list_open=AsyncMock(return_value=[opened]))),
    )
    evaluate = AsyncMock(
        return_value=SimpleNamespace(
            alerts_created=0, notifications_created=0, data_problem_active=True
        )
    )
    monkeypatch.setattr(
        module,
        "IndicativeEntryService",
        Mock(return_value=SimpleNamespace(evaluate=evaluate)),
    )
    products = SimpleNamespace(
        for_trade=AsyncMock(
            side_effect=(
                RuntimeError("intercepted synthetic transport") if failure == "exception" else None
            ),
            return_value=(
                SimpleNamespace(quote_refresh_error="SYNTHETIC_RETAINED")
                if failure == "retained"
                else None
            ),
        )
    )
    result = await module.IndicativeEntryRuntime(
        database,
        scope="INDICATIVE_ENTRY_V1",
        products=products,
        notifications_enabled=False,
    ).run()
    assert result.positions_evaluated == 2 and result.data_problems == 2
    products.for_trade.assert_awaited_once_with(opened.trade_id)
    assert evaluate.await_args_list[0].kwargs["refresh_failed"] is True
    assert evaluate.await_args_list[1].kwargs["refresh_failed"] is False
    assert evaluate.await_args_list[1].kwargs["position_id"] == closed.position_id


@pytest.mark.asyncio
async def test_single_position_failure_does_not_skip_other_positions(monkeypatch):
    positions = [
        SimpleNamespace(
            workspace_id=UUID(int=1), trade_id=UUID(int=i), position_id=UUID(int=i + 10)
        )
        for i in (2, 3)
    ]
    session = SimpleNamespace(execute=AsyncMock(return_value=SimpleNamespace(all=lambda: [])))

    @asynccontextmanager
    async def context():
        yield session

    monkeypatch.setattr(
        module,
        "OpenPositionReader",
        Mock(return_value=SimpleNamespace(list_open=AsyncMock(return_value=positions))),
    )
    evaluate = AsyncMock(
        side_effect=[
            ValueError("synthetic inconsistent owner"),
            SimpleNamespace(alerts_created=2, notifications_created=0, data_problem_active=False),
        ]
    )
    monkeypatch.setattr(
        module,
        "IndicativeEntryService",
        Mock(return_value=SimpleNamespace(evaluate=evaluate)),
    )
    result = await module.IndicativeEntryRuntime(
        SimpleNamespace(session_context=context), scope="INDICATIVE_ENTRY_V1"
    ).run()
    assert result == module.IndicativeRunResult(1, 2, 0, 0, 1)
