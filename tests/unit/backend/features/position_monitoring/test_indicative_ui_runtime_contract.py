"""Synthetic runner-to-JSON proof for passive UI and controlled PC activation."""

from dataclasses import replace
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from tests.unit.backend.features.position_monitoring.test_runner import Runtime

from app.core.config import Settings
from app.features.position_monitoring.api.router import get_monitoring_runtime_status
from app.features.position_monitoring.service.indicative_entry_runtime import IndicativeRunResult
from app.features.position_monitoring.service.product_deadline_review_runtime import (
    ProductDeadlineRunResult,
)
from app.features.position_monitoring.service.runner import PositionMonitoringRunner


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "scope,version",
    [
        ("DISABLED", "indicative-entry-review-v1"),
        ("INDICATIVE_ENTRY_V1", "indicative-entry-review-v1"),
        ("INDICATIVE_ENTRY_V2", "indicative-entry-review-v2"),
    ],
)
async def test_activation_source_and_target_versions_are_exact_passive_json(scope, version):
    settings = Settings(
        environment="test",
        position_monitoring={"enabled": True, "review_scope": scope},
    )
    # This container has no provider, execution, persistence or delivery capability.
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))
    report = await get_monitoring_runtime_status(request, SimpleNamespace(settings=settings))
    wire = report.model_dump(mode="json")
    assert wire["review_scope"] == scope and wire["review_rule_version"] == version
    assert wire["hebeltrader_scope"] == "DISABLED"
    assert wire["review_notifications_enabled"] is False
    assert wire["enabled"] is True and wire["running"] is False
    assert wire["last_cycle_completed_at"] is None and wire["last_result"] is None


@pytest.mark.asyncio
async def test_completed_runner_cycle_exposes_separate_entry_and_deadline_counts_without_rerun():
    clock = datetime(2026, 11, 18, 20, tzinfo=UTC)
    cycle = replace(
        await Runtime().run(),
        indicative_entry=IndicativeRunResult(
            positions_evaluated=6, alerts_created=2, data_problems=4, position_errors=0
        ),
        product_deadline=ProductDeadlineRunResult(
            positions_evaluated=3, alerts_created=1, data_problems=2, position_errors=1
        ),
    )
    synthetic_runtime = SimpleNamespace(run=AsyncMock())
    runner = PositionMonitoringRunner(
        runtime=synthetic_runtime, interval_seconds=60, now=lambda: clock
    )

    async def one_completed_cycle():
        runner.stop()
        return cycle

    synthetic_runtime.run.side_effect = one_completed_cycle
    await runner.run_forever()
    settings = Settings(
        environment="test",
        position_monitoring={"enabled": True, "review_scope": "INDICATIVE_ENTRY_V2"},
    )
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(position_monitoring_runner=runner))
    )
    reports = [
        (
            await get_monitoring_runtime_status(request, SimpleNamespace(settings=settings))
        ).model_dump(mode="json")
        for _ in range(2)
    ]
    assert reports[0] == reports[1]
    wire = reports[0]
    assert wire["last_cycle_completed_at"] == "2026-11-18T20:00:00Z"
    assert wire["running"] is False and wire["cycle_running"] is False
    assert wire["last_error"] is None
    assert wire["review_rule_version"] == "indicative-entry-review-v2"
    assert {
        key: value
        for key, value in wire["last_result"].items()
        if key.startswith(("review_", "deadline_"))
    } == {
        "review_positions_evaluated": 6,
        "review_alerts_created": 2,
        "review_data_problems": 4,
        "review_position_errors": 0,
        "deadline_positions_evaluated": 3,
        "deadline_alerts_created": 1,
        "deadline_data_problems": 2,
        "deadline_position_errors": 1,
    }
    assert wire["last_result"]["positions_checked"] == 0
    assert wire["last_result"]["b04_positions_evaluated"] == 0
    synthetic_runtime.run.assert_awaited_once()
