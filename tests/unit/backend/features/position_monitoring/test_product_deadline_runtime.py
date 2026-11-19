"""Scope gating and pre-dispatch owner recheck without a database or external calls."""

from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from tests.unit.backend.features.position_monitoring import test_hebeltrader_deadlines as facts
from tests.unit.backend.features.position_monitoring.test_product_deadline_review_contract import (
    NOW,
    decision,
    inputs,
)

from app.features.position_monitoring.service import product_deadline_review_delivery as delivery
from app.features.position_monitoring.service import product_deadline_review_runtime as runtime
from app.features.position_monitoring.service.product_deadline_review import (
    product_deadline_context,
)


@pytest.mark.parametrize(
    "scope", ["DISABLED", "INDICATIVE_ENTRY_V1", "HEBELTRADER_CONFIRMED_BASELINE"]
)
async def test_only_explicit_v2_scope_runs_deadline_sweep(scope):
    database = SimpleNamespace(
        session_context=Mock(side_effect=AssertionError("No work authorized"))
    )
    assert (
        await runtime.ProductDeadlineReviewRuntime(database, scope=scope).run()
        == runtime.ProductDeadlineRunResult()
    )
    database.session_context.assert_not_called()


@pytest.mark.parametrize(
    ("change", "kind", "expected"),
    [
        ("same", "DEADLINE_REVIEW", None),
        ("gap", "DEADLINE_REVIEW", "REVIEW_DEADLINE_INPUTS_UNAVAILABLE"),
        ("closed", "DEADLINE_REVIEW", "REVIEW_POSITION_CLOSED"),
        ("later_stage", "DEADLINE_REVIEW", "REVIEW_ALERT_RESOLVED"),
        ("gap", "DATA_UNAVAILABLE", None),
        ("same", "DATA_UNAVAILABLE", "REVIEW_ALERT_RESOLVED"),
    ],
)
async def test_delivery_rechecks_current_owner_premises_without_mutating_or_backfilling(
    monkeypatch,
    change,
    kind,
    expected,
):
    value = inputs()
    context = product_deadline_context(value, decision(value), kind, uuid4(), uuid4(), NOW)
    latest = {
        "same": value,
        "gap": replace(value, problems=("PRODUCT_LISTING_TERMS_WITHDRAWN",)),
        "closed": replace(value, closed=True),
        "later_stage": inputs(now=datetime(2026, 10, 12, 22, tzinfo=facts.ZONE)),
    }[change]
    engine = create_async_engine("postgresql+asyncpg://unused.invalid/synthetic_unused")
    session = SimpleNamespace(bind=engine, commit=AsyncMock(), flush=AsyncMock(), add=Mock())
    snapshot = object()

    @asynccontextmanager
    async def owner_snapshot(actual):
        assert actual is engine
        yield snapshot

    reader = AsyncMock(return_value=latest)
    monkeypatch.setattr(delivery, "_owner_snapshot", owner_snapshot)
    monkeypatch.setattr(delivery, "read_product_deadline_inputs", reader)
    try:
        result = await delivery.deadline_review_delivery_problem(
            session,
            workspace_id=value.workspace_id,
            trade_id=value.trade_id,
            position_id=value.position_id,
            price_context=context,
            known_at=NOW,
        )
        assert result == expected
        reader.assert_awaited_once()
        assert reader.call_args.args == (snapshot,)
        session.commit.assert_not_awaited()
        session.flush.assert_not_awaited()
        session.add.assert_not_called()
    finally:
        await engine.dispose()


async def test_unrelated_notifications_do_not_acquire_a_deadline_owner_snapshot():
    result = await delivery.deadline_review_delivery_problem(
        object(),
        workspace_id=facts.WORKSPACE,
        trade_id=uuid4(),
        position_id=uuid4(),
        price_context={"scope": "INDICATIVE_ENTRY_V1"},
        known_at=NOW,
    )
    assert result is None


async def test_background_sweep_preserves_closed_subjects_for_cleanup_and_separate_counters(
    monkeypatch,
):
    live = SimpleNamespace(workspace_id=facts.WORKSPACE, trade_id=uuid4(), position_id=uuid4())
    sold = SimpleNamespace(workspace_id=facts.WORKSPACE, trade_id=uuid4(), position_id=uuid4())
    session = SimpleNamespace(execute=AsyncMock(return_value=SimpleNamespace(all=lambda: [sold])))

    class Database:
        @asynccontextmanager
        async def session_context(self):
            yield session

    evaluate = AsyncMock(
        return_value=SimpleNamespace(
            alerts_created=0,
            notifications_created=0,
            data_problem_active=False,
        )
    )
    monkeypatch.setattr(runtime.OpenPositionReader, "list_open", AsyncMock(return_value=[live]))
    monkeypatch.setattr(runtime.ProductDeadlineReviewService, "evaluate", evaluate)
    result = await runtime.ProductDeadlineReviewRuntime(
        Database(), scope="INDICATIVE_ENTRY_V2"
    ).run()
    assert result.positions_evaluated == 2 and result.position_errors == 0
    assert result.alerts_created == result.notifications_created == 0
    assert {call.kwargs["position_id"] for call in evaluate.await_args_list} == {
        live.position_id,
        sold.position_id,
    }
    assert all(call.kwargs["notifications_enabled"] is False for call in evaluate.await_args_list)
