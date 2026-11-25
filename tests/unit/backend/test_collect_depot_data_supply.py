"""Exercise the diagnostic collector with synthetic state and intercepted commands.

No Docker daemon, backend, database, provider, or user installation is accessed.
The standard-library suite also runs without installing backend dependencies.
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
import re
import stat
import subprocess
import sys
import tarfile
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts/collect-depot-data-supply.py"
# Frozen Python heredoc from the reviewed 2026-11-20 diagnostic, docs head 134352a6.
REVIEWED_PAYLOAD_SHA256 = "b8dee0cd47ccd95a224cf5897eb60233d3195bf9d76700a103acfcfbc5dbafab"
REVISION = "a" * 40
TIME = "2026-11-21T08:00:00+00:00"
SECRET = "synthetic-private-api-key-$NEVER_COPY-this"
READ_NAMES = (
    "indicative-entry",
    "product-deadline-review",
    "hebeltrader-original-bid",
    "hebeltrader-targets",
    "hebeltrader-loss",
    "hebeltrader-evidence",
)


def load_tool() -> ModuleType:
    spec = importlib.util.spec_from_file_location("_depot_data_supply_test_tool", SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError("Collector module unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class CollectorContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tool = load_tool()

    def test_existing_get_payload_and_six_position_reads_are_preserved(self) -> None:
        payload = self.tool.BACKEND_PAYLOAD
        self.assertEqual(hashlib.sha256(payload.encode()).hexdigest(), REVIEWED_PAYLOAD_SHA256)
        tree = ast.parse(payload)
        reads = next(
            node.value
            for node in tree.body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "READS" for target in node.targets
            )
        )
        self.assertIsInstance(reads, ast.Tuple)
        self.assertEqual(
            [ast.literal_eval(row.elts[0]) for row in reads.elts],
            [
                "indicative-entry",
                "product-deadline-review",
                "hebeltrader-original-bid",
                "hebeltrader-targets",
                "hebeltrader-loss",
                "hebeltrader-evidence",
            ],
        )
        client_calls = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "client"
        }
        self.assertEqual(client_calls, {"get"})

    def test_host_imports_only_standard_library(self) -> None:
        tree = ast.parse(SCRIPT.read_text())
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        self.assertFalse(imports - sys.stdlib_module_names)


def monitoring_envelope() -> dict:
    """A host-envelope fixture, not a substitute for backend DTO/live qualification."""
    response = {"http_status": 200, "body": {}}
    value = {
        "schema": "PRIVATE_MONITORING_READBACK_2026_11_20",
        "requests": "GET_ONLY",
        "global_atomic_snapshot": False,
        "collection_status": "COMPLETE_PASSIVE_READBACK_NOT_RULE_QUALIFICATION",
        "started_at": TIME,
        "completed_at": TIME,
        "coverage_checks": {
            "positions_requested": 1,
            "inventory_schema_ids_and_counts_valid": True,
            "nonempty_portfolio_observed": True,
            "same_inventory_and_bindings": True,
            "same_idle_cycle_markers": True,
            "auxiliary_reads_available": True,
            "all_position_reads_available": True,
        },
        "positions": [
            {
                "identity_private": {"synthetic_private_position": "PRIVATE_POSITION"},
                "reads": {name: copy.deepcopy(response) for name in READ_NAMES},
            }
        ],
    }
    for name in (
        "runtime_before",
        "refresh_before",
        "inventory_before",
        "inventory_after",
        "refresh_after",
        "runtime_after",
    ):
        value[name] = copy.deepcopy(response)
    return value


class SyntheticInstallation:
    """A private disposable state; every external command must match a read allowlist."""

    def __init__(self, root: Path, tool: ModuleType) -> None:
        self.tool = tool
        self.home = root / "synthetic home"
        self.home.mkdir(mode=0o700)
        self.base = self.home / "Boerse with spaces"
        self.app = self.base / "trading-workspace-app"
        self.app.mkdir(parents=True)
        self.control = self.base / "trading-workspace-state"
        self.control.mkdir(mode=0o700)
        runs = self.control / "runs"
        runs.mkdir(mode=0o700)
        operation = runs / "synthetic-installed-release"
        operation.mkdir(mode=0o700)
        self.state = operation / "deployment"
        self.state.mkdir(mode=0o700)
        self.write(self.app / "VERSION", "1.5.52\n")
        self.write(self.control / "current-state", str(self.state) + "\n")
        self.write(self.state / "release-root", str(self.app) + "\n")
        self.write(self.state / "revision", REVISION + "\n")
        for marker in ("prepared", "deployed"):
            self.write(self.state / marker, "")
        # The collector has no reason to copy either credential-bearing file.
        self.write(self.state / "environment.env", "API_KEY=" + SECRET + "\n")
        self.write(self.state / "preserve.json", json.dumps({"secret": SECRET}))
        self.ids = dict(zip(tool.SERVICES, (digit * 64 for digit in "1234"), strict=True))
        self.images = {
            service: "sha256:" + digit * 64
            for service, digit in zip(tool.SERVICES, "5678", strict=True)
        }
        self.write(self.state / "database-container", self.ids["database"] + "\n")
        for service in tool.APP_SERVICES:
            self.write(self.state / (service + ".image"), self.images[service] + "\n")
        chain = (
            f"{self.app}/docker/compose.yml,{self.app}/docker/compose.issuer-monitoring.yml,"
            f"{self.state}/preserve.json"
        )
        self.containers = {
            service: {
                "id": self.ids[service],
                "name": f"/trading-workspace-{service}-1",
                "image_id": self.images[service],
                "project": "trading-workspace",
                "service": service,
                "config_files": chain,
                "state": "running",
                "started_at": TIME,
                "restart_count": 0,
                "health": "healthy",
            }
            for service in tool.SERVICES
        }
        self.calls: list[tuple[list[str], str | None]] = []
        self.head = REVISION
        self.image_revision = REVISION
        self.monitoring = monitoring_envelope()
        self.schema = {
            "source": "INSTALLED_BACKEND_DATABASE_CONFIGURATION",
            "read_only": True,
            "status": "READ_ONLY_SCHEMA_VERSION_OBSERVED",
            "started_at": TIME,
            "completed_at": TIME,
            "versions": ["20261118_0060"],
        }

    @staticmethod
    def write(path: Path, value: str) -> None:
        path.write_text(value)
        path.chmod(0o600)

    def command(self, args: list[str], *, input_text: str | None = None, timeout: int = 30) -> str:
        self.calls.append((args, input_text))
        if args[0] == "git":
            prefix = [
                "git",
                "--no-optional-locks",
                "-c",
                "core.fsmonitor=false",
                "-C",
                str(self.app),
            ]
            if args[: len(prefix)] != prefix or input_text is not None:
                raise AssertionError("Unapproved git invocation")
            operation = args[len(prefix) :]
            if operation == ["rev-parse", "--verify", "HEAD"]:
                return self.head + "\n"
            if operation == ["status", "--porcelain=v1", "--untracked-files=all"]:
                return ""
            if operation == ["show", "HEAD:VERSION"]:
                return "1.5.52\n"
            raise AssertionError("Mutating or unexpected git invocation")
        if args[:3] != ["docker", "--host", "unix:///synthetic-local-engine.sock"]:
            raise AssertionError("Non-local or unexpected command")
        operation = args[3:]
        if operation == [
            "ps",
            "--all",
            "--no-trunc",
            "--quiet",
            "--filter",
            "label=com.docker.compose.project=trading-workspace",
        ]:
            return "\n".join(self.ids.values())
        if operation[:4] == ["inspect", "--type", "container", "--format"]:
            if len(operation) != 6 or input_text is not None:
                raise AssertionError("Full/unscoped container inspection")
            template = operation[4]
            if any(value in template for value in (".Config.Env", ".Mounts", ".State.Health.Log")):
                raise AssertionError("Credential-bearing Docker inspection")
            container_id = operation[5]
            row = next(row for row in self.containers.values() if row["id"] == container_id)
            return json.dumps(row)
        if operation[:3] == ["image", "inspect", "--format"]:
            if len(operation) != 5 or input_text is not None:
                raise AssertionError("Full/unscoped image inspection")
            if ".Config.Env" in operation[3]:
                raise AssertionError("Credential-bearing image inspection")
            return json.dumps({"id": operation[4], "revision": self.image_revision})
        if operation == ["exec", "-i", self.ids["backend"], "python", "-B", "-"]:
            if input_text == self.tool.SCHEMA_PAYLOAD and timeout == 60:
                return json.dumps(self.schema)
            if input_text == self.tool.BACKEND_PAYLOAD and timeout == 900:
                return json.dumps(self.monitoring)
            raise AssertionError("Unapproved backend command/payload")
        raise AssertionError("Mutating or unexpected Docker invocation")

    def files(self) -> dict[str, bytes]:
        return {
            str(path.relative_to(self.base)): path.read_bytes()
            for path in self.base.rglob("*")
            if path.is_file()
        }


class CollectorHostTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tool = load_tool()
        temporary = tempfile.TemporaryDirectory(prefix="depot-collector-synthetic-")
        self.addCleanup(temporary.cleanup)
        self.installation = SyntheticInstallation(Path(temporary.name), self.tool)
        self.command_patch = patch.object(
            self.tool, "run_command", side_effect=self.installation.command
        )
        self.command_patch.start()
        self.addCleanup(self.command_patch.stop)
        local_docker = patch.object(
            self.tool,
            "docker_prefix",
            return_value=["docker", "--host", "unix:///synthetic-local-engine.sock"],
        )
        local_docker.start()
        self.addCleanup(local_docker.stop)
        no_live_commands = patch.object(
            subprocess, "run", side_effect=AssertionError("Live subprocess forbidden in tests")
        )
        no_live_commands.start()
        self.addCleanup(no_live_commands.stop)
        # This harness may itself run under an enclosing Git workspace. Model a
        # user's separate home; the real output-location rejection is tested below.
        output_location = patch.object(self.tool, "outside_git", return_value=True)
        output_location.start()
        self.addCleanup(output_location.stop)

    def invoke(self) -> tuple[int, Path, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        before = set(self.installation.home.iterdir())
        original_umask = os.umask(0o022)
        try:
            with (
                patch.object(self.tool.Path, "home", return_value=self.installation.home),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                code = self.tool.main(["--base", str(self.installation.base)])
        finally:
            os.umask(original_umask)
        new = set(self.installation.home.iterdir()) - before
        directories = [path for path in new if path.is_dir()]
        self.assertEqual(len(directories), 1, stdout.getvalue() + stderr.getvalue())
        output = directories[0]
        return code, output, stdout.getvalue() + stderr.getvalue()

    def assert_private_bundle(self, output: Path, console: str) -> dict:
        self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o700)
        expected = {
            "installation-before.json",
            "installation-after.json",
            "schema.json",
            "monitoring-private.json",
            "summary.json",
        }
        self.assertEqual({path.name for path in output.iterdir()}, expected)
        for path in output.iterdir():
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            json.loads(path.read_text())
            self.assertNotIn(SECRET, path.read_text())
        package = output.with_name(output.name + ".tar.gz")
        self.assertTrue(package.is_file())
        self.assertEqual(stat.S_IMODE(package.stat().st_mode), 0o600)
        with tarfile.open(package) as archive:
            self.assertEqual(
                set(archive.getnames()), {output.name + "/" + name for name in expected}
            )
            self.assertTrue(all(member.mode == 0o600 for member in archive.getmembers()))
        self.assertIn(str(output), console)
        self.assertIn(str(package), console)
        self.assertNotIn(SECRET, console)
        self.assertNotIn("PRIVATE_POSITION", console)
        return json.loads((output / "summary.json").read_text())

    def test_success_uses_only_approved_reads_and_preserves_installation(self) -> None:
        original = self.installation.files()
        code, output, console = self.invoke()
        self.assertEqual(code, 0)
        summary = self.assert_private_bundle(output, console)
        self.assertEqual(summary["status"], "COMPLETE_PASSIVE_TRANSPORT_NOT_RULE_QUALIFICATION")
        self.assertIs(summary["global_atomic_snapshot"], False)
        self.assertEqual(self.installation.files(), original)
        payloads = [payload for _, payload in self.installation.calls if payload is not None]
        self.assertEqual(payloads, [self.tool.SCHEMA_PAYLOAD, self.tool.BACKEND_PAYLOAD])

    def test_pending_operation_preserves_error_bundle_without_external_commands(self) -> None:
        self.installation.write(self.installation.control / "pending", SECRET)
        code, output, console = self.invoke()
        self.assertEqual(code, 2)
        summary = self.assert_private_bundle(output, console)
        self.assertIs(summary["transport_complete"], False)
        before = json.loads((output / "installation-before.json").read_text())
        self.assertEqual(before["read_error"], "MANAGED_OPERATION_PENDING")
        self.assertEqual(self.installation.calls, [])

    def test_invalid_container_and_image_bindings_never_execute_backend(self) -> None:
        original = copy.deepcopy(self.installation.containers)
        changes = (
            ("backend", "project", "foreign-project"),
            ("backend", "name", "/unexpected-backend"),
            ("backend", "service", "unrelated"),
            ("backend", "config_files", "/unrelated/compose.yml"),
            ("backend", "image_id", "sha256:" + "f" * 64),
        )
        for service, field, value in changes:
            with self.subTest(field=field):
                self.installation.containers = copy.deepcopy(original)
                self.installation.containers[service][field] = value
                self.installation.calls.clear()
                code, output, console = self.invoke()
                self.assertEqual(code, 2)
                self.assert_private_bundle(output, console)
                self.assertFalse(any(payload for _, payload in self.installation.calls))

    def test_mismatching_checkout_or_image_revision_is_not_an_installation_proof(self) -> None:
        for field in ("head", "image_revision"):
            with self.subTest(field=field):
                setattr(self.installation, field, "b" * 40)
                self.installation.calls.clear()
                with self.assertRaises(self.tool.DiagnosticError):
                    self.tool.read_installation(self.installation.base)
                self.assertFalse(any(payload for _, payload in self.installation.calls))
                setattr(self.installation, field, REVISION)

    def test_symlinked_or_nonprivate_state_is_rejected_before_commands(self) -> None:
        pointer = self.installation.control / "current-state"
        value = pointer.read_text()
        pointer.chmod(0o644)
        with self.assertRaisesRegex(self.tool.DiagnosticError, "PRIVATE_STATE_PERMISSIONS_INVALID"):
            self.tool.read_installation(self.installation.base)
        pointer.unlink()
        target = self.installation.control / "pointer-target"
        self.installation.write(target, value)
        pointer.symlink_to(target)
        with self.assertRaisesRegex(self.tool.DiagnosticError, "UNSAFE_INSTALLATION_PATH"):
            self.tool.read_installation(self.installation.base)
        self.assertEqual(self.installation.calls, [])

    def test_unhealthy_or_stopped_neighbors_do_not_hide_readable_backend_evidence(self) -> None:
        self.installation.containers["frontend"].update(state="exited", health=None)
        self.installation.containers["issuer-renderer"].update(health="unhealthy")
        self.installation.containers["backend"].update(health="unhealthy")
        code, output, console = self.invoke()
        self.assertEqual(code, 0)
        self.assert_private_bundle(output, console)
        self.assertEqual(sum(payload is not None for _, payload in self.installation.calls), 2)

    def test_docker_utc_z_timestamps_work_with_python310_host_parser(self) -> None:
        class Python310DateTime(datetime):
            @classmethod
            def fromisoformat(cls, value: str) -> datetime:
                if value.endswith("Z"):
                    raise ValueError("Python 3.10 does not accept the UTC Z suffix")
                fraction = re.search(r"\.(\d+)(?=[+-]\d{2}:\d{2}$)", value)
                if fraction and len(fraction[1]) not in (3, 6):
                    raise ValueError("Python 3.10 requires three or six fractional digits")
                return super().fromisoformat(value)

        for container in self.installation.containers.values():
            container["started_at"] = "2026-11-21T08:00:00.123456789Z"
        with patch.object(self.tool, "datetime", Python310DateTime):
            code, output, console = self.invoke()
        self.assertEqual(code, 0)
        self.assert_private_bundle(output, console)
        before = json.loads((output / "installation-before.json").read_text())
        self.assertEqual(
            before["containers"]["backend"]["started_at"], "2026-11-21T08:00:00.123456789Z"
        )

    def test_stopped_backend_retains_both_metadata_snapshots_without_exec(self) -> None:
        self.installation.containers["backend"].update(state="exited", health=None)
        code, output, console = self.invoke()
        self.assertEqual(code, 2)
        summary = self.assert_private_bundle(output, console)
        self.assertIs(summary["installation_unchanged_and_verified"], True)
        for name in ("schema.json", "monitoring-private.json"):
            value = json.loads((output / name).read_text())
            self.assertEqual(value["read_error"], "EXISTING_BACKEND_NOT_RUNNING")
        self.assertFalse(any(payload for _, payload in self.installation.calls))

    def test_schema_failure_does_not_discard_available_monitoring_reads(self) -> None:
        self.installation.schema = {"read_error": "password=" + SECRET}
        code, output, console = self.invoke()
        self.assertEqual(code, 2)
        summary = self.assert_private_bundle(output, console)
        self.assertIs(summary["schema_read_available"], False)
        self.assertIs(summary["monitoring_transport_complete"], True)
        self.assertEqual(sum(payload is not None for _, payload in self.installation.calls), 2)

    def test_incomplete_readback_is_packaged_but_not_reported_as_complete(self) -> None:
        del self.installation.monitoring["positions"][0]["reads"]["hebeltrader-evidence"]
        code, output, console = self.invoke()
        self.assertEqual(code, 2)
        summary = self.assert_private_bundle(output, console)
        self.assertIs(summary["monitoring_transport_complete"], False)

    def test_changed_installation_prevents_complete_transport_after_successful_reads(self) -> None:
        original = self.installation.command

        def command(args: list[str], **kwargs: object) -> str:
            result = original(args, **kwargs)
            if kwargs.get("input_text") == self.tool.BACKEND_PAYLOAD:
                self.installation.containers["backend"]["restart_count"] += 1
            return result

        with patch.object(self.tool, "run_command", side_effect=command):
            code, output, console = self.invoke()
        self.assertEqual(code, 2)
        summary = self.assert_private_bundle(output, console)
        self.assertIs(summary["installation_unchanged_and_verified"], False)


class CommandBoundaryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tool = load_tool()

    def test_remote_docker_host_is_rejected_before_any_subprocess(self) -> None:
        with (
            patch.dict(os.environ, {"DOCKER_HOST": "tcp://external.invalid:2376"}),
            patch.object(subprocess, "run") as command,
            self.assertRaisesRegex(self.tool.DiagnosticError, "REMOTE_DOCKER_HOST_NOT_ALLOWED"),
        ):
            self.tool.docker_prefix()
        command.assert_not_called()

    def test_home_inside_git_is_rejected_before_output_or_commands(self) -> None:
        with tempfile.TemporaryDirectory(prefix="depot-collector-output-guard-") as name:
            home = Path(name)
            (home / ".git").mkdir()
            stdout, stderr = io.StringIO(), io.StringIO()
            original_umask = os.umask(0o022)
            try:
                with (
                    patch.object(self.tool.Path, "home", return_value=home),
                    patch.object(self.tool.tempfile, "mkdtemp") as output,
                    patch.object(subprocess, "run") as command,
                    redirect_stdout(stdout),
                    redirect_stderr(stderr),
                ):
                    code = self.tool.main(["--base", str(home / "Boerse")])
            finally:
                os.umask(original_umask)
            self.assertEqual(code, 2)
            self.assertIn("HOME_INSIDE_GIT_NO_PRIVATE_OUTPUT_LOCATION", stderr.getvalue())
            output.assert_not_called()
            command.assert_not_called()

    def test_child_process_has_no_ambient_remote_docker_context_and_no_shell(self) -> None:
        variables = {
            "DOCKER_HOST": "tcp://external.invalid:2376",
            "DOCKER_CONTEXT": "external-context",
            "DOCKER_TLS_VERIFY": "1",
            "DOCKER_CERT_PATH": "/private-certificates",
        }
        with (
            patch.dict(os.environ, variables),
            patch.object(
                subprocess,
                "run",
                return_value=subprocess.CompletedProcess(["synthetic"], 0, "safe output", SECRET),
            ) as command,
        ):
            self.assertEqual(self.tool.run_command(["synthetic"]), "safe output")
        kwargs = command.call_args.kwargs
        self.assertFalse(kwargs.get("shell", False))
        self.assertFalse(set(variables) & set(kwargs["env"]))
        self.assertEqual(kwargs["env"]["GIT_OPTIONAL_LOCKS"], "0")

    def test_command_errors_never_expose_raw_stderr_stdout_or_exception_text(self) -> None:
        cases = (
            (subprocess.CompletedProcess(["synthetic"], 1, SECRET, SECRET), None, "COMMAND_FAILED"),
            (None, subprocess.TimeoutExpired(SECRET, 1, SECRET, SECRET), "COMMAND_TIMEOUT"),
            (None, OSError(SECRET), "COMMAND_UNAVAILABLE"),
        )
        for result, error, expected in cases:
            with self.subTest(expected=expected):
                with (
                    patch.object(subprocess, "run", return_value=result, side_effect=error),
                    self.assertRaises(self.tool.DiagnosticError) as caught,
                ):
                    self.tool.run_command(["synthetic"])
                self.assertEqual(str(caught.exception), expected)
                self.assertNotIn(SECRET, json.dumps(self.tool.safe_error(caught.exception)))


class SchemaPayloadTest(unittest.TestCase):
    def run_schema(self, *, fail_select: bool) -> tuple[dict, list[str], dict]:
        tool = load_tool()
        statements: list[str] = []
        engine_options: dict = {}
        database_url = "postgresql+asyncpg://configured-user:" + SECRET + "@configured/db"

        class Connection:
            async def __aenter__(self) -> Connection:
                return self

            async def __aexit__(self, *args: object) -> None:
                statements.append("CONNECTION_CLOSED")

            async def execute(self, query: str) -> SimpleNamespace:
                statements.append(query)
                allowed = {
                    "BEGIN READ ONLY",
                    "SET LOCAL statement_timeout = '10s'",
                    "SET LOCAL lock_timeout = '2s'",
                    "SELECT version_num FROM alembic_version ORDER BY version_num",
                    "ROLLBACK",
                }
                if query not in allowed:
                    raise AssertionError("Unexpected database statement")
                if query.startswith("SELECT") and fail_select:
                    raise RuntimeError(database_url)
                return SimpleNamespace(
                    scalars=lambda: SimpleNamespace(all=lambda: ["20261118_0060"])
                )

        class Engine:
            def connect(self) -> Connection:
                return Connection()

            async def dispose(self) -> None:
                statements.append("ENGINE_DISPOSED")

        def create_engine(url: str, **kwargs: object) -> Engine:
            self.assertEqual(url, database_url)
            engine_options.update(kwargs)
            return Engine()

        modules = {
            name: ModuleType(name)
            for name in (
                "app",
                "app.core",
                "app.core.config",
                "sqlalchemy",
                "sqlalchemy.ext",
                "sqlalchemy.ext.asyncio",
                "sqlalchemy.pool",
            )
        }
        modules["app.core.config"].get_settings = lambda: SimpleNamespace(database_url=database_url)
        modules["sqlalchemy"].text = lambda value: value
        modules["sqlalchemy.ext.asyncio"].create_async_engine = create_engine
        modules["sqlalchemy.pool"].NullPool = type("SyntheticNullPool", (), {})
        stdout = io.StringIO()
        original_logging_disable = logging.root.manager.disable
        try:
            with patch.dict(sys.modules, modules), redirect_stdout(stdout):
                exec(compile(tool.SCHEMA_PAYLOAD, "<synthetic-schema-payload>", "exec"), {})
        finally:
            logging.disable(original_logging_disable)
        self.assertNotIn(SECRET, stdout.getvalue())
        return json.loads(stdout.getvalue()), statements, engine_options

    def test_installed_backend_configuration_is_read_under_enforced_read_only_transaction(
        self,
    ) -> None:
        result, statements, options = self.run_schema(fail_select=False)
        self.assertEqual(result["versions"], ["20261118_0060"])
        self.assertEqual(result["status"], "READ_ONLY_SCHEMA_VERSION_OBSERVED")
        self.assertEqual(statements[0], "BEGIN READ ONLY")
        self.assertEqual(statements[-3:], ["ROLLBACK", "CONNECTION_CLOSED", "ENGINE_DISPOSED"])
        self.assertEqual(sum(statement.startswith("SELECT") for statement in statements), 1)
        self.assertIs(options["echo"], False)
        self.assertEqual(options["isolation_level"], "AUTOCOMMIT")
        self.assertEqual(
            options["connect_args"]["server_settings"]["default_transaction_read_only"], "on"
        )
        self.assertEqual(options["connect_args"]["server_settings"]["statement_timeout"], "10000")

    def test_schema_failure_still_rolls_back_disposes_and_redacts_credentials(self) -> None:
        result, statements, _ = self.run_schema(fail_select=True)
        self.assertEqual(result["read_error"], "RuntimeError")
        self.assertNotIn("status", result)
        self.assertEqual(statements[-3:], ["ROLLBACK", "CONNECTION_CLOSED", "ENGINE_DISPOSED"])


if __name__ == "__main__":
    unittest.main()
