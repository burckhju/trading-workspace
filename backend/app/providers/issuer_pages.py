"""Bounded anonymous issuer-page discovery with exact DOM identity evidence."""

from __future__ import annotations

import asyncio
import hashlib
import re
from collections.abc import Callable
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from html.parser import HTMLParser
from time import monotonic
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import httpx

from app.features.market_data.domain.issuer_route_evidence import (
    SITES,
    VERSION,
    allowed_product_url,
    product_url,
)

MAX_BYTES = 2_000_000


def is_jpmorgan_terms_page(text: str, *, has_product_bindings: bool) -> bool:
    """Recognize the observed full-page gate, not footer links or a cookie banner."""
    normalized = " ".join(text.casefold().split())
    return (
        not has_product_bindings
        and "wichtige hinweise und nutzungsbedingungen" in normalized
        and "die nutzung dieser website ist nur nutzern gestattet" in normalized
        and "bestätigungsbuttons" in normalized
    )


VOID = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)


def provider_for_issuer(name: str | None) -> str | None:
    tokens = re.findall(r"[a-z0-9]+", (name or "").casefold())
    if tokens[:2] == ["morgan", "stanley"]:
        return "MORGAN_STANLEY"
    if (
        tokens[:1] == ["jpmorgan"]
        or tokens[:3] == ["j", "p", "morgan"]
        or tokens[:2] == ["jp", "morgan"]
    ):
        return "JPMORGAN"
    return None


@dataclass(frozen=True)
class PageEvidence:
    provider: str
    isin: str
    stream_id: str
    currency: str
    product_type: str
    valid_through: str
    source_url: str
    source_sha256: str
    verified_at: str
    schema_version: str = VERSION
    acquisition_mode: str = "PUBLIC_HTTP"

    def payload(self) -> dict[str, str]:
        return asdict(self)


class Node:
    def __init__(self, tag: str, attrs: dict[str, str], parent: Node | None) -> None:
        self.tag, self.attrs, self.parent = tag, attrs, parent
        self.parts: list[str] = []

    @property
    def text(self) -> str:
        return " ".join(" ".join(self.parts).split())


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Node("root", {}, None)
        self.stack: list[Node] = [self.root]
        self.nodes: list[Node] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if len(self.nodes) >= 25_000 or len(self.stack) >= 64:
            raise ValueError("ISSUER_PAGE_STRUCTURE_LIMIT")
        node = Node(tag, {key: value or "" for key, value in attrs}, self.stack[-1])
        self.nodes.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                self.stack = self.stack[:index]
                break

    def handle_data(self, data: str) -> None:
        if any(node.tag in {"script", "style"} for node in self.stack):
            return
        for node in self.stack:
            node.parts.append(data)

    @staticmethod
    def ancestor(node: Node, tag: str) -> Node | None:
        parent = node.parent
        while parent is not None and parent.tag != tag:
            parent = parent.parent
        return parent

    def product_fields(self, isin: str) -> dict[str, str]:
        tables: dict[Node, dict[str, set[str]]] = {}
        rows: dict[Node, list[Node]] = {}
        for node in self.nodes:
            if node.tag in {"td", "th"}:
                row = self.ancestor(node, "tr")
                if row is not None:
                    rows.setdefault(row, []).append(node)
        for row, cells in rows.items():
            table = self.ancestor(row, "table")
            if table is not None and len(cells) == 2:
                key = cells[0].text.rstrip(":").casefold()
                tables.setdefault(table, {}).setdefault(key, set()).add(cells[1].text)
        product = [fields for fields in tables.values() if fields.get("isin") == {isin}]
        if not product:
            raise ValueError("ISSUER_PRODUCT_TABLE_MISSING")
        combined: dict[str, set[str]] = {}
        for fields in product:
            for key, values in fields.items():
                combined.setdefault(key, set()).update(values)
        required = ("isin", "produkttyp", "bewertungstag")
        if any(len(combined.get(key, set())) != 1 for key in required):
            raise ValueError("ISSUER_PRODUCT_METADATA_AMBIGUOUS")
        if any(len(combined.get(key, set())) > 1 for key in ("wkn", "währung")):
            raise ValueError("ISSUER_PRODUCT_METADATA_AMBIGUOUS")
        return {key: next(iter(values)) for key, values in combined.items() if len(values) == 1}


def parse_product_page(
    raw: bytes, provider: str, isin: str, url: str, *, now: datetime | None = None
) -> PageEvidence:
    if len(raw) > MAX_BYTES or not allowed_product_url(url, provider, isin):
        raise ValueError("ISSUER_UNTRUSTED_PRODUCT_PAGE")
    parser = PageParser()
    try:
        parser.feed(raw.decode("utf-8-sig"))
        parser.close()
    except UnicodeError:
        raise ValueError("ISSUER_PAGE_ENCODING_INVALID") from None
    if provider == "JPMORGAN" and is_jpmorgan_terms_page(
        parser.root.text,
        has_product_bindings=any(
            n.attrs.get("data-item", "").endswith(isin)
            and n.attrs.get("data-field") in {"bid", "ask"}
            for n in parser.nodes
        ),
    ):
        raise ValueError("ISSUER_PAGE_TERMS_REQUIRED")
    headings = " ".join(n.text for n in parser.nodes if n.tag in {"title", "h1", "h2"}).casefold()
    if any(
        signal in headings
        for signal in (
            "verify you are human",
            "checking your browser",
            "access denied",
            "just a moment",
            "automated queries",
            "unusual traffic",
        )
    ):
        raise ValueError("ISSUER_PAGE_ACCESS_BLOCKED")
    fields = parser.product_fields(isin)
    if fields["produkttyp"].casefold() != "optionsschein":
        raise ValueError("ISSUER_UNSUPPORTED_PRODUCT_TYPE")
    if fields.get("wkn") is not None and fields["wkn"] != isin[5:11]:
        raise ValueError("ISSUER_PRODUCT_IDENTITY_CONFLICT")
    try:
        expiry = datetime.strptime(fields["bewertungstag"], "%d.%m.%Y").date()
    except ValueError:
        raise ValueError("ISSUER_EXPIRY_DATE_UNVERIFIED") from None
    when = now or datetime.now(UTC)
    if expiry < when.astimezone(ZoneInfo("Europe/Berlin")).date():
        raise ValueError("ISSUER_PRODUCT_EXPIRED")
    grid, clock = SITES[provider][2:]
    targets = [
        n
        for n in parser.nodes
        if (
            re.fullmatch(r"X[A-Z0-9]{1,20}" + re.escape(isin), n.attrs.get("data-item", ""))
            and n.attrs.get("data-source") == "lightstreamer"
            and n.attrs.get("data-grid") == grid
            and n.attrs.get("data-field") in {"bid", "ask", clock}
        )
    ]
    ids = {n.attrs["data-item"] for n in targets}
    if len(ids) != 1 or {n.attrs["data-field"] for n in targets} != {"bid", "ask", clock}:
        raise ValueError("ISSUER_STREAM_BINDING_UNVERIFIED")
    # Both price cells must bind the currency to this exact stream item.
    currencies = set()
    price_class = "productdetail-box-number" if provider == "JPMORGAN" else "price"
    for node in (n for n in targets if n.attrs["data-field"] in {"bid", "ask"}):
        parent, bound = node.parent, False
        for _ in range(3):
            if parent is None:
                break
            if price_class in parent.attrs.get("class", "").split():
                found = re.findall(r"\b[A-Z]{3}\b", parent.text)
                if len(found) != 1:
                    raise ValueError("ISSUER_QUOTE_CURRENCY_UNVERIFIED")
                currencies.add(found[0])
                bound = True
                break
            parent = parent.parent
        if not bound:
            raise ValueError("ISSUER_QUOTE_CURRENCY_UNVERIFIED")
    currency = next(iter(currencies)) if len(currencies) == 1 else None
    if currency != "EUR" or (fields.get("währung") not in {None, currency}):
        raise ValueError("ISSUER_QUOTE_CURRENCY_UNVERIFIED")
    if provider == "MORGAN_STANLEY" and fields.get("währung") != currency:
        raise ValueError("ISSUER_QUOTE_CURRENCY_UNVERIFIED")
    return PageEvidence(
        provider,
        isin,
        next(iter(ids)),
        currency,
        "Optionsschein",
        expiry.isoformat(),
        url,
        hashlib.sha256(raw).hexdigest(),
        when.isoformat(),
    )


class DiscoveryDeferred(ValueError):
    def __init__(self, retry_after_seconds: float):
        super().__init__("ISSUER_DISCOVERY_COOLDOWN")
        self.retry_after_seconds = max(1.0, retry_after_seconds)


class IssuerPageClient:
    """One discovery lane, bounded requests and per-provider cooldowns; no browser tokens."""

    def __init__(
        self,
        *,
        client_factory: Callable[..., httpx.AsyncClient] = httpx.AsyncClient,
        timer: Callable[[], float] = monotonic,
        renderer_enabled: bool = False,
    ) -> None:
        self.client_factory, self.timer = client_factory, timer
        self.next_request: dict[str, float] = {}
        self.renderer_enabled = renderer_enabled

    async def fetch(self, provider: str, isin: str) -> PageEvidence:
        try:
            return await self._fetch_http(provider, isin)
        except ValueError as exc:
            # Transport failures and an incomplete HTML shell may be recovered by
            # rendering. Never retry access denial, rate limits or identity conflicts
            # using another client, and never relax the shared identity parser.
            if not self.renderer_enabled or str(exc) not in {
                "ISSUER_PAGE_TRANSPORT_ERROR",
                "ISSUER_PRODUCT_TABLE_MISSING",
                "ISSUER_STREAM_BINDING_UNVERIFIED",
                # Only the renderer can hold an operator-approved consent state.
                # It never clicks consent during unattended product discovery.
                "ISSUER_PAGE_TERMS_REQUIRED",
            }:
                raise
            from app.providers.issuer_rendered import fetch_rendered_page

            try:
                raw, url, captured_at = await fetch_rendered_page(
                    provider, isin, client_factory=self.client_factory
                )
            except ValueError:
                self.next_request[provider] = max(
                    self.next_request.get(provider, 0), self.timer() + 300
                )
                raise
            proof = parse_product_page(raw, provider, isin, url, now=captured_at)
            self.next_request[provider] = self.timer() + 15
            return replace(proof, acquisition_mode="RENDERED_DOM")

    async def _fetch_http(self, provider: str, isin: str) -> PageEvidence:
        now = self.timer()
        if now < self.next_request.get(provider, 0):
            raise DiscoveryDeferred(self.next_request[provider] - now)
        self.next_request[provider] = now + 15
        url = product_url(provider, isin)
        try:
            async with asyncio.timeout(20):
                async with self.client_factory(
                    timeout=15, follow_redirects=False, trust_env=False
                ) as client:
                    for _ in range(3):
                        async with client.stream(
                            "GET", url, headers={"Accept": "text/html"}
                        ) as response:
                            if response.status_code in {301, 302, 303, 307, 308}:
                                redirect = urljoin(url, response.headers.get("location", ""))
                                if not allowed_product_url(redirect, provider, isin):
                                    raise ValueError("ISSUER_REDIRECT_BLOCKED")
                                url = redirect
                                continue
                            if response.status_code in {401, 403, 429}:
                                self.next_request[provider] = self.timer() + 3600
                                raise ValueError("ISSUER_PAGE_ACCESS_OR_RATE_LIMIT")
                            if response.status_code != 200:
                                raise ValueError(f"ISSUER_PAGE_HTTP_{response.status_code}")
                            if "text/html" not in response.headers.get("content-type", "").lower():
                                raise ValueError("ISSUER_PAGE_CONTENT_TYPE_INVALID")
                            parts, size = [], 0
                            async for part in response.aiter_bytes():
                                size += len(part)
                                if size > MAX_BYTES:
                                    raise ValueError("ISSUER_PAGE_SIZE_LIMIT")
                                parts.append(part)
                            return parse_product_page(b"".join(parts), provider, isin, url)
                    raise ValueError("ISSUER_REDIRECT_LIMIT")
        except (httpx.HTTPError, TimeoutError):
            self.next_request[provider] = self.timer() + 300
            raise ValueError("ISSUER_PAGE_TRANSPORT_ERROR") from None
