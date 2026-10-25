"""Native FT-006 reference handoff is exact, read-only and never a listing fallback."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.features.candidate.service.live_workflow import CandidateLiveWorkflowService
from app.features.candidate.service.orchestration import StoredAnalysisReference
from app.features.candidate.service.source_resolution import (
    SemanticTopDownSourceResolver,
)

NOW = datetime(2026, 10, 25, 12, tzinfo=UTC)


def native_session():
    workspace, reference = uuid4(), uuid4()
    instrument = SimpleNamespace(
        id=uuid4(),
        workspace_id=workspace,
        market_reference_id=reference,
        listing_id=None,
        kind="MARKET_REFERENCE",
    )
    session = Mock()
    session.scalars = AsyncMock(return_value=Mock(all=Mock(return_value=[instrument])))
    session.scalar = AsyncMock(return_value=200)
    session.execute = AsyncMock()
    return session, workspace, reference, instrument


def completed_run(resolver):
    analysis = SimpleNamespace(id=uuid4())
    run = SimpleNamespace(id=uuid4(), version=3, observation_count=200)
    resolver._latest_completed = AsyncMock(return_value=(analysis, run))
    return analysis, run


def assert_read_only(session):
    for name in ("add", "add_all", "delete", "flush", "commit"):
        getattr(session, name).assert_not_called()


async def test_native_source_binds_exact_instrument_owner_snapshot_and_cutoff():
    session, workspace, reference, instrument = native_session()
    resolver = SemanticTopDownSourceResolver(session)
    analysis, run = completed_run(resolver)

    actual = await resolver.native_reference_source(workspace, reference, NOW)

    assert actual == StoredAnalysisReference(analysis.id, run.version)
    options = resolver._latest_completed.await_args.kwargs
    assert options["workspace_id"] == workspace
    assert options["cutoff"] == NOW
    predicate = options["predicate"].compile()
    assert instrument.id in predicate.params.values()
    assert "market_analyses.listing_id IS NULL" in str(predicate)
    assert "market_analyses.underlying_id IS NULL" in str(predicate)
    snapshot_query = session.scalar.await_args.args[0].compile()
    assert run.id in snapshot_query.params.values()
    assert_read_only(session)


@pytest.mark.parametrize("defect", ["workspace", "reference", "kind", "listing", "ambiguous"])
async def test_native_identity_errors_are_rejected_without_a_listing_guess(defect):
    session, workspace, reference, instrument = native_session()
    if defect == "workspace":
        instrument.workspace_id = uuid4()
    elif defect == "reference":
        instrument.market_reference_id = uuid4()
    elif defect == "kind":
        instrument.kind = "LISTING"
    elif defect == "listing":
        instrument.listing_id = uuid4()
    else:
        session.scalars.return_value.all.return_value = [instrument, instrument]
    resolver = SemanticTopDownSourceResolver(session)
    resolver._listing_for_reference = AsyncMock()

    with pytest.raises(ValueError, match="native market-reference instrument"):
        await resolver._source_for_reference(workspace, reference, NOW, "market")

    session.execute.assert_not_awaited()
    resolver._listing_for_reference.assert_not_awaited()
    assert_read_only(session)


@pytest.mark.parametrize("snapshot_count", [0, 199, 201])
async def test_incomplete_native_snapshot_cannot_select_a_legacy_bridge(snapshot_count):
    session, workspace, reference, _ = native_session()
    session.scalar.return_value = snapshot_count
    resolver = SemanticTopDownSourceResolver(session)
    completed_run(resolver)
    resolver._listing_for_reference = AsyncMock()

    with pytest.raises(ValueError, match="complete persisted snapshot"):
        await resolver._source_for_reference(workspace, reference, NOW, "market")

    resolver._listing_for_reference.assert_not_awaited()
    assert_read_only(session)


async def test_native_instrument_without_completed_run_does_not_fall_back():
    session, workspace, reference, _ = native_session()
    resolver = SemanticTopDownSourceResolver(session)
    resolver._latest_completed = AsyncMock(return_value=None)
    resolver._listing_for_reference = AsyncMock()

    with pytest.raises(ValueError, match="no completed native reference analysis"):
        await resolver._source_for_reference(workspace, reference, NOW, "market")

    resolver._listing_for_reference.assert_not_awaited()
    session.scalar.assert_not_awaited()
    assert_read_only(session)


async def test_absent_native_identity_retains_the_historized_listing_bridge():
    session, workspace, reference, _ = native_session()
    session.scalars.return_value.all.return_value = []
    resolver = SemanticTopDownSourceResolver(session)
    listing = uuid4()
    source = StoredAnalysisReference(uuid4(), 2)
    resolver._listing_for_reference = AsyncMock(return_value=listing)
    resolver._latest_completed_for_listing = AsyncMock(return_value=source)

    assert await resolver._source_for_reference(workspace, reference, NOW, "sector") == source
    resolver._listing_for_reference.assert_awaited_once_with(
        workspace, reference, NOW.date(), "sector"
    )
    resolver._latest_completed_for_listing.assert_awaited_once_with(
        workspace, listing, NOW, "sector"
    )
    assert_read_only(session)


@pytest.mark.parametrize("available", [True, False])
async def test_reference_readiness_uses_the_same_native_source_without_provider_actions(
    monkeypatch, available
):
    session, workspace, reference_id, _ = native_session()
    source = StoredAnalysisReference(uuid4(), 4)
    lookup = AsyncMock(return_value=source)
    if not available:
        lookup.side_effect = ValueError("no complete persisted snapshot")
    monkeypatch.setattr(SemanticTopDownSourceResolver, "native_reference_source", lookup)
    service = CandidateLiveWorkflowService(session)
    service._one_active = AsyncMock()
    service._append_listing_pipeline = AsyncMock()
    reference = SimpleNamespace(id=reference_id, code="SYNTHETIC-NATIVE")
    steps = []

    await service._append_reference_pipeline(steps, workspace, NOW.date(), NOW, reference, "MARKET")

    lookup.assert_awaited_once_with(workspace, reference_id, NOW)
    service._one_active.assert_not_awaited()
    service._append_listing_pipeline.assert_not_awaited()
    analysis = next(step for step in steps if step.code == "MARKET_ANALYSIS")
    assert analysis.status == ("COMPLETE" if available else "BLOCKED")
    assert analysis.resource_id == (source.analysis_id if available else reference_id)
    assert all(step.action is None for step in steps)
    assert_read_only(session)
