"""Real disposable SQL proves status points remain bounded by price retention."""

from copy import deepcopy
from datetime import timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from tests.unit.backend.features.market_data import (
    test_retained_quotes as retained_tests,
)
from tests.unit.backend.features.market_data.test_original_quote_retention import (
    runtime,
)
from tests.unit.backend.features.market_data.test_retained_quotes import (
    NOW,
    SqlDatabase,
)
from tests.unit.backend.providers.frankfurt_quotes.test_adapter_api import (
    context as adapter_context,
)
from tests.unit.backend.providers.frankfurt_quotes.test_schema import payload

from app.features.market_data.persistence.models import (
    WarrantProviderMappingModel,
    WarrantQuoteObservationModel,
    WarrantQuoteSampleModel,
)
from app.features.market_data.service.quote_history import QuoteHistoryReader
from app.providers.frankfurt_quotes.schema import FrankfurtSnapshot

context = retained_tests.context


def configured_adapter(c):
    with Session(c.database.engine) as session:
        session.get(WarrantProviderMappingModel, c.mapping).provider_exchange_code = "XFRA"
        session.commit()
    data = payload()
    data["generated_at"] = NOW.isoformat()
    data["records"][0].update(
        bid_at="2026-09-11T20:00:00+02:00",
        ask_at="2026-09-11T17:59:50Z",
        status_observed_at="2026-09-11T19:59:30+02:00",
    )
    adapter, _database, snapshots, _request, _row = adapter_context()
    adapter._database = c.database
    adapter._clock = lambda: NOW
    snapshots.load.return_value = (FrankfurtSnapshot.model_validate(data), NOW, False)
    return adapter, snapshots, data


@pytest.mark.asyncio
async def test_status_text_and_original_instant_survive_sql_retention_samples_and_restart(
    context,
):
    c = context
    adapter, snapshots, _data = configured_adapter(c)
    first = await runtime(c, NOW, adapter).get_warrant_listing_quote(c.request)
    original = first.data.original_market_status
    assert original.original_time_text == "2026-09-11T19:59:30+02:00"
    with Session(c.database.engine) as session:
        sample = session.scalar(select(WarrantQuoteSampleModel))
        sample_id, sample_fingerprint = sample.id, sample.quote_fingerprint
        original_sample = deepcopy(sample.payload)
        stored = session.scalar(select(WarrantQuoteObservationModel))
        assert (
            stored.payload["data"]["original_market_status"]
            == sample.payload["quote"]["original_market_status"]
        )
    c.database.engine.dispose()
    c.database = SqlDatabase(c.url)
    c.provider.get_warrant_listing_quote.side_effect = TimeoutError("synthetic outage")
    retained = await runtime(c, NOW + timedelta(minutes=5)).get_warrant_listing_quote(c.request)
    assert retained.data.retained is True
    assert retained.data.original_market_status == original
    assert retained.retrieved_at == first.retrieved_at
    async with c.database.session_context() as session:
        report = await QuoteHistoryReader(session).report(
            c.request.workspace_id, c.warrant, now=NOW + timedelta(minutes=5)
        )
    historic = next(item for item in report.items if item.id == sample_id)
    assert historic.quote.original_market_status == original
    assert historic.quote_fingerprint == sample_fingerprint
    with Session(c.database.engine) as session:
        assert session.get(WarrantQuoteSampleModel, sample_id).payload == original_sample
    assert report.items[0].quote is None
    snapshots.load.assert_awaited_once()


@pytest.mark.asyncio
async def test_new_closed_without_bid_does_not_retime_old_open_or_claim_a_complete_status_stream(
    context,
):
    c = context
    adapter, snapshots, data = configured_adapter(c)
    first = await runtime(c, NOW, adapter).get_warrant_listing_quote(c.request)
    with Session(c.database.engine) as session:
        original_payload = deepcopy(session.scalar(select(WarrantQuoteObservationModel)).payload)
        original_sample = deepcopy(session.scalar(select(WarrantQuoteSampleModel)).payload)
    later = NOW + timedelta(minutes=1)
    data["generated_at"] = later.isoformat()
    data["records"][0].update(
        bid=None,
        ask=None,
        trading_status="CLOSED",
        status_observed_at="2026-09-11T20:00:30+02:00",
    )
    adapter._clock = lambda: later
    snapshots.load.return_value = (FrankfurtSnapshot.model_validate(data), later, False)
    retained = await runtime(c, later, adapter).get_warrant_listing_quote(c.request)
    assert retained.data.retained is True
    assert retained.data.refresh_error == "WARRANT_NO_QUOTE_RETURNED"
    assert retained.data.original_market_status == first.data.original_market_status
    assert retained.data.original_market_status.status == "OPEN"
    assert retained.data.original_market_status.observed_at == NOW - timedelta(seconds=30)
    assert retained.retrieved_at == NOW
    with Session(c.database.engine) as session:
        assert session.scalar(select(WarrantQuoteObservationModel)).payload == original_payload
        samples = session.scalars(select(WarrantQuoteSampleModel)).all()
        assert len(samples) == 1  # Existing first-capture-per-slot policy is not status continuity.
        assert samples[0].payload == original_sample
    assert snapshots.load.await_count == 2


@pytest.mark.asyncio
async def test_new_priced_closed_status_is_preserved_as_distinct_evidence_with_unchanged_prices(
    context,
):
    c = context
    adapter, snapshots, data = configured_adapter(c)
    first = await runtime(c, NOW, adapter).get_warrant_listing_quote(c.request)
    later = NOW + timedelta(minutes=5)
    data["generated_at"] = later.isoformat()
    data["records"][0].update(
        trading_status="CLOSED", status_observed_at="2026-09-11T20:04:30+02:00"
    )
    adapter._clock = lambda: later
    snapshots.load.return_value = (FrankfurtSnapshot.model_validate(data), later, False)
    closed = await runtime(c, later, adapter).get_warrant_listing_quote(c.request)
    assert closed.data.retained is False
    assert closed.data.bid == first.data.bid
    assert closed.data.observed_at == first.data.observed_at
    assert closed.data.original_market_status.status == "CLOSED"
    assert closed.data.original_market_status.observed_at == later - timedelta(seconds=30)
    with Session(c.database.engine) as session:
        samples = session.scalars(select(WarrantQuoteSampleModel)).all()
        assert len(samples) == 2
        assert len({sample.quote_fingerprint for sample in samples}) == 2
        assert {
            sample.payload["quote"]["original_market_status"]["status"] for sample in samples
        } == {
            "OPEN",
            "CLOSED",
        }
