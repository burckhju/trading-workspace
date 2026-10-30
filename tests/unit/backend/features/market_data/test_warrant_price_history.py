"""Historical prices use durable evidence clocks and never manufacture a time series."""

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session
from tests.unit.backend.features.market_data import test_retained_quotes as retained_tests
from tests.unit.backend.features.market_data.test_retained_quotes import ISIN, NOW, SqlDatabase

from app.features.market_data.domain.enums import MarketDataProvider, QualityStatus
from app.features.market_data.persistence.models import (
    WarrantProviderMappingModel,
    WarrantQuoteObservationModel,
    WarrantQuoteSampleModel,
)
from app.features.market_data.service import warrant_price_history as prices
from app.features.market_data.service.quote_history import QUOTE, QuoteHistoryReader
from app.features.market_data.service.retained_quotes import RetainedWarrantQuoteProvider
from app.features.product.persistence.models import WarrantListingModel, WarrantModel

context = retained_tests.context


def sample(c, *, minute=0, quote=None, status="REFERENCE_ONLY", **overrides):
    """Insert an already-captured historical fact, including deliberately damaged legacy JSON."""
    at = NOW + timedelta(minutes=minute)
    quote = c.result.data if quote is None else quote
    values = dict(
        id=uuid4(),
        workspace_id=c.request.workspace_id,
        warrant_id=c.warrant,
        warrant_listing_id=c.request.warrant_listing_id,
        provider="FRANKFURT_QUOTES",
        identity_key="a" * 64,
        isin=ISIN,
        captured_at=at,
        slot_at=at,
        day_utc=at.date(),
        status=status,
        reason=None,
        quote_fingerprint=None,
        payload={"quote": QUOTE.dump_python(quote, mode="json"), "retrieved_at": at.isoformat()},
    )
    values.update(overrides)
    with Session(c.database.engine) as session:
        session.add(WarrantQuoteSampleModel(**values))
        session.commit()
    return values["id"]


def retained(c, *, result=None, **overrides):
    values = dict(
        workspace_id=c.request.workspace_id,
        warrant_listing_id=c.request.warrant_listing_id,
        provider="FRANKFURT_QUOTES",
        identity_key="a" * 64,
        payload=prices.RESULT.dump_python(result or c.result, mode="json"),
    )
    values.update(overrides)
    with Session(c.database.engine) as session:
        session.add(WarrantQuoteObservationModel(**values))
        session.commit()


async def read(c, *, now=NOW + timedelta(hours=1), **kwargs):
    async with c.database.session_context() as session:
        return await QuoteHistoryReader(session).prices(
            c.request.workspace_id, c.warrant, now=now, **kwargs
        )


@pytest.mark.asyncio
async def test_cache_rereads_and_retention_are_one_original_point_after_restart(context):
    c = context
    for minute in (0, 5, 10):
        await RetainedWarrantQuoteProvider(
            c.database,
            c.provider,
            MarketDataProvider.FRANKFURT_QUOTES,
            capture_clock=lambda minute=minute: NOW + timedelta(minutes=minute),
        ).get_warrant_listing_quote(c.request)
    c.provider.get_warrant_listing_quote.reset_mock()
    c.provider.get_warrant_listing_quote.side_effect = AssertionError(
        "Chart must not call provider"
    )
    c.database.engine.dispose()
    c.database = SqlDatabase(c.url)
    statements = []

    def record_sql(_connection, _cursor, statement, _parameters, _context, _executemany):
        statements.append(statement)

    event.listen(c.database.engine, "before_cursor_execute", record_sql)
    try:
        report = await read(c)
    finally:
        event.remove(c.database.engine, "before_cursor_execute", record_sql)
    assert len(report.series) == 1
    series = report.series[0]
    assert series.currency == "EUR" and series.price_kind == "LAST_TRADE"
    assert len(series.points) == 1
    point = series.points[0]
    assert point.observed_at == point.retrieved_at == point.captured_at == NOW
    assert point.price == Decimal("0.231") and point.storage == "SAMPLE"
    assert report.samples_available == report.samples_considered == 3
    assert report.excluded == {"DUPLICATE_OBSERVATION": 3}
    assert report.collection_started_at == NOW
    assert report.truncated is False
    assert statements and all(
        statement.lstrip().upper().startswith("SELECT") for statement in statements
    )
    c.provider.get_warrant_listing_quote.assert_not_awaited()


@pytest.mark.asyncio
async def test_legacy_retention_only_keeps_one_old_point_without_backfill_or_capture_time(context):
    c = context
    old = NOW - timedelta(days=730)
    retained(c, result=replace(c.result, data=replace(c.result.data, observed_at=old)))
    # Today's preferred currency and inactive mapping cannot rewrite proven historical evidence.
    with Session(c.database.engine) as session:
        session.get(WarrantListingModel, c.request.warrant_listing_id).quotation_currency_code = (
            "USD"
        )
        session.get(WarrantProviderMappingModel, c.mapping).status = "DISABLED"
        session.commit()
    report = await read(c)
    assert report.samples_available == report.samples_considered == 0
    assert report.collection_started_at is None
    assert report.window_start is None
    assert len(report.series) == len(report.series[0].points) == 1
    assert report.series[0].currency == "EUR"
    point = report.series[0].points[0]
    assert point.observed_at == old
    assert point.retrieved_at == NOW
    assert point.captured_at is None and point.storage == "RETAINED"
    recent = await read(c, days=31)
    assert recent.series == () and recent.excluded == {"OUTSIDE_WINDOW": 1}


@pytest.mark.asyncio
async def test_price_window_uses_source_time_with_inclusive_boundary_not_late_capture(context):
    c = context
    end = NOW + timedelta(hours=1)
    start = end - timedelta(days=7)
    for minute, observed in ((0, start - timedelta(microseconds=1)), (5, start), (10, NOW)):
        sample(c, minute=minute, quote=replace(c.result.data, observed_at=observed))
    report = await read(c, now=end, days=7)
    assert report.window_start == start and report.window_end == end
    assert [point.observed_at for point in report.series[0].points] == [start, NOW]
    assert report.excluded == {"OUTSIDE_WINDOW": 1}
    assert report.samples_considered == 3


@pytest.mark.asyncio
async def test_provider_mapping_currency_price_kind_and_mode_remain_distinct(context):
    c = context
    reference = c.result.data
    two_sided = replace(
        reference,
        bid=Decimal("0.2"),
        ask=Decimal("0.3"),
        reference_price=None,
        reference_price_type=None,
        source_mode="OFFICIAL_WEBSITE",
        max_quote_age_seconds=60,
    )
    sample(c)
    sample(c, minute=5, quote=reference, provider="VONTOBEL_MARKETS")
    sample(c, minute=10, quote=reference, identity_key="b" * 64)
    sample(c, minute=15, quote=replace(reference, currency="USD"))
    sample(c, minute=20, quote=replace(reference, reference_price_type="PREVIOUS_CLOSE"))
    sample(c, minute=25, quote=replace(reference, source_mode="ALTERNATE_REFERENCE"))
    sample(c, minute=30, quote=two_sided, status="STALE")
    report = await read(c)
    assert len(report.series) == 8
    assert len({series.id for series in report.series}) == 8
    assert {(s.provider, s.identity_key) for s in report.series} == {
        ("FRANKFURT_QUOTES", "a" * 64),
        ("FRANKFURT_QUOTES", "b" * 64),
        ("VONTOBEL_MARKETS", "a" * 64),
    }
    assert {s.currency for s in report.series} == {"EUR", "USD"}
    assert {s.price_kind for s in report.series} == {"BID", "ASK", "LAST_TRADE", "PREVIOUS_CLOSE"}
    assert all(len(s.points) == 1 for s in report.series)
    assert {s.points[0].status for s in report.series if s.price_kind in {"BID", "ASK"}} == {
        "STALE"
    }
    assert report.excluded == {}


@pytest.mark.asyncio
async def test_same_price_at_new_source_time_is_new_evidence_and_revisions_are_not_overwritten(
    context,
):
    c = context
    sample(c, quote=replace(c.result.data, observed_at=NOW - timedelta(days=3)))
    sample(c, minute=5)
    sample(c, minute=10, quote=replace(c.result.data, reference_price=Decimal("0.232")))
    report = await read(c)
    points = report.series[0].points
    assert len(points) == 3
    assert points[0].observed_at == NOW - timedelta(days=3)
    assert points[0].price == Decimal("0.231")
    assert {(p.observed_at, p.price) for p in points[1:]} == {
        (NOW, Decimal("0.231")),
        (NOW, Decimal("0.232")),
    }
    assert report.excluded == {}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case,expected",
    [
        ("unknown_original", "TIMESTAMP_UNKNOWN"),
        ("missing_receipt", "TIME_INCONSISTENT"),
        ("naive_receipt", "TIME_INCONSISTENT"),
        ("source_after_receipt", "TIME_INCONSISTENT"),
        ("receipt_after_capture", "TIME_INCONSISTENT"),
        ("capture_failure", "REQUEST_FAILED"),
        ("inconsistent_status", "TIME_INCONSISTENT"),
        ("no_quote", "NO_QUOTE"),
        ("no_price", "NO_PRICE"),
        ("bad_json", "INVALID_OBSERVATION"),
        ("bad_receipt", "INVALID_OBSERVATION"),
        ("negative_price", "INVALID_OBSERVATION"),
        ("wrong_isin", "IDENTITY_MISMATCH"),
        ("wrong_symbol", "IDENTITY_MISMATCH"),
        ("wrong_listing", "IDENTITY_MISMATCH"),
        ("empty_identity", "IDENTITY_MISMATCH"),
    ],
)
async def test_unplottable_evidence_is_explained_without_substituting_a_clock(
    context, case, expected
):
    c = context
    data = QUOTE.dump_python(c.result.data, mode="json")
    payload = {"quote": data, "retrieved_at": NOW.isoformat()}
    overrides = {}
    if case == "unknown_original":
        data["observed_at"] = None
    elif case == "missing_receipt":
        payload.pop("retrieved_at")
    elif case == "naive_receipt":
        payload["retrieved_at"] = NOW.replace(tzinfo=None).isoformat()
    elif case == "source_after_receipt":
        data["observed_at"] = (NOW + timedelta(seconds=1)).isoformat()
    elif case == "receipt_after_capture":
        payload["retrieved_at"] = (NOW + timedelta(seconds=1)).isoformat()
    elif case == "capture_failure":
        overrides["reason"] = "PROVIDER_FAILED"
    elif case == "inconsistent_status":
        overrides["status"] = "TIME_INCONSISTENT"
    elif case == "no_quote":
        payload["quote"] = None
    elif case == "no_price":
        data.update(reference_price=None, reference_price_type=None)
    elif case == "bad_json":
        payload["quote"] = {"unexpected": "legacy"}
    elif case == "bad_receipt":
        payload["retrieved_at"] = "not-a-timestamp"
    elif case == "negative_price":
        data["reference_price"] = "-1"
    elif case == "wrong_isin":
        data["isin"] = "DE000VH4VNA6"
    elif case == "wrong_symbol":
        data["provider_symbol"] = "DE000VH4VNA6"
    elif case == "wrong_listing":
        data["warrant_listing_id"] = str(uuid4())
    else:
        overrides["identity_key"] = ""
    sample(c, payload=payload, **overrides)
    report = await read(c)
    assert report.series == ()
    assert report.excluded == {expected: 1}
    assert report.samples_considered == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["quality", "provider", "receipt_future", "no_quote"])
async def test_retention_does_not_relax_quality_identity_or_time_rules(context, change):
    c = context
    result = c.result
    expected = "INVALID_OBSERVATION"
    if change == "quality":
        result = replace(result, quality_status=QualityStatus.SUSPICIOUS)
    elif change == "provider":
        result = replace(result, provider=MarketDataProvider.VONTOBEL_MARKETS)
    elif change == "receipt_future":
        result = replace(result, retrieved_at=NOW + timedelta(days=1))
        expected = "TIME_INCONSISTENT"
    else:
        result = replace(result, data=None)
        expected = "NO_QUOTE"
    retained(c, result=result)
    report = await read(c)
    assert report.series == () and report.excluded == {expected: 1}


@pytest.mark.asyncio
async def test_missing_product_foreign_workspace_and_old_product_identity_cannot_leak_points(
    context,
):
    c = context
    sample(c)
    retained(c)
    async with c.database.session_context() as session:
        reader = QuoteHistoryReader(session)
        assert await reader.prices(uuid4(), c.warrant, now=NOW) is None
        assert await reader.prices(c.request.workspace_id, uuid4(), now=NOW) is None
    with Session(c.database.engine) as session:
        session.get(WarrantModel, c.warrant).isin = "DE000VH4VNA6"
        session.commit()
    changed = await read(c)
    assert changed.series == () and changed.excluded == {"IDENTITY_MISMATCH": 2}


@pytest.mark.asyncio
async def test_foreign_product_and_workspace_samples_and_future_captures_are_not_read(context):
    c = context
    sample(c)
    sample(c, minute=5, warrant_id=uuid4())
    sample(c, minute=10, workspace_id=uuid4())
    sample(c, minute=120)
    report = await read(c)
    assert report.samples_available == report.samples_considered == 1
    assert len(report.series) == len(report.series[0].points) == 1
    assert report.excluded == {}


@pytest.mark.asyncio
async def test_truncation_reports_available_sample_count_and_never_backfills_missing_points(
    context, monkeypatch
):
    c = context
    monkeypatch.setattr(prices, "MAX_HISTORY_SAMPLES", 2)
    for minute in (0, 5, 10):
        sample(
            c,
            minute=minute,
            quote=replace(c.result.data, observed_at=NOW + timedelta(minutes=minute)),
        )
    report = await read(c)
    assert report.truncated is True
    assert report.samples_available == 3 and report.samples_considered == 2
    assert report.collection_started_at == NOW
    assert [p.observed_at for p in report.series[0].points] == [
        NOW + timedelta(minutes=5),
        NOW + timedelta(minutes=10),
    ]


@pytest.mark.asyncio
async def test_empty_history_and_invalid_ranges_are_distinct(context):
    c = context
    empty = await read(c)
    assert empty.series == () and empty.excluded == {}
    assert empty.collection_started_at is None and empty.samples_available == 0
    assert empty.truncated is False
    async with c.database.session_context() as session:
        reader = QuoteHistoryReader(session)
        for now, days in ((NOW.replace(tzinfo=None), None), (NOW, 0), (NOW, 367)):
            with pytest.raises(ValueError, match="Invalid history window"):
                await reader.prices(c.request.workspace_id, c.warrant, now=now, days=days)


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [None, [], "legacy-damaged-envelope"])
async def test_malformed_json_envelope_cannot_hide_other_valid_history(context, payload):
    sample(context)
    sample(context, minute=5, payload=payload)
    report = await read(context)
    assert len(report.series) == len(report.series[0].points) == 1
    assert report.series[0].points[0].price == Decimal("0.231")
    assert report.excluded == {"INVALID_OBSERVATION": 1}
