"""Deterministic file preparation, without operational import or provider access."""

from __future__ import annotations

import csv
import hashlib
import io
import json
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal

from app.features.learning.application.research_preparation_parsing import parse_research_input
from app.features.learning.domain.research_preparation import (
    CASE_FIELDS,
    HISTORICAL_RESULT_STATUS,
    INPUT_SCHEMA_VERSION,
    PREPARATION_VERSION,
    PUBLICATION_PRECISION,
    REQUIRED_DERIVATIVE_CURRENCY,
    DerivativeType,
    JsonObject,
    JsonValue,
    PreparationError,
    ResearchInput,
    ReviewedCase,
    SourceStatus,
    review_input,
)

_UNDERLYING_REQUIREMENTS = (
    "VERIFIED_INSTRUMENT_IDENTITY",
    "VERIFIED_LISTING_CURRENCY_AND_PRICE_UNIT",
    "TRADING_CALENDAR_AND_SESSION_TIMES",
    "PUBLICATION_TIME_AND_FIRST_ELIGIBLE_SESSION",
    "RAW_OHLC_WITH_PROVENANCE_AND_QUALITY",
    "SPLITS_AND_DIVIDENDS_WITH_EFFECTIVE_DATES",
    "RULE_SPECIFIC_WARMUP_WINDOW",
)
_DERIVATIVE_REQUIREMENTS = (
    "VERIFIED_PRODUCT_IDENTITY_AND_UNDERLYING_LINK",
    "VERIFIED_EUR_LISTING_AND_PRICE_UNIT",
    "HISTORICAL_BID_ASK_WITH_ORIGINAL_TIME_VENUE_AND_QUALITY",
    "PRODUCT_CALENDAR_AND_FIRST_ELIGIBLE_SESSION",
    "EFFECTIVE_DATED_TERMS_RATIO_STRIKE_AND_CURRENCIES",
    "LAST_TRADING_DAY_AND_MATURITY_OR_OPEN_END_EVIDENCE",
    "SETTLEMENT_RULES_AND_ACTUAL_SETTLEMENT_EVIDENCE_WHEN_DUE",
)
_TURBO_REQUIREMENTS = (
    "EFFECTIVE_DATED_KNOCK_OUT_BARRIER",
    "FINANCING_LEVEL_AND_ADJUSTMENTS",
    "KNOCK_OUT_EVENT_AND_RESIDUAL_VALUE_EVIDENCE",
)


def _json_bytes(value: JsonObject) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _fingerprint(source: ResearchInput, reviewed: ReviewedCase) -> str:
    payload: JsonObject = {
        "input_schema_version": INPUT_SCHEMA_VERSION,
        "source": source.source.snapshot(),
        "case": reviewed.source.snapshot(),
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _case_report(source: ResearchInput, reviewed: ReviewedCase) -> JsonObject:
    return {
        "issue_id": reviewed.source.issue_id,
        "economic_key": list(reviewed.source.economic_key),
        "source_fingerprint_sha256": _fingerprint(source, reviewed),
        "publication_precision": PUBLICATION_PRECISION,
        "source_status": reviewed.status.value,
        "historical_result_status": HISTORICAL_RESULT_STATUS,
        "issues": [issue.snapshot() for issue in reviewed.issues],
        "source_values": reviewed.source.snapshot(),
    }


def _case_csv(source: ResearchInput, reviewed_cases: tuple[ReviewedCase, ...]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        (
            "source_filename",
            "source_sha256",
            *CASE_FIELDS,
            "publication_precision",
            "source_status",
            "historical_result_status",
            "source_fingerprint_sha256",
            "issues_json",
        )
    )
    for reviewed in reviewed_cases:
        values = reviewed.source.snapshot()
        writer.writerow(
            (
                source.source.filename,
                source.source.sha256,
                *(values[field] for field in CASE_FIELDS),
                PUBLICATION_PRECISION,
                reviewed.status.value,
                HISTORICAL_RESULT_STATUS,
                _fingerprint(source, reviewed),
                json.dumps(
                    [issue.snapshot() for issue in reviewed.issues],
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ),
            )
        )
    return buffer.getvalue().encode("utf-8")


def _case_window(reviewed: ReviewedCase, cutoff: date) -> JsonObject:
    case = reviewed.source
    return {
        "issue_id": case.issue_id,
        "publication_date": case.publication_date.isoformat(),
        "publication_precision": PUBLICATION_PRECISION,
        "publication_before_cutoff": case.publication_date < cutoff,
        "first_eligible_session_status": "CALENDAR_AND_PUBLICATION_TIME_REQUIRED",
        "maturity_date": case.maturity_date.isoformat() if case.maturity_date else None,
        "maturity_on_or_before_cutoff": (
            case.maturity_date <= cutoff if case.maturity_date is not None else None
        ),
        "open_end": case.open_end,
    }


def _request_groups(
    reviewed_cases: tuple[ReviewedCase, ...],
    *,
    axis: Literal["underlying", "derivative"],
    cutoff: date,
) -> list[JsonValue]:
    groups: dict[tuple[str | None, str | None, str | None], list[ReviewedCase]] = {}
    for reviewed in reviewed_cases:
        prices = reviewed.source.underlying if axis == "underlying" else reviewed.source.derivative
        unresolved_case = (
            reviewed.source.issue_id if prices.wkn is None or not prices.wkn.strip() else None
        )
        key = (prices.wkn, prices.currency, unresolved_case)
        groups.setdefault(key, []).append(reviewed)
    result: list[JsonValue] = []
    for (wkn, currency, unresolved_case), cases in sorted(
        groups.items(), key=lambda item: tuple(value or "" for value in item[0])
    ):
        cases.sort(key=lambda reviewed: reviewed.source.issue_id)
        eligible_dates = [
            case.source.publication_date for case in cases if case.source.publication_date < cutoff
        ]
        requirements = list(
            _UNDERLYING_REQUIREMENTS if axis == "underlying" else _DERIVATIVE_REQUIREMENTS
        )
        if axis == "derivative" and any(
            case.source.derivative_type == DerivativeType.TURBO_LONG for case in cases
        ):
            requirements.extend(_TURBO_REQUIREMENTS)
        group: JsonObject = {
            "axis": axis,
            "wkn": wkn,
            "source_currency": currency,
            "unresolved_case_id": unresolved_case,
            "listing_status": "UNVERIFIED_LISTING",
            "provider_status": "NOT_SELECTED",
            "issue_ids": [case.source.issue_id for case in cases],
            "from_date": min(eligible_dates).isoformat() if eligible_dates else None,
            "to_date": cutoff.isoformat(),
            "window_status": (
                "CANDIDATE_WINDOW_REQUIRES_CALENDAR"
                if eligible_dates
                else "NO_POST_PUBLICATION_WINDOW"
            ),
            "warmup_status": "REQUIRES_EXPLICIT_RULE_AND_CALENDAR_DEFINITION",
            "required_evidence": list(requirements),
            "case_windows": [_case_window(case, cutoff) for case in cases],
            "cases_requiring_source_review": [
                case.source.issue_id
                for case in cases
                if case.status == SourceStatus.REVIEW_REQUIRED
            ],
        }
        if axis == "derivative":
            group["required_quote_currency"] = REQUIRED_DERIVATIVE_CURRENCY
            group["derivative_types"] = [
                product_type
                for product_type in sorted({case.source.derivative_type.value for case in cases})
            ]
        result.append(group)
    return result


@dataclass(frozen=True, slots=True)
class PreparationBundle:
    manifest: JsonObject
    cases_csv: bytes
    data_requests: JsonObject

    def output_files(self) -> tuple[tuple[str, bytes], ...]:
        """The completion manifest is written only after both other complete files."""
        return (
            ("cases.csv", self.cases_csv),
            ("data_requests.json", _json_bytes(self.data_requests)),
            ("manifest.json", _json_bytes(self.manifest)),
        )


def build_research_preparation(
    raw: bytes, *, cutoff: date, expected_count: int
) -> PreparationBundle:
    source = parse_research_input(raw)
    reviewed_cases = review_input(source, cutoff=cutoff, expected_count=expected_count)
    input_sha256 = hashlib.sha256(raw).hexdigest()
    data_requests: JsonObject = {
        "schema_version": "hebeltrader-research-data-requests-v1",
        "preparation_version": PREPARATION_VERSION,
        "input_sha256": input_sha256,
        "cutoff": cutoff.isoformat(),
        "status": "DATA_QUALIFICATION_REQUIRED",
        "historical_result_status": HISTORICAL_RESULT_STATUS,
        "underlying": _request_groups(reviewed_cases, axis="underlying", cutoff=cutoff),
        "derivative": _request_groups(reviewed_cases, axis="derivative", cutoff=cutoff),
    }
    cases_csv = _case_csv(source, reviewed_cases)
    status_counts = Counter(case.status for case in reviewed_cases)
    issue_counts = Counter(issue.code for case in reviewed_cases for issue in case.issues)
    manifest: JsonObject = {
        "schema_version": "hebeltrader-research-manifest-v1",
        "preparation_version": PREPARATION_VERSION,
        "input_schema_version": INPUT_SCHEMA_VERSION,
        "status": "PREPARED",
        "cutoff": cutoff.isoformat(),
        "expected_count": expected_count,
        "case_count": len(reviewed_cases),
        "source": source.source.snapshot(),
        "source_hash_verification": "DECLARED_NOT_REHASHED",
        "input_sha256": input_sha256,
        "publication_precision": PUBLICATION_PRECISION,
        "source_status_counts": {status.value: status_counts[status] for status in SourceStatus},
        "source_issue_counts": dict(sorted(issue_counts.items())),
        "historical_result_status": HISTORICAL_RESULT_STATUS,
        "historical_result_counts": {HISTORICAL_RESULT_STATUS: len(reviewed_cases)},
        "required_derivative_quote_currency": REQUIRED_DERIVATIVE_CURRENCY,
        "currency_conversion_performed": False,
        "operational_records_created": 0,
        "network_requests": 0,
        "source_validation_scope": "COMPLETENESS_AND_FORMAT_ONLY_NOT_MARKET_QUALIFICATION",
        "artifacts_sha256": {
            "cases.csv": hashlib.sha256(cases_csv).hexdigest(),
            "data_requests.json": hashlib.sha256(_json_bytes(data_requests)).hexdigest(),
        },
        "cases": [_case_report(source, case) for case in reviewed_cases],
    }
    return PreparationBundle(manifest=manifest, cases_csv=cases_csv, data_requests=data_requests)


def prepare_research_files(
    *, input_path: Path, output_dir: Path, cutoff: date, expected_count: int
) -> PreparationBundle:
    """Read one explicit file and exclusively create one new directory with three outputs."""
    if output_dir.exists() or output_dir.is_symlink():
        raise PreparationError(
            "OUTPUT_EXISTS", "Ausgabepfad existiert bereits; kein Überschreiben."
        )
    bundle = build_research_preparation(
        input_path.read_bytes(), cutoff=cutoff, expected_count=expected_count
    )
    files = bundle.output_files()
    try:
        output_dir.mkdir()
    except FileExistsError as exc:
        raise PreparationError(
            "OUTPUT_EXISTS", "Ausgabepfad wurde zwischenzeitlich angelegt."
        ) from exc
    for filename, content in files:
        with (output_dir / filename).open("xb") as output:
            output.write(content)
    return bundle
