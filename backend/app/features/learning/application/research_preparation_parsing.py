"""Strict JSON boundary for the offline research-preparation source contract."""

from __future__ import annotations

import json
import re
from datetime import date
from typing import cast

from app.features.learning.domain.research_preparation import (
    CASE_FIELDS,
    INPUT_SCHEMA_VERSION,
    DerivativeType,
    PreparationError,
    ResearchCase,
    ResearchInput,
    ResearchPriceAxis,
    SourceDecimal,
    SourceFile,
    source_decimal,
)


def parse_date(value: object, *, field: str) -> date:
    if not isinstance(value, str) or re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is None:
        raise PreparationError("INVALID_DATE", f"{field}: YYYY-MM-DD erforderlich.")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise PreparationError("INVALID_DATE", f"{field}: ungültiges Kalenderdatum.") from exc


def _object(value: object, *, field: str, keys: tuple[str, ...]) -> dict[str, object]:
    if not isinstance(value, dict):
        raise PreparationError("INVALID_OBJECT", f"{field}: JSON-Objekt erforderlich.")
    result = cast(dict[str, object], value)
    if set(result) != set(keys):
        missing = sorted(set(keys) - set(result))
        unexpected = sorted(set(result) - set(keys))
        raise PreparationError(
            "INVALID_FIELDS", f"{field}: fehlende Schlüssel {missing}; unbekannte {unexpected}."
        )
    return result


def _string(value: object, *, field: str, nullable: bool = True) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str):
        raise PreparationError("INVALID_TYPE", f"{field}: Zeichenfolge erforderlich.")
    if not nullable and (not value or value != value.strip()):
        raise PreparationError("INVALID_STRING", f"{field}: nicht leer, keine äußeren Leerzeichen.")
    return value


def _required_string(value: object, *, field: str) -> str:
    result = _string(value, field=field, nullable=False)
    assert result is not None
    return result


def _price(value: object, *, field: str, allow_zero: bool = False) -> SourceDecimal | None:
    raw = _string(value, field=field)
    return None if raw is None else source_decimal(raw, field=field, allow_zero=allow_zero)


def _axis(values: dict[str, object], prefix: str) -> ResearchPriceAxis:
    return ResearchPriceAxis(
        wkn=_string(values[f"{prefix}_wkn"], field=f"{prefix}_wkn"),
        currency=_string(values[f"{prefix}_currency"], field=f"{prefix}_currency"),
        reference_price=_price(
            values[f"{prefix}_reference_price"], field=f"{prefix}_reference_price"
        ),
        target_1=_price(values[f"{prefix}_target_1"], field=f"{prefix}_target_1"),
        target_2=_price(values[f"{prefix}_target_2"], field=f"{prefix}_target_2"),
        stop_1=_price(values[f"{prefix}_stop_1"], field=f"{prefix}_stop_1"),
        stop_2=_price(values[f"{prefix}_stop_2"], field=f"{prefix}_stop_2"),
    )


def _case(value: object, index: int) -> ResearchCase:
    values = _object(value, field=f"cases[{index}]", keys=CASE_FIELDS)
    source_row = values["source_row"]
    if source_row is not None and (
        not isinstance(source_row, int) or isinstance(source_row, bool) or source_row <= 0
    ):
        raise PreparationError("INVALID_SOURCE_ROW", "source_row: positive Ganzzahl oder null.")
    open_end = values["open_end"]
    if open_end is not None and not isinstance(open_end, bool):
        raise PreparationError("INVALID_TYPE", "open_end: Boolean oder null erforderlich.")
    raw_type = _required_string(values["derivative_type"], field="derivative_type")
    try:
        derivative_type = DerivativeType(raw_type)
    except ValueError as exc:
        raise PreparationError(
            "INVALID_DERIVATIVE_TYPE", "Unbekannter derivative_type-Enumwert."
        ) from exc
    return ResearchCase(
        issue_id=_required_string(values["issue_id"], field="issue_id"),
        publication_date=parse_date(values["publication_date"], field="publication_date"),
        source_sheet=_string(values["source_sheet"], field="source_sheet"),
        source_row=source_row,
        source_document=_string(values["source_document"], field="source_document"),
        underlying_name=_string(values["underlying_name"], field="underlying_name"),
        underlying=_axis(values, "underlying"),
        derivative=_axis(values, "derivative"),
        derivative_type=derivative_type,
        derivative_type_raw=_string(values["derivative_type_raw"], field="derivative_type_raw"),
        strike=_price(values["strike"], field="strike", allow_zero=True),
        strike_currency=_string(values["strike_currency"], field="strike_currency"),
        maturity_date=(
            parse_date(values["maturity_date"], field="maturity_date")
            if values["maturity_date"] is not None
            else None
        ),
        open_end=open_end,
    )


def _unique_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise PreparationError("DUPLICATE_JSON_KEY", f"Doppelter JSON-Schlüssel: {key}")
        result[key] = value
    return result


def _reject_numeric_literal(value: str) -> object:
    raise PreparationError("INVALID_NUMERIC_LITERAL", "Dezimalwerte als Zeichenfolgen übergeben.")


def parse_research_input(raw: bytes) -> ResearchInput:
    try:
        decoded: object = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_unique_keys,
            parse_float=_reject_numeric_literal,
            parse_constant=_reject_numeric_literal,
        )
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise PreparationError("INVALID_JSON", "Gültiges UTF-8-JSON erforderlich.") from exc
    values = _object(decoded, field="input", keys=("schema_version", "source", "cases"))
    if values["schema_version"] != INPUT_SCHEMA_VERSION:
        raise PreparationError("INVALID_SCHEMA_VERSION", "Nicht unterstütztes Eingabeschema.")
    source = _object(values["source"], field="source", keys=("filename", "sha256"))
    filename = _required_string(source["filename"], field="source.filename")
    sha256 = _required_string(source["sha256"], field="source.sha256")
    if re.fullmatch(r"[a-fA-F0-9]{64}", sha256) is None:
        raise PreparationError("INVALID_SOURCE_HASH", "source.sha256: 64 Hexadezimalzeichen nötig.")
    cases = values["cases"]
    if not isinstance(cases, list):
        raise PreparationError("INVALID_CASE_LIST", "cases: Liste erforderlich.")
    raw_cases = cast(list[object], cases)
    return ResearchInput(
        SourceFile(filename, sha256), tuple(_case(c, i) for i, c in enumerate(raw_cases))
    )
