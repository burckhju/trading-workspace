"""Regression: the existing confirmation path must remain reachable for missing data."""

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.operational_workspace.service.read_model import OperationalWorkspaceReadModel


@pytest.mark.asyncio
async def test_product_selection_choice_projection_includes_confirmable_unselected_run() -> None:
    workspace_id = uuid4()
    run_id = uuid4()
    evaluated_at = datetime.now(UTC)
    session = AsyncMock(spec=AsyncSession)
    session.execute.return_value = SimpleNamespace(all=lambda: [(run_id, evaluated_at)])
    model = OperationalWorkspaceReadModel(cast(AsyncSession, session))

    actions = await model._product_selection_choice_actions(workspace_id)

    assert len(actions) == 1
    action = actions[0]
    assert action.id == f"product-selection-run:{run_id}:choose-product"
    assert action.action_type == "PRODUCT_SELECTION_CHOICE"
    assert action.priority == "ACTION"
    assert action.title == "Produkt auswählen"
    assert "Begründung und Bestätigung" in action.detail
    assert "geeignetes Produkt" not in action.detail
    assert action.resource_type == "product_selection_run"
    assert action.resource_id == run_id
    assert action.target == f"/product-selection?run_id={run_id}"
    assert action.occurred_at == evaluated_at

    statement = session.execute.await_args.args[0]
    sql = str(statement)
    assert "SELECT DISTINCT" in sql
    assert "JOIN product_evaluations" in sql
    assert "LEFT OUTER JOIN product_selections" in sql
    assert "product_selection_runs.workspace_id" in sql
    assert "product_evaluations.eligibility_status" in sql
    compiled = str(statement.compile(compile_kwargs={"literal_binds": True}))
    assert "IN ('ELIGIBLE', 'NOT_EVALUABLE')" in compiled
    assert "INELIGIBLE" not in compiled
    assert "product_selections.id IS NULL" in sql
