"""Bounded original Stuttgart HTML extraction; no HTTP or market-status inference."""

import re
from datetime import datetime
from urllib.parse import urlsplit

from app.features.market.contracts import is_canonical_isin
from app.features.product.domain.deadline_listing_terms import OriginalListingTermsFacts
from app.providers.issuer_pages import Node, PageParser

MAX_BYTES = 2_000_000


def parse_original_listing_terms(
    document: bytes, *, expected_isin: str, expected_wkn: str | None = None
) -> OriginalListingTermsFacts:
    """Extract the exact labeled last exchange day from an identified original.

    The canonical URL and visible product heading must agree with the actual
    Product owner; an underlying table, a quote timestamp, settlement date or
    final valuation day cannot substitute for the required listing-date field.
    Supplied HTML is retained as evidence, never claimed to be independently
    authenticated by this parser.
    """
    if not 1 <= len(document) <= MAX_BYTES or not is_canonical_isin(expected_isin):
        raise ValueError("PRODUCT_LISTING_TERMS_INPUT_INVALID")
    try:
        text = document.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError("PRODUCT_LISTING_TERMS_ENCODING_INVALID") from error
    page = PageParser()
    page.feed(text)
    urls = {
        node.attrs.get("href", "")
        for node in page.nodes
        if node.tag == "link" and "canonical" in node.attrs.get("rel", "").casefold().split()
    }
    if len(urls) != 1:
        raise ValueError("PRODUCT_LISTING_TERMS_CANONICAL_MISSING")
    source = next(iter(urls))
    url = urlsplit(source)
    path = re.fullmatch(
        r"/de-de/produkte/hebelprodukte/optionsscheine/stuttgart/([a-z0-9]{6})/", url.path
    )
    if (
        url.scheme != "https"
        or url.netloc != "www.boerse-stuttgart.de"
        or url.query
        or url.fragment
        or path is None
    ):
        raise ValueError("PRODUCT_LISTING_TERMS_SOURCE_UNSUPPORTED")
    wkn = path.group(1).upper()
    if expected_wkn is not None and wkn != expected_wkn:
        raise ValueError("PRODUCT_LISTING_TERMS_WKN_MISMATCH")
    titles = {node.text for node in page.nodes if node.tag == "title"}
    if len(titles) != 1:
        raise ValueError("PRODUCT_LISTING_TERMS_VENUE_UNVERIFIED")
    title = next(iter(titles))
    if not title.endswith("Börse Stuttgart (XSTU)") or not re.search(rf"\b{wkn}\b", title):
        raise ValueError("PRODUCT_LISTING_TERMS_VENUE_UNVERIFIED")
    headings = {node.parent.text for node in page.nodes if node.tag == "h1" and node.parent}
    if len(headings) != 1:
        raise ValueError("PRODUCT_LISTING_TERMS_PRODUCT_HEADING_MISSING")
    heading = next(iter(headings))
    if set(re.findall(r"\bISIN\s*:?\s*([A-Z]{2}[A-Z0-9]{9}[0-9])\b", heading)) != {
        expected_isin
    } or set(re.findall(r"\bWKN\s*:?\s*([A-Z0-9]{6})\b", heading)) != {wkn}:
        raise ValueError("PRODUCT_LISTING_TERMS_IDENTITY_MISMATCH")
    rows: dict[Node, list[Node]] = {}
    for node in page.nodes:
        if node.tag in {"td", "th"}:
            row = PageParser.ancestor(node, "tr")
            if row is not None:
                rows.setdefault(row, []).append(node)
    values = {
        cells[1].text
        for row, cells in rows.items()
        if len(cells) == 2
        and cells[0].text == "Letzter Börsenhandelstag"
        and _within_product_master_data(row, expected_isin, wkn)
    }
    last_trading_on = None
    issues: tuple[str, ...] = ()
    if not values:
        issues = ("PRODUCT_LAST_TRADING_DAY_EVIDENCE_MISSING",)
    elif len(values) != 1:
        issues = ("PRODUCT_LAST_TRADING_DAY_CONFLICT",)
    else:
        value = next(iter(values))
        try:
            if re.fullmatch(r"[0-9]{2}\.[0-9]{2}\.[0-9]{4}", value) is None:
                raise ValueError("Date precision not established")
            last_trading_on = datetime.strptime(value, "%d.%m.%Y").date()
        except ValueError:
            issues = ("PRODUCT_LAST_TRADING_DAY_INVALID",)
    return OriginalListingTermsFacts(expected_isin, wkn, source, last_trading_on, issues)


def _within_product_master_data(node: Node, isin: str, wkn: str) -> bool:
    parent = node.parent
    while parent is not None:
        if parent.attrs.get("id", "").startswith("MasterDataBlock-"):
            return set(re.findall(r"\bISIN\s*:?\s*([A-Z]{2}[A-Z0-9]{9}[0-9])\b", parent.text)) == {
                isin
            } and set(re.findall(r"\bWKN\s*:?\s*([A-Z0-9]{6})\b", parent.text)) == {wkn}
        parent = parent.parent
    return False
