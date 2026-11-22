#!/usr/bin/env python3
"""Collect private, passive evidence from an existing managed Linux installation.

Host dependencies: Python standard library, git and the existing local Docker
engine. Never start services, run Compose, contact a provider or modify the
installation. A complete transport is not a qualification of monitoring rules.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
import re
import stat
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

SERVICES = ("backend", "database", "frontend", "issuer-renderer")
APP_SERVICES = ("backend", "frontend", "issuer-renderer")
READ_NAMES = (
    "indicative-entry",
    "product-deadline-review",
    "hebeltrader-original-bid",
    "hebeltrader-targets",
    "hebeltrader-loss",
    "hebeltrader-evidence",
)
COMPLETE_READBACK = "COMPLETE_PASSIVE_READBACK_NOT_RULE_QUALIFICATION"
REFERENCE_SCHEMA_REVISIONS = ["20261118_0060"]
REFERENCE_FILES = frozenset(
    {
        "installation-before.json",
        "installation-after.json",
        "schema.json",
        "monitoring-private.json",
        "summary.json",
    }
)
MAX_REFERENCE_ARCHIVE_BYTES = 16 * 1024 * 1024
MAX_REFERENCE_TAR_BYTES = 16 * 1024 * 1024
MAX_REFERENCE_JSON_BYTES = 8 * 1024 * 1024
MAX_REFERENCE_TOTAL_BYTES = 12 * 1024 * 1024
SOURCE_GAP_COMPLETE = "COMPLETE_PASSIVE_SOURCE_GAP_READ_NOT_PRICE_QUALIFICATION"
BACKEND_PAYLOAD = r"""import asyncio
import json
from datetime import UTC, datetime
from uuid import UUID

import httpx
from pydantic import TypeAdapter, ValidationError

from app.features.market_data.service.position_quote_coverage import PositionQuoteCoverageReport
from app.features.position_monitoring.service.hebeltrader_loss_read import LossStatusReport
from app.features.position_monitoring.service.hebeltrader_original_bid_contracts import (
    HebeltraderOriginalBidReport,
)
from app.features.position_monitoring.service.hebeltrader_target_contracts import (
    HebeltraderTargetsReport,
)
from app.features.position_monitoring.service.indicative_entry_read import IndicativeStatusReport
from app.features.position_monitoring.service.product_deadline_review_read import (
    ProductDeadlineStatusReport,
)
from app.features.trade_position.service.hebeltrader_coverage import HebeltraderCoverage

BASE = "/api/v1/position-monitoring"
INVENTORY = "/api/v1/market-data/positions/quote-coverage"
READS = (
    ("indicative-entry", BASE),
    ("product-deadline-review", BASE),
    ("hebeltrader-original-bid", BASE),
    ("hebeltrader-targets", BASE),
    ("hebeltrader-loss", BASE),
    ("hebeltrader-evidence", "/api/v1/trade-position"),
)
INVENTORY_RESPONSE = TypeAdapter(PositionQuoteCoverageReport)
POSITION_RESPONSES = {
    "indicative-entry": TypeAdapter(IndicativeStatusReport),
    "product-deadline-review": TypeAdapter(ProductDeadlineStatusReport),
    "hebeltrader-original-bid": TypeAdapter(HebeltraderOriginalBidReport),
    "hebeltrader-targets": TypeAdapter(HebeltraderTargetsReport),
    "hebeltrader-loss": TypeAdapter(LossStatusReport),
    "hebeltrader-evidence": TypeAdapter(HebeltraderCoverage),
}

def now():
    return datetime.now(UTC).isoformat()

async def get(client, path, params=None):
    started = now()
    try:
        response = await client.get(path, params=params)
        if response.status_code != 200:
            return {"read_at": started, "http_status": response.status_code,
                    "read_error": "DIAGNOSTIC_READ_UNAVAILABLE"}
        body = response.json()
        if not isinstance(body, dict):
            return {"read_at": started, "http_status": 200,
                    "read_error": "JSON_OBJECT_REQUIRED"}
        return {"read_at": started, "http_status": 200, "body": body}
    except (httpx.HTTPError, ValueError) as error:
        return {"read_at": started, "read_error": type(error).__name__}

def canonical_uuid(value):
    if not isinstance(value, str):
        raise ValueError("UUID_STRING_REQUIRED")
    parsed = UUID(value)
    if parsed.int == 0 or value.lower() != str(parsed):
        raise ValueError("CANONICAL_NONZERO_UUID_REQUIRED")
    return str(parsed)

def valid_time(value):
    if not isinstance(value, str):
        return False
    try:
        return datetime.fromisoformat(value).utcoffset() is not None
    except ValueError:
        return False

def validate_inventory(snapshot):
    if snapshot.get("http_status") != 200 or snapshot.get("read_error"):
        return [], ["INVENTORY_READ_UNAVAILABLE"]
    body = snapshot.get("body", {})
    try:
        INVENTORY_RESPONSE.validate_python(body)
    except (ValidationError, ValueError, TypeError):
        return [], ["INVENTORY_RESPONSE_SCHEMA_INVALID"]
    summary, rows = body.get("summary"), body.get("items")
    if (not isinstance(summary, dict) or not isinstance(rows, list)
            or type(summary.get("open_positions")) is not int
            or summary["open_positions"] < 0
            or summary["open_positions"] != len(rows)
            or not valid_time(body.get("assessed_at"))
            or body.get("assessment_scope") != "STORED_OBSERVATIONS_NOT_LIVE_VALUATION"
            or body.get("execution_usable") is not False):
        return [], ["INVENTORY_SCHEMA_OR_COUNT_INVALID"]
    validated, position_ids, trade_ids = [], set(), set()
    for row in rows:
        if not isinstance(row, dict):
            return [], ["INVENTORY_ITEM_NOT_OBJECT"]
        try:
            clean = dict(row)
            for key in ("position_id", "trade_id", "warrant_id"):
                clean[key] = canonical_uuid(row.get(key))
            for key in ("selection_id", "warrant_listing_id", "mapping_id"):
                if key not in row:
                    raise ValueError("INVENTORY_FIELD_MISSING")
                clean[key] = canonical_uuid(row[key]) if row[key] is not None else None
            for key in ("selected_provider", "selection_status", "mic", "currency"):
                if key not in row or (row[key] is not None and not isinstance(row[key], str)):
                    raise ValueError("INVENTORY_FIELD_INVALID")
            if ("mapping_version" not in row or
                    (row["mapping_version"] is not None and
                     (type(row["mapping_version"]) is not int or row["mapping_version"] < 1))):
                raise ValueError("INVENTORY_MAPPING_VERSION_INVALID")
        except (ValueError, AttributeError, TypeError):
            return [], ["INVENTORY_IDENTITY_SCHEMA_INVALID"]
        if clean["position_id"] in position_ids or clean["trade_id"] in trade_ids:
            return [], ["INVENTORY_DUPLICATE_POSITION_OR_TRADE"]
        position_ids.add(clean["position_id"])
        trade_ids.add(clean["trade_id"])
        validated.append(clean)
    return sorted(validated, key=lambda row: row["position_id"]), []

def bindings(rows):
    keys = ("position_id", "trade_id", "warrant_id", "selection_id",
            "selected_provider", "warrant_listing_id", "mapping_id",
            "mapping_version", "selection_status", "mic", "currency")
    return sorted(tuple(str(row.get(key)) for key in keys) for row in rows)

def marker(snapshot):
    body = snapshot.get("body", {})
    if (snapshot.get("http_status") != 200 or snapshot.get("read_error")
            or type(body.get("cycle_running")) is not bool
            or not valid_time(body.get("last_cycle_started_at"))
            or not valid_time(body.get("last_cycle_completed_at"))):
        return None
    keys = ("last_cycle_started_at", "last_cycle_completed_at", "cycle_running")
    return tuple(body.get(key) for key in keys)

def validate_position_read(snapshot, row, name):
    if snapshot.get("http_status") != 200 or snapshot.get("read_error"):
        return
    body = snapshot.get("body", {})
    try:
        POSITION_RESPONSES[name].validate_python(body)
        if any(canonical_uuid(body.get(key)) != row[key]
               for key in ("trade_id", "position_id")):
            raise ValueError("WRONG_POSITION")
        clocks = ("read_at",) if name in {
            "indicative-entry", "product-deadline-review", "hebeltrader-loss"
        } else ("read_started_at", "read_completed_at")
        if name == "hebeltrader-original-bid":
            clocks += ("evaluated_at",)
        if any(not valid_time(body.get(key)) for key in clocks):
            raise ValueError("INVALID_READ_TIME")
        if name in {"indicative-entry", "product-deadline-review", "hebeltrader-loss"}:
            if "latest_assessment" not in body:
                raise ValueError("MISSING_ASSESSMENT_FIELD")
            assessment = body["latest_assessment"]
            if assessment is not None and (not isinstance(assessment, dict)
                    or not isinstance(assessment.get("reasons"), list)
                    or not all(isinstance(reason, str) for reason in assessment["reasons"])
                    or not valid_time(assessment.get("evaluated_at"))):
                raise ValueError("INVALID_ASSESSMENT")
    except (ValidationError, ValueError, AttributeError, TypeError):
        snapshot["read_error"] = "POSITION_RESPONSE_SCHEMA_OR_IDENTITY_INVALID"

async def main():
    result = {"schema": "PRIVATE_MONITORING_READBACK_2026_11_20",
              "started_at": now(), "requests": "GET_ONLY",
              "global_atomic_snapshot": False}
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000",
                               timeout=15, trust_env=False,
                               follow_redirects=False) as client:
        result["runtime_before"] = await get(client, BASE + "/runtime/status")
        result["refresh_before"] = await get(client, "/api/v1/market-data/refresh/status")
        result["inventory_before"] = await get(client, INVENTORY)
        initial, initial_errors = validate_inventory(result["inventory_before"])
        result["inventory_before_errors"] = initial_errors
        result["positions"] = []
        for number, row in enumerate(initial, 1):
            entry = {"label": f"P{number:02d}", "identity_private": row, "reads": {}}
            for name, prefix in READS:
                read = await get(
                    client, f"{prefix}/trades/{row['trade_id']}/{name}",
                    {"position_id": row["position_id"]})
                validate_position_read(read, row, name)
                entry["reads"][name] = read
            result["positions"].append(entry)
        result["inventory_after"] = await get(client, INVENTORY)
        result["refresh_after"] = await get(client, "/api/v1/market-data/refresh/status")
        result["runtime_after"] = await get(client, BASE + "/runtime/status")
    final, final_errors = validate_inventory(result["inventory_after"])
    result["inventory_after_errors"] = final_errors
    valid_inventory = not initial_errors and not final_errors
    before_marker = marker(result["runtime_before"])
    after_marker = marker(result["runtime_after"])
    result["coverage_checks"] = {
        "inventory_schema_ids_and_counts_valid": valid_inventory,
        "positions_requested": len(initial),
        "nonempty_portfolio_observed": valid_inventory and bool(initial),
        "same_inventory_and_bindings": valid_inventory and bindings(initial) == bindings(final),
        "same_idle_cycle_markers": (
            before_marker is not None and before_marker == after_marker
            and before_marker[2] is False),
        "auxiliary_reads_available": all(
            result[key].get("http_status") == 200 and not result[key].get("read_error")
            for key in ("runtime_before", "refresh_before", "refresh_after", "runtime_after")),
        "all_position_reads_available": valid_inventory and bool(initial) and all(
            read.get("http_status") == 200 and not read.get("read_error")
            for entry in result["positions"] for read in entry["reads"].values()),
    }
    checks = result["coverage_checks"]
    result["collection_status"] = (
        "INVENTORY_UNAVAILABLE_OR_INVALID" if not valid_inventory else
        "NO_OPEN_POSITIONS_NO_COVERAGE_EVIDENCE" if not initial else
        "AUXILIARY_READS_UNAVAILABLE" if not checks["auxiliary_reads_available"] else
        "POSITION_READS_INCOMPLETE" if not checks["all_position_reads_available"] else
        "CHANGED_OR_UNVERIFIED_COLLECTION_WINDOW" if not (
            checks["same_inventory_and_bindings"] and checks["same_idle_cycle_markers"]) else
        "COMPLETE_PASSIVE_READBACK_NOT_RULE_QUALIFICATION")
    result["completed_at"] = now()
    print(json.dumps(result, ensure_ascii=False, indent=2))

asyncio.run(main())
"""

SCHEMA_PAYLOAD = r"""import asyncio
import json
import logging
from datetime import UTC, datetime

logging.disable(logging.CRITICAL)

async def main():
    result = {"source": "INSTALLED_BACKEND_DATABASE_CONFIGURATION",
              "started_at": datetime.now(UTC).isoformat(), "read_only": True}
    engine = None
    try:
        from app.core.config import get_settings
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy.pool import NullPool

        settings = get_settings()
        engine = create_async_engine(
            settings.database_url, echo=False, poolclass=NullPool,
            isolation_level="AUTOCOMMIT",
            connect_args={"timeout": 10, "server_settings": {
                "default_transaction_read_only": "on",
                "statement_timeout": "10000", "lock_timeout": "2000"}},
        )
        async with engine.connect() as connection:
            await connection.execute(text("BEGIN READ ONLY"))
            try:
                await connection.execute(text("SET LOCAL statement_timeout = '10s'"))
                await connection.execute(text("SET LOCAL lock_timeout = '2s'"))
                rows = await connection.execute(
                    text("SELECT version_num FROM alembic_version ORDER BY version_num"))
                result["versions"] = list(rows.scalars().all())
            finally:
                await connection.execute(text("ROLLBACK"))
        result["status"] = "READ_ONLY_SCHEMA_VERSION_OBSERVED"
    except Exception as error:
        result["read_error"] = type(error).__name__
    finally:
        if engine is not None:
            try:
                await engine.dispose()
            except Exception as error:
                result["read_error"] = type(error).__name__
    result["completed_at"] = datetime.now(UTC).isoformat()
    print(json.dumps(result, sort_keys=True))

asyncio.run(main())
"""


SOURCE_GAP_PAYLOAD = r"""import asyncio
import json
import logging
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from uuid import UUID

logging.disable(logging.CRITICAL)

class BoundReadError(Exception):
    pass

def require(condition, code):
    if not condition:
        raise BoundReadError(code)

def instant(value):
    value = datetime.fromisoformat(value) if isinstance(value, str) else value
    require(isinstance(value, datetime) and value.utcoffset() is not None,
            "REFERENCE_TIME_INVALID")
    return value.astimezone(UTC)

def route_matches(actual, expected):
    return (isinstance(actual, dict) and set(actual) == set(expected)
            and all(instant(actual[key]) == instant(expected[key])
                    if key == "selected_at" else str(actual[key]) == str(expected[key])
                    for key in expected))

def source_matches(inputs, reference):
    saved = inputs.get("saved_quote")
    binding = reference["binding"]
    return (isinstance(saved, dict)
            and saved.get("provider") == binding["provider"]
            and route_matches(saved.get("route"), binding["route"])
            and inputs.get("warrant_isin") == binding["isin"])

def assessment_view(row, reference):
    require(isinstance(row.inputs, dict) and isinstance(row.result, dict),
            "STORED_ASSESSMENT_STRUCTURE_INVALID")
    fields = ("saved_quote", "status_observations", "current_refresh_failed")
    return {
        "id": row.id, "workspace_id": row.workspace_id, "trade_id": row.trade_id,
        "position_id": row.position_id, "rule_version": row.rule_version,
        "previous_assessment_id": row.previous_assessment_id,
        "evaluated_at": row.evaluated_at, "recorded_at": row.recorded_at,
        "ordering_at": row.ordering_at, "outcome": row.outcome,
        "owner_basis_id": row.owner_basis_id, "input_fingerprint": row.input_fingerprint,
        "reasons": row.result.get("reasons"),
        "inputs": {key: row.inputs.get(key) for key in fields},
        "stored_input_fields_present": {key: key in row.inputs for key in fields},
        "source_binding_matches_reference": source_matches(row.inputs, reference),
        "scope": "STORED_ASSESSMENT_NOT_REEVALUATION",
    }

async def read_bound_facts(session, reference):
    from app.features.market_data.domain.status_observations import StatusRouteBinding
    from app.features.market_data.persistence.models import PositionQuoteSourceSelectionModel
    from app.features.market_data.service.risk_read import RiskMarketDataReader
    from app.features.market_data.service.status_observations import MarketStatusReader
    from app.features.position_monitoring.persistence.indicative_entry import (
        IndicativeEntryAssessmentModel,
    )
    from app.features.position_monitoring.service.indicative_entry import (
        latest_indicative_assessment,
    )
    from app.features.product.persistence.models import WarrantModel
    from app.features.trade_position.service.open_position_reader import OpenPositionReader

    binding, archived = reference["binding"], reference["assessment"]
    workspace_id, trade_id, position_id, warrant_id = (
        UUID(binding[key]) for key in ("workspace_id", "trade_id", "position_id", "warrant_id")
    )
    read_at = datetime.now(UTC)
    position = await OpenPositionReader(session).read(
        workspace_id=workspace_id, trade_id=trade_id, lock=False)
    require(position is not None, "REFERENCED_POSITION_NOT_OPEN")
    require((position.workspace_id, position.trade_id, position.position_id, position.warrant_id)
            == (workspace_id, trade_id, position_id, warrant_id),
            "CURRENT_POSITION_BINDING_CHANGED")
    warrant = await session.get(WarrantModel, warrant_id)
    require(warrant is not None and warrant.workspace_id == workspace_id
            and warrant.isin == binding["isin"] and warrant.wkn == binding["wkn"]
            and str(warrant.underlying_id) == binding["underlying_id"],
            "CURRENT_PRODUCT_BINDING_CHANGED")
    saved = await RiskMarketDataReader(session).saved_quote(
        workspace_id=workspace_id, position_id=position_id, as_of=read_at,
        expected_warrant_id=warrant_id)
    require(saved.route is not None and route_matches(asdict(saved.route), binding["route"]),
            "CURRENT_QUOTE_ROUTE_CHANGED_OR_UNAVAILABLE")
    selection = await session.get(PositionQuoteSourceSelectionModel, saved.route.selection_id)
    require(selection is not None and selection.workspace_id == workspace_id
            and selection.position_id == position_id and selection.superseded_at is None
            and selection.selection_status == "SELECTED"
            and selection.provider == binding["provider"]
            and selection.identity_key == binding["route"]["identity_key"]
            and str(selection.warrant_listing_id) == binding["route"]["warrant_listing_id"]
            and str(selection.warrant_provider_mapping_id) == binding["mapping_id"]
            and selection.mapping_version == binding["mapping_version"]
            and selection.policy_version == binding["policy_version"]
            and instant(selection.selected_at) == instant(binding["route"]["selected_at"]),
            "CURRENT_SELECTION_BINDING_CHANGED")
    require(saved.provider in (None, selection.provider), "CURRENT_QUOTE_PROVIDER_CHANGED")
    if saved.quote is not None:
        require(saved.provider == selection.provider
                and saved.quote.provider_exchange_code == binding["provider_exchange_code"]
                and saved.quote.provider_symbol == warrant.isin,
                "CURRENT_QUOTE_BINDING_CHANGED")

    historical = await session.get(IndicativeEntryAssessmentModel, UUID(archived["id"]))
    require(historical is not None, "ARCHIVED_ASSESSMENT_NOT_FOUND")
    require((historical.workspace_id, historical.trade_id, historical.position_id)
            == (workspace_id, trade_id, position_id)
            and historical.rule_version == archived["rule_version"]
            and instant(historical.evaluated_at) == instant(archived["evaluated_at"])
            and instant(historical.recorded_at) == instant(archived["recorded_at"])
            and historical.outcome == archived["outcome"]
            and historical.owner_basis_id == archived["owner_basis_id"]
            and isinstance(historical.result, dict)
            and historical.result.get("reasons") == archived["reasons"]
            and isinstance(historical.inputs, dict)
            and source_matches(historical.inputs, reference),
            "ARCHIVED_ASSESSMENT_BINDING_MISMATCH")
    current = await latest_indicative_assessment(session, workspace_id, position_id)
    require(current is not None, "CURRENT_ASSESSMENT_NOT_FOUND")
    require((current.workspace_id, current.trade_id, current.position_id)
            == (workspace_id, trade_id, position_id)
            and current.rule_version in ("indicative-entry-review-v1", "indicative-entry-review-v2")
            and instant(current.recorded_at) <= read_at
            and instant(current.evaluated_at) <= read_at,
            "CURRENT_ASSESSMENT_SCOPE_OR_TIME_INVALID")

    # A missing saved price does not erase the identity-verified selection or journal.
    route = StatusRouteBinding(
        workspace_id, warrant_id, saved.route.warrant_listing_id, selection.provider,
        saved.route.identity_key, warrant.isin, saved.route.venue_mic)
    status = await MarketStatusReader(session).read(
        route=route, event_at=read_at, known_at=read_at)
    require(status.route == route and status.event_at == status.known_at == read_at,
            "STATUS_SNAPSHOT_BINDING_MISMATCH")
    journal_state = ("GAP_PRESENT" if status.latest_gap is not None else
                     "NO_GAP_IN_BOUND_ROUTE" if status.latest_capture is not None else
                     "NO_OBSERVATIONS_IN_BOUND_ROUTE")
    return {
        "read_at": read_at, "binding_status": "ARCHIVED_POSITION_AND_CURRENT_ROUTE_MATCH",
        "saved_quote": asdict(saved), "current_status": asdict(status),
        "status_provider_basis": ("SAVED_QUOTE_AND_SELECTION" if saved.provider is not None
                                  else "IDENTITY_VERIFIED_SELECTION_WITHOUT_SAVED_PRICE"),
        "journal_state": journal_state,
        "archived_assessment": assessment_view(historical, reference),
        "current_assessment": assessment_view(current, reference),
        "same_assessment_head": current.id == historical.id,
    }

async def main():
    result = {"schema": "PRIVATE_DEPOT_SOURCE_GAP_READ_V1",
              "source": "INSTALLED_BACKEND_DATABASE_CONFIGURATION",
              "started_at": datetime.now(UTC).isoformat(), "read_only": True,
              "scope": "ONE_ARCHIVED_POSITION_STORED_FACTS_ONLY"}
    engine = None
    try:
        from app.core.config import get_settings
        from pydantic import TypeAdapter
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.pool import NullPool

        raw = sys.stdin.buffer.read(65537)
        require(len(raw) <= 65536, "REFERENCE_INPUT_TOO_LARGE")
        reference = json.loads(raw)
        require(isinstance(reference, dict)
                and reference.get("schema") == "PRIVATE_DEPOT_SOURCE_GAP_REFERENCE_V1",
                "REFERENCE_INPUT_INVALID")
        result["reference"] = reference
        settings = get_settings()
        engine = create_async_engine(
            settings.database_url, echo=False, poolclass=NullPool,
            isolation_level="AUTOCOMMIT",
            connect_args={"timeout": 10, "server_settings": {
                "default_transaction_read_only": "on", "statement_timeout": "10000",
                "lock_timeout": "2000"}},
        )
        async with engine.connect() as connection:
            try:
                await connection.execute(text("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY"))
                await connection.execute(text("SET LOCAL statement_timeout = '10s'"))
                await connection.execute(text("SET LOCAL lock_timeout = '2s'"))
                properties = (await connection.execute(text(
                    "SELECT current_setting('transaction_read_only'), "
                    "current_setting('transaction_isolation')"))).one()
                require(tuple(properties) == ("on", "repeatable read"),
                        "DATABASE_READ_ONLY_SNAPSHOT_NOT_ESTABLISHED")
                result["transaction"] = {"read_only": properties[0],
                                         "isolation": properties[1]}
                async with AsyncSession(bind=connection, autoflush=False,
                                        expire_on_commit=False) as session:
                    try:
                        result.update(TypeAdapter(object).dump_python(
                            await read_bound_facts(session, reference), mode="json"))
                    finally:
                        await session.rollback()
            finally:
                # AUTOCOMMIT needs an actual SQL rollback, not only Session.rollback().
                await connection.execute(text("ROLLBACK"))
        result["status"] = "COMPLETE_PASSIVE_SOURCE_GAP_READ_NOT_PRICE_QUALIFICATION"
    except Exception as error:
        result["read_error"] = type(error).__name__
        if isinstance(error, BoundReadError):
            result["reason"] = str(error)
    finally:
        if engine is not None:
            try:
                await engine.dispose()
            except Exception as error:
                result["read_error"] = type(error).__name__
    result["completed_at"] = datetime.now(UTC).isoformat()
    print(json.dumps(result, sort_keys=True, allow_nan=False))

asyncio.run(main())
"""


class DiagnosticError(Exception):
    """Only static, credential-free error codes may cross the host boundary."""


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def require(condition: bool, code: str) -> None:
    if not condition:
        raise DiagnosticError(code)


def run_command(args: list[str], *, input_text: str | None = None, timeout: int = 30) -> str:
    """Return stdout without ever exposing commands, stderr or exception messages."""
    environment = dict(os.environ)
    # The explicit local socket is authoritative, not ambient remote contexts/TLS.
    for key in (
        "DOCKER_HOST",
        "DOCKER_CONTEXT",
        "DOCKER_TLS_VERIFY",
        "DOCKER_CERT_PATH",
    ):
        environment.pop(key, None)
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    try:
        completed = subprocess.run(
            args,
            input=input_text,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
            env=environment,
        )
    except subprocess.TimeoutExpired:
        raise DiagnosticError("COMMAND_TIMEOUT") from None
    except OSError:
        raise DiagnosticError("COMMAND_UNAVAILABLE") from None
    require(completed.returncode == 0, "COMMAND_FAILED")
    return completed.stdout


def docker_prefix() -> list[str]:
    configured = os.environ.get("DOCKER_HOST", "")
    if configured:
        require(configured.startswith("unix:///"), "REMOTE_DOCKER_HOST_NOT_ALLOWED")
        socket = configured[len("unix://") :]
        require("\x00" not in socket and "\n" not in socket, "INVALID_LOCAL_DOCKER_SOCKET")
    else:
        rootless = Path(f"/run/user/{os.getuid()}/docker.sock")
        socket = str(rootless) if rootless.exists() else "/var/run/docker.sock"
    return ["docker", "--host", "unix://" + socket]


def checked_path(path: Path, *, directory: bool = False, private: bool = False) -> Path:
    try:
        info = path.lstat()
        valid_kind = stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)
        require(valid_kind and path.resolve(strict=True) == path, "UNSAFE_INSTALLATION_PATH")
        if private:
            require(
                info.st_uid == os.getuid() and info.st_mode & 0o077 == 0,
                "PRIVATE_STATE_PERMISSIONS_INVALID",
            )
    except OSError:
        raise DiagnosticError("INSTALLATION_PATH_UNAVAILABLE") from None
    return path


def read_line(path: Path, *, private: bool = True) -> str:
    checked_path(path, private=private)
    try:
        with path.open("rb") as stream:
            data = stream.read(4097)
        require(len(data) <= 4096, "STATE_FILE_TOO_LARGE")
        value = data.decode("utf-8").rstrip("\n")
        require(
            bool(value) and not any(c in value for c in "\n\r\x00"),
            "STATE_FILE_INVALID",
        )
        return value
    except (OSError, UnicodeError):
        raise DiagnosticError("STATE_FILE_UNREADABLE") from None


def require_no_pending(base: Path) -> None:
    control = base / "trading-workspace-state"
    require(
        not os.path.lexists(control / "pending")
        and not os.path.lexists(control / "current-state.new"),
        "MANAGED_OPERATION_PENDING",
    )


def parse_json(raw: str) -> dict:
    try:
        value = json.loads(raw)
    except (ValueError, TypeError):
        raise DiagnosticError("INVALID_JSON_RESPONSE") from None
    require(isinstance(value, dict), "JSON_OBJECT_REQUIRED")
    return value


def valid_time(value: object) -> bool:
    if not isinstance(value, str):
        return False
    # Python 3.10 accepts neither Z nor Docker's arbitrary fractional precision.
    # Normalize only this validation input; artifacts retain the original string.
    normalized = value.removesuffix("Z") + "+00:00" if value.endswith("Z") else value
    normalized = re.sub(
        r"(\d{2}:\d{2}:\d{2})\.(\d+)(?=[+-]\d{2}:\d{2}$)",
        lambda match: match[1] + "." + match[2][:6].ljust(6, "0"),
        normalized,
    )
    try:
        return datetime.fromisoformat(normalized).utcoffset() is not None
    except ValueError:
        return False


def read_installation(base: Path) -> dict:
    """Read only small state files and explicitly selected Docker metadata."""
    app, control = base / "trading-workspace-app", base / "trading-workspace-state"
    checked_path(base, directory=True)
    checked_path(app, directory=True)
    checked_path(control, directory=True, private=True)
    require_no_pending(base)
    pointer = read_line(control / "current-state")
    state = Path(pointer)
    require(
        state.is_absolute()
        and state.parent.parent == control / "runs"
        and state.name == "deployment",
        "CURRENT_STATE_BINDING_INVALID",
    )
    checked_path(state.parent, directory=True, private=True)
    checked_path(state, directory=True, private=True)
    for marker in ("prepared", "deployed"):
        checked_path(state / marker, private=True)
    revision = read_line(state / "revision")
    require(re.fullmatch(r"[0-9a-f]{40}", revision) is not None, "STATE_REVISION_INVALID")
    require(read_line(state / "release-root") == str(app), "RELEASE_ROOT_MISMATCH")
    git = ["git", "--no-optional-locks", "-c", "core.fsmonitor=false", "-C", str(app)]
    head = run_command([*git, "rev-parse", "--verify", "HEAD"]).strip()
    require(head == revision, "CHECKOUT_REVISION_MISMATCH")
    require(
        not run_command([*git, "status", "--porcelain=v1", "--untracked-files=all"]).strip(),
        "CHECKOUT_NOT_CLEAN",
    )
    version = read_line(app / "VERSION", private=False)
    require(re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version) is not None, "VERSION_INVALID")
    require(
        run_command([*git, "show", "HEAD:VERSION"]).strip() == version,
        "CHECKOUT_VERSION_MISMATCH",
    )
    docker = docker_prefix()
    ids = run_command(
        [
            *docker,
            "ps",
            "--all",
            "--no-trunc",
            "--quiet",
            "--filter",
            "label=com.docker.compose.project=trading-workspace",
        ]
    ).split()
    require(
        len(ids) == 4
        and len(set(ids)) == 4
        and all(re.fullmatch(r"[0-9a-f]{64}", cid) for cid in ids),
        "PROJECT_CONTAINER_INVENTORY_INVALID",
    )
    # Deliberately never request .Config.Env, full labels, mounts or health logs.
    template = (
        '{"id":{{json .Id}},"name":{{json .Name}},"image_id":{{json .Image}},'
        '"project":{{json (index .Config.Labels "com.docker.compose.project")}},'
        '"service":{{json (index .Config.Labels "com.docker.compose.service")}},'
        '"config_files":{{json (index .Config.Labels "com.docker.compose.project.config_files")}},'
        '"state":{{json .State.Status}},"started_at":{{json .State.StartedAt}},'
        '"restart_count":{{json .RestartCount}},'
        '"health":{{if .State.Health}}{{json .State.Health.Status}}{{else}}null{{end}}}'
    )
    containers = {}
    chain = (
        f"{app}/docker/compose.yml,{app}/docker/compose.issuer-monitoring.yml,"
        f"{state}/preserve.json"
    )
    for cid in sorted(ids):
        item = parse_json(
            run_command([*docker, "inspect", "--type", "container", "--format", template, cid])
        )
        service = item.get("service")
        require(
            service in SERVICES and service not in containers,
            "FOREIGN_OR_DUPLICATE_CONTAINER",
        )
        require(
            item.get("id") == cid
            and item.get("project") == "trading-workspace"
            and item.get("name") == f"/trading-workspace-{service}-1",
            "CONTAINER_IDENTITY_MISMATCH",
        )
        require(
            item.get("state")
            in {
                "created",
                "running",
                "paused",
                "restarting",
                "removing",
                "exited",
                "dead",
            }
            and item.get("health") in {None, "starting", "healthy", "unhealthy"}
            and valid_time(item.get("started_at"))
            and type(item.get("restart_count")) is int
            and item["restart_count"] >= 0,
            "CONTAINER_STATE_SCHEMA_INVALID",
        )
        image_id = item.get("image_id")
        require(
            isinstance(image_id, str) and re.fullmatch(r"sha256:[0-9a-f]{64}", image_id),
            "IMAGE_ID_INVALID",
        )
        if service == "database":
            require(
                read_line(state / "database-container") == cid,
                "DATABASE_CONTAINER_MISMATCH",
            )
        else:
            require(item.get("config_files") == chain, "COMPOSE_CHAIN_MISMATCH")
            require(
                read_line(state / (service + ".image")) == image_id,
                "STORED_IMAGE_MISMATCH",
            )
            image = parse_json(
                run_command(
                    [
                        *docker,
                        "image",
                        "inspect",
                        "--format",
                        '{"id":{{json .Id}},"revision":{{json (index .Config.Labels '
                        '"org.opencontainers.image.revision")}}}',
                        image_id,
                    ]
                )
            )
            require(
                image.get("id") == image_id and image.get("revision") == revision,
                "IMAGE_REVISION_MISMATCH",
            )
            item["image_revision"] = image["revision"]
        item.pop("config_files", None)
        containers[service] = item
    require(set(containers) == set(SERVICES), "PROJECT_SERVICES_INCOMPLETE")
    require_no_pending(base)
    require(
        read_line(control / "current-state") == pointer,
        "INSTALLATION_CHANGED_DURING_READ",
    )
    return {
        "status": "VERIFIED_INSTALLATION_BINDING",
        "commit": head,
        "version": version,
        "current_state": str(state.relative_to(control)),
        "containers": containers,
        "scope": "REVISION_IMAGE_CONTAINER_BINDING_NOT_FULL_CONFIGURATION_AUDIT",
    }


def collect_schema(backend_id: str) -> dict:
    require(re.fullmatch(r"[0-9a-f]{64}", backend_id) is not None, "INVALID_BACKEND_ID")
    value = parse_json(
        run_command(
            [*docker_prefix(), "exec", "-i", backend_id, "python", "-B", "-"],
            input_text=SCHEMA_PAYLOAD,
            timeout=60,
        )
    )
    versions = value.get("versions")
    valid = (
        value.get("source") == "INSTALLED_BACKEND_DATABASE_CONFIGURATION"
        and value.get("read_only") is True
        and not value.get("read_error")
        and value.get("status") == "READ_ONLY_SCHEMA_VERSION_OBSERVED"
        and valid_time(value.get("started_at"))
        and valid_time(value.get("completed_at"))
        and isinstance(versions, list)
        and bool(versions)
        and all(isinstance(v, str) and re.fullmatch(r"[A-Za-z0-9_]{1,64}", v) for v in versions)
        and len(set(versions)) == len(versions)
    )
    # Do not pass arbitrary schema-process output or error strings into artifacts.
    if not valid:
        code = value.get("read_error")
        return {
            "read_error": (
                code
                if isinstance(code, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,79}", code)
                else "SCHEMA_READ_INVALID_OR_UNAVAILABLE"
            )
        }
    return {
        "source": value["source"],
        "read_only": True,
        "status": value["status"],
        "started_at": value["started_at"],
        "completed_at": value["completed_at"],
        "versions": versions,
        "reference_versions": REFERENCE_SCHEMA_REVISIONS,
        "matches_reviewed_reference": sorted(versions) == REFERENCE_SCHEMA_REVISIONS,
    }


def collect_monitoring(backend_id: str) -> dict:
    require(re.fullmatch(r"[0-9a-f]{64}", backend_id) is not None, "INVALID_BACKEND_ID")
    return parse_json(
        run_command(
            [*docker_prefix(), "exec", "-i", backend_id, "python", "-B", "-"],
            input_text=BACKEND_PAYLOAD,
            timeout=900,
        )
    )


def monitoring_complete(value: dict) -> bool:
    checks = value.get("coverage_checks", {})
    positions = value.get("positions")
    if not (
        value.get("schema") == "PRIVATE_MONITORING_READBACK_2026_11_20"
        and value.get("requests") == "GET_ONLY"
        and value.get("global_atomic_snapshot") is False
        and value.get("collection_status") == COMPLETE_READBACK
        and valid_time(value.get("started_at"))
        and valid_time(value.get("completed_at"))
        and isinstance(checks, dict)
        and isinstance(positions, list)
        and bool(positions)
        and type(checks.get("positions_requested")) is int
        and checks["positions_requested"] == len(positions)
    ):
        return False
    for key in (
        "inventory_schema_ids_and_counts_valid",
        "nonempty_portfolio_observed",
        "same_inventory_and_bindings",
        "same_idle_cycle_markers",
        "auxiliary_reads_available",
        "all_position_reads_available",
    ):
        if checks.get(key) is not True:
            return False
    for key in (
        "runtime_before",
        "refresh_before",
        "inventory_before",
        "inventory_after",
        "refresh_after",
        "runtime_after",
    ):
        item = value.get(key)
        if not (
            isinstance(item, dict)
            and item.get("http_status") == 200
            and not item.get("read_error")
            and isinstance(item.get("body"), dict)
        ):
            return False
    for position in positions:
        if not isinstance(position, dict) or not isinstance(position.get("reads"), dict):
            return False
        if set(position["reads"]) != set(READ_NAMES):
            return False
        for read in position["reads"].values():
            if not (
                isinstance(read, dict)
                and read.get("http_status") == 200
                and not read.get("read_error")
                and isinstance(read.get("body"), dict)
            ):
                return False
    return True


def write_json(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8") as stream:
        os.chmod(path, 0o600)
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def safe_error(error: BaseException) -> dict:
    return {
        "read_error": (str(error) if isinstance(error, DiagnosticError) else type(error).__name__)
    }


def canonical_uuid(value: object) -> str:
    require(isinstance(value, str), "REFERENCE_UUID_INVALID")
    try:
        parsed = UUID(value)
    except ValueError:
        raise DiagnosticError("REFERENCE_UUID_INVALID") from None
    require(parsed.int != 0 and str(parsed) == value, "REFERENCE_UUID_INVALID")
    return value


def reference_json(raw: bytes) -> dict:
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "REFERENCE_DUPLICATE_JSON_KEY")
            result[key] = value
        return result

    def invalid_constant(_value):
        raise DiagnosticError("REFERENCE_NONFINITE_JSON_NUMBER")

    try:
        value = json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid_constant)
    except (ValueError, UnicodeError, RecursionError):
        raise DiagnosticError("REFERENCE_JSON_INVALID") from None
    require(isinstance(value, dict), "REFERENCE_JSON_OBJECT_REQUIRED")
    return value


def read_reference_archive(path: Path) -> tuple[dict, str, str]:
    """Read a bounded original collector package in memory; never extract files."""
    path = path.expanduser().absolute()
    checked_path(path)
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(descriptor, "rb") as stream:
            info = os.fstat(stream.fileno())
            require(stat.S_ISREG(info.st_mode), "REFERENCE_ARCHIVE_NOT_REGULAR")
            require(
                info.st_size <= MAX_REFERENCE_ARCHIVE_BYTES,
                "REFERENCE_ARCHIVE_TOO_LARGE",
            )
            compressed = stream.read(MAX_REFERENCE_ARCHIVE_BYTES + 1)
        require(
            len(compressed) <= MAX_REFERENCE_ARCHIVE_BYTES,
            "REFERENCE_ARCHIVE_TOO_LARGE",
        )
        with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as stream:
            raw_tar = stream.read(MAX_REFERENCE_TAR_BYTES + 1)
        require(len(raw_tar) <= MAX_REFERENCE_TAR_BYTES, "REFERENCE_TAR_TOO_LARGE")
        documents, root_name, total, monitoring_hash = {}, None, 0, None
        with tarfile.open(fileobj=io.BytesIO(raw_tar), mode="r:") as archive:
            for member in archive:
                require(len(documents) < 5, "REFERENCE_MEMBER_COUNT_INVALID")
                parts = member.name.split("/")
                require(
                    len(parts) == 2
                    and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", parts[0]) is not None
                    and parts[1] in REFERENCE_FILES
                    and member.isreg()
                    and not member.issparse(),
                    "REFERENCE_MEMBER_INVALID",
                )
                require(root_name in (None, parts[0]), "REFERENCE_MEMBER_ROOT_MISMATCH")
                root_name = parts[0]
                name = parts[1]
                require(name not in documents, "REFERENCE_DUPLICATE_MEMBER")
                require(
                    0 < member.size <= MAX_REFERENCE_JSON_BYTES,
                    "REFERENCE_MEMBER_TOO_LARGE",
                )
                total += member.size
                require(total <= MAX_REFERENCE_TOTAL_BYTES, "REFERENCE_TOTAL_TOO_LARGE")
                stream = archive.extractfile(member)
                require(stream is not None, "REFERENCE_MEMBER_UNREADABLE")
                with stream:
                    raw = stream.read(MAX_REFERENCE_JSON_BYTES + 1)
                require(len(raw) == member.size, "REFERENCE_MEMBER_SIZE_MISMATCH")
                documents[name] = reference_json(raw)
                if name == "monitoring-private.json":
                    monitoring_hash = hashlib.sha256(raw).hexdigest()
        require(set(documents) == REFERENCE_FILES, "REFERENCE_MEMBERS_INCOMPLETE")
    except (OSError, EOFError, tarfile.TarError):
        raise DiagnosticError("REFERENCE_ARCHIVE_UNREADABLE") from None
    return documents, hashlib.sha256(compressed).hexdigest(), monitoring_hash


def reference_inventory(snapshot: dict) -> dict:
    require(isinstance(snapshot, dict), "REFERENCE_INVENTORY_INVALID")
    body = snapshot.get("body")
    require(
        snapshot.get("http_status") == 200
        and not snapshot.get("read_error")
        and isinstance(body, dict)
        and isinstance(body.get("items"), list)
        and isinstance(body.get("summary"), dict)
        and type(body["summary"].get("open_positions")) is int
        and body["summary"]["open_positions"] == len(body["items"])
        and 0 < len(body["items"]) <= 1000
        and valid_time(body.get("assessed_at"))
        and body.get("assessment_scope") == "STORED_OBSERVATIONS_NOT_LIVE_VALUATION"
        and body.get("execution_usable") is False,
        "REFERENCE_INVENTORY_INVALID",
    )
    rows, trade_ids = {}, set()
    for row in body["items"]:
        require(isinstance(row, dict), "REFERENCE_INVENTORY_ITEM_INVALID")
        for key in ("position_id", "trade_id", "warrant_id"):
            canonical_uuid(row.get(key))
        for key in ("selection_id", "warrant_listing_id", "mapping_id"):
            require(key in row, "REFERENCE_INVENTORY_BINDING_MISSING")
            if row[key] is not None:
                canonical_uuid(row[key])
        require(
            row["position_id"] not in rows and row["trade_id"] not in trade_ids,
            "REFERENCE_INVENTORY_DUPLICATE_ID",
        )
        rows[row["position_id"]] = row
        trade_ids.add(row["trade_id"])
    return rows


def read_source_gap_reference(path: Path, label: str) -> dict:
    require(
        isinstance(label, str) and re.fullmatch(r"P[0-9]{2,4}", label) is not None,
        "REFERENCE_POSITION_LABEL_INVALID",
    )
    documents, archive_hash, monitoring_hash = read_reference_archive(path)
    summary, monitoring = (
        documents["summary.json"],
        documents["monitoring-private.json"],
    )
    require(
        summary.get("schema") == "PRIVATE_DEPOT_DATA_SUPPLY_DIAGNOSTIC_2026_11_21"
        and summary.get("transport_complete") is True
        and summary.get("read_only") is True
        and summary.get("backend_payload_sha256")
        == hashlib.sha256(BACKEND_PAYLOAD.encode()).hexdigest()
        and monitoring_complete(monitoring),
        "REFERENCE_COMPLETE_COLLECTOR_READ_REQUIRED",
    )
    installation = documents["installation-before.json"]
    require(
        installation == documents["installation-after.json"]
        and installation.get("status") == "VERIFIED_INSTALLATION_BINDING"
        and isinstance(installation.get("commit"), str)
        and re.fullmatch(r"[0-9a-f]{40}", installation["commit"]) is not None
        and isinstance(installation.get("version"), str)
        and re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", installation["version"]) is not None,
        "REFERENCE_INSTALLATION_INVALID",
    )
    schema = documents["schema.json"]
    require(
        schema.get("status") == "READ_ONLY_SCHEMA_VERSION_OBSERVED"
        and schema.get("read_only") is True
        and not schema.get("read_error")
        and isinstance(schema.get("versions"), list)
        and bool(schema["versions"])
        and all(
            isinstance(v, str) and re.fullmatch(r"[A-Za-z0-9_]{1,64}", v)
            for v in schema["versions"]
        ),
        "REFERENCE_SCHEMA_READ_INVALID",
    )
    before = reference_inventory(monitoring["inventory_before"])
    after = reference_inventory(monitoring["inventory_after"])
    keys = (
        "position_id",
        "trade_id",
        "warrant_id",
        "isin",
        "wkn",
        "selection_id",
        "selection_status",
        "selected_provider",
        "warrant_listing_id",
        "mapping_id",
        "mapping_version",
        "provider_exchange_code",
        "mic",
        "currency",
        "policy_version",
        "selected_at",
        "identity_valid",
        "source_verified",
    )
    require(set(before) == set(after), "REFERENCE_INVENTORY_CHANGED")
    require(
        all(
            {k: row.get(k) for k in keys} == {k: after[pid].get(k) for k in keys}
            for pid, row in before.items()
        ),
        "REFERENCE_BINDING_CHANGED",
    )
    labels = {pid: f"P{number:02d}" for number, pid in enumerate(sorted(before), 1)}
    found, seen = None, set()
    require(len(monitoring["positions"]) == len(before), "REFERENCE_POSITION_COUNT_INVALID")
    for entry in monitoring["positions"]:
        row = entry.get("identity_private")
        require(isinstance(row, dict), "REFERENCE_POSITION_IDENTITY_INVALID")
        pid = canonical_uuid(row.get("position_id"))
        require(
            pid in before and pid not in seen and entry.get("label") == labels[pid],
            "REFERENCE_POSITION_LABEL_OR_ID_MISMATCH",
        )
        require(
            all(row.get(k) == before[pid].get(k) for k in keys),
            "REFERENCE_POSITION_INVENTORY_MISMATCH",
        )
        seen.add(pid)
        if entry["label"] == label:
            require(found is None, "REFERENCE_DUPLICATE_LABEL")
            found = entry
    require(found is not None, "REFERENCE_POSITION_LABEL_NOT_FOUND")
    row = found["identity_private"]
    require(
        row.get("selection_status") == "SELECTED"
        and row.get("identity_valid") is True
        and row.get("source_verified") is True,
        "REFERENCE_VERIFIED_SOURCE_REQUIRED",
    )
    for key in ("selection_id", "warrant_listing_id", "mapping_id"):
        canonical_uuid(row.get(key))
    for key, pattern in (
        ("isin", r"[A-Z]{2}[A-Z0-9]{9}[0-9]"),
        ("currency", r"[A-Z]{3}"),
        ("mic", r"[A-Z0-9]{4}"),
        ("selected_provider", r"[A-Z][A-Z0-9_]{0,63}"),
        ("provider_exchange_code", r"[A-Z0-9_-]{1,32}"),
        ("policy_version", r"[A-Za-z0-9_.:-]{1,128}"),
    ):
        require(
            isinstance(row.get(key), str) and re.fullmatch(pattern, row[key]) is not None,
            "REFERENCE_SOURCE_FIELD_INVALID",
        )
    require(
        row.get("wkn") is None
        or (isinstance(row["wkn"], str) and re.fullmatch(r"[A-Z0-9]{6}", row["wkn"]) is not None),
        "REFERENCE_WKN_INVALID",
    )
    require(
        type(row.get("mapping_version")) is int and row["mapping_version"] > 0,
        "REFERENCE_MAPPING_VERSION_INVALID",
    )
    indicative = found["reads"]["indicative-entry"]["body"]
    original = found["reads"]["hebeltrader-original-bid"]["body"]
    for body in (indicative, original):
        require(
            all(body.get(k) == row[k] for k in ("trade_id", "position_id")),
            "REFERENCE_READER_SCOPE_MISMATCH",
        )
    require(original.get("product_id") == row["warrant_id"], "REFERENCE_PRODUCT_MISMATCH")
    underlying_id = canonical_uuid(original.get("underlying_id"))
    saved = original.get("saved_quote")
    require(
        isinstance(saved, dict) and isinstance(saved.get("route"), dict),
        "REFERENCE_SAVED_ROUTE_REQUIRED",
    )
    route = saved["route"]
    uuid_keys = (
        "workspace_id",
        "position_id",
        "warrant_id",
        "warrant_listing_id",
        "trading_venue_id",
        "selection_id",
    )
    require(
        set(route) == {*uuid_keys, "venue_mic", "currency", "identity_key", "selected_at"},
        "REFERENCE_ROUTE_SCHEMA_INVALID",
    )
    for key in uuid_keys:
        canonical_uuid(route.get(key))
    require(
        valid_time(route.get("selected_at"))
        and route["selected_at"] == row.get("selected_at")
        and isinstance(route.get("identity_key"), str)
        and re.fullmatch(r"[0-9a-f]{64}", route["identity_key"]) is not None
        and saved.get("identity_key") == route["identity_key"]
        and saved.get("provider") == row["selected_provider"]
        and route["venue_mic"] == row["mic"]
        and route["currency"] == row["currency"]
        and all(
            route[k] == row[k]
            for k in ("position_id", "warrant_id", "warrant_listing_id", "selection_id")
        ),
        "REFERENCE_ROUTE_BINDING_MISMATCH",
    )
    assessment = indicative.get("latest_assessment")
    require(isinstance(assessment, dict), "REFERENCE_ASSESSMENT_REQUIRED")
    canonical_uuid(assessment.get("id"))
    require(
        assessment.get("rule_version")
        in ("indicative-entry-review-v1", "indicative-entry-review-v2")
        and valid_time(assessment.get("evaluated_at"))
        and valid_time(assessment.get("recorded_at"))
        and assessment.get("outcome")
        in {"UNAVAILABLE", "BELOW_ENTRY", "AT_OR_ABOVE_ENTRY", "NOT_REACHED", "CLOSED"}
        and isinstance(assessment.get("owner_basis_id"), str)
        and re.fullmatch(r"[0-9a-f]{64}", assessment["owner_basis_id"]) is not None
        and isinstance(assessment.get("reasons"), list)
        and all(
            isinstance(r, str) and re.fullmatch(r"[A-Z0-9_]{1,100}", r)
            for r in assessment["reasons"]
        ),
        "REFERENCE_ASSESSMENT_INVALID",
    )
    source = assessment.get("source")
    require(
        isinstance(source, dict)
        and source.get("provider") == saved["provider"]
        and source.get("listing_id") == route["warrant_listing_id"]
        and source.get("identity_key") == route["identity_key"]
        and source.get("venue_mic") == route["venue_mic"],
        "REFERENCE_ASSESSMENT_SOURCE_MISMATCH",
    )
    return {
        "schema": "PRIVATE_DEPOT_SOURCE_GAP_REFERENCE_V1",
        "position_label": label,
        "archive_sha256": archive_hash,
        "monitoring_sha256": monitoring_hash,
        "archived_read_at": monitoring["completed_at"],
        "installation": {k: installation[k] for k in ("commit", "version")},
        "schema_versions": schema["versions"],
        "binding": {
            "workspace_id": route["workspace_id"],
            "trade_id": row["trade_id"],
            "position_id": row["position_id"],
            "warrant_id": row["warrant_id"],
            "underlying_id": underlying_id,
            "isin": row["isin"],
            "wkn": row["wkn"],
            "provider": saved["provider"],
            "provider_exchange_code": row["provider_exchange_code"],
            "mapping_id": row["mapping_id"],
            "mapping_version": row["mapping_version"],
            "policy_version": row["policy_version"],
            "route": route,
        },
        "assessment": {
            k: assessment[k]
            for k in (
                "id",
                "rule_version",
                "evaluated_at",
                "recorded_at",
                "outcome",
                "owner_basis_id",
                "reasons",
            )
        },
    }


def source_gap_complete(value: dict, reference: dict) -> bool:
    """Check transport/binding evidence, never interpret a gap as price recovery."""
    if not (
        value.get("schema") == "PRIVATE_DEPOT_SOURCE_GAP_READ_V1"
        and value.get("source") == "INSTALLED_BACKEND_DATABASE_CONFIGURATION"
        and value.get("scope") == "ONE_ARCHIVED_POSITION_STORED_FACTS_ONLY"
        and value.get("status") == SOURCE_GAP_COMPLETE
        and value.get("read_only") is True
        and not value.get("read_error")
        and value.get("reference") == reference
        and value.get("transaction") == {"read_only": "on", "isolation": "repeatable read"}
        and value.get("binding_status") == "ARCHIVED_POSITION_AND_CURRENT_ROUTE_MATCH"
        and all(valid_time(value.get(k)) for k in ("started_at", "completed_at", "read_at"))
    ):
        return False
    binding = reference["binding"]
    status_route = {
        "workspace_id": binding["workspace_id"],
        "warrant_id": binding["warrant_id"],
        "warrant_listing_id": binding["route"]["warrant_listing_id"],
        "provider": binding["provider"],
        "identity_key": binding["route"]["identity_key"],
        "isin": binding["isin"],
        "venue_mic": binding["route"]["venue_mic"],
    }
    status, saved = value.get("current_status"), value.get("saved_quote")
    if not (
        isinstance(status, dict)
        and status.get("route") == status_route
        and valid_time(status.get("event_at"))
        and valid_time(status.get("known_at"))
        and status["event_at"] == status["known_at"] == value["read_at"]
        and "latest_gap" in status
        and "latest_capture" in status
        and isinstance(status.get("latest_observations"), list)
        and isinstance(status.get("point_observations"), list)
        and isinstance(saved, dict)
        and isinstance(saved.get("route"), dict)
        and isinstance(saved.get("reason"), str)
        and saved.get("provider") in (None, binding["provider"])
        and value.get("status_provider_basis")
        in {
            "SAVED_QUOTE_AND_SELECTION",
            "IDENTITY_VERIFIED_SELECTION_WITHOUT_SAVED_PRICE",
        }
    ):
        return False
    for key, expected in binding["route"].items():
        actual = saved["route"].get(key)
        if key == "selected_at":
            if not (
                valid_time(actual)
                and actual.replace("Z", "+00:00") == expected.replace("Z", "+00:00")
            ):
                return False
        elif actual != expected:
            return False
    gap, capture = status["latest_gap"], status["latest_capture"]
    for observation in (gap, capture):
        if observation is not None and not (
            isinstance(observation, dict)
            and observation.get("route") == status_route
            and valid_time(observation.get("captured_at"))
            and (observation.get("retrieved_at") is None or valid_time(observation["retrieved_at"]))
        ):
            return False
    expected_state = (
        "GAP_PRESENT"
        if gap is not None
        else ("NO_GAP_IN_BOUND_ROUTE" if capture is not None else "NO_OBSERVATIONS_IN_BOUND_ROUTE")
    )
    if value.get("journal_state") != expected_state:
        return False
    if gap is not None and not (
        gap.get("original") is None and isinstance(gap.get("reason"), str) and gap["reason"]
    ):
        return False
    if capture is None and (
        gap is not None or status["latest_observations"] or status["point_observations"]
    ):
        return False
    for key in ("archived_assessment", "current_assessment"):
        assessment = value.get(key)
        if not (
            isinstance(assessment, dict)
            and all(
                assessment.get(k) == binding[k] for k in ("workspace_id", "trade_id", "position_id")
            )
            and assessment.get("scope") == "STORED_ASSESSMENT_NOT_REEVALUATION"
            and all(valid_time(assessment.get(k)) for k in ("evaluated_at", "recorded_at"))
            and isinstance(assessment.get("inputs"), dict)
            and set(assessment["inputs"])
            == {"saved_quote", "status_observations", "current_refresh_failed"}
            and isinstance(assessment.get("stored_input_fields_present"), dict)
            and type(assessment.get("source_binding_matches_reference")) is bool
        ):
            return False
        try:
            canonical_uuid(assessment.get("id"))
        except DiagnosticError:
            return False
    archived = value["archived_assessment"]
    for key, expected in reference["assessment"].items():
        actual = archived.get(key)
        if key in ("evaluated_at", "recorded_at"):
            if actual.replace("Z", "+00:00") != expected.replace("Z", "+00:00"):
                return False
        elif actual != expected:
            return False
    return archived["source_binding_matches_reference"] is True and value.get(
        "same_assessment_head"
    ) is (archived["id"] == value["current_assessment"]["id"])


def collect_source_gap_read(backend_id: str, reference: dict) -> dict:
    require(re.fullmatch(r"[0-9a-f]{64}", backend_id) is not None, "INVALID_BACKEND_ID")
    request = json.dumps(reference, sort_keys=True, separators=(",", ":"), allow_nan=False)
    require(len(request.encode()) <= 65536, "REFERENCE_INPUT_TOO_LARGE")
    value = parse_json(
        run_command(
            [
                *docker_prefix(),
                "exec",
                "-i",
                backend_id,
                "python",
                "-B",
                "-c",
                SOURCE_GAP_PAYLOAD,
            ],
            input_text=request,
            timeout=120,
        )
    )
    if value.get("read_error"):
        if (
            value.get("schema") == "PRIVATE_DEPOT_SOURCE_GAP_READ_V1"
            and isinstance(value["read_error"], str)
            and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,79}", value["read_error"])
            and (
                "reason" not in value
                or (
                    isinstance(value["reason"], str)
                    and re.fullmatch(r"[A-Z0-9_]{1,100}", value["reason"])
                )
            )
        ):
            return value
        return {"read_error": "SOURCE_GAP_READ_UNAVAILABLE"}
    require(source_gap_complete(value, reference), "SOURCE_GAP_RESPONSE_INVALID")
    return value


def collect_source_gap(base: Path, output_dir: Path, archive: Path, label: str) -> dict:
    summary = {
        "schema": "PRIVATE_DEPOT_SOURCE_GAP_DIAGNOSTIC_V1",
        "started_at": now(),
        "read_only": True,
        "global_atomic_snapshot": False,
        "source_gap_payload_sha256": hashlib.sha256(SOURCE_GAP_PAYLOAD.encode()).hexdigest(),
    }
    reference, before, after, schema, gap = {}, {}, {}, {}, {}
    try:
        reference = read_source_gap_reference(archive, label)
        summary["reference_archive_sha256"] = reference["archive_sha256"]
        summary["reference_software"] = reference["installation"]
    except Exception as error:
        gap = safe_error(error)
    if reference:
        try:
            before = read_installation(base)
        except Exception as error:
            before = safe_error(error)
        if not before.get("read_error"):
            try:
                require(
                    before["containers"]["backend"].get("state") == "running",
                    "EXISTING_BACKEND_NOT_RUNNING",
                )
                require_no_pending(base)
                backend_id = before["containers"]["backend"]["id"]
                schema = collect_schema(backend_id)
                require(
                    schema.get("status") == "READ_ONLY_SCHEMA_VERSION_OBSERVED"
                    and not schema.get("read_error"),
                    "SCHEMA_READ_REQUIRED",
                )
                require_no_pending(base)
                gap = collect_source_gap_read(backend_id, reference)
            except Exception as error:
                gap = safe_error(error)
            try:
                after = read_installation(base)
            except Exception as error:
                after = safe_error(error)
        else:
            gap = {"read_error": "INSTALLATION_NOT_VERIFIED_NO_SOURCE_READ"}
    else:
        before = {"read_error": "REFERENCE_NOT_VERIFIED_NO_INSTALLATION_READ"}
    schema = schema or {"read_error": "NO_SCHEMA_READ"}
    after = after or {"read_error": "NO_INSTALLATION_AFTER_READ"}
    gap = gap or {"read_error": "NO_SOURCE_GAP_READ"}
    for name, value in (
        ("installation-before.json", before),
        ("installation-after.json", after),
        ("schema.json", schema),
        ("source-gap-private.json", gap),
    ):
        write_json(output_dir / name, value)
    summary["reference_archive_verified"] = bool(reference)
    summary["installation_unchanged_and_verified"] = (
        before.get("status") == "VERIFIED_INSTALLATION_BINDING"
        and not before.get("read_error")
        and not after.get("read_error")
        and before == after
    )
    # A regular restart/update since the reference is metadata, not a silent route substitution.
    summary["same_software_as_reference"] = (
        {k: before.get(k) for k in ("commit", "version")} == reference["installation"]
        if reference and not before.get("read_error")
        else None
    )
    summary["schema_read_available"] = schema.get(
        "status"
    ) == "READ_ONLY_SCHEMA_VERSION_OBSERVED" and not schema.get("read_error")
    summary["source_gap_transport_complete"] = bool(reference) and source_gap_complete(
        gap, reference
    )
    summary["transport_complete"] = all(
        summary[k]
        for k in (
            "reference_archive_verified",
            "installation_unchanged_and_verified",
            "schema_read_available",
            "source_gap_transport_complete",
        )
    )
    summary["status"] = (
        SOURCE_GAP_COMPLETE
        if summary["transport_complete"]
        else "INCOMPLETE_PASSIVE_SOURCE_GAP_DIAGNOSTIC"
    )
    summary["completed_at"] = now()
    return summary


def collect(base: Path, output_dir: Path) -> dict:
    summary = {
        "schema": "PRIVATE_DEPOT_DATA_SUPPLY_DIAGNOSTIC_2026_11_21",
        "started_at": now(),
        "read_only": True,
        "global_atomic_snapshot": False,
        "backend_payload_sha256": hashlib.sha256(BACKEND_PAYLOAD.encode()).hexdigest(),
    }
    before, after, schema, monitoring = {}, {}, {}, {}
    try:
        before = read_installation(base)
    except Exception as error:
        before = safe_error(error)
    write_json(output_dir / "installation-before.json", before)
    if not before.get("read_error"):
        backend_id = before["containers"]["backend"]["id"]
        try:
            require(
                before["containers"]["backend"].get("state") == "running",
                "EXISTING_BACKEND_NOT_RUNNING",
            )
            require_no_pending(base)
            schema = collect_schema(backend_id)
        except Exception as error:
            schema = safe_error(error)
        try:
            require(
                before["containers"]["backend"].get("state") == "running",
                "EXISTING_BACKEND_NOT_RUNNING",
            )
            require_no_pending(base)
            monitoring = collect_monitoring(backend_id)
        except Exception as error:
            monitoring = safe_error(error)
        try:
            after = read_installation(base)
        except Exception as error:
            after = safe_error(error)
    else:
        schema = {"read_error": "INSTALLATION_NOT_VERIFIED_NO_DATABASE_READ"}
        monitoring = {"read_error": "INSTALLATION_NOT_VERIFIED_NO_API_READ"}
        after = {"read_error": "INSTALLATION_NOT_VERIFIED"}
    write_json(output_dir / "schema.json", schema)
    write_json(output_dir / "monitoring-private.json", monitoring)
    write_json(output_dir / "installation-after.json", after)
    summary["installation_unchanged_and_verified"] = (
        before.get("status") == "VERIFIED_INSTALLATION_BINDING"
        and not before.get("read_error")
        and not after.get("read_error")
        and before == after
    )
    summary["schema_read_available"] = schema.get(
        "status"
    ) == "READ_ONLY_SCHEMA_VERSION_OBSERVED" and not schema.get("read_error")
    summary["monitoring_transport_complete"] = monitoring_complete(monitoring)
    summary["monitoring_collection_status"] = monitoring.get("collection_status")
    summary["transport_complete"] = all(
        summary[key]
        for key in (
            "installation_unchanged_and_verified",
            "schema_read_available",
            "monitoring_transport_complete",
        )
    )
    summary["status"] = (
        "COMPLETE_PASSIVE_TRANSPORT_NOT_RULE_QUALIFICATION"
        if summary["transport_complete"]
        else "INCOMPLETE_PASSIVE_DIAGNOSTIC"
    )
    summary["completed_at"] = now()
    return summary


def outside_git(path: Path) -> bool:
    return all(not os.path.lexists(parent / ".git") for parent in (path, *path.parents))


def make_archive(output_dir: Path) -> Path:
    destination = output_dir.with_name(output_dir.name + ".tar.gz")
    descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with (
        os.fdopen(descriptor, "wb") as stream,
        tarfile.open(fileobj=stream, mode="w:gz") as archive,
    ):
        for path in sorted(output_dir.iterdir()):
            require(
                path.is_file() and not path.is_symlink(),
                "UNEXPECTED_DIAGNOSTIC_ARTIFACT",
            )
            archive.add(path, arcname=output_dir.name + "/" + path.name, recursive=False)
    return destination


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base",
        default=os.environ.get("TRADING_WORKSPACE_BASE", str(Path.home() / "Boerse")),
        help="Existing managed installation base (default: TRADING_WORKSPACE_BASE or ~/Boerse)",
    )
    parser.add_argument(
        "--source-gap-from",
        metavar="ARCHIVE.tar.gz",
        help="Read only one archived position's stored source journal/assessments; no HTTP GETs",
    )
    parser.add_argument(
        "--position-label",
        metavar="P02",
        help="Position label in --source-gap-from (bound to its archived IDs, never today's order)",
    )
    args = parser.parse_args(argv)
    os.umask(0o077)
    output_dir = None
    try:
        home = Path.home().resolve(strict=True)
        require(outside_git(home), "HOME_INSIDE_GIT_NO_PRIVATE_OUTPUT_LOCATION")
        output_dir = Path(tempfile.mkdtemp(prefix="trading-workspace-diagnose.", dir=home))
        os.chmod(output_dir, 0o700)
        print("Privates Diagnoseverzeichnis: " + str(output_dir), flush=True)
        base = Path(args.base).expanduser().absolute()
        try:
            require(
                not args.position_label or args.source_gap_from,
                "SOURCE_GAP_ARCHIVE_REQUIRED",
            )
            if args.source_gap_from:
                require(bool(args.position_label), "POSITION_LABEL_REQUIRED")
                summary = collect_source_gap(
                    base, output_dir, Path(args.source_gap_from), args.position_label
                )
            else:
                summary = collect(base, output_dir)
        except (Exception, KeyboardInterrupt) as error:
            summary = {
                "status": "INCOMPLETE_PASSIVE_DIAGNOSTIC",
                "transport_complete": False,
                **safe_error(error),
                "completed_at": now(),
            }
        write_json(output_dir / "summary.json", summary)
        archive = make_archive(output_dir)
        print("Privates Diagnosepaket: " + str(archive), flush=True)
        print("Status: " + summary["status"], flush=True)
        print(
            "Das Paket enthält private Depotdaten; nicht im Repository veröffentlichen.",
            flush=True,
        )
        return 0 if summary.get("transport_complete") is True else 2
    except (Exception, KeyboardInterrupt) as error:
        print(
            "Diagnosefehler: " + safe_error(error)["read_error"],
            file=sys.stderr,
            flush=True,
        )
        if output_dir is not None:
            print(
                "Privates Diagnoseverzeichnis bleibt erhalten: " + str(output_dir),
                flush=True,
            )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
