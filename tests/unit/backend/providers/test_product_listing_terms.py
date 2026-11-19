"""Only invented original HTML is used; no provider or real portfolio fixtures."""

from datetime import date

import pytest

from app.features.market.contracts import is_canonical_isin
from app.providers.product_listing_terms import MAX_BYTES, parse_original_listing_terms

WKN = "ZZ0000"
ISIN = next(value for digit in range(10) if is_canonical_isin(value := f"DE000{WKN}{digit}"))
URL = f"https://www.boerse-stuttgart.de/de-de/produkte/hebelprodukte/optionsscheine/stuttgart/{WKN.lower()}/"


def original(*, value="18.12.2026", label="Letzter Börsenhandelstag", rows="", isin=ISIN, wkn=WKN):
    return (
        f"<html><head><title>Synthetic product - {wkn} - Börse Stuttgart (XSTU)</title>"
        f'<link rel="canonical" href="{URL}"></head><body>'
        "<section><h1>Synthetic stock/OS/Call [100]/Synthetic issuer</h1>"
        f"WKN {wkn} ISIN {isin}</section>"
        f'<div id="MasterDataBlock-synthetic"><h2>Stammdaten</h2>WKN {wkn} ISIN {isin}'
        f"<table><tr><td>{label}</td><td><span>{value}</span></td></tr>{rows}</table></div>"
        "</body></html>"
    ).encode()


def parse(document, **kwargs):
    return parse_original_listing_terms(document, expected_isin=ISIN, **kwargs)


def test_exact_original_header_canonical_venue_and_product_master_data_are_required():
    document = original()
    before = bytes(document)
    result = parse(document, expected_wkn=WKN)
    assert result.isin == ISIN and result.wkn == WKN
    assert result.source_reference == URL
    assert result.last_trading_on == date(2026, 12, 18)
    assert result.venue_mic == "XSTU"
    assert result.issues == ()
    assert document == before


@pytest.mark.parametrize("label", ["Letzter Bewertungstag", "Zahltag", "Fälligkeit", "Kurszeit"])
def test_other_product_or_market_times_cannot_replace_last_exchange_day(label):
    result = parse(original(label=label))
    assert result.last_trading_on is None
    assert result.issues == ("PRODUCT_LAST_TRADING_DAY_EVIDENCE_MISSING",)


@pytest.mark.parametrize(
    "value", ["", "-", "18.12.", "2026-12-18", "18.12.2026 22:00", "32.12.2026"]
)
def test_unusable_date_is_retained_as_unsuitable_without_invented_precision(value):
    result = parse(original(value=value))
    assert result.last_trading_on is None
    assert result.issues == ("PRODUCT_LAST_TRADING_DAY_INVALID",)


def test_repeated_identical_rows_are_one_fact_but_conflicting_dates_remain_unresolved():
    duplicate = "<tr><td>Letzter Börsenhandelstag</td><td>18.12.2026</td></tr>"
    assert parse(original(rows=duplicate)).last_trading_on == date(2026, 12, 18)
    conflict = duplicate.replace("18.12.2026", "17.12.2026")
    result = parse(original(rows=conflict))
    assert result.last_trading_on is None
    assert result.issues == ("PRODUCT_LAST_TRADING_DAY_CONFLICT",)


def test_underlying_table_or_script_cannot_supply_missing_product_date():
    document = original(label="Zahltag")
    unrelated = (
        '<div id="UnderlyingSecurityBlock-synthetic"><table><tr>'
        "<td>Letzter Börsenhandelstag</td><td>18.12.2026</td></tr></table></div>"
        "<script>Letzter Börsenhandelstag 18.12.2026</script>"
    )
    result = parse(document.replace(b"</body>", unrelated.encode() + b"</body>"))
    assert result.last_trading_on is None


@pytest.mark.parametrize(
    ("old", "new", "reason"),
    [
        ("www.boerse-stuttgart.de", "unrelated.example.invalid", "SOURCE_UNSUPPORTED"),
        ("https://", "http://", "SOURCE_UNSUPPORTED"),
        ("/stuttgart/", "/frankfurt/", "SOURCE_UNSUPPORTED"),
        ("(XSTU)", "(XFRA)", "VENUE_UNVERIFIED"),
        (f"ISIN {ISIN}", "ISIN DE0000000000", "IDENTITY_MISMATCH"),
        (f"WKN {WKN}", "WKN YY0000", "IDENTITY_MISMATCH"),
        ('rel="canonical"', 'rel="alternate"', "CANONICAL_MISSING"),
        ("<h1>", "<h2>", "PRODUCT_HEADING_MISSING"),
    ],
)
def test_identity_source_and_venue_are_not_accepted_from_a_similar_product(old, new, reason):
    with pytest.raises(ValueError, match=reason):
        parse(original().replace(old.encode(), new.encode()))


def test_saved_wkn_contradiction_cannot_be_overwritten_by_original_file():
    with pytest.raises(ValueError, match="WKN_MISMATCH"):
        parse(original(), expected_wkn="YY0000")


def test_bounded_original_requires_valid_encoding_and_no_browser_gate_bypass():
    with pytest.raises(ValueError, match="INPUT_INVALID"):
        parse(b"x" * (MAX_BYTES + 1))
    with pytest.raises(ValueError, match="ENCODING_INVALID"):
        parse(b"\xff")
    with pytest.raises(ValueError, match="CANONICAL_MISSING"):
        parse(b"<html><title>Sign in</title><body>Terms acceptance required</body></html>")


def test_a_canonical_link_in_text_or_script_is_not_canonical_evidence():
    doc = original().replace(b'<link rel="canonical"', b'<meta name="canonical"')
    with pytest.raises(ValueError, match="CANONICAL_MISSING"):
        parse(doc)
