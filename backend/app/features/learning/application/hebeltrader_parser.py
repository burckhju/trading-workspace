"""Hebeltrader PDF extraction for external historical observations.

The parser deliberately extracts source facts only. It does not resolve workspace
identities, infer trades, or correct inconsistent source values.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO

from pypdf import PdfReader


class HebeltraderParseError(ValueError):
    """The document is not parseable as a supported Hebeltrader issue."""


@dataclass(frozen=True, slots=True)
class HebeltraderValidationIssue:
    code: str
    field: str | None
    message: str


@dataclass(frozen=True, slots=True)
class HebeltraderRecommendation:
    issue_date: date
    issue_number: int
    recommendation_title: str
    underlying_name: str
    underlying_wkn: str
    underlying_price: Decimal
    underlying_currency: str
    underlying_target_1: Decimal
    underlying_target_2: Decimal
    underlying_stop_1: Decimal
    underlying_stop_2: Decimal
    gd50: Decimal
    gd200: Decimal
    derivative_type: str
    derivative_wkn: str
    derivative_indicated_price: Decimal
    derivative_currency: str
    derivative_target_1: Decimal
    derivative_target_2: Decimal
    derivative_stop_1: Decimal
    derivative_stop_2: Decimal
    strike: Decimal
    strike_currency: str
    omega_or_leverage: Decimal
    maturity_date: date
    price_indication_at: datetime | None
    stock_upside_pct: Decimal | None
    stock_risk_pct: Decimal | None
    derivative_upside_pct: Decimal | None
    derivative_risk_pct: Decimal | None
    raw_text: str
    validation_issues: tuple[HebeltraderValidationIssue, ...]


_ISSUE_RE = re.compile(r"(?P<date>\d{2}\.\d{2}\.\d{4})\s*[·•]\s*#\s*(?P<number>\d+)/(?P<year>\d{4})")
_MONEY_RE = r"(?P<value>-?\d+(?:[.,]\d+)?)\s*(?P<currency>€|\$)"
_WKN_RE = re.compile(r"\bWKN\s+([A-Z0-9]{6})\b")


def _decimal(value: str) -> Decimal:
    try:
        return Decimal(value.replace(".", "").replace(",", "."))
    except InvalidOperation as error:
        raise HebeltraderParseError(f"invalid decimal value: {value}") from error


def _currency(symbol: str) -> str:
    return "EUR" if symbol == "€" else "USD"


def _date(value: str) -> date:
    return datetime.strptime(value, "%d.%m.%Y").date()


def _short_date(value: str) -> date:
    return datetime.strptime(value, "%d.%m.%y").date()


def _search(pattern: str, text: str, *, field: str) -> re.Match[str]:
    match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
    if match is None:
        raise HebeltraderParseError(f"missing required field: {field}")
    return match


def _money(label: str, text: str) -> tuple[Decimal, str]:
    match = _search(rf"{re.escape(label)}\s*{_MONEY_RE}", text, field=label)
    return _decimal(match.group("value")), _currency(match.group("currency"))


def _percent_pair(text: str, row_label: str) -> tuple[Decimal | None, Decimal | None]:
    match = re.search(
        rf"{re.escape(row_label)}\s+([+-]?\d+(?:[.,]\d+)?)\s*%\s+([+-]?\d+(?:[.,]\d+)?)\s*%",
        text,
        re.IGNORECASE,
    )
    if match is None:
        return None, None
    return _decimal(match.group(1)), _decimal(match.group(2))


def extract_pdf_text(content: bytes) -> str:
    """Extract text from a PDF without OCR.

    Hebeltrader 2026 samples contain a usable text layer. OCR is intentionally not
    part of this adapter; image-only documents are review failures rather than guessed.
    """

    try:
        reader = PdfReader(BytesIO(content))
    except Exception as error:  # pypdf exposes several parser-specific exceptions
        raise HebeltraderParseError("invalid PDF") from error

    pages = [(page.extract_text() or "") for page in reader.pages]
    text = "\n".join(pages).strip()
    if not text:
        raise HebeltraderParseError("PDF has no extractable text layer")
    return text


def parse_hebeltrader_pdf(content: bytes) -> HebeltraderRecommendation:
    return parse_hebeltrader_text(extract_pdf_text(content))


def parse_hebeltrader_text(text: str) -> HebeltraderRecommendation:
    issue_match = _ISSUE_RE.search(text)
    if issue_match is None:
        raise HebeltraderParseError("missing Hebeltrader issue date/number")

    issue_date = _date(issue_match.group("date"))
    issue_number = int(issue_match.group("number"))
    if int(issue_match.group("year")) != issue_date.year:
        raise HebeltraderParseError("issue number year does not match issue date")

    page1 = text.split("CHARTTECHNISCHES BILD AKTIE", 1)[0]
    chart_section = text.split("CHARTTECHNISCHES BILD AKTIE", 1)
    if len(chart_section) != 2:
        raise HebeltraderParseError("missing underlying technical section")
    page3 = chart_section[1]

    derivative_wkn_matches = _WKN_RE.findall(page1)
    underlying_wkn_matches = _WKN_RE.findall(page3)
    if not derivative_wkn_matches:
        raise HebeltraderParseError("missing derivative WKN")
    if not underlying_wkn_matches:
        raise HebeltraderParseError("missing underlying WKN")

    derivative_name_match = _search(
        r"(?P<name>[^\n]+)\s*\n?\s*Optionsschein\s+(?P<kind>Call|Put)",
        page1,
        field="derivative type",
    )
    underlying_match = _search(
        r"Basiswert\s+(?P<name>[^\n]+)",
        page3,
        field="underlying name",
    )

    title_lines = [line.strip() for line in page1.splitlines() if line.strip()]
    recommendation_title = next(
        (line for line in title_lines if line.endswith("!") and "HEBELTRADER" not in line.upper()),
        derivative_name_match.group("name").strip(),
    )

    derivative_price, derivative_currency = _money("Akt. Kurs**", page1)
    derivative_target_1, target_currency_1 = _money("Ziel 1", page1)
    derivative_target_2, target_currency_2 = _money("Ziel 2", page1)
    derivative_stop_1, stop_currency_1 = _money("Stopp 1", page1)
    derivative_stop_2, stop_currency_2 = _money("Stopp 2", page1)
    if len({derivative_currency, target_currency_1, target_currency_2, stop_currency_1, stop_currency_2}) != 1:
        raise HebeltraderParseError("inconsistent derivative currencies")

    strike, strike_currency = _money("Basispreis", page1)
    omega_match = _search(r"Omega/Hebel\s*([0-9]+(?:[.,][0-9]+)?)", page1, field="Omega/Hebel")
    maturity_match = _search(r"Laufzeit\s*(\d{2}\.\d{2}\.\d{2})", page1, field="Laufzeit")

    underlying_price, underlying_currency = _money("Akt. Kurs", page3)
    underlying_target_1, u_t1_cur = _money("Kursziel 1", page3)
    underlying_target_2, u_t2_cur = _money("Kursziel 2", page3)
    underlying_stop_1, u_s1_cur = _money("Stopp 1", page3)
    underlying_stop_2, u_s2_cur = _money("Stopp 2", page3)
    gd50, gd50_cur = _money("GD50", page3)
    gd200, gd200_cur = _money("GD200", page3)
    if len({underlying_currency, u_t1_cur, u_t2_cur, u_s1_cur, u_s2_cur, gd50_cur, gd200_cur}) != 1:
        raise HebeltraderParseError("inconsistent underlying currencies")

    issues: list[HebeltraderValidationIssue] = []
    indication_match = re.search(
        r"Kursindikation,\s*Stand:\s*(\d{2}\.\d{2}\.\d{4})\s+um\s+(\d{2}:\d{2})\s+Uhr",
        page1,
        re.IGNORECASE,
    )
    price_indication_at: datetime | None = None
    if indication_match is not None:
        price_indication_at = datetime.strptime(
            f"{indication_match.group(1)} {indication_match.group(2)}", "%d.%m.%Y %H:%M"
        )
        if price_indication_at.date() != issue_date:
            issues.append(
                HebeltraderValidationIssue(
                    code="PRICE_INDICATION_DATE_MISMATCH",
                    field="price_indication_at",
                    message="price indication date differs from issue date",
                )
            )
    else:
        issues.append(
            HebeltraderValidationIssue(
                code="PRICE_INDICATION_TIMESTAMP_MISSING",
                field="price_indication_at",
                message="price indication timestamp could not be extracted",
            )
        )

    if "Xx.xx.26" in text or "XX.XX.26" in text.upper():
        issues.append(
            HebeltraderValidationIssue(
                code="SOURCE_PLACEHOLDER_DATE",
                field=None,
                message="source contains an unresolved placeholder date",
            )
        )

    stock_upside, stock_risk = _percent_pair(text, "Aktie")
    derivative_upside, derivative_risk = _percent_pair(text, "Hebelprodukt")

    return HebeltraderRecommendation(
        issue_date=issue_date,
        issue_number=issue_number,
        recommendation_title=recommendation_title,
        underlying_name=underlying_match.group("name").strip(),
        underlying_wkn=underlying_wkn_matches[0],
        underlying_price=underlying_price,
        underlying_currency=underlying_currency,
        underlying_target_1=underlying_target_1,
        underlying_target_2=underlying_target_2,
        underlying_stop_1=underlying_stop_1,
        underlying_stop_2=underlying_stop_2,
        gd50=gd50,
        gd200=gd200,
        derivative_type=f"OPTIONSSCHEIN_{derivative_name_match.group('kind').upper()}",
        derivative_wkn=derivative_wkn_matches[0],
        derivative_indicated_price=derivative_price,
        derivative_currency=derivative_currency,
        derivative_target_1=derivative_target_1,
        derivative_target_2=derivative_target_2,
        derivative_stop_1=derivative_stop_1,
        derivative_stop_2=derivative_stop_2,
        strike=strike,
        strike_currency=strike_currency,
        omega_or_leverage=_decimal(omega_match.group(1)),
        maturity_date=_short_date(maturity_match.group(1)),
        price_indication_at=price_indication_at,
        stock_upside_pct=stock_upside,
        stock_risk_pct=stock_risk,
        derivative_upside_pct=derivative_upside,
        derivative_risk_pct=derivative_risk,
        raw_text=text,
        validation_issues=tuple(issues),
    )
