"""Saved EOD reads preserve their real limits, origins and unqualified price scale."""

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.features.market.domain.enums import (
    DataOrigin,
    LifecycleStatus,
    UnderlyingType,
)
from app.features.market.domain.enums import (
    QualityStatus as ReferenceQuality,
)
from app.features.market.persistence import top_down_models as _top_down_models  # noqa: F401
from app.features.market.persistence.models import ListingModel, TradingVenueModel, UnderlyingModel
from app.features.market_data.domain.enums import MarketDataProvider, PriceType, QualityStatus
from app.features.market_data.persistence.instruments import MarketDataInstrumentModel
from app.features.market_data.persistence.mapping import apply_daily_price, daily_price_to_domain
from app.features.market_data.persistence.models import DailyPriceModel
from app.features.market_data.service import hebeltrader_history as module
from app.features.market_data.service.hebeltrader_history import HebeltraderHistoryReader
from app.features.position_monitoring.domain.hebeltrader_targets import (
    TargetComparisonQualification,
    TargetPositionBasis,
    TargetSourceBasis,
    evaluate_hebeltrader_targets,
)
from app.features.position_monitoring.service.hebeltrader_target_projection import target_history
from app.features.trade_position.domain.price_binding import PriceBasis, PriceBinding

NOW = datetime(2026, 11, 14, 12, tzinfo=UTC)
RECORDED = NOW - timedelta(hours=1)
RETRIEVED = NOW - timedelta(hours=2)
SOURCE_UPDATED = NOW - timedelta(hours=3)
REFERENCE_CREATED = datetime(2025, 1, 1, tzinfo=UTC)


class SqlSession:
    """Execute the actual production SELECTs against synthetic in-memory SQLite."""

    def __init__(self, session):
        self.session = session

    @property
    def no_autoflush(self):
        return self.session.no_autoflush

    async def execute(self, statement):
        return self.session.execute(statement)

    async def scalars(self, statement):
        return self.session.scalars(statement)


@pytest.fixture(autouse=True)
def forbid_outbound_http(monkeypatch):
    asynchronous = AsyncMock(side_effect=AssertionError("Saved history cannot fetch prices"))
    synchronous = Mock(side_effect=AssertionError("Saved history cannot fetch prices"))
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", asynchronous)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", synchronous)
    yield
    asynchronous.assert_not_awaited()
    synchronous.assert_not_called()


@pytest.fixture
def context():
    engine = create_engine("sqlite://")
    for model in (
        TradingVenueModel,
        UnderlyingModel,
        ListingModel,
        MarketDataInstrumentModel,
        DailyPriceModel,
    ):
        model.__table__.create(engine)
    c = SimpleNamespace(
        engine=engine,
        workspace=uuid4(),
        underlying=uuid4(),
        listing=uuid4(),
        venue=uuid4(),
    )
    clocks = dict(created_at=REFERENCE_CREATED, updated_at=REFERENCE_CREATED, version=1)
    with Session(engine) as session:
        session.add_all(
            [
                TradingVenueModel(
                    id=c.venue,
                    mic="XETR",
                    name="Synthetic venue",
                    country_code="DE",
                    timezone="Europe/Berlin",
                    is_active=True,
                    reference_version="synthetic-reference-v1",
                    **clocks,
                ),
                UnderlyingModel(
                    id=c.underlying,
                    workspace_id=c.workspace,
                    type=UnderlyingType.STOCK,
                    name="Synthetic underlying",
                    lifecycle_status=LifecycleStatus.ACTIVE,
                    quality_status=ReferenceQuality.VERIFIED,
                    data_origin=DataOrigin.MANUAL,
                    **clocks,
                ),
                ListingModel(
                    id=c.listing,
                    workspace_id=c.workspace,
                    underlying_id=c.underlying,
                    trading_venue_id=c.venue,
                    ticker="SYNTH",
                    currency_code="EUR",
                    lifecycle_status=LifecycleStatus.ACTIVE,
                    is_primary=True,
                    data_origin=DataOrigin.MANUAL,
                    **clocks,
                ),
            ]
        )
        session.commit()
    yield c
    engine.dispose()


def insert_prices(c, days, **overrides):
    rows = []
    for day in days:
        values = dict(
            id=uuid4(),
            workspace_id=c.workspace,
            listing_id=c.listing,
            market_data_instrument_id=None,
            trading_date=day,
            open=Decimal("101.5"),
            high=Decimal("107.25"),
            low=Decimal("99.75"),
            close=Decimal("105"),
            adjusted_close=Decimal("105"),
            volume=Decimal("123.5"),
            currency="EUR",
            provider=MarketDataProvider.EODHD,
            provider_symbol="SYNTH.XETRA",
            retrieved_at=RETRIEVED,
            source_updated_at=SOURCE_UPDATED,
            quality_status=QualityStatus.VALID,
            warnings="",
            price_type=PriceType.EOD,
            created_at=RECORDED,
            updated_at=RECORDED,
        )
        values.update(overrides)
        rows.append(DailyPriceModel(**values))
    with Session(c.engine, expire_on_commit=False) as session:
        session.add_all(rows)
        session.commit()
    return rows


async def read(c, **overrides):
    values = dict(
        workspace_id=c.workspace,
        underlying_id=c.underlying,
        listing_id=c.listing,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 11, 14),
        known_at=NOW,
    )
    values.update(overrides)
    with Session(c.engine) as session:
        return await HebeltraderHistoryReader(SqlSession(session)).read(**values)


@pytest.mark.asyncio
async def test_full_saved_range_beyond_61_rows_is_scoped_and_only_selects(context):
    c = context
    days = [date(2026, 1, 1) + timedelta(days=index) for index in range(100)]
    originals = insert_prices(c, reversed(days))
    insert_prices(c, [date(2025, 12, 31), date(2026, 11, 15)])
    statements = []

    def capture(_connection, _cursor, statement, _parameters, _context, _executemany):
        statements.append(statement)

    event.listen(c.engine, "before_cursor_execute", capture)
    try:
        result = await read(c, listing_id=None)
    finally:
        event.remove(c.engine, "before_cursor_execute", capture)
    assert result.status == "AVAILABLE" and result.stored_range_complete
    assert result.intervals_complete and result.rows_observed == 100
    assert [row.trading_date for row in result.rows] == days
    assert {row.source_row_id for row in result.rows} == {row.id for row in originals}
    assert all(statement.lstrip().upper().startswith("SELECT") for statement in statements)
    assert result.binding.listing_id == c.listing
    assert result.binding.provenance == "CURRENT_REFERENCE_NOT_HISTORICALLY_VERIFIED"
    assert result.calendar_coverage == "NOT_ASSESSED"
    assert result.qualification_required == "HISTORICAL_BINDING_AND_COMPARISON_SCALE"
    assert all(
        row.scale_status == "REQUIRES_EXPLICIT_COMPARISON_QUALIFICATION" for row in result.rows
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("day,hours", [(date(2026, 3, 29), 23), (date(2026, 10, 25), 25)])
async def test_date_only_envelope_respects_dst_and_preserves_separate_clocks(context, day, hours):
    original = insert_prices(context, [day], source_updated_at=None)[0]
    result = await read(context)
    row = result.rows[0]
    assert row.source_row_id == original.id and row.price_basis == "UNDERLYING"
    assert row.time_precision == "DATE_ONLY"
    assert row.interval_basis == "LOCAL_CALENDAR_DAY_NOT_VERIFIED_SESSION"
    assert row.interval_end - row.interval_start == timedelta(hours=hours)
    assert row.interval_start < row.interval_end < row.retrieved_at
    assert row.source_updated_at is None
    assert row.retrieved_at == RETRIEVED and row.recorded_at == RECORDED
    assert row.last_updated_at == RECORDED and row.issues == ()


@pytest.mark.asyncio
async def test_incomplete_day_and_late_evidence_remain_unusable_at_original_cutoff(context):
    insert_prices(context, [NOW.date()])
    result = await read(context)
    assert result.stored_range_complete and not result.intervals_complete
    assert result.rows[0].issues == ("FULL_LOCAL_DAY_NOT_COMPLETED_AT_CUTOFF",)
    before_capture = await read(context, known_at=RECORDED - timedelta(minutes=1))
    assert "DATA_NOT_KNOWN_AT_CUTOFF" in before_capture.rows[0].issues
    assert before_capture.rows[0].fingerprint == result.rows[0].fingerprint
    assert before_capture.fingerprint != result.fingerprint


@pytest.mark.asyncio
async def test_fingerprints_bind_source_content_range_and_metadata_but_not_read_clock(context):
    original = insert_prices(context, [date(2026, 10, 1)])[0]
    first = await read(context)
    later = await read(context, known_at=NOW + timedelta(seconds=1))
    assert first.fingerprint == later.fingerprint
    assert first.binding.fingerprint == later.binding.fingerprint
    assert first.rows[0].fingerprint == later.rows[0].fingerprint
    changed_start = await read(context, start_date=date(2026, 9, 1))
    assert changed_start.fingerprint != first.fingerprint
    with Session(context.engine) as session:
        row = session.get(DailyPriceModel, original.id)
        row.high = Decimal("108.25")
        row.updated_at = NOW
        session.commit()
    changed_price = await read(context)
    assert changed_price.rows[0].source_row_id == first.rows[0].source_row_id
    assert changed_price.rows[0].fingerprint != first.rows[0].fingerprint
    assert changed_price.fingerprint != first.fingerprint
    assert first.rows[0].high == Decimal("107.25")  # Earlier immutable DTO stays intact.
    with Session(context.engine) as session:
        venue = session.get(TradingVenueModel, context.venue)
        venue.timezone = "America/New_York"
        venue.version = 2
        venue.updated_at = NOW
        session.commit()
    changed_binding = await read(context)
    assert changed_binding.binding.fingerprint != first.binding.fingerprint
    assert changed_binding.rows[0].fingerprint == changed_price.rows[0].fingerprint
    assert changed_binding.rows[0].interval_start != changed_price.rows[0].interval_start
    assert changed_binding.fingerprint != changed_price.fingerprint


@pytest.mark.asyncio
async def test_next_utc_day_preserves_qualification_for_identical_completed_material(context):
    insert_prices(context, [date(2026, 10, 1), date(2026, 10, 2)])
    first = await read(context)
    tomorrow = NOW + timedelta(days=1)
    later = await read(context, end_date=tomorrow.date(), known_at=tomorrow)
    assert first.end_date != later.end_date
    assert first.known_at != later.known_at
    assert first.start_date == later.start_date
    assert first.binding == later.binding and first.rows == later.rows
    assert first.intervals_complete and later.intervals_complete
    assert first.fingerprint == later.fingerprint


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["new_row", "replacement", "quality", "completed_interval"])
async def test_next_day_material_changes_still_require_comparison_review(context, change):
    day = NOW.date() if change == "completed_interval" else date(2026, 10, 1)
    original = insert_prices(
        context, [day], warnings="review required" if change == "quality" else ""
    )[0]
    first = await read(context)
    if change == "new_row":
        insert_prices(context, [date(2026, 10, 2)])
    elif change in {"replacement", "quality"}:
        with Session(context.engine) as session:
            row = session.get(DailyPriceModel, original.id)
            if change == "replacement":
                row.id = uuid4()
            else:
                row.warnings = ""
            session.commit()
    tomorrow = NOW + timedelta(days=1)
    later = await read(context, end_date=tomorrow.date(), known_at=tomorrow)
    assert first.fingerprint != later.fingerprint
    assert first.binding == later.binding
    if change == "completed_interval":
        assert first.rows[0].fingerprint == later.rows[0].fingerprint
        assert first.rows[0].issues == ("FULL_LOCAL_DAY_NOT_COMPLETED_AT_CUTOFF",)
        assert later.rows[0].issues == ()
        assert not first.intervals_complete and later.intervals_complete
    elif change == "quality":
        assert first.rows[0].issues == ("EOD_QUALITY_LIMITED",)
        assert later.rows[0].issues == ()
    elif change == "replacement":
        assert first.rows[0].source_row_id != later.rows[0].source_row_id
    else:
        assert len(first.rows) == 1 and len(later.rows) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "change",
    [
        "identical",
        "price",
        "quality",
        "warnings",
        "provider",
        "symbol",
        "source_time",
        "recorded",
        "identity",
        "currency",
        "adjustment",
    ],
)
async def test_real_provider_refresh_preserves_only_unchanged_target_proofs(context, change):
    original = insert_prices(context, [date(2026, 10, 1)])[0]
    first = await read(context)
    binding = PriceBinding(PriceBasis.UNDERLYING, context.underlying, "EUR")
    source = TargetSourceBasis(
        uuid4(),
        binding,
        "synthetic-confirmed-original-scale",
        Decimal("100"),
        Decimal("106"),
        Decimal("107"),
        issue_date=date(2026, 9, 28),
        content_hash="a" * 64,
    )
    position = TargetPositionBasis(
        workspace_id=context.workspace,
        trade_id=uuid4(),
        position_id=uuid4(),
        product_id=uuid4(),
        underlying_id=context.underlying,
        owner_basis_id="unchanged-synthetic-execution-owner",
        opened_at=datetime(2026, 9, 29, 12, tzinfo=UTC),
        opened_on=None,
        opening_timezone=None,
        remaining_quantity=100,
        closed=False,
        option_direction="CALL",
    )
    qualification = TargetComparisonQualification(
        first.fingerprint,
        first.binding.fingerprint,
        source.source_version_id,
        source.scale_reference,
        "Synthetic reviewed original source and listing comparison",
    )
    initial = evaluate_hebeltrader_targets(
        position=position,
        source=source,
        history=target_history(first),
        qualification=qualification,
        assessment_id=uuid4(),
        assessed_at=NOW,
    )
    assert initial.z1.status == initial.z2.status == "PROVEN"

    refreshed_at = NOW + timedelta(minutes=5)
    changes = {
        "price": {"high": Decimal("108.25")},
        "quality": {"quality_status": QualityStatus.SUSPICIOUS},
        "warnings": {"warnings": ("Synthetic changed source quality",)},
        "provider": {"provider": MarketDataProvider.JPMORGAN},
        "symbol": {"provider_symbol": "SYNTH.OTHER"},
        "source_time": {"source_updated_at": SOURCE_UPDATED + timedelta(seconds=1)},
        "currency": {"currency": "USD"},
        "adjustment": {"adjusted_close": Decimal("104")},
    }.get(change, {})
    refreshed = replace(daily_price_to_domain(original), retrieved_at=refreshed_at, **changes)
    with Session(context.engine) as session:
        stored = session.get(DailyPriceModel, original.id)
        assert apply_daily_price(stored, refreshed, now=refreshed_at) is True
        if change == "identity":
            stored.id = uuid4()
        elif change == "recorded":
            stored.created_at = RECORDED - timedelta(seconds=1)
        session.commit()
    later = await read(context, known_at=refreshed_at + timedelta(seconds=1))
    assert first.rows[0].retrieved_at == RETRIEVED
    assert first.rows[0].last_updated_at == RECORDED
    assert later.rows[0].retrieved_at == refreshed_at
    assert later.rows[0].last_updated_at == refreshed_at
    if change != "recorded":
        assert first.rows[0].recorded_at == later.rows[0].recorded_at
    if change != "source_time":
        assert first.rows[0].source_updated_at == later.rows[0].source_updated_at
    following = evaluate_hebeltrader_targets(
        position=position,
        source=source,
        history=target_history(later),
        qualification=qualification,
        assessment_id=uuid4(),
        assessed_at=refreshed_at + timedelta(seconds=1),
        previous=initial,
    )
    assert following.z1.proof == initial.z1.proof
    assert following.z2.proof == initial.z2.proof
    assert following.z1.event_id == initial.z1.event_id
    assert following.z2.event_id == initial.z2.event_id
    if change == "identical":
        assert first.rows[0].fingerprint == later.rows[0].fingerprint
        assert first.fingerprint == later.fingerprint == qualification.history_fingerprint
        assert initial.input_fingerprint == following.input_fingerprint
        assert following.z1.status == following.z2.status == "PROVEN"
        assert following.z1.current_assessability == "ASSESSABLE"
        assert following.z2.current_assessability == "ASSESSABLE"
        assert following.z1.review_reasons == following.z2.review_reasons == ()
    else:
        assert first.rows[0].fingerprint != later.rows[0].fingerprint
        assert first.fingerprint != later.fingerprint
        assert following.z1.status == following.z2.status == "REVIEW_REQUIRED"
        expected = (
            "ORIGINAL_PRICE_EVIDENCE_REPLACED"
            if change == "identity"
            else "ORIGINAL_PRICE_EVIDENCE_CHANGED"
        )
        assert expected in following.z1.review_reasons
        assert expected in following.z2.review_reasons


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["workspace_id", "underlying_id", "listing_id"])
async def test_foreign_or_missing_identity_never_returns_rows(context, field):
    insert_prices(context, [date(2026, 10, 1)])
    result = await read(context, **{field: uuid4()})
    assert result.binding is None and result.rows == ()
    assert result.status == "MISSING" and result.reasons == ("LISTING_IDENTITY_NOT_FOUND",)
    assert result.stored_range_complete is False


@pytest.mark.asyncio
async def test_missing_primary_is_explicit_and_inactive_exact_listing_is_historical_reference(
    context,
):
    insert_prices(context, [date(2026, 10, 1)])
    with Session(context.engine) as session:
        listing = session.get(ListingModel, context.listing)
        listing.lifecycle_status = LifecycleStatus.INACTIVE
        listing.is_primary = False
        session.commit()
    discovery = await read(context, listing_id=None)
    assert discovery.reasons == ("NO_UNIQUE_ACTIVE_PRIMARY_LISTING",)
    exact = await read(context)
    assert exact.status == "AVAILABLE" and len(exact.rows) == 1
    assert exact.binding.provenance == "CURRENT_REFERENCE_NOT_HISTORICALLY_VERIFIED"


@pytest.mark.asyncio
async def test_original_provider_currency_and_warnings_are_not_replaced_by_current_reference(
    context,
):
    insert_prices(context, [date(2026, 10, 1)], warnings="\n")
    with Session(context.engine) as session:
        listing = session.get(ListingModel, context.listing)
        listing.currency_code = "USD"
        listing.ticker = "CHANGED"
        listing.version = 2
        listing.updated_at = NOW
        session.commit()
    result = await read(context)
    row = result.rows[0]
    assert result.binding.currency == "USD" and row.currency == "EUR"
    assert row.provider == "EODHD" and row.provider_symbol == "SYNTH.XETRA"
    assert row.warnings == ("", "") and row.issues == ("EOD_QUALITY_LIMITED",)
    assert row.source_updated_at == SOURCE_UPDATED


@pytest.mark.asyncio
async def test_adjustment_indication_blocks_automatic_scale_claim_and_never_changes_prices(context):
    insert_prices(context, [date(2026, 10, 1)], adjusted_close=Decimal("52.5"))
    insert_prices(context, [date(2026, 10, 2)])
    insert_prices(context, [date(2026, 10, 3)], currency="USD", adjusted_close=None)
    result = await read(context)
    assert [row.scale_status for row in result.rows] == [
        "ADJUSTMENT_INDICATION_PRESENT",
        "ADJUSTMENT_INDICATION_PRESENT",
        "REQUIRES_EXPLICIT_COMPARISON_QUALIFICATION",
    ]
    assert all(row.high == Decimal("107.25") and row.close == 105 for row in result.rows)
    assert result.rows[0].adjusted_close == Decimal("52.5")
    assert result.rows[2].adjusted_close is None
    assert result.qualification_required == "HISTORICAL_BINDING_AND_COMPARISON_SCALE"


@pytest.mark.asyncio
async def test_row_limit_refuses_partial_history_and_reports_the_sentinel(context, monkeypatch):
    monkeypatch.setattr(module, "MAX_HISTORY_ROWS", 3)
    insert_prices(context, [date(2026, 10, 1) + timedelta(days=index) for index in range(5)])
    result = await read(context)
    assert result.status == "LIMIT_EXCEEDED"
    assert result.rows == () and result.rows_observed == 4 and result.row_limit == 3
    assert not result.stored_range_complete and not result.intervals_complete
    assert result.reasons == ("HISTORICAL_RANGE_ROW_LIMIT_EXCEEDED",)


@pytest.mark.asyncio
@pytest.mark.parametrize("defect", ["timezone", "future_metadata", "future_price", "time_order"])
async def test_unsupported_reference_and_unavailable_original_clocks_fail_closed(context, defect):
    original = insert_prices(context, [date(2026, 10, 1)])[0]
    with Session(context.engine) as session:
        if defect == "timezone":
            session.get(TradingVenueModel, context.venue).timezone = "Not/A_Zone"
        elif defect == "future_metadata":
            session.get(TradingVenueModel, context.venue).updated_at = NOW + timedelta(seconds=1)
        elif defect == "future_price":
            session.get(DailyPriceModel, original.id).updated_at = NOW + timedelta(seconds=1)
        else:
            session.get(DailyPriceModel, original.id).source_updated_at = RECORDED
        session.commit()
    result = await read(context)
    if defect == "timezone":
        assert result.status == "BLOCKED"
        assert result.rows[0].interval_start is None and result.rows[0].interval_end is None
        assert result.rows[0].issues == ("LISTING_TIMEZONE_UNAVAILABLE",)
    elif defect == "future_metadata":
        assert result.status == "BLOCKED"
        assert result.reasons == ("CURRENT_REFERENCE_NOT_KNOWN_AT_CUTOFF",)
    elif defect == "future_price":
        assert result.rows[0].issues == ("DATA_NOT_KNOWN_AT_CUTOFF",)
    else:
        assert result.rows[0].issues == ("INVALID_STORED_TIME_ORDER",)


@pytest.mark.asyncio
async def test_reader_never_autoflushes_pending_caller_changes(context):
    insert_prices(context, [date(2026, 10, 1)])
    with Session(context.engine) as session:
        venue = session.get(TradingVenueModel, context.venue)
        venue.name = "Pending unrelated caller change"
        session.flush = Mock(side_effect=AssertionError("Read attempted autoflush"))
        result = await HebeltraderHistoryReader(SqlSession(session)).read(
            workspace_id=context.workspace,
            underlying_id=context.underlying,
            listing_id=None,
            start_date=date(2026, 10, 1),
            end_date=date(2026, 10, 1),
            known_at=NOW,
        )
        assert result.status == "AVAILABLE"
        session.flush.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("scope", ["valid", "workspace", "listing", "reference", "missing"])
async def test_optional_market_data_identity_must_match_the_same_listing_owner(context, scope):
    instrument_id = uuid4()
    if scope != "missing":
        with Session(context.engine) as session:
            session.add(
                MarketDataInstrumentModel(
                    id=instrument_id,
                    workspace_id=context.workspace if scope != "workspace" else uuid4(),
                    kind="MARKET_REFERENCE" if scope == "reference" else "LISTING",
                    listing_id=(
                        None
                        if scope == "reference"
                        else uuid4() if scope == "listing" else context.listing
                    ),
                    market_reference_id=uuid4() if scope == "reference" else None,
                    created_at=REFERENCE_CREATED,
                )
            )
            session.commit()
    insert_prices(context, [date(2026, 10, 1)], market_data_instrument_id=instrument_id)
    result = await read(context)
    assert result.rows[0].market_data_instrument_id == instrument_id
    assert result.rows[0].issues == (
        () if scope == "valid" else ("MARKET_DATA_INSTRUMENT_SCOPE_MISMATCH",)
    )
