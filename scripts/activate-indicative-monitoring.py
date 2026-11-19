#!/usr/bin/env python3
"""Prepare/apply the bounded indicative review scope in an installed Linux release.

Reuse the unchanged managed-deployment checks, backups and Compose chain. This
does not install a release, approve a provider or send a notification test.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import os
import re
import shlex
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any, NoReturn

PREFIX = "TRADING_WORKSPACE_POSITION_MONITORING__"
SCOPE_KEY = PREFIX + "REVIEW_SCOPE"
RUNNER_KEY = PREFIX + "ENABLED"
NOTIFICATIONS_KEY = PREFIX + "REVIEW_NOTIFICATIONS_ENABLED"
SCOPE = "INDICATIVE_ENTRY_V2"
RULE_VERSION = "indicative-entry-review-v2"
SOURCE_SCOPES = ("DISABLED", "INDICATIVE_ENTRY_V1")
RULE_VERSIONS = {
    "DISABLED": "indicative-entry-review-v1",
    "INDICATIVE_ENTRY_V1": "indicative-entry-review-v1",
    SCOPE: RULE_VERSION,
}
OPERATION = "activate-indicative-monitoring"
OPERATION_VERSION = "indicative-review-linux-operation-v2"
SCRIPT_PATH = "scripts/activate-indicative-monitoring.py"
SUPPORT_PATH = "scripts/enable-eodhd-linux.py"
SUPPORT_SHA256 = "b650c0bf46397c721a382380b2d2061f6261f943e523f1951c4a5c20733ce90a"
TARGETS = {SCOPE_KEY: SCOPE, RUNNER_KEY: "true", NOTIFICATIONS_KEY: "false"}
COUNTERS = (
    "review_positions_evaluated",
    "review_alerts_created",
    "review_data_problems",
    "review_position_errors",
)
DEADLINE_COUNTERS = (
    "deadline_positions_evaluated",
    "deadline_alerts_created",
    "deadline_data_problems",
    "deadline_position_errors",
)
COUNTER_LABELS = ("Positionen ausgewertet", "Hinweise erstellt", "Datenprobleme", "Positionsfehler")


class ActivationError(ValueError):
    """Static diagnostics only; private configuration never belongs in errors."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ActivationError(message)


def load_support(base: Path) -> ModuleType:
    """Load the reviewed utility bytes without changing their policies or globals."""
    require(
        base.is_absolute() and base.resolve() == base,
        "Base path must be absolute and direct.",
    )
    path = base / "trading-workspace-app" / SUPPORT_PATH
    require(
        path.is_file() and not path.is_symlink(),
        "Managed activation support is unavailable.",
    )
    source = path.read_bytes()
    require(
        hashlib.sha256(source).hexdigest() == SUPPORT_SHA256,
        "Pinned activation support differs.",
    )
    module = ModuleType("_checked_indicative_activation_support")
    module.__file__ = str(path)
    exec(compile(source, str(path), "exec"), module.__dict__)
    return module


def patch_environment(text: str) -> str:
    """Replace only literal scope/runner flags, retaining all unrelated bytes."""
    require(isinstance(text, str) and "\x00" not in text, "Unsupported environment file.")
    lines = text.splitlines(keepends=True)
    seen: set[str] = set()
    assignment = re.compile(
        r"^(?P<prefix>[ \t]*(?:export[ \t]+)?)(?P<key>[A-Za-z_][A-Za-z0-9_]*)"
        r"(?P<equals>[ \t]*=)(?P<value>[^\r\n]*)(?P<newline>\r?\n)?$"
    )
    allowed = {
        SCOPE_KEY: set(SOURCE_SCOPES),
        RUNNER_KEY: {"false", "true"},
        NOTIFICATIONS_KEY: {"false"},
    }
    for index, line in enumerate(lines):
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#"):
            continue
        match = assignment.fullmatch(line)
        if match and match["key"].upper() in TARGETS:
            key = match["key"]
            require(key in TARGETS and key not in seen, "Ambiguous activation assignment.")
            seen.add(key)
            value = re.fullmatch(
                r"(?P<space>[ \t]*)(?P<quote>['\"]?)(?P<literal>[A-Za-z0-9_]+)(?P=quote)"
                r"(?P<tail>[ \t]*(?:#[^\r\n]*)?)",
                match["value"],
            )
            require(
                value is not None and value["literal"] in allowed[key],
                "Unexpected activation value; use a disabled or V1 scope with review delivery off.",
            )
            assert value is not None
            if value["literal"] != TARGETS[key]:
                lines[index] = (
                    match["prefix"]
                    + key
                    + match["equals"]
                    + value["space"]
                    + TARGETS[key]
                    + value["tail"]
                    + (match["newline"] or "")
                )
        elif any(re.match(r"(?:export\s+)?" + key + r"\b", stripped, re.I) for key in TARGETS):
            raise ActivationError("Unsupported activation assignment.")
    result = "".join(lines)
    newline = "\r\n" if "\r\n" in text else "\n"
    for key, target in TARGETS.items():
        if key not in seen:
            if result and not result.endswith("\n"):
                result += newline
            result += key + "=" + target + newline
    return result


def _source_scope(environment: dict[str, Any]) -> str:
    scope = environment.get(SCOPE_KEY)
    require(
        scope in SOURCE_SCOPES,
        "Indicative review must be disabled or use V1 before this transition.",
    )
    assert isinstance(scope, str)
    return scope


def validate_transition(h: Any, before: dict[str, Any], after: dict[str, Any]) -> None:
    old, new = h._backend_environment(before), h._backend_environment(after)
    _source_scope(old)
    require(
        old.get(RUNNER_KEY) in ("true", "false"),
        "Unknown existing runner configuration.",
    )
    require(
        old.get(NOTIFICATIONS_KEY) == "false",
        "Indicative notifications must remain disabled.",
    )
    require(
        all(new.get(key) == value for key, value in TARGETS.items()),
        "Unexpected target scope.",
    )
    expected = copy.deepcopy(before)
    h._backend_environment(expected).update(TARGETS)
    require(
        h._canonical(expected) == h._canonical(after),
        "Configuration differs beyond the indicative scope and runner activation.",
    )


def _previous_activation(h: Any, state: Path) -> bool:
    activation: bool = h._previous_activation(state)
    return activation


def _release(h: Any, app: Path, log: Path, revision: str, version: str) -> None:
    tagged = (
        h.run_command(
            [
                "git",
                "-C",
                str(app),
                "rev-parse",
                "--verify",
                "refs/tags/v" + version + "^{commit}",
            ],
            operation_log=log,
        )
        .decode()
        .strip()
    )
    require(tagged == revision, "Installed version tag and release revision differ.")
    installed_tool = app / SCRIPT_PATH
    require(
        installed_tool.is_file()
        and not installed_tool.is_symlink()
        and installed_tool.read_bytes() == Path(__file__).resolve().read_bytes(),
        "Use the activation tool from the installed tagged release.",
    )


def _runtime(h: Any, log: Path, *, scope: str, enabled: bool) -> dict[str, Any]:
    require(scope in RULE_VERSIONS, "Unknown runtime scope.")
    keys = (
        "enabled",
        "running",
        "review_scope",
        "review_rule_version",
        "review_notifications_enabled",
        "last_cycle_completed_at",
        "last_error",
        "last_result",
    )
    source = (
        "import json,urllib.request; "
        "r=urllib.request.urlopen('http://127.0.0.1:8000/health/ready',timeout=10); "
        "assert r.status==200 and json.load(r)['status']=='ready'; "
        "r=urllib.request.urlopen("
        "'http://127.0.0.1:8000/api/v1/position-monitoring/runtime/status',timeout=10); "
        "v=json.load(r); print(json.dumps({k:v[k] for k in " + repr(keys) + "}))"
    )
    value = h.parse_json(
        h.run_command(
            ["docker", "exec", h.PROJECT + "-backend-1", "python", "-c", source],
            operation_log=log,
        )
    )
    require(
        isinstance(value, dict)
        and value.get("enabled") is enabled
        and value.get("running") is enabled
        and value.get("review_scope") == scope
        and value.get("review_rule_version") == RULE_VERSIONS[scope]
        and value.get("review_notifications_enabled") is False,
        "Loaded review scope, runner or notification settings differ.",
    )
    assert isinstance(value, dict)
    return value


def _print_cycle_counters(result: Any, counters: tuple[str, ...], label: str) -> None:
    if not isinstance(result, dict) or any(
        type(result.get(key)) is not int or result[key] < 0 for key in counters
    ):
        print(label + ": Ergebnisse dieses Teilumfangs fehlen noch.")
        return
    print(
        "Letzter abgeschlossener Durchlauf · "
        + label
        + ": "
        + "; ".join(
            COUNTER_LABELS[index] + "=" + str(result[key]) for index, key in enumerate(counters)
        )
    )
    if result[counters[0]] == 0:
        print(label + ": Keine ausgewertete Position belegt; Depotabdeckung bleibt offen.")
    if result[counters[2]] or result[counters[3]]:
        print(
            label + ": Daten- oder Auswertungsprobleme bestehen; Hinweise im Arbeitsbereich prüfen."
        )


def print_runtime_summary(value: dict[str, Any]) -> None:
    print("Geladener Teilumfang: " + SCOPE + "; Regelversion: " + RULE_VERSION)
    print("Runner gestartet; externe Benachrichtigungen dieses Teilumfangs sind deaktiviert.")
    completed = value.get("last_cycle_completed_at")
    if value.get("last_error"):
        print("Letzter Prüfdurchlauf fehlgeschlagen; vorherige Zähler belegen keine Erholung.")
    elif not completed:
        print("Noch kein abgeschlossener Prüfdurchlauf belegt; Datenabdeckung bleibt offen.")
    else:
        result = value.get("last_result")
        _print_cycle_counters(result, COUNTERS, "Einstandsprüfung")
        _print_cycle_counters(result, DEADLINE_COUNTERS, "Produkttermin-Erinnerungen")
    print(
        "Produkttermine sind Kalendererinnerungen; "
        "keine bestätigte instrumentbezogene Ausstiegsfrist."
    )
    print("Keine B58-Qualifikation oder vollständige Hebeltrader-Überwachung bestätigt.")


def prepare(base: Path) -> Path:
    h = load_support(base)
    app, control = h._layout(base)
    h._require_idle_control(control)
    with h._lock(control):
        h._require_idle_control(control)
        old = h._current(control)
        old_activation = _previous_activation(h, old)
        legacy = h._legacy(app)
        launcher_path, launcher_hash = h._launcher(app)
        runs = control / "runs"
        h._private_directory(runs)
        prefix = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-review-")  # noqa: UP017
        operation = Path(tempfile.mkdtemp(prefix=prefix, dir=runs))
        state = operation / "deployment"
        state.mkdir(mode=0o700)
        log = state / "operation.log"
        h._mark(state, "prepare-preflight")
        items, before, revision, version = h._validate_old(
            app,
            old,
            log,
            legacy,
            activation_state=old_activation,
        )
        _release(h, app, log, revision, version)
        environment = h._backend_environment(before)
        source_scope = _source_scope(environment)
        summary = h.summarize_automation(before)
        _runtime(h, log, scope=source_scope, enabled=summary["monitoring_enabled"])
        require(
            environment.get(NOTIFICATIONS_KEY) == "false",
            "Review notifications are not disabled.",
        )
        for name in h.LEGACY_INPUTS - {
            "environment.env",
            "baseline.json",
            "candidate.json",
        }:
            h._write_private(state / name, h._read_private(old / name), exclusive=True)
        patched = patch_environment(h._read_private(old / "environment.env").decode("utf-8"))
        h._write_private(state / "environment.env", patched.encode(), exclusive=True)
        h._write_json(state / "baseline.json", items)
        candidate = h.parse_json(h._compose(app, state, log, "config", "--format", "json"))
        validate_transition(h, before, candidate)
        h._write_json(state / "candidate.json", candidate)
        tool = Path(__file__).resolve().read_bytes()
        h._write_private(state / "activation-tool.py", tool, exclusive=True)
        h._write_json(
            state / "transition.json",
            {
                "schema": 1,
                "operation": OPERATION,
                "operation_version": OPERATION_VERSION,
                "source_scope": source_scope,
                "source_rule_version": RULE_VERSIONS[source_scope],
                "target_scope": SCOPE,
                "target_rule_version": RULE_VERSION,
                "old_state": str(old),
                "old_activation": old_activation,
                "application_root": str(app),
                "release_revision": revision,
                "release_version": version,
                "old_seal_sha256": h._digest(h._read_private(old / "inputs.sha256")),
                "old_pointer_sha256": h._digest(h._read_private(control / "current-state")),
                "tool_sha256": h._digest(tool),
                "support_sha256": SUPPORT_SHA256,
                "launcher_path": str(launcher_path),
                "launcher_sha256": launcher_hash,
                "automation_before": summary,
            },
        )
        h._create_seal(state)
        h._write_private(state / "prepared", b"", exclusive=True)
        h._mark(state, "prepared")
        for directory in (state, operation, runs):
            h._sync_directory(directory)
        print("Vorbereitet: " + str(state))
        print("Installierter Tag: v" + version + "; unveränderter Commit: " + revision)
        print(
            "Änderung: "
            + source_scope
            + " → "
            + SCOPE
            + "; Regelversion: "
            + RULE_VERSION
            + "; allgemeiner Runner an, Review-Zustellung aus."
        )
        print("V2 ergänzt Einstandsindikation und beleggebundene Produkttermin-Erinnerungen.")
        print(
            "Provider, Refresh, vorhandene Telegramkonfiguration, Images und Datenbindungen "
            "bleiben erhalten."
        )
        print(
            "Vorhandene Automatik: "
            + ", ".join(key + "=" + str(value).lower() for key, value in sorted(summary.items()))
        )
        if summary["telegram_enabled"]:
            print(
                "Bereits konfigurierte andere Nachrichtenzustellungen können beim "
                "Runnerstart weiterlaufen."
            )
        print("Einmalige Anwendung des vorbereiteten Zustands:")
        print(
            shlex.join(
                [
                    "python3",
                    str(state / "activation-tool.py"),
                    "apply",
                    str(state),
                    "--base",
                    str(base),
                ]
            )
        )
        return state


def _precheck(h: Any, state: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    h._seal_entries(state, activation=True)
    require(
        (state / "prepared").is_file()
        and not (state / "apply-started").exists()
        and not (state / "deployed").exists(),
        "Activation is not an unused prepared operation.",
    )
    transition = h.parse_json(h._read_private(state / "transition.json"))
    source_scope = transition.get("source_scope") if isinstance(transition, dict) else None
    require(
        isinstance(transition, dict)
        and type(transition.get("schema")) is int
        and transition.get("schema") == 1
        and transition.get("operation") == OPERATION
        and transition.get("operation_version") == OPERATION_VERSION
        and isinstance(source_scope, str)
        and source_scope in SOURCE_SCOPES
        and transition.get("source_rule_version") == RULE_VERSIONS[source_scope]
        and transition.get("target_scope") == SCOPE
        and transition.get("target_rule_version") == RULE_VERSION
        and transition.get("support_sha256") == SUPPORT_SHA256
        and type(transition.get("old_activation")) is bool,
        "Unknown activation record.",
    )
    digest = h._digest(Path(__file__).resolve().read_bytes())
    require(
        digest == transition.get("tool_sha256")
        and digest == h._digest(h._read_private(state / "activation-tool.py")),
        "Prepared activation tool differs.",
    )
    candidate = h.parse_json(h._read_private(state / "candidate.json"))
    target = h._backend_environment(candidate)
    require(
        all(target.get(key) == value for key, value in TARGETS.items()),
        "Prepared scope differs.",
    )
    return candidate, transition


def apply(base: Path, state: Path) -> None:
    h = load_support(base)
    candidate, transition = _precheck(h, state)
    app, control = h._layout(base)
    require(
        state.parent.parent == control / "runs"
        and state.name == "deployment"
        and transition.get("application_root") == str(app),
        "Prepared installation differs.",
    )
    h._private_directory(state.parent)
    h._require_idle_control(control)
    with h._lock(control):
        candidate, transition = _precheck(h, state)
        h._require_idle_control(control)
        old = h._current(control)
        require(
            str(old) == transition.get("old_state")
            and h._digest(h._read_private(control / "current-state"))
            == transition.get("old_pointer_sha256")
            and h._digest(h._read_private(old / "inputs.sha256"))
            == transition.get("old_seal_sha256"),
            "Previously prepared deployment changed.",
        )
        legacy = h._legacy(app)
        launcher_path, launcher_hash = h._launcher(app)
        require(
            str(launcher_path) == transition.get("launcher_path")
            and launcher_hash == transition.get("launcher_sha256"),
            "Installed launcher changed.",
        )
        log = state / "operation.log"
        h._mark(state, "apply-preflight")
        live, before, revision, version = h._validate_old(
            app, old, log, legacy, activation_state=transition["old_activation"]
        )
        require(
            revision == transition.get("release_revision")
            and version == transition.get("release_version"),
            "Application release changed.",
        )
        _release(h, app, log, revision, version)
        h._legacy_call(
            legacy,
            "verify_identity",
            h.parse_json(h._read_private(state / "baseline.json")),
            live,
        )
        summary = h.summarize_automation(before)
        require(
            summary == transition.get("automation_before"),
            "Existing automation changed.",
        )
        source_scope = _source_scope(h._backend_environment(before))
        require(source_scope == transition["source_scope"], "Prepared source scope changed.")
        _runtime(h, log, scope=source_scope, enabled=summary["monitoring_enabled"])
        rendered = h.parse_json(h._compose(app, state, log, "config", "--format", "json"))
        h._legacy_call(legacy, "verify_configuration", candidate, rendered)
        validate_transition(h, before, rendered)
        # No old state or container has been modified before these guards pass.
        h._write_private(control / "pending", (str(state.parent) + "\n").encode(), exclusive=True)
        h._write_private(state / "apply-started", b"", exclusive=True)
        h._mark(state, "stop-and-backup")
        h._sync_directory(state)
        h._sync_directory(control)
        h.run_command(
            [
                "docker",
                "stop",
                "--time",
                "60",
                h.PROJECT + "-backend-1",
                h.PROJECT + "-issuer-renderer-1",
            ],
            operation_log=log,
        )
        h._backup(state, log)
        common = (
            "up",
            "-d",
            "--no-build",
            "--pull",
            "never",
            "--force-recreate",
            "--no-deps",
            "--wait",
            "--wait-timeout",
            "180",
        )
        h._mark(state, "renderer")
        h._compose(app, state, log, *common, "issuer-renderer")
        h._mark(state, "application")
        h._compose(app, state, log, *common, "backend", "frontend")
        h._mark(state, "verification")
        h._seal_entries(state, activation=True)
        h._seal_entries(old, activation=transition["old_activation"])
        deployed = h._inspect(log)
        h._legacy_call(legacy, "validate_candidate", deployed, candidate)
        h._check_images_and_chain(deployed, app, state, candidate, legacy, log)
        runtime = _runtime(h, log, scope=SCOPE, enabled=True)
        h._write_json(state / "runtime-verification.json", runtime)
        base_config = h.parse_json(
            h._compose(app, state, log, "config", "--format", "json", base_only=True)
        )
        h._legacy_call(legacy, "make_overlay", deployed, base_config, revision)
        require(
            h._digest(h._read_private(control / "current-state"))
            == transition["old_pointer_sha256"]
            and h._line(control / "pending") == str(state.parent),
            "Operation ownership changed.",
        )
        h._write_json(state / "deployed.json", deployed)
        h._write_private(state / "deployed", b"", exclusive=True)
        h._mark(state, "publish-state")
        h._sync_directory(state)
        h._sync_directory(state.parent)
        h._write_private(
            control / "current-state.new", (str(state) + "\n").encode(), exclusive=True
        )
        os.replace(control / "current-state.new", control / "current-state")
        h._sync_directory(control)
        os.replace(control / "pending", state.parent / "completed")
        h._sync_directory(control)
        h._sync_directory(state.parent)
        h._mark(state, "completed")
        print(
            "Konfiguration angewendet; Programmversion, Images und Providerfreigaben unverändert."
        )
        print("Neuer verwalteter Zustand: " + str(state))
        print_runtime_summary(runtime)


class _SafeParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ActivationError("Invalid arguments; use --help. No argument values printed.")


def main(argv: list[str] | None = None) -> int:
    parser = _SafeParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    default_base = os.environ.get("TRADING_WORKSPACE_BASE", str(Path.home() / "Boerse"))
    for action in ("prepare", "apply"):
        command = commands.add_parser(action)
        command.add_argument("--base", default=default_base, type=Path)
        if action == "apply":
            command.add_argument("state", type=Path)
    try:
        args = parser.parse_args(argv)
        require(os.getuid() != 0, "Run as the existing deployment owner, not root/sudo.")
        if args.action == "prepare":
            prepare(args.base.expanduser())
        else:
            apply(args.base.expanduser(), args.state.expanduser())
        return 0
    except ActivationError as error:
        print("Indicative activation stopped: " + str(error), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print(
            "Activation interrupted. Retain private diagnostics and pending markers.",
            file=sys.stderr,
        )
        return 130
    except Exception:
        print(
            "Activation stopped. Inspect private diagnostics; no private values printed. "
            "Do not remove markers or repeat a started apply.",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
