"""Bounded original PRIIPs extraction; no quotes, consent gates or historical claims."""

import re
from datetime import date
from io import BytesIO
from urllib.parse import urlparse

import httpx
from pypdf import PdfReader

from app.features.market.contracts import is_canonical_isin
from app.features.product.domain.review_evidence import ExtractedProductFacts

PARSER_VERSION = "current-product-document-v1"
MAX_BYTES = 2_000_000


def kid_url(issuer: str, isin: str) -> str | None:
    if not is_canonical_isin(isin):
        return None
    name = re.sub(r"[^a-z0-9]", "", issuer.casefold().replace("é", "e"))
    if name.startswith(("jpmorgan", "jpmorganse")):
        return f"https://www.jpmorgan-key-information-documents.com/priips/document/{isin}/de/pop"
    if name.startswith("bnpparibas"):
        return f"https://kid.bnpparibas.com/{isin}_DE.pdf"
    if name.startswith(("societegenerale", "sgeffekten")):
        return f"https://kid.sgmarkets.com/public/api/kid/isin/{isin}?lang=ger"
    if name.startswith(("unicredit", "hvb")):
        return (
            "https://www.onemarkets.de/content/onemarkets-relaunch/de.pdf"
            f"?document=KID_DE_{isin}.pdf"
        )
    return None


async def fetch_original(client: httpx.AsyncClient, url: str) -> bytes:
    """Pinned callers only; redirects, HTML gates and oversized documents fail closed."""
    async with client.stream("GET", url, follow_redirects=False) as response:
        response.raise_for_status()
        if response.status_code != 200:
            raise ValueError("PRODUCT_DOCUMENT_HTTP_UNSUITABLE")
        data = bytearray()
        async for chunk in response.aiter_bytes():
            data.extend(chunk)
            if len(data) > MAX_BYTES:
                raise ValueError("PRODUCT_DOCUMENT_TOO_LARGE")
    if not data.startswith(b"%PDF-"):
        raise ValueError("PRODUCT_DOCUMENT_NOT_PDF")
    return bytes(data)


def _one_date(pattern: str, text: str) -> date | None:
    values = set(re.findall(pattern, text, re.I))
    if len(values) != 1:
        return None
    value = next(iter(values))
    try:
        return date.fromisoformat("-".join(reversed(value.split("."))))
    except ValueError:
        return None


def extract_kid_text(text: str, *, isin: str, source_url: str) -> ExtractedProductFacts:
    """Recognize only observed labeled fields, never investment/ratio example amounts."""
    text = " ".join(text.split())
    if (
        not is_canonical_isin(isin)
        or re.search(r"\b" + re.escape(isin) + r"\b", text) is None
        or "Basisinformationsblatt" not in text
        or "Optionsschein" not in text
    ):
        raise ValueError("PRODUCT_DOCUMENT_IDENTITY_UNVERIFIED")
    host = urlparse(source_url).hostname
    if host not in {
        "www.jpmorgan-key-information-documents.com",
        "kid.bnpparibas.com",
        "kid.sgmarkets.com",
        "www.onemarkets.de",
    }:
        raise ValueError("PRODUCT_DOCUMENT_SOURCE_UNSUPPORTED")
    underlyings = {
        value
        for value in re.findall(r"\b[A-Z]{2}[A-Z0-9]{9}[0-9]\b", text)
        if value != isin and is_canonical_isin(value)
    }
    currency_matches = set(
        re.findall(
            r"(?:Währung des Produkts|Festgelegte Währung)\s*:?\s*(?:Euro\s*\()?([A-Z]{3})",
            text,
        )
    )
    currency = next(iter(currency_matches)) if len(currency_matches) == 1 else None
    unit = (
        "CURRENCY_PER_WARRANT"
        if re.search(r"(?:Kursnotierung|Notierung)\s*:?\s*Stücknotiz\b", text)
        else None
    )
    venues = set()
    if re.search(r"(?:Referenzstelle|Maßgebliche Börse)\s*:?\s*New York Stock Exchange", text):
        venues.add("XNYS")
    if re.search(r"Maßgebliche Börse\s*:?\s*Deutsche Börse Xetra", text):
        venues.add("XETR")
    maturity = None
    if host == "kid.bnpparibas.com":
        maturity = _one_date(
            r"Bewertungstag Der Ausübungstag bzw\. der (\d{2}\.\d{2}\.\d{4})", text
        )
    elif host == "www.onemarkets.de":
        maturity = _one_date(r"Finaler Bewertungstag (\d{2}\.\d{2}\.\d{4})", text)
    # Dates expressed as month names are parsed only in the exercise-period field.
    if host in {"www.jpmorgan-key-information-documents.com", "kid.sgmarkets.com"}:
        months = {
            name: n
            for n, name in enumerate(
                (
                    "Januar",
                    "Februar",
                    "März",
                    "April",
                    "Mai",
                    "Juni",
                    "Juli",
                    "August",
                    "September",
                    "Oktober",
                    "November",
                    "Dezember",
                ),
                1,
            )
        }
        periods = re.finditer(
            r"Ausübungs(?:zeitraum|frist)\s*:?(.{0,170}?)\b(?:Referenzpreis|Ausübungstag|Basiswert)\b",
            text,
        )
        ends = set()
        for period in periods:
            dates = re.findall(r"(\d{1,2})\. (" + "|".join(months) + r") (\d{4})", period[1])
            if len(dates) == 2:
                day, month, year = dates[-1]
                ends.add(date(int(year), months[month], int(day)))
        maturity = next(iter(ends)) if len(ends) == 1 else None
    issues = () if len(underlyings) == 1 else ("PRODUCT_DOCUMENT_UNDERLYING_AMBIGUOUS",)
    return ExtractedProductFacts(
        isin=isin,
        underlying_isin=next(iter(underlyings)) if len(underlyings) == 1 else None,
        currency=currency,
        unit=unit,
        reference_venue_mic=next(iter(venues)) if len(venues) == 1 else None,
        maturity_on=maturity,
        issues=issues,
    )


def extract_kid(document: bytes, *, isin: str, source_url: str) -> ExtractedProductFacts:
    if not 0 < len(document) <= MAX_BYTES or not document.startswith(b"%PDF-"):
        raise ValueError("PRODUCT_DOCUMENT_INVALID")
    reader = PdfReader(BytesIO(document))
    if len(reader.pages) > 12:
        raise ValueError("PRODUCT_DOCUMENT_PAGE_LIMIT")
    return extract_kid_text(
        "\n".join(page.extract_text() for page in reader.pages),
        isin=isin,
        source_url=source_url,
    )
