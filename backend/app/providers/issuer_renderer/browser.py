"""Bounded browser acquisition; no database, credentials, consent clicks or quote decisions."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from time import monotonic
from urllib.parse import urlsplit

from playwright.async_api import (
    Browser,
    Error,
    Playwright,
    Route,
    StorageState,
    WebSocketRoute,
    async_playwright,
)
from playwright.async_api import TimeoutError as BrowserTimeout

from app.features.market_data.domain.issuer_route_evidence import (
    SITES,
    allowed_product_url,
    product_url,
)
from app.providers.issuer_pages import MAX_BYTES, parse_product_page
from app.providers.issuer_rendered import RENDER_SCHEMA
from app.providers.issuer_renderer.consent_state import load_consent

VERSION = "ISSUER_RENDERER_V1"
# The two sites' observed consent assets (2026-09-29). Analytics and arbitrary hosts
# are unnecessary for product identity and are not made reachable by the browser.
ASSET_HOSTS = frozenset({"cdn.cookielaw.org", "c.evidon.com", "geolocation.onetrust.com"})
RECOVERABLE_DOM_ERRORS = frozenset(
    {
        "ISSUER_PRODUCT_TABLE_MISSING",
        "ISSUER_PRODUCT_METADATA_AMBIGUOUS",
        "ISSUER_STREAM_BINDING_UNVERIFIED",
        "ISSUER_QUOTE_CURRENCY_UNVERIFIED",
    }
)

# Operates on a detached clone; live page fields and attributes remain untouched.
# Scripts, forms and event/URL attributes never cross into the backend response.
SANITIZED_DOM = """() => {
  const copy = document.documentElement.cloneNode(true);
  copy.querySelectorAll('script,style,noscript,template,iframe,object,embed,form,input,textarea')
    .forEach(n => n.remove());
  const keep = new Set(['class', 'data-item', 'data-field', 'data-grid', 'data-source']);
  [copy, ...copy.querySelectorAll('*')].forEach(n => [...n.attributes].forEach(a => {
    if (!keep.has(a.name)) n.removeAttribute(a.name);
  }));
  return '<!doctype html>' + copy.outerHTML;
}"""

ACCESS_STATE = """() => {
  const visible = e => !!(e.getClientRects().length) && getComputedStyle(e).visibility !== 'hidden';
  const headings = [...document.querySelectorAll('title,h1,h2')]
    .filter(e => e.tagName === 'TITLE' || visible(e))
    .map(e => e.textContent || '').join(' ').toLowerCase();
  const blocks = ['verify you are human', 'checking your browser', 'access denied',
    'just a moment', 'automated queries', 'unusual traffic'];
  if (blocks.some(word => headings.includes(word)))
    return 'ISSUER_RENDER_ACCESS_BLOCKED';
  const dialogs = [...document.querySelectorAll('[role="dialog"],dialog')].filter(visible);
  for (const dialog of dialogs) {
    const text = (dialog.innerText || '').toLowerCase();
    if (/captcha|verify you are human|sicherheitsüberprüfung/.test(text))
      return 'ISSUER_RENDER_ACCESS_BLOCKED';
    if (/nutzungsbedingungen|terms of use|terms and conditions/.test(text) && !/cookie/.test(text)
        && [...dialog.querySelectorAll('button,input[type="submit"]')].some(e =>
          /akzept|accept|agree/.test((e.innerText || e.value || '').toLowerCase())))
      return 'ISSUER_RENDER_TERMS_REQUIRED';
  }
  return null;
}"""


class RenderFailure(ValueError):
    """A sanitized machine-readable failure, never a browser message or response body."""


def allowed_resource(url: str, provider: str) -> bool:
    try:
        parsed = urlsplit(url)
        hosts = {SITES[provider][0], *ASSET_HOSTS}
        if provider == "JPMORGAN":
            hosts.add("jpmorgan-zertifikate.de")
        return (
            parsed.scheme == "https"
            and parsed.hostname in hosts
            and parsed.port in {None, 443}
            and not parsed.username
            and not parsed.password
        )
    except (KeyError, ValueError):
        return False


class IssuerRenderer:
    """One browser, one page at a time, fresh context per product and provider cooldowns."""

    def __init__(self, *, timer: Callable[[], float] = monotonic) -> None:
        self.timer = timer
        self.lock = asyncio.Lock()
        self.next_request: dict[str, float] = {}
        self.playwright: Playwright | None = None
        self.browser: Browser | None = None

    async def start(self) -> None:
        self.playwright = await async_playwright().start()
        try:
            await self._launch()
        except BaseException:
            await self.close()
            raise

    async def _launch(self) -> None:
        assert self.playwright is not None
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            chromium_sandbox=True,
            timeout=20_000,
        )
        context = await self.browser.new_context()
        try:
            page = await context.new_page()
            await page.goto("about:blank")
        finally:
            await asyncio.wait_for(context.close(), timeout=3)

    def healthy(self) -> bool:
        return self.browser is not None and self.browser.is_connected()

    async def close(self) -> None:
        try:
            if self.browser is not None:
                await self.browser.close()
        finally:
            if self.playwright is not None:
                await self.playwright.stop()
            self.browser = self.playwright = None

    async def render(self, provider: str, isin: str) -> dict[str, object]:
        url = product_url(provider, isin)
        if self.lock.locked():
            raise RenderFailure("ISSUER_RENDERER_BUSY")
        if self.timer() < self.next_request.get(provider, 0):
            raise RenderFailure("ISSUER_RENDERER_THROTTLED")
        async with self.lock:
            self.next_request[provider] = self.timer() + 15
            try:
                async with asyncio.timeout(35):
                    if not self.healthy():
                        await self._launch()
                    return await self._capture(provider, isin, url)
            except RenderFailure as exc:
                delay = (
                    3600
                    if str(exc)
                    in {
                        "ISSUER_RENDER_ACCESS_BLOCKED",
                        "ISSUER_RENDER_TERMS_REQUIRED",
                    }
                    else 300
                )
                self.next_request[provider] = self.timer() + delay
                raise
            except (BrowserTimeout, TimeoutError):
                self.next_request[provider] = self.timer() + 300
                raise RenderFailure("ISSUER_RENDER_TIMEOUT") from None
            except Error:
                self.next_request[provider] = self.timer() + 300
                raise RenderFailure("ISSUER_RENDER_BROWSER_ERROR") from None

    async def _capture(
        self, provider: str, isin: str, url: str, *, consent_override: StorageState | None = None
    ) -> dict[str, object]:
        assert self.browser is not None
        try:
            consent = (
                (consent_override if consent_override is not None else load_consent())
                if provider == "JPMORGAN"
                else None
            )
        except ValueError:
            raise RenderFailure("ISSUER_CONSENT_STATE_INVALID") from None
        context = await self.browser.new_context(
            accept_downloads=False,
            service_workers="block",
            ignore_https_errors=False,
            storage_state=consent,
        )
        try:
            page = await context.new_page()
            requests = 0
            navigation_error: str | None = None

            async def guard(route: Route) -> None:
                nonlocal requests, navigation_error
                request = route.request
                requests += 1
                if requests > 128:
                    navigation_error = "ISSUER_RENDER_REQUEST_LIMIT"
                    await route.abort()
                    return
                if request.is_navigation_request():
                    if request.frame != page.main_frame:
                        await route.abort()
                        return
                    if not allowed_product_url(request.url, provider, isin):
                        navigation_error = "ISSUER_RENDER_NAVIGATION_BLOCKED"
                        await route.abort()
                        return
                if request.method not in {"GET", "HEAD"} or not allowed_resource(
                    request.url, provider
                ):
                    await route.abort()
                    return
                await route.continue_()

            await context.route("**/*", guard)

            # Stream subscriptions are handled by the existing issuer adapters.
            async def close_socket(socket: WebSocketRoute) -> None:
                await socket.close()

            await context.route_web_socket("**/*", close_socket)
            try:
                response = await page.goto(url, wait_until="domcontentloaded", timeout=20_000)
            except Error:
                if navigation_error:
                    raise RenderFailure(navigation_error) from None
                raise
            if response is None:
                raise RenderFailure("ISSUER_RENDER_TRANSPORT_ERROR")
            if response.status in {401, 403, 429}:
                raise RenderFailure("ISSUER_RENDER_ACCESS_BLOCKED")
            if response.status != 200:
                raise RenderFailure("ISSUER_RENDER_HTTP_ERROR")
            if "text/html" not in response.headers.get("content-type", "").lower():
                raise RenderFailure("ISSUER_RENDER_CONTENT_TYPE_INVALID")
            # Streaming sites never reach networkidle. Wait for actual identity DOM,
            # bounded by the outer deadline, without clicking anything on the page.
            deadline = self.timer() + 12
            while True:
                if navigation_error:
                    raise RenderFailure(navigation_error)
                denied = await page.evaluate(ACCESS_STATE)
                if denied:
                    raise RenderFailure(denied)
                if not allowed_product_url(page.url, provider, isin):
                    raise RenderFailure("ISSUER_RENDER_NAVIGATION_BLOCKED")
                html = await page.evaluate(SANITIZED_DOM)
                raw = html.encode("utf-8")
                if len(raw) > MAX_BYTES:
                    raise RenderFailure("ISSUER_RENDER_PAGE_TOO_LARGE")
                now = datetime.now(UTC)
                try:
                    parse_product_page(raw, provider, isin, page.url, now=now)
                except ValueError as exc:
                    if str(exc) == "ISSUER_PAGE_TERMS_REQUIRED":
                        raise RenderFailure("ISSUER_RENDER_TERMS_REQUIRED") from None
                    if str(exc) not in RECOVERABLE_DOM_ERRORS:
                        # Identity conflicts/expired products fail here and again in
                        # the backend; never keep waiting for them to become valid.
                        raise RenderFailure("ISSUER_RENDER_PRODUCT_INCOMPLETE") from None
                    if self.timer() >= deadline:
                        raise RenderFailure("ISSUER_RENDER_PRODUCT_INCOMPLETE") from None
                    await asyncio.sleep(0.25)
                    continue
                return {
                    "schema_version": RENDER_SCHEMA,
                    "provider": provider,
                    "isin": isin,
                    "source_url": page.url,
                    "html": html,
                    "captured_at": now.isoformat(),
                }
        finally:
            await asyncio.wait_for(context.close(), timeout=3)
