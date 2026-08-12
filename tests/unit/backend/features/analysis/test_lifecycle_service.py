from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from app.features.analysis.persistence.models import MarketAnalysisRunModel
from app.features.analysis.service.application import MarketAnalysisService

ANALYSIS_ID = UUID("10000000-0000-4000-8000-000000000001")
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")
RUN_ID = UUID("40000000-0000-4000-8000-000000000001")


def parameters() -> dict:
    return {
        "price_field": "ADJUSTED_CLOSE",
        "short_window": 20,
        "medium_window": 50,
        "long_window": 200,
        "momentum_windows": [20, 60, 120],
        "volatility_window": 20,
        "range_window": 52,
        "minimum_required_observations": 200,
        "maximum_data_age_days": 7,
        "annualization_factor": "252",
        "rounding_scale": 6,
    }


def source_run(status: str = "NOT_EVALUABLE") -> MarketAnalysisRunModel:
    return MarketAnalysisRunModel(
        id=RUN_ID,
        analysis_id=ANALYSIS_ID,
        version=1,
        status=status,
        quality_status="INSUFFICIENT",
        model_id="EOD_TREND_MOMENTUM",
        model_version="1.0.0",
        parameters=parameters(),
        metrics={},
        notes=[],
        data_sources=["EODHD"],
        input_hash="a" * 64,
        observation_count=1,
        analysis_time=datetime(2026, 8, 6, tzinfo=UTC),
        correlation_id=None,
        error_message=None,
    )


@pytest.mark.asyncio
async def test_retry_reuses_persisted_snapshot_and_does_not_read_market_data() -> None:
    session = AsyncMock()
    service = MarketAnalysisService(session)
    service._repo = AsyncMock()
    service._market_data = AsyncMock()
    service._repo.get_analysis.return_value = SimpleNamespace(id=ANALYSIS_ID)
    service._repo.get_run.return_value = source_run()
    service._repo.get_supersede_event.return_value = None
    service._repo.list_snapshot.return_value = (
        SimpleNamespace(
            trading_date=date(2026, 8, 5),
            open=Decimal("100"),
            high=Decimal("103"),
            low=Decimal("99"),
            close=Decimal("102"),
            adjusted_close=Decimal("102"),
            volume=Decimal("1000"),
            currency="EUR",
            provider="EODHD",
            provider_symbol="SIE.XETRA",
            quality_status="GOOD",
            warnings=[],
        ),
    )
    replacement = source_run("COMPLETED")
    replacement.version = 2
    service._execute_snapshot = AsyncMock(return_value=replacement)
    service._append_superseded_event = AsyncMock()

    result = await service.retry(WORKSPACE_ID, ANALYSIS_ID, 1, "corr-2", "retry exact snapshot")

    assert result.version == 2
    service._market_data.list_daily_prices.assert_not_awaited()
    call = service._execute_snapshot.await_args.kwargs
    assert call["source_version"] == 1
    assert call["parameters"].as_dict() == parameters()
    assert call["rows"][0].canonical()["close"] == "102"
    service._append_superseded_event.assert_awaited_once()


@pytest.mark.asyncio
async def test_retry_rejects_already_superseded_source() -> None:
    session = AsyncMock()
    service = MarketAnalysisService(session)
    service._repo = AsyncMock()
    service._repo.get_analysis.return_value = SimpleNamespace(id=ANALYSIS_ID)
    service._repo.get_run.return_value = source_run()
    service._repo.get_supersede_event.return_value = SimpleNamespace(id="event")

    with pytest.raises(Exception, match="already superseded"):
        await service.retry(WORKSPACE_ID, ANALYSIS_ID, 1, None, None)


@pytest.mark.asyncio
async def test_reproducibility_verification_recalculates_exact_persisted_inputs() -> None:
    from datetime import timedelta

    from app.features.analysis.domain.calculator import (
        MODEL_ID,
        MODEL_VERSION,
        calculate,
    )
    from app.features.analysis.domain.models import (
        AnalysisParameters,
        SnapshotRow,
        calculate_input_hash,
    )

    params = AnalysisParameters()
    domain_rows = tuple(
        SnapshotRow(
            trading_date=date(2025, 1, 1) + timedelta(days=index),
            open=Decimal("100") + index,
            high=Decimal("102") + index,
            low=Decimal("99") + index,
            close=Decimal("101") + index,
            adjusted_close=Decimal("101") + index,
            volume=Decimal("1000"),
            currency="EUR",
            provider="EODHD",
            provider_symbol="TEST.XETRA",
            quality_status="GOOD",
            warnings=(),
        )
        for index in range(220)
    )
    computation = calculate(params, domain_rows)
    last_date = domain_rows[-1].trading_date
    run = MarketAnalysisRunModel(
        id=RUN_ID,
        analysis_id=ANALYSIS_ID,
        version=1,
        status="COMPLETED",
        quality_status=computation.quality_status.value,
        model_id=MODEL_ID,
        model_version=MODEL_VERSION,
        parameters=params.as_dict(),
        metrics=computation.metrics,
        notes=list(computation.notes),
        data_sources=["EODHD"],
        input_hash=calculate_input_hash(MODEL_ID, MODEL_VERSION, params, domain_rows),
        observation_count=len(domain_rows),
        analysis_time=datetime(last_date.year, last_date.month, last_date.day, 12, tzinfo=UTC),
        correlation_id=None,
        error_message=None,
    )
    persisted_rows = tuple(
        SimpleNamespace(
            trading_date=row.trading_date,
            open=row.open,
            high=row.high,
            low=row.low,
            close=row.close,
            adjusted_close=row.adjusted_close,
            volume=row.volume,
            currency=row.currency,
            provider=row.provider,
            provider_symbol=row.provider_symbol,
            quality_status=row.quality_status,
            warnings=list(row.warnings),
        )
        for row in domain_rows
    )
    persisted_criteria = tuple(
        SimpleNamespace(
            code=item.code,
            classification=item.classification.value,
            value=item.value,
            explanation=item.explanation,
        )
        for item in computation.criteria
    )
    session = AsyncMock()
    service = MarketAnalysisService(session)
    service._repo = AsyncMock()
    service._repo.get_analysis.return_value = SimpleNamespace(id=ANALYSIS_ID)
    service._repo.get_run.return_value = run
    service._repo.list_snapshot.return_value = persisted_rows
    service._repo.list_criteria.return_value = persisted_criteria

    result = await service.verify_reproducibility(WORKSPACE_ID, ANALYSIS_ID, 1)

    assert result == {
        "verified": True,
        "model_available": True,
        "input_hash_matches": True,
        "metrics_match": True,
        "criteria_match": True,
        "quality_status_match": True,
        "notes_match": True,
    }
