"""Execute the existing choice projection against isolated PostgreSQL test relations."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.features.operational_workspace.service.read_model import OperationalWorkspaceReadModel


def _test_database_url() -> str:
    url = os.environ.get("TRADING_WORKSPACE_TEST_DATABASE_URL", "")
    if not url:
        pytest.skip("TRADING_WORKSPACE_TEST_DATABASE_URL is not configured")
    if url.split("?", 1)[0].rsplit("/", 1)[-1] != "trading_workspace_test":
        pytest.fail("Choice projection tests require the disposable trading_workspace_test")
    return url


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("statuses", "selected", "expected"),
    [
        (("ELIGIBLE",), False, 1),
        (("NOT_EVALUABLE",), False, 1),
        (("INELIGIBLE",), False, 0),
        ((), False, 0),
        (("NOT_EVALUABLE", "NOT_EVALUABLE"), False, 1),
        (("ELIGIBLE", "NOT_EVALUABLE", "INELIGIBLE"), False, 1),
        (("NOT_EVALUABLE", "INELIGIBLE"), False, 1),
        (("NOT_EVALUABLE",), True, 0),
        (("ELIGIBLE",), True, 0),
        (("UNKNOWN",), False, 0),
    ],
)
async def test_choice_projection_respects_confirmable_status_and_workspace(
    statuses: tuple[str, ...], selected: bool, expected: int
) -> None:
    engine = create_async_engine(_test_database_url())
    workspace_id, other_workspace_id, run_id, foreign_run_id = (uuid4() for _ in range(4))
    now = datetime.now(UTC)
    try:
        async with engine.connect() as connection, connection.begin():
            # Connection-local relations shadow, never alter, migrated owner tables.
            # The real API/owner-schema handoff is covered by the browser regression.
            await connection.execute(
                text(
                    "CREATE TEMP TABLE product_selection_runs "
                    "(id uuid PRIMARY KEY, workspace_id uuid NOT NULL, "
                    "evaluated_at timestamptz NOT NULL) ON COMMIT DROP"
                )
            )
            await connection.execute(
                text(
                    "CREATE TEMP TABLE product_evaluations "
                    "(id uuid PRIMARY KEY, run_id uuid NOT NULL, "
                    "eligibility_status varchar(32) NOT NULL) ON COMMIT DROP"
                )
            )
            await connection.execute(
                text(
                    "CREATE TEMP TABLE product_selections "
                    "(id uuid PRIMARY KEY, run_id uuid NOT NULL) ON COMMIT DROP"
                )
            )
            for identity, workspace, values in (
                (run_id, workspace_id, statuses),
                (foreign_run_id, other_workspace_id, ("ELIGIBLE", "NOT_EVALUABLE")),
            ):
                await connection.execute(
                    text("INSERT INTO product_selection_runs VALUES (:id, :workspace, :at)"),
                    {"id": identity, "workspace": workspace, "at": now},
                )
                for value in values:
                    await connection.execute(
                        text("INSERT INTO product_evaluations VALUES (:id, :run, :status)"),
                        {"id": uuid4(), "run": identity, "status": value},
                    )
            if selected:
                await connection.execute(
                    text("INSERT INTO product_selections VALUES (:id, :run)"),
                    {"id": uuid4(), "run": run_id},
                )
            async with AsyncSession(
                bind=connection, join_transaction_mode="create_savepoint"
            ) as session:
                reader = OperationalWorkspaceReadModel(session)
                actions = await reader._product_selection_choice_actions(workspace_id)
                assert len(actions) == expected
                assert all(action.resource_id == run_id for action in actions)
                if expected:
                    action = actions[0]
                    assert action.target == f"/product-selection?run_id={run_id}"
                    assert action.action_type == "PRODUCT_SELECTION_CHOICE"
                    assert "Begründung und Bestätigung" in action.detail
                    assert "geeignetes Produkt" not in action.detail
                # Repeated reads neither consume a run nor create selections.
                assert await reader._product_selection_choice_actions(workspace_id) == actions
                foreign = await reader._product_selection_choice_actions(other_workspace_id)
                assert [action.resource_id for action in foreign] == [foreign_run_id]
                count = await session.scalar(text("SELECT count(*) FROM product_selections"))
                assert count == int(selected)
    finally:
        await engine.dispose()
