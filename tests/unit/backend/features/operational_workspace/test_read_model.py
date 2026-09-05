"""Focused tests for the ephemeral operational workspace projection."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.candidate.service.live_workflow import CandidateLiveWorkflow, WorkflowStep
from app.features.candidate.service.runtime_readiness import (
    RuntimeAwareCandidateLiveWorkflowService,
)
from app.features.operational_workspace.service.read_model import (
    OperationalAction,
    OperationalWorkspaceReadModel,
)


class _Rows:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def all(self) -> list[Any]:
        return self._rows


def _action(*, priority: str, occurred_at: datetime | None, suffix: str) -> OperationalAction:
    resource_id = uuid4()
    return OperationalAction(
        id=f"action:{suffix}",
        source_feature="test",
        action_type="TEST",
        priority=priority,
        state="ACTIONABLE",
        title="Test",
        detail="Test",
        resource_type="test",
        resource_id=resource_id,
        next_action="Test",
        target="/test",
        occurred_at=occurred_at,
    )


@pytest.mark.asyncio
async def test_candidate_projection_uses_authoritative_live_workflow() -> None:
    workspace_id = uuid4()
    now = datetime.now(UTC)
    ready_id = uuid4()
    blocked_id = uuid4()
    candidates = [
        SimpleNamespace(id=ready_id, created_at=now),
        SimpleNamespace(id=blocked_id, created_at=now + timedelta(seconds=1)),
    ]

    session = AsyncMock(spec=AsyncSession)
    session.scalars.return_value = _Rows(candidates)
    workflow = SimpleNamespace(
        inspect=AsyncMock(
            side_effect=[
                CandidateLiveWorkflow(
                    candidate_id=ready_id,
                    underlying_id=uuid4(),
                    as_of=now,
                    ready=True,
                    can_evaluate=True,
                    next_action=None,
                    steps=(),
                ),
                CandidateLiveWorkflow(
                    candidate_id=blocked_id,
                    underlying_id=uuid4(),
                    as_of=now,
                    ready=False,
                    can_evaluate=False,
                    next_action="ASSIGN_SECTOR",
                    steps=(
                        WorkflowStep(
                            code="SECTOR_ASSIGNMENT",
                            label="Sector assignment",
                            status="BLOCKED",
                            detail="No active sector assignment.",
                            action="ASSIGN_SECTOR",
                        ),
                    ),
                ),
            ]
        )
    )
    model = OperationalWorkspaceReadModel(
        cast(AsyncSession, session),
        cast(RuntimeAwareCandidateLiveWorkflowService, workflow),
    )

    actions = await model._candidate_actions(workspace_id)

    assert [action.priority for action in actions] == ["ACTION", "BLOCKED"]
    assert actions[0].id == f"candidate:{ready_id}:evaluation-ready"
    assert actions[1].next_action == "ASSIGN_SECTOR"
    assert all(action.target == "/candidates" for action in actions)
    assert workflow.inspect.await_count == 2


@pytest.mark.asyncio
async def test_open_alert_projection_uses_existing_alert_state() -> None:
    workspace_id = uuid4()
    now = datetime.now(UTC)
    stop_alert = SimpleNamespace(
        id=uuid4(),
        trade_id=uuid4(),
        alert_type="STOP_REACHED",
        reason="Effective stop reached.",
        detected_at=now,
    )
    target_alert = SimpleNamespace(
        id=uuid4(),
        trade_id=uuid4(),
        alert_type="TARGET_REACHED",
        reason="Target 1 reached.",
        detected_at=now + timedelta(seconds=1),
    )
    session = AsyncMock(spec=AsyncSession)
    session.scalars.return_value = _Rows([stop_alert, target_alert])
    model = OperationalWorkspaceReadModel(cast(AsyncSession, session))

    actions = await model._alert_actions(workspace_id)

    assert [action.title for action in actions] == ["Stop erreicht", "Target erreicht"]
    assert [action.id for action in actions] == [
        f"alert:{stop_alert.id}:open",
        f"alert:{target_alert.id}:open",
    ]
    assert [action.detail for action in actions] == [stop_alert.reason, target_alert.reason]
    assert all(action.action_type == "POSITION_ALERT" for action in actions)
    assert all(action.priority == "ACTION" for action in actions)
    assert actions[0].target == f"/trade-management?trade_id={stop_alert.trade_id}"
    assert actions[1].target == f"/trade-management?trade_id={target_alert.trade_id}"
    assert [action.occurred_at for action in actions] == [
        stop_alert.detected_at,
        target_alert.detected_at,
    ]


@pytest.mark.asyncio
async def test_terminal_notification_failure_projection_links_to_trade_management() -> None:
    workspace_id = uuid4()
    notification_id = uuid4()
    trade_id = uuid4()
    created_at = datetime.now(UTC)
    session = AsyncMock(spec=AsyncSession)
    session.execute.return_value = _Rows([(notification_id, "TELEGRAM", created_at, trade_id)])
    model = OperationalWorkspaceReadModel(cast(AsyncSession, session))

    actions = await model._notification_failure_actions(workspace_id)

    assert len(actions) == 1
    action = actions[0]
    assert action.id == f"notification:{notification_id}:failed"
    assert action.action_type == "NOTIFICATION_DELIVERY_FAILURE"
    assert action.priority == "ACTION"
    assert action.title == "Benachrichtigung fehlgeschlagen"
    assert "TELEGRAM" in action.detail
    assert action.target == f"/trade-management?trade_id={trade_id}"
    assert action.occurred_at == created_at


@pytest.mark.asyncio
async def test_open_position_projection_only_links_to_trade_management() -> None:
    workspace_id = uuid4()
    trade_id = uuid4()
    opened_at = datetime.now(UTC)
    session = AsyncMock(spec=AsyncSession)
    session.execute.return_value = _Rows([(trade_id, opened_at)])
    model = OperationalWorkspaceReadModel(cast(AsyncSession, session))

    actions = await model._open_position_actions(workspace_id)

    assert len(actions) == 1
    action = actions[0]
    assert action.action_type == "OPEN_POSITION_MANAGEMENT"
    assert action.target == f"/trade-management?trade_id={trade_id}"
    assert action.occurred_at == opened_at


@pytest.mark.asyncio
async def test_post_trade_projection_follows_existing_review_lifecycle() -> None:
    workspace_id = uuid4()
    now = datetime.now(UTC)
    trades = [uuid4() for _ in range(6)]
    session = AsyncMock(spec=AsyncSession)
    session.execute.return_value = _Rows([(trade_id, now) for trade_id in trades])

    completed_a = SimpleNamespace(id=uuid4(), status="COMPLETED", completed_at=now)
    completed_b = SimpleNamespace(id=uuid4(), status="COMPLETED", completed_at=now)
    completed_c = SimpleNamespace(id=uuid4(), status="COMPLETED", completed_at=now)
    completed_d = SimpleNamespace(id=uuid4(), status="COMPLETED", completed_at=now)
    review_b = SimpleNamespace(id=uuid4())
    review_c = SimpleNamespace(id=uuid4())
    review_d = SimpleNamespace(id=uuid4())
    session.scalar.side_effect = [
        None,
        SimpleNamespace(id=uuid4(), status="ACTIVE", completed_at=None),
        completed_a,
        None,
        completed_b,
        review_b,
        SimpleNamespace(status="DRAFT"),
        completed_c,
        review_c,
        SimpleNamespace(status="FINALIZED"),
        completed_d,
        review_d,
        None,
    ]
    model = OperationalWorkspaceReadModel(cast(AsyncSession, session))

    actions = await model._post_trade_actions(workspace_id)

    assert [action.title for action in actions] == [
        "Nachbeobachtung starten",
        "Exit Review erstellen",
        "Exit Review abschließen",
        "Exit Review aktualisieren",
    ]
    assert all(action.priority == "REVIEW" for action in actions)
    assert all(action.target.startswith("/post-trade?trade_id=") for action in actions)


@pytest.mark.asyncio
async def test_list_actions_sorts_by_priority_time_then_id() -> None:
    now = datetime.now(UTC)
    model = OperationalWorkspaceReadModel(cast(AsyncSession, AsyncMock(spec=AsyncSession)))
    action_late = _action(priority="ACTION", occurred_at=now + timedelta(minutes=1), suffix="b")
    action_early = _action(priority="ACTION", occurred_at=now, suffix="a")
    review = _action(priority="REVIEW", occurred_at=now - timedelta(days=1), suffix="review")
    blocked = _action(priority="BLOCKED", occurred_at=None, suffix="blocked")
    model._candidate_actions = AsyncMock(return_value=[blocked])
    model._alert_actions = AsyncMock(return_value=[])
    model._notification_failure_actions = AsyncMock(return_value=[])
    model._open_position_actions = AsyncMock(return_value=[action_late, action_early])
    model._post_trade_actions = AsyncMock(return_value=[review])

    actions = await model.list_actions(workspace_id=uuid4())

    assert actions == (action_early, action_late, review, blocked)
