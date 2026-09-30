import asyncio
from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import TypeAdapter
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config.morganstanley import MorganStanleySettings
from app.features.market.persistence.models import TradingVenueModel
from app.features.market_data.domain.enums import (
    CacheStatus,
    MappingStatus,
    MarketDataCapability,
    MarketDataProvider,
    QualityStatus,
)
from app.features.market_data.domain.models import WarrantQuoteSnapshot
from app.features.market_data.persistence.models import (
    WarrantProviderMappingModel,
    WarrantQuoteObservationModel,
)
from app.features.market_data.persistence.quote_identity import verified_identity
from app.features.market_data.service.quote_coverage import (
    ProductRecord,
    QuoteCoverageService,
    RouteRecord,
)
from app.features.market_data.service.retained_quotes import (
    RetainedWarrantQuoteProvider,
)
from app.features.market_data.service.types import MarketDataResult, WarrantQuoteRequest
from app.features.position_monitoring.service.product_valuation import (
    ProductPositionValuationService,
)
from app.features.product.persistence.models import WarrantListingModel, WarrantModel
from app.providers import issuer_bindings
from app.providers.morganstanley import adapter
from app.providers.morganstanley.adapter import (
    MorganStanleyWarrantQuoteAdapter,
    parse_item,
)
from app.providers.morganstanley.products import INSTRUMENTS
from app.providers.morganstanley.stream import StreamItem, decode_fields, fetch_batch
from app.tools.configure_morganstanley_positions import apply_plan, digest, plan

NOW = datetime(2026, 9, 22, 17, 36, tzinfo=UTC)
ISIN = next(iter(INSTRUMENTS))


def stream_item(**values):
    return StreamItem(
        (
            dict(
                bid="0.3200",
                bidsize="75000",
                ask="0.3300",
                asksize="75000",
                lastquotetimestamp="21/09/2026 20:12:52.047",
                **values,
            )
            if not values
            else {
                **dict(
                    bid="0.3200",
                    bidsize="75000",
                    ask="0.3300",
                    asksize="75000",
                    lastquotetimestamp="21/09/2026 20:12:52.047",
                ),
                **values,
            }
        ),
        NOW,
    )


def request():
    return WarrantQuoteRequest(uuid4(), uuid4(), uuid4(), NOW, expected_currency="EUR")


def identity():
    return SimpleNamespace(isin=ISIN, wkn="MJ3QFV", currency="EUR", stream_id=INSTRUMENTS[ISIN])


def result(quote):
    return MarketDataResult(
        quote,
        MarketDataProvider.MORGAN_STANLEY,
        MarketDataCapability.WARRANT_LISTING_QUOTE,
        uuid4(),
        NOW,
        CacheStatus.MISS,
        QualityStatus.VALID,
        (),
        0,
        0,
    )


class Socket:
    def __init__(self, frames):
        self.frames = list(frames)
        self.sent = []
        self.exited = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        self.exited = True

    async def send(self, value):
        self.sent.append(value)

    async def recv(self):
        if self.frames:
            return self.frames.pop(0)
        return await asyncio.Future()


def snapshot(index):
    return f"z(1,{index},'0.3200','75000','0.3300','75000','21/09/2026 20:12:52.047');"


def test_full_local_time_is_preserved_without_timezone_and_zero_ask_is_absent():
    q = parse_item(stream_item(ask="0.0000", asksize="0"), request(), identity())
    assert q.bid == Decimal("0.3200") and q.ask is None and q.ask_volume == 0
    assert q.quote_time_text == "21/09/2026 20:12:52.047" and q.observed_at is None
    assert q.quote_time_basis == "LOCAL_DATETIME_TIMEZONE_UNKNOWN"
    restored = TypeAdapter(WarrantQuoteSnapshot).validate_json(
        TypeAdapter(WarrantQuoteSnapshot).dump_json(q)
    )
    assert restored == q


@pytest.mark.parametrize(
    "changes",
    [
        dict(ask="0.1"),
        dict(bid="NaN"),
        dict(bidsize="-1"),
        dict(lastquotetimestamp="24:01:00"),
        dict(lastquotetimestamp="31/02/2026 19:35:17"),
    ],
)
def test_bad_or_changed_schema_fails_explicitly(changes):
    with pytest.raises(ValueError):
        parse_item(stream_item(**changes), request(), identity())


def test_legacy_bid_quotes_still_require_timestamp():
    q = parse_item(stream_item(), request(), identity())
    with pytest.raises(ValueError):
        replace(q, source_mode=None)
    with pytest.raises(ValueError):
        replace(q, observed_at=NOW)


def test_decoder_clears_explicit_null_and_processes_time_only_delta():
    fields = stream_item().fields
    clock, _ = decode_fields("4,'21/09/2026 20:12:53.047'", fields)
    assert (
        clock["bid"] == fields["bid"] and clock["lastquotetimestamp"] == "21/09/2026 20:12:53.047"
    )
    lost, _ = decode_fields("'#','#',3", fields)
    assert lost["bid"] is None and lost["bidsize"] is None and lost["ask"] == fields["ask"]
    with pytest.raises(ValueError):
        decode_fields("__import__('os')", fields)


async def test_batch_merges_per_item_and_destroys_own_session():
    socket = Socket(
        [
            "start('OWN',null,5000,50000);",
            snapshot(1),
            "d(1,1,2,'0.0000','0','21/09/2026 20:12:54.047');"
            + "".join(snapshot(i) for i in range(2, 11)),
        ]
    )
    batch = await fetch_batch(0.1, connector=lambda *a, **kw: socket)
    assert len(batch) == 10 and batch[ISIN].fields["ask"] == "0.0000"
    assert batch[list(INSTRUMENTS)[1]].fields["ask"] == "0.3300"
    assert socket.exited and "LS_op=destroy&LS_session=OWN" in socket.sent[-1]
    assert "LS_password" not in "".join(socket.sent)


async def test_partial_batch_does_not_invent_missing_product():
    socket = Socket(["start('OWN',null,5000,50000);", snapshot(1)])
    batch = await fetch_batch(0.02, connector=lambda *a, **kw: socket)
    assert list(batch) == [ISIN] and socket.exited


@pytest.mark.parametrize(
    "bad",
    [
        "z(2,1,'1','1','2','1','10:00:00');",
        "d(1,1,5);",
        "error(7,1,1,'private-body');",
        "loop(0);",
        "z(1,1,evil());",
    ],
)
async def test_transport_protocol_errors_are_not_silently_ignored(bad):
    socket = Socket(["start('OWN',null,5000,50000);", bad])
    with pytest.raises(ValueError, match="MORGAN_STANLEY_") as e:
        await fetch_batch(0.02, connector=lambda *a, **kw: socket)
    assert "private-body" not in str(e.value) and socket.exited


class DummyDatabase:
    @asynccontextmanager
    async def session_context(self):
        yield None


async def test_batch_cache_reuses_receipt_time_and_unmapped_request_does_not_connect(
    monkeypatch,
):
    monkeypatch.setattr(adapter, "read_quote_identity", AsyncMock(return_value=identity()))
    monkeypatch.setattr(
        issuer_bindings, "read_bindings", AsyncMock(return_value={ISIN: INSTRUMENTS[ISIN]})
    )
    fetcher = AsyncMock(return_value={ISIN: stream_item()})
    provider = MorganStanleyWarrantQuoteAdapter(
        database=DummyDatabase(),
        settings=MorganStanleySettings(enabled=True),
        fetcher=fetcher,
    )
    req = request()
    a, b = await asyncio.gather(
        provider.get_warrant_listing_quote(req),
        provider.get_warrant_listing_quote(req),
    )
    assert fetcher.await_count == 1 and a.retrieved_at == b.retrieved_at == NOW
    assert b.cache_status == CacheStatus.HIT
    monkeypatch.setattr(adapter, "read_quote_identity", AsyncMock(return_value=None))
    with pytest.raises(Exception, match="MORGAN_STANLEY_VERIFIED_MAPPING_REQUIRED"):
        await provider.get_warrant_listing_quote(request())
    assert fetcher.await_count == 1


class AsyncSessionBridge:
    def __init__(self, session):
        self.session = session

    async def execute(self, stmt):
        return self.session.execute(stmt)

    async def scalar(self, stmt):
        return self.session.scalar(stmt)

    async def get(self, model, key):
        return self.session.get(model, key)

    def add(self, row):
        self.session.add(row)

    async def commit(self):
        self.session.commit()


class SqlDatabase:
    def __init__(self):
        self.engine = create_engine("sqlite://")

    @asynccontextmanager
    async def session_context(self):
        with Session(self.engine, expire_on_commit=False) as s:
            yield AsyncSessionBridge(s)


@pytest.fixture
def route():
    db = SqlDatabase()
    for m in (
        TradingVenueModel,
        WarrantModel,
        WarrantListingModel,
        WarrantProviderMappingModel,
        WarrantQuoteObservationModel,
    ):
        m.__table__.create(db.engine)
    req = request()
    common = dict(created_at=NOW, updated_at=NOW, version=1)
    venue = TradingVenueModel(
        id=uuid4(),
        mic="XSTU",
        name="Stuttgart",
        country_code="DE",
        timezone="Europe/Berlin",
        is_active=True,
        reference_version="test",
        **common,
    )
    warrant = WarrantModel(
        id=uuid4(),
        workspace_id=req.workspace_id,
        issuer_id=uuid4(),
        underlying_id=uuid4(),
        display_name="MorganStanley",
        isin=ISIN,
        wkn="MJ3QFV",
        lifecycle_status="ACTIVE",
        **common,
    )
    listing = WarrantListingModel(
        id=req.warrant_listing_id,
        workspace_id=req.workspace_id,
        warrant_id=warrant.id,
        trading_venue_id=venue.id,
        symbol=None,
        quotation_currency_code="EUR",
        lifecycle_status="ACTIVE",
        **common,
    )
    mapping = WarrantProviderMappingModel(
        id=uuid4(),
        workspace_id=req.workspace_id,
        warrant_listing_id=listing.id,
        provider=MarketDataProvider.MORGAN_STANLEY,
        provider_symbol=ISIN,
        provider_exchange_code="ISSUER",
        status=MappingStatus.ACTIVE,
        validated_at=NOW,
        **common,
    )
    with Session(db.engine, expire_on_commit=False) as s:
        s.add_all([venue, warrant, listing, mapping])
        s.commit()
    yield SimpleNamespace(
        db=db, req=req, venue=venue, warrant=warrant, listing=listing, mapping=mapping
    )
    db.engine.dispose()


async def test_real_mapping_identity_and_null_snapshot_replace_old_quote(route):
    r = route
    q = parse_item(stream_item(), r.req, identity())
    provider = AsyncMock()
    provider.get_warrant_listing_quote.return_value = result(q)
    retained = RetainedWarrantQuoteProvider(r.db, provider, MarketDataProvider.MORGAN_STANLEY)
    assert (await retained.get_warrant_listing_quote(r.req)).data.bid == Decimal(".3200")
    provider.get_warrant_listing_quote.return_value = result(
        parse_item(
            stream_item(bid=None, ask=None, bidsize=None, asksize=None, lastquotetimestamp=None),
            r.req,
            identity(),
        )
    )
    withdrawn = await retained.get_warrant_listing_quote(r.req)
    assert withdrawn.data.bid is None and withdrawn.data.ask is None and not withdrawn.data.retained
    provider.get_warrant_listing_quote.side_effect = ValueError("outage")
    after = await retained.get_warrant_listing_quote(r.req)
    assert after.data.bid is None and after.data.refresh_error is not None
    assert verified_identity(
        r.req.workspace_id,
        r.listing,
        r.warrant,
        r.venue,
        MarketDataProvider.MORGAN_STANLEY,
        r.mapping,
    )
    r.warrant.isin = "DE000JE7KTY8"
    r.mapping.provider_symbol = r.warrant.isin
    assert (
        verified_identity(
            r.req.workspace_id,
            r.listing,
            r.warrant,
            r.venue,
            MarketDataProvider.MORGAN_STANLEY,
            r.mapping,
        )
        is None
    )


async def test_unknown_timestamp_valuation_exposes_price_and_time_but_no_executable_value():
    req = request()
    trade, position, evaluation = (
        SimpleNamespace(id=uuid4(), workspace_id=req.workspace_id, product_evaluation_id=uuid4()),
        SimpleNamespace(id=uuid4(), open_quantity=10, cost_basis=Decimal("2")),
        SimpleNamespace(warrant_listing_id=req.warrant_listing_id),
    )
    listing = SimpleNamespace(id=req.warrant_listing_id, symbol=None, quotation_currency_code="EUR")
    s = SimpleNamespace(
        execute=AsyncMock(return_value=SimpleNamespace(one_or_none=lambda: (trade, position))),
        scalar=AsyncMock(side_effect=[None, evaluation, listing]),
    )

    class DB:
        @asynccontextmanager
        async def session_context(self):
            yield s

    provider = SimpleNamespace(
        get_warrant_listing_quote=AsyncMock(
            return_value=result(parse_item(stream_item(), req, identity()))
        )
    )
    value = await ProductPositionValuationService(database=DB(), quote_provider=provider).for_trade(
        trade.id
    )
    assert value.status == "INDICATIVE" and value.analysis_usable
    assert value.quote_time_text == "21/09/2026 20:12:52.047" and value.quote_observed_at is None
    assert value.quote_age_seconds is None and value.quote_age_limit_exceeded is None
    assert value.analysis_market_value == Decimal("3.2000")
    assert value.market_value is None and not value.valuation_usable and not value.execution_usable


def test_coverage_reports_unknown_age_instead_of_old_or_fresh_bid(route):
    r = route
    q = replace(parse_item(stream_item(), r.req, identity()), assessed_at=NOW)
    payload = TypeAdapter(MarketDataResult[WarrantQuoteSnapshot | None]).dump_python(
        result(q), mode="json"
    )
    row = RouteRecord(
        "MORGAN_STANLEY",
        r.listing.id,
        "XSTU",
        "EUR",
        r.mapping.id,
        "ACTIVE",
        ISIN,
        "ISSUER",
        NOW,
        "ROUTE_IDENTITY_VERIFIED",
        "same",
        "same",
        payload,
    )
    product = ProductRecord(
        r.warrant.id, "Call", ISIN, "MJ3QFV", "MorganStanley", True, False, (row,)
    )
    coverage = QuoteCoverageService._route(row, product, True, NOW, {})
    assert coverage.observation_status == "QUOTE_TIMESTAMP_UNKNOWN"
    assert coverage.quote_time_text == "21/09/2026 20:12:52.047" and coverage.age_seconds is None


async def test_changed_preview_hash_aborts_before_writes(monkeypatch):
    from app.tools import configure_morganstanley_positions as module

    s = SimpleNamespace(
        execute=AsyncMock(),
        commit=AsyncMock(),
        add=lambda row: pytest.fail("unexpected write"),
    )

    class DB:
        @asynccontextmanager
        async def session_context(self):
            yield s

    monkeypatch.setattr(module, "plan", AsyncMock(return_value={"preview_sha256": "changed"}))
    with pytest.raises(ValueError, match="MORGAN_STANLEY_PREVIEW_CHANGED"):
        await apply_plan(DB(), uuid4(), "old", {})
    s.commit.assert_not_awaited()
    assert "SERIALIZABLE" in str(s.execute.call_args.args[0])


@pytest.mark.parametrize(
    "status,count",
    [("NO_VERIFIED_QUOTE_SOURCE", 1), ("SELECTED", 0), ("AMBIGUOUS_SOURCE", 0)],
)
async def test_mapping_preview_preserves_existing_source_decisions(route, status, count):
    r = route
    selection = SimpleNamespace(id=uuid4(), selection_status=status, selection_reason=status)
    positions = [
        (
            SimpleNamespace(
                id=uuid4(),
                open_quantity=10,
                cost_basis=Decimal("2"),
                last_execution_at=NOW,
            ),
            SimpleNamespace(id=uuid4(), origin="EXTERNAL", product_evaluation_id=None),
            r.warrant,
        )
    ]
    s = SimpleNamespace(
        execute=AsyncMock(
            side_effect=[
                SimpleNamespace(all=lambda: positions),
                SimpleNamespace(all=lambda: [(r.listing, r.venue)]),
            ]
        ),
        scalars=AsyncMock(side_effect=[[selection], []]),
    )
    preview = await plan(s, r.req.workspace_id)
    assert preview["eligible_count"] == count
    if count:
        assert preview["eligible"][0]["listing_id"] == str(r.listing.id)
        assert preview["eligible"][0]["provider_exchange_code"] == "ISSUER"
    else:
        assert preview["excluded"][0]["reason"] == "EXISTING_SELECTION_PRESERVED"
    payload = {k: v for k, v in preview.items() if k not in ("preview_sha256", "eligible_count")}
    assert preview["preview_sha256"] == digest(payload)


@pytest.mark.parametrize("existing_mapping", [True, False])
@pytest.mark.parametrize("quote_state", ["valid", "missing_bid", "missing_timestamp"])
async def test_sql_preview_apply_and_repeat_preserve_position_and_populate_observation(
    route,
    existing_mapping,
    quote_state,
):
    from sqlalchemy import select, text

    from app.features.market.persistence.models import CurrencyModel
    from app.features.market_data.persistence.models import (
        PositionQuoteSourceSelectionModel,
    )
    from app.features.trade_plan.persistence import (
        models as _trade_plan_models,  # noqa: F401
    )
    from app.features.trade_position.persistence.models import PositionModel, TradeModel

    r = route
    if not existing_mapping:
        with Session(r.db.engine) as session:
            session.delete(session.get(WarrantProviderMappingModel, r.mapping.id))
            session.commit()
    for model in (
        CurrencyModel,
        TradeModel,
        PositionModel,
        PositionQuoteSourceSelectionModel,
    ):
        model.__table__.create(r.db.engine)
    # Mirror the PostgreSQL partial unique index explicitly on SQLite.
    with r.db.engine.begin() as connection:
        connection.execute(text("DROP INDEX uq_position_quote_source_selections_active_position"))
        connection.execute(
            text(
                "CREATE UNIQUE INDEX uq_position_quote_source_selections_active_position "
                "ON position_quote_source_selections (workspace_id,position_id) "
                "WHERE superseded_at IS NULL"
            )
        )
    trade_id, position_id, old_id = uuid4(), uuid4(), uuid4()
    with Session(r.db.engine) as s:
        s.add_all(
            [
                CurrencyModel(
                    code="EUR",
                    name="Euro",
                    minor_unit=2,
                    is_active=True,
                    reference_version="test",
                    created_at=NOW,
                    updated_at=NOW,
                ),
                TradeModel(
                    id=trade_id,
                    workspace_id=r.req.workspace_id,
                    product_id=r.warrant.id,
                    origin="EXTERNAL",
                    created_at=NOW,
                    created_by=uuid4(),
                ),
                PositionModel(
                    id=position_id,
                    trade_id=trade_id,
                    product_id=r.warrant.id,
                    open_quantity=10,
                    cost_basis=Decimal("2"),
                    average_entry_price=Decimal(".2"),
                    opened_at=NOW,
                    last_execution_at=NOW,
                ),
                PositionQuoteSourceSelectionModel(
                    id=old_id,
                    workspace_id=r.req.workspace_id,
                    position_id=position_id,
                    selection_status="NO_VERIFIED_QUOTE_SOURCE",
                    selection_reason="NO_VERIFIED_QUOTE_SOURCE",
                    policy_version="TEST",
                    evidence={},
                    selected_at=NOW,
                ),
            ]
        )
        s.commit()

    class Bridge(AsyncSessionBridge):
        async def execute(self, stmt):
            if str(stmt) == "SET TRANSACTION ISOLATION LEVEL SERIALIZABLE":
                return None  # SQLite unit harness cannot verify PostgreSQL MVCC.
            return await super().execute(stmt)

        async def scalars(self, stmt):
            return self.session.scalars(stmt)

        async def flush(self):
            self.session.flush()

    class DB:
        @asynccontextmanager
        async def session_context(self):
            with Session(r.db.engine, expire_on_commit=False) as s:
                yield Bridge(s)

    db = DB()
    async with db.session_context() as s:
        preview = await plan(s, r.req.workspace_id)
    assert preview["eligible_count"] == 1
    if quote_state != "valid":
        bad_item = (
            stream_item(bid=None, bidsize=None)
            if quote_state == "missing_bid"
            else stream_item(lastquotetimestamp=None)
        )
        with pytest.raises(ValueError, match=r"MORGAN_STANLEY_.*(BID_REQUIRED|TIMESTAMP_MISSING)"):
            await apply_plan(db, r.req.workspace_id, preview["preview_sha256"], {ISIN: bad_item})
        async with db.session_context() as s:
            assert (await s.get(PositionQuoteSourceSelectionModel, old_id)).superseded_at is None
            assert (
                await s.get(
                    WarrantQuoteObservationModel,
                    (r.req.workspace_id, r.req.warrant_listing_id, "MORGAN_STANLEY"),
                )
                is None
            )
        return
    changed = await apply_plan(
        db, r.req.workspace_id, preview["preview_sha256"], {ISIN: stream_item()}
    )
    assert changed["reselected"] == 1
    async with db.session_context() as s:
        again = await plan(s, r.req.workspace_id)
        assert again["eligible_count"] == 0
        old = await s.get(PositionQuoteSourceSelectionModel, old_id)
        assert old.superseded_at is not None
        position = await s.get(PositionModel, position_id)
        assert position.open_quantity == 10 and position.cost_basis == Decimal("2")
        current = await s.scalar(
            select(PositionQuoteSourceSelectionModel).where(
                PositionQuoteSourceSelectionModel.superseded_at.is_(None)
            )
        )
        assert current.provider == "MORGAN_STANLEY"
        observation = await s.get(
            WarrantQuoteObservationModel,
            (r.req.workspace_id, r.req.warrant_listing_id, "MORGAN_STANLEY"),
        )
        assert observation.payload["data"]["quote_time_text"] == "21/09/2026 20:12:52.047"
        assert observation.payload["data"]["observed_at"] is None


def test_user_snapshots_keep_decimal_precision_date_fractional_seconds_and_zero_volume():
    import json
    from pathlib import Path

    from app.providers.morganstanley.adapter import quote_warnings
    from app.providers.morganstanley.stream import SCHEMA

    fixture = (
        Path(__file__).resolve().parents[3] / "fixtures/morganstanley/user-snapshots-20260921.json"
    )
    captured = json.loads(fixture.read_text())
    quotes = {}
    for row in captured["items"]:
        q = parse_item(
            StreamItem(dict(zip(SCHEMA, row["fields"], strict=True)), NOW),
            request(),
            SimpleNamespace(isin=row["isin"], wkn=row["isin"][5:11], currency="EUR"),
        )
        quotes[row["isin"]] = q
        assert q.observed_at is None
        assert q.quote_time_text == row["fields"][4]
        restored = TypeAdapter(WarrantQuoteSnapshot).validate_json(
            TypeAdapter(WarrantQuoteSnapshot).dump_json(q)
        )
        assert restored == q
    assert len(quotes) == 10
    assert sum(q.bid is not None for q in quotes.values()) == 9
    assert quotes["DE000MJ3QMM4"].quote_time_text.endswith(".77")
    assert quotes["DE000MN25S42"].quote_time_text.endswith(".03")
    assert quotes["DE000MJ3QFV9"].ask is None
    assert quotes["DE000MJ7DUX3"].bid_volume == quotes["DE000MJ7DUX3"].ask_volume == 0
    assert "BID_WITHOUT_POSITIVE_VOLUME" in quote_warnings(quotes["DE000MJ7DUX3"])
    empty = quotes["DE000MN2ZUN2"]
    assert empty.bid is empty.ask is empty.quote_time_text is None
    assert empty.quote_time_basis == "TIMESTAMP_MISSING"


async def test_expired_product_is_explicitly_excluded_before_mapping_and_selection_queries(route):
    r = route
    r.warrant.isin = "DE000MN2ZUN2"
    r.warrant.wkn = "MN2ZUN"
    r.mapping.provider_symbol = r.warrant.isin
    s = SimpleNamespace(
        execute=AsyncMock(
            return_value=SimpleNamespace(
                all=lambda: [(SimpleNamespace(id=uuid4()), SimpleNamespace(id=uuid4()), r.warrant)]
            )
        ),
        scalars=AsyncMock(side_effect=AssertionError("must not select expired product")),
    )
    preview = await plan(s, r.req.workspace_id)
    assert preview["eligible_count"] == 0
    assert preview["excluded"][0]["reason"] == "PRODUCT_EXPIRED_SETTLEMENT_REVIEW_REQUIRED"
    assert (
        verified_identity(
            r.req.workspace_id,
            r.listing,
            r.warrant,
            r.venue,
            MarketDataProvider.MORGAN_STANLEY,
            r.mapping,
        )
        is None
    )
    s.scalars.assert_not_awaited()


async def test_new_batch_never_inherits_missing_item_or_fields_from_old_batch(monkeypatch):
    monkeypatch.setattr(adapter, "read_quote_identity", AsyncMock(return_value=identity()))
    monkeypatch.setattr(
        issuer_bindings, "read_bindings", AsyncMock(return_value={ISIN: INSTRUMENTS[ISIN]})
    )
    fetcher = AsyncMock(side_effect=[{ISIN: stream_item()}, {}])
    provider = MorganStanleyWarrantQuoteAdapter(
        database=DummyDatabase(), settings=MorganStanleySettings(enabled=True), fetcher=fetcher
    )
    assert (await provider.get_warrant_listing_quote(request())).data.bid is not None
    provider._batches.batches.clear()
    provider._batches.next_fetch = 0
    with pytest.raises(Exception, match="MORGAN_STANLEY_SNAPSHOT_MISSING"):
        await provider.get_warrant_listing_quote(request())
    assert fetcher.await_count == 2


async def test_disabled_source_never_connects():
    fetcher = AsyncMock()
    provider = MorganStanleyWarrantQuoteAdapter(
        database=DummyDatabase(), settings=MorganStanleySettings(), fetcher=fetcher
    )
    with pytest.raises(Exception, match="MORGAN_STANLEY_DISABLED"):
        await provider.get_warrant_listing_quote(request())
    fetcher.assert_not_awaited()
