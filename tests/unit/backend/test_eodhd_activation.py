"""Qualify the bounded provider change without a Docker daemon or live accounts."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from tests.unit.backend.tools.test_legacy_issuer_deployment import deployment_fixture

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts/enable-eodhd-linux.py"
PREFIX = "TRADING_WORKSPACE_"
ENABLED = PREFIX + "MARKET_DATA__EODHD__ENABLED"
API_KEY = PREFIX + "MARKET_DATA__EODHD__API_KEY"
FLAGS = {
    "refresh_enabled": PREFIX + "MARKET_DATA__REFRESH__ENABLED",
    "auto_configure": PREFIX + "MARKET_DATA__REFRESH__AUTO_CONFIGURE",
    "monitoring_enabled": PREFIX + "POSITION_MONITORING__ENABLED",
    "telegram_enabled": PREFIX + "NOTIFICATION__TELEGRAM__ENABLED",
}
SECRET = "fixture-secret-$TOKEN-$$literal-" + "$" + "{NAME}-ümlaut"


def load_tool() -> ModuleType:
    spec = importlib.util.spec_from_file_location("_eodhd_activation_tests_tool", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


tool = load_tool()


@pytest.fixture
def models() -> tuple[dict[str, Any], dict[str, Any]]:
    _, before = deployment_fixture()
    for service, values in before["services"].items():
        values["image"] = f"trading-workspace-{service}:retained"
    backend = before["services"]["backend"]
    backend["read_only"] = False
    backend["command"] = ["python", "-m", "uvicorn", "app.main:app"]
    backend["environment"].update(
        {
            ENABLED: "false",
            API_KEY: SECRET,
            **dict.fromkeys(FLAGS.values(), "false"),
        }
    )
    after = copy.deepcopy(before)
    after["services"]["backend"]["environment"][ENABLED] = "true"
    return before, after


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_environment_patch_retains_all_other_content(newline: str) -> None:
    prefix = newline.join(
        [
            "# Existing private installation",
            f"# {ENABLED}=false is a comment",
            f"POSTGRES_PASSWORD='{SECRET}'",
            "",
        ]
    )
    suffix = newline.join(
        [
            f"{API_KEY}='{SECRET}'",
            f"{FLAGS['monitoring_enabled']}=true",
            f"{FLAGS['telegram_enabled']}=true",
            "",
        ]
    )
    before = prefix + f"{ENABLED}=false" + newline + suffix
    assert tool.patch_enabled_environment(before) == prefix + f"{ENABLED}=true" + newline + suffix


@pytest.mark.parametrize("before", ["", "OTHER=retained", "OTHER=retained\n"])
def test_missing_activation_line_is_added_without_replacing_existing_settings(before: str) -> None:
    patched = tool.patch_enabled_environment(before)
    assert patched.startswith(before)
    assert patched.splitlines() == [*before.splitlines(), f"{ENABLED}=true"]


@pytest.mark.parametrize(
    "text",
    [
        f"{ENABLED}=false\n{API_KEY}={SECRET}\n{ENABLED}=false\n",
        f"{ENABLED}=true\n{API_KEY}={SECRET}\n",
        f"{ENABLED}={SECRET}\n",
        f"{ENABLED}=\n",
    ],
)
def test_environment_patch_rejects_ambiguous_or_unexpected_values(text: str) -> None:
    with pytest.raises(tool.ActivationError) as error:
        tool.patch_enabled_environment(text)
    assert SECRET not in str(error.value)


def test_transition_accepts_only_activation_and_does_not_rewrite_evidence(
    models: tuple[dict[str, Any], dict[str, Any]],
) -> None:
    before, after = models
    original_before = json.dumps(before)
    original_after = json.dumps(after)
    assert tool.validate_transition(before, after) is None
    assert json.dumps(before) == original_before
    assert json.dumps(after) == original_after
    # JSON presentation and object-key order carry no runtime meaning.
    assert tool.validate_transition(before, json.loads(json.dumps(after, sort_keys=True))) is None


@pytest.mark.parametrize(
    "change",
    [
        "key",
        "database",
        "monitoring",
        "telegram",
        "port",
        "mount",
        "image",
        "sandbox",
        "boolean-type",
        "numeric-type",
        "command-order",
        "added-field",
        "removed-field",
    ],
)
def test_transition_rejects_every_other_runtime_change(
    models: tuple[dict[str, Any], dict[str, Any]], change: str
) -> None:
    before, after = models
    backend = after["services"]["backend"]
    if change == "key":
        backend["environment"][API_KEY] = SECRET + "-changed"
    elif change == "database":
        backend["environment"][PREFIX + "DATABASE_URL"] = SECRET + "-changed"
    elif change in {"monitoring", "telegram"}:
        backend["environment"][FLAGS[change + "_enabled"]] = "true"
    elif change == "port":
        backend["ports"][0]["published"] = "9000"
    elif change == "mount":
        backend["volumes"][0]["source"] = "/unexpected/" + SECRET
    elif change == "image":
        backend["image"] = "unreviewed:latest"
    elif change == "sandbox":
        after["services"]["issuer-renderer"]["security_opt"] = ["seccomp=unconfined"]
    elif change == "boolean-type":
        backend["read_only"] = 0
    elif change == "numeric-type":
        after["services"]["issuer-renderer"]["pids_limit"] = 256.0
    elif change == "command-order":
        backend["command"] = list(reversed(backend["command"]))
    elif change == "added-field":
        after["unreviewed"] = SECRET
    else:
        del backend["read_only"]
    with pytest.raises(tool.ActivationError) as error:
        tool.validate_transition(before, after)
    assert SECRET not in str(error.value)


@pytest.mark.parametrize(
    "old,new", [("true", "true"), ("false", "false"), (False, "true"), ("false", True)]
)
def test_transition_requires_the_declared_string_false_to_true_change(
    models: tuple[dict[str, Any], dict[str, Any]], old: object, new: object
) -> None:
    before, after = models
    before["services"]["backend"]["environment"][ENABLED] = old
    after["services"]["backend"]["environment"][ENABLED] = new
    with pytest.raises(tool.ActivationError):
        tool.validate_transition(before, after)


@pytest.mark.parametrize("missing_from", ["before", "after"])
def test_transition_rejects_a_missing_current_or_target_flag(
    models: tuple[dict[str, Any], dict[str, Any]], missing_from: str
) -> None:
    before, after = models
    missing = before if missing_from == "before" else after
    del missing["services"]["backend"]["environment"][ENABLED]
    with pytest.raises(tool.ActivationError):
        tool.validate_transition(before, after)


@pytest.mark.parametrize(
    "flags",
    [
        (False, False, False, False),
        (True, False, False, False),
        (False, False, True, True),
        (True, False, True, True),
        (True, True, True, True),
    ],
)
def test_automation_summary_reports_each_existing_dimension(
    models: tuple[dict[str, Any], dict[str, Any]], flags: tuple[bool, bool, bool, bool]
) -> None:
    _, candidate = models
    expected = dict(zip(FLAGS, flags, strict=True))
    for name, value in expected.items():
        candidate["services"]["backend"]["environment"][FLAGS[name]] = str(value).lower()
    assert tool.summarize_automation(candidate) == expected


@pytest.mark.parametrize("flag", list(FLAGS.values()))
@pytest.mark.parametrize("missing", [True, False])
def test_missing_or_invalid_automation_is_not_reported_as_disabled(
    models: tuple[dict[str, Any], dict[str, Any]], flag: str, missing: bool
) -> None:
    _, candidate = models
    if missing:
        del candidate["services"]["backend"]["environment"][flag]
    else:
        candidate["services"]["backend"]["environment"][flag] = SECRET
    with pytest.raises(tool.ActivationError) as error:
        tool.summarize_automation(candidate)
    assert SECRET not in str(error.value)


@pytest.mark.parametrize(
    "refresh,monitoring,telegram",
    [(True, False, False), (False, True, False), (False, True, True), (True, True, True)],
)
def test_existing_workers_require_explicit_acknowledgement(
    refresh: bool, monitoring: bool, telegram: bool
) -> None:
    summary = {
        "refresh_enabled": refresh,
        "auto_configure": False,
        "monitoring_enabled": monitoring,
        "telegram_enabled": telegram,
    }
    with pytest.raises(tool.ActivationError):
        tool.require_automation_ack(summary, False)
    assert tool.require_automation_ack(summary, True) is None


def test_inactive_workers_do_not_need_an_automation_acknowledgement() -> None:
    summary = dict.fromkeys(FLAGS, False)
    assert tool.require_automation_ack(summary, False) is None


@pytest.mark.parametrize(
    "raw",
    [
        '{"secret":"' + SECRET + '","broken":',
        '{"secret":"' + SECRET + '","secret":"different"}',
        '{"nested":{"value":1,"value":2},"secret":"' + SECRET + '"}',
        '{"value":NaN,"secret":"' + SECRET + '"}',
        '{"value":Infinity,"secret":"' + SECRET + '"}',
        '{"value":-Infinity,"secret":"' + SECRET + '"}',
        '"' + SECRET + '"',
        "null",
    ],
)
def test_json_rejection_never_exposes_private_values(
    raw: str, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(tool.ActivationError) as error:
        tool.parse_json(raw)
    assert SECRET not in str(error.value)
    output = capsys.readouterr()
    assert output.out == output.err == ""


@pytest.mark.parametrize("value", [{"secret": SECRET}, [{"secret": SECRET}]])
def test_json_reader_retains_literals_and_unicode(
    value: dict[str, str] | list[dict[str, str]],
) -> None:
    assert tool.parse_json(json.dumps(value, ensure_ascii=False).encode("utf-8")) == value


def test_failing_command_keeps_diagnostics_private(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    log = tmp_path / "operation.log"
    command = [
        sys.executable,
        "-c",
        "import sys; print(sys.argv[1]); print(sys.argv[1], file=sys.stderr); sys.exit(9)",
        SECRET,
    ]
    with pytest.raises(tool.ActivationError) as error:
        tool.run_command(command, operation_log=log)
    assert SECRET not in str(error.value)
    captured = capsys.readouterr()
    assert captured.out == captured.err == ""
    assert SECRET in log.read_text()
    assert log.stat().st_mode & 0o077 == 0


def test_missing_command_does_not_publish_its_private_arguments(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(tool.ActivationError) as error:
        tool.run_command(
            [str(tmp_path / ("missing-command-" + SECRET))],
            operation_log=tmp_path / "operation.log",
        )
    assert SECRET not in str(error.value)
    captured = capsys.readouterr()
    assert captured.out == captured.err == ""


def test_apply_without_worker_acknowledgement_makes_no_changes(
    tmp_path: Path,
    models: tuple[dict[str, Any], dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    base = tmp_path / "Boerse with spaces"
    state = base / "trading-workspace-state/runs/review/deployment"
    state.mkdir(mode=0o700, parents=True)
    _, candidate = models
    environment = candidate["services"]["backend"]["environment"]
    environment[FLAGS["refresh_enabled"]] = "true"
    environment[FLAGS["monitoring_enabled"]] = "true"
    environment[FLAGS["telegram_enabled"]] = "true"
    candidate_file = state / "candidate.json"
    candidate_file.write_text(json.dumps(candidate))
    candidate_file.chmod(0o600)
    before = {path: path.read_bytes() for path in base.rglob("*") if path.is_file()}

    def refuse_command(*args: object, **kwargs: object) -> bytes:
        pytest.fail("The unacknowledged apply must not invoke any external command.")

    monkeypatch.setattr(tool, "run_command", refuse_command)
    assert tool.main(["apply", str(state), "--base", str(base)]) != 0
    captured = capsys.readouterr()
    # A private-path/ownership/seal check may reject this incomplete state before
    # the automation check. The real Docker test uses a fully prepared state and
    # requires the specific missing-acknowledgement diagnostic there.
    assert SECRET not in captured.out + captured.err
    assert {path: path.read_bytes() for path in base.rglob("*") if path.is_file()} == before


@pytest.mark.parametrize("marker", ["pending", "current-state.new"])
@pytest.mark.parametrize("dangling_link", [False, True])
def test_prepare_preserves_interrupted_operation_markers_before_any_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    marker: str,
    dangling_link: bool,
) -> None:
    base = tmp_path / "Boerse with spaces"
    (base / "trading-workspace-app").mkdir(parents=True)
    control = base / "trading-workspace-state"
    control.mkdir(mode=0o700)
    interrupted = control / marker
    if dangling_link:
        interrupted.symlink_to(tmp_path / "missing-private-target")
    else:
        interrupted.write_text(SECRET)
        interrupted.chmod(0o600)

    def refuse_command(*args: object, **kwargs: object) -> bytes:
        pytest.fail("An interrupted operation must block every external command.")

    monkeypatch.setattr(tool, "run_command", refuse_command)
    with pytest.raises(tool.ActivationError) as error:
        tool.prepare(base)
    assert SECRET not in str(error.value)
    assert {path.name for path in control.iterdir()} == {marker}
    if dangling_link:
        assert interrupted.is_symlink()
        assert interrupted.readlink() == tmp_path / "missing-private-target"
    else:
        assert interrupted.read_text() == SECRET
