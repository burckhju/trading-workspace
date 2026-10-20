"""Boundary tests for rendered acquisition; no public site or user database is contacted."""

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.features.market.contracts import is_canonical_isin
from app.features.market_data.domain.enums import MarketDataProvider as P
from app.features.market_data.domain.issuer_route_evidence import product_url
from app.features.market_data.service.issuer_discovery import discover_issuer_route
from app.features.product.persistence.models import WarrantListingModel, WarrantModel
from app.providers.issuer_pages import IssuerPageClient
from app.providers.issuer_rendered import fetch_rendered_page
from app.providers.issuer_renderer.api import RenderRequest
from app.providers.issuer_renderer.browser import (
    ACCESS_STATE,
    SANITIZED_DOM,
    IssuerRenderer,
    RenderFailure,
    allowed_resource,
)
from tests.unit.backend.features.market_data import (
    test_issuer_route_discovery as discovery_fixtures,
)
from tests.unit.backend.features.market_data.test_issuer_route_discovery import (
    ISIN,
    page,
    prepare,
)

context = discovery_fixtures.context
selection_context = discovery_fixtures.selection_context


@pytest.mark.parametrize("isin", ["DE000MJK091", "DE000AB12CD1", "de000je7kty8", None])
def test_bad_identifier_cannot_enter_rendering(isin):
    assert not is_canonical_isin(isin)
    with pytest.raises(ValidationError):
        RenderRequest(provider="JPMORGAN", isin=isin)


def test_renderer_accepts_no_arbitrary_url_or_credentials():
    assert RenderRequest(provider="JPMORGAN", isin=ISIN).isin == ISIN
    with pytest.raises(ValidationError):
        RenderRequest(provider="JPMORGAN", isin=ISIN, url="http://127.0.0.1", password="secret")


@pytest.mark.parametrize(
    "change,reason",
    [
        ("missing", "ISSUER_LISTING_MISSING"),
        ("inactive", "ISSUER_NO_ACTIVE_EUR_LISTING"),
        ("bad_isin", "ISSUER_ISIN_INVALID"),
        ("bad_checksum", "ISSUER_ISIN_INVALID"),
    ],
)
async def test_master_data_diagnostics_precede_all_network_access(
    selection_context, change, reason
):
    c = selection_context
    pages = prepare(c)
    with Session(c.database.engine) as session:
        listing = session.get(WarrantListingModel, c.request.warrant_listing_id)
        if change == "missing":
            session.delete(listing)
        elif change == "inactive":
            listing.lifecycle_status = "INACTIVE"
        else:
            warrant = session.get(WarrantModel, c.warrant)
            warrant.isin = "DE000MJK091" if change == "bad_isin" else "DE000AB12CD1"
            warrant.wkn = None
        session.commit()
    result = await discover_issuer_route(c.database, pages, c.workspace, c.warrant, P.JPMORGAN)
    assert result["status"] == "NEEDS_MASTER_DATA" and result["reason"] == reason
    assert result["mapping_created"] is False
    pages.fetch.assert_not_awaited()


@pytest.mark.parametrize("denial", [401, 403, 429, "challenge"])
async def test_http_access_rejection_never_uses_browser_fallback(denial):
    calls = []

    def respond(request):
        calls.append(request.url)
        return httpx.Response(
            200 if denial == "challenge" else denial,
            headers={"Content-Type": "text/html"},
            text="<title>Verify you are human</title>",
        )

    client = IssuerPageClient(
        renderer_enabled=True,
        client_factory=lambda **kw: httpx.AsyncClient(transport=httpx.MockTransport(respond), **kw),
    )
    with pytest.raises(ValueError, match="ISSUER_PAGE_ACCESS"):
        await client.fetch("JPMORGAN", ISIN)
    assert len(calls) == 1


@pytest.mark.parametrize("change", ["isin", "url", "old", "naive", "future", "array"])
async def test_renderer_response_must_match_request_and_capture_time(change):
    payload = {
        "schema_version": "ISSUER_RENDERED_DOM_V1",
        "provider": "JPMORGAN",
        "isin": ISIN,
        "source_url": product_url("JPMORGAN", ISIN),
        "html": page().decode(),
        "captured_at": datetime.now(UTC).isoformat(),
    }
    if change == "isin":
        payload["isin"] = "DE000JE7KTY8"
    if change == "url":
        payload["source_url"] = "https://example.invalid/"
    if change == "old":
        payload["captured_at"] = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    if change == "future":
        payload["captured_at"] = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    if change == "naive":
        payload["captured_at"] = "2026-09-29T12:00:00"
    if change == "array":
        payload = []
    with pytest.raises(ValueError, match="ISSUER_RENDER_RESPONSE_INVALID"):
        await fetch_rendered_page(
            "JPMORGAN",
            ISIN,
            client_factory=lambda **kw: httpx.AsyncClient(
                transport=httpx.MockTransport(lambda r: httpx.Response(200, json=payload)), **kw
            ),
        )


@pytest.mark.parametrize(
    "url",
    [
        "http://www.jpmorgan-zertifikate.de/",
        "https://www.jpmorgan-zertifikate.de.evil.invalid/",
        "https://127.0.0.1/",
        "https://database/",
        "file:///etc/passwd",
        "https://name:secret@www.jpmorgan-zertifikate.de/",
        "https://www.jpmorgan-zertifikate.de:444/",
    ],
)
def test_renderer_resource_allowlist_blocks_local_and_foreign_destinations(url):
    assert not allowed_resource(url, "JPMORGAN")


class FakePage:
    def __init__(self, *, denied=None, failure=None, include_clock=True):
        self.url = product_url("JPMORGAN", ISIN)
        self.main_frame = object()
        self.denied, self.failure = denied, failure
        self.include_clock = include_clock

    async def goto(self, *args, **kwargs):
        if self.failure:
            raise self.failure
        return SimpleNamespace(status=200, headers={"content-type": "text/html"})

    async def evaluate(self, script):
        if script == ACCESS_STATE:
            return self.denied
        assert script == SANITIZED_DOM
        return page(include_clock=self.include_clock).decode()


class FakeContext:
    def __init__(self, page):
        self.page, self.closed, self.guard = page, False, None

    async def new_page(self):
        return self.page

    async def route(self, pattern, handler):
        self.guard = handler

    async def route_web_socket(self, pattern, handler):
        self.ws_handler = handler

    async def close(self):
        self.closed = True


@pytest.mark.parametrize(
    "denied", [None, "ISSUER_RENDER_ACCESS_BLOCKED", "ISSUER_RENDER_TERMS_REQUIRED"]
)
@pytest.mark.parametrize("include_clock", [True, False])
async def test_context_always_closes_and_access_gates_remain_closed(denied, include_clock):
    renderer = IssuerRenderer()
    context = FakeContext(FakePage(denied=denied, include_clock=include_clock))
    renderer.browser = SimpleNamespace(
        new_context=AsyncMock(return_value=context), is_connected=lambda: True
    )
    if denied:
        with pytest.raises(RenderFailure, match=denied):
            await renderer.render("JPMORGAN", ISIN)
        assert renderer.next_request["JPMORGAN"] > renderer.timer() + 3500
    else:
        result = await renderer.render("JPMORGAN", ISIN)
        assert result["isin"] == ISIN
        assert result["html"] == page(include_clock=include_clock).decode()
    assert context.closed
    assert renderer.browser.new_context.await_args.kwargs == {
        "accept_downloads": False,
        "service_workers": "block",
        "ignore_https_errors": False,
        "storage_state": None,
    }


async def test_cancelled_navigation_closes_its_context():
    renderer = IssuerRenderer()
    context = FakeContext(FakePage(failure=asyncio.CancelledError()))
    renderer.browser = SimpleNamespace(
        new_context=AsyncMock(return_value=context), is_connected=lambda: True
    )
    with pytest.raises(asyncio.CancelledError):
        await renderer.render("JPMORGAN", ISIN)
    assert context.closed and not renderer.lock.locked()


async def test_renderer_is_single_flight_and_has_provider_cooldown():
    renderer = IssuerRenderer(timer=lambda: 100.0)
    renderer.browser = SimpleNamespace(is_connected=lambda: True)
    started, release = asyncio.Event(), asyncio.Event()

    async def capture(*args):
        started.set()
        await release.wait()
        return {}

    renderer._capture = capture
    first = asyncio.create_task(renderer.render("JPMORGAN", ISIN))
    await started.wait()
    with pytest.raises(RenderFailure, match="ISSUER_RENDERER_BUSY"):
        await renderer.render("MORGAN_STANLEY", ISIN)
    release.set()
    await first
    with pytest.raises(RenderFailure, match="ISSUER_RENDERER_THROTTLED"):
        await renderer.render("JPMORGAN", ISIN)
