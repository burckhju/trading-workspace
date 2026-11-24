"""Qualify the archived candidate collector with synthetic data and intercepted I/O.

No user archive, Docker daemon, live database, or provider is accessed. Host tests
use only the standard library; payload tests use actual backend contracts with
controlled connections and owner responses.
"""

from __future__ import annotations

import ast
import asyncio
import copy
import hashlib
import importlib.util
import io
import json
import logging
import os
import socket
import stat
import sys
import tarfile
import tempfile
import unittest
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID

ROOT = Path(__file__).resolve().parents[3]
SECRET = "synthetic-source-coverage-password-NEVER-OUTPUT"
COMPLETE = "COMPLETE_PASSIVE_SOURCE_COVERAGE_READ_NOT_RULE_QUALIFICATION"
HAS_BACKEND = sys.version_info >= (3, 12) and importlib.util.find_spec("sqlalchemy") is not None
FROZEN_PAYLOADS = {
    "BACKEND_PAYLOAD": "b8dee0cd47ccd95a224cf5897eb60233d3195bf9d76700a103acfcfbc5dbafab",
    "SCHEMA_PAYLOAD": "7aba0ec505ed0c1bebbf190faa8c09c888bb1d78a8c3a22db2b2d4c1602f783d",
    "SOURCE_GAP_PAYLOAD": "56123ebd72cb83621f706bf13ee2d9a46dc05e54559f8ce51b7b9cf3038134dd",
}


def fixture_helpers():
    path = ROOT / "tests/unit/backend/test_collect_depot_source_gap.py"
    spec = importlib.util.spec_from_file_location("_source_coverage_fixture_helpers", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


HELPERS = fixture_helpers()
TIME = HELPERS.TIME
uid = HELPERS.uid


def candidate_documents(tool, *, unbound_count=3):
    """Reuse the reviewed full-archive envelope, adding actual unbound DTO shapes."""
    documents = HELPERS.fixture_documents(tool)
    monitoring = documents["monitoring-private.json"]
    selected = copy.deepcopy(monitoring["positions"][1])
    template = copy.deepcopy(monitoring["positions"][0]["identity_private"])
    assessment_template = selected["reads"]["indicative-entry"]["body"]["latest_assessment"]
    positions = [selected]
    numbers = [1, *range(3, unbound_count + 2)] if unbound_count else []
    if not numbers:
        selected["label"] = "P01"
    for offset, number in enumerate(numbers):
        status = (None, "NO_VERIFIED_QUOTE_SOURCE", "AMBIGUOUS_SOURCE")[offset % 3]
        row = {
            **template,
            "position_id": uid(number),
            "trade_id": uid(100 + number),
            "warrant_id": uid(200 + number),
            "isin": f"DE{number:010d}",
            "wkn": None,
            "selection_id": uid(600 + number) if status else None,
            "selection_status": status,
            "selection_reason": "SYNTHETIC_NO_UNIQUE_ROUTE" if status else None,
            "policy_version": "synthetic-policy-v1" if status else None,
            "selected_at": TIME if status else None,
            "selected_provider": None,
            "warrant_listing_id": None,
            "mapping_id": None,
            "mapping_version": None,
            "provider_exchange_code": None,
            "mic": None,
            "currency": None,
            "identity_valid": False,
            "source_verified": False,
        }
        reads = {
            name: {
                "http_status": 200,
                "body": {"trade_id": row["trade_id"], "position_id": row["position_id"]},
            }
            for name in tool.READ_NAMES
        }
        reads["hebeltrader-original-bid"]["body"].update(
            product_id=row["warrant_id"],
            underlying_id=uid(300 + number),
            saved_quote=None,
            unused_provider_payload=SECRET,
        )
        assessment = None
        if status:
            assessment = {
                **assessment_template,
                "id": uid(800 + number),
                "reasons": ["NO_CONFIRMED_SAVED_QUOTE_SOURCE"],
            }
            assessment.pop("source")
        reads["indicative-entry"]["body"]["latest_assessment"] = assessment
        positions.append({"label": f"P{number:02d}", "identity_private": row, "reads": reads})
    positions.sort(key=lambda row: row["identity_private"]["position_id"])
    monitoring["positions"] = positions
    for key in ("inventory_before", "inventory_after"):
        body = monitoring[key]["body"]
        body["items"] = [copy.deepcopy(row["identity_private"]) for row in positions]
        body["summary"]["open_positions"] = len(positions)
    monitoring["coverage_checks"]["positions_requested"] = len(positions)
    for key in ("refresh_before", "refresh_after"):
        monitoring[key]["body"]["workspace_id"] = uid(10)
    return documents


def coverage_responses(reference):
    """Serialize real public DTOs with rejected routes and one unrelated holding."""
    from datetime import UTC

    from app.features.market_data.service.position_quote_coverage import (
        PositionQuoteCoverage,
        PositionQuoteCoverageReport,
        PositionQuoteCoverageSummary,
        PositionQuoteSourceHealth,
    )
    from app.features.market_data.service.quote_coverage import (
        CoverageReport,
        ProductCoverage,
        RefreshJobCoverage,
        RouteCoverage,
    )
    from pydantic import TypeAdapter

    positions, products = [], []
    now = datetime.now(UTC)
    extra = copy.deepcopy(reference["positions"][0])
    extra["binding"].update(position_id=uid(99), trade_id=uid(199), warrant_id=uid(299))
    for archived in (*reference["positions"], extra):
        binding, selection = archived["binding"], archived["selection"]
        position_id = UUID(binding["position_id"])
        warrant_id = UUID(binding["warrant_id"])
        name = "synthetic-unrelated-holding" if position_id.int == 99 else "Synthetic product"
        positions.append(
            PositionQuoteCoverage(
                position_id=position_id,
                trade_id=UUID(binding["trade_id"]),
                warrant_id=warrant_id,
                name=name,
                isin=binding["isin"],
                wkn=binding["wkn"],
                selection_id=UUID(selection["id"]) if selection["id"] else None,
                selection_status=selection["selection_status"],
                selection_reason=selection["selection_reason"],
                policy_version=selection["policy_version"],
                selected_at=(
                    datetime.fromisoformat(TIME.replace("Z", "+00:00"))
                    if selection["selected_at"]
                    else None
                ),
                selected_provider=None,
                warrant_listing_id=None,
                mapping_id=None,
                provider_exchange_code=None,
                mic=None,
                currency=None,
                mapping_status=None,
                mapping_version=None,
                identity_valid=False,
                source_verified=False,
                source_health=PositionQuoteSourceHealth.NO_VERIFIED_QUOTE_SOURCE,
                candidate_product_coverage="NO_VERIFIED_QUOTE_SOURCE",
            )
        )
        routes = (
            RouteCoverage(
                provider="EODHD",
                listing_id=UUID(int=4000 + warrant_id.int),
                mic="XFRA",
                currency="EUR",
                mapping_id=UUID(int=5000 + warrant_id.int),
                mapping_status="ACTIVE",
                provider_identity=binding["isin"],
                provider_exchange_code="F",
                validated_at=now,
                configured=False,
                route_reason="ROUTE_IDENTITY_VERIFIED",
                observation_status="NO_SAVED_OBSERVATION",
            ),
            RouteCoverage(
                provider="JPMORGAN",
                listing_id=UUID(int=6000 + warrant_id.int),
                mic="XETR",
                currency="EUR",
                mapping_id=None,
                mapping_status=None,
                provider_identity=None,
                provider_exchange_code="ISSUER",
                validated_at=None,
                configured=True,
                route_reason="MAPPING_NOT_VERIFIED",
                observation_status="NO_SAVED_OBSERVATION",
            ),
        )
        products.append(
            ProductCoverage(
                warrant_id=warrant_id,
                name=name,
                isin=binding["isin"],
                wkn=binding["wkn"],
                issuer="Synthetic issuer",
                issuer_probe_eligible=True,
                coverage="NO_VERIFIED_QUOTE_SOURCE",
                routes=routes,
                refresh_status="FAILED",
                refresh_reason="SYNTHETIC_SNAPSHOT_TIMEOUT",
                checked_at=now,
                next_run_at=None,
                discovery_reasons=("SYNTHETIC_MAPPING_REQUIRES_REVIEW",),
                refresh_jobs=(
                    RefreshJobCoverage(
                        "ISSUER_QUOTES", "FAILED", "SYNTHETIC_SNAPSHOT_TIMEOUT", now, None
                    ),
                ),
            )
        )
    summary = PositionQuoteCoverageSummary(
        open_positions=len(positions),
        bound_positions=0,
        legacy_unbound=1,
        source_verified=0,
        fresh_quote=0,
        last_available=0,
        retained_after_refresh_error=0,
        stale=0,
        reference_only=0,
        missing_quote=0,
        missing_source=len(positions) - 1,
        source_disabled=0,
        mapping_conflict=0,
        ambiguous_source=0,
        invalid_quote=0,
    )
    position_report = PositionQuoteCoverageReport(
        now, ("JPMORGAN",), ("JPMORGAN", "EODHD"), summary, tuple(reversed(positions))
    )
    product_report = CoverageReport(
        now, True, True, ("JPMORGAN", "EODHD"), ("JPMORGAN",), tuple(reversed(products))
    )
    return {
        "positions": TypeAdapter(PositionQuoteCoverageReport).dump_python(
            position_report, mode="json"
        ),
        "products": TypeAdapter(CoverageReport).dump_python(product_report, mode="json"),
    }


class SourceCoverageFixture(unittest.TestCase):
    def setUp(self):
        self.tool = HELPERS.load_tool()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.archive = Path(self.tmp.name) / "original.tar.gz"
        self.documents = candidate_documents(self.tool)

    def reference(self):
        HELPERS.write_archive(self.archive, self.documents)
        return self.tool.read_source_coverage_reference(self.archive)


class CoverageArchiveTest(SourceCoverageFixture):
    def test_all_archived_unbound_candidates_are_selected_without_index_rebinding(self):
        monitoring = self.documents["monitoring-private.json"]
        monitoring["positions"].reverse()
        monitoring["inventory_before"]["body"]["items"].reverse()
        reference = self.reference()
        self.assertEqual(reference["schema"], "PRIVATE_DEPOT_SOURCE_COVERAGE_REFERENCE_V1")
        actual = {
            item["position_label"]: item["binding"]["position_id"]
            for item in reference["positions"]
        }
        self.assertEqual(actual, {"P01": uid(1), "P03": uid(3), "P04": uid(4)})
        self.assertNotIn("P02", actual)
        self.assertEqual(
            reference["archive_sha256"], hashlib.sha256(self.archive.read_bytes()).hexdigest()
        )
        for item in reference["positions"]:
            self.assertEqual(item["binding"]["workspace_id"], uid(10))
            self.assertNotIn("route", item["binding"])
        self.assertNotIn(SECRET, json.dumps(reference))

    def test_missing_optional_history_and_identity_are_not_invented(self):
        monitoring = self.documents["monitoring-private.json"]
        first = monitoring["positions"][0]
        first["identity_private"]["isin"] = None
        first["reads"]["hebeltrader-original-bid"]["body"]["underlying_id"] = None
        for key in ("inventory_before", "inventory_after"):
            monitoring[key]["body"]["items"][0]["isin"] = None
        reference = self.reference()
        item = next(row for row in reference["positions"] if row["position_label"] == "P01")
        self.assertIsNone(item["assessment"])
        self.assertIsNone(item["binding"]["underlying_id"])
        self.assertIsNone(item["binding"]["isin"])
        self.assertIsNone(item["binding"]["wkn"])
        self.assertIsNone(item["selection"]["id"])
        self.assertIsNone(item["selection"]["provider"])

    def test_archive_scope_and_reader_binding_changes_fail_closed(self):
        original = copy.deepcopy(self.documents)
        for change in (
            "workspace",
            "workspace_missing",
            "label",
            "reader_position",
            "reader_product",
            "underlying_uuid",
            "inventory_binding",
            "incomplete",
            "payload_hash",
        ):
            with self.subTest(change=change):
                self.documents = copy.deepcopy(original)
                monitoring = self.documents["monitoring-private.json"]
                first = monitoring["positions"][0]
                if change == "workspace":
                    monitoring["refresh_after"]["body"]["workspace_id"] = uid(11)
                elif change == "workspace_missing":
                    monitoring["refresh_before"]["body"].pop("workspace_id")
                elif change == "label":
                    first["label"] = "P03"
                elif change == "reader_position":
                    first["reads"]["indicative-entry"]["body"]["position_id"] = uid(99)
                elif change == "reader_product":
                    first["reads"]["hebeltrader-original-bid"]["body"]["product_id"] = uid(299)
                elif change == "underlying_uuid":
                    first["reads"]["hebeltrader-original-bid"]["body"]["underlying_id"] = "bad"
                elif change == "inventory_binding":
                    monitoring["inventory_after"]["body"]["items"][0]["trade_id"] = uid(999)
                elif change == "incomplete":
                    self.documents["summary.json"]["transport_complete"] = False
                else:
                    self.documents["summary.json"]["backend_payload_sha256"] = "0" * 64
                with self.assertRaises(self.tool.DiagnosticError):
                    self.reference()

    def test_empty_or_over_budget_candidate_sets_are_rejected(self):
        for count in (0, 21):
            with self.subTest(count=count):
                self.documents = candidate_documents(self.tool, unbound_count=count)
                with self.assertRaises(self.tool.DiagnosticError):
                    self.reference()
        self.documents = candidate_documents(self.tool, unbound_count=20)
        self.assertEqual(len(self.reference()["positions"]), 20)

    def test_candidate_reader_keeps_shared_archive_member_guards(self):
        extra = tarfile.TarInfo("synthetic-readback/raw-provider.json")
        raw = json.dumps({"secret": SECRET}).encode()
        extra.size = len(raw)
        HELPERS.write_archive(self.archive, self.documents, extras=[(extra, raw)])
        with self.assertRaises(self.tool.DiagnosticError):
            self.tool.read_source_coverage_reference(self.archive)

    def test_existing_three_payloads_remain_byte_identical(self):
        for name, expected in FROZEN_PAYLOADS.items():
            with self.subTest(payload=name):
                self.assertEqual(
                    hashlib.sha256(getattr(self.tool, name).encode()).hexdigest(), expected
                )


class CoverageHostTest(SourceCoverageFixture):
    def invoke(self, *, bad_archive=False, changed_installation=False, read_failure=False):
        HELPERS.write_archive(self.archive, self.documents)
        if bad_archive:
            self.archive.write_bytes(b"not-an-archive")
        home = Path(tempfile.mkdtemp(prefix="synthetic-home-", dir=self.tmp.name))
        installation = copy.deepcopy(self.documents["installation-before.json"])
        installation["version"] = "1.5.54"
        installation["commit"] = "b" * 40
        installation["containers"]["backend"]["id"] = "b" * 64
        after = copy.deepcopy(installation)
        if changed_installation:
            after["containers"]["backend"]["id"] = "c" * 64
        fake_result = {"synthetic_bound_read": True, "status": COMPLETE}
        stdout, stderr = io.StringIO(), io.StringIO()
        old_umask = os.umask(0o077)
        try:
            with (
                patch.object(self.tool.Path, "home", return_value=home),
                # Only the isolated test HOME is exempted from the outside-Git guard.
                patch.object(self.tool, "outside_git", return_value=True),
                patch.object(
                    self.tool, "read_installation", side_effect=[installation, after]
                ) as installations,
                patch.object(self.tool, "require_no_pending"),
                patch.object(
                    self.tool, "collect_schema", return_value=self.documents["schema.json"]
                ),
                patch.object(
                    self.tool,
                    "collect_source_coverage_read",
                    side_effect=RuntimeError(SECRET) if read_failure else None,
                    return_value=fake_result,
                ) as coverage_read,
                patch.object(
                    self.tool,
                    "source_coverage_complete",
                    side_effect=lambda value, _ref: value == fake_result,
                ),
                patch.object(
                    self.tool,
                    "collect_monitoring",
                    side_effect=AssertionError("No broad collector"),
                ),
                patch.object(
                    self.tool, "collect_source_gap", side_effect=AssertionError("No P02 collector")
                ),
                patch.object(
                    self.tool, "run_command", side_effect=AssertionError("No live commands")
                ),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                code = self.tool.main(
                    ["--base", str(home / "Boerse"), "--source-coverage-from", str(self.archive)]
                )
        finally:
            os.umask(old_umask)
        output = next(path for path in home.glob("trading-workspace-diagnose.*") if path.is_dir())
        console = stdout.getvalue() + stderr.getvalue()
        self.assertNotIn(SECRET, console)
        for path in output.glob("*.json"):
            self.assertNotIn(SECRET, path.read_text())
        return code, output, console, installations, coverage_read

    def test_new_mode_collects_only_archived_candidates_into_a_private_bundle(self):
        code, output, console, _, read = self.invoke()
        self.assertEqual(code, 0, console)
        self.assertEqual(read.call_args.args[0], "b" * 64)
        reference = read.call_args.args[1]
        self.assertEqual(
            {row["position_label"] for row in reference["positions"]}, {"P01", "P03", "P04"}
        )
        self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o700)
        self.assertEqual(
            {path.name for path in output.iterdir()},
            {
                "installation-before.json",
                "installation-after.json",
                "schema.json",
                "source-coverage-private.json",
                "summary.json",
            },
        )
        for path in (*output.iterdir(), output.with_name(output.name + ".tar.gz")):
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        summary = json.loads((output / "summary.json").read_text())
        self.assertTrue(summary["transport_complete"])
        self.assertNotIn(uid(1), console)
        self.assertNotIn("DE0000000001", console)

    def test_invalid_archive_stops_before_installation_read_and_preserves_error_bundle(self):
        code, output, _, installations, read = self.invoke(bad_archive=True)
        self.assertEqual(code, 2)
        installations.assert_not_called()
        read.assert_not_called()
        self.assertTrue(output.with_name(output.name + ".tar.gz").is_file())
        self.assertFalse(json.loads((output / "summary.json").read_text())["transport_complete"])

    def test_changed_installation_or_read_failure_never_becomes_complete(self):
        for failure in ("installation", "read"):
            with self.subTest(failure=failure):
                code, output, *_ = self.invoke(
                    changed_installation=failure == "installation",
                    read_failure=failure == "read",
                )
                self.assertEqual(code, 2)
                summary = json.loads((output / "summary.json").read_text())
                self.assertFalse(summary["transport_complete"])
                self.assertTrue(output.with_name(output.name + ".tar.gz").is_file())

    def test_cli_conflicts_and_position_label_without_gap_do_not_collect(self):
        cases = (
            ["--source-coverage-from", "a.tar.gz", "--source-gap-from", "b.tar.gz"],
            ["--source-coverage-from", "a.tar.gz", "--position-label", "P01"],
        )
        for argv in cases:
            with self.subTest(argv=argv):
                old_umask = os.umask(0o077)
                try:
                    with (
                        patch.object(self.tool, "collect_source_coverage") as collect,
                        patch.object(self.tool, "collect_source_gap") as gap,
                        patch.object(self.tool, "read_installation") as installation,
                        patch.object(self.tool, "run_command") as command,
                        patch.object(self.tool.Path, "home", return_value=Path(self.tmp.name)),
                        patch.object(self.tool, "outside_git", return_value=True),
                        redirect_stdout(io.StringIO()),
                        redirect_stderr(io.StringIO()),
                    ):
                        try:
                            code = self.tool.main(argv)
                        except SystemExit as error:
                            code = error.code
                        self.assertEqual(code, 2)
                        collect.assert_not_called()
                        gap.assert_not_called()
                        installation.assert_not_called()
                        command.assert_not_called()
                finally:
                    os.umask(old_umask)

    def test_payload_command_is_constant_and_private_reference_uses_only_stdin(self):
        reference = self.reference()
        captured = {}

        def command(args, **kwargs):
            captured.update(args=args, **kwargs)
            return json.dumps({"synthetic": True})

        with (
            patch.object(self.tool, "run_command", side_effect=command),
            patch.object(self.tool, "source_coverage_complete", return_value=True),
        ):
            self.tool.collect_source_coverage_read("a" * 64, reference)
        self.assertEqual(
            captured["args"][-4:], ["python", "-B", "-c", self.tool.SOURCE_COVERAGE_PAYLOAD]
        )
        self.assertEqual(json.loads(captured["input_text"]), reference)
        self.assertNotIn(uid(1), " ".join(captured["args"]))


@unittest.skipUnless(HAS_BACKEND, "Payload requires the actual Python 3.12 backend contracts")
class CoveragePayloadTest(SourceCoverageFixture):
    def run_payload(self, *, change=None, fail=None, with_document=False):
        import httpx
        import sqlalchemy.ext.asyncio as sa_async
        from app.core import config
        from app.features.market.persistence.models import UnderlyingModel
        from app.features.market_data.persistence.models import PositionQuoteSourceSelectionModel
        from app.features.market_data.persistence.position_quote_source import (
            PositionQuoteSourceSelectionRepository,
        )
        from app.features.position_monitoring.persistence.indicative_entry import (
            IndicativeEntryAssessmentModel,
        )
        from app.features.position_monitoring.service import indicative_entry
        from app.features.product.domain.price_scale_evidence import ProductPriceScaleBinding
        from app.features.product.domain.review_evidence import (
            ProductReviewAcquisitionState,
            ProductReviewEvidence,
        )
        from app.features.product.persistence.models import WarrantModel
        from app.features.product.persistence.review_evidence import ProductReviewDocumentModel
        from app.features.product.service import review_evidence
        from app.features.product.service.review_acquisition import ProductReviewReadiness
        from app.features.trade_position.persistence.repositories import (
            SqlAlchemyPositionRepository,
            SqlAlchemyReadOnlyTradeRepository,
        )
        from sqlalchemy.dialects import postgresql

        reference = self.reference()
        namespace = {"__name__": "_source_coverage_payload_test"}
        exec(
            compile(self.tool.SOURCE_COVERAGE_PAYLOAD, "<synthetic-source-coverage>", "exec"),
            namespace,
        )
        namespace["validate_reference"](reference)
        responses = coverage_responses(reference)
        stamp = datetime.fromisoformat(TIME.replace("Z", "+00:00"))
        trades, positions, warrants, selections, assessments, current_assessments = (
            {},
            {},
            {},
            {},
            {},
            {},
        )
        for target in reference["positions"]:
            binding = target["binding"]
            ids = {
                key: UUID(binding[key])
                for key in (
                    "workspace_id",
                    "trade_id",
                    "position_id",
                    "warrant_id",
                    "underlying_id",
                )
            }
            number = ids["position_id"].int
            trades[ids["trade_id"]] = SimpleNamespace(
                id=ids["trade_id"],
                workspace_id=ids["workspace_id"],
                product_id=ids["warrant_id"],
                cancelled_at=None,
            )
            positions[ids["trade_id"]] = SimpleNamespace(
                id=ids["position_id"],
                trade_id=ids["trade_id"],
                product_id=ids["warrant_id"],
                is_closed=False,
                closed_at=None,
                open_quantity=1,
            )
            warrants[ids["warrant_id"]] = SimpleNamespace(
                id=ids["warrant_id"],
                workspace_id=ids["workspace_id"],
                isin=binding["isin"],
                wkn=binding["wkn"],
                underlying_id=ids["underlying_id"],
            )
            selected = target["selection"]
            if selected["id"] is not None:
                candidate = {
                    "provider": "EODHD",
                    "listing_id": uid(1000 + number),
                    "mapping_id": uid(2000 + number),
                    "mapping_version": 1,
                    "identity_key": "c" * 64,
                    "currency": "EUR",
                    "mic": "XFRA",
                    "provider_exchange_code": "F",
                    "raw_provider_response": SECRET,
                }
                selections[ids["position_id"]] = SimpleNamespace(
                    id=UUID(selected["id"]),
                    workspace_id=ids["workspace_id"],
                    position_id=ids["position_id"],
                    selection_status=selected["selection_status"],
                    selection_reason=selected["selection_reason"],
                    policy_version=selected["policy_version"],
                    selected_at=stamp,
                    provider=None,
                    warrant_listing_id=None,
                    warrant_provider_mapping_id=None,
                    mapping_version=None,
                    identity_key=None,
                    superseded_at=None,
                    evidence={
                        "warrant_id": binding["warrant_id"],
                        "allowed_providers": ["EODHD"],
                        "verified_candidates": [candidate],
                        "allowed_candidates": [candidate],
                        "eligible_candidates": [],
                        "unrelated_raw_field": SECRET,
                    },
                )
            archived = target["assessment"]
            if archived is not None:
                old = SimpleNamespace(
                    id=UUID(archived["id"]),
                    workspace_id=ids["workspace_id"],
                    trade_id=ids["trade_id"],
                    position_id=ids["position_id"],
                    rule_version=archived["rule_version"],
                    previous_assessment_id=None,
                    evaluated_at=stamp,
                    recorded_at=stamp,
                    ordering_at=None,
                    outcome=archived["outcome"],
                    owner_basis_id=archived["owner_basis_id"],
                    input_fingerprint="f" * 64,
                    inputs={
                        "warrant_isin": binding["isin"],
                        "quote": {"reasons": ["OLD_NO_SOURCE"]},
                    },
                    result={"reasons": archived["reasons"]},
                )
                assessments[old.id] = old
            current_assessments[ids["position_id"]] = SimpleNamespace(
                id=UUID(int=1800 + number),
                workspace_id=ids["workspace_id"],
                trade_id=ids["trade_id"],
                position_id=ids["position_id"],
                rule_version="indicative-entry-review-v2",
                previous_assessment_id=None,
                evaluated_at=stamp,
                recorded_at=stamp,
                ordering_at=None,
                outcome="UNAVAILABLE",
                owner_basis_id="d" * 64,
                input_fingerprint="e" * 64,
                inputs={
                    "warrant_isin": binding["isin"],
                    "saved_quote": {"refresh_error": SECRET},
                    "quote": {"reasons": ["CURRENT_NO_SOURCE"]},
                    "product_scale": {"source_reference": "https://invalid.example/?key=" + SECRET},
                    "unexpected_raw_payload": SECRET,
                },
                result={"reasons": ["SYNTHETIC_CURRENT_NO_SOURCE"]},
            )
        first_trade = UUID(uid(101))
        if change == "missing_trade":
            trades.pop(first_trade)
        elif change == "missing_position":
            positions.pop(first_trade)
        elif change == "closed":
            positions[first_trade].is_closed = True
            positions[first_trade].closed_at = stamp
            positions[first_trade].open_quantity = 0
        elif change == "cancelled":
            trades[first_trade].cancelled_at = stamp
        elif change == "product":
            warrants[UUID(uid(201))].isin = "DE0000000999"
        elif change == "position":
            positions[first_trade].id = UUID(uid(999))
        elif change == "old_assessment":
            assessments[UUID(uid(803))].trade_id = UUID(uid(999))
        elif change == "new_selection":
            selected_at = stamp.replace(day=3)
            candidate = {
                "provider": "EODHD",
                "listing_id": uid(4201),
                "mapping_id": uid(5201),
                "mapping_version": 1,
                "identity_key": "c" * 64,
                "currency": "EUR",
                "mic": "XFRA",
                "provider_exchange_code": "F",
            }
            selections[UUID(uid(1))] = SimpleNamespace(
                id=UUID(uid(1601)),
                workspace_id=UUID(uid(10)),
                position_id=UUID(uid(1)),
                selection_status="SELECTED",
                selection_reason="UNIQUE_VERIFIED_ROUTE",
                policy_version="POSITION_QUOTE_SOURCE_POLICY_V1",
                selected_at=selected_at,
                provider="EODHD",
                warrant_listing_id=UUID(uid(4201)),
                warrant_provider_mapping_id=UUID(uid(5201)),
                mapping_version=1,
                identity_key="c" * 64,
                superseded_at=None,
                evidence={
                    "warrant_id": uid(201),
                    "allowed_providers": ["EODHD"],
                    "verified_candidates": [candidate],
                    "allowed_candidates": [candidate],
                    "eligible_candidates": [candidate],
                },
            )
            row = next(
                item for item in responses["positions"]["items"] if item["position_id"] == uid(1)
            )
            row.update(
                selection_id=uid(1601),
                selection_status="SELECTED",
                selection_reason="UNIQUE_VERIFIED_ROUTE",
                policy_version="POSITION_QUOTE_SOURCE_POLICY_V1",
                selected_at=selected_at.isoformat(),
                selected_provider="EODHD",
                warrant_listing_id=uid(4201),
                mapping_id=uid(5201),
                mapping_status="ACTIVE",
                mapping_version=2,
                provider_exchange_code="F",
                mic="XFRA",
                currency="EUR",
                source_health="MAPPING_CONFLICT",
            )
        calls, engine_options, session_options, client_options = [], {}, {}, {}
        database_url = "postgresql+asyncpg://synthetic:" + SECRET + "@unreachable.example/test"

        class Connection:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                calls.append("CONNECTION_CLOSED")

            async def execute(self, statement):
                sql = str(statement)
                calls.append(sql)
                if sql.startswith("SELECT current_setting"):
                    values = ("off" if fail == "readonly" else "on", "repeatable read")
                    return SimpleNamespace(one=lambda: values)
                if sql not in {
                    "BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY",
                    "ROLLBACK",
                    "SET LOCAL statement_timeout = '10s'",
                    "SET LOCAL lock_timeout = '2s'",
                }:
                    raise AssertionError("Unexpected SQL: " + sql)
                return None

        class Engine:
            def connect(self):
                return Connection()

            async def dispose(self):
                calls.append("ENGINE_DISPOSED")

        def check_select(statement):
            compiled = statement.compile(dialect=postgresql.dialect())
            sql = str(compiled)
            self.assertTrue(statement.is_select)
            self.assertNotIn("FOR UPDATE", sql.upper())
            self.assertIn(UUID(uid(10)), compiled.params.values())
            calls.append("OWNER_SELECT")
            return statement.column_descriptions[0]["entity"], compiled.params

        class Session:
            def __init__(self, **kwargs):
                session_options.update(kwargs)

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                calls.append("SESSION_CLOSED")

            async def scalar(self, statement):
                entity, parameters = check_select(statement)
                if entity is WarrantModel:
                    return next(
                        (row for key, row in warrants.items() if key in parameters.values()), None
                    )
                if entity is UnderlyingModel:
                    return SimpleNamespace(isin="US0000000001")
                raise AssertionError("Unexpected scalar owner")

            async def scalars(self, statement):
                entity, parameters = check_select(statement)
                if entity is not PositionQuoteSourceSelectionModel:
                    raise AssertionError("Unexpected selection owner")
                row = next(
                    (row for key, row in selections.items() if key in parameters.values()), None
                )
                return SimpleNamespace(one_or_none=lambda: row)

            async def get(self, entity, key):
                if entity is IndicativeEntryAssessmentModel:
                    return assessments.get(key)
                if entity is PositionQuoteSourceSelectionModel:
                    return next((row for row in selections.values() if row.id == key), None)
                raise AssertionError("Unexpected primary-key owner")

            async def rollback(self):
                calls.append("SESSION_ROLLBACK")

            async def commit(self):
                raise AssertionError("No commit allowed")

            async def flush(self):
                raise AssertionError("No flush allowed")

        async def trade_read(_self, workspace_id, trade_id):
            self.assertEqual(workspace_id, UUID(uid(10)))
            calls.append("TRADE_READ")
            if fail == "owner":
                raise RuntimeError(database_url)
            return trades.get(trade_id)

        async def position_read(_self, workspace_id, trade_id):
            self.assertEqual(workspace_id, UUID(uid(10)))
            calls.append("POSITION_READ")
            return positions.get(trade_id)

        async def latest_read(_session, workspace_id, position_id):
            self.assertEqual(workspace_id, UUID(uid(10)))
            return current_assessments.get(position_id)

        async def review_read(_self, *, workspace_id, warrant_id, known_at):
            calls.append(("PRODUCT_REVIEW", str(warrant_id)))
            if with_document:
                document = stored_document(workspace_id, warrant_id)
                warrant = warrants[warrant_id]
                return ProductReviewEvidence(
                    workspace_id,
                    warrant_id,
                    known_at,
                    "AVAILABLE",
                    (),
                    document.id,
                    document.recorded_at,
                    "a" * 64,
                    binding=ProductPriceScaleBinding(
                        warrant_id,
                        warrant.isin,
                        UUID(uid(700)),
                        warrant.underlying_id,
                        document.terms_id,
                    ),
                    currency="EUR",
                    unit="CURRENCY_PER_WARRANT",
                    source_reference=document.source_reference,
                    source_document_sha256=document.document_sha256,
                    reference_venue_mic="XETR",
                )
            return ProductReviewEvidence(
                workspace_id,
                warrant_id,
                known_at,
                "MISSING",
                ("PRODUCT_REVIEW_DOCUMENT_MISSING",),
                None,
                None,
                "a" * 64,
            )

        async def acquisition_read(_self, **_kwargs):
            return ProductReviewAcquisitionState(
                "FAILED", stamp, stamp, ("SYNTHETIC_DOCUMENT_GAP",)
            )

        def stored_document(workspace_id, warrant_id):
            document = b"synthetic-original-document-" + SECRET.encode()
            return ProductReviewDocumentModel(
                id=UUID(uid(900 + warrant_id.int)),
                workspace_id=workspace_id,
                warrant_id=warrant_id,
                terms_id=UUID(uid(3000 + warrant_id.int)),
                kind="KID",
                revision_number=1,
                recorded_at=stamp,
                retrieved_at=stamp,
                source_reference="https://issuer.example.invalid/kid?token=" + SECRET,
                document_sha256=hashlib.sha256(document).hexdigest(),
                document=document,
                binding={"warrant_id": str(warrant_id)},
                facts={
                    "isin": warrants[warrant_id].isin,
                    "underlying_isin": "US0000000001",
                    "currency": "EUR",
                    "unit": "CURRENCY_PER_WARRANT",
                    "reference_venue_mic": "XETR",
                    "issues": [],
                    "unexpected_document_fact": SECRET,
                },
                parser_version="current-product-document-v2",
            )

        async def document_read(_session, **kwargs):
            if with_document:
                self.assertEqual(kwargs["kind"], "KID")
                return stored_document(kwargs["workspace_id"], kwargs["warrant_id"])
            return None

        request_counts = {"positions": 0, "products": 0}

        def handler(request):
            self.assertEqual(request.method, "GET")
            self.assertEqual(request.url.host, "127.0.0.1")
            self.assertEqual(request.url.port, 8000)
            self.assertIn(
                request.url.path,
                {
                    "/api/v1/market-data/positions/quote-coverage",
                    "/api/v1/market-data/warrants/quote-coverage",
                },
            )
            kind = "positions" if "/positions/" in request.url.path else "products"
            request_counts[kind] += 1
            calls.append(("GET", request.url.path))
            if fail == "http":
                return httpx.Response(503, text=SECRET)
            body = copy.deepcopy(responses[kind])
            identity_key = "position_id" if kind == "positions" else "warrant_id"
            removed = uid(1 if kind == "positions" else 201)
            if change in {"closed", "cancelled", "missing_trade", "missing_position"}:
                body["items"] = [row for row in body["items"] if row[identity_key] != removed]
                if kind == "positions":
                    body["summary"]["open_positions"] -= 1
            if change == "coverage_binding" and kind == "positions" and request_counts[kind] == 2:
                row = next(row for row in body["items"] if row["position_id"] == uid(1))
                row["selection_reason"] = "CHANGED_DURING_COLLECTION"
            if change == "quote_only" and kind == "products" and request_counts[kind] == 2:
                row = next(item for item in body["items"] if item["warrant_id"] == uid(203))
                row["routes"][0]["bid"] = "1.25"
                row["routes"][0]["refresh_error"] = "SYNTHETIC_NEW_QUOTE_FACT"
            if fail == "dto":
                body["items"][0][identity_key] = SECRET
            return httpx.Response(200, json=body)

        real_client = httpx.AsyncClient

        def client_factory(**kwargs):
            client_options.update(kwargs)
            return real_client(transport=httpx.MockTransport(handler), **kwargs)

        def engine_factory(url, **kwargs):
            self.assertEqual(url, database_url)
            engine_options.update(kwargs)
            return Engine()

        previous_logging = logging.root.manager.disable
        with ExitStack() as stack:
            stack.enter_context(
                patch.object(
                    config, "get_settings", return_value=SimpleNamespace(database_url=database_url)
                )
            )
            stack.enter_context(
                patch.object(sa_async, "create_async_engine", side_effect=engine_factory)
            )
            stack.enter_context(patch.object(sa_async, "AsyncSession", Session))
            stack.enter_context(patch.object(httpx, "AsyncClient", side_effect=client_factory))
            stack.enter_context(patch.object(SqlAlchemyReadOnlyTradeRepository, "get", trade_read))
            stack.enter_context(
                patch.object(SqlAlchemyPositionRepository, "get_for_trade", position_read)
            )
            stack.enter_context(
                patch.object(indicative_entry, "latest_indicative_assessment", latest_read)
            )
            stack.enter_context(
                patch.object(
                    review_evidence.ProductReviewEvidenceReader, "current_for_review", review_read
                )
            )
            stack.enter_context(
                patch.object(
                    review_evidence.ProductReviewEvidenceReader,
                    "acquisition_state",
                    acquisition_read,
                )
            )
            stack.enter_context(patch.object(review_evidence, "latest_document", document_read))
            stack.enter_context(
                patch.object(
                    ProductReviewReadiness,
                    "prepare_for_review",
                    side_effect=AssertionError("No product acquisition"),
                )
            )
            stack.enter_context(
                patch.object(
                    PositionQuoteSourceSelectionRepository,
                    "active_for_position",
                    side_effect=AssertionError("No locking repository"),
                )
            )
            stack.enter_context(
                patch.object(socket.socket, "connect", side_effect=AssertionError("No network"))
            )
            result = asyncio.run(namespace["run_payload"](reference))
        self.assertEqual(logging.root.manager.disable, previous_logging)
        self.assertNotIn(SECRET, json.dumps(result))
        self.assertNotIn(database_url, json.dumps(result))
        self.assertNotIn("synthetic-unrelated-holding", json.dumps(result))
        return result, reference, calls, engine_options, session_options, client_options

    def test_real_dto_candidates_and_historical_decision_evidence_reach_the_bound_export(self):
        result, reference, calls, options, session_options, client_options = self.run_payload()
        self.assertEqual(result["status"], COMPLETE, result.get("read_error"))
        self.assertTrue(self.tool.source_coverage_complete(result, reference))
        self.assertEqual(
            {row["position_label"] for row in result["positions"]}, {"P01", "P03", "P04"}
        )
        third = next(row for row in result["positions"] if row["position_label"] == "P03")
        self.assertEqual(third["coverage_after"]["warrant"]["data"]["issuer"], "Synthetic issuer")
        routes = third["coverage_after"]["warrant"]["data"]["routes"]
        self.assertEqual(len(routes), 2)
        self.assertFalse(routes[0]["configured"])
        self.assertEqual(routes[1]["route_reason"], "MAPPING_NOT_VERIFIED")
        self.assertEqual(third["selection"]["evidence"]["allowed_providers"], ["EODHD"])
        self.assertEqual(third["selection"]["evidence"]["eligible_candidates"], [])
        self.assertEqual(len(third["selection"]["evidence"]["verified_candidates"]), 1)
        self.assertNotEqual(third["archived_assessment"]["id"], third["current_assessment"]["id"])
        self.assertEqual(third["current_assessment"]["scope"], "STORED_ASSESSMENT_NOT_REEVALUATION")
        self.assertEqual(third["product_review"]["status"], "MISSING")
        self.assertIn("NOT_RULE_QUALIFICATION", result["status"])
        database_calls = [item for item in calls if isinstance(item, str)]
        self.assertEqual(database_calls[-3:], ["ROLLBACK", "CONNECTION_CLOSED", "ENGINE_DISPOSED"])
        self.assertIn("SESSION_ROLLBACK", calls)
        self.assertFalse(options["echo"])
        self.assertEqual(options["isolation_level"], "AUTOCOMMIT")
        self.assertEqual(
            options["connect_args"]["server_settings"]["default_transaction_read_only"], "on"
        )
        self.assertFalse(session_options["autoflush"])
        self.assertFalse(client_options["trust_env"])
        self.assertFalse(client_options["follow_redirects"])

    def test_present_kid_metadata_matches_review_revision_without_exporting_document_or_url(self):
        result, reference, *_ = self.run_payload(with_document=True)
        self.assertEqual(result["status"], COMPLETE, result.get("read_error"))
        self.assertTrue(self.tool.source_coverage_complete(result, reference))
        for row in result["positions"]:
            with self.subTest(position_label=row["position_label"]):
                kid = row["kid_metadata"]
                self.assertEqual(kid["status"], "PRESENT")
                self.assertEqual(kid["id"], row["product_review"]["revision_id"])
                self.assertEqual(kid["scope"], "STORED_KID_METADATA_NO_DOCUMENT_BYTES")
                self.assertEqual(kid["kind"], "KID")
                self.assertEqual(kid["revision_number"], 1)
                self.assertEqual(kid["parser_version"], "current-product-document-v2")
                self.assertEqual(kid["recorded_at"], row["product_review"]["recorded_at"])
                self.assertEqual(kid["retrieved_at"], kid["recorded_at"])
                self.assertEqual(
                    kid["document_sha256"],
                    hashlib.sha256(b"synthetic-original-document-" + SECRET.encode()).hexdigest(),
                )
                self.assertEqual(kid["facts"]["underlying_isin"], kid["current_underlying_isin"])
                self.assertEqual(kid["current_underlying_isin"], "US0000000001")
                self.assertTrue(kid["source_reference_present"])
                self.assertEqual(
                    kid["source_reference_sha256"],
                    hashlib.sha256(
                        ("https://issuer.example.invalid/kid?token=" + SECRET).encode()
                    ).hexdigest(),
                )
                self.assertNotIn("source_reference", kid)
                self.assertNotIn("document", kid)
                self.assertNotIn("unexpected_document_fact", kid["facts"])

    def test_absence_and_closed_states_are_distinct_observed_facts(self):
        for change, state, reason in (
            ("missing_trade", "MISSING", "REFERENCED_TRADE_NOT_FOUND"),
            ("missing_position", "MISSING", "REFERENCED_POSITION_NOT_FOUND"),
            ("closed", "CLOSED", "ARCHIVED_POSITION_AND_PRODUCT_MATCH"),
            ("cancelled", "CANCELLED", "ARCHIVED_POSITION_AND_PRODUCT_MATCH"),
        ):
            with self.subTest(change=change):
                result, *_ = self.run_payload(change=change)
                row = next(row for row in result["positions"] if row["position_label"] == "P01")
                self.assertEqual(row["position_state"]["status"], state)
                self.assertEqual(row["binding_status"], reason)
                self.assertEqual(
                    row["coverage_before"]["position"]["status"], "NOT_IN_OPEN_POSITION_REPORT"
                )

    def test_changed_product_or_position_never_attaches_foreign_product_evidence(self):
        for change in ("product", "position"):
            with self.subTest(change=change):
                result, reference, calls, *_ = self.run_payload(change=change)
                row = next(row for row in result["positions"] if row["position_label"] == "P01")
                self.assertIn(
                    row["binding_status"],
                    {"CURRENT_POSITION_BINDING_CHANGED", "CURRENT_PRODUCT_BINDING_CHANGED"},
                )
                self.assertIsNone(row["product_review"])
                self.assertNotIn(("PRODUCT_REVIEW", uid(201)), calls)
                self.assertFalse(self.tool.source_coverage_complete(result, reference))

    def test_reference_and_in_collection_binding_changes_are_not_transport_success(self):
        for change in ("old_assessment", "coverage_binding"):
            with self.subTest(change=change):
                result, reference, *_ = self.run_payload(change=change)
                self.assertNotEqual(result["status"], COMPLETE)
                self.assertFalse(self.tool.source_coverage_complete(result, reference))
        result, reference, *_ = self.run_payload(change="quote_only")
        self.assertEqual(result["status"], COMPLETE)
        self.assertTrue(self.tool.source_coverage_complete(result, reference))
        third = next(row for row in result["positions"] if row["position_label"] == "P03")
        self.assertIsNone(third["coverage_before"]["warrant"]["data"]["routes"][0]["bid"])
        self.assertEqual(third["coverage_after"]["warrant"]["data"]["routes"][0]["bid"], "1.25")

    def test_new_selection_retains_current_mapping_conflict_without_rebinding_archive(self):
        result, reference, *_ = self.run_payload(change="new_selection")
        self.assertEqual(result["status"], COMPLETE)
        self.assertTrue(self.tool.source_coverage_complete(result, reference))
        first = next(row for row in result["positions"] if row["position_label"] == "P01")
        self.assertEqual(first["archived_selection"]["status"], "NOT_IN_REFERENCE")
        self.assertTrue(first["selection_changed_since_archive"])
        self.assertEqual(first["selection"]["selection_status"], "SELECTED")
        self.assertEqual(first["selection"]["mapping_version"], 1)
        current = first["coverage_after"]["position"]["data"]
        self.assertEqual(current["mapping_version"], 2)
        self.assertEqual(current["source_health"], "MAPPING_CONFLICT")

    def test_readonly_and_owner_failures_roll_back_and_redact(self):
        for failure in ("readonly", "owner", "http", "dto"):
            with self.subTest(failure=failure):
                result, reference, calls, *_ = self.run_payload(fail=failure)
                self.assertNotEqual(result["status"], COMPLETE)
                self.assertFalse(self.tool.source_coverage_complete(result, reference))
                self.assertIn("ROLLBACK", calls)
                self.assertIn("ENGINE_DISPOSED", calls)
                self.assertLess(calls.index("ROLLBACK"), calls.index("ENGINE_DISPOSED"))
                if failure == "readonly":
                    self.assertNotIn("TRADE_READ", calls)
                else:
                    self.assertIn("SESSION_ROLLBACK", calls)

    def test_host_rejects_incomplete_identity_or_snapshot_claims(self):
        result, reference, *_ = self.run_payload()
        for change in ("missing_position", "binding", "transaction", "scope"):
            value = copy.deepcopy(result)
            if change == "missing_position":
                value["positions"].pop()
            elif change == "binding":
                value["positions"][0]["binding"]["trade_id"] = uid(999)
            elif change == "transaction":
                value["transaction"]["read_only"] = "off"
            else:
                value["global_atomic_snapshot"] = True
            with self.subTest(change=change):
                self.assertFalse(self.tool.source_coverage_complete(value, reference))

    def test_host_rejects_incomplete_present_facts_and_false_stable_selection_claims(self):
        result, reference, *_ = self.run_payload(with_document=True)
        self.assertTrue(self.tool.source_coverage_complete(result, reference))
        for change in (
            "assessment_outcome",
            "assessment_owner_basis_id",
            "review_reasons",
            "review_revision_id",
            "acquisition_data",
            "kid_metadata",
            "selection_reason",
        ):
            value = copy.deepcopy(result)
            row = value["positions"][0]
            if change.startswith("assessment_"):
                row["current_assessment"].pop(change.removeprefix("assessment_"))
            elif change.startswith("review_"):
                row["product_review"].pop(change.removeprefix("review_"))
            elif change == "acquisition_data":
                row["acquisition"] = {"status": "PRESENT"}
            elif change == "kid_metadata":
                row["kid_metadata"] = {"status": "PRESENT"}
            else:
                row["coverage_after"]["position"]["data"][
                    "selection_reason"
                ] = "CHANGED_DURING_COLLECTION"
            with self.subTest(change=change):
                self.assertEqual(value["status"], COMPLETE)
                self.assertFalse(self.tool.source_coverage_complete(value, reference))
                with (
                    patch.object(self.tool, "run_command", return_value=json.dumps(value)),
                    self.assertRaisesRegex(
                        self.tool.DiagnosticError, "SOURCE_COVERAGE_RESPONSE_INVALID"
                    ),
                ):
                    self.tool.collect_source_coverage_read("a" * 64, reference)

    def test_host_preserves_bound_partial_facts_but_rejects_a_false_complete_claim(self):
        result, reference, *_ = self.run_payload(change="coverage_binding")
        self.assertEqual(result["status"], "INCOMPLETE_PASSIVE_SOURCE_COVERAGE_READ")
        self.assertNotIn("read_error", result)
        with patch.object(self.tool, "run_command", return_value=json.dumps(result)):
            received = self.tool.collect_source_coverage_read("a" * 64, reference)
        self.assertEqual(received, result)
        inconsistent = {**result, "status": COMPLETE}
        with (
            patch.object(self.tool, "run_command", return_value=json.dumps(inconsistent)),
            self.assertRaisesRegex(self.tool.DiagnosticError, "SOURCE_COVERAGE_RESPONSE_INVALID"),
        ):
            self.tool.collect_source_coverage_read("a" * 64, reference)

    def test_payload_calls_no_mutation_or_provider_owner(self):
        tree = ast.parse(self.tool.SOURCE_COVERAGE_PAYLOAD)
        forbidden = {
            "commit",
            "flush",
            "with_for_update",
            "begin_nested",
            "prepare_for_review",
            "active_for_position",
            "lock_open_position",
            "evaluate",
            "fetch",
        }
        calls = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        self.assertFalse(calls & forbidden)
        imports = {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        self.assertFalse(any(name.startswith("app.providers") for name in imports))


if __name__ == "__main__":
    unittest.main()
