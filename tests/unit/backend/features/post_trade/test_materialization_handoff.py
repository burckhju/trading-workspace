"""Ordering and owner-delegation checks; PostgreSQL tests prove actual locks."""

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.features.post_trade.application.handoff_service import Ft012Handoff
from app.features.post_trade.application.materialization_handoff import (
    Ft011SourceBusyError,
    InspectedFt012HandoffService,
)
from app.features.post_trade.domain import ExitReviewCurrentness


@pytest.mark.parametrize("guarded", [True, False])
@pytest.mark.parametrize(
    "currentness", [ExitReviewCurrentness.CURRENT, ExitReviewCurrentness.STALE, None]
)
async def test_handoff_inspects_exact_source_after_optional_guard(guarded, currentness):
    ws, trade = uuid4(), uuid4()
    value = Ft012Handoff(True, "READY", uuid4(), uuid4(), uuid4())
    order = []

    async def acquire(**kwargs):
        assert kwargs == {"workspace_id": ws, "trade_id": trade}
        order.append("guard")

    async def read(**kwargs):
        assert kwargs == {"workspace_id": ws, "trade_id": trade}
        order.append("gate")
        return value

    async def inspect(**kwargs):
        assert kwargs == {"workspace_id": ws, "version_id": value.exit_review_version_id}
        order.append("inspect")
        return currentness

    service = InspectedFt012HandoffService(
        handoff=SimpleNamespace(get=read),
        inspector=SimpleNamespace(inspect_version_currentness=inspect),
        guard=SimpleNamespace(acquire=acquire) if guarded else None,
    )
    result = await service.get(workspace_id=ws, trade_id=trade)
    assert order == (["guard"] if guarded else []) + ["gate", "inspect"]
    assert result.ready == (currentness is ExitReviewCurrentness.CURRENT)
    assert result.exit_review_version_id == value.exit_review_version_id
    assert result.reason == (
        "READY"
        if result.ready
        else "EXIT_REVIEW_STALE" if currentness else "EXIT_REVIEW_SOURCE_UNKNOWN"
    )
    assert value.ready  # No mutation to an existing handoff or review.


async def test_incomplete_gate_does_not_inspect_or_complete_observation():
    value = Ft012Handoff(False, "POST_TRADE_OBSERVATION_INCOMPLETE", uuid4(), None, None)
    inspector = SimpleNamespace(inspect_version_currentness=AsyncMock())
    service = InspectedFt012HandoffService(
        handoff=SimpleNamespace(get=AsyncMock(return_value=value)), inspector=inspector
    )
    assert await service.get(workspace_id=uuid4(), trade_id=uuid4()) is value
    inspector.inspect_version_currentness.assert_not_awaited()


async def test_busy_guard_never_reads_an_unprotected_handoff():
    handoff = SimpleNamespace(get=AsyncMock())
    service = InspectedFt012HandoffService(
        handoff=handoff,
        inspector=SimpleNamespace(inspect_version_currentness=AsyncMock()),
        guard=SimpleNamespace(acquire=AsyncMock(side_effect=Ft011SourceBusyError())),
    )
    with pytest.raises(Ft011SourceBusyError):
        await service.get(workspace_id=uuid4(), trade_id=uuid4())
    handoff.get.assert_not_awaited()
