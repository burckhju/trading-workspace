"""Versioned FT-006 owners on PostgreSQL; UUID-scoped, rollback-only fixtures.

Synthetic provenance belongs to the fixture name/symbol, not a fabricated data
quality warning. Negative cases add an actual marked quality warning separately.
No provider, scheduler, runtime activation, notification or production DB is used.
"""

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from tests.integration.backend.database.test_market_analysis_instrument_guard_postgres import (
    _test_database_url,
)

from app.features.analysis.api.dependencies import get_market_analysis_service
from app.features.analysis.domain.calculator import MODEL_ID
from app.features.analysis.domain.errors import AnalysisConflict
from app.features.analysis.domain.governed_provenance import governed_runtime_definition
from app.features.analysis.domain.models import AnalysisParameters, calculate_input_hash
from app.features.analysis.persistence.models import MarketAnalysisRunModel
from app.features.analysis.service.application import MarketAnalysisService
from app.features.analysis.service.reference_application import MarketReferenceAnalysisService
from app.features.market.domain.enums import (
    DataOrigin,
    LifecycleStatus,
    QualityStatus,
    UnderlyingType,
)
from app.features.market.persistence.models import (
    ListingModel,
    TradingVenueModel,
    UnderlyingModel,
    WorkspaceModel,
)
from app.features.market.persistence.top_down_models import MarketReferenceModel
from app.features.market_data.domain.enums import MarketDataProvider, PriceType
from app.features.market_data.domain.enums import QualityStatus as PriceQuality
from app.features.market_data.persistence.instruments import MarketDataInstrumentModel
from app.features.market_data.persistence.models import DailyPriceModel
from app.features.model.persistence.models import GovernedModelRecord, ModelVersionRecord

analysis_router = import_module("app.features.analysis.api.router")


def completed_days(today, count):
    days = []
    day = today - timedelta(days=1)
    while len(days) < count:
        if day.weekday() < 5:
            days.append(day)
        day -= timedelta(days=1)
    return tuple(reversed(days))


@pytest_asyncio.fixture
async def isolated_analysis_context():
    engine = create_async_engine(_test_database_url())
    try:
        async with engine.connect() as connection:
            actual = await connection.scalar(text("SELECT current_database()"))
            assert actual == "trading_workspace_test"
            await connection.rollback()
            transaction = await connection.begin()
            try:
                async with AsyncSession(
                    bind=connection,
                    expire_on_commit=False,
                    join_transaction_mode="create_savepoint",
                ) as session:
                    now = datetime.now(UTC)
                    workspace = uuid4()
                    session.add(
                        WorkspaceModel(
                            id=workspace, name=f"SYNTHETIC FT006 {workspace}", created_at=now
                        )
                    )
                    await session.flush()
                    yield SimpleNamespace(session=session, workspace=workspace, now=now)
            finally:
                await transaction.rollback()
    finally:
        await engine.dispose()


async def create_source(context, owner, *, count=220, warning="", quality=PriceQuality.VALID):
    session, workspace, now = context.session, context.workspace, context.now
    symbol = f"SYNTHETIC-FT006-{uuid4().hex[:12]}"
    listing = None
    if owner == "listing":
        venue = await session.scalar(
            select(TradingVenueModel).where(TradingVenueModel.is_active.is_(True)).limit(1)
        )
        assert venue is not None
        underlying = UnderlyingModel(
            id=uuid4(),
            workspace_id=workspace,
            type=UnderlyingType.STOCK,
            name=f"TEST ONLY {symbol}",
            lifecycle_status=LifecycleStatus.ACTIVE,
            quality_status=QualityStatus.COMPLETE,
            version=1,
            created_at=now,
            updated_at=now,
            data_origin=DataOrigin.MANUAL,
        )
        session.add(underlying)
        await session.flush()
        listing = ListingModel(
            id=uuid4(),
            workspace_id=workspace,
            underlying_id=underlying.id,
            trading_venue_id=venue.id,
            ticker=symbol,
            currency_code="EUR",
            lifecycle_status=LifecycleStatus.ACTIVE,
            is_primary=True,
            version=1,
            created_at=now,
            updated_at=now,
            data_origin=DataOrigin.MANUAL,
        )
        session.add(listing)
        await session.flush()
        service = MarketAnalysisService(session)
        analysis = await service.create(workspace, underlying.id, listing.id, symbol)
    else:
        reference = MarketReferenceModel(
            id=uuid4(),
            workspace_id=workspace,
            code=symbol,
            name=f"TEST ONLY {symbol}",
            reference_type="INDEX",
            region="GLOBAL",
            role="BENCHMARK",
            reference_version="synthetic-ft006",
            active=True,
            created_at=now,
        )
        session.add(reference)
        await session.flush()
        service = MarketReferenceAnalysisService(session)
        analysis = await service.create_for_market_reference(
            workspace_id=workspace, market_reference_id=reference.id, actor=symbol
        )
    assert analysis.market_data_instrument_id is not None
    instrument = await session.get(MarketDataInstrumentModel, analysis.market_data_instrument_id)
    assert instrument is not None
    assert instrument.workspace_id == workspace
    days = completed_days(now.date(), count)
    for index, day in enumerate(days):
        price = Decimal(100 + index)
        session.add(
            DailyPriceModel(
                id=uuid4(),
                workspace_id=workspace,
                listing_id=None if listing is None else listing.id,
                market_data_instrument_id=instrument.id,
                trading_date=day,
                open=price,
                high=price + 1,
                low=price - 1,
                close=price,
                adjusted_close=price,
                volume=Decimal(1000),
                currency="EUR",
                provider=MarketDataProvider.EODHD,
                provider_symbol=symbol,
                retrieved_at=now,
                source_updated_at=None,
                quality_status=quality,
                warnings=warning,
                price_type=PriceType.EOD,
                created_at=now,
                updated_at=now,
            )
        )
    await session.flush()
    return SimpleNamespace(
        service=service, analysis=analysis, days=days, owner=owner, workspace=workspace
    )


async def run_source(source, version=None):
    options = {} if version is None else {"model_version": version}
    if source.owner == "reference":
        return await source.service.run_market_reference(
            workspace_id=source.workspace,
            analysis_id=source.analysis.id,
            start_date=source.days[0],
            end_date=source.days[-1],
            parameters=AnalysisParameters(),
            correlation_id="synthetic-ft006",
            **options,
        )
    return await source.service.run(
        source.workspace,
        source.analysis.id,
        source.days[0],
        source.days[-1],
        AnalysisParameters(),
        "synthetic-ft006",
        **options,
    )


async def add_governed_version(context, model, ordinal, version, status="APPROVED"):
    definition = governed_runtime_definition(model_id=MODEL_ID, model_version=version)
    assert definition is not None
    record = ModelVersionRecord(
        id=uuid4(),
        model_id=model.id,
        version=ordinal,
        status=status,
        definition=definition,
        change_summary="Synthetic provenance fixture, not a user approval or activation",
        created_at=context.now,
        created_by=uuid4(),
        previous_version_id=None,
    )
    context.session.add(record)
    await context.session.flush()
    return record


@pytest.mark.asyncio
@pytest.mark.parametrize("owner", ["listing", "reference"])
async def test_both_native_owners_preserve_history_and_exact_governed_contract(
    isolated_analysis_context, owner
):
    context = isolated_analysis_context
    source = await create_source(context, owner)
    model = GovernedModelRecord(
        id=uuid4(),
        workspace_id=context.workspace,
        model_key=MODEL_ID,
        name="SYNTHETIC FT006 provenance",
        purpose="Rollback-only version binding test",
        created_at=context.now,
        created_by=uuid4(),
    )
    context.session.add(model)
    await context.session.flush()
    old_definition = await add_governed_version(context, model, 1, "1.0.0")
    corrected = await add_governed_version(context, model, 2, "1.0.1", status="DRAFT")
    old = await run_source(source)
    assert old.model_version == "1.0.0"
    assert old.quality_status == "LIMITED"
    assert old.governed_model_version_id == old_definition.id
    old_facts = (old.input_hash, deepcopy(old.metrics), list(old.notes), old.quality_status)
    unapproved = await run_source(source, "1.0.1")
    assert unapproved.quality_status == "GOOD"
    assert unapproved.governed_model_version_id is None
    # Fixture-only separate APPROVED contract. No production governance command.
    approved = await add_governed_version(context, model, 3, "1.0.1")
    new = await run_source(source, "1.0.1")
    assert new.model_version == "1.0.1"
    assert new.status == "COMPLETED"
    assert new.quality_status == "GOOD"
    assert new.governed_model_version_id == approved.id
    assert new.governed_model_version_id != old_definition.id
    assert new.input_hash != old.input_hash
    assert new.metrics == old.metrics
    old_snapshot = await source.service._repo.list_snapshot(old.id)
    new_snapshot = await source.service._repo.list_snapshot(new.id)
    old_rows = tuple(source.service._snapshot_to_domain(row) for row in old_snapshot)
    new_rows = tuple(source.service._snapshot_to_domain(row) for row in new_snapshot)
    assert old_rows == new_rows
    assert all(row.quality_status == "VALID" and row.warnings == () for row in new_rows)
    expected_hash = calculate_input_hash(MODEL_ID, "1.0.1", AnalysisParameters(), new_rows)
    assert new.input_hash == expected_hash
    for run in (old, unapproved, new):
        result = await source.service.verify_reproducibility(
            context.workspace, source.analysis.id, run.version
        )
        assert all(result.values())
    await context.session.refresh(old)
    assert (old.input_hash, old.metrics, old.notes, old.quality_status) == old_facts
    await context.session.refresh(corrected)
    assert corrected.status == "DRAFT"
    # Multiple exact approved contracts are ambiguous, never latest-wins.
    await add_governed_version(context, model, 4, "1.0.1")
    ambiguous = await run_source(source, "1.0.1")
    assert ambiguous.governed_model_version_id is None
    before = await context.session.scalar(
        select(func.count())
        .select_from(MarketAnalysisRunModel)
        .where(MarketAnalysisRunModel.analysis_id == source.analysis.id)
    )
    with pytest.raises(AnalysisConflict, match="not available"):
        await run_source(source, "latest")
    after = await context.session.scalar(
        select(func.count())
        .select_from(MarketAnalysisRunModel)
        .where(MarketAnalysisRunModel.analysis_id == source.analysis.id)
    )
    assert before == after == 4


@pytest.mark.asyncio
@pytest.mark.parametrize("owner", ["listing", "reference"])
@pytest.mark.parametrize("version", ["1.0.0", "1.0.1"])
async def test_native_retry_cannot_upgrade_or_replace_source_snapshot(
    isolated_analysis_context, owner, version
):
    context = isolated_analysis_context
    source = await create_source(context, owner, count=1)
    original = await run_source(source, version)
    assert original.status == "NOT_EVALUABLE"
    original_facts = (original.status, original.input_hash, list(original.notes))
    source.service._market_data.list_daily_prices = AsyncMock(
        side_effect=AssertionError("Retry may not read current prices")
    )
    replacement = await source.service.retry(
        context.workspace, source.analysis.id, original.version, "synthetic-retry", None
    )
    assert replacement.id != original.id
    assert replacement.version == original.version + 1
    assert replacement.model_version == version
    assert replacement.input_hash == original.input_hash
    assert replacement.quality_status == "INSUFFICIENT"
    assert (original.status, original.input_hash, original.notes) == original_facts
    verification = await source.service.verify_reproducibility(
        context.workspace, source.analysis.id, replacement.version
    )
    assert all(verification.values())
    source.service._market_data.list_daily_prices.assert_not_awaited()
    events = await source.service.events(context.workspace, source.analysis.id)
    superseded = [event for event in events if event.event_type == "SUPERSEDED"]
    assert len(superseded) == 1
    assert superseded[0].source_version == original.version
    assert superseded[0].replacement_version == replacement.version


@pytest.mark.asyncio
@pytest.mark.parametrize("owner", ["listing", "reference"])
@pytest.mark.parametrize("fault", ["warning", "quality", "stale"])
async def test_native_corrected_quality_retains_negative_evidence(
    isolated_analysis_context, owner, fault
):
    context = isolated_analysis_context
    if fault == "stale":
        context.now -= timedelta(days=30)
    source = await create_source(
        context,
        owner,
        warning="synthetic negative quality case" if fault == "warning" else "",
        quality=PriceQuality.SUSPICIOUS if fault == "quality" else PriceQuality.VALID,
    )
    run = await run_source(source, "1.0.1")
    assert run.quality_status == "LIMITED"
    assert run.status == "COMPLETED_WITH_WARNINGS"
    assert run.notes
    expected = {
        "warning": "source warning",
        "quality": "SUSPICIOUS",
        "stale": "maximum_data_age",
    }
    assert any(expected[fault] in note for note in run.notes)
    result = await source.service.verify_reproducibility(
        context.workspace, source.analysis.id, run.version
    )
    assert all(result.values())


@pytest.mark.asyncio
async def test_native_http_explicit_version_and_invalid_selection_no_partial_run(
    isolated_analysis_context, monkeypatch
):
    context = isolated_analysis_context
    source = await create_source(context, "listing")
    # Reuse the real route and owner, with this UUID workspace and real session.
    monkeypatch.setattr(analysis_router, "WORKSPACE_ID", context.workspace)
    app = FastAPI()
    app.include_router(analysis_router.router)
    app.dependency_overrides[get_market_analysis_service] = lambda: source.service
    transport = ASGITransport(app=app)
    path = f"/api/v1/market-analyses/{source.analysis.id}/runs"
    body = {
        "start_date": source.days[0].isoformat(),
        "end_date": source.days[-1].isoformat(),
    }
    async with AsyncClient(transport=transport, base_url="http://test.invalid") as client:
        legacy = await client.post(path, json=body)
        assert legacy.status_code == 201
        assert legacy.json()["model_version"] == "1.0.0"
        assert legacy.json()["quality_status"] == "LIMITED"
        corrected = await client.post(path, json={**body, "model_version": "1.0.1"})
        assert corrected.status_code == 201
        assert corrected.json()["model_version"] == "1.0.1"
        assert corrected.json()["quality_status"] == "GOOD"
        invalid = await client.post(path, json={**body, "model_version": "latest"})
        assert invalid.status_code == 422
        versions = await source.service._repo.list_runs(source.analysis.id)
        assert len(versions) == 2
        for version in (1, 2):
            verified = await client.post(f"{path}/{version}/verify")
            assert verified.status_code == 200
            assert all(verified.json().values())
