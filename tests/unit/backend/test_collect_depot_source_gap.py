"""Qualify the narrow private collector using synthetic archives and intercepted I/O.

Host tests need only the standard library. Payload tests use the real installed
backend contracts, with every database connection and owner read replaced by
controlled fixtures. They do not contact PostgreSQL, Docker, or a provider.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import io
import json
import logging
import os
import stat
import subprocess
import sys
import tarfile
import tempfile
import unittest
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts/collect-depot-data-supply.py"
TIME = "2020-01-02T12:00:00Z"
SECRET = "synthetic-password-NEVER-OUTPUT"
HAS_BACKEND = sys.version_info >= (3, 12) and importlib.util.find_spec("sqlalchemy") is not None


def load_tool():
    spec = importlib.util.spec_from_file_location("_source_gap_test_tool", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def uid(number: int) -> str:
    return str(UUID(int=number))


def fixture_documents(tool) -> dict:
    route = {
        "workspace_id": uid(10),
        "position_id": uid(2),
        "warrant_id": uid(202),
        "warrant_listing_id": uid(402),
        "trading_venue_id": uid(502),
        "venue_mic": "XETR",
        "currency": "EUR",
        "identity_key": "d" * 64,
        "selection_id": uid(602),
        "selected_at": TIME,
    }
    selected = {
        "position_id": uid(2),
        "trade_id": uid(102),
        "warrant_id": uid(202),
        "isin": "DE0000000001",
        "wkn": None,
        "selection_id": uid(602),
        "selection_status": "SELECTED",
        "selected_provider": "JPMORGAN",
        "warrant_listing_id": uid(402),
        "mapping_id": uid(702),
        "mapping_version": 1,
        "provider_exchange_code": "ISSUER",
        "mic": "XETR",
        "currency": "EUR",
        "policy_version": "synthetic-policy-v1",
        "selected_at": TIME,
        "identity_valid": True,
        "source_verified": True,
    }
    first = {
        **selected,
        "position_id": uid(1),
        "trade_id": uid(101),
        "warrant_id": uid(201),
    }
    for key in (
        "selection_id",
        "selected_provider",
        "warrant_listing_id",
        "mapping_id",
    ):
        first[key] = None
    first.update(
        selection_status="NO_VERIFIED_QUOTE_SOURCE",
        identity_valid=False,
        source_verified=False,
    )
    assessment = {
        "id": uid(802),
        "rule_version": "indicative-entry-review-v2",
        "evaluated_at": TIME,
        "recorded_at": TIME,
        "outcome": "UNAVAILABLE",
        "owner_basis_id": "e" * 64,
        "reasons": ["REVIEW_BID_MISSING"],
        "source": {
            "provider": "JPMORGAN",
            "listing_id": uid(402),
            "identity_key": route["identity_key"],
            "venue_mic": "XETR",
        },
    }
    inventory = {
        "http_status": 200,
        "body": {
            "items": [first, selected],
            "summary": {"open_positions": 2},
            "assessed_at": TIME,
            "assessment_scope": "STORED_OBSERVATIONS_NOT_LIVE_VALUATION",
            "execution_usable": False,
        },
    }
    positions = []
    for number, row in enumerate((first, selected), 1):
        reads = {
            name: {
                "http_status": 200,
                "body": {
                    "trade_id": row["trade_id"],
                    "position_id": row["position_id"],
                },
            }
            for name in tool.READ_NAMES
        }
        if number == 2:
            reads["indicative-entry"]["body"]["latest_assessment"] = assessment
            reads["hebeltrader-original-bid"]["body"].update(
                {
                    "product_id": row["warrant_id"],
                    "underlying_id": uid(302),
                    "saved_quote": {
                        "route": route,
                        "provider": "JPMORGAN",
                        "identity_key": route["identity_key"],
                    },
                }
            )
        positions.append({"label": f"P{number:02d}", "identity_private": row, "reads": reads})
    monitoring = {
        "schema": "PRIVATE_MONITORING_READBACK_2026_11_20",
        "requests": "GET_ONLY",
        "global_atomic_snapshot": False,
        "collection_status": tool.COMPLETE_READBACK,
        "started_at": TIME,
        "completed_at": TIME,
        "positions": positions,
        "coverage_checks": {
            key: True
            for key in (
                "inventory_schema_ids_and_counts_valid",
                "nonempty_portfolio_observed",
                "same_inventory_and_bindings",
                "same_idle_cycle_markers",
                "auxiliary_reads_available",
                "all_position_reads_available",
            )
        },
    }
    monitoring["coverage_checks"]["positions_requested"] = 2
    for name in ("runtime_before", "runtime_after", "refresh_before", "refresh_after"):
        monitoring[name] = {"http_status": 200, "body": {}}
    monitoring["inventory_before"] = copy.deepcopy(inventory)
    monitoring["inventory_after"] = copy.deepcopy(inventory)
    installation = {
        "status": "VERIFIED_INSTALLATION_BINDING",
        "commit": "a" * 40,
        "version": "1.5.52",
        "containers": {"backend": {"id": "a" * 64, "state": "running", "started_at": TIME}},
    }
    return {
        "monitoring-private.json": monitoring,
        "installation-before.json": copy.deepcopy(installation),
        "installation-after.json": copy.deepcopy(installation),
        "schema.json": {
            "status": "READ_ONLY_SCHEMA_VERSION_OBSERVED",
            "read_only": True,
            "versions": ["20261118_0060"],
        },
        "summary.json": {
            "schema": "PRIVATE_DEPOT_DATA_SUPPLY_DIAGNOSTIC_2026_11_21",
            "transport_complete": True,
            "read_only": True,
            "backend_payload_sha256": hashlib.sha256(tool.BACKEND_PAYLOAD.encode()).hexdigest(),
        },
    }


def write_archive(path: Path, documents: dict, *, extras=(), transform=None) -> None:
    with tarfile.open(path, "w:gz") as archive:
        for name, value in documents.items():
            raw = json.dumps(value).encode()
            info = tarfile.TarInfo("synthetic-readback/" + name)
            info.size = len(raw)
            if transform:
                info, raw = transform(info, raw)
            archive.addfile(info, io.BytesIO(raw) if info.isreg() else None)
        for info, raw in extras:
            archive.addfile(info, io.BytesIO(raw) if raw is not None else None)


class SourceGapFixture(unittest.TestCase):
    def setUp(self):
        self.tool = load_tool()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.archive = Path(self.tmp.name) / "original.tar.gz"
        self.documents = fixture_documents(self.tool)

    def reference(self):
        write_archive(self.archive, self.documents)
        return self.tool.read_source_gap_reference(self.archive, "P02")


class ArchiveReferenceTest(SourceGapFixture):
    def test_reference_uses_archived_identity_not_list_index(self):
        self.documents["monitoring-private.json"]["positions"].reverse()
        ref = self.reference()
        self.assertEqual(ref["binding"]["position_id"], uid(2))
        self.assertEqual(ref["assessment"]["id"], uid(802))
        self.assertNotIn("bid", ref["binding"])
        self.assertEqual(ref["installation"]["version"], "1.5.52")

    def test_tar_rejects_links_traversal_duplicates_extra_and_missing_members(self):
        for kind in (
            "symlink",
            "hardlink",
            "traversal",
            "duplicate",
            "extra",
            "missing",
        ):
            with self.subTest(kind=kind):
                docs = copy.deepcopy(self.documents)
                extras, transform = [], None
                if kind == "missing":
                    docs.pop("schema.json")
                elif kind in ("symlink", "hardlink", "traversal"):

                    def transform(info, raw, kind=kind):
                        if info.name.endswith("schema.json"):
                            if kind == "traversal":
                                info.name = "../schema.json"
                            else:
                                info.type = (
                                    tarfile.SYMTYPE if kind == "symlink" else tarfile.LNKTYPE
                                )
                                info.linkname = "/synthetic-private-secret"
                                info.size = 0
                        return info, raw

                else:
                    info = tarfile.TarInfo(
                        "synthetic-readback/"
                        + ("schema.json" if kind == "duplicate" else "extra.json")
                    )
                    info.size = 2
                    extras = [(info, b"{}")]
                write_archive(self.archive, docs, extras=extras, transform=transform)
                with self.assertRaises(self.tool.DiagnosticError):
                    self.tool.read_source_gap_reference(self.archive, "P02")

    def test_archive_and_decompression_and_member_limits_are_bounded(self):
        write_archive(self.archive, self.documents)
        for limit in (
            "MAX_REFERENCE_ARCHIVE_BYTES",
            "MAX_REFERENCE_TAR_BYTES",
            "MAX_REFERENCE_JSON_BYTES",
            "MAX_REFERENCE_TOTAL_BYTES",
        ):
            with (
                self.subTest(limit=limit),
                patch.object(self.tool, limit, 10),
                self.assertRaises(self.tool.DiagnosticError),
            ):
                self.tool.read_source_gap_reference(self.archive, "P02")

    def test_duplicate_json_keys_and_nonfinite_numbers_are_rejected(self):
        for raw in (b'{"id":1,"id":2}', b'{"value":NaN}', b'{"value":Infinity}'):
            with self.subTest(raw=raw), self.assertRaises(self.tool.DiagnosticError):
                self.tool.reference_json(raw)

    def test_archive_inventory_label_uuid_and_assessment_changes_fail_closed(self):
        def edit(kind, documents):
            monitoring = documents["monitoring-private.json"]
            row = monitoring["positions"][1]
            if kind == "uuid":
                row["identity_private"]["position_id"] = "../../other"
            elif kind == "duplicate_id":
                monitoring["positions"][0] = copy.deepcopy(row)
            elif kind == "label":
                row["label"] = "P01"
            elif kind == "inventory_changed":
                monitoring["inventory_after"]["body"]["items"][1]["currency"] = "USD"
            elif kind == "assessment_route":
                row["reads"]["indicative-entry"]["body"]["latest_assessment"]["source"][
                    "identity_key"
                ] = ("f" * 64)
            else:
                row["reads"]["indicative-entry"]["body"]["latest_assessment"]["id"] = "not-uuid"

        for kind in (
            "uuid",
            "duplicate_id",
            "label",
            "inventory_changed",
            "assessment_route",
            "assessment_id",
        ):
            with self.subTest(kind=kind):
                documents = copy.deepcopy(self.documents)
                edit(kind, documents)
                write_archive(self.archive, documents)
                with self.assertRaises(self.tool.DiagnosticError):
                    self.tool.read_source_gap_reference(self.archive, "P02")


@unittest.skipUnless(HAS_BACKEND, "Real backend contracts require the backend Python/dependencies")
class SourceGapPayloadTest(SourceGapFixture):
    def run_payload(
        self,
        *,
        missing_quote=False,
        empty_journal=False,
        newer_head=False,
        change=None,
        fail=None,
    ):
        import sqlalchemy.ext.asyncio as sa_async

        from app.core import config
        from app.features.market_data.domain.models import WarrantQuoteSnapshot
        from app.features.market_data.domain.risk_evidence import (
            SavedQuoteEvidence,
            SavedQuoteRouteBinding,
        )
        from app.features.market_data.domain.status_observations import (
            MarketStatusObservation,
            StatusEvidenceRead,
        )
        from app.features.market_data.persistence.models import (
            PositionQuoteSourceSelectionModel,
        )
        from app.features.market_data.service.risk_read import RiskMarketDataReader
        from app.features.market_data.service.status_observations import (
            MarketStatusReader,
        )
        from app.features.position_monitoring.persistence.indicative_entry import (
            IndicativeEntryAssessmentModel,
        )
        from app.features.position_monitoring.service import indicative_entry
        from app.features.product.persistence.models import WarrantModel
        from app.features.trade_position.service.open_position_reader import (
            OpenPositionReader,
            OpenPositionReference,
        )

        ref = self.reference()
        b = ref["binding"]
        route_values = dict(b["route"])
        for key in (
            "workspace_id",
            "position_id",
            "warrant_id",
            "warrant_listing_id",
            "trading_venue_id",
            "selection_id",
        ):
            route_values[key] = UUID(route_values[key])
        route_values["selected_at"] = datetime.fromisoformat(TIME.replace("Z", "+00:00"))
        route = SavedQuoteRouteBinding(**route_values)
        if change == "route":
            route = replace(route, identity_key="f" * 64)
        quote = (
            None
            if missing_quote
            else WarrantQuoteSnapshot(
                UUID(b["route"]["warrant_listing_id"]),
                None,
                None,
                "EUR",
                b["isin"],
                "ISSUER",
                None,
                isin=b["isin"],
                source_mode="OFFICIAL_ISSUER_INDICATION_TIME_ONLY",
                quote_time_text="12:00:00",
                quote_time_basis="DATE_AND_TIMEZONE_UNKNOWN",
            )
        )
        saved = SavedQuoteEvidence(
            (
                "NO_SAVED_QUOTE_FOR_CURRENT_ROUTE"
                if missing_quote
                else "LAST_SUCCESS_IS_NOT_A_PRICE_SERIES"
            ),
            quote=quote,
            provider=None if missing_quote else "JPMORGAN",
            route=route,
        )
        warrant = SimpleNamespace(
            workspace_id=UUID(b["workspace_id"]),
            isin=b["isin"],
            wkn=None,
            underlying_id=UUID(b["underlying_id"]),
        )
        if change == "product":
            warrant.isin = "DE0000000002"
        selection = SimpleNamespace(
            workspace_id=UUID(b["workspace_id"]),
            position_id=UUID(b["position_id"]),
            superseded_at=None,
            selection_status="SELECTED",
            provider="JPMORGAN",
            identity_key=b["route"]["identity_key"],
            warrant_listing_id=UUID(b["route"]["warrant_listing_id"]),
            warrant_provider_mapping_id=UUID(b["mapping_id"]),
            mapping_version=1,
            policy_version=b["policy_version"],
            selected_at=route_values["selected_at"],
        )
        if change == "selection":
            selection.mapping_version = 2
        old_inputs = {
            "warrant_isin": b["isin"],
            "saved_quote": {"provider": "JPMORGAN", "route": copy.deepcopy(b["route"])},
            "status_observations": {
                "known_at": TIME,
                "latest_gap": {"reason": "HISTORICAL_RESPONSE_EMPTY"},
            },
        }
        old = SimpleNamespace(
            **{k: UUID(b[k]) for k in ("workspace_id", "trade_id", "position_id")},
            id=UUID(ref["assessment"]["id"]),
            rule_version=ref["assessment"]["rule_version"],
            previous_assessment_id=None,
            evaluated_at=route_values["selected_at"],
            recorded_at=route_values["selected_at"],
            ordering_at=None,
            outcome="UNAVAILABLE",
            owner_basis_id="e" * 64,
            input_fingerprint="f" * 64,
            inputs=old_inputs,
            result={"reasons": ref["assessment"]["reasons"]},
        )
        if change == "old_time":
            old.evaluated_at += timedelta(seconds=1)
        if change == "old_scope":
            old.trade_id = UUID(uid(999))
        if change == "old_route":
            old.inputs["saved_quote"]["route"]["identity_key"] = "f" * 64
        current = copy.deepcopy(old)
        if newer_head:
            current.id = UUID(uid(999))
            current.previous_assessment_id = old.id
            current.evaluated_at += timedelta(days=1)
            current.recorded_at += timedelta(days=1)
            current.inputs["status_observations"] = {
                "known_at": "2020-01-03T12:00:00Z",
                "latest_gap": None,
            }
        calls, options, session_options = [], {}, {}
        database_url = "postgresql+asyncpg://synthetic:" + SECRET + "@unreachable.example/test"

        class Connection:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                calls.append("CONNECTION_CLOSED")

            async def execute(self, statement):
                sql = str(statement)
                allowed = {
                    "BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY",
                    "SET LOCAL statement_timeout = '10s'",
                    "SET LOCAL lock_timeout = '2s'",
                    "SELECT current_setting('transaction_read_only'), "
                    "current_setting('transaction_isolation')",
                    "ROLLBACK",
                }
                if sql not in allowed:
                    raise AssertionError("Unexpected database SQL")
                calls.append(sql)
                if fail == "settings" and sql.startswith("SELECT"):
                    raise RuntimeError(database_url)
                return SimpleNamespace(
                    one=lambda: (
                        "off" if fail == "readonly" else "on",
                        "repeatable read",
                    )
                )

        class Engine:
            def connect(self):
                return Connection()

            async def dispose(self):
                calls.append("ENGINE_DISPOSED")

        class Session:
            def __init__(self, **kwargs):
                session_options.update(kwargs)

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                calls.append("SESSION_CLOSED")

            async def rollback(self):
                calls.append("SESSION_ROLLBACK")

            async def get(self, model, key):
                calls.append("GET:" + model.__name__)
                if model is WarrantModel and key == UUID(b["warrant_id"]):
                    return warrant
                if model is PositionQuoteSourceSelectionModel and key == UUID(
                    b["route"]["selection_id"]
                ):
                    return selection
                if model is IndicativeEntryAssessmentModel and key == UUID(ref["assessment"]["id"]):
                    return old
                raise AssertionError("Unexpected private scope")

        async def position_read(_self, **kwargs):
            self.assertEqual(
                kwargs,
                {
                    "workspace_id": UUID(b["workspace_id"]),
                    "trade_id": UUID(b["trade_id"]),
                    "lock": False,
                },
            )
            calls.append("OPEN_POSITION_READ")
            if change == "closed":
                return None
            return OpenPositionReference(
                *(UUID(b[k]) for k in ("workspace_id", "trade_id", "position_id", "warrant_id"))
            )

        async def quote_read(_self, **kwargs):
            self.assertEqual(kwargs["expected_warrant_id"], UUID(b["warrant_id"]))
            self.assertGreater(kwargs["as_of"], old.evaluated_at)
            calls.append("SAVED_QUOTE_READ")
            return saved

        async def latest_read(_session, workspace_id, position_id):
            self.assertEqual(
                (workspace_id, position_id),
                (UUID(b["workspace_id"]), UUID(b["position_id"])),
            )
            calls.append("LATEST_ASSESSMENT_READ")
            return current

        async def status_read(_self, **kwargs):
            self.assertEqual(set(kwargs), {"route", "event_at", "known_at"})
            self.assertEqual(kwargs["event_at"], kwargs["known_at"])
            self.assertEqual(kwargs["route"].identity_key, b["route"]["identity_key"])
            calls.append("STATUS_READ")
            if fail == "status":
                raise RuntimeError(database_url)
            gap = (
                None
                if empty_journal
                else MarketStatusObservation(
                    UUID(uid(903)),
                    "1" * 64,
                    kwargs["route"],
                    kwargs["known_at"] - timedelta(seconds=2),
                    None,
                    None,
                    "SYNTHETIC_UPSTREAM_TIMEOUT",
                )
            )
            return StatusEvidenceRead(
                kwargs["route"],
                kwargs["event_at"],
                kwargs["known_at"],
                "NO_POINT_AT_EVENT",
                None,
                (),
                (),
                gap,
                gap,
            )

        def create_engine(url, **kwargs):
            self.assertEqual(url, database_url)
            options.update(kwargs)
            return Engine()

        output = io.StringIO()
        previous_logging = logging.root.manager.disable
        try:
            with ExitStack() as stack:
                stack.enter_context(
                    patch.object(
                        config,
                        "get_settings",
                        return_value=SimpleNamespace(database_url=database_url),
                    )
                )
                stack.enter_context(
                    patch.object(sa_async, "create_async_engine", side_effect=create_engine)
                )
                stack.enter_context(patch.object(sa_async, "AsyncSession", Session))
                stack.enter_context(patch.object(OpenPositionReader, "read", position_read))
                stack.enter_context(patch.object(RiskMarketDataReader, "saved_quote", quote_read))
                stack.enter_context(patch.object(MarketStatusReader, "read", status_read))
                stack.enter_context(
                    patch.object(indicative_entry, "latest_indicative_assessment", latest_read)
                )
                stack.enter_context(
                    patch.object(
                        sys,
                        "stdin",
                        SimpleNamespace(buffer=io.BytesIO(json.dumps(ref).encode())),
                    )
                )
                stack.enter_context(
                    patch.object(
                        subprocess,
                        "run",
                        side_effect=AssertionError("No live commands"),
                    )
                )
                stack.enter_context(redirect_stdout(output))
                exec(
                    compile(self.tool.SOURCE_GAP_PAYLOAD, "<synthetic-source-gap>", "exec"),
                    {},
                )
        finally:
            logging.disable(previous_logging)
        self.assertNotIn(SECRET, output.getvalue())
        self.assertNotIn(database_url, output.getvalue())
        return json.loads(output.getvalue()), ref, calls, options, session_options

    def test_actual_contracts_keep_historical_context_and_new_head_separate(self):
        result, ref, calls, options, session_options = self.run_payload(newer_head=True)
        self.assertTrue(self.tool.source_gap_complete(result, ref), result)
        self.assertFalse(result["same_assessment_head"])
        self.assertEqual(
            result["archived_assessment"]["inputs"]["status_observations"]["latest_gap"]["reason"],
            "HISTORICAL_RESPONSE_EMPTY",
        )
        self.assertEqual(
            result["current_status"]["latest_gap"]["reason"],
            "SYNTHETIC_UPSTREAM_TIMEOUT",
        )
        self.assertEqual(calls[0], "BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY")
        self.assertEqual(calls[-3:], ["ROLLBACK", "CONNECTION_CLOSED", "ENGINE_DISPOSED"])
        self.assertFalse(session_options["autoflush"])
        self.assertFalse(options["echo"])
        self.assertEqual(
            options["connect_args"]["server_settings"]["default_transaction_read_only"],
            "on",
        )

    def test_missing_quote_and_empty_bound_journal_are_readable_not_price_success(self):
        result, ref, *_ = self.run_payload(missing_quote=True, empty_journal=True)
        self.assertTrue(self.tool.source_gap_complete(result, ref), result)
        self.assertEqual(result["journal_state"], "NO_OBSERVATIONS_IN_BOUND_ROUTE")
        self.assertIsNone(result["saved_quote"]["quote"])
        self.assertEqual(
            result["status_provider_basis"],
            "IDENTITY_VERIFIED_SELECTION_WITHOUT_SAVED_PRICE",
        )
        self.assertIn("NOT_PRICE_QUALIFICATION", result["status"])

    def test_changed_bindings_and_archived_identity_fail_before_journal_read(self):
        for change in (
            "closed",
            "product",
            "route",
            "selection",
            "old_time",
            "old_scope",
            "old_route",
        ):
            with self.subTest(change=change):
                result, ref, calls, *_ = self.run_payload(change=change)
                self.assertFalse(self.tool.source_gap_complete(result, ref))
                self.assertEqual(result["read_error"], "BoundReadError")
                self.assertNotIn("STATUS_READ", calls)
                self.assertEqual(calls[-3:], ["ROLLBACK", "CONNECTION_CLOSED", "ENGINE_DISPOSED"])

    def test_database_and_owner_failures_always_rollback_and_redact(self):
        for fail in ("settings", "readonly", "status"):
            with self.subTest(fail=fail):
                result, ref, calls, *_ = self.run_payload(fail=fail)
                self.assertFalse(self.tool.source_gap_complete(result, ref))
                self.assertIn("read_error", result)
                self.assertEqual(calls[-3:], ["ROLLBACK", "CONNECTION_CLOSED", "ENGINE_DISPOSED"])
                if fail != "status":
                    self.assertNotIn("OPEN_POSITION_READ", calls)

    def test_host_rejects_incomplete_or_misbound_response(self):
        result, ref, *_ = self.run_payload()
        for kind in ("missing_time", "status_route", "gap_reason", "archived_id"):
            modified = copy.deepcopy(result)
            if kind == "missing_time":
                modified.pop("read_at")
            elif kind == "status_route":
                modified["current_status"]["route"]["identity_key"] = "f" * 64
            elif kind == "gap_reason":
                modified["current_status"]["latest_gap"]["reason"] = None
            else:
                modified["archived_assessment"]["id"] = uid(999)
            with self.subTest(kind=kind):
                self.assertFalse(self.tool.source_gap_complete(modified, ref))


class SourceGapHostTest(SourceGapFixture):
    def invoke(self, *, bad_archive=False, changed_installation=False):
        write_archive(self.archive, self.documents)
        if bad_archive:
            self.archive.write_bytes(b"not-an-archive")
        home = Path(self.tmp.name) / "synthetic-home"
        home.mkdir(mode=0o700)
        installation = copy.deepcopy(self.documents["installation-before.json"])
        # A later regular restart is legitimate; only this read's before/after must match.
        installation["containers"]["backend"]["id"] = "b" * 64
        after = copy.deepcopy(installation)
        if changed_installation:
            after["containers"]["backend"]["id"] = "c" * 64
        stdout, stderr = io.StringIO(), io.StringIO()
        fake_gap = {"synthetic_bound_read": True}
        old_umask = os.umask(0o077)
        try:
            with (
                patch.object(self.tool.Path, "home", return_value=home),
                patch.object(self.tool, "outside_git", return_value=True),
                patch.object(
                    self.tool, "read_installation", side_effect=[installation, after]
                ) as installations,
                patch.object(self.tool, "require_no_pending"),
                patch.object(
                    self.tool,
                    "collect_schema",
                    return_value=self.documents["schema.json"],
                ),
                patch.object(
                    self.tool, "collect_source_gap_read", return_value=fake_gap
                ) as gap_read,
                patch.object(
                    self.tool,
                    "source_gap_complete",
                    side_effect=lambda value, _ref: value == fake_gap,
                ),
                patch.object(
                    self.tool,
                    "collect_monitoring",
                    side_effect=AssertionError("No broad GET collector"),
                ),
                patch.object(
                    self.tool,
                    "run_command",
                    side_effect=AssertionError("No live command"),
                ),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                code = self.tool.main(
                    [
                        "--base",
                        str(home / "Boerse"),
                        "--source-gap-from",
                        str(self.archive),
                        "--position-label",
                        "P02",
                    ]
                )
        finally:
            os.umask(old_umask)
        directories = list(home.glob("trading-workspace-diagnose.*"))
        output = next(p for p in directories if p.is_dir())
        return (
            code,
            output,
            stdout.getvalue() + stderr.getvalue(),
            installations,
            gap_read,
        )

    def test_narrow_mode_uses_existing_private_bundle_and_accepts_regular_restart(self):
        code, output, console, _, gap_read = self.invoke()
        self.assertEqual(code, 0, console)
        self.assertEqual(gap_read.call_args.args[0], "b" * 64)
        self.assertEqual(gap_read.call_args.args[1]["binding"]["position_id"], uid(2))
        self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o700)
        self.assertEqual(
            {p.name for p in output.iterdir()},
            {
                "installation-before.json",
                "installation-after.json",
                "schema.json",
                "source-gap-private.json",
                "summary.json",
            },
        )
        for path in (*output.iterdir(), output.with_name(output.name + ".tar.gz")):
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertNotIn(uid(2), console)
        self.assertNotIn("DE0000000001", console)

    def test_invalid_archive_never_inspects_or_executes_backend_and_keeps_bundle(self):
        code, output, console, installations, gap_read = self.invoke(bad_archive=True)
        self.assertEqual(code, 2)
        installations.assert_not_called()
        gap_read.assert_not_called()
        self.assertTrue(output.with_name(output.name + ".tar.gz").is_file())
        self.assertIn(str(output), console)
        self.assertFalse(json.loads((output / "summary.json").read_text())["transport_complete"])

    def test_installation_change_makes_otherwise_complete_read_incomplete(self):
        code, output, *_ = self.invoke(changed_installation=True)
        self.assertEqual(code, 2)
        summary = json.loads((output / "summary.json").read_text())
        self.assertFalse(summary["installation_unchanged_and_verified"])
        self.assertFalse(summary["transport_complete"])

    def test_embedded_command_is_constant_and_private_binding_only_uses_stdin(self):
        ref = self.reference()
        captured = {}

        def command(args, **kwargs):
            captured.update(args=args, **kwargs)
            return json.dumps({"synthetic": True})

        with (
            patch.object(self.tool, "run_command", side_effect=command),
            patch.object(self.tool, "source_gap_complete", return_value=True),
        ):
            self.tool.collect_source_gap_read("a" * 64, ref)
        self.assertEqual(
            captured["args"][-4:], ["python", "-B", "-c", self.tool.SOURCE_GAP_PAYLOAD]
        )
        self.assertNotIn(uid(2), " ".join(captured["args"]))
        self.assertEqual(json.loads(captured["input_text"]), ref)

    def test_payload_has_no_mutating_or_provider_http_calls(self):
        tree = ast.parse(self.tool.SOURCE_GAP_PAYLOAD)
        forbidden = {
            "commit",
            "flush",
            "begin_nested",
            "prepare_for_review",
            "evaluate",
            "fetch",
            "create_subprocess_exec",
        }
        calls = {
            n.func.attr
            for n in ast.walk(tree)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        }
        self.assertFalse(calls & forbidden)
        imports = {n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
        self.assertFalse(
            any(name.startswith(("httpx", "requests", "app.providers")) for name in imports)
        )


if __name__ == "__main__":
    unittest.main()
