"""Exact model contracts across existing run, retry, verify and reference owners."""

from copy import deepcopy
from dataclasses import asdict, replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.features.analysis.domain.calculator import MODEL_ID
from app.features.analysis.domain.errors import AnalysisConflict
from app.features.analysis.domain.models import (
    AnalysisParameters,
    SnapshotRow,
    calculate_input_hash,
)
from app.features.analysis.service import application
from app.features.analysis.service.application import MarketAnalysisService
from app.features.analysis.service.reference_application import MarketReferenceAnalysisService

NOW = datetime(2026, 10, 25, 12, tzinfo=UTC)


def rows(count=220):
    days = []
    day = NOW.date() - timedelta(days=1)
    while len(days) < count:
        if day.weekday() < 5:
            days.append(day)
        day -= timedelta(days=1)
    return tuple(
        SnapshotRow(
            day,
            Decimal(100 + index),
            Decimal(102 + index),
            Decimal(99 + index),
            Decimal(101 + index),
            Decimal(101 + index),
            Decimal(1000),
            "EUR",
            "EODHD",
            "SYNTHETIC-FT006",
            "VALID",
            (),
        )
        for index, day in enumerate(reversed(days))
    )


@pytest.fixture
def owner(monkeypatch):
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW

    monkeypatch.setattr(application, "datetime", Clock)
    service = MarketAnalysisService(AsyncMock())
    service._repo = AsyncMock()
    service._repo.get_analysis.return_value = SimpleNamespace(id=uuid4(), listing_id=uuid4())
    service._repo.get_latest_run.return_value = None
    service._repo.get_supersede_event.return_value = None
    service._repo.next_version.return_value = 1
    service._market_data = AsyncMock()
    return service


def prices(source_rows, reference=False):
    result = []
    for row in source_rows:
        value = asdict(row)
        value["provider"] = SimpleNamespace(value=row.provider)
        value["quality_status"] = SimpleNamespace(value=row.quality_status)
        value["warnings"] = "\n".join(row.warnings) if reference else row.warnings
        result.append(SimpleNamespace(**value))
    return tuple(result)


async def execute(owner, source_rows, version):
    return await owner._execute_snapshot(
        analysis_id=uuid4(),
        parameters=AnalysisParameters(),
        rows=source_rows,
        correlation_id="synthetic-ft006",
        source_version=None,
        model_version=version,
    )


def install_readback(owner, run):
    owner._repo.get_run.return_value = run
    owner._repo.list_snapshot.return_value = owner._repo.add_snapshot_rows.await_args.args[0]
    owner._repo.list_criteria.return_value = owner._repo.add_criteria.await_args.args[0]


@pytest.mark.asyncio
@pytest.mark.parametrize("version,quality", [("1.0.0", "LIMITED"), ("1.0.1", "GOOD")])
async def test_execute_persists_exact_contract_and_verifies_it(owner, version, quality):
    source_rows = rows()
    before = tuple(row.canonical() for row in source_rows)
    run = await execute(owner, source_rows, version)
    assert (run.model_id, run.model_version, run.quality_status) == (MODEL_ID, version, quality)
    expected_hash = calculate_input_hash(MODEL_ID, version, AnalysisParameters(), source_rows)
    assert run.input_hash == expected_hash
    stored_rows = owner._repo.add_snapshot_rows.await_args.args[0]
    assert tuple(owner._snapshot_to_domain(row).canonical() for row in stored_rows) == before
    assert tuple(row.canonical() for row in source_rows) == before
    install_readback(owner, run)
    owner._session.reset_mock()
    result = await owner.verify_reproducibility(uuid4(), run.analysis_id, 1)
    assert result["verified"] is True
    assert all(result.values())
    owner._session.commit.assert_not_awaited()
    owner._market_data.list_daily_prices.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("version,quality", [(None, "LIMITED"), ("1.0.1", "GOOD")])
async def test_listing_run_preserves_default_and_accepts_explicit_version(owner, version, quality):
    source_rows = rows()
    owner._market_data.list_daily_prices.return_value = prices(source_rows)
    options = {} if version is None else {"model_version": version}
    run = await owner.run(
        uuid4(),
        uuid4(),
        source_rows[0].trading_date,
        source_rows[-1].trading_date,
        AnalysisParameters(),
        None,
        **options,
    )
    assert run.model_version == (version or "1.0.0")
    assert run.quality_status == quality


@pytest.mark.asyncio
@pytest.mark.parametrize("version", ["1.0.0", "1.0.1"])
async def test_retry_preserves_source_model_snapshot_hash_and_terminal_row(owner, version):
    source = await execute(owner, rows(1), version)
    assert source.status == "NOT_EVALUABLE"
    install_readback(owner, source)
    before = (source.status, source.input_hash, deepcopy(source.metrics), list(source.notes))
    owner._repo.next_version.return_value = 2
    owner._market_data.list_daily_prices.side_effect = AssertionError("No live prices on retry")
    replacement = await owner.retry(uuid4(), source.analysis_id, 1, "retry", "synthetic")
    assert replacement.id != source.id
    assert replacement.version == 2
    assert replacement.model_version == version
    assert replacement.input_hash == source.input_hash
    assert replacement.quality_status == "INSUFFICIENT"
    assert (source.status, source.input_hash, source.metrics, source.notes) == before
    owner._market_data.list_daily_prices.assert_not_awaited()
    event = owner._repo.add_event.await_args.args[0]
    assert (event.event_type, event.source_version, event.replacement_version) == (
        "SUPERSEDED",
        1,
        2,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model_id,version", [("OTHER", "1.0.1"), (MODEL_ID, "latest"), (MODEL_ID, "9.0.0")]
)
async def test_unknown_execution_is_rejected_before_any_persistence(owner, model_id, version):
    with pytest.raises(AnalysisConflict, match="not available"):
        await owner._execute_snapshot(
            analysis_id=uuid4(),
            parameters=AnalysisParameters(),
            rows=rows(),
            correlation_id=None,
            source_version=None,
            model_id=model_id,
            model_version=version,
        )
    assert owner._repo.mock_calls == []
    owner._session.commit.assert_not_awaited()
    owner._session.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_unknown_listing_version_does_not_read_prices_or_write(owner):
    with pytest.raises(AnalysisConflict, match="not available"):
        await owner.run(
            uuid4(),
            uuid4(),
            date(2026, 1, 1),
            date(2026, 10, 23),
            AnalysisParameters(),
            None,
            model_version="latest",
        )
    owner._market_data.list_daily_prices.assert_not_awaited()
    owner._repo.add_run.assert_not_awaited()
    owner._session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_verify_unknown_identity_never_uses_another_calculator(owner):
    run = await execute(owner, rows(), "1.0.1")
    install_readback(owner, run)
    run.model_version = "future-unsupported"
    owner._session.reset_mock()
    result = await owner.verify_reproducibility(uuid4(), run.analysis_id, 1)
    assert result["model_available"] is False
    assert result["verified"] is False
    owner._repo.list_criteria.assert_not_awaited()
    owner._session.commit.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("fault", ["warnings", "stale", "source_quality"])
async def test_new_version_keeps_limiting_facts_and_verifies_at_original_time(owner, fault):
    source_rows = rows()
    if fault == "warnings":
        source_rows = (
            replace(source_rows[0], warnings=("synthetic quality warning",)),
            *source_rows[1:],
        )
    elif fault == "source_quality":
        source_rows = (replace(source_rows[0], quality_status="SUSPICIOUS"), *source_rows[1:])
    else:
        source_rows = tuple(
            replace(row, trading_date=row.trading_date - timedelta(days=100)) for row in source_rows
        )
    run = await execute(owner, source_rows, "1.0.1")
    assert run.quality_status == "LIMITED"
    assert run.notes
    install_readback(owner, run)
    result = await owner.verify_reproducibility(uuid4(), run.analysis_id, 1)
    assert result["verified"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("version,quality", [("1.0.0", "LIMITED"), ("1.0.1", "GOOD")])
async def test_reference_owner_uses_same_versioned_executor(owner, version, quality):
    service = MarketReferenceAnalysisService(owner._session)
    service._repo = owner._repo
    service._repo.get_analysis.return_value = SimpleNamespace(
        id=uuid4(),
        listing_id=None,
        market_data_instrument_id=uuid4(),
    )
    service._identity = AsyncMock()
    service._identity.get.return_value = SimpleNamespace(
        kind="MARKET_REFERENCE", market_reference_id=uuid4()
    )
    service._active_reference = AsyncMock(return_value=SimpleNamespace(active=True))
    source_rows = rows()
    service._session.scalars.return_value = Mock(all=Mock(return_value=prices(source_rows, True)))
    run = await service.run_market_reference(
        workspace_id=uuid4(),
        analysis_id=uuid4(),
        start_date=source_rows[0].trading_date,
        end_date=source_rows[-1].trading_date,
        parameters=AnalysisParameters(),
        correlation_id=None,
        model_version=version,
    )
    assert run.model_version == version
    assert run.quality_status == quality
    install_readback(service, run)
    verification = await service.verify_reproducibility(uuid4(), run.analysis_id, 1)
    assert verification["verified"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("version", ["1.0.0", "1.0.1"])
async def test_verify_matches_persisted_criteria_order_without_rewriting(owner, version):
    run = await execute(owner, rows(), version)
    install_readback(owner, run)
    stored = owner._repo.list_criteria.return_value
    owner._repo.list_criteria.return_value = sorted(stored, key=lambda item: item.code)
    before = tuple(
        (item.code, item.classification, item.value, item.explanation) for item in stored
    )
    result = await owner.verify_reproducibility(uuid4(), run.analysis_id, 1)
    assert result["criteria_match"] is True
    assert result["verified"] is True
    after = tuple((item.code, item.classification, item.value, item.explanation) for item in stored)
    assert after == before


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fault", ["code", "classification", "value", "explanation", "missing", "duplicate"]
)
async def test_verify_rejects_changed_criterion_fields_and_multiplicity(owner, fault):
    run = await execute(owner, rows(), "1.0.1")
    install_readback(owner, run)
    stored = list(owner._repo.list_criteria.return_value)
    if fault == "missing":
        stored.pop()
    elif fault == "duplicate":
        stored.append(stored[0])
    elif fault == "value":
        stored[0].value += Decimal("0.000001")
    else:
        setattr(stored[0], fault, "corrupted-synthetic-value")
    owner._repo.list_criteria.return_value = sorted(stored, key=lambda item: item.code)
    result = await owner.verify_reproducibility(uuid4(), run.analysis_id, 1)
    assert result["criteria_match"] is False
    assert result["verified"] is False
