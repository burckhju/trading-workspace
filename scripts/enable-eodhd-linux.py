#!/usr/bin/env python3
"""Prepare/apply one explicit EODHD activation in the managed Linux installation.

The application release, images and legacy validators never change.  Preparation
only writes a new private generation.  Applying it can resume already configured
provider, monitoring and notification work; the operator must acknowledge that.
"""

from __future__ import annotations

import argparse
import copy
import fcntl
import hashlib
import json
import math
import os
import re
import runpy
import shlex
import stat
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT = "trading-workspace"
ENABLED_KEY = "TRADING_WORKSPACE_MARKET_DATA__EODHD__ENABLED"
APPLICATION_SERVICES = ("backend", "frontend", "issuer-renderer")
SERVICES = ("backend", "issuer-renderer", "database", "frontend")
AUTOMATION_KEYS = {
    "refresh_enabled": "TRADING_WORKSPACE_MARKET_DATA__REFRESH__ENABLED",
    "auto_configure": "TRADING_WORKSPACE_MARKET_DATA__REFRESH__AUTO_CONFIGURE",
    "monitoring_enabled": "TRADING_WORKSPACE_POSITION_MONITORING__ENABLED",
    "telegram_enabled": "TRADING_WORKSPACE_NOTIFICATION__TELEGRAM__ENABLED",
}
LEGACY_HASHES = {
    "scripts/migrate-legacy-issuer.sh": (
        "98e654752c7da85828d7367d19e3f145c43960634dfc831be17778caae7756d9"
    ),
    "backend/app/tools/legacy_issuer_deployment.py": (
        "37319d79a373f3f4fe0a7f7d416164cde165787be30714731d61d538f70de4f4"
    ),
}
LEGACY_INPUTS = {
    "environment.env",
    "preserve.json",
    "baseline.json",
    "helper-image",
    "revision",
    "release-root",
    "candidate.json",
    "backend.image",
    "frontend.image",
    "issuer-renderer.image",
    "database-container",
}
ADDITIONAL_INPUTS = {"activation-tool.py", "transition.json"}


class ActivationError(ValueError):
    """A diagnostic composed exclusively from public, static descriptions."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ActivationError(message)


def patch_enabled_environment(text: str) -> str:
    """Change one literal false assignment, or append the missing assignment.

    Other bytes (including secret quoting/dollars and line endings) are retained.
    Ambiguous or nonliteral assignments are refused; Compose is subsequently
    required to prove the exact single effective configuration difference.
    """
    require(isinstance(text, str) and "\x00" not in text, "Unsupported environment file.")
    lines = text.splitlines(keepends=True)
    matches: list[tuple[int, re.Match[str]]] = []
    assignment = re.compile(
        r"^(?P<prefix>[ \t]*(?:export[ \t]+)?)(?P<key>[A-Za-z_][A-Za-z0-9_]*)"
        r"(?P<equals>[ \t]*=)(?P<value>[^\r\n]*)(?P<newline>\r?\n)?$"
    )
    for index, line in enumerate(lines):
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#"):
            continue
        match = assignment.fullmatch(line)
        if match and match["key"].upper() == ENABLED_KEY:
            require(match["key"] == ENABLED_KEY, "Ambiguous EODHD activation variable.")
            matches.append((index, match))
        elif re.match(r"(?:export\s+)?" + ENABLED_KEY + r"\b", stripped, re.I):
            raise ActivationError("Unsupported EODHD activation assignment.")
    require(len(matches) <= 1, "Duplicate EODHD activation assignments.")
    if matches:
        index, match = matches[0]
        value = re.fullmatch(
            r"(?P<space>[ \t]*)(?P<quote>['\"]?)false(?P=quote)" r"(?P<tail>[ \t]*(?:#[^\r\n]*)?)",
            match["value"],
        )
        require(value is not None, "EODHD activation requires a literal false value.")
        assert value is not None
        lines[index] = (
            match["prefix"]
            + match["key"]
            + match["equals"]
            + value["space"]
            + "true"
            + value["tail"]
            + (match["newline"] or "")
        )
        return "".join(lines)
    newline = "\r\n" if "\r\n" in text else "\n"
    separator = "" if not text or text.endswith("\n") else newline
    return text + separator + ENABLED_KEY + "=true" + newline


def _json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, "Duplicate JSON field.")
        result[key] = value
    return result


def _json_value(value: Any) -> None:
    if isinstance(value, dict):
        require(all(isinstance(key, str) for key in value), "Invalid JSON object.")
        for item in value.values():
            _json_value(item)
    elif isinstance(value, list):
        for item in value:
            _json_value(item)
    elif isinstance(value, float):
        require(math.isfinite(value), "Non-finite JSON number.")
    else:
        require(value is None or type(value) in (str, int, bool), "Invalid JSON value.")


def parse_json(raw: bytes | str) -> dict[str, Any] | list[Any]:
    try:
        value = json.loads(raw, object_pairs_hook=_json_object)
        require(isinstance(value, (dict, list)), "Expected a JSON object or array.")
        _json_value(value)
        return value
    except ActivationError:
        raise
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise ActivationError("Invalid private JSON input; no values printed.") from None


def _canonical(value: Any) -> str:
    _json_value(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _backend_environment(candidate: dict[str, Any]) -> dict[str, Any]:
    try:
        result = candidate["services"]["backend"]["environment"]
        require(isinstance(result, dict), "Missing backend environment.")
        return result
    except (KeyError, TypeError):
        raise ActivationError("Missing backend environment.") from None


def validate_transition(before: dict[str, Any], after: dict[str, Any]) -> None:
    """Permit exactly one string false -> true; never mutate inspection evidence."""
    require(isinstance(before, dict) and isinstance(after, dict), "Expected Compose objects.")
    old = _backend_environment(before)
    new = _backend_environment(after)
    require(old.get(ENABLED_KEY) == "false", "Previous EODHD state must be literal false.")
    require(new.get(ENABLED_KEY) == "true", "New EODHD state must be literal true.")
    expected = copy.deepcopy(before)
    _backend_environment(expected)[ENABLED_KEY] = "true"
    require(
        _canonical(expected) == _canonical(after),
        "Configuration differs beyond the single EODHD activation flag.",
    )


def summarize_automation(candidate: dict[str, Any]) -> dict[str, bool]:
    environment = _backend_environment(candidate)
    result: dict[str, bool] = {}
    for label, key in AUTOMATION_KEYS.items():
        value = environment.get(key)
        require(
            type(value) is str and value in ("true", "false"),
            "Missing or invalid automation flag: " + label + ".",
        )
        result[label] = value == "true"
    return result


def require_automation_ack(summary: dict[str, bool], allow_existing_automation: bool) -> None:
    require(
        set(summary) == set(AUTOMATION_KEYS)
        and all(type(value) is bool for value in summary.values()),
        "Missing or invalid automation summary.",
    )
    if summary["refresh_enabled"] or summary["monitoring_enabled"]:
        require(
            allow_existing_automation is True,
            "Existing automation can access providers and deliver configured notifications. "
            "Apply requires --allow-existing-automation.",
        )


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _private_directory(path: Path) -> None:
    require(
        path.is_absolute() and not any(ord(c) < 32 for c in str(path)),
        "Expected an absolute private path without control characters.",
    )
    try:
        info = path.lstat()
        require(
            stat.S_ISDIR(info.st_mode)
            and info.st_uid == os.getuid()
            and stat.S_IMODE(info.st_mode) == 0o700
            and path.resolve() == path,
            "Private directory ownership, permissions or path differ.",
        )
    except OSError:
        raise ActivationError("Private directory is unavailable.") from None


def _read_private(path: Path) -> bytes:
    try:
        info = path.lstat()
        require(
            stat.S_ISREG(info.st_mode)
            and info.st_uid == os.getuid()
            and stat.S_IMODE(info.st_mode) == 0o600,
            "Private input ownership, permissions or file type differ.",
        )
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(descriptor, "rb") as source:
            return source.read()
    except OSError:
        raise ActivationError("A private input is unavailable.") from None


def _write_private(path: Path, data: bytes, *, exclusive: bool = False) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW
    flags |= os.O_EXCL if exclusive else os.O_TRUNC
    try:
        descriptor = os.open(path, flags, 0o600)
        with os.fdopen(descriptor, "wb") as destination:
            os.fchmod(destination.fileno(), 0o600)
            destination.write(data)
            destination.flush()
            os.fsync(destination.fileno())
    except OSError:
        raise ActivationError("A private operation record could not be written.") from None


def _write_json(path: Path, value: Any) -> None:
    _write_private(path, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode())


def _append_log(path: Path, content: bytes) -> None:
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, "ab") as destination:
            require(
                stat.S_IMODE(os.fstat(destination.fileno()).st_mode) == 0o600,
                "Private log permissions differ.",
            )
            destination.write(content)
    except OSError:
        raise ActivationError("Private diagnostics could not be written.") from None


def run_command(
    args: list[str],
    *,
    operation_log: Path,
    input_data: bytes | None = None,
    environment: dict[str, str] | None = None,
) -> bytes:
    """Capture all subprocess details privately; never interpolate a shell command."""
    try:
        result = subprocess.run(
            args,
            input=input_data,
            capture_output=True,
            env=environment,
            check=False,
        )
    except OSError as error:
        _append_log(operation_log, ("Subprocess unavailable: " + str(error) + "\n").encode())
        raise ActivationError(
            "A required local command could not be executed; see private diagnostics."
        ) from None
    _append_log(operation_log, b"\nstdout:\n" + result.stdout + b"\nstderr:\n" + result.stderr)
    require(
        result.returncode == 0,
        "A local command failed; details remain in the private operation log.",
    )
    return result.stdout


def _run_file_command(
    args: list[str],
    destination: Path,
    log: Path,
    *,
    source: Path | None = None,
) -> None:
    """Stream potentially large backups instead of loading database contents in memory."""
    try:
        descriptor = os.open(
            destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
        )
        with os.fdopen(descriptor, "wb") as output:
            if source is None:
                result = subprocess.run(
                    args,
                    stdin=subprocess.DEVNULL,
                    stdout=output,
                    stderr=subprocess.PIPE,
                    check=False,
                )
            else:
                with source.open("rb") as input_file:
                    result = subprocess.run(
                        args, stdin=input_file, stdout=output, stderr=subprocess.PIPE, check=False
                    )
            output.flush()
            os.fsync(output.fileno())
        _append_log(log, b"\nbackup stderr:\n" + result.stderr)
        require(
            result.returncode == 0 and destination.stat().st_size > 0,
            "Private backup or archive verification failed.",
        )
    except OSError as error:
        _append_log(log, ("Backup command unavailable: " + str(error) + "\n").encode())
        raise ActivationError("Private backup command failed.") from None


def _seal_entries(state: Path, *, activation: bool = False) -> dict[str, str]:
    _private_directory(state)
    entries: dict[str, str] = {}
    for line in _read_private(state / "inputs.sha256").decode("ascii").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64}) [ *]([A-Za-z0-9_.-]+)", line)
        require(match is not None, "Invalid private input seal.")
        assert match is not None
        checksum, name = match.groups()
        require(name not in entries, "Duplicate private input seal member.")
        entries[name] = checksum
    expected = LEGACY_INPUTS | (ADDITIONAL_INPUTS if activation else set())
    require(set(entries) == expected, "Private input seal members differ.")
    for name, checksum in entries.items():
        require(_digest(_read_private(state / name)) == checksum, "A sealed input has changed.")
    return entries


def _create_seal(state: Path) -> None:
    names = sorted(LEGACY_INPUTS | ADDITIONAL_INPUTS)
    body = "".join(_digest(_read_private(state / name)) + "  " + name + "\n" for name in names)
    _write_private(state / "inputs.sha256", body.encode(), exclusive=True)


def _line(path: Path) -> str:
    value = _read_private(path).decode("utf-8").strip()
    require(
        bool(value) and not any(ord(char) < 32 for char in value),
        "Invalid private identity record.",
    )
    return value


def _layout(base: Path) -> tuple[Path, Path]:
    require(base.is_absolute() and base.resolve() == base, "Base path must be absolute and direct.")
    app, control = base / "trading-workspace-app", base / "trading-workspace-state"
    require(app.is_dir() and not app.is_symlink(), "Managed application directory is unavailable.")
    _private_directory(control)
    for parent in (control, *control.parents):
        require(not (parent / ".git").exists(), "Private state must remain outside Git checkouts.")
    return app, control


@contextmanager
def _lock(control: Path) -> Iterator[None]:
    descriptor = os.open(control / "update.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(descriptor)
        require(
            stat.S_ISREG(info.st_mode)
            and info.st_uid == os.getuid()
            and stat.S_IMODE(info.st_mode) == 0o600,
            "Operation lock ownership or permissions differ.",
        )
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ActivationError("Another managed operation is running.") from None
        yield
    finally:
        os.close(descriptor)


def _current(control: Path) -> Path:
    current = Path(_line(control / "current-state"))
    require(
        current.parent.parent == control / "runs" and current.name == "deployment",
        "Unexpected current-state target.",
    )
    _private_directory(current.parent)
    _private_directory(current)
    require(
        (current / "prepared").is_file() and (current / "deployed").is_file(),
        "Current deployment is not completed.",
    )
    return current


def _legacy(app: Path) -> dict[str, Any]:
    for relative, checksum in LEGACY_HASHES.items():
        path = app / relative
        require(
            path.is_file() and not path.is_symlink() and _digest(path.read_bytes()) == checksum,
            "Pinned legacy deployment tooling differs; review is required.",
        )
    return runpy.run_path(
        str(app / "backend/app/tools/legacy_issuer_deployment.py"),
        run_name="checked_legacy_issuer_deployment",
    )


def _legacy_call(legacy: dict[str, Any], function: str, *args: Any) -> Any:
    try:
        return legacy[function](*args)
    except Exception:
        raise ActivationError(
            "The unchanged legacy deployment validator rejected the state."
        ) from None


def _compose(app: Path, state: Path, log: Path, *args: str, base_only: bool = False) -> bytes:
    command = [
        "docker",
        "compose",
        "--project-name",
        PROJECT,
        "--env-file",
        str(state / "environment.env"),
        "-f",
        str(app / "docker/compose.yml"),
    ]
    if not base_only:
        command += [
            "-f",
            str(app / "docker/compose.issuer-monitoring.yml"),
            "-f",
            str(state / "preserve.json"),
        ]
    environment = dict(os.environ)
    environment["ISSUER_RENDERER_SECCOMP_PATH"] = str(
        app / "docker/issuer-renderer/seccomp_profile.json"
    )
    return run_command(command + list(args), operation_log=log, environment=environment)


def _inspect(log: Path) -> list[dict[str, Any]]:
    names = [PROJECT + "-" + service + "-1" for service in SERVICES]
    ids = run_command(
        [
            "docker",
            "ps",
            "--all",
            "--quiet",
            "--filter",
            "label=com.docker.compose.project=" + PROJECT,
        ],
        operation_log=log,
    )
    require(len(ids.splitlines()) == 4, "Expected exactly the four managed containers.")
    value = parse_json(run_command(["docker", "inspect", *names], operation_log=log))
    require(isinstance(value, list), "Expected container inspection records.")
    return value


def _provider_status(log: Path, *, enabled: bool) -> None:
    source = (
        "import json,urllib.request; "
        "r=urllib.request.urlopen('http://127.0.0.1:8000/health/ready',timeout=10); "
        "assert r.status==200 and json.load(r)['status']=='ready'; "
        "r=urllib.request.urlopen("
        "'http://127.0.0.1:8000/api/v1/market-data/providers/status',timeout=10); "
        "v=json.load(r); assert v['provider']=='EODHD'; "
        "print(json.dumps({'enabled':v['enabled'],'configured':v['configured']}))"
    )
    status = parse_json(
        run_command(
            ["docker", "exec", PROJECT + "-backend-1", "python", "-c", source], operation_log=log
        )
    )
    require(
        status == {"enabled": enabled, "configured": True}
        and type(status.get("enabled")) is bool
        and type(status.get("configured")) is bool,
        "Loaded EODHD enabled/configured status differs.",
    )


def _launcher(app: Path) -> tuple[Path, str]:
    directory = Path(os.environ.get("TRADING_WORKSPACE_BIN_DIR", str(Path.home() / ".local/bin")))
    path = directory / "trading-workspace"
    require(
        path.is_absolute()
        and path.is_file()
        and not path.is_symlink()
        and os.access(path, os.X_OK),
        "The installed managed launcher is unavailable.",
    )
    checksum = _digest(path.read_bytes())
    require(
        checksum == _digest((app / "scripts/trading-workspace.sh").read_bytes()),
        "Installed launcher differs from the checked application launcher.",
    )
    return path, checksum


def _check_images_and_chain(
    items: list[dict[str, Any]],
    app: Path,
    state: Path,
    candidate: dict[str, Any],
    legacy: dict[str, Any],
    log: Path,
) -> None:
    containers = _legacy_call(legacy, "containers_by_service", items)
    chain = ",".join(
        str(path)
        for path in (
            app / "docker/compose.yml",
            app / "docker/compose.issuer-monitoring.yml",
            state / "preserve.json",
        )
    )
    revision = _line(state / "revision")
    require(
        containers["database"]["Id"] == _line(state / "database-container"),
        "Database container identity differs.",
    )
    for service in SERVICES:
        container = containers[service]
        require(
            container["State"].get("Health", {}).get("Status") == "healthy",
            "A managed service is not healthy.",
        )
        if service == "database":
            continue
        require(
            container["Config"]["Labels"].get("com.docker.compose.project.config_files") == chain,
            "Application container Compose provenance differs.",
        )
        image_id = _line(state / (service + ".image"))
        require(container["Image"] == image_id, "Application image identity differs.")
        images = parse_json(
            run_command(
                ["docker", "image", "inspect", candidate["services"][service]["image"]],
                operation_log=log,
            )
        )
        require(
            isinstance(images, list)
            and len(images) == 1
            and images[0]["Id"] == image_id
            and images[0]["Config"].get("Labels", {}).get("org.opencontainers.image.revision")
            == revision,
            "Pinned local image reference or revision differs.",
        )
    helper = parse_json(
        run_command(
            ["docker", "image", "inspect", _line(state / "helper-image")], operation_log=log
        )
    )
    require(
        isinstance(helper, list)
        and len(helper) == 1
        and helper[0]["Id"] == _line(state / "helper-image"),
        "Pinned helper image is unavailable.",
    )


def _validate_old(
    app: Path,
    old: Path,
    log: Path,
    legacy: dict[str, Any],
    *,
    activation_state: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any], str, str]:
    _seal_entries(old, activation=activation_state)
    revision = _line(old / "revision")
    require(
        re.fullmatch(r"[0-9a-f]{40}", revision) is not None
        and _line(old / "release-root") == str(app),
        "Release identity differs.",
    )
    head = (
        run_command(["git", "-C", str(app), "rev-parse", "HEAD"], operation_log=log)
        .decode()
        .strip()
    )
    require(head == revision, "Checkout and sealed release differ.")
    require(
        not run_command(
            ["git", "-C", str(app), "status", "--porcelain", "--untracked-files=all"],
            operation_log=log,
        ).strip(),
        "Application checkout is not clean.",
    )
    origin = (
        run_command(["git", "-C", str(app), "remote", "get-url", "origin"], operation_log=log)
        .decode()
        .strip()
    )
    require(
        origin
        in (
            "https://github.com/burckhju/trading-workspace",
            "https://github.com/burckhju/trading-workspace.git",
        ),
        "Unexpected application origin.",
    )
    version = (app / "VERSION").read_text().strip()
    require(
        re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version) is not None, "Invalid application version."
    )
    candidate = parse_json(_read_private(old / "candidate.json"))
    rendered = parse_json(_compose(app, old, log, "config", "--format", "json"))
    _legacy_call(legacy, "verify_configuration", candidate, rendered)
    items = _inspect(log)
    _legacy_call(legacy, "validate_candidate", items, candidate)
    _check_images_and_chain(items, app, old, candidate, legacy, log)
    return items, candidate, revision, version


def _mark(state: Path, phase: str) -> None:
    _write_private(state / "phase", (phase + "\n").encode())


def _require_idle_control(control: Path) -> None:
    require(not os.path.lexists(control / "pending"), "An earlier managed operation is pending.")
    require(
        not os.path.lexists(control / "current-state.new"),
        "An unfinished state-pointer publication requires review.",
    )


def prepare(base: Path) -> Path:
    app, control = _layout(base)
    _require_idle_control(control)
    with _lock(control):
        _require_idle_control(control)
        old = _current(control)
        _seal_entries(old)
        legacy = _legacy(app)
        launcher_path, launcher_hash = _launcher(app)
        runs = control / "runs"
        _private_directory(runs)
        # Keep the host-side launcher usable before Python 3.11.
        prefix = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-eodhd-")  # noqa: UP017
        operation = Path(tempfile.mkdtemp(prefix=prefix, dir=runs))
        state = operation / "deployment"
        state.mkdir(mode=0o700)
        log = state / "operation.log"
        _mark(state, "prepare-preflight")
        items, before, revision, version = _validate_old(app, old, log, legacy)
        _provider_status(log, enabled=False)
        summary = summarize_automation(before)
        for name in LEGACY_INPUTS - {"environment.env", "baseline.json", "candidate.json"}:
            _write_private(state / name, _read_private(old / name), exclusive=True)
        environment = patch_enabled_environment(
            _read_private(old / "environment.env").decode("utf-8")
        )
        _write_private(state / "environment.env", environment.encode(), exclusive=True)
        _write_json(state / "baseline.json", items)
        candidate = parse_json(_compose(app, state, log, "config", "--format", "json"))
        validate_transition(before, candidate)
        require(summarize_automation(candidate) == summary, "Automation configuration changed.")
        _write_json(state / "candidate.json", candidate)
        tool = Path(__file__).resolve().read_bytes()
        _write_private(state / "activation-tool.py", tool, exclusive=True)
        transition = {
            "schema": 1,
            "operation": "enable-eodhd",
            "old_state": str(old),
            "application_root": str(app),
            "release_revision": revision,
            "release_version": version,
            "old_seal_sha256": _digest(_read_private(old / "inputs.sha256")),
            "old_pointer_sha256": _digest(_read_private(control / "current-state")),
            "tool_sha256": _digest(tool),
            "launcher_path": str(launcher_path),
            "launcher_sha256": launcher_hash,
            "automation": summary,
            "prepared_at": datetime.now(timezone.utc).isoformat(),  # noqa: UP017
        }
        _write_json(state / "transition.json", transition)
        _create_seal(state)
        _write_private(state / "prepared", b"", exclusive=True)
        _mark(state, "prepared")
        _sync_directory(state)
        _sync_directory(operation)
        _sync_directory(runs)
        print("Prepared private EODHD activation: " + str(state))
        print("Application version: " + version + "; unchanged commit: " + revision)
        print("Only configuration change: " + ENABLED_KEY + " false -> true")
        print("Application version, commit and images remain unchanged; no service was modified.")
        print("Existing automation: " + json.dumps(summary, sort_keys=True))
        print("Apply may access providers and deliver existing configured notifications.")
        command = [
            "python3",
            str(state / "activation-tool.py"),
            "apply",
            str(state),
            "--base",
            str(base),
        ]
        if summary["refresh_enabled"] or summary["monitoring_enabled"]:
            command.append("--allow-existing-automation")
        print("After explicit approval, apply in a maintenance window:")
        print(shlex.join(command))
        return state


def _precheck_apply(
    state: Path, allow_existing_automation: bool
) -> tuple[dict[str, Any], dict[str, Any]]:
    # This intentionally precedes any command, lock/log creation or pending marker.
    _private_directory(state)
    candidate = parse_json(_read_private(state / "candidate.json"))
    summary = summarize_automation(candidate)
    require_automation_ack(summary, allow_existing_automation)
    _seal_entries(state, activation=True)
    require(
        (state / "prepared").is_file()
        and not (state / "apply-started").exists()
        and not (state / "deployed").exists(),
        "Activation is not an unused prepared operation.",
    )
    transition = parse_json(_read_private(state / "transition.json"))
    require(
        isinstance(transition, dict)
        and transition.get("schema") == 1
        and transition.get("operation") == "enable-eodhd",
        "Unknown activation record.",
    )
    require(summary == transition.get("automation"), "Recorded automation summary differs.")
    checksum = _digest(Path(__file__).resolve().read_bytes())
    require(
        checksum == transition.get("tool_sha256")
        and checksum == _digest(_read_private(state / "activation-tool.py")),
        "The prepared activation tool differs.",
    )
    return candidate, transition


def _backup(state: Path, log: Path) -> None:
    _run_file_command(
        [
            "docker",
            "exec",
            PROJECT + "-database-1",
            "sh",
            "-c",
            'pg_dump --no-password --format=custom -U "$POSTGRES_USER" -d "$POSTGRES_DB"',
        ],
        state / "database.dump",
        log,
    )
    _run_file_command(
        ["docker", "exec", "-i", PROJECT + "-database-1", "pg_restore", "--list"],
        state / "database.contents",
        log,
        source=state / "database.dump",
    )
    _run_file_command(
        ["docker", "cp", PROJECT + "-issuer-renderer-1:/state/.", "-"],
        state / "consent-state.tar",
        log,
    )
    _run_file_command(
        ["tar", "-tf", str(state / "consent-state.tar")], state / "consent.contents", log
    )
    _write_private(state / "backups-verified", b"", exclusive=True)
    _sync_directory(state)


def _sync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def apply(base: Path, state: Path, allow_existing_automation: bool = False) -> None:
    candidate, transition = _precheck_apply(state, allow_existing_automation)
    app, control = _layout(base)
    require(
        state.parent.parent == control / "runs" and state.name == "deployment",
        "Prepared activation belongs to a different managed installation.",
    )
    _private_directory(state.parent)
    require(transition.get("application_root") == str(app), "Prepared application path differs.")
    _require_idle_control(control)
    with _lock(control):
        # Re-read the bound plan after acquiring the shared operation lock.
        candidate, transition = _precheck_apply(state, allow_existing_automation)
        _require_idle_control(control)
        old = _current(control)
        require(
            str(old) == transition.get("old_state")
            and _digest(_read_private(control / "current-state"))
            == transition.get("old_pointer_sha256")
            and _digest(_read_private(old / "inputs.sha256")) == transition.get("old_seal_sha256"),
            "The previously approved deployment state has changed.",
        )
        legacy = _legacy(app)
        launcher_path, launcher_hash = _launcher(app)
        require(
            str(launcher_path) == transition.get("launcher_path")
            and launcher_hash == transition.get("launcher_sha256"),
            "Installed launcher changed.",
        )
        log = state / "operation.log"
        _mark(state, "apply-preflight")
        live, before, revision, version = _validate_old(app, old, log, legacy)
        require(
            revision == transition.get("release_revision")
            and version == transition.get("release_version"),
            "Application release changed since preparation.",
        )
        _legacy_call(
            legacy, "verify_identity", parse_json(_read_private(state / "baseline.json")), live
        )
        _provider_status(log, enabled=False)
        rendered = parse_json(_compose(app, state, log, "config", "--format", "json"))
        _legacy_call(legacy, "verify_configuration", candidate, rendered)
        validate_transition(before, rendered)
        require_automation_ack(summarize_automation(rendered), allow_existing_automation)
        # All checks above are read-only with respect to the old state and containers.
        _write_private(control / "pending", (str(state.parent) + "\n").encode(), exclusive=True)
        _write_private(state / "apply-started", b"", exclusive=True)
        _mark(state, "stop-and-backup")
        _sync_directory(state)
        _sync_directory(control)
        run_command(
            [
                "docker",
                "stop",
                "--time",
                "60",
                PROJECT + "-backend-1",
                PROJECT + "-issuer-renderer-1",
            ],
            operation_log=log,
        )
        _backup(state, log)
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
        _mark(state, "renderer")
        _compose(app, state, log, *common, "issuer-renderer")
        _mark(state, "application")
        _compose(app, state, log, *common, "backend", "frontend")
        _mark(state, "verification")
        _seal_entries(state, activation=True)
        _seal_entries(old)
        deployed = _inspect(log)
        _legacy_call(legacy, "validate_candidate", deployed, candidate)
        _check_images_and_chain(deployed, app, state, candidate, legacy, log)
        _provider_status(log, enabled=True)
        # The unchanged next-update overlay must accept the persisted new .env.
        base_config = parse_json(
            _compose(app, state, log, "config", "--format", "json", base_only=True)
        )
        _legacy_call(legacy, "make_overlay", deployed, base_config, revision)
        require(
            _digest(_read_private(control / "current-state")) == transition["old_pointer_sha256"]
            and _line(control / "pending") == str(state.parent),
            "Operation ownership changed.",
        )
        _write_json(state / "deployed.json", deployed)
        _write_private(state / "deployed", b"", exclusive=True)
        _mark(state, "publish-state")
        _sync_directory(state)
        _sync_directory(state.parent)
        _write_private(control / "current-state.new", (str(state) + "\n").encode(), exclusive=True)
        os.replace(control / "current-state.new", control / "current-state")
        _sync_directory(control)
        os.replace(control / "pending", state.parent / "completed")
        _sync_directory(control)
        _sync_directory(state.parent)
        _mark(state, "completed")
        print("EODHD enabled and configured. Application release and images are unchanged.")
        print("New managed state: " + str(state))
        print(
            "Existing automation settings are retained in the started backend; no scheduler cycle "
            "is claimed and this tool sent no test message."
        )


class _SafeParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ActivationError("Invalid arguments; use --help. No argument values printed.")


def main(argv: list[str] | None = None) -> int:
    parser = _SafeParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)
    default_base = os.environ.get("TRADING_WORKSPACE_BASE", str(Path.home() / "Boerse"))
    for action in ("prepare", "apply"):
        command = subparsers.add_parser(action)
        command.add_argument("--base", default=default_base, type=Path)
        if action == "apply":
            command.add_argument("state", type=Path)
            command.add_argument("--allow-existing-automation", action="store_true")
    try:
        args = parser.parse_args(argv)
        require(os.getuid() != 0, "Run as the existing deployment owner, not root/sudo.")
        if args.action == "prepare":
            prepare(args.base.expanduser())
        else:
            apply(args.base.expanduser(), args.state.expanduser(), args.allow_existing_automation)
        return 0
    except ActivationError as error:
        print("EODHD activation stopped: " + str(error), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print(
            "EODHD activation interrupted. Retain private diagnostics and any pending marker.",
            file=sys.stderr,
        )
        return 130
    except Exception:
        print(
            "EODHD activation stopped. Inspect private operation diagnostics; "
            "no private values printed. "
            "Do not delete markers or repeat an already started apply.",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
