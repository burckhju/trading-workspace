"""Prepare or fetch one bounded ARIVA evaluation using existing position bindings.

The default reads only the local position-coverage GET. ``--fetch`` additionally
uses explicitly supplied ARIVA_MDS_CLIENT_ID / ARIVA_MDS_CLIENT_SECRET environment
values. Neither mode changes application data or qualifies a B58 source.
"""

import argparse
import asyncio
import hashlib
import json
import logging
import os
import re
import tempfile
from collections.abc import Callable, Mapping, Sequence
from contextlib import AsyncExitStack
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Never, TextIO
from urllib.parse import urlsplit

import httpx
from pydantic import SecretStr, TypeAdapter

from app.features.market.contracts import is_canonical_isin
from app.features.market_data.service.position_quote_coverage import (
    PositionQuoteCoverageReport,
)
from app.providers.ariva_mds.evaluation import (
    MAX_ISINS,
    MAX_RESPONSE_BYTES,
    ArivaCredentials,
    ArivaProbeClient,
    ArivaProbeError,
    CapturedResponse,
    inspect_marketstates,
)

SCHEMA_VERSION = "ARIVA_B58_EVALUATION_PROBE_V1"
COVERAGE_PATH = "/api/v1/market-data/positions/quote-coverage"
_COVERAGE = TypeAdapter(PositionQuoteCoverageReport)
_CODE = re.compile(r"[A-Z][A-Z0-9_]{0,119}\Z")


class ProbeInputError(ValueError):
    """Fixed local error code; never include response bodies or secret inputs."""


@dataclass(frozen=True)
class ProbeOptions:
    fetch: bool = False
    api_url: str = "http://127.0.0.1:8000"
    output: Path | None = None


def _now() -> datetime:
    return datetime.now(UTC)


def _api_url(value: str) -> str:
    try:
        url = urlsplit(value)
        port = url.port
    except ValueError:
        raise ProbeInputError("LOCAL_API_URL_INVALID") from None
    if (
        url.scheme != "http"
        or url.hostname not in {"localhost", "127.0.0.1", "::1"}
        or url.username is not None
        or url.password is not None
        or url.path not in {"", "/"}
        or url.query
        or url.fragment
        or (port is not None and not 1 <= port <= 65535)
    ):
        raise ProbeInputError("LOCAL_API_URL_INVALID")
    return value.rstrip("/")


def _reserve_report(path: Path | None, now: datetime) -> tuple[Path, TextIO]:
    if path is None:
        descriptor, filename = tempfile.mkstemp(
            prefix=f"trading-workspace-ariva-b58-{now:%Y%m%dT%H%M%SZ}-", suffix=".json"
        )
        return Path(filename), os.fdopen(descriptor, "w", encoding="utf-8")
    destination = path.absolute()
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(destination, flags, 0o600)
    except FileExistsError:
        raise ProbeInputError("REPORT_ALREADY_EXISTS") from None
    return destination, os.fdopen(descriptor, "w", encoding="utf-8")


async def _coverage(
    http: httpx.AsyncClient, url: str, request: dict[str, Any], clock: Callable[[], datetime]
) -> PositionQuoteCoverageReport:
    request.update(operation="LOCAL_POSITION_COVERAGE", url=url, started_at=clock().isoformat())
    try:
        async with asyncio.timeout(30):
            async with http.stream(
                "GET",
                url,
                headers={"Accept": "application/json", "Authorization": ""},
                follow_redirects=False,
                timeout=10,
            ) as response:
                request["http_status"] = response.status_code
                if response.status_code != 200:
                    raise ProbeInputError("LOCAL_COVERAGE_HTTP_FAILED")
                mime = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
                if mime != "application/json":
                    raise ProbeInputError("LOCAL_COVERAGE_CONTENT_TYPE_INVALID")
                raw = bytearray()
                async for chunk in response.aiter_bytes():
                    raw.extend(chunk)
                    if len(raw) > MAX_RESPONSE_BYTES:
                        raise ProbeInputError("LOCAL_COVERAGE_RESPONSE_TOO_LARGE")
        request.update(sha256=hashlib.sha256(raw).hexdigest(), response_bytes=len(raw))
        try:
            report = _COVERAGE.validate_json(bytes(raw))
        except ValueError:
            raise ProbeInputError("LOCAL_COVERAGE_PAYLOAD_INVALID") from None
        if report.assessed_at.utcoffset() is None:
            raise ProbeInputError("LOCAL_COVERAGE_CLOCK_INVALID")
        if report.summary.open_positions != len(report.items):
            raise ProbeInputError("LOCAL_COVERAGE_POSITION_COUNT_MISMATCH")
        return report
    except (httpx.HTTPError, TimeoutError):
        raise ProbeInputError("LOCAL_COVERAGE_TRANSPORT_FAILED") from None
    finally:
        request["completed_at"] = clock().isoformat()


def _plan(coverage: PositionQuoteCoverageReport) -> dict[str, Any]:
    isins = sorted(
        {row.isin for row in coverage.items if row.isin is not None and is_canonical_isin(row.isin)}
    )
    bindings = [
        {
            "position_id": str(row.position_id),
            "trade_id": str(row.trade_id),
            "warrant_id": str(row.warrant_id),
            "isin": row.isin,
            "wkn": row.wkn,
            "selected_provider": row.selected_provider,
            "selection_status": row.selection_status,
            "selection_reason": row.selection_reason,
            "selection_policy_version": row.policy_version,
            "selected_at": row.selected_at.isoformat() if row.selected_at else None,
            "listing_id": str(row.warrant_listing_id) if row.warrant_listing_id else None,
            "mapping_id": str(row.mapping_id) if row.mapping_id else None,
            "mapping_version": row.mapping_version,
            "provider_exchange_code": row.provider_exchange_code,
            "mic": row.mic,
            "currency": row.currency,
            "identity_valid": row.identity_valid,
            "source_health": row.source_health.value,
            "target_status": (
                "PLANNED" if is_canonical_isin(row.isin) else "ISIN_MISSING_OR_INVALID"
            ),
        }
        for row in coverage.items
    ]
    return {
        "coverage_assessed_at": coverage.assessed_at.isoformat(),
        "coverage_scope": coverage.assessment_scope,
        "positions": bindings,
        "isins": isins,
        "unique_isins": len(isins),
        "request_source_id": "XSC",
        "request_quality": "REALTIME",
        "listing_variant_selection": "ALL_DELIVERED_VARIANTS_PRESERVED",
        "existing_selection_changed": False,
    }


def _credentials(environ: Mapping[str, str]) -> ArivaCredentials:
    client_id = environ.get("ARIVA_MDS_CLIENT_ID", "")
    client_secret = environ.get("ARIVA_MDS_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        raise ProbeInputError("ARIVA_EVALUATION_CREDENTIALS_MISSING")
    return ArivaCredentials(SecretStr(client_id), SecretStr(client_secret))


def _captured(response: CapturedResponse) -> dict[str, Any]:
    return {
        "url": response.url,
        "retrieved_at": response.retrieved_at.isoformat(),
        "sha256": response.sha256,
        "raw_text": response.raw_text,
        "bytes_definition": "UTF8_DECODED_ORIGINAL_HTTP_BODY",
    }


async def _fetch(
    report: dict[str, Any],
    client: ArivaProbeClient,
    isins: tuple[str, ...],
    clock: Callable[[], datetime],
) -> None:
    report["provider_access_attempted"] = True
    report["provider_operation"] = "SOURCE_WITH_LAZY_CLIENT_CREDENTIALS_AUTHENTICATION"
    source = await client.source()
    report["source_original"] = _captured(source)
    report["provider_operation"] = "MARKETSTATES"
    marketstates = await client.marketstates(isins)
    report["marketstates_original"] = _captured(marketstates)
    findings = inspect_marketstates(marketstates, isins=isins, source=source)
    report["findings"] = findings
    delivered = set(findings.get("delivered_isins", ())) & set(isins)
    listing_captures: list[CapturedResponse] = []
    listing_requests: list[dict[str, Any]] = []
    report["listing_requests"] = listing_requests
    report["listing_originals"] = []
    stopped = False
    for isin in isins:
        request: dict[str, Any] = {"isin": isin}
        listing_requests.append(request)
        if isin not in delivered:
            request["status"] = "NOT_REQUESTED_NO_MATCHING_MARKETSTATE"
            continue
        if stopped:
            request["status"] = "NOT_REQUESTED_AFTER_SOURCE_FAILURE"
            continue
        request.update(status="REQUESTED", started_at=clock().isoformat())
        try:
            report["provider_operation"] = "INSTRUMENT_LISTINGS"
            captured = await client.listings(isin)
            listing_captures.append(captured)
            report["listing_originals"].append({"isin": isin, **_captured(captured)})
            request.update(status="CAPTURED", retrieved_at=captured.retrieved_at.isoformat())
        except ArivaProbeError as exc:
            request.update(status="FAILED", reason=_reason(exc), http_status=exc.http_status)
            # A single missing instrument is disclosed. Other access/transport/
            # schema failures stop this source; never retry or increase fanout.
            stopped = exc.http_status != 404
        finally:
            request["completed_at"] = clock().isoformat()
    report["findings"] = inspect_marketstates(
        marketstates, isins=isins, source=source, listings=tuple(listing_captures)
    )
    report["requested_acquisition_complete"] = all(
        request["status"] == "CAPTURED" for request in listing_requests
    )
    report["provider_operation"] = "COMPLETED"
    report["status"] = "B58_UNQUALIFIED"


def _reason(error: ValueError) -> str:
    reason = str(error)
    return reason if _CODE.fullmatch(reason) else "EVALUATION_PROBE_FAILED"


async def run_probe(
    options: ProbeOptions,
    *,
    backend_http: httpx.AsyncClient | None = None,
    provider_http: httpx.AsyncClient | None = None,
    environ: Mapping[str, str] | None = None,
    clock: Callable[[], datetime] = _now,
) -> tuple[Path, dict[str, Any], int]:
    """Reserve a private report before requests; use only explicit read boundaries."""
    api_url = _api_url(options.api_url)
    started = clock()
    path, output = _reserve_report(options.output, started)
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": "PREPARING",
        "mode": "FETCH" if options.fetch else "PLAN",
        "started_at": started.isoformat(),
        "application_state_read_only": True,
        "provider_access_attempted": False,
        "requested_acquisition_complete": False,
        "b58_qualified": False,
        "listing_binding_verified": False,
        "production_activation_changed": False,
        "snapshot_scope": "SEPARATE_REQUEST_CAPTURES_NOT_ONE_ATOMIC_SNAPSHOT",
        "local_coverage_request": {},
        "limitations": [
            "COVERAGE_USES_EXISTING_POSITION_PROJECTION",
            "XSC_IS_A_PROVIDER_SOURCE_CODE_NOT_AN_ISO_MIC",
            "EXISTING_LISTING_BINDINGS_ARE_CONTEXT_NOT_ARIVA_QUALIFICATION",
            "SNAPSHOT_CANNOT_PROVE_NEGATIVE_STATUS_DELIVERY_OR_RECOVERY",
            "STATUS_ORIGINAL_TIME_AND_SEMANTICS_UNDOCUMENTED",
        ],
    }
    code = 2
    with output:
        try:
            async with AsyncExitStack() as stack:
                if backend_http is None:
                    backend_http = await stack.enter_async_context(
                        httpx.AsyncClient(trust_env=False, follow_redirects=False, timeout=10)
                    )
                coverage = await _coverage(
                    backend_http,
                    api_url + COVERAGE_PATH,
                    report["local_coverage_request"],
                    clock,
                )
                plan = _plan(coverage)
                report["plan"] = plan
                isins = tuple(plan["isins"])
                if not isins:
                    raise ProbeInputError("NO_VALID_HELD_ISINS")
                if len(isins) > MAX_ISINS:
                    raise ProbeInputError("ARIVA_TARGET_LIMIT_EXCEEDED_NO_PARTIAL_FETCH")
                if options.fetch:
                    credentials = _credentials(os.environ if environ is None else environ)
                    if provider_http is None:
                        provider_http = await stack.enter_async_context(
                            httpx.AsyncClient(trust_env=False, follow_redirects=False, timeout=10)
                        )
                    await _fetch(
                        report,
                        ArivaProbeClient(provider_http, credentials, clock=clock),
                        isins,
                        clock,
                    )
                else:
                    report["status"] = "PLAN_PREPARED_NO_PROVIDER_REQUEST"
                    code = 0
        except (ProbeInputError, ArivaProbeError) as exc:
            report.update(status="PROBE_INCOMPLETE", reason=_reason(exc))
            if isinstance(exc, ArivaProbeError):
                report["http_status"] = exc.http_status
        except (httpx.HTTPError, TimeoutError, ValueError):
            report.update(status="PROBE_INCOMPLETE", reason="EVALUATION_PROBE_FAILED")
        finally:
            report["completed_at"] = clock().isoformat()
            json.dump(report, output, ensure_ascii=False, indent=2, default=str)
            output.write("\n")
    return path, report, code


class _Parser(argparse.ArgumentParser):
    def error(self, _message: str) -> Never:
        # argparse normally echoes unknown argument values, including accidental
        # --client-secret inputs. The CLI deliberately accepts no secret flags.
        raise ProbeInputError("CLI_ARGUMENTS_INVALID")


def main(argv: Sequence[str] | None = None) -> int:
    parser = _Parser(description=__doc__)
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--output", type=Path)
    logging.getLogger("httpx").setLevel(logging.CRITICAL)
    logging.getLogger("httpcore").setLevel(logging.CRITICAL)
    try:
        args = parser.parse_args(argv)
        path, report, code = asyncio.run(
            run_probe(ProbeOptions(fetch=args.fetch, api_url=args.api_url, output=args.output))
        )
    except ProbeInputError as error:
        print(json.dumps({"status": "PROBE_NOT_STARTED", "reason": _reason(error)}))
        return 2
    except OSError:
        print(
            json.dumps(
                {
                    "status": "REPORT_OR_IO_FAILED",
                    "reason": "REPORT_FILE_UNAVAILABLE",
                    "provider_access_attempted": "UNKNOWN",
                    "b58_qualified": False,
                }
            )
        )
        return 2
    print(
        json.dumps(
            {
                "status": report["status"],
                "b58_qualified": False,
                "provider_access_attempted": report["provider_access_attempted"],
                "report_file": str(path),
                "report_location": "LOCAL_EXECUTION_FILESYSTEM_CONTAINER_IF_RUN_IN_CONTAINER",
                "reason": report.get("reason"),
            },
            ensure_ascii=False,
        )
    )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
