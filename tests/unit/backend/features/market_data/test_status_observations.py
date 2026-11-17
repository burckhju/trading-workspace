"""Independent status ingestion through real disposable SQL and existing adapters."""

from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from tests.unit.backend.features.market_data import test_retained_quotes as retained
from tests.unit.backend.features.market_data.test_original_market_status_retention import (
    configured_adapter,
)
from tests.unit.backend.features.market_data.test_original_quote_retention import runtime

from app.features.market_data.domain.enums import MarketDataProvider, QualityStatus
from app.features.market_data.domain.models import WarrantQuoteSnapshot
from app.features.market_data.domain.original_market_status_evidence import (
    OriginalMarketStatusEvidence,
)
from app.features.market_data.domain.status_observations import StatusRouteBinding
from app.features.market_data.persistence.models import (
    WarrantMarketStatusObservationModel,
    WarrantProviderMappingModel,
    WarrantQuoteObservationModel,
    WarrantQuoteSampleModel,
)
from app.features.market_data.persistence.quote_identity import read_quote_identity
from app.features.market_data.service.errors import MarketDataInvalidResponseError
from app.features.market_data.service.status_observations import MarketStatusReader
from app.providers.frankfurt_quotes.schema import FrankfurtSnapshot

context = retained.context
NOW = retained.NOW
PROVIDER = MarketDataProvider.FRANKFURT_QUOTES


def status_result(c, status, at, *, retrieved=None, reference="synthetic-status-source"):
    received = retrieved or at
    original = OriginalMarketStatusEvidence(
        version="original-market-status-evidence-v1",
        source_contract="synthetic-status-only-v1",
        source_reference=reference,
        generated_at=at,
        isin=retained.ISIN,
        venue_mic="XFRA",
        status=status,
        original_status_text=status,
        source_status_field="instrument_state",
        observed_at=at,
        original_time_text=at.isoformat(),
        source_time_field="instrument_state_time",
    )
    quote = WarrantQuoteSnapshot(
        warrant_listing_id=c.request.warrant_listing_id,
        bid=None,
        ask=None,
        currency="EUR",
        provider_symbol=retained.ISIN,
        provider_exchange_code="XSC",
        observed_at=None,
        isin=retained.ISIN,
        venue_mic="XFRA",
        trading_status=status,
        original_market_status=original,
    )
    return replace(
        c.result, data=quote, retrieved_at=received, quality_status=QualityStatus.INCOMPLETE
    )


async def deliver(c, result, captured_at):
    c.provider.get_warrant_listing_quote.side_effect = None
    c.provider.get_warrant_listing_quote.return_value = result
    c.request = replace(c.request, as_of=captured_at, correlation_id=uuid4())
    with pytest.raises(MarketDataInvalidResponseError, match="WARRANT_QUOTE_NOT_VALIDATED"):
        await runtime(c, captured_at).get_warrant_listing_quote(c.request)


async def report(c, event_at, known_at, **kwargs):
    async with c.database.session_context() as session:
        identity = await read_quote_identity(session, c.request, PROVIDER)
        route = StatusRouteBinding(
            c.request.workspace_id,
            c.warrant,
            c.request.warrant_listing_id,
            PROVIDER.value,
            identity.key,
            identity.isin,
            identity.mic,
        )
        return await MarketStatusReader(session).read(
            route=route, event_at=event_at, known_at=known_at, **kwargs
        )


def status_rows(c):
    with Session(c.database.engine) as session:
        return session.scalars(select(WarrantMarketStatusObservationModel)).all()


@pytest.mark.asyncio
async def test_actual_adapter_status_only_survives_price_fallback_and_same_sample_slot(context):
    c = context
    adapter, snapshots, payload = configured_adapter(c)
    first = await runtime(c, NOW, adapter).get_warrant_listing_quote(c.request)
    with Session(c.database.engine) as session:
        price_before = session.scalar(select(WarrantQuoteObservationModel)).payload
        sample_before = session.scalar(select(WarrantQuoteSampleModel)).payload
    later = NOW + timedelta(seconds=30)
    payload["generated_at"] = later.isoformat()
    payload["records"][0].update(
        bid=None, ask=None, trading_status="CLOSED", status_observed_at=later.isoformat()
    )
    adapter._clock = lambda: later
    snapshots.load.return_value = (FrankfurtSnapshot.model_validate(payload), later, False)
    fallback = await runtime(c, later, adapter).get_warrant_listing_quote(c.request)
    assert fallback.data.retained
    assert fallback.data.original_market_status == first.data.original_market_status
    evidence = await report(c, later, later)
    assert evidence.point_verdict == "OBSERVED_AT_INSTANT"
    assert evidence.observed_status == "CLOSED"
    assert evidence.latest_observations[0].original.status == "CLOSED"
    assert evidence.latest_capture.original.original_time_text == later.isoformat()
    assert evidence.source_qualification == "NOT_INDEPENDENTLY_VERIFIED"
    assert evidence.status_validity_interval == "NOT_ESTABLISHED"
    assert len(status_rows(c)) == 2
    with Session(c.database.engine) as session:
        assert session.scalar(select(WarrantQuoteObservationModel)).payload == price_before
        samples = session.scalars(select(WarrantQuoteSampleModel)).all()
        assert len(samples) == 1 and samples[0].payload == sample_before
    # Neither the prior OPEN nor the later CLOSED is extended to a new clock.
    next_read = await report(
        c, later + timedelta(microseconds=1), later + timedelta(microseconds=1)
    )
    assert next_read.point_verdict == "NO_POINT_AT_EVENT"
    assert next_read.observed_status is None
    assert next_read.latest_observations[0].original.status == "CLOSED"


@pytest.mark.asyncio
async def test_duplicates_restart_late_observations_and_known_at_preserve_source_order(context):
    c = context
    first = status_result(c, "OPEN", NOW)
    await deliver(c, first, NOW)
    await deliver(
        c, replace(first, retrieved_at=NOW + timedelta(seconds=1)), NOW + timedelta(seconds=1)
    )
    assert len(status_rows(c)) == 1
    later = NOW + timedelta(minutes=1)
    await deliver(c, status_result(c, "SUSPENDED", later), later)
    # A late source point arrives after the newer SUSPENDED source observation.
    historical = NOW + timedelta(seconds=30)
    known = later + timedelta(seconds=1)
    await deliver(c, status_result(c, "OPEN", historical, retrieved=known), known)
    c.database.engine.dispose()
    c.database = retained.SqlDatabase(c.url)
    read = await report(c, historical, known)
    assert read.observed_status == "OPEN"
    assert read.latest_observations[0].original.status == "SUSPENDED"
    assert read.latest_observations[0].original.observed_at == later
    assert read.latest_capture.original.observed_at == historical
    previous_knowledge = await report(c, historical, later)
    assert previous_knowledge.point_verdict == "NO_POINT_AT_EVENT"
    assert previous_knowledge.latest_observations[0].original.status == "SUSPENDED"
    assert len(status_rows(c)) == 3


@pytest.mark.asyncio
async def test_same_instant_conflict_is_not_last_writer_wins_and_source_filter_is_exact(context):
    c = context
    await deliver(c, status_result(c, "OPEN", NOW), NOW)
    later = NOW + timedelta(seconds=1)
    await deliver(c, status_result(c, "CLOSED", NOW, retrieved=later), later)
    conflict = await report(c, NOW, later)
    assert conflict.point_verdict == "CONFLICTING_POINTS"
    assert conflict.observed_status is None
    assert {item.original.status for item in conflict.latest_observations} == {"OPEN", "CLOSED"}
    switched = status_result(c, "SUSPENDED", NOW, retrieved=later, reference="different-source")
    await deliver(c, switched, later)
    selected = await report(c, NOW, later, source_reference="different-source")
    assert selected.observed_status == "SUSPENDED"
    assert {item.source_reference for item in selected.source_history} == {
        "synthetic-status-source",
        "different-source",
    }
    absent = await report(c, NOW, later, source_reference="never-observed-source")
    assert absent.point_verdict == "NO_POINT_AT_EVENT"
    assert not absent.latest_observations


@pytest.mark.asyncio
async def test_transport_gap_is_not_closed_and_never_reconfirms_previous_open(context):
    c = context
    await deliver(c, status_result(c, "OPEN", NOW), NOW)
    later = NOW + timedelta(seconds=1)
    c.provider.get_warrant_listing_quote.side_effect = TimeoutError("never persist secret URL")
    c.request = replace(c.request, correlation_id=uuid4(), as_of=later)
    with pytest.raises(MarketDataInvalidResponseError):
        await runtime(c, later).get_warrant_listing_quote(c.request)
    # Retrying the same logical request cannot create another gap fact.
    with pytest.raises(MarketDataInvalidResponseError):
        await runtime(c, later).get_warrant_listing_quote(c.request)
    read = await report(c, later, later)
    assert read.point_verdict == "NO_POINT_AT_EVENT"
    assert read.latest_capture.kind == "GAP"
    assert read.latest_gap.reason == "TimeoutError"
    assert read.latest_gap.original is None
    assert read.latest_observations[0].original.status == "OPEN"
    assert len(status_rows(c)) == 2
    assert "secret" not in repr(status_rows(c))


@pytest.mark.asyncio
async def test_route_revision_never_reuses_old_status_and_history_remains(context):
    c = context
    await deliver(c, status_result(c, "OPEN", NOW), NOW)
    original = (await report(c, NOW, NOW)).route
    with Session(c.database.engine) as session:
        row = session.get(WarrantProviderMappingModel, c.mapping)
        row.version += 1
        session.commit()
    later = NOW + timedelta(seconds=1)
    changed = await report(c, NOW, later)
    assert changed.route.identity_key != original.identity_key
    assert changed.other_route_keys == (original.identity_key,)
    assert changed.source_history[0].route == original
    assert changed.point_verdict == "NO_POINT_AT_EVENT"
    await deliver(c, status_result(c, "OPEN", later), later)
    changed = await report(c, later, later)
    assert changed.observed_status == "OPEN"
    assert len(status_rows(c)) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid", ["time", "route", "retained", "refresh_error"])
async def test_invalid_source_fact_becomes_gap_without_using_price_quality(context, invalid):
    c = context
    candidate = status_result(c, "OPEN", NOW)
    if invalid == "time":
        candidate = replace(candidate, retrieved_at=NOW + timedelta(seconds=1))
    elif invalid == "route":
        candidate = replace(candidate, data=replace(candidate.data, provider_exchange_code="OTHER"))
    elif invalid == "retained":
        candidate = replace(candidate, data=replace(candidate.data, retained=True))
    else:
        candidate = replace(candidate, data=replace(candidate.data, refresh_error="SYNTHETIC"))
    c.provider.get_warrant_listing_quote.return_value = candidate
    with pytest.raises(MarketDataInvalidResponseError):
        await runtime(c, NOW).get_warrant_listing_quote(c.request)
    read = await report(c, NOW, NOW)
    assert read.point_verdict == "NO_POINT_AT_EVENT"
    assert read.latest_capture.kind == "GAP"
    assert read.latest_gap is not None


@pytest.mark.asyncio
async def test_crossed_prices_do_not_erase_separately_valid_status_and_read_does_not_flush(context):
    c = context
    adapter, snapshots, payload = configured_adapter(c)
    payload["records"][0].update(bid="3", ask="2", status_observed_at=NOW.isoformat())
    snapshots.load.return_value = (FrankfurtSnapshot.model_validate(payload), NOW, False)
    observation = await adapter.get_warrant_listing_quote(c.request)
    assert observation.quality_status is QualityStatus.INCOMPLETE
    assert observation.data.original_market_status.status == "OPEN"
    assert observation.data.bid is observation.data.ask is observation.data.observed_at is None
    with pytest.raises(MarketDataInvalidResponseError):
        await runtime(c, NOW, adapter).get_warrant_listing_quote(c.request)
    async with c.database.session_context() as session:
        identity = await read_quote_identity(session, c.request, PROVIDER)
        route = StatusRouteBinding(
            c.request.workspace_id,
            c.warrant,
            c.request.warrant_listing_id,
            PROVIDER.value,
            identity.key,
            identity.isin,
            identity.mic,
        )
        pending = WarrantQuoteObservationModel(
            workspace_id=c.request.workspace_id,
            warrant_listing_id=c.request.warrant_listing_id,
            provider="invalid-unflushed-test",
            identity_key=identity.key,
            payload={},
        )
        session.add(pending)
        read = await MarketStatusReader(session).read(route=route, event_at=NOW, known_at=NOW)
        assert read.observed_status == "OPEN"
        assert pending in session.session.new
    with Session(c.database.engine) as session:
        assert session.scalar(select(WarrantQuoteObservationModel)) is None


@pytest.mark.asyncio
async def test_future_event_is_not_a_permitted_status_query(context):
    c = context
    with pytest.raises(ValueError, match="STATUS_EVENT_AFTER_KNOWN_AT"):
        await report(c, NOW + timedelta(microseconds=1), NOW)


@pytest.mark.asyncio
async def test_corrupt_stored_time_binding_is_read_failure_not_positive_status(context):
    c = context
    await deliver(c, status_result(c, "OPEN", NOW), NOW)
    with Session(c.database.engine) as session:
        # Damage only this disposable SQLite copy; PostgreSQL rejects UPDATE
        # through the append-only trigger covered in the integration test.
        session.execute(
            update(WarrantMarketStatusObservationModel).values(source_contract="other-contract")
        )
        session.commit()
    with pytest.raises(ValueError, match="ORIGINAL_MARKET_STATUS_STORED_BINDING_INVALID"):
        await report(c, NOW, NOW)
