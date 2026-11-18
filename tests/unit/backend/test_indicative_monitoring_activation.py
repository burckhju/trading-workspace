"""Synthetic activation with intercepted commands and unchanged deployment guards.

Full activation needs a disposable state directory outside Git, as production
does. Environments whose entire writable scratch lies under Git skip those cases;
CI must execute them without skips using its ordinary temporary directory.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from app.tools import legacy_issuer_deployment as legacy
from tests.unit.backend.tools.test_legacy_issuer_deployment import deployment_fixture

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts/activate-indicative-monitoring.py"
REVISION = "a" * 40
SECRET = "synthetic-$TOKEN-$$literal-${NO_INTERPOLATION}-ümlaut"


def load_tool() -> ModuleType:
    spec = importlib.util.spec_from_file_location("_indicative_activation_test_tool", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


tool = load_tool()
original_support_loader = tool.load_support


class FakeInstallation:
    def __init__(
        self,
        root: Path,
        monkeypatch: pytest.MonkeyPatch,
        *,
        scope: str = "DISABLED",
        previous_activation: bool = False,
    ) -> None:
        self.base = root / "synthetic Boerse"
        self.app = self.base / "trading-workspace-app"
        for relative in (
            tool.SCRIPT_PATH,
            tool.SUPPORT_PATH,
            "scripts/trading-workspace.sh",
            "scripts/migrate-legacy-issuer.sh",
            "backend/app/tools/legacy_issuer_deployment.py",
        ):
            destination = self.app / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes((ROOT / relative).read_bytes())
        (self.app / "VERSION").write_text("1.5.49\n")
        binary = root / "synthetic-bin"
        binary.mkdir()
        launcher = binary / "trading-workspace"
        launcher.write_bytes((ROOT / "scripts/trading-workspace.sh").read_bytes())
        launcher.chmod(0o755)
        monkeypatch.setenv("TRADING_WORKSPACE_BIN_DIR", str(binary))
        self.control = self.base / "trading-workspace-state"
        self.control.mkdir(mode=0o700)
        runs = self.control / "runs"
        runs.mkdir(mode=0o700)
        operation = runs / "synthetic-installed-release"
        operation.mkdir(mode=0o700)
        self.old = operation / "deployment"
        self.old.mkdir(mode=0o700)
        self.h = original_support_loader(self.base)
        self.live, self.before = deployment_fixture()
        backend = self.before["services"]["backend"]["environment"]
        backend.update(
            {
                tool.SCOPE_KEY: scope,
                tool.RUNNER_KEY: "true" if scope == "INDICATIVE_ENTRY_V1" else "false",
                tool.NOTIFICATIONS_KEY: "false",
                "TRADING_WORKSPACE_POSITION_MONITORING__HEBELTRADER_SCOPE": "DISABLED",
                "TRADING_WORKSPACE_MARKET_DATA__REFRESH__AUTO_CONFIGURE": "false",
                "TRADING_WORKSPACE_MARKET_DATA__EODHD__ENABLED": "false",
                "TRADING_WORKSPACE_MARKET_DATA__EODHD__API_KEY": SECRET.replace("$", "$$"),
            }
        )
        for service, candidate in self.before["services"].items():
            candidate["image"] = f"trading-workspace-{service}:migration-{REVISION}"
        self.active_state = self.old
        self.commands: list[list[str]] = []
        self.mutations: list[list[str]] = []
        self.backups: list[list[str]] = []
        self.tag_revision = REVISION
        self.fail_backup = False
        self.runtime_before: dict[str, Any] = {}
        self.runtime_after: dict[str, Any] = {}
        self._update_live(self.before, self.old)
        for name in self.h.LEGACY_INPUTS:
            data = b"synthetic\n"
            if name == "environment.env":
                data = (
                    f"# Synthetic private installation\nPOSTGRES_PASSWORD='{SECRET}'\n"
                    + f"{tool.SCOPE_KEY}={scope}\n"
                    + f"{tool.RUNNER_KEY}={backend[tool.RUNNER_KEY]}\n"
                    + f"{tool.NOTIFICATIONS_KEY}=false\n"
                ).encode()
            elif name == "candidate.json":
                data = json.dumps(self.before).encode()
            elif name == "baseline.json":
                data = json.dumps(self.live).encode()
            elif name == "preserve.json":
                data = json.dumps(legacy.make_overlay(self.live, self.before, REVISION)).encode()
            elif name == "revision":
                data = (REVISION + "\n").encode()
            elif name == "release-root":
                data = (str(self.app) + "\n").encode()
            elif name == "helper-image":
                data = b"sha256:synthetic-helper\n"
            elif name == "database-container":
                data = b"id-database\n"
            elif name.endswith(".image"):
                data = ("sha256:old-" + name.removesuffix(".image") + "\n").encode()
            self.h._write_private(self.old / name, data, exclusive=True)
        seal = "".join(
            self.h._digest(self.h._read_private(self.old / name)) + "  " + name + "\n"
            for name in sorted(self.h.LEGACY_INPUTS)
        )
        if previous_activation:
            old_tool = b"raise AssertionError('Synthetic previous tool must never execute')\n"
            self.h._write_private(self.old / "activation-tool.py", old_tool, exclusive=True)
            self.h._write_json(
                self.old / "transition.json",
                {
                    "schema": 1,
                    "operation": tool.OPERATION,
                    "old_activation": False,
                    "tool_sha256": self.h._digest(old_tool),
                },
            )
            self.h._create_seal(self.old)
        else:
            self.h._write_private(self.old / "inputs.sha256", seal.encode(), exclusive=True)
        for name in ("prepared", "deployed"):
            self.h._write_private(self.old / name, b"", exclusive=True)
        self.h._write_private(self.control / "current-state", (str(self.old) + "\n").encode())
        monkeypatch.setattr(tool, "load_support", lambda _base: self.h)
        monkeypatch.setattr(self.h, "run_command", self.run)
        monkeypatch.setattr(self.h, "_run_file_command", self.backup)

    def _update_live(self, model: dict[str, Any], state: Path) -> None:
        runtime = legacy.compose_runtime(model)
        chain = ",".join(
            str(path)
            for path in (
                self.app / "docker/compose.yml",
                self.app / "docker/compose.issuer-monitoring.yml",
                state / "preserve.json",
            )
        )
        for item in self.live:
            service = item["Config"]["Labels"]["com.docker.compose.service"]
            item["State"]["Health"] = {"Status": "healthy"}
            item["Config"]["Env"] = [
                f"{k}={v}" for k, v in runtime["services"][service]["environment"].items()
            ]
            if service != "database":
                item["Config"]["Labels"]["com.docker.compose.project.config_files"] = chain
                if state != self.old:
                    item["Id"] = "id-activated-" + service

    def config(self, state: Path) -> dict[str, Any]:
        candidate = copy.deepcopy(self.before)
        if state != self.old:
            lines = (state / "environment.env").read_text().splitlines()
            assert all(key + "=" + value in lines for key, value in tool.TARGETS.items())
            candidate["services"]["backend"]["environment"].update(tool.TARGETS)
        return candidate

    def run(self, command: list[str], **_kwargs: Any) -> bytes:
        self.commands.append(command)
        if command[0] == "git":
            if command[3:5] == ["rev-parse", "HEAD"]:
                return REVISION.encode()
            if command[3:5] == ["rev-parse", "--verify"]:
                return self.tag_revision.encode()
            if command[3] == "status":
                return b""
            if command[3:] == ["remote", "get-url", "origin"]:
                return b"https://github.com/burckhju/trading-workspace.git\n"
        if command[:2] == ["docker", "compose"]:
            state = Path(command[command.index("--env-file") + 1]).parent
            if command[-3:] == ["config", "--format", "json"]:
                return json.dumps(self.config(state)).encode()
            assert "up" in command and "--no-build" in command and "never" in command
            self.mutations.append(command)
            if command[-2:] == ["backend", "frontend"]:
                self.active_state = state
                self._update_live(self.config(state), state)
            else:
                assert command[-1] == "issuer-renderer"
            return b""
        if command[:2] == ["docker", "ps"]:
            return b"one\ntwo\nthree\nfour\n"
        if command[:2] == ["docker", "inspect"]:
            return json.dumps(self.live).encode()
        if command[:3] == ["docker", "image", "inspect"]:
            ref = command[3]
            image = (
                "sha256:synthetic-helper"
                if ref == "sha256:synthetic-helper"
                else next(
                    "sha256:old-" + service
                    for service in self.h.SERVICES
                    if ref == self.before["services"][service]["image"]
                )
            )
            return json.dumps(
                [
                    {
                        "Id": image,
                        "Config": {"Labels": {"org.opencontainers.image.revision": REVISION}},
                    }
                ]
            ).encode()
        if command[:2] == ["docker", "exec"]:
            assert command[2:5] == ["trading-workspace-backend-1", "python", "-c"]
            assert "/health/ready" in command[5] and "/runtime/status" in command[5]
            assert "/providers/" not in command[5] and "telegram" not in command[5]
            environment = self.config(self.active_state)["services"]["backend"]["environment"]
            active = self.active_state != self.old
            value = {
                "enabled": environment[tool.RUNNER_KEY] == "true",
                "running": environment[tool.RUNNER_KEY] == "true",
                "review_scope": environment[tool.SCOPE_KEY],
                "review_rule_version": (
                    "indicative-entry-review-v2"
                    if environment[tool.SCOPE_KEY] == "INDICATIVE_ENTRY_V2"
                    else "indicative-entry-review-v1"
                ),
                "review_notifications_enabled": False,
                "last_cycle_completed_at": None,
                "last_error": None,
                "last_result": None,
            }
            value.update(self.runtime_after if active else self.runtime_before)
            return json.dumps(value).encode()
        if command[:2] == ["docker", "stop"]:
            assert command[-2:] == [
                "trading-workspace-backend-1",
                "trading-workspace-issuer-renderer-1",
            ]
            self.mutations.append(command)
            return b""
        pytest.fail("Unexpected command in synthetic installation")

    def backup(self, command: list[str], destination: Path, _log: Path, **_kwargs: Any) -> None:
        self.backups.append(command)
        if self.fail_backup:
            raise self.h.ActivationError("Synthetic backup failed.")
        self.h._write_private(destination, b"synthetic-backup", exclusive=True)


@pytest.fixture
def installation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
) -> FakeInstallation:
    scope, previous_activation = getattr(request, "param", ("DISABLED", False))
    return FakeInstallation(
        tmp_path, monkeypatch, scope=scope, previous_activation=previous_activation
    )


@pytest.fixture
def managed_installation(installation: FakeInstallation) -> FakeInstallation:
    control = installation.control
    if any((parent / ".git").exists() for parent in (control, *control.parents)):
        pytest.skip(
            "Managed state must remain outside Git. This environment's temporary directory is "
            "inside Git; CI must run this case with the unchanged layout guard outside Git."
        )
    return installation


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
@pytest.mark.parametrize("scope", ["DISABLED", "INDICATIVE_ENTRY_V1"])
def test_env_patch_preserves_secrets_and_unrelated_settings(newline: str, scope: str) -> None:
    before = newline.join(
        [
            f"# {tool.SCOPE_KEY}=DISABLED",
            f"SECRET='{SECRET}'",
            f"export {tool.SCOPE_KEY} = '{scope}' # retained comment",
            f"{tool.RUNNER_KEY}=false",
            f'{tool.NOTIFICATIONS_KEY}="false"',
            "TRADING_WORKSPACE_NOTIFICATION__TELEGRAM__ENABLED=true",
            "",
        ]
    )
    after = tool.patch_environment(before)
    assert after == before.replace("'" + scope + "' #", tool.SCOPE + " #").replace(
        tool.RUNNER_KEY + "=false",
        tool.RUNNER_KEY + "=true",
    )


@pytest.mark.parametrize("before", ["", f"SECRET='{SECRET}'", f"{tool.RUNNER_KEY}=true\n"])
def test_absent_flags_are_appended_without_rewriting_existing_values(before: str) -> None:
    after = tool.patch_environment(before)
    assert after.startswith(before)
    assert all(key + "=" + value in after.splitlines() for key, value in tool.TARGETS.items())


@pytest.mark.parametrize(
    "assignment",
    [
        f"{tool.SCOPE_KEY}={tool.SCOPE}",
        f"{tool.SCOPE_KEY.lower()}=DISABLED",
        f"{tool.SCOPE_KEY}=DISABLED\n{tool.SCOPE_KEY}=DISABLED",
        f"{tool.SCOPE_KEY}=${{OTHER}}",
        f"{tool.RUNNER_KEY}=TRUE",
        f"{tool.NOTIFICATIONS_KEY}=true",
        f"export {tool.SCOPE_KEY} DISABLED",
        f"{tool.SCOPE_KEY}=DISABLED\x00",
    ],
)
def test_ambiguous_or_already_v2_configuration_is_rejected(assignment: str) -> None:
    with pytest.raises(tool.ActivationError) as error:
        tool.patch_environment(f"SECRET='{SECRET}'\n" + assignment)
    assert SECRET not in str(error.value)


@pytest.mark.parametrize(
    "change",
    [
        "provider",
        "refresh",
        "telegram",
        "b04",
        "notifications",
        "port",
        "image",
        "volume",
        "sandbox",
    ],
)
def test_effective_transition_refuses_unrelated_changes(
    installation: FakeInstallation, change: str
) -> None:
    before = copy.deepcopy(installation.before)
    after = copy.deepcopy(before)
    environment = after["services"]["backend"]["environment"]
    environment.update(tool.TARGETS)
    if change in {"provider", "refresh", "telegram", "b04", "notifications"}:
        key = {
            "provider": "TRADING_WORKSPACE_MARKET_DATA__EODHD__ENABLED",
            "refresh": "TRADING_WORKSPACE_MARKET_DATA__REFRESH__ENABLED",
            "telegram": "TRADING_WORKSPACE_NOTIFICATION__TELEGRAM__ENABLED",
            "b04": "TRADING_WORKSPACE_POSITION_MONITORING__HEBELTRADER_SCOPE",
            "notifications": tool.NOTIFICATIONS_KEY,
        }[change]
        environment[key] = "B04_B57_V1" if change == "b04" else "true"
    elif change == "port":
        after["services"]["backend"]["ports"][0]["published"] = "9000"
    elif change == "image":
        after["services"]["backend"]["image"] = "unreviewed:latest"
    elif change == "volume":
        after["services"]["backend"]["volumes"][0]["source"] = "/different"
    else:
        after["services"]["issuer-renderer"]["security_opt"] = ["seccomp=unconfined"]
    with pytest.raises(tool.ActivationError) as error:
        tool.validate_transition(installation.h, before, after)
    assert SECRET not in str(error.value)


@pytest.mark.parametrize("runner", ["false", "true"])
@pytest.mark.parametrize("scope", ["DISABLED", "INDICATIVE_ENTRY_V1"])
def test_transition_retains_existing_runner_and_disabled_notifications(
    installation: FakeInstallation, runner: str, scope: str
) -> None:
    before = copy.deepcopy(installation.before)
    before["services"]["backend"]["environment"][tool.SCOPE_KEY] = scope
    before["services"]["backend"]["environment"][tool.RUNNER_KEY] = runner
    after = copy.deepcopy(before)
    after["services"]["backend"]["environment"].update(tool.TARGETS)
    tool.validate_transition(installation.h, before, after)
    assert before["services"]["backend"]["environment"][tool.SCOPE_KEY] == scope


@pytest.mark.parametrize(
    "scope", [None, "INDICATIVE_ENTRY_V2", "B04_B57_V1", "HEBELTRADER_CONFIRMED_BASELINE"]
)
def test_transition_refuses_any_unreviewed_or_already_activated_source_scope(
    installation: FakeInstallation, scope: str | None
) -> None:
    before = copy.deepcopy(installation.before)
    before["services"]["backend"]["environment"][tool.SCOPE_KEY] = scope
    after = copy.deepcopy(before)
    after["services"]["backend"]["environment"].update(tool.TARGETS)
    with pytest.raises(tool.ActivationError, match="disabled or use V1"):
        tool.validate_transition(installation.h, before, after)


def test_existing_enabled_review_delivery_requires_separate_review(
    installation: FakeInstallation,
) -> None:
    before = copy.deepcopy(installation.before)
    before["services"]["backend"]["environment"][tool.NOTIFICATIONS_KEY] = "true"
    after = copy.deepcopy(before)
    after["services"]["backend"]["environment"].update(tool.TARGETS)
    with pytest.raises(tool.ActivationError, match="notifications must remain disabled"):
        tool.validate_transition(installation.h, before, after)


@pytest.mark.parametrize(
    "installation",
    [("DISABLED", False), ("INDICATIVE_ENTRY_V1", False), ("INDICATIVE_ENTRY_V1", True)],
    indirect=True,
)
def test_prepare_then_apply_keeps_seals_images_data_and_normal_update_path(
    managed_installation: FakeInstallation, capsys: pytest.CaptureFixture[str]
) -> None:
    f = managed_installation
    original = {path.name: path.read_bytes() for path in f.old.iterdir()}
    state = tool.prepare(f.base)
    assert not f.mutations and not f.backups
    assert f.h._line(f.control / "current-state") == str(f.old)
    f.h._seal_entries(state, activation=True)
    transition = json.loads((state / "transition.json").read_text())
    assert (
        transition["source_scope"] == f.before["services"]["backend"]["environment"][tool.SCOPE_KEY]
    )
    assert transition["source_rule_version"] == "indicative-entry-review-v1"
    assert transition["target_scope"] == "INDICATIVE_ENTRY_V2"
    assert transition["target_rule_version"] == "indicative-entry-review-v2"
    assert transition["operation_version"] == "indicative-review-linux-operation-v2"
    output = capsys.readouterr()
    assert SECRET not in output.out + output.err
    assert "apply" in output.out and "Provider" in output.out

    tool.apply(f.base, state)

    assert {path.name: path.read_bytes() for path in f.old.iterdir()} == original
    assert f.h._line(f.control / "current-state") == str(state)
    assert not (f.control / "pending").exists()
    assert (state.parent / "completed").is_file()
    assert (state / "backups-verified").is_file()
    assert f.h._line(state / "phase") == "completed"
    f.h._seal_entries(state, activation=True)
    assert f.h._previous_activation(state) is True
    assert len(f.mutations) == 3 and len(f.backups) == 4
    assert f.live[2]["Id"] == "id-database"
    assert all("--pull" in command and "never" in command for command in f.mutations[1:])
    assert all(path.stat().st_mode & 0o077 == 0 for path in state.iterdir() if path.is_file())
    assert all("migration" not in " ".join(command[:3]) for command in f.commands)
    output = capsys.readouterr()
    assert SECRET not in output.out + output.err
    assert "Noch kein abgeschlossener Prüfdurchlauf belegt" in output.out
    assert "keine" in output.out.lower()
    before_repeat = len(f.commands)
    with pytest.raises(ValueError):
        tool.apply(f.base, state)
    assert len(f.commands) == before_repeat


@pytest.mark.parametrize(
    "installation", [("DISABLED", False), ("INDICATIVE_ENTRY_V1", True)], indirect=True
)
@pytest.mark.parametrize("phase", ["prepare", "apply"])
@pytest.mark.parametrize(
    "mismatch",
    [
        {"review_scope": "INDICATIVE_ENTRY_V2"},
        {"review_rule_version": "indicative-entry-review-v2"},
        {"review_notifications_enabled": True},
    ],
)
def test_loaded_source_scope_and_rule_version_must_match_before_any_service_change(
    managed_installation: FakeInstallation, phase: str, mismatch: dict[str, Any]
) -> None:
    f = managed_installation
    state = tool.prepare(f.base) if phase == "apply" else None
    f.runtime_before = mismatch
    with pytest.raises(tool.ActivationError, match="Loaded review scope"):
        if state is None:
            tool.prepare(f.base)
        else:
            tool.apply(f.base, state)
    assert not f.mutations and not f.backups
    assert not (f.control / "pending").exists()
    assert f.h._line(f.control / "current-state") == str(f.old)


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema", True),
        ("operation_version", "indicative-review-linux-operation-v1"),
        ("source_scope", "INDICATIVE_ENTRY_V2"),
        ("source_rule_version", "indicative-entry-review-v2"),
        ("target_scope", "INDICATIVE_ENTRY_V1"),
        ("target_rule_version", "indicative-entry-review-v1"),
    ],
)
def test_prepared_transition_binds_scope_and_rule_version_even_when_sealed(
    managed_installation: FakeInstallation, field: str, value: Any
) -> None:
    f = managed_installation
    state = tool.prepare(f.base)
    transition = json.loads((state / "transition.json").read_text())
    transition[field] = value
    f.h._write_json(state / "transition.json", transition)
    # Deliberately construct an internally sealed but unsupported synthetic record.
    # The production seal creator remains exclusive and is never weakened.
    names = sorted(f.h.LEGACY_INPUTS | f.h.ADDITIONAL_INPUTS)
    seal = "".join(
        f.h._digest(f.h._read_private(state / name)) + "  " + name + "\n" for name in names
    )
    f.h._write_private(state / "inputs.sha256", seal.encode())
    with pytest.raises(tool.ActivationError, match="Unknown activation record"):
        tool.apply(f.base, state)
    assert not f.mutations and not f.backups
    assert not (f.control / "pending").exists()
    assert f.h._line(f.control / "current-state") == str(f.old)


@pytest.mark.parametrize("marker", ["pending", "current-state.new"])
@pytest.mark.parametrize("symlink", [False, True])
def test_interrupted_control_marker_is_refused_by_unchanged_guard(
    installation: FakeInstallation, marker: str, symlink: bool
) -> None:
    f = installation
    path = f.control / marker
    if symlink:
        path.symlink_to(f.base / "absent-synthetic-path")
    else:
        f.h._write_private(path, SECRET.encode())
    with pytest.raises(ValueError):
        f.h._require_idle_control(f.control)
    assert not f.commands and not f.mutations
    assert path.is_symlink() if symlink else path.read_text() == SECRET


@pytest.mark.parametrize("drift", ["seal", "tag", "container", "image", "configuration"])
def test_pre_apply_drift_is_rejected_before_service_changes(
    managed_installation: FakeInstallation, drift: str
) -> None:
    f = managed_installation
    state = tool.prepare(f.base)
    if drift == "seal":
        f.h._write_private(state / "environment.env", b"changed\n")
    elif drift == "tag":
        f.tag_revision = "b" * 40
    elif drift == "container":
        f.live[0]["Id"] = "id-unexpected-backend"
    elif drift == "image":
        f.live[0]["Image"] = "sha256:unexpected-image"
    else:
        f.before["services"]["backend"]["environment"][
            "TRADING_WORKSPACE_MARKET_DATA__EODHD__ENABLED"
        ] = "true"
    with pytest.raises(ValueError):
        tool.apply(f.base, state)
    assert not f.mutations and not f.backups
    assert not (f.control / "pending").exists()
    assert f.h._line(f.control / "current-state") == str(f.old)


def test_backup_failure_retains_pending_state_and_cannot_be_blindly_replayed(
    managed_installation: FakeInstallation,
) -> None:
    f = managed_installation
    state = tool.prepare(f.base)
    f.fail_backup = True
    with pytest.raises(ValueError):
        tool.apply(f.base, state)
    assert len(f.mutations) == 1
    assert f.h._line(f.control / "current-state") == str(f.old)
    assert f.h._line(f.control / "pending") == str(state.parent)
    assert f.h._line(state / "phase") == "stop-and-backup"
    before = len(f.commands)
    with pytest.raises(ValueError):
        tool.apply(f.base, state)
    assert len(f.commands) == before


@pytest.mark.parametrize(
    "runtime",
    [
        {"review_notifications_enabled": True},
        {"running": False},
        {"review_scope": "DISABLED"},
        {"review_scope": "INDICATIVE_ENTRY_V1"},
        {"review_rule_version": "indicative-entry-review-v1"},
    ],
)
def test_actual_loaded_scope_is_required_before_publishing_state(
    managed_installation: FakeInstallation, runtime: dict[str, Any]
) -> None:
    f = managed_installation
    state = tool.prepare(f.base)
    f.runtime_after = runtime
    with pytest.raises(tool.ActivationError):
        tool.apply(f.base, state)
    assert (f.control / "pending").exists()
    assert f.h._line(f.control / "current-state") == str(f.old)
    assert not (state / "deployed").exists()


@pytest.mark.parametrize(
    "result,expected",
    [
        ({"last_error": "SYNTHETIC_FAILURE"}, "Prüfdurchlauf fehlgeschlagen"),
        ({}, "Noch kein abgeschlossener Prüfdurchlauf belegt"),
        (
            {"last_cycle_completed_at": "2026-11-17T20:00:00Z"},
            "Ergebnisse dieses Teilumfangs fehlen",
        ),
        (
            {
                "last_cycle_completed_at": "2026-11-17T20:00:00Z",
                "last_result": dict.fromkeys(tool.COUNTERS, 0)
                | {"review_positions_evaluated": 1, "review_data_problems": 1},
            },
            "Daten- oder Auswertungsprobleme bestehen",
        ),
    ],
)
def test_scope_confirmation_never_invents_completed_or_healthy_cycles(
    result: dict[str, Any], expected: str, capsys: pytest.CaptureFixture[str]
) -> None:
    tool.print_runtime_summary(result)
    out = capsys.readouterr().out
    assert expected in out
    assert "Keine B58-Qualifikation" in out


def test_entry_and_deadline_results_remain_separate_and_limitations_visible(
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = dict.fromkeys((*tool.COUNTERS, *tool.DEADLINE_COUNTERS), 0)
    result.update(
        review_positions_evaluated=6,
        review_alerts_created=2,
        deadline_positions_evaluated=3,
        deadline_alerts_created=1,
        deadline_data_problems=2,
        deadline_position_errors=1,
    )
    tool.print_runtime_summary(
        {"last_cycle_completed_at": "2026-11-18T15:00:00Z", "last_result": result}
    )
    out = capsys.readouterr().out
    assert "INDICATIVE_ENTRY_V2; Regelversion: indicative-entry-review-v2" in out
    assert "Einstandsprüfung: Positionen ausgewertet=6; Hinweise erstellt=2" in out
    assert "Produkttermin-Erinnerungen: Positionen ausgewertet=3; Hinweise erstellt=1" in out
    assert "Produkttermin-Erinnerungen: Daten- oder Auswertungsprobleme bestehen" in out
    assert "Positionen ausgewertet=9" not in out
    assert "keine bestätigte instrumentbezogene Ausstiegsfrist" in out
    assert "Keine B58-Qualifikation" in out


@pytest.mark.parametrize("invalid", [None, False, -1, "3"])
def test_missing_or_invalid_deadline_counts_do_not_hide_completed_entry_counts(
    invalid: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    result = dict.fromkeys((*tool.COUNTERS, *tool.DEADLINE_COUNTERS), 0)
    result["review_positions_evaluated"] = 6
    result["deadline_positions_evaluated"] = invalid
    tool.print_runtime_summary(
        {"last_cycle_completed_at": "2026-11-18T15:00:00Z", "last_result": result}
    )
    out = capsys.readouterr().out
    assert "Einstandsprüfung: Positionen ausgewertet=6" in out
    assert "Produkttermin-Erinnerungen: Ergebnisse dieses Teilumfangs fehlen noch" in out
    assert "Produkttermin-Erinnerungen: Positionen ausgewertet=" not in out


def test_failed_cycle_never_reuses_previous_success_counters(
    capsys: pytest.CaptureFixture[str],
) -> None:
    tool.print_runtime_summary(
        {
            "last_cycle_completed_at": "2026-11-18T15:00:00Z",
            "last_result": dict.fromkeys((*tool.COUNTERS, *tool.DEADLINE_COUNTERS), 2),
            "last_error": "SYNTHETIC_FAILURE",
        }
    )
    out = capsys.readouterr().out
    assert "vorherige Zähler belegen keine Erholung" in out
    assert "Positionen ausgewertet=" not in out


def test_zero_counts_do_not_claim_portfolio_coverage(capsys: pytest.CaptureFixture[str]) -> None:
    tool.print_runtime_summary(
        {
            "last_cycle_completed_at": "2026-11-18T15:00:00Z",
            "last_result": dict.fromkeys((*tool.COUNTERS, *tool.DEADLINE_COUNTERS), 0),
        }
    )
    out = capsys.readouterr().out
    assert out.count("Keine ausgewertete Position belegt; Depotabdeckung bleibt offen.") == 2


def test_changed_support_bytes_are_not_executed(installation: FakeInstallation) -> None:
    destination = installation.app / tool.SUPPORT_PATH
    marker = installation.base / "must-not-exist"
    destination.write_text("from pathlib import Path\nPath(" + repr(str(marker)) + ").touch()\n")
    with pytest.raises(tool.ActivationError):
        original_support_loader(installation.base)
    assert not marker.exists()


def test_production_layout_still_rejects_state_under_git(installation: FakeInstallation) -> None:
    f = installation
    (f.base / ".git").mkdir()
    unmodified = original_support_loader(f.base)
    with pytest.raises(unmodified.ActivationError, match="outside Git checkouts"):
        unmodified._layout(f.base)
    assert not f.commands and not f.mutations
