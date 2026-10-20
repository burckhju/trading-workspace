"""Read-only names must follow exact product references, not URLs or underlyings."""

from dataclasses import asdict, replace
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.operational_workspace.api.dtos import OperationalActionResponse
from app.features.operational_workspace.service.prioritization import prioritize_position_monitoring
from app.features.operational_workspace.service.read_model import (
    OperationalAction,
    OperationalWorkspaceReadModel,
)
from app.features.position_monitoring.service.health import (
    MonitoringHealthStatus,
    PositionMonitoringHealth,
)
from app.features.product.service.application import WarrantService

NOW = datetime(2026, 9, 14, 12, tzinfo=UTC)
METHODS = (
    "_candidate_actions",
    "_alert_actions",
    "_notification_failure_actions",
    "_trade_plan_review_actions",
    "_product_selection_start_actions",
    "_product_selection_choice_actions",
    "_initial_purchase_actions",
    "_open_position_actions",
    "_post_trade_actions",
)


def action(**changes):
    return OperationalAction(
        **{
            "id": str(uuid4()),
            "source_feature": "SYNTHETIC",
            "action_type": "OPEN_POSITION_MANAGEMENT",
            "priority": "ACTION",
            "state": "ACTIONABLE",
            "title": "Offene Position verwalten",
            "detail": "SYNTHETIC",
            "resource_type": "trade",
            "resource_id": uuid4(),
            "next_action": "Prüfen",
            "target": "/do-not-parse?trade_id=wrong",
            "occurred_at": NOW,
            **changes,
        }
    )


class Rows:
    def __init__(self, values):
        self.values = values

    def all(self):
        return self.values


@pytest.mark.parametrize(
    "method",
    [
        "_alert_actions",
        "_notification_failure_actions",
        "_initial_purchase_actions",
        "_open_position_actions",
        "_post_trade_actions",
    ],
)
async def test_action_projects_exact_product_reference(method):
    product_id, resource_id, trade_id = uuid4(), uuid4(), uuid4()
    alert = SimpleNamespace(
        id=resource_id,
        trade_id=trade_id,
        alert_type="STOP_REACHED",
        reason="SYNTHETIC",
        detected_at=NOW,
    )
    rows = {
        "_alert_actions": [(alert, product_id)],
        "_notification_failure_actions": [(resource_id, "TELEGRAM", NOW, trade_id, product_id)],
        "_initial_purchase_actions": [(resource_id, uuid4(), NOW, product_id)],
        "_open_position_actions": [(trade_id, NOW, product_id)],
        "_post_trade_actions": [(trade_id, NOW, product_id)],
    }
    session = AsyncMock(spec=AsyncSession)
    session.execute.return_value = Rows(rows[method])
    session.scalars.return_value = Rows([alert])
    session.scalar.return_value = None
    result = await getattr(OperationalWorkspaceReadModel(session), method)(uuid4())
    assert len(result) == 1
    assert result[0].product_id == product_id
    session.commit.assert_not_awaited()
    session.flush.assert_not_awaited()


async def test_one_batch_enriches_all_actions_and_preserves_missing_and_unselected_context():
    workspace_id, a, b, missing = uuid4(), uuid4(), uuid4(), uuid4()
    items = [action(product_id=a if i % 2 else b) for i in range(100)]
    items += [
        action(product_id=missing),
        action(action_type="PRODUCT_SELECTION_CHOICE", resource_type="product_selection_run"),
    ]
    model = OperationalWorkspaceReadModel(AsyncMock(spec=AsyncSession))
    for method in METHODS:
        setattr(
            model,
            method,
            AsyncMock(return_value=items if method == "_open_position_actions" else []),
        )
    from app.features.product.service.identities import WarrantIdentity

    names = {
        a: WarrantIdentity(a, "SYNTHETIC Alpha", "DE000SYN0010", "SYN001"),
        b: WarrantIdentity(b, "SYNTHETIC Beta", "DE000SYN0020", "SYN002"),
    }
    with patch.object(
        WarrantService, "read_identities", new_callable=AsyncMock, return_value=names
    ) as reader:
        result = await model.list_actions(workspace_id=workspace_id)
    reader.assert_awaited_once_with(workspace_id=workspace_id, warrant_ids={a, b, missing})
    assert len(result) == len(items)
    originals = {item.id: item for item in items}
    for item in result:
        original = originals[item.id]
        identity = names.get(item.product_id)
        assert item.product_name == (identity.display_name if identity else None)
        assert item.product_wkn == (identity.wkn if identity else None)
        assert item.product_isin == (identity.isin if identity else None)
        assert replace(item, product_name=None, product_isin=None, product_wkn=None) == original
        response = OperationalActionResponse(**asdict(item)).model_dump(mode="json")
        assert response["product_name"] == item.product_name


async def test_data_health_priority_keeps_identity():
    original = action(
        product_id=uuid4(),
        product_name="SYNTHETIC Call",
        product_isin="DE000SYN0010",
        product_wkn="SYN001",
    )
    health = PositionMonitoringHealth(
        original.resource_id, uuid4(), MonitoringHealthStatus.STALE, "SYNTHETIC"
    )
    result = await prioritize_position_monitoring(
        (original,), health_reader=AsyncMock(return_value=health)
    )
    assert result[0].action_type == "POSITION_DATA_HEALTH"
    assert result[0].product_name == original.product_name
    assert result[0].product_id == original.product_id
    assert result[0].product_isin == original.product_isin
    assert result[0].product_wkn == original.product_wkn
