"""Exercise the one-position handoff with fake owners, never a real PC or provider."""

from __future__ import annotations

import asyncio
import copy
import json
import runpy
import stat
import tempfile
import unittest
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID

ROOT = Path(__file__).resolve().parents[3]
TOOL = runpy.run_path(str(ROOT / "scripts/read-p01-gettex-binding.py"))
COLLECTOR = runpy.run_path(str(ROOT / "scripts/collect-depot-data-supply.py"))
SECRET = "synthetic-provider-secret-never-export"


def reference() -> dict:
    return {
        "schema": "PRIVATE_DEPOT_SOURCE_COVERAGE_REFERENCE_V1",
        "archive_sha256": "a" * 64,
        "monitoring_sha256": "b" * 64,
        "archived_read_at": "2026-11-24T19:33:58+00:00",
        "installation": {"commit": "c" * 40, "version": "1.5.54"},
        "schema_versions": ["20261118_0060"],
        "positions": [
            {
                "position_label": "P01",
                "binding": {
                    "workspace_id": "00000000-0000-4000-8000-000000000001",
                    "trade_id": str(UUID(int=2)),
                    "position_id": str(UUID(int=3)),
                    "warrant_id": str(UUID(int=4)),
                    "underlying_id": str(UUID(int=5)),
                    "isin": "DE000AA00001",
                    "wkn": "AA0000",
                },
                "selection": {
                    key: None
                    for key in (
                        "id",
                        "selection_status",
                        "selection_reason",
                        "policy_version",
                        "selected_at",
                        "provider",
                    )
                },
                "assessment": None,
            }
        ],
    }


def backend_namespace() -> dict:
    namespace = {
        "__name__": "test_p01_extension",
        "COLLECTOR_PAYLOAD": COLLECTOR["SOURCE_COVERAGE_PAYLOAD"],
    }
    exec(TOOL["OWNER_EXTENSION"], namespace)
    return namespace


class P01HandoffTest(unittest.TestCase):
    def test_archived_label_isolated_before_backend_and_no_current_relabelling(self) -> None:
        original = reference()
        other = copy.deepcopy(original["positions"][0])
        other.update(position_label="P02")
        other["binding"].update(position_id=str(UUID(int=99)), trade_id=str(UUID(int=98)))
        original["positions"].insert(0, other)
        reader = Mock(return_value=original)
        result = TOOL["p01_reference"](
            {"read_source_coverage_reference": reader}, Path("/old.tar.gz")
        )
        self.assertEqual(result["positions"], reference()["positions"])
        self.assertEqual(result["archive_sha256"], original["archive_sha256"])
        self.assertEqual(len(original["positions"]), 2)
        payload = TOOL["backend_payload"](COLLECTOR, result)
        self.assertNotIn(str(UUID(int=99)), payload)
        compile(payload, "private-backend-input", "exec")
        for invalid in ([], [other], [*result["positions"], *result["positions"]]):
            reader.return_value = {**original, "positions": invalid}
            with self.assertRaisesRegex(TOOL["ReadError"], "EXACTLY_ONE_ARCHIVED_P01_REQUIRED"):
                TOOL["p01_reference"](
                    {"read_source_coverage_reference": reader}, Path("/old.tar.gz")
                )

    def test_binding_mismatch_never_expands_owner_reads(self) -> None:
        namespace = backend_namespace()
        namespace["original_read"] = AsyncMock(
            return_value={"binding_status": "CURRENT_PRODUCT_BINDING_CHANGED"}
        )
        namespace["add_owner_context"] = AsyncMock(side_effect=AssertionError("must not read"))
        result = asyncio.run(
            namespace["read_owner_position"](
                object(), reference()["positions"][0], datetime.now(UTC)
            )
        )
        self.assertEqual(result["binding_status"], "CURRENT_PRODUCT_BINDING_CHANGED")
        namespace["add_owner_context"].assert_not_awaited()

    def test_backend_keeps_single_reference_and_existing_read_only_transaction(self) -> None:
        namespace = backend_namespace()
        seen = []

        async def fake_database(ref, result):
            seen.extend(ref["positions"])
            self.assertIs(
                namespace["helpers"]["read_bound_position"], namespace["read_owner_position"]
            )
            result.update(database_read_complete=True)

        namespace["helpers"]["read_database"] = fake_database
        result = asyncio.run(namespace["run_read"](reference()))
        self.assertTrue(result["database_read_complete"])
        self.assertEqual(seen, reference()["positions"])
        invalid = reference()
        invalid["positions"][0]["position_label"] = "P02"
        with self.assertRaisesRegex(Exception, "EXACTLY_ONE_ARCHIVED_P01_REQUIRED"):
            asyncio.run(namespace["run_read"](invalid))
        self.assertEqual(len(seen), 1)

    def test_actual_owner_callback_whitelists_private_settings_and_revision_output(self) -> None:
        namespace = backend_namespace()
        binding = reference()["positions"][0]["binding"]
        wid, pid = UUID(binding["workspace_id"]), UUID(binding["warrant_id"])
        active = SimpleNamespace(value="ACTIVE")
        product = SimpleNamespace(
            id=pid,
            workspace_id=wid,
            issuer_id=UUID(int=6),
            underlying_id=UUID(int=5),
            isin=binding["isin"],
            wkn=binding["wkn"],
            product_family="WARRANT",
            lifecycle_status=active,
            version=7,
        )
        terms = SimpleNamespace(
            id=UUID(int=7),
            warrant_id=pid,
            version_no=4,
            effective_from=datetime.now(UTC),
            effective_to=None,
            option_direction="CALL",
            strike="1.0",
            strike_currency_code="USD",
            maturity_date="2027-01-01",
            ratio="0.1",
        )
        venue = SimpleNamespace(id=UUID(int=8), mic="MUND", is_active=True, version=2)
        listing = SimpleNamespace(
            id=UUID(int=9),
            workspace_id=wid,
            warrant_id=pid,
            trading_venue_id=venue.id,
            symbol=None,
            quotation_currency_code="EUR",
            lifecycle_status=active,
            version=3,
        )
        settings = SimpleNamespace(
            market_data=SimpleNamespace(
                gettex_delayed=SimpleNamespace(
                    enabled=True,
                    private_use_confirmed=True,
                    timeout_seconds=180,
                    max_download_bytes=1024,
                    fallback_windows=8,
                    unavailable_retry_seconds=60,
                    feed_delay_seconds=900,
                    api_key=SECRET,
                ),
                refresh=SimpleNamespace(
                    workspace_id=wid,
                    enabled=True,
                    warrants_interval_seconds=300,
                    auto_configure=False,
                    auto_select_position_sources=True,
                    password=SECRET,
                ),
            ),
            position_monitoring=SimpleNamespace(
                enabled=True,
                review_scope="INDICATIVE_ENTRY_V2",
                interval_seconds=900,
                review_notifications_enabled=False,
                token=SECRET,
            ),
            database_url=SECRET,
        )
        owner = SimpleNamespace(
            get=AsyncMock(return_value=product),
            current_terms=AsyncMock(return_value=terms),
            listings=AsyncMock(return_value=[listing]),
        )
        market = SimpleNamespace(
            find_trading_venue_by_mic=AsyncMock(return_value=venue),
            get_trading_venue=AsyncMock(return_value=venue),
        )
        revision_reader = SimpleNamespace(latest=AsyncMock(return_value=None))

        @dataclass
        class UnitRead:
            status: str = "MISSING"

        unit_reader = SimpleNamespace(current=AsyncMock(return_value=UnitRead()))
        modules = {
            "app.core.config": {"get_settings": lambda: settings},
            "app.features.market.persistence.repositories": {
                "SqlAlchemyReferenceDataRepository": lambda _: market
            },
            "app.features.product.domain.listing_unit_evidence": {
                "ListingUnitRoute": lambda *args: args
            },
            "app.features.product.persistence.listing_unit_evidence": {
                "ListingUnitEvidenceRepository": lambda _: revision_reader
            },
            "app.features.product.service.application": {"WarrantService": lambda _: owner},
            "app.features.product.service.listing_unit_evidence": {
                "ListingUnitEvidenceReader": lambda _: unit_reader
            },
        }
        fake_modules = {}
        for name, values in modules.items():
            module = ModuleType(name)
            module.__dict__.update(values)
            fake_modules[name] = module
        row = {}
        at = datetime.now(UTC)
        with patch.dict("sys.modules", fake_modules):
            asyncio.run(
                namespace["add_owner_context"](object(), reference()["positions"][0], at, row)
            )
        self.assertNotIn(SECRET, json.dumps(row, default=str))
        self.assertEqual(row["owner_context"]["terms"]["version_no"], 4)
        self.assertTrue(row["readiness"]["exactly_one_active_mund_eur_route"])
        self.assertFalse(row["readiness"]["mapping_preview_executed"])
        self.assertEqual(unit_reader.current.await_args.kwargs["event_at"], at)
        owner.get.assert_awaited_once_with(wid, pid)
        market.find_trading_venue_by_mic.assert_awaited_once_with("MUND")

    def test_modified_collector_rejected_before_its_code_can_execute(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            scripts = base / "trading-workspace-app/scripts"
            scripts.mkdir(parents=True)
            marker = base / "should-not-exist"
            (scripts / "collect-depot-data-supply.py").write_text(
                f"open({str(marker)!r}, 'w').close()"
            )
            with self.assertRaisesRegex(TOOL["ReadError"], "COLLECTOR_VERSION_MISMATCH"):
                TOOL["load_helpers"](base)
            self.assertFalse(marker.exists())

    def test_private_output_permissions_git_rejection_and_no_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            # The runner itself can place all writable temp paths inside Git.
            # Model the test's repository boundary, not that enclosing harness.
            with patch("os.path.lexists", lambda p: Path(p) == root / ".git" and Path(p).exists()):
                output = TOOL["create_output_dir"](COLLECTOR, str(root / "private"))
                COLLECTOR["write_json"](output / "result.json", {"private": True})
                self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o700)
                self.assertEqual(stat.S_IMODE((output / "result.json").stat().st_mode), 0o600)
                with self.assertRaises(FileExistsError):
                    TOOL["create_output_dir"](COLLECTOR, str(output))
                (root / ".git").mkdir()
                with self.assertRaisesRegex(
                    TOOL["ReadError"], "PRIVATE_OUTPUT_MUST_BE_OUTSIDE_GIT"
                ):
                    TOOL["create_output_dir"](COLLECTOR, str(root / "in-git"))

    def test_host_requires_matching_release_schema_and_unchanged_installation(self) -> None:
        before = {
            "commit": TOOL["EXPECTED_COMMIT"],
            "version": "1.5.55",
            "containers": {"backend": {"id": "a" * 64, "state": "running", "health": "healthy"}},
        }
        row = {
            "binding_status": "ARCHIVED_POSITION_AND_PRODUCT_MATCH",
            "binding": reference()["positions"][0]["binding"],
            "owner_context": {},
        }
        helpers = {
            **COLLECTOR,
            "read_installation": Mock(return_value=before),
            "collect_schema": Mock(return_value={"versions": TOOL["EXPECTED_SCHEMA"]}),
            "docker_prefix": Mock(return_value=["docker", "--host", "unix:///local.sock"]),
            "run_command": Mock(
                return_value=json.dumps(
                    {
                        "read_only": True,
                        "database_read_complete": True,
                        "transaction": {"read_only": "on", "isolation": "repeatable read"},
                        "positions": [row],
                    }
                )
            ),
        }
        result = TOOL["collect"](helpers, Path("/installation"), reference())
        self.assertTrue(result["read_complete"])
        helpers["read_installation"].side_effect = [before, {**before, "version": "1.5.56"}]
        self.assertFalse(
            TOOL["collect"](helpers, Path("/installation"), reference())["read_complete"]
        )
        helpers["read_installation"].side_effect = None
        helpers["run_command"].reset_mock()
        helpers["collect_schema"].return_value = {"versions": ["20261118_0060"]}
        with self.assertRaisesRegex(TOOL["ReadError"], "INSTALLED_SCHEMA_MISMATCH"):
            TOOL["collect"](helpers, Path("/installation"), reference())
        helpers["run_command"].assert_not_called()
        self.assertEqual(
            TOOL["error_code"](
                COLLECTOR["DiagnosticError"]("REFERENCE_MEMBERS_INCOMPLETE"), COLLECTOR
            ),
            "REFERENCE_MEMBERS_INCOMPLETE",
        )
        self.assertEqual(TOOL["error_code"](RuntimeError(SECRET), COLLECTOR), "RuntimeError")


if __name__ == "__main__":
    unittest.main()
