"""Real FT-006 reference runs feed the existing Candidate consumer without listings."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from tests.integration.backend.database import (
    test_ft006_versioned_quality_postgres as fixtures,
)
from tests.integration.backend.database.test_ft006_versioned_quality_postgres import (
    create_source,
    run_source,
)

from app.features.analysis.service.reference_application import (
    MarketReferenceAnalysisService,
)
from app.features.candidate.service.live_workflow import CandidateLiveWorkflowService
from app.features.candidate.service.orchestration import StoredAnalysisReference
from app.features.candidate.service.source_resolution import (
    SemanticTopDownSourceResolver,
)
from app.features.market.persistence.top_down_models import MarketReferenceModel
from app.features.market.service.top_down_administration import (
    TopDownReferenceAdministrationService,
)
from app.features.market_data.persistence.instruments import MarketDataInstrumentModel

isolated_analysis_context = fixtures.isolated_analysis_context


async def fingerprint(session):
    values = {}
    for table in (
        "market_analyses",
        "market_analysis_runs",
        "market_analysis_snapshot_rows",
        "market_analysis_criterion_results",
        "market_analysis_events",
        "market_data_instruments",
        "provider_instrument_mappings",
        "daily_prices",
    ):
        values[table] = await session.scalar(
            text(
                "SELECT md5(coalesce(jsonb_agg(to_jsonb(t) ORDER BY id)::text, '[]')) "
                f"FROM {table} t"
            )
        )
    return values


async def test_native_reference_lookup_preserves_exact_run_cutoff_and_read_only_facts(
    isolated_analysis_context,
):
    context = isolated_analysis_context
    source = await create_source(context, "reference")
    first = await run_source(source, "1.0.1")
    assert first.quality_status == "GOOD" and first.status == "COMPLETED"
    second = await run_source(source, "1.0.0")
    assert second.quality_status == "LIMITED"
    instrument = await context.session.get(
        MarketDataInstrumentModel, source.analysis.market_data_instrument_id
    )
    reference = await context.session.get(MarketReferenceModel, instrument.market_reference_id)
    assert source.analysis.listing_id is None and source.analysis.underlying_id is None
    assert instrument.listing_id is None and instrument.kind == "MARKET_REFERENCE"
    resolver = SemanticTopDownSourceResolver(context.session)
    before = await fingerprint(context.session)

    with pytest.raises(ValueError, match="no completed native reference analysis"):
        await resolver.native_reference_source(
            context.workspace,
            reference.id,
            first.analysis_time - timedelta(microseconds=1),
        )
    assert await resolver.native_reference_source(
        context.workspace, reference.id, first.analysis_time
    ) == StoredAnalysisReference(source.analysis.id, first.version)
    assert await resolver.native_reference_source(
        context.workspace, reference.id, datetime.now(UTC)
    ) == StoredAnalysisReference(source.analysis.id, second.version)
    with pytest.raises(ValueError, match="incompatible owner"):
        await resolver.native_reference_source(reference.id, reference.id, datetime.now(UTC))

    steps = []
    await CandidateLiveWorkflowService(context.session)._append_reference_pipeline(
        steps,
        context.workspace,
        first.analysis_time.date(),
        first.analysis_time,
        reference,
        "MARKET",
    )
    assert [step.status for step in steps] == ["COMPLETE", "COMPLETE"]
    assert steps[-1].resource_id == source.analysis.id
    assert f"v{first.version}" in steps[-1].detail
    assert all(step.action is None for step in steps)
    assert await fingerprint(context.session) == before


async def test_legacy_listing_bridge_is_preserved_only_when_native_identity_is_absent(
    isolated_analysis_context,
):
    context = isolated_analysis_context
    legacy = await create_source(context, "listing")
    run = await run_source(legacy, "1.0.0")
    admin = TopDownReferenceAdministrationService(context.session)
    reference = (await admin.bootstrap_v1(context.workspace)).market_references[0]
    await admin.assign_reference_listing(
        workspace_id=context.workspace,
        market_reference_id=reference.id,
        listing_id=legacy.analysis.listing_id,
        valid_from=context.now.date(),
        valid_to=None,
        source="SYNTHETIC legacy bridge compatibility",
        source_reference=None,
        quality_status="GOOD",
    )
    resolver = SemanticTopDownSourceResolver(context.session)
    assert await resolver._source_for_reference(
        context.workspace, reference.id, datetime.now(UTC), "market"
    ) == StoredAnalysisReference(legacy.analysis.id, run.version)

    await MarketReferenceAnalysisService(context.session).create_for_market_reference(
        workspace_id=context.workspace,
        market_reference_id=reference.id,
        actor="SYNTHETIC native source availability check",
    )
    before = await fingerprint(context.session)
    with pytest.raises(ValueError, match="no completed native reference analysis"):
        await resolver._source_for_reference(
            context.workspace, reference.id, datetime.now(UTC), "market"
        )
    steps = []
    cutoff = datetime.now(UTC)
    await CandidateLiveWorkflowService(context.session)._append_reference_pipeline(
        steps, context.workspace, cutoff.date(), cutoff, reference, "MARKET"
    )
    assert len(steps) == 1 and steps[0].status == "BLOCKED"
    assert await fingerprint(context.session) == before
