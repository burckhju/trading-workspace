"""Synthetic DOM contract fixtures plus real SQL discovery/selection/adapter tests."""

import asyncio
from dataclasses import replace
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from tests.unit.backend.features.market_data import (
    test_automatic_source_selection as selection_fixtures,
)
from tests.unit.backend.features.market_data.test_automatic_source_selection import (
    decide,
    history,
)
from tests.unit.backend.providers.test_jpmorgan_runtime import Socket

from app.core.config.jpmorgan import JPMorganSettings
from app.core.config.morganstanley import MorganStanleySettings
from app.features.market.persistence.models import CurrencyModel, IssuerModel, TradingVenueModel
from app.features.market_data.domain.enums import MappingStatus
from app.features.market_data.domain.enums import MarketDataProvider as P
from app.features.market_data.domain.issuer_route_evidence import product_url
from app.features.market_data.persistence.models import WarrantProviderMappingModel as Mapping
from app.features.market_data.service.issuer_discovery import discover_issuer_route
from app.features.market_data.service.source_reconciliation import reconcile_warrant_positions
from app.features.product.persistence.models import WarrantListingModel, WarrantModel
from app.features.trade_plan.persistence import models as trade_plan_models  # noqa: F401
from app.providers.issuer_bindings import IssuerBatches, read_bindings
from app.providers.issuer_pages import DiscoveryDeferred, IssuerPageClient, parse_product_page
from app.providers.jpmorgan.adapter import JPMorganWarrantQuoteAdapter
from app.providers.jpmorgan.stream import StreamItem, fetch_batch
from app.providers.morganstanley.adapter import MorganStanleyWarrantQuoteAdapter

context = selection_fixtures.context
selection_context = selection_fixtures.selection_context

NOW = datetime(2026, 9, 28, 12, tzinfo=UTC)
ISIN = "DE000AB12CD8"  # Synthetic; never requested from a live endpoint.


def page(
    provider="JPMORGAN",
    isin=ISIN,
    currency="EUR",
    expiry="31.12.2099",
    prefix="XTEST1",
    include_clock=True,
):
    grid, clock = (
        ("staticgrid", "quotetime")
        if provider == "JPMORGAN"
        else ("instruments", "lastquotetimestamp")
    )
    price_class = "productdetail-box-number" if provider == "JPMORGAN" else "price"
    quote = "".join(
        f'<span class="{price_class}"><strong><span data-field="{field}" '
        f'data-grid="{grid}" data-item="{prefix}{isin}" data-source="lightstreamer">'
        f"1,234</span></strong> {currency}</span>"
        for field in (("bid", "ask", clock) if include_clock else ("bid", "ask"))
    )
    return (
        f"<table><tr><td>ISIN</td><td>{isin}</td></tr>"
        f"<tr><td>WKN</td><td>{isin[5:11]}</td></tr>"
        "<tr><td>Produkttyp</td><td>Optionsschein</td></tr>"
        f"<tr><td>Bewertungstag</td><td>{expiry}</td></tr>"
        f"<tr><td>Währung</td><td>{currency}</td></tr></table>"
        + quote
        + "<table><tr><td>ISIN</td><td>US4581401001</td></tr>"
        "<tr><td>Währung</td><td>USD</td></tr></table>"
    ).encode()


def evidence(provider=P.JPMORGAN, **kwargs):
    return parse_product_page(
        page(provider.value, **kwargs),
        provider.value,
        ISIN,
        product_url(provider.value, ISIN),
        now=NOW,
    )


@pytest.mark.parametrize("provider", list((P.JPMORGAN, P.MORGAN_STANLEY)))
def test_bound_product_fields_ignore_underlying_currency(provider):
    value = evidence(provider)
    assert value.isin == ISIN and value.currency == "EUR" and value.stream_id == "XTEST1" + ISIN
    assert value.valid_through == "2099-12-31"


def test_jpmorgan_price_bindings_verify_route_without_dom_clock():
    value = evidence(include_clock=False)
    assert value.stream_id == "XTEST1" + ISIN
    assert value.currency == "EUR" and value.isin == ISIN


def test_morgan_stanley_clock_binding_is_still_required():
    with pytest.raises(ValueError, match=r"^ISSUER_STREAM_BINDING_UNVERIFIED$"):
        evidence(P.MORGAN_STANLEY, include_clock=False)


@pytest.mark.parametrize("include_clock", [True, False])
@pytest.mark.parametrize("field", ["bid", "ask"])
@pytest.mark.parametrize("change", ["missing", "other_item", "wrong_grid", "wrong_source"])
def test_jpmorgan_requires_both_exact_price_bindings(include_clock, field, change):
    raw = page(include_clock=include_clock)
    start = raw.index(f'data-field="{field}"'.encode())
    end = raw.index(b">", start)
    target = raw[start:end]
    replacements = {
        "missing": (field.encode(), b"ignored"),
        "other_item": (b"XTEST1", b"XOTHER2"),
        "wrong_grid": (b"staticgrid", b"othergrid"),
        "wrong_source": (b"lightstreamer", b"otherfeed"),
    }
    old, new = replacements[change]
    raw = raw[:start] + target.replace(old, new) + raw[end:]
    with pytest.raises(ValueError, match=r"^ISSUER_STREAM_BINDING_UNVERIFIED$"):
        parse_product_page(raw, "JPMORGAN", ISIN, product_url("JPMORGAN", ISIN), now=NOW)


def test_present_jpmorgan_clock_cannot_conflict_with_price_stream():
    raw = page().replace(
        b'data-field="quotetime" data-grid="staticgrid" data-item="XTEST1',
        b'data-field="quotetime" data-grid="staticgrid" data-item="XOTHER2',
    )
    with pytest.raises(ValueError, match=r"^ISSUER_STREAM_BINDING_UNVERIFIED$"):
        parse_product_page(raw, "JPMORGAN", ISIN, product_url("JPMORGAN", ISIN), now=NOW)


@pytest.mark.parametrize(
    "change",
    [
        "foreign_isin",
        "foreign_currency",
        "no_ask_currency",
        "wrong_type",
        "expired",
        "ambiguous_stream",
        "wrong_wkn",
    ],
)
def test_invalid_or_ambiguous_evidence_is_rejected(change):
    raw = page()
    if change == "foreign_isin":
        raw = raw.replace(ISIN.encode(), b"DE000OTHER12")
    if change == "foreign_currency":
        raw = raw.replace(b"EUR", b"USD")
    if change == "no_ask_currency":
        raw = raw.replace(b"</strong> EUR</span>", b"</strong></span>", 1)
    if change == "wrong_type":
        raw = raw.replace(b"Optionsschein", b"Discount-Zertifikat")
    if change == "expired":
        raw = raw.replace(b"31.12.2099", b"01.01.2020")
    if change == "ambiguous_stream":
        raw = raw.replace(b"XTEST1", b"XOTHER2", 1)
    if change == "wrong_wkn":
        raw = raw.replace(b"<td>AB12CD</td>", b"<td>FOREIG</td>")
    with pytest.raises(ValueError, match="ISSUER_"):
        parse_product_page(raw, "JPMORGAN", ISIN, product_url("JPMORGAN", ISIN), now=NOW)


@pytest.mark.parametrize("status", [403, 429])
async def test_http_limits_do_not_retry_or_leak_secrets(status):
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(status, text="private body")

    client = IssuerPageClient(
        client_factory=lambda **kw: httpx.AsyncClient(transport=httpx.MockTransport(respond), **kw)
    )
    with pytest.raises(ValueError, match="ISSUER_PAGE_ACCESS_OR_RATE_LIMIT"):
        await client.fetch("JPMORGAN", ISIN)
    with pytest.raises(DiscoveryDeferred):
        await client.fetch("JPMORGAN", ISIN)
    assert len(requests) == 1 and "cookie" not in requests[0].headers


async def test_redirect_to_untrusted_host_is_never_followed():
    hits = []

    def respond(request):
        hits.append(request)
        return httpx.Response(302, headers={"location": "https://untrusted.invalid/"})

    client = IssuerPageClient(
        client_factory=lambda **kw: httpx.AsyncClient(transport=httpx.MockTransport(respond), **kw)
    )
    with pytest.raises(ValueError, match="ISSUER_REDIRECT_BLOCKED"):
        await client.fetch("JPMORGAN", ISIN)
    assert len(hits) == 1


def prepare(c, provider=P.JPMORGAN):
    with Session(c.database.engine) as session:
        warrant = session.get(WarrantModel, c.warrant)
        warrant.isin, warrant.wkn = ISIN, ISIN[5:11]
        session.get(IssuerModel, warrant.issuer_id).legal_name = (
            "J.P. Morgan SE" if provider == P.JPMORGAN else "Morgan Stanley & Co. International plc"
        )
        session.delete(session.get(Mapping, c.mapping))
        session.commit()
    c.container.jpmorgan = object() if provider == P.JPMORGAN else None
    c.container.morganstanley = object() if provider == P.MORGAN_STANLEY else None
    return SimpleNamespace(fetch=AsyncMock(return_value=evidence(provider)))


@pytest.mark.parametrize(
    "provider,include_clock", [(P.JPMORGAN, True), (P.JPMORGAN, False), (P.MORGAN_STANLEY, True)]
)
@pytest.mark.parametrize("acquisition", ["http", "rendered"])
async def test_new_isin_discovery_selection_and_actual_adapter_batch(
    selection_context, provider, acquisition, include_clock
):
    c = selection_context
    pages = prepare(c, provider)
    pages.fetch.return_value = evidence(provider, include_clock=include_clock)
    hits = []
    if acquisition == "rendered":

        def respond(request):
            hits.append(str(request.url))
            if request.url.host == "issuer-renderer":
                return httpx.Response(
                    200,
                    json={
                        "schema_version": "ISSUER_RENDERED_DOM_V1",
                        "provider": provider.value,
                        "isin": ISIN,
                        "source_url": product_url(provider.value, ISIN),
                        "html": page(provider.value, include_clock=include_clock).decode(),
                        "captured_at": datetime.now(UTC).isoformat(),
                    },
                )
            return httpx.Response(
                200,
                headers={"Content-Type": "text/html"},
                text="<html><title>Product shell</title></html>",
            )

        pages = IssuerPageClient(
            renderer_enabled=True,
            client_factory=lambda **kw: httpx.AsyncClient(
                transport=httpx.MockTransport(respond), **kw
            ),
        )
    assert (await decide(c, allowed=(provider,))).selection_status == "NO_VERIFIED_QUOTE_SOURCE"
    result = await discover_issuer_route(c.database, pages, c.workspace, c.warrant, provider)
    assert result["mapping_created"] is True
    again = await discover_issuer_route(c.database, pages, c.workspace, c.warrant, provider)
    assert again["reason"] == "ISSUER_EXISTING_ROUTE_PRESERVED"
    if acquisition == "rendered":
        assert len(hits) == 2
        with Session(c.database.engine) as session:
            assert (
                session.scalar(select(Mapping)).identity_evidence["acquisition_mode"]
                == "RENDERED_DOM"
            )
    else:
        assert pages.fetch.await_count == 1
    selected = await reconcile_warrant_positions(c.container, c.workspace, c.warrant)
    assert selected["decisions_changed"] == 1 and selected["statuses"] == {"SELECTED": 1}
    assert history(c)[-1].policy_version == provider.value + "_ISSUER_INDICATION_V1"
    assert await read_bindings(c.database, c.workspace, provider) == {ISIN: "XTEST1" + ISIN}
    fields = {"bid": "0.0230", "bidsize": "100", "ask": "0.0000", "asksize": "0"}
    fields.update(
        {"quotetime": "14:00:00" if include_clock else None}
        if provider == P.JPMORGAN
        else {"lastquotetimestamp": "28/09/2026 14:00:00.047"}
    )
    fetcher = AsyncMock(return_value={ISIN: StreamItem(fields, NOW)})
    cls, cfg = (
        (JPMorganWarrantQuoteAdapter, JPMorganSettings)
        if provider == P.JPMORGAN
        else (MorganStanleyWarrantQuoteAdapter, MorganStanleySettings)
    )
    adapter = cls(database=c.database, settings=cfg(enabled=True), fetcher=fetcher)
    quote, cached = await asyncio.gather(
        adapter.get_warrant_listing_quote(c.request), adapter.get_warrant_listing_quote(c.request)
    )
    assert str(quote.data.bid) == "0.0230" and quote.data.ask is None
    assert quote.data.observed_at is None and quote.retrieved_at == cached.retrieved_at == NOW
    if not include_clock:
        assert quote.data.quote_time_text is None
        assert quote.data.quote_time_basis == "DATE_AND_TIMEZONE_UNKNOWN"
        assert "ISSUER_INDICATION_NOT_EXECUTABLE" in quote.warnings
    from app.features.market_data.persistence.models import WarrantQuoteObservationModel
    from app.features.market_data.service.retained_quotes import RetainedWarrantQuoteProvider

    retained = RetainedWarrantQuoteProvider(c.database, adapter, provider)
    stored = await retained.get_warrant_listing_quote(c.request)
    assert stored.data.observed_at is None and stored.data.bid == quote.data.bid
    with Session(c.database.engine) as session:
        row = session.get(
            WarrantQuoteObservationModel,
            (c.workspace, c.request.warrant_listing_id, provider.value),
        )
        assert row is not None and row.payload["data"]["observed_at"] is None
    assert fetcher.await_count == 1
    assert fetcher.await_args.kwargs == {"instruments": {ISIN: "XTEST1" + ISIN}}
    with Session(c.database.engine) as session:
        issuer_id = session.get(WarrantModel, c.warrant).issuer_id
        session.get(IssuerModel, issuer_id).is_active = False
        session.commit()
    with pytest.raises(Exception, match="WARRANT_ACTIVE_QUOTE_IDENTITY_NOT_FOUND"):
        await retained.get_warrant_listing_quote(c.request)
    with Session(c.database.engine) as session:
        session.get(IssuerModel, issuer_id).is_active = True
        session.commit()
    with Session(c.database.engine) as session:
        mapping = session.scalar(select(Mapping))
        mapping.identity_evidence = {**mapping.identity_evidence, "listing_version": 500}
        session.commit()
    with pytest.raises(Exception, match="VERIFIED_MAPPING_REQUIRED"):
        await adapter.get_warrant_listing_quote(c.request)
    assert fetcher.await_count == 1


@pytest.mark.parametrize(
    "change",
    [
        "inactive_issuer",
        "inactive_currency",
        "two_listings",
        "wrong_workspace",
        "disabled_mapping",
        "expired_product",
    ],
)
async def test_preflight_never_registers_ineligible_products(selection_context, change):
    c = selection_context
    pages = prepare(c)
    workspace = c.workspace
    with Session(c.database.engine) as session:
        w = session.get(WarrantModel, c.warrant)
        listing = session.get(WarrantListingModel, c.request.warrant_listing_id)
        if change == "inactive_issuer":
            session.get(IssuerModel, w.issuer_id).is_active = False
        elif change == "inactive_currency":
            session.get(CurrencyModel, "EUR").is_active = False
        elif change == "wrong_workspace":
            workspace = uuid4()
        elif change == "two_listings":
            other_venue = uuid4()
            session.add(
                TradingVenueModel(
                    id=other_venue,
                    mic="XSTU",
                    name="Stuttgart",
                    country_code="DE",
                    timezone="Europe/Berlin",
                    is_active=True,
                    reference_version="test",
                    version=1,
                    created_at=NOW,
                    updated_at=NOW,
                )
            )
            session.add(
                WarrantListingModel(
                    id=uuid4(),
                    workspace_id=c.workspace,
                    warrant_id=c.warrant,
                    trading_venue_id=other_venue,
                    symbol="second",
                    quotation_currency_code="EUR",
                    lifecycle_status="ACTIVE",
                    version=1,
                    created_at=NOW,
                    updated_at=NOW,
                )
            )
        elif change == "expired_product":
            w.lifecycle_status = "INACTIVE"
        elif change == "disabled_mapping":
            session.add(
                Mapping(
                    id=uuid4(),
                    workspace_id=c.workspace,
                    warrant_listing_id=listing.id,
                    provider=P.JPMORGAN,
                    provider_symbol=ISIN,
                    provider_exchange_code="ISSUER",
                    status=MappingStatus.DISABLED,
                    version=1,
                    created_at=NOW,
                    updated_at=NOW,
                )
            )
        session.commit()
    r = await discover_issuer_route(c.database, pages, workspace, c.warrant, P.JPMORGAN)
    assert (
        r["status"]
        == ("NEEDS_MASTER_DATA" if change in {"inactive_currency", "two_listings"} else "BLOCKED")
        and not r["mapping_created"]
    )
    pages.fetch.assert_not_awaited()


async def test_master_data_change_during_http_prevents_registration(selection_context):
    c = selection_context
    pages = prepare(c)

    async def fetch(*args):
        with Session(c.database.engine) as session:
            session.get(WarrantModel, c.warrant).version += 1
            session.commit()
        return evidence()

    pages.fetch = fetch
    r = await discover_issuer_route(c.database, pages, c.workspace, c.warrant, P.JPMORGAN)
    assert r["reason"] == "ISSUER_MASTER_DATA_CHANGED_DURING_DISCOVERY"
    with Session(c.database.engine) as session:
        assert session.scalar(select(Mapping)) is None


async def test_dynamic_stream_binding_controls_item_order_without_prefix_inference():
    socket = Socket(
        ["start('OWN',null,5000,50000);", "z(1,1,'0.0230','100','0.0240','100','14:00:00');"]
    )
    values = await fetch_batch(
        0.05, connector=lambda *a, **kw: socket, instruments={ISIN: "XUNUSUAL9" + ISIN}
    )
    assert list(values) == [ISIN] and values[ISIN].fields["bid"] == "0.0230"
    assert "XUNUSUAL9" + ISIN in "".join(socket.sent)
    assert "X0000010F00" not in "".join(socket.sent)
    assert socket.exited


async def test_foreign_workspace_mapping_cannot_be_taken_over(selection_context):
    c = selection_context
    pages = prepare(c)
    with Session(c.database.engine) as session:
        session.add(
            Mapping(
                id=uuid4(),
                workspace_id=uuid4(),
                warrant_listing_id=uuid4(),
                provider=P.JPMORGAN,
                provider_symbol=ISIN,
                provider_exchange_code="ISSUER",
                status=MappingStatus.ACTIVE,
                validated_at=NOW,
                created_at=NOW,
                updated_at=NOW,
                version=1,
            )
        )
        session.commit()
    result = await discover_issuer_route(c.database, pages, c.workspace, c.warrant, P.JPMORGAN)
    assert result["reason"] == "ISSUER_EXISTING_MAPPING_REQUIRES_REVIEW"
    pages.fetch.assert_not_awaited()


async def test_expired_proof_cannot_authorize_new_route(selection_context):
    c = selection_context
    pages = prepare(c)
    pages.fetch.return_value = replace(evidence(), valid_through="2020-01-01")
    result = await discover_issuer_route(c.database, pages, c.workspace, c.warrant, P.JPMORGAN)
    assert result["reason"] == "ISSUER_PAGE_EVIDENCE_INVALID"
    with Session(c.database.engine) as session:
        assert session.scalar(select(Mapping)) is None


async def test_provider_budget_is_shared_and_never_reuses_another_workspace(monkeypatch):
    from app.providers import issuer_bindings as module

    monkeypatch.setattr(module, "read_bindings", AsyncMock(return_value={ISIN: "XTEST1" + ISIN}))
    fetcher = AsyncMock(return_value={ISIN: object()})
    cache = IssuerBatches(None, P.JPMORGAN, JPMorganSettings(enabled=True), fetcher)
    identity = SimpleNamespace(isin=ISIN, stream_id="XTEST1" + ISIN)
    workspace = uuid4()
    await cache.get(workspace, identity)
    cache.invalidate_routes()
    assert (await cache.get(workspace, identity))[2] is True
    with pytest.raises(ValueError, match="BATCH_COOLDOWN"):
        await cache.get(uuid4(), identity)
    assert fetcher.await_count == 1


async def test_many_products_rotate_batches_with_one_shared_budget(monkeypatch):
    from app.providers import issuer_bindings as module

    bindings = {f"ISIN{i:03d}": f"STREAM{i:03d}" for i in range(65)}
    monkeypatch.setattr(module, "read_bindings", AsyncMock(return_value=bindings))
    clock = [100.0]
    monkeypatch.setattr(module, "monotonic", lambda: clock[0])
    fetcher = AsyncMock(return_value={})
    cache = IssuerBatches(None, P.JPMORGAN, JPMorganSettings(enabled=True), fetcher)
    identity = SimpleNamespace(isin="ISIN000", stream_id=bindings["ISIN000"])
    workspace = uuid4()
    await cache.get(workspace, identity)
    assert len(fetcher.await_args.kwargs["instruments"]) == 64
    clock[0] += 61
    with pytest.raises(ValueError, match="BATCH_COOLDOWN"):
        await cache.get(workspace, identity)
    assert fetcher.await_args.kwargs["instruments"] == {"ISIN064": "STREAM064"}
    assert fetcher.await_count == 2


async def test_discovery_lane_does_not_block_quotes_and_has_short_deferred_retry(monkeypatch):
    from tests.unit.backend.features.market_data.test_refresh import runtime

    from app.features.market_data.service import refresh as module
    from app.features.market_data.service.refresh_catalog import RefreshInstrument

    value = runtime(auto_configure=False)
    value.settings.auto_discover_issuer_routes = True
    item = RefreshInstrument(uuid4(), "New product", ISIN, issuer="J.P. Morgan SE")
    value.container = SimpleNamespace(
        database=None, jpmorgan=object(), morganstanley=None, frankfurt=None, vontobel=None
    )
    monkeypatch.setattr(module, "read_catalog", AsyncMock(return_value=([item], [])))
    monkeypatch.setattr(module, "read_issuer_route_groups", AsyncMock(return_value=(set(), set())))
    started, release, quoted = asyncio.Event(), asyncio.Event(), asyncio.Event()

    async def discover(*args):
        started.set()
        await release.wait()
        raise DiscoveryDeferred(15)

    async def quote(*args, **kw):
        quoted.set()
        return {"reason": "QUOTE_OBSERVATIONS_AVAILABLE"}

    value._configure_issuer = discover
    value._warrant = quote
    await value.run_once(wait_for_completion=False)
    try:
        await asyncio.wait_for(started.wait(), 1)
        await asyncio.wait_for(quoted.wait(), 1)
        release.set()
        await asyncio.gather(*value._lane_tasks.values())
        job = value.jobs[f"ISSUER_MAPPING:JPMORGAN:{item.id}"]
        assert job["status"] == "DEFERRED" and job["retry_after_seconds"] == 15
        assert job["lane"] == "ISSUER_DISCOVERY"
    finally:
        await value.stop()


def test_migration_preserves_legacy_data_and_refuses_evidence_loss():
    import importlib.util
    from pathlib import Path

    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import create_engine, text

    import app

    migration = (
        Path(app.__file__).resolve().parents[1]
        / "migrations/versions/20260928_0042_issuer_route_evidence.py"
    )
    spec = importlib.util.spec_from_file_location("evidence_migration", migration)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE warrant_provider_mappings "
                "(id INTEGER PRIMARY KEY, provider_symbol TEXT)"
            )
        )
        connection.execute(text("INSERT INTO warrant_provider_mappings VALUES (1,'legacy')"))
        with Operations.context(MigrationContext.configure(connection)):
            module.upgrade()
            assert connection.execute(
                text("SELECT provider_symbol,identity_evidence FROM warrant_provider_mappings")
            ).one() == ("legacy", None)
            connection.execute(text("UPDATE warrant_provider_mappings SET identity_evidence='{}'"))
            with pytest.raises(RuntimeError, match="evidence exists"):
                module.downgrade()
