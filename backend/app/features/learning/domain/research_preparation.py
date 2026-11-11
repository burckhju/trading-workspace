"""Offline source contracts; no execution or historical-outcome semantics."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import StrEnum

INPUT_SCHEMA_VERSION = "hebeltrader-research-input-v1"
PREPARATION_VERSION = "hebeltrader-research-preparation-v1"
HISTORICAL_RESULT_STATUS = "NOT_COMPUTED"
PUBLICATION_PRECISION = "DATE_ONLY"
REQUIRED_DERIVATIVE_CURRENCY = "EUR"
PRICE_FIELDS = ("reference_price", "target_1", "target_2", "stop_1", "stop_2")
CASE_FIELDS = (
    "issue_id",
    "publication_date",
    "source_sheet",
    "source_row",
    "source_document",
    "underlying_name",
    "underlying_wkn",
    "underlying_currency",
    *(f"underlying_{field}" for field in PRICE_FIELDS),
    "derivative_wkn",
    "derivative_type",
    "derivative_type_raw",
    "derivative_currency",
    *(f"derivative_{field}" for field in PRICE_FIELDS),
    "strike",
    "strike_currency",
    "maturity_date",
    "open_end",
)

type JsonValue = str | int | bool | None | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]


class PreparationError(ValueError):
    """An input or output contract violation that prevents a complete preparation."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        super().__init__(detail)


class DerivativeType(StrEnum):
    WARRANT_CALL = "WARRANT_CALL"
    WARRANT_PUT = "WARRANT_PUT"
    TURBO_LONG = "TURBO_LONG"
    UNKNOWN = "UNKNOWN"


class SourceStatus(StrEnum):
    USABLE_SOURCE = "USABLE_SOURCE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


@dataclass(frozen=True, slots=True)
class SourceDecimal:
    """Both the exact supplied lexeme and its unrounded finite decimal value."""

    raw: str
    value: Decimal


def source_decimal(raw: str, *, field: str, allow_zero: bool = False) -> SourceDecimal:
    if re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", raw) is None:
        raise PreparationError("INVALID_DECIMAL", f"{field}: ungültige Dezimalzeichenfolge")
    try:
        value = Decimal(raw)
    except InvalidOperation as exc:
        raise PreparationError("INVALID_DECIMAL", f"{field}: ungültige Dezimalzahl") from exc
    if not value.is_finite() or value < 0 or (not allow_zero and value == 0):
        raise PreparationError("INVALID_PRICE", f"{field}: ungültiger Preisbereich")
    return SourceDecimal(raw=raw, value=value)


@dataclass(frozen=True, slots=True)
class SourceFile:
    filename: str
    sha256: str

    def snapshot(self) -> JsonObject:
        return {"filename": self.filename, "sha256": self.sha256}


@dataclass(frozen=True, slots=True)
class ResearchPriceAxis:
    wkn: str | None
    currency: str | None
    reference_price: SourceDecimal | None
    target_1: SourceDecimal | None
    target_2: SourceDecimal | None
    stop_1: SourceDecimal | None
    stop_2: SourceDecimal | None

    def prices(self) -> tuple[SourceDecimal | None, ...]:
        return (self.reference_price, self.target_1, self.target_2, self.stop_1, self.stop_2)

    def snapshot(self, prefix: str) -> JsonObject:
        result: JsonObject = {f"{prefix}_wkn": self.wkn, f"{prefix}_currency": self.currency}
        for field, price in zip(PRICE_FIELDS, self.prices(), strict=True):
            result[f"{prefix}_{field}"] = price.raw if price is not None else None
        return result


@dataclass(frozen=True, slots=True)
class ResearchCase:
    issue_id: str
    publication_date: date
    source_sheet: str | None
    source_row: int | None
    source_document: str | None
    underlying_name: str | None
    underlying: ResearchPriceAxis
    derivative: ResearchPriceAxis
    derivative_type: DerivativeType
    derivative_type_raw: str | None
    strike: SourceDecimal | None
    strike_currency: str | None
    maturity_date: date | None
    open_end: bool | None

    @property
    def economic_key(self) -> tuple[str, str | None, str | None]:
        return (self.issue_id, self.underlying.wkn, self.derivative.wkn)

    def snapshot(self) -> JsonObject:
        return {
            "issue_id": self.issue_id,
            "publication_date": self.publication_date.isoformat(),
            "source_sheet": self.source_sheet,
            "source_row": self.source_row,
            "source_document": self.source_document,
            "underlying_name": self.underlying_name,
            **self.underlying.snapshot("underlying"),
            **self.derivative.snapshot("derivative"),
            "derivative_type": self.derivative_type.value,
            "derivative_type_raw": self.derivative_type_raw,
            "strike": self.strike.raw if self.strike is not None else None,
            "strike_currency": self.strike_currency,
            "maturity_date": self.maturity_date.isoformat() if self.maturity_date else None,
            "open_end": self.open_end,
        }


@dataclass(frozen=True, slots=True)
class ResearchInput:
    source: SourceFile
    cases: tuple[ResearchCase, ...]


@dataclass(frozen=True, slots=True)
class SourceIssue:
    code: str
    field: str
    detail: str

    def snapshot(self) -> JsonObject:
        return {"code": self.code, "field": self.field, "detail": self.detail}


@dataclass(frozen=True, slots=True)
class ReviewedCase:
    source: ResearchCase
    issues: tuple[SourceIssue, ...]

    @property
    def status(self) -> SourceStatus:
        return SourceStatus.REVIEW_REQUIRED if self.issues else SourceStatus.USABLE_SOURCE


def _present(value: str | None) -> bool:
    return value is not None and bool(value.strip())


def _identifier_issues(value: str | None, *, field: str, currency: bool) -> list[SourceIssue]:
    if not _present(value):
        return [SourceIssue("MISSING_SOURCE_VALUE", field, "Quellenangabe fehlt.")]
    pattern = r"[A-Z]{3}" if currency else r"[A-Z0-9]{6}"
    if value is not None and re.fullmatch(pattern, value) is None:
        return [
            SourceIssue(
                "CURRENCY_FORMAT_INVALID" if currency else "WKN_FORMAT_INVALID",
                field,
                "Quellenwert hat nicht das erwartete Format; keine stille Normalisierung.",
            )
        ]
    return []


def _axis_issues(axis: ResearchPriceAxis, prefix: str) -> list[SourceIssue]:
    issues = _identifier_issues(axis.wkn, field=f"{prefix}_wkn", currency=False)
    issues.extend(_identifier_issues(axis.currency, field=f"{prefix}_currency", currency=True))
    for field, price in zip(PRICE_FIELDS, axis.prices(), strict=True):
        if price is None:
            issues.append(SourceIssue("MISSING_SOURCE_VALUE", f"{prefix}_{field}", "Kurs fehlt."))
    return issues


def review_case(case: ResearchCase, cutoff: date) -> ReviewedCase:
    """Review source facts only; a usable source is not qualified market evidence."""
    issues = _axis_issues(case.underlying, "underlying")
    issues.extend(_axis_issues(case.derivative, "derivative"))
    issues.extend(_identifier_issues(case.strike_currency, field="strike_currency", currency=True))
    if not _present(case.underlying_name):
        issues.append(
            SourceIssue("MISSING_SOURCE_VALUE", "underlying_name", "Basiswertname fehlt.")
        )
    has_sheet_row = _present(case.source_sheet) and case.source_row is not None
    if not has_sheet_row and not _present(case.source_document):
        issues.append(SourceIssue("SOURCE_LOCATOR_MISSING", "source_document", "Herkunft fehlt."))
    if (_present(case.source_sheet) and case.source_row is None) or (
        case.source_row is not None and not _present(case.source_sheet)
    ):
        issues.append(SourceIssue("SOURCE_LOCATOR_INCOMPLETE", "source_row", "Blatt/Zeile fehlt."))
    if (
        case.derivative.currency is not None
        and case.derivative.currency != REQUIRED_DERIVATIVE_CURRENCY
    ):
        issues.append(
            SourceIssue(
                "DERIVATIVE_CURRENCY_CONFLICT",
                "derivative_currency",
                "Quellenwährung widerspricht der separat erklärten EUR-Produktnotierung.",
            )
        )
    if (
        _present(case.strike_currency)
        and _present(case.underlying.currency)
        and case.strike_currency != case.underlying.currency
    ):
        issues.append(
            SourceIssue(
                "STRIKE_CURRENCY_CONTRACT_REVIEW",
                "strike_currency",
                "Abweichende Basispreis-/Basiswertwährung erfordert Vertragsbeleg.",
            )
        )
    if case.strike is None:
        issues.append(SourceIssue("MISSING_SOURCE_VALUE", "strike", "Basispreis fehlt."))
    if case.derivative_type == DerivativeType.UNKNOWN:
        issues.append(
            SourceIssue("DERIVATIVE_TYPE_UNRESOLVED", "derivative_type", "Typ ungeklärt.")
        )
    if case.derivative_type == DerivativeType.TURBO_LONG:
        issues.append(
            SourceIssue(
                "TURBO_TERMS_REQUIRED",
                "derivative_type",
                "KO-, Finanzierungs- und Restwertbelege sind zusätzlich erforderlich.",
            )
        )
    if case.maturity_date is None and case.open_end is not True:
        issues.append(
            SourceIssue("MATURITY_OR_OPEN_END_MISSING", "maturity_date", "Laufzeit ist ungeklärt.")
        )
    if case.maturity_date is not None:
        if case.open_end is True:
            issues.append(
                SourceIssue("MATURITY_OPEN_END_CONFLICT", "open_end", "Fälligkeit und Open End.")
            )
        if case.maturity_date < case.publication_date:
            issues.append(
                SourceIssue(
                    "MATURITY_BEFORE_PUBLICATION",
                    "maturity_date",
                    "Fälligkeit vor Veröffentlichung.",
                )
            )
    if case.publication_date >= cutoff:
        issues.append(
            SourceIssue(
                "NO_POST_PUBLICATION_WINDOW",
                "publication_date",
                "Bis zum Stichtag ist keine abgeschlossene Folgesitzung aus DATE_ONLY ableitbar.",
            )
        )
    return ReviewedCase(case, tuple(issues))


def review_input(
    source: ResearchInput, *, cutoff: date, expected_count: int
) -> tuple[ReviewedCase, ...]:
    if expected_count <= 0:
        raise PreparationError("INVALID_EXPECTED_COUNT", "Sollanzahl muss positiv sein.")
    if len(source.cases) != expected_count:
        raise PreparationError(
            "CASE_COUNT_MISMATCH", f"Soll {expected_count}, Ist {len(source.cases)} Empfehlungen."
        )
    issue_ids: set[str] = set()
    economic_keys: set[tuple[str, str | None, str | None]] = set()
    for case in source.cases:
        if case.economic_key in economic_keys:
            raise PreparationError(
                "DUPLICATE_ECONOMIC_KEY", f"Doppelter Schlüssel: {case.issue_id}"
            )
        if case.issue_id in issue_ids:
            raise PreparationError("DUPLICATE_ISSUE_ID", f"Doppelte Ausgabe-ID: {case.issue_id}")
        economic_keys.add(case.economic_key)
        issue_ids.add(case.issue_id)
    return tuple(review_case(case, cutoff) for case in source.cases)
