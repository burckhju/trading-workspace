"""Sample actual retained-provider reads against SQL, including failure and restarts."""

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session
from tests.unit.backend.features.market_data import test_retained_quotes as retained_tests
from tests.unit.backend.features.market_data.test_retained_quotes import (
    NOW,
    SqlDatabase,
)

from app.features.market_data.domain.enums import MarketDataProvider
from app.features.market_data.persistence.models import (
    WarrantProviderMappingModel,
)
from app.features.market_data.service.errors import MarketDataInvalidResponseError
from app.features.market_data.service.quote_history import QuoteHistoryReader, sample_status
from app.features.market_data.service.retained_quotes import RetainedWarrantQuoteProvider

context = retained_tests.context


def wrapper(c, at):
    return RetainedWarrantQuoteProvider(
        c.database, c.provider, MarketDataProvider.FRANKFURT_QUOTES, capture_clock=lambda: at
    )


async def report(c, at=NOW + timedelta(hours=1), **kwargs):
    async with c.database.session_context() as session:
        return await QuoteHistoryReader(session).report(
            c.request.workspace_id, c.warrant, now=at, **kwargs
        )


@pytest.mark.asyncio
async def test_first_failed_slot_survives_success_and_repeated_reads(context):
    c = context
    c.provider.get_warrant_listing_quote.side_effect = TimeoutError("secret URL")
    with pytest.raises(MarketDataInvalidResponseError):
        await wrapper(c, NOW).get_warrant_listing_quote(c.request)
    c.provider.get_warrant_listing_quote.side_effect = None
    for seconds in (1, 30, 299):
        assert (
            await wrapper(c, NOW + timedelta(seconds=seconds)).get_warrant_listing_quote(c.request)
            == c.result
        )
    first = await report(c)
    assert len(first.items) == 1
    assert first.items[0].reason == "TimeoutError"
    assert first.items[0].quote is None
    assert first.segments[0].distinct_quote_evidence == 0
    assert first.segments[0].statuses["REQUEST_FAILED"] == 1
    assert first.time_coverage_percent is None
    assert first.iv_history_available is first.execution_usable is False
    await wrapper(c, NOW + timedelta(minutes=5)).get_warrant_listing_quote(c.request)
    c.database.engine.dispose()
    c.database = SqlDatabase(c.url)
    restored = await report(c)
    assert len(restored.items) == 2
    assert restored.items[0].quote.observed_at == NOW
    assert restored.items[0].retrieved_at == NOW
    assert restored.items[0].captured_at == NOW + timedelta(minutes=5)
    assert restored.segments[0].statuses["REFERENCE_ONLY"] == 1


@pytest.mark.asyncio
async def test_cached_quote_not_new_evidence_and_fallback_not_sampled_as_success(context):
    c = context
    for minute in (0, 5, 10):
        await wrapper(c, NOW + timedelta(minutes=minute)).get_warrant_listing_quote(c.request)
    c.provider.get_warrant_listing_quote.side_effect = MarketDataInvalidResponseError(
        "FRANKFURT_REQUEST_THROTTLED"
    )
    fallback = await wrapper(c, NOW + timedelta(minutes=15)).get_warrant_listing_quote(c.request)
    assert fallback.data.retained
    view = await report(c)
    segment = view.segments[0]
    assert segment.sampled_slots == 4 and segment.distinct_quote_evidence == 1
    assert segment.observed_utc_days == 1
    assert view.items[0].quote is None and view.items[0].retrieved_at is None
    assert view.items[0].reason == "FRANKFURT_REQUEST_THROTTLED"
    assert view.items[1].quote.reference_price == Decimal(".231")


@pytest.mark.asyncio
async def test_mapping_revision_separates_segments_even_in_same_slot(context):
    c = context
    await wrapper(c, NOW).get_warrant_listing_quote(c.request)
    with Session(c.database.engine) as session:
        mapping = session.get(WarrantProviderMappingModel, c.mapping)
        mapping.version += 1
        session.commit()
    await wrapper(c, NOW + timedelta(seconds=1)).get_warrant_listing_quote(c.request)
    view = await report(c)
    assert len(view.segments) == 2
    assert len({s.identity_key for s in view.segments}) == 2
    assert all(s.sampled_slots == 1 for s in view.segments)


@pytest.mark.asyncio
async def test_window_detail_limit_ownership_and_empty_state(context):
    c = context
    empty = await report(c)
    assert empty.items == empty.segments == ()
    assert empty.collection_started_at is None
    for minute in range(0, 300, 5):
        await wrapper(c, NOW + timedelta(minutes=minute)).get_warrant_listing_quote(c.request)
    full = await report(c, NOW + timedelta(hours=5))
    assert len(full.items) == 50 and full.segments[0].sampled_slots == 60
    assert full.collection_started_at == NOW
    later = await report(c, NOW + timedelta(days=2), days=1)
    assert later.items == later.segments == () and later.collection_started_at == NOW
    async with c.database.session_context() as session:
        reader = QuoteHistoryReader(session)
        assert await reader.report(uuid4(), c.warrant, now=NOW) is None
        for now, days in ((NOW.replace(tzinfo=None), 7), (NOW, 0), (NOW, 32)):
            with pytest.raises(ValueError):
                await reader.report(c.request.workspace_id, c.warrant, now=now, days=days)


@pytest.mark.parametrize(
    "changes,age,status",
    [
        ({}, 0, "TWO_SIDED_WITHIN_AGE_LIMIT"),
        ({}, 60, "TWO_SIDED_WITHIN_AGE_LIMIT"),
        ({}, 61, "STALE"),
        ({}, -1, "TIME_INCONSISTENT"),
        ({"ask": None}, 0, "ONE_SIDED"),
        ({"max_quote_age_seconds": None}, 0, "AGE_POLICY_UNKNOWN"),
    ],
)
def test_age_boundary_never_extended_for_market_close(context, changes, age, status):
    q = replace(
        context.result.data,
        reference_price=None,
        reference_price_type=None,
        source_mode="OFFICIAL_WEBSITE",
        bid=Decimal(".2"),
        ask=Decimal(".22"),
        max_quote_age_seconds=60,
    )
    assert sample_status(replace(q, **changes), None, NOW + timedelta(seconds=age)) == status


@pytest.mark.asyncio
async def test_unknown_source_clock_stays_unknown_and_no_quote_retains_receipt(context):
    c = context
    c.provider.get_warrant_listing_quote.return_value = replace(
        c.result, data=replace(c.result.data, observed_at=None)
    )
    await wrapper(c, NOW).get_warrant_listing_quote(c.request)
    c.provider.get_warrant_listing_quote.return_value = replace(c.result, data=None)
    await wrapper(c, NOW + timedelta(minutes=5)).get_warrant_listing_quote(c.request)
    view = await report(c)
    assert view.items[0].status == "NO_QUOTE"
    assert view.items[0].retrieved_at == NOW
    assert view.items[0].quote is None
    assert view.items[1].quote.observed_at is None
    assert view.items[1].status == "TIMESTAMP_UNKNOWN"
    assert view.items[1].retrieved_at == view.items[1].captured_at == NOW
