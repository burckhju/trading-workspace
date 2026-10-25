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
from sqlalchemy import event, select, text
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
from app.features.learning.persistence.models import LearningEvidenceModel
from app.features.market.api.dependencies import get_market_reference_analysis_service
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
from app.features.model.domain.enums import ValidationConclusion
from app.features.model.persistence.models import ModelVersionRecord
from app.features.model.service.application import ModelGovernanceService

analysis_router = import_module("app.features.analysis.api.router")
reference_router = import_module("app.features.market.api.reference_market_data_router")


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


async def create_source(
    context,
    owner,
    *,
    count=220,
    warning="",
    quality=PriceQuality.VALID,
    missing_adjusted=False,
):
    session, workspace, now = context.session, context.workspace, context.now
    # Match the canonical provider code produced by the regular TC-001 owner.
    # The legacy listing reader normalizes codes; 1.0.1 preserves stored text.
    symbol = f"SYNTHETIC-FT006-{uuid4().hex[:12].upper()}"
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
            role="BROAD_MARKET",
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
                adjusted_close=None if missing_adjusted and index == 0 else price,
                volume=Decimal(1000),
                currency="EUR",
                provider=MarketDataProvider.EODHD,
                provider_symbol=symbol,
                retrieved_at=now,
                source_updated_at=None,
                quality_status=quality if index == 0 else PriceQuality.VALID,
                warnings=warning if index == 0 else "",
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


async def create_governed_model(
    context,
    version,
    *,
    workspace=None,
    model_key=MODEL_ID,
    overrides=None,
    approved=True,
):
    definition = governed_runtime_definition(model_id=MODEL_ID, model_version=version)
    assert definition is not None
    definition = {**definition, **(overrides or {})}
    workspace = context.workspace if workspace is None else workspace
    actor = uuid4()
    governance = ModelGovernanceService(context.session)
    model, baseline = await governance.create_model(
        workspace_id=workspace,
        model_key=model_key,
        name="SYNTHETIC FT006 provenance",
        purpose="Rollback-only exact runtime binding qualification",
        initial_definition=definition,
        actor=actor,
    )
    if approved:
        await governance.approve_initial_version(
            workspace_id=workspace,
            model_id=model.id,
            version_id=baseline.id,
            actor=actor,
            correlation_id="synthetic-ft006-baseline",
        )
    return model, baseline


async def approve_successor(context, model, base, version):
    definition = governed_runtime_definition(model_id=MODEL_ID, model_version=version)
    assert definition is not None
    actor, evidence_id = uuid4(), uuid4()
    # This minimal evidence anchor isolates the provenance listener boundary.
    # The B07 browser journey separately creates full owner-produced evidence.
    context.session.add(
        LearningEvidenceModel(
            id=evidence_id,
            workspace_id=context.workspace,
            evidence_type="FT011",
            created_at=context.now,
        )
    )
    await context.session.flush()
    governance = ModelGovernanceService(context.session)
    hypothesis = await governance.create_hypothesis(
        workspace_id=context.workspace,
        title="Synthetic FT006 exact runtime provenance",
        statement="Exercise immutable runtime binding, without an economic claim.",
        evidence_ids=(evidence_id,),
        source_lesson_version_id=None,
        actor=actor,
    )
    proposal = await governance.create_proposal(
        workspace_id=context.workspace,
        model_id=model.id,
        base_model_version_id=base.id,
        hypothesis_id=hypothesis.id,
        proposed_definition=definition,
        rationale="Synthetic provenance boundary qualification only",
        actor=actor,
    )
    await governance.validate_proposal(
        workspace_id=context.workspace,
        proposal_id=proposal.id,
        evidence_ids=(evidence_id,),
        evidence_cutoff_at=context.now,
        conclusion=ValidationConclusion.SUPPORTS,
        metrics={"synthetic_evidence_count": 1},
        notes="No model activation, production approval or B07 claim",
        actor=actor,
    )
    successor, _ = await governance.approve_proposal(
        workspace_id=context.workspace,
        proposal_id=proposal.id,
        actor=actor,
        correlation_id="synthetic-ft006-successor",
    )
    return successor


async def persisted_facts(session, *, governance_only=False):
    tables = [
        "governed_models",
        "governed_model_versions",
        "model_approvals",
        "model_runtime_activations",
    ]
    if not governance_only:
        tables += [
            "market_analyses",
            "market_analysis_runs",
            "market_analysis_snapshot_rows",
            "market_analysis_criterion_results",
            "market_analysis_events",
        ]
    return {
        table: await session.scalar(
            text(
                "SELECT COALESCE(jsonb_agg(to_jsonb(fact) ORDER BY to_jsonb(fact)::text), "
                f"'[]'::jsonb)::text FROM {table} AS fact"
            )
        )
        for table in tables
    }


async def run_facts(service, run):
    return {
        "run": deepcopy(
            {
                column.name: getattr(run, column.name)
                for column in MarketAnalysisRunModel.__table__.columns
            }
        ),
        "snapshot": tuple(
            service._snapshot_to_domain(row).canonical()
            for row in await service._repo.list_snapshot(run.id)
        ),
        "criteria": tuple(
            (row.code, row.classification, row.value, row.explanation)
            for row in await service._repo.list_criteria(run.id)
        ),
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("owner", ["listing", "reference"])
async def test_both_native_owners_preserve_history_and_exact_governed_contract(
    isolated_analysis_context, owner
):
    context = isolated_analysis_context
    source = await create_source(context, owner)
    model, old_definition = await create_governed_model(context, "1.0.0")
    old = await run_source(source, "1.0.0")
    assert old.model_version == "1.0.0"
    assert old.quality_status == "LIMITED"
    assert old.governed_model_version_id == old_definition.id
    old_facts = await run_facts(source.service, old)
    unapproved = await run_source(source, "1.0.1")
    assert unapproved.quality_status == "GOOD"
    assert unapproved.governed_model_version_id is None
    approved = await approve_successor(context, model, old_definition, "1.0.1")
    governance_facts = await persisted_facts(context.session, governance_only=True)
    new = await run_source(source)
    assert new.model_version == "1.0.1"
    assert new.status == "COMPLETED"
    assert new.quality_status == "GOOD"
    assert new.governed_model_version_id == approved.id
    assert new.governed_model_version_id != old_definition.id
    assert new.input_hash != old.input_hash
    assert new.metrics == old.metrics
    assert (await run_facts(source.service, new))["criteria"] == old_facts["criteria"]
    old_snapshot = await source.service._repo.list_snapshot(old.id)
    new_snapshot = await source.service._repo.list_snapshot(new.id)
    old_rows = tuple(source.service._snapshot_to_domain(row) for row in old_snapshot)
    new_rows = tuple(source.service._snapshot_to_domain(row) for row in new_snapshot)
    assert old_rows == new_rows
    assert all(row.quality_status == "VALID" and row.warnings == () for row in new_rows)
    expected_hash = calculate_input_hash(MODEL_ID, "1.0.1", AnalysisParameters(), new_rows)
    assert new.input_hash == expected_hash
    # A subsequent provider correction changes the current price, not old snapshots.
    current_price = await context.session.scalar(
        select(DailyPriceModel).where(
            DailyPriceModel.workspace_id == context.workspace,
            DailyPriceModel.market_data_instrument_id == source.analysis.market_data_instrument_id,
            DailyPriceModel.trading_date == source.days[-1],
        )
    )
    assert current_price is not None
    current_price.adjusted_close += Decimal("1")
    current_price.updated_at = datetime.now(UTC)
    await context.session.commit()
    before_verify = await persisted_facts(context.session)
    for run in (old, unapproved, new):
        result = await source.service.verify_reproducibility(
            context.workspace, source.analysis.id, run.version
        )
        assert all(result.values())
    assert await persisted_facts(context.session) == before_verify
    assert await persisted_facts(context.session, governance_only=True) == governance_facts
    await context.session.refresh(old)
    assert await run_facts(source.service, old) == old_facts
    await context.session.refresh(unapproved)
    assert unapproved.governed_model_version_id is None
    before = await persisted_facts(context.session)
    with pytest.raises(AnalysisConflict, match="not available"):
        await run_source(source, "latest")
    assert await persisted_facts(context.session) == before


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
    original_facts = await run_facts(source.service, original)
    source.service._market_data.list_daily_prices = AsyncMock(
        side_effect=AssertionError("Retry may not read current prices")
    )
    source.service._market_data.list_snapshot_rows = AsyncMock(
        side_effect=AssertionError("Retry may not read current prices")
    )

    def reject_price_selects(_connection, _cursor, statement, _parameters, _context, _many):
        assert "daily_prices" not in statement.lower(), "Retry must use only saved snapshots"

    connection = context.session.bind.sync_connection
    event.listen(connection, "before_cursor_execute", reject_price_selects)
    try:
        replacement = await source.service.retry(
            context.workspace, source.analysis.id, original.version, "synthetic-retry", None
        )
    finally:
        event.remove(connection, "before_cursor_execute", reject_price_selects)
    assert replacement.id != original.id
    assert replacement.version == original.version + 1
    assert replacement.model_version == version
    assert replacement.input_hash == original.input_hash
    assert replacement.quality_status == "INSUFFICIENT"
    assert await run_facts(source.service, original) == original_facts
    replacement_facts = await run_facts(source.service, replacement)
    assert replacement_facts["snapshot"] == original_facts["snapshot"]
    assert replacement.parameters == original.parameters
    verification = await source.service.verify_reproducibility(
        context.workspace, source.analysis.id, replacement.version
    )
    assert all(verification.values())
    source.service._market_data.list_daily_prices.assert_not_awaited()
    source.service._market_data.list_snapshot_rows.assert_not_awaited()
    events = await source.service.events(context.workspace, source.analysis.id)
    superseded = [event for event in events if event.event_type == "SUPERSEDED"]
    assert len(superseded) == 1
    assert superseded[0].source_version == original.version
    assert superseded[0].replacement_version == replacement.version


@pytest.mark.asyncio
@pytest.mark.parametrize("owner", ["listing", "reference"])
@pytest.mark.parametrize(
    "fault", ["warning", "suspicious", "incomplete", "adjusted_close", "stale"]
)
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
        quality={
            "suspicious": PriceQuality.SUSPICIOUS,
            "incomplete": PriceQuality.INCOMPLETE,
        }.get(fault, PriceQuality.VALID),
        missing_adjusted=fault == "adjusted_close",
    )
    run = await run_source(source, "1.0.1")
    assert run.quality_status == "LIMITED"
    assert run.status == "COMPLETED_WITH_WARNINGS"
    assert run.notes
    expected = {
        "warning": "source warning",
        "suspicious": "SUSPICIOUS",
        "incomplete": "INCOMPLETE",
        "adjusted_close": "missing",
        "stale": "maximum_data_age",
    }
    assert any(expected[fault] in note for note in run.notes)
    result = await source.service.verify_reproducibility(
        context.workspace, source.analysis.id, run.version
    )
    assert all(result.values())


@pytest.mark.asyncio
@pytest.mark.parametrize("owner", ["listing", "reference"])
async def test_native_http_explicit_version_and_invalid_selection_no_partial_run(
    isolated_analysis_context, monkeypatch, owner
):
    context = isolated_analysis_context
    source = await create_source(context, owner)
    # Reuse the real route and owner, with this UUID workspace and real session.
    monkeypatch.setattr(analysis_router, "WORKSPACE_ID", context.workspace)
    monkeypatch.setattr(reference_router, "WORKSPACE_ID", context.workspace)
    app = FastAPI()
    app.include_router(analysis_router.router)
    app.include_router(reference_router.router)
    app.dependency_overrides[get_market_analysis_service] = lambda: source.service
    app.dependency_overrides[get_market_reference_analysis_service] = lambda: source.service
    transport = ASGITransport(app=app)
    history_path = f"/api/v1/market-analyses/{source.analysis.id}/runs"
    path = (
        f"/api/v1/top-down-reference-data/market-reference-analyses/{source.analysis.id}/runs"
        if owner == "reference"
        else history_path
    )
    body = {
        "start_date": source.days[0].isoformat(),
        "end_date": source.days[-1].isoformat(),
    }
    async with AsyncClient(transport=transport, base_url="http://test.invalid") as client:
        legacy = await client.post(path, json={**body, "model_version": "1.0.0"})
        assert legacy.status_code == 201
        assert legacy.json()["model_version"] == "1.0.0"
        assert legacy.json()["quality_status"] == "LIMITED"
        corrected = await client.post(path, json=body)
        assert corrected.status_code == 201
        assert corrected.json()["model_version"] == "1.0.1"
        assert corrected.json()["quality_status"] == "GOOD"
        before_rejection = await persisted_facts(context.session)
        invalid = await client.post(path, json={**body, "model_version": "latest"})
        assert invalid.status_code == 422
        assert await persisted_facts(context.session) == before_rejection
        versions = await source.service._repo.list_runs(source.analysis.id)
        assert len(versions) == 2
        for version in (1, 2):
            details = await client.get(f"{history_path}/{version}")
            assert details.status_code == 200
            value = details.json()
            assert value["analysis"]["market_data_instrument_id"] == str(
                source.analysis.market_data_instrument_id
            )
            assert value["analysis"]["listing_id"] == (
                None if owner == "reference" else str(source.analysis.listing_id)
            )
            assert value["analysis"]["underlying_id"] == (
                None if owner == "reference" else str(source.analysis.underlying_id)
            )
            assert all(row["quality_status"] == "VALID" for row in value["snapshot"])
            verified = await client.post(f"{history_path}/{version}/verify")
            assert verified.status_code == 200
            assert all(verified.json().values())


@pytest.mark.asyncio
@pytest.mark.parametrize("version", ["1.0.0", "1.0.1"])
@pytest.mark.parametrize(
    "boundary", ["absent", "draft", "workspace", "model_key", "implementation"]
)
async def test_native_provenance_requires_exact_approved_workspace_contract(
    isolated_analysis_context, version, boundary
):
    context = isolated_analysis_context
    source = await create_source(context, "listing")
    baseline = None
    if boundary != "absent":
        workspace = context.workspace
        if boundary == "workspace":
            workspace = uuid4()
            context.session.add(
                WorkspaceModel(
                    id=workspace,
                    name=f"SYNTHETIC foreign FT006 workspace {workspace}",
                    created_at=context.now,
                )
            )
            await context.session.flush()
        _, baseline = await create_governed_model(
            context,
            version,
            workspace=workspace,
            model_key="OTHER_SYNTHETIC_MODEL" if boundary == "model_key" else MODEL_ID,
            overrides=(
                {"implementation_ref": "synthetic/nonmatching-artifact"}
                if boundary == "implementation"
                else None
            ),
            approved=boundary != "draft",
        )
    before = await persisted_facts(context.session, governance_only=True)
    run = await run_source(source, version)
    assert (run.model_id, run.model_version) == (MODEL_ID, version)
    assert run.governed_model_version_id is None
    verification = await source.service.verify_reproducibility(
        context.workspace, source.analysis.id, run.version
    )
    assert all(verification.values())
    assert await persisted_facts(context.session, governance_only=True) == before
    if boundary == "draft":
        stored = await context.session.get(ModelVersionRecord, baseline.id)
        assert stored is not None and stored.status == "DRAFT"


@pytest.mark.asyncio
@pytest.mark.parametrize("version", ["1.0.0", "1.0.1"])
async def test_native_provenance_ambiguity_is_not_latest_wins_or_a_backfill(
    isolated_analysis_context, version
):
    context = isolated_analysis_context
    source = await create_source(context, "reference")
    unbound = await run_source(source, version)
    assert unbound.governed_model_version_id is None
    unbound_facts = await run_facts(source.service, unbound)
    model, first = await create_governed_model(context, version)
    bound = await run_source(source, version)
    assert bound.governed_model_version_id == first.id
    bound_facts = await run_facts(source.service, bound)
    second = await approve_successor(context, model, first, version)
    assert second.id != first.id
    before = await persisted_facts(context.session, governance_only=True)
    ambiguous = await run_source(source, version)
    assert ambiguous.governed_model_version_id is None
    for run in (unbound, bound, ambiguous):
        result = await source.service.verify_reproducibility(
            context.workspace, source.analysis.id, run.version
        )
        assert all(result.values())
    assert await persisted_facts(context.session, governance_only=True) == before
    await context.session.refresh(unbound)
    await context.session.refresh(bound)
    assert await run_facts(source.service, unbound) == unbound_facts
    assert await run_facts(source.service, bound) == bound_facts


@pytest.mark.asyncio
@pytest.mark.parametrize("owner", ["listing", "reference"])
@pytest.mark.parametrize(
    "warning,expected",
    [
        ("", ()),
        ("\n", ("", "")),
        (" ", (" ",)),
        (
            " first source warning \n\nlast warning\n",
            (" first source warning ", "", "last warning", ""),
        ),
    ],
)
async def test_native_warning_transport_preserves_entries_and_empty_separator_diagnostics(
    isolated_analysis_context, owner, warning, expected
):
    context = isolated_analysis_context
    source = await create_source(context, owner, warning=warning)
    run = await run_source(source, "1.0.1")
    snapshot = await source.service._repo.list_snapshot(run.id)
    assert tuple(snapshot[0].warnings) == expected
    assert all(row.warnings == [] for row in snapshot[1:])
    assert run.quality_status == ("LIMITED" if expected else "GOOD")
    assert run.status == ("COMPLETED_WITH_WARNINGS" if expected else "COMPLETED")
    for entry in expected:
        assert f"{source.days[0].isoformat()}: source warning: {entry}" in run.notes
    persisted = await context.session.scalar(
        select(DailyPriceModel).where(
            DailyPriceModel.workspace_id == context.workspace,
            DailyPriceModel.market_data_instrument_id == source.analysis.market_data_instrument_id,
            DailyPriceModel.trading_date == source.days[0],
        )
    )
    assert persisted is not None and persisted.warnings == warning
    before = await persisted_facts(context.session)
    verified = await source.service.verify_reproducibility(
        context.workspace, source.analysis.id, run.version
    )
    assert all(verified.values())
    assert await persisted_facts(context.session) == before
