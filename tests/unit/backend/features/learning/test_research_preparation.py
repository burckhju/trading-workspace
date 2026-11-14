from __future__ import annotations

import csv
import hashlib
import io
import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import cast

import pytest

from app.features.learning.application.research_preparation import (
    PreparationBundle,
    build_research_preparation,
    prepare_research_files,
)
from app.features.learning.application.research_preparation_parsing import parse_research_input
from app.features.learning.domain.research_preparation import (
    INPUT_SCHEMA_VERSION,
    JsonObject,
    JsonValue,
    PreparationError,
)

CUTOFF = date(2026, 11, 10)


def _case(issue_id: str = "2026-SYNTHETIC-001") -> JsonObject:
    return {
        "issue_id": issue_id,
        "publication_date": "2026-01-05",
        "source_sheet": "Synthetic",
        "source_row": 2,
        "source_document": None,
        "underlying_name": "Synthetic Company",
        "underlying_wkn": "A00001",
        "underlying_currency": "USD",
        "underlying_reference_price": "100.00",
        "underlying_target_1": "120.00",
        "underlying_target_2": "130.00",
        "underlying_stop_1": "90.00",
        "underlying_stop_2": "85.00",
        "derivative_wkn": "B00001",
        "derivative_type": "WARRANT_CALL",
        "derivative_type_raw": "Synthetic call warrant",
        "derivative_currency": "EUR",
        "derivative_reference_price": "1.20",
        "derivative_target_1": "1.80",
        "derivative_target_2": "2.40",
        "derivative_stop_1": "0.85",
        "derivative_stop_2": "0.70",
        "strike": "95.00",
        "strike_currency": "USD",
        "maturity_date": "2027-12-31",
        "open_end": False,
    }


def _payload(cases: list[JsonObject]) -> JsonObject:
    return {
        "schema_version": INPUT_SCHEMA_VERSION,
        "source": {"filename": "synthetic.xlsx", "sha256": "0" * 64},
        "cases": list(cases),
    }


def _raw(cases: list[JsonObject]) -> bytes:
    return json.dumps(_payload(cases), ensure_ascii=False).encode("utf-8")


def _prepare(cases: list[JsonObject]) -> PreparationBundle:
    return build_research_preparation(_raw(cases), cutoff=CUTOFF, expected_count=len(cases))


def _objects(value: JsonValue) -> list[JsonObject]:
    assert isinstance(value, list)
    assert all(isinstance(item, dict) for item in value)
    return cast(list[JsonObject], value)


def _codes(report: JsonObject) -> set[str]:
    return {str(issue["code"]) for issue in _objects(report["issues"])}


def test_preserves_exact_source_values_and_separate_currency_axes() -> None:
    case = _case()
    case["derivative_reference_price"] = "1.20000000000000000001"
    raw = _raw([case])
    parsed = parse_research_input(raw)
    price = parsed.cases[0].derivative.reference_price
    assert price is not None
    assert price.value == Decimal("1.20000000000000000001")
    bundle = _prepare([case])
    report = _objects(bundle.manifest["cases"])[0]
    assert report["source_values"] == case
    assert report["source_status"] == "USABLE_SOURCE"
    assert report["publication_precision"] == "DATE_ONLY"
    assert report["historical_result_status"] == "NOT_COMPUTED"
    assert report["issues"] == []
    assert bundle.manifest["input_sha256"] == hashlib.sha256(raw).hexdigest()
    assert bundle.manifest["source_hash_verification"] == "DECLARED_NOT_REHASHED"
    assert bundle.manifest["currency_conversion_performed"] is False
    row = next(csv.DictReader(io.StringIO(bundle.cases_csv.decode("utf-8"))))
    assert row["derivative_reference_price"] == case["derivative_reference_price"]
    assert row["underlying_currency"] == "USD"
    assert row["derivative_currency"] == "EUR"
    assert row["strike_currency"] == "USD"
    assert row["source_sha256"] == "0" * 64


@pytest.mark.parametrize("missing", ["strike_currency", "derivative_currency", "underlying_stop_2"])
def test_missing_source_values_are_not_inferred(missing: str) -> None:
    case = _case()
    case[missing] = None
    report = _objects(_prepare([case]).manifest["cases"])[0]
    assert report["source_status"] == "REVIEW_REQUIRED"
    assert "MISSING_SOURCE_VALUE" in _codes(report)
    values = cast(JsonObject, report["source_values"])
    assert values[missing] is None
    assert report["historical_result_status"] == "NOT_COMPUTED"


def test_currency_and_identifier_conflicts_remain_visible_without_repair() -> None:
    case = _case()
    case.update(
        derivative_currency="USD",
        strike_currency="EUR",
        underlying_wkn="a00001",
        underlying_currency=" usd ",
    )
    bundle = _prepare([case])
    report = _objects(bundle.manifest["cases"])[0]
    assert _codes(report) == {
        "DERIVATIVE_CURRENCY_CONFLICT",
        "STRIKE_CURRENCY_CONTRACT_REVIEW",
        "WKN_FORMAT_INVALID",
        "CURRENCY_FORMAT_INVALID",
    }
    assert report["source_values"] == case
    product = _objects(bundle.data_requests["derivative"])[0]
    assert product["source_currency"] == "USD"
    assert product["required_quote_currency"] == "EUR"
    assert product["listing_status"] == "UNVERIFIED_LISTING"


@pytest.mark.parametrize("bad_price", ["0", "-1", "NaN", "Infinity", "1,20", " 1.20 ", "1_000"])
def test_invalid_price_strings_prevent_preparation(bad_price: str) -> None:
    case = _case()
    case["derivative_reference_price"] = bad_price
    with pytest.raises(PreparationError):
        _prepare([case])


@pytest.mark.parametrize("bad_value", [12, True, [], {}])
def test_nonstring_source_money_is_rejected(bad_value: JsonValue) -> None:
    case = _case()
    case["strike"] = bad_value
    with pytest.raises(PreparationError, match="Zeichenfolge"):
        _prepare([case])


@pytest.mark.parametrize("literal", [b"1.20", b"NaN", b"Infinity"])
def test_json_numeric_price_literals_are_not_converted_to_floats(literal: bytes) -> None:
    raw = _raw([_case()]).replace(b'"1.20"', literal)
    with pytest.raises(PreparationError) as rejected:
        build_research_preparation(raw, cutoff=CUTOFF, expected_count=1)
    assert rejected.value.code == "INVALID_NUMERIC_LITERAL"


def test_zero_strike_is_allowed_but_negative_strike_is_rejected() -> None:
    case = _case()
    case["strike"] = "0.000"
    report = _objects(_prepare([case]).manifest["cases"])[0]
    assert report["source_status"] == "USABLE_SOURCE"
    assert report["source_values"] == case
    case["strike"] = "-0.01"
    with pytest.raises(PreparationError) as rejected:
        _prepare([case])
    assert rejected.value.code == "INVALID_PRICE"


@pytest.mark.parametrize("bad_date", ["20261110", "2026-02-30", "2026-11-10T00:00:00Z", None])
def test_publication_requires_calendar_date_without_manufactured_time(bad_date: JsonValue) -> None:
    case = _case()
    case["publication_date"] = bad_date
    with pytest.raises(PreparationError) as rejected:
        _prepare([case])
    assert rejected.value.code == "INVALID_DATE"


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("source_row", 0, "INVALID_SOURCE_ROW"),
        ("source_row", True, "INVALID_SOURCE_ROW"),
        ("open_end", 1, "INVALID_TYPE"),
        ("issue_id", " ", "INVALID_STRING"),
        ("derivative_type", "CALL", "INVALID_DERIVATIVE_TYPE"),
    ],
)
def test_invalid_field_types_and_enums_are_fatal(field: str, value: JsonValue, code: str) -> None:
    case = _case()
    case[field] = value
    with pytest.raises(PreparationError) as rejected:
        _prepare([case])
    assert rejected.value.code == code


def test_missing_location_and_partial_location_are_retained_for_review() -> None:
    missing = _case()
    missing.update(source_sheet=None, source_row=None)
    partial = _case("2026-SYNTHETIC-002")
    partial.update(source_row=None, source_document="synthetic.pdf")
    reports = _objects(_prepare([missing, partial]).manifest["cases"])
    assert "SOURCE_LOCATOR_MISSING" in _codes(reports[0])
    assert "SOURCE_LOCATOR_INCOMPLETE" in _codes(reports[1])
    partial["source_sheet"] = None
    report = _objects(_prepare([partial]).manifest["cases"])[0]
    assert report["source_status"] == "USABLE_SOURCE"


def test_maturity_conflicts_do_not_drop_cases_or_create_settlement_results() -> None:
    case = _case()
    case.update(maturity_date="2025-12-31", open_end=True)
    bundle = _prepare([case])
    report = _objects(bundle.manifest["cases"])[0]
    assert _codes(report) == {"MATURITY_BEFORE_PUBLICATION", "MATURITY_OPEN_END_CONFLICT"}
    assert report["historical_result_status"] == "NOT_COMPUTED"
    assert report["source_values"] == case
    request = _objects(bundle.data_requests["derivative"])[0]
    window = _objects(request["case_windows"])[0]
    assert window["maturity_on_or_before_cutoff"] is True
    assert "SETTLEMENT_RULES_AND_ACTUAL_SETTLEMENT_EVIDENCE_WHEN_DUE" in cast(
        list[str], request["required_evidence"]
    )


def test_missing_maturity_needs_explicit_open_end_and_turbos_keep_additional_needs() -> None:
    case = _case()
    case.update(maturity_date=None, open_end=None, derivative_type="UNKNOWN", strike=None)
    report = _objects(_prepare([case]).manifest["cases"])[0]
    assert {
        "MATURITY_OR_OPEN_END_MISSING",
        "DERIVATIVE_TYPE_UNRESOLVED",
        "MISSING_SOURCE_VALUE",
    } <= _codes(report)
    case.update(open_end=True, derivative_type="TURBO_LONG", strike="0")
    bundle = _prepare([case])
    report = _objects(bundle.manifest["cases"])[0]
    assert _codes(report) == {"TURBO_TERMS_REQUIRED"}
    product = _objects(bundle.data_requests["derivative"])[0]
    assert product["derivative_types"] == ["TURBO_LONG"]
    assert "EFFECTIVE_DATED_KNOCK_OUT_BARRIER" in cast(list[str], product["required_evidence"])
    assert _objects(product["case_windows"])[0]["maturity_on_or_before_cutoff"] is None


@pytest.mark.parametrize("publication", ["2026-11-10", "2026-11-11"])
def test_cutoff_day_and_future_case_have_no_invented_following_session(publication: str) -> None:
    case = _case()
    case["publication_date"] = publication
    bundle = _prepare([case])
    assert "NO_POST_PUBLICATION_WINDOW" in _codes(_objects(bundle.manifest["cases"])[0])
    for axis in ("underlying", "derivative"):
        group = _objects(bundle.data_requests[axis])[0]
        assert group["from_date"] is None
        assert group["window_status"] == "NO_POST_PUBLICATION_WINDOW"
        assert group["issue_ids"] == [case["issue_id"]]


def test_data_groups_preserve_axes_currencies_unknowns_and_all_case_ids() -> None:
    cases = [_case(f"2026-SYNTHETIC-{index:03}") for index in range(1, 7)]
    cases[1]["publication_date"] = "2026-11-10"
    cases[2]["underlying_currency"] = "EUR"
    cases[3]["underlying_wkn"] = None
    cases[4]["underlying_wkn"] = None
    cases[5]["underlying_wkn"] = "B00001"
    bundle = _prepare(cases)
    underlying = _objects(bundle.data_requests["underlying"])
    assert len(underlying) == 5
    usd = next(g for g in underlying if g["wkn"] == "A00001" and g["source_currency"] == "USD")
    assert usd["issue_ids"] == [cases[0]["issue_id"], cases[1]["issue_id"]]
    assert usd["from_date"] == "2026-01-05"
    unknown = [group for group in underlying if group["wkn"] is None]
    assert len(unknown) == 2
    assert {g["unresolved_case_id"] for g in unknown} == {
        cases[3]["issue_id"],
        cases[4]["issue_id"],
    }
    derivative = _objects(bundle.data_requests["derivative"])
    assert len(derivative) == 1
    assert derivative[0]["issue_ids"] == [case["issue_id"] for case in cases]


def test_fingerprint_binds_exact_source_version_but_not_json_whitespace() -> None:
    case = _case()
    first = _prepare([case])
    reformatted = build_research_preparation(
        json.dumps(_payload([case]), indent=2).encode(), cutoff=CUTOFF, expected_count=1
    )
    fingerprint = _objects(first.manifest["cases"])[0]["source_fingerprint_sha256"]
    assert _objects(reformatted.manifest["cases"])[0]["source_fingerprint_sha256"] == fingerprint
    assert first.manifest["input_sha256"] != reformatted.manifest["input_sha256"]
    case["derivative_reference_price"] = "1.2"
    changed = _prepare([case])
    assert _objects(changed.manifest["cases"])[0]["source_fingerprint_sha256"] != fingerprint


@pytest.mark.parametrize("same_key", [True, False])
def test_duplicates_are_fatal_before_creating_output(tmp_path: Path, same_key: bool) -> None:
    first, second = _case(), _case()
    if not same_key:
        second["derivative_wkn"] = "B00002"
    source = tmp_path / "source.json"
    source.write_bytes(_raw([first, second]))
    output = tmp_path / "rejected"
    with pytest.raises(PreparationError) as rejected:
        prepare_research_files(
            input_path=source, output_dir=output, cutoff=CUTOFF, expected_count=2
        )
    assert rejected.value.code == ("DUPLICATE_ECONOMIC_KEY" if same_key else "DUPLICATE_ISSUE_ID")
    assert not output.exists()


@pytest.mark.parametrize("expected", [222, 0, -1])
def test_count_errors_are_fatal_before_creating_output(tmp_path: Path, expected: int) -> None:
    source = tmp_path / "source.json"
    source.write_bytes(_raw([_case()]))
    output = tmp_path / "rejected"
    with pytest.raises(PreparationError):
        prepare_research_files(
            input_path=source, output_dir=output, cutoff=CUTOFF, expected_count=expected
        )
    assert not output.exists()


def test_222_cases_round_trip_once_with_deterministic_outputs_and_artifact_hashes(
    tmp_path: Path,
) -> None:
    cases = [_case(f"2026-SYNTHETIC-{index:03}") for index in range(1, 223)]
    source = tmp_path / "source.json"
    source.write_bytes(_raw(cases))
    first, second = tmp_path / "first", tmp_path / "second"
    bundle = prepare_research_files(
        input_path=source, output_dir=first, cutoff=CUTOFF, expected_count=222
    )
    prepare_research_files(input_path=source, output_dir=second, cutoff=CUTOFF, expected_count=222)
    assert {path.name for path in first.iterdir()} == {
        "cases.csv",
        "data_requests.json",
        "manifest.json",
    }
    for path in first.iterdir():
        assert path.read_bytes() == (second / path.name).read_bytes()
    reports = _objects(bundle.manifest["cases"])
    assert len({str(report["issue_id"]) for report in reports}) == 222
    assert bundle.manifest["historical_result_counts"] == {"NOT_COMPUTED": 222}
    rows = list(csv.DictReader(io.StringIO(bundle.cases_csv.decode())))
    assert len(rows) == 222
    assert {row["issue_id"] for row in rows} == {str(case["issue_id"]) for case in cases}
    hashes = cast(JsonObject, bundle.manifest["artifacts_sha256"])
    for name, expected_hash in hashes.items():
        assert hashlib.sha256((first / name).read_bytes()).hexdigest() == expected_hash


@pytest.mark.parametrize("kind", ["empty_directory", "file", "broken_symlink"])
def test_existing_output_is_never_overwritten(tmp_path: Path, kind: str) -> None:
    source = tmp_path / "source.json"
    source.write_bytes(_raw([_case()]))
    output = tmp_path / "existing"
    if kind == "empty_directory":
        output.mkdir()
    elif kind == "file":
        output.write_text("preserve")
    else:
        output.symlink_to(tmp_path / "missing")
    with pytest.raises(PreparationError) as rejected:
        prepare_research_files(
            input_path=source, output_dir=output, cutoff=CUTOFF, expected_count=1
        )
    assert rejected.value.code == "OUTPUT_EXISTS"
    if kind == "file":
        assert output.read_text() == "preserve"


@pytest.mark.parametrize("raw", [b"{}", b"[]", b"{", b"\xff", b'{"x":1,"x":2}'])
def test_invalid_json_and_missing_contract_fields_are_rejected(raw: bytes) -> None:
    with pytest.raises(PreparationError):
        build_research_preparation(raw, cutoff=CUTOFF, expected_count=1)


@pytest.mark.parametrize("change", ["schema", "hash", "case_list", "extra", "missing", "source"])
def test_strict_schema_rejects_unknown_or_malformed_structure(change: str) -> None:
    case = _case()
    payload = _payload([case])
    if change == "schema":
        payload["schema_version"] = "unknown"
    elif change == "hash":
        payload["source"] = {"filename": "synthetic.xlsx", "sha256": "bad"}
    elif change == "case_list":
        payload["cases"] = None
    elif change == "extra":
        case["guessed_return"] = "0"
    elif change == "missing":
        del case["strike_currency"]
    else:
        payload["source"] = None
    with pytest.raises(PreparationError):
        build_research_preparation(json.dumps(payload).encode(), cutoff=CUTOFF, expected_count=1)
