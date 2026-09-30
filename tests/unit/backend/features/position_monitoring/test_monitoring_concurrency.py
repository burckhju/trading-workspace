"""Concurrent quote reads must not overlap state transactions or drop failures."""

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.features.position_monitoring.domain.models import (
    MonitoringRule,
    MonitoringRuleType,
    PriceObservation,
)
from app.features.position_monitoring.domain.transitions import TriggerTransition
from app.features.position_monitoring.service import cycle as module
from app.features.position_monitoring.service.application import (
    MonitoringEvaluationResult,
    PositionMonitoringService,
)
from app.features.position_monitoring.service.cycle import PositionMonitoringCycleService
from app.features.position_monitoring.service.rule_prices import RulePriceResult
from app.features.position_monitoring.service.subjects import (
    MonitoringSubject,
    MonitoringSubjectResolution,
)
from app.features.trade_position.domain.price_binding import PriceBasis, PriceBinding

NOW = datetime(2026, 9, 23, 12, tzinfo=UTC)
BINDING = PriceBinding(PriceBasis.WARRANT, uuid4(), "EUR")
RULE = MonitoringRule("stop", MonitoringRuleType.STOP_REACHED, Decimal(1), BINDING)


def resolutions(n):
    return tuple(
        MonitoringSubjectResolution(
            uuid4(),
            MonitoringSubject(
                uuid4(),
                uuid4(),
                uuid4(),
                None,
                None,
                str(i),
                (RULE,),
                warrant_id=BINDING.instrument_id,
            ),
        )
        for i in range(n)
    )


def cycle(items, processor, parallel=4):
    return PositionMonitoringCycleService(
        subjects=SimpleNamespace(list_resolutions=AsyncMock(return_value=items)),
        market_data=None,
        processor=processor,
        new_id=uuid4,
        now=lambda: NOW,
        parallel_positions=parallel,
    )


def result(timestamp=NOW):
    return RulePriceResult(
        "INDICATIVE",
        "WARRANT_REFERENCE_PRICE_CHECKED",
        PriceObservation(
            Decimal("0.9"),
            timestamp,
            BINDING,
            {"provider": "FRANKFURT_QUOTES", "execution_usable": "false"},
        ),
    )


@pytest.mark.asyncio
async def test_fast_position_is_evaluated_while_first_quotes_wait_and_writes_are_serial(
    monkeypatch,
):
    items = resolutions(7)
    release, fast_done = asyncio.Event(), asyncio.Event()
    active = peak = writes = peak_writes = 0
    completed = []

    async def price(**kwargs):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        try:
            if int(kwargs["subject"].symbol) < 3:
                await release.wait()
            return result()
        finally:
            active -= 1

    async def process(**kwargs):
        nonlocal writes, peak_writes
        writes += 1
        peak_writes = max(peak_writes, writes)
        await asyncio.sleep(0)
        completed.append(kwargs["position_id"])
        if kwargs["position_id"] == items[-1].subject.position_id:
            fast_done.set()
        writes -= 1
        return MonitoringEvaluationResult(TriggerTransition.STAYED_CLEAR, None)

    monkeypatch.setattr(module, "rule_price", price)
    task = asyncio.create_task(cycle(items, SimpleNamespace(process=process)).run())
    try:
        await asyncio.wait_for(fast_done.wait(), 1)
        assert all(item.subject.position_id not in completed for item in items[:3])
        assert peak == 4 and peak_writes == 1
        release.set()
        report = await task
        assert report.positions_seen == report.positions_checked == report.rules_evaluated == 7
        assert [c["position_id"] for c in report.rule_checks] == [
            str(i.subject.position_id) for i in items
        ]
        assert all(float(c["price_request_seconds"]) >= 0 for c in report.rule_checks)
        assert report.position_errors == 0
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


@pytest.mark.asyncio
async def test_cancel_joins_every_quote_worker(monkeypatch):
    entered, ended = [], []
    ready = asyncio.Event()

    async def price(**kwargs):
        key = kwargs["subject"].position_id
        entered.append(key)
        if len(entered) == 4:
            ready.set()
        try:
            await asyncio.Event().wait()
        finally:
            ended.append(key)

    monkeypatch.setattr(module, "rule_price", price)
    processor = SimpleNamespace(process=AsyncMock())
    task = asyncio.create_task(cycle(resolutions(10), processor).run())
    await asyncio.wait_for(ready.wait(), 1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert set(entered) == set(ended) and len(entered) == 4
    processor.process.assert_not_awaited()


@pytest.mark.asyncio
async def test_old_quote_is_reported_with_evidence_and_never_rewinds_actual_state(monkeypatch):
    stored = None
    alerts = []

    async def get(**kwargs):
        return stored

    async def put(value):
        nonlocal stored
        stored = value

    async def add(value):
        alerts.append(value)

    resolver = AsyncMock()
    app = PositionMonitoringService(
        states=SimpleNamespace(get=get, put=put),
        alerts=SimpleNamespace(add=add, resolve=resolver),
        new_id=uuid4,
        now=lambda: NOW,
    )
    items = resolutions(1)
    subject = items[0].subject
    await app.evaluate(
        position_id=subject.position_id,
        trade_id=subject.trade_id,
        rule=RULE,
        observation=result().observation,
    )
    newest = stored
    monkeypatch.setattr(
        module, "rule_price", AsyncMock(return_value=result(NOW - timedelta(days=5)))
    )
    report = await cycle(items, SimpleNamespace(process=app.evaluate)).run()
    assert report.stale_market_data == 1 and report.position_errors == report.rules_evaluated == 0
    assert stored is newest and len(alerts) == 1
    resolver.assert_not_awaited()
    assert report.rule_checks[0]["reason"] == "OUT_OF_ORDER_RULE_OBSERVATION"
    assert report.rule_checks[0]["previous_seen_at"] == NOW.isoformat()
    assert report.rule_checks[0]["previous_time_basis"] == "SOURCE_TIMESTAMP"


@pytest.mark.asyncio
async def test_database_failure_is_not_mislabelled_stale_or_exposed(monkeypatch):
    class DBError(Exception):
        sqlstate = "23505"

    failure = IntegrityError("SQL private", {"password": "secret"}, DBError("private server"))
    monkeypatch.setattr(module, "rule_price", AsyncMock(return_value=result()))
    processor = SimpleNamespace(
        process=AsyncMock(
            side_effect=[failure, MonitoringEvaluationResult(TriggerTransition.STAYED_CLEAR, None)]
        )
    )
    report = await cycle(resolutions(2), processor).run()
    assert report.position_errors == 1 and report.positions_checked == 1
    check = report.rule_checks[0]
    assert check["reason"] == "RULE_EVALUATION_FAILED"
    assert check["error_type"] == "IntegrityError" and check["sqlstate"] == "23505"
    assert "secret" not in str(report) and "private" not in str(report)


@pytest.mark.asyncio
async def test_quote_failure_is_isolated_and_empty_cycle_is_supported(monkeypatch):
    monkeypatch.setattr(
        module, "rule_price", AsyncMock(side_effect=[RuntimeError("private URL"), result()])
    )
    processor = SimpleNamespace(
        process=AsyncMock(
            return_value=MonitoringEvaluationResult(TriggerTransition.STAYED_CLEAR, None)
        )
    )
    report = await cycle(resolutions(2), processor).run()
    assert report.market_data_errors == report.positions_checked == 1
    assert report.rule_checks[0]["error_type"] == "RuntimeError" and "private URL" not in str(
        report
    )
    assert (await cycle((), processor).run()).positions_seen == 0


@pytest.mark.asyncio
async def test_status_audit_reads_no_quotes_and_keeps_nonpositive_or_retained_quotes_out(
    monkeypatch,
):
    import httpx

    from app.tools import audit_monitoring_performance as audit

    paths = []
    issuer = next(iter(audit.TARGETS))
    monitoring = {
        "enabled": True,
        "running": True,
        "last_cycle_completed_at": NOW.isoformat(),
        "last_rule_checks": [
            {
                "isin": issuer,
                "position_id": "1",
                "status": "INDICATIVE",
                "price_request_seconds": "0.5",
            }
        ],
    }
    refresh = {
        "enabled": True,
        "leader": True,
        "last_scan_at": NOW.isoformat(),
        "jobs": [
            {
                "isin": issuer,
                "lane": "ISSUER_QUOTES",
                "status": "AVAILABLE",
                "checked_at": NOW.isoformat(),
                "quotes": [
                    {
                        "provider": audit.TARGETS[issuer],
                        "bid": "NaN",
                        "retrieved_at": NOW.isoformat(),
                    }
                ],
            }
        ],
    }

    def respond(request):
        paths.append((request.method, request.url.path))
        return httpx.Response(
            200, json=monitoring if "position-monitoring" in request.url.path else refresh
        )

    client = httpx.AsyncClient(
        base_url="http://127.0.0.1:8000", transport=httpx.MockTransport(respond)
    )
    monkeypatch.setattr(audit.httpx, "AsyncClient", lambda **kwargs: client)
    report = await audit.audit(0)
    assert report["wait_completed"] is True
    assert paths == [
        ("GET", "/api/v1/position-monitoring/runtime/status"),
        ("GET", "/api/v1/market-data/refresh/status"),
    ]
    assert report["summary"]["issuer_refresh_success_count"] == 0
    quote = refresh["jobs"][0]["quotes"][0]
    quote.update(bid="0.001", retained=True)
    assert audit.summarize(monitoring, refresh)["summary"]["issuer_refresh_success_count"] == 0
    quote["retained"] = False
    assert audit.summarize(monitoring, refresh)["summary"]["issuer_refresh_success_count"] == 1


def test_parallelism_is_bounded_and_duration_survives_api_model():
    from pydantic import ValidationError

    from app.core.config import Settings
    from app.features.position_monitoring.api.dtos import MonitoringRuntimeStatusResponse

    assert Settings(environment="test").position_monitoring.parallel_positions == 4
    with pytest.raises(ValidationError):
        Settings(environment="test", position_monitoring={"parallel_positions": 5})
    response = MonitoringRuntimeStatusResponse(
        enabled=True, interval_seconds=900, parallel_positions=4, last_cycle_duration_seconds=12.345
    )
    assert response.model_dump()["last_cycle_duration_seconds"] == 12.345
