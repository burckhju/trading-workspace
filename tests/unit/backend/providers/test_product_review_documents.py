"""Synthetic original-document shapes; every HTTP transport is intercepted."""

from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import httpx
import pytest

import app.providers.product_review_documents as documents
from tests.unit.backend.providers.product_review_document_fixture import synthetic_kid_pdf

ISIN = "DE000TEST124"
UNDERLYING = "US00SYNTH011"
SECOND_UNDERLYING = "US00SYNTH029"
BNP_URL = f"https://kid.bnpparibas.com/{ISIN}_DE.pdf"
IDENTITY = f"Synthetisches Basisinformationsblatt Optionsschein {ISIN} Basiswert {UNDERLYING}"


def test_real_pdf_extraction_preserves_source_labels_and_does_not_claim_a_last_trading_day():
    original = synthetic_kid_pdf(
        f"{IDENTITY} Währung des Produkts: EUR Kursnotierung: Stücknotiz "
        "Bewertungstag Der Ausübungstag bzw. der 15.01.2027"
    )
    result = documents.extract_kid(original, isin=ISIN, source_url=BNP_URL)
    assert result.currency == "EUR"
    assert result.unit == "CURRENCY_PER_WARRANT"
    assert result.maturity_on == date(2027, 1, 15)
    assert result.last_trading_on is None


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    asynchronous = AsyncMock(side_effect=AssertionError("No external product document requests"))
    synchronous = Mock(side_effect=AssertionError("No external product document requests"))
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", asynchronous)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", synchronous)
    yield
    asynchronous.assert_not_awaited()
    synchronous.assert_not_called()


@pytest.mark.parametrize(
    ("issuer", "expected"),
    [
        ("BNP Paribas", BNP_URL),
        (
            "J.P. Morgan SE",
            f"https://www.jpmorgan-key-information-documents.com/priips/document/{ISIN}/de/pop",
        ),
        ("Société Générale", f"https://kid.sgmarkets.com/public/api/kid/isin/{ISIN}?lang=ger"),
        ("SG Effekten", f"https://kid.sgmarkets.com/public/api/kid/isin/{ISIN}?lang=ger"),
        (
            "UniCredit Bank",
            "https://www.onemarkets.de/content/onemarkets-relaunch/de.pdf"
            f"?document=KID_DE_{ISIN}.pdf",
        ),
        (
            "HVB",
            "https://www.onemarkets.de/content/onemarkets-relaunch/de.pdf"
            f"?document=KID_DE_{ISIN}.pdf",
        ),
        ("Synthetic unsupported issuer", None),
    ],
)
def test_pins_each_supported_issuer_to_its_document_route(issuer, expected):
    assert documents.kid_url(issuer, ISIN) == expected


@pytest.mark.parametrize("invalid", ["", ISIN.lower(), f" {ISIN}", "DE000TEST120", "../payload"])
def test_does_not_repair_noncanonical_or_unsafe_identifiers(invalid):
    assert documents.kid_url("BNP Paribas", invalid) is None


@pytest.mark.parametrize(
    ("issuer", "date_text"),
    [
        ("BNP Paribas", "Bewertungstag Der Ausübungstag bzw. der 15.01.2027"),
        ("UniCredit", "Finaler Bewertungstag 15.01.2027"),
        (
            "J.P. Morgan SE",
            "Ausübungszeitraum: 01. Januar 2026 bis 15. Januar 2027 Referenzpreis",
        ),
        (
            "Société Générale",
            "Ausübungsfrist: 01. Januar 2026 bis 15. Januar 2027 Basiswert",
        ),
    ],
)
def test_extracts_only_labelled_current_document_facts(issuer, date_text):
    url = documents.kid_url(issuer, ISIN)
    text = (
        f"{IDENTITY}\n Währung des Produkts: Euro (EUR)\n Kursnotierung: Stücknotiz\n"
        f"Referenzstelle: New York Stock Exchange\n {date_text}"
    )
    result = documents.extract_kid_text(text, isin=ISIN, source_url=url)
    assert result.isin == ISIN
    assert result.underlying_isin == UNDERLYING
    assert result.currency == "EUR"
    assert result.unit == "CURRENCY_PER_WARRANT"
    assert result.reference_venue_mic == "XNYS"
    assert result.maturity_on == date(2027, 1, 15)
    assert result.last_trading_on is None
    assert result.last_trading_venue_mic is None
    assert result.issues == ()


def test_investment_examples_ratio_and_unrelated_dates_are_not_price_scale_evidence():
    result = documents.extract_kid_text(
        f"{IDENTITY} Anlagebetrag 10.000 EUR. Bezugsverhältnis 0,1. "
        "Beispielpreis 0,55 EUR. Stand 18.11.2026. Rückzahlung 15.01.2027.",
        isin=ISIN,
        source_url=BNP_URL,
    )
    assert result.currency is None
    assert result.unit is None
    assert result.reference_venue_mic is None
    assert result.maturity_on is None


def test_ambiguous_fields_remain_unproven_instead_of_choosing_the_first_match():
    result = documents.extract_kid_text(
        f"{IDENTITY} Weiterer Basiswert {SECOND_UNDERLYING}. "
        "Währung des Produkts: EUR Festgelegte Währung: USD "
        "Referenzstelle: New York Stock Exchange Maßgebliche Börse: Deutsche Börse Xetra "
        "Bewertungstag Der Ausübungstag bzw. der 15.01.2027 "
        "Bewertungstag Der Ausübungstag bzw. der 16.01.2027",
        isin=ISIN,
        source_url=BNP_URL,
    )
    assert result.underlying_isin is None
    assert result.currency is None
    assert result.reference_venue_mic is None
    assert result.maturity_on is None
    assert result.issues == ("PRODUCT_DOCUMENT_UNDERLYING_AMBIGUOUS",)


@pytest.mark.parametrize(
    "text",
    [
        f"Optionsschein {ISIN} {UNDERLYING}",
        f"Basisinformationsblatt Aktienanleihe {ISIN} {UNDERLYING}",
        f"Basisinformationsblatt Optionsschein {SECOND_UNDERLYING}",
        f"Basisinformationsblatt Optionsschein {ISIN.lower()}",
    ],
)
def test_rejects_missing_document_type_or_exact_product_identity(text):
    with pytest.raises(ValueError, match="PRODUCT_DOCUMENT_IDENTITY_UNVERIFIED"):
        documents.extract_kid_text(text, isin=ISIN, source_url=BNP_URL)


@pytest.mark.parametrize(
    "source", ["https://example.invalid/kid.pdf", "https://kid.bnpparibas.com.evil.invalid/kid.pdf"]
)
def test_unsupported_or_lookalike_host_does_not_qualify_a_payload(source):
    with pytest.raises(ValueError, match="PRODUCT_DOCUMENT_SOURCE_UNSUPPORTED"):
        documents.extract_kid_text(IDENTITY, isin=ISIN, source_url=source)


def test_invalid_numeric_date_and_missing_underlying_remain_unproven():
    result = documents.extract_kid_text(
        f"Basisinformationsblatt Optionsschein {ISIN} "
        "Bewertungstag Der Ausübungstag bzw. der 31.02.2027",
        isin=ISIN,
        source_url=BNP_URL,
    )
    assert result.maturity_on is None
    assert result.underlying_isin is None
    assert result.issues == ("PRODUCT_DOCUMENT_UNDERLYING_AMBIGUOUS",)


@pytest.mark.asyncio
async def test_original_fetch_is_bounded_and_does_not_follow_redirects():
    seen = []

    def handle(request):
        seen.append(request)
        return httpx.Response(302, headers={"location": "https://example.invalid/login"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await documents.fetch_original(client, BNP_URL)
    assert len(seen) == 1
    assert str(seen[0].url) == BNP_URL


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "payload", "error"),
    [
        (200, b"<html>Consent/login gate</html>", "PRODUCT_DOCUMENT_NOT_PDF"),
        (200, b"", "PRODUCT_DOCUMENT_NOT_PDF"),
        (204, b"", "PRODUCT_DOCUMENT_HTTP_UNSUITABLE"),
        (200, b"%PDF-" + b"x" * documents.MAX_BYTES, "PRODUCT_DOCUMENT_TOO_LARGE"),
    ],
)
async def test_fetch_rejects_html_empty_non_document_and_oversized_payloads(status, payload, error):
    transport = httpx.MockTransport(lambda _request: httpx.Response(status, content=payload))
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(ValueError, match=error):
            await documents.fetch_original(client, BNP_URL)


@pytest.mark.asyncio
async def test_fetch_preserves_original_bytes_at_the_size_boundary():
    payload = b"%PDF-" + b"x" * (documents.MAX_BYTES - 5)
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, content=payload))
    async with httpx.AsyncClient(transport=transport) as client:
        assert await documents.fetch_original(client, BNP_URL) == payload


@pytest.mark.parametrize("payload", [b"", b"html", b"%PDF-" + b"x" * documents.MAX_BYTES])
def test_pdf_parser_rejects_invalid_bytes_before_constructing_a_reader(monkeypatch, payload):
    factory = Mock(side_effect=AssertionError("Invalid data must not reach PDF parser"))
    monkeypatch.setattr(documents, "PdfReader", factory)
    with pytest.raises(ValueError, match="PRODUCT_DOCUMENT_INVALID"):
        documents.extract_kid(payload, isin=ISIN, source_url=BNP_URL)
    factory.assert_not_called()


def test_pdf_parser_limits_pages_and_combines_only_extracted_page_text(monkeypatch):
    pages = [SimpleNamespace(extract_text=Mock(return_value=IDENTITY)) for _ in range(13)]
    monkeypatch.setattr(documents, "PdfReader", lambda _stream: SimpleNamespace(pages=pages))
    with pytest.raises(ValueError, match="PRODUCT_DOCUMENT_PAGE_LIMIT"):
        documents.extract_kid(b"%PDF-SYNTHETIC", isin=ISIN, source_url=BNP_URL)
    for page in pages:
        page.extract_text.assert_not_called()
    pages[:] = [
        SimpleNamespace(extract_text=Mock(return_value=IDENTITY)),
        SimpleNamespace(extract_text=Mock(return_value="Kursnotierung: Stücknotiz")),
    ]
    result = documents.extract_kid(b"%PDF-SYNTHETIC", isin=ISIN, source_url=BNP_URL)
    assert result.unit == "CURRENCY_PER_WARRANT"
    assert result.currency is None
