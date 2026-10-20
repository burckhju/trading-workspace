"""Run the actual maintenance entry point against disposable Git/Docker fixtures."""

from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from tests.unit.backend.tools.test_legacy_issuer_deployment import deployment_fixture

ROOT = Path(__file__).resolve().parents[3]

FAKE_DOCKER = r"""#!/usr/bin/env python3
import io, json, os, pathlib, subprocess, sys, tarfile
args = sys.argv[1:]
fixture = pathlib.Path(os.environ["TEST_FIXTURE"])
log_args = list(args)
if "-c" in log_args and "--entrypoint" in log_args:
    log_args[log_args.index("-c") + 1] = "<validator source>"
with (fixture / "calls.jsonl").open("a") as log:
    log.write(json.dumps(log_args) + "\n")
revision = subprocess.check_output(
    ["git", "-C", str(fixture / "release checkout"), "rev-parse", "HEAD"], text=True
).strip()
failed = os.environ.get("TEST_FAIL", "")
if args[0] == "run":
    code_index = args.index("-c") + 1
    command = [sys.executable, "-c", args[code_index], *args[code_index+1:]]
    sys.exit(subprocess.run(command).returncode)
if args[0] == "ps":
    print("a\nb\nc\nd" if failed != "extra-container" else "a\nb\nc\nd\ne")
elif args[0] == "inspect":
    if "--format" in args:
        pattern = args[args.index("--format")+1]
        service = args[-1].removeprefix("trading-workspace-").removesuffix("-1")
        image = f"sha256:{'new' if (fixture / 'replaced').exists() else 'old'}-{service}"
        print("id-database" if pattern == "{{.Id}}" else image)
    else:
        print((fixture / "inspect.json").read_text())
elif args[:2] == ["image", "inspect"]:
    service = args[-1].removeprefix("trading-workspace-").split(":")[0]
    print(revision if "revision" in args[3] else f"sha256:new-{service}")
elif args[:2] == ["volume", "inspect"]:
    print("[]")
elif args[0] == "compose":
    if "config" in args:
        base = args.count("-f") == 1
        print((fixture / ("base.json" if base else "candidate.json")).read_text())
    if "build" in args and failed == "build": sys.exit(1)
    if "up" in args:
        if args[-1] == "issuer-renderer" and failed == "renderer": sys.exit(1)
        if args[-1] == "frontend":
            if failed == "application": sys.exit(1)
            (fixture / "replaced").touch()
    if "alembic" in args and "upgrade" in args and failed == "migration": sys.exit(1)
elif args[0] == "exec":
    if "pg_dump" in args[-1]:
        if failed == "backup": sys.exit(1)
        print("synthetic custom backup")
    if "pg_restore" in args:
        if failed == "backup-list": sys.exit(1)
        print("synthetic TOC")
elif args[0] == "cp":
    if failed == "consent": sys.exit(1)
    with tarfile.open(fileobj=sys.stdout.buffer, mode="w|") as archive:
        data = b"{}"
        info = tarfile.TarInfo("consent-test.json")
        info.size = len(data)
        archive.addfile(info, io.BytesIO(data))
"""


@pytest.fixture
def migration_checkout(tmp_path: Path) -> tuple[Path, Path, dict[str, str]]:
    root = tmp_path / "release checkout"
    for relative in (
        "scripts/migrate-legacy-issuer.sh",
        "backend/app/tools/legacy_issuer_deployment.py",
    ):
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, destination)
    (root / "docker/issuer-renderer").mkdir(parents=True)
    (root / "docker/issuer-renderer/seccomp_profile.json").write_text("{}")
    for name in ("compose.yml", "compose.issuer-monitoring.yml"):
        (root / "docker" / name).write_text("services: {}")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-qm",
            "fixture",
        ],
        check=True,
    )
    legacy = tmp_path / "legacy checkout"
    (legacy / "docker").mkdir(parents=True)
    (legacy / "docker/.env").write_text("PRIVATE=synthetic-secret\n")
    (legacy / "docker/compose.yml").write_text("services: {}")
    items, candidate = deployment_fixture()
    (tmp_path / "inspect.json").write_text(json.dumps(items))
    (tmp_path / "base.json").write_text(json.dumps(candidate))
    (tmp_path / "candidate.json").write_text(json.dumps(candidate))
    binary = tmp_path / "bin"
    binary.mkdir()
    (binary / "docker").write_text(FAKE_DOCKER)
    (binary / "docker").chmod(0o755)
    env = {**os.environ, "TEST_FIXTURE": str(tmp_path), "PATH": f"{binary}:{os.environ['PATH']}"}
    return root, tmp_path / "private state", env


def run(fixture: tuple[Path, Path, dict[str, str]], mode: str) -> subprocess.CompletedProcess[str]:
    root, state, env = fixture
    args = ["bash", str(root / "scripts/migrate-legacy-issuer.sh"), mode]
    if mode == "prepare":
        args.append(str(root.parent / "legacy checkout"))
    args.append(str(state))
    return subprocess.run(args, capture_output=True, text=True, env=env)


def calls(root: Path) -> list[list[str]]:
    path = root.parent / "calls.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def test_equal_rendered_json_does_not_block_apply_or_diagnostics(
    migration_checkout: tuple[Path, Path, dict[str, str]],
) -> None:
    root, state, env = migration_checkout
    assert run(migration_checkout, "prepare").returncode == 0
    rendered = root.parent / "candidate.json"
    rendered.write_text(json.dumps(json.loads(rendered.read_text()), sort_keys=True, indent=4))
    assert rendered.read_bytes() != (state / "candidate.json").read_bytes()
    result = run(migration_checkout, "apply")
    assert result.returncode == 0, result.stderr
    result = subprocess.run(
        ["bash", str(root / "scripts/migrate-legacy-issuer.sh"), "compose", str(state), "ps"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    assert calls(root)[-1][-1] == "ps"


def test_preparation_builds_without_restarting_and_apply_orders_safety_gates(
    migration_checkout: tuple[Path, Path, dict[str, str]],
) -> None:
    root, state, _ = migration_checkout
    before = (root.parent / "legacy checkout/docker/.env").read_bytes()
    result = run(migration_checkout, "prepare")
    assert result.returncode == 0, result.stderr
    prepared = calls(root)
    assert not any(args[0] in ("stop", "cp", "exec") or "up" in args for args in prepared)
    assert (state / "environment.env").read_bytes() == before
    assert (state.stat().st_mode & 0o777) == 0o700
    assert all((path.stat().st_mode & 0o077) == 0 for path in state.iterdir())
    result = run(migration_checkout, "apply")
    assert result.returncode == 0, result.stderr + (state / "operation.log").read_text()
    commands = calls(root)[len(prepared) :]
    stop = next(i for i, args in enumerate(commands) if args[0] == "stop")
    backup = next(i for i, args in enumerate(commands) if "pg_dump" in args[-1])
    consent = next(i for i, args in enumerate(commands) if args[0] == "cp")
    renderer = next(
        i for i, args in enumerate(commands) if "up" in args and args[-1] == "issuer-renderer"
    )
    migration = next(i for i, args in enumerate(commands) if "upgrade" in args)
    application = next(
        i for i, args in enumerate(commands) if "up" in args and args[-1] == "frontend"
    )
    assert stop < backup < consent < renderer < migration < application
    assert all("--no-deps" in args for args in commands if "up" in args or "upgrade" in args)
    assert not any(
        "down" in args or "stamp" in args or args[-2:] == ["up", "database"] for args in commands
    )
    assert (state / "deployed").exists()
    assert (root.parent / "legacy checkout/docker/.env").read_bytes() == before
    assert "synthetic-secret" not in result.stdout + result.stderr
    repeated = run(migration_checkout, "apply")
    assert repeated.returncode != 0
    assert "already started" in repeated.stderr


@pytest.mark.parametrize(
    "failure", ["backup", "backup-list", "consent", "renderer", "migration", "application"]
)
def test_failure_never_crosses_the_next_gate(
    migration_checkout: tuple[Path, Path, dict[str, str]],
    failure: str,
) -> None:
    root, state, env = migration_checkout
    assert run(migration_checkout, "prepare").returncode == 0
    start = len(calls(root))
    env["TEST_FAIL"] = failure
    result = run(migration_checkout, "apply")
    assert result.returncode != 0
    assert not (state / "deployed").exists()
    commands = calls(root)[start:]
    if failure in ("backup", "backup-list", "consent"):
        assert not any("up" in args for args in commands)
        assert not (state / "backups-verified").exists()
    if failure in ("backup", "backup-list", "consent", "renderer"):
        assert not any("alembic" in args for args in commands)
    if failure != "application":
        assert not any("up" in args and args[-1] == "frontend" for args in commands)
    assert "synthetic-secret" not in result.stdout + result.stderr


@pytest.mark.parametrize(
    "drift",
    [
        "environment.env",
        "preserve.json",
        "candidate.json",
        "baseline.json",
        "image",
        "running",
        "ambient",
    ],
)
def test_drift_refuses_apply_before_stopping(
    migration_checkout: tuple[Path, Path, dict[str, str]],
    drift: str,
) -> None:
    root, state, _ = migration_checkout
    assert run(migration_checkout, "prepare").returncode == 0
    start = len(calls(root))
    if drift == "image":
        (state / "backend.image").write_text("other-image")
    elif drift == "running":
        data = json.loads((root.parent / "inspect.json").read_text())
        data[0]["Id"] = "another-container"
        (root.parent / "inspect.json").write_text(json.dumps(data))
    elif drift == "ambient":
        data = json.loads((root.parent / "candidate.json").read_text())
        data["services"]["frontend"]["build"] = {"args": {"VITE_API_BASE_URL": "different"}}
        (root.parent / "candidate.json").write_text(json.dumps(data))
    else:
        with (state / drift).open("a") as output:
            output.write("\nchanged")
    result = run(migration_checkout, "apply")
    assert result.returncode != 0
    assert not any(args[0] == "stop" for args in calls(root)[start:])
    assert not (state / "apply-started").exists()


@pytest.mark.parametrize("failure", ["build", "extra-container", "dirty-checkout", "target-drift"])
def test_preparation_refuses_unreviewed_state_without_service_mutation(
    migration_checkout: tuple[Path, Path, dict[str, str]],
    failure: str,
) -> None:
    root, state, env = migration_checkout
    env["TEST_FAIL"] = failure
    if failure == "dirty-checkout":
        (root / "unreviewed-file").write_text("changed")
    elif failure == "target-drift":
        data: dict[str, Any] = json.loads((root.parent / "candidate.json").read_text())
        data = copy.deepcopy(data)
        data["volumes"]["postgres-data"]["name"] = "empty-volume"
        (root.parent / "candidate.json").write_text(json.dumps(data))
    result = run(migration_checkout, "prepare")
    assert result.returncode != 0
    assert not (state / "prepared").exists()
    assert not any(args[0] in ("stop", "cp", "exec") or "up" in args for args in calls(root))


def newer_tool_checkout(root: Path) -> Path:
    tool = root.parent / "newer tool checkout"
    subprocess.run(["git", "clone", "-q", str(root), str(tool)], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(tool),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "--allow-empty",
            "-qm",
            "new tool",
        ],
        check=True,
    )
    return tool


def test_newer_tool_uses_sealed_release_for_compose_only(
    migration_checkout: tuple[Path, Path, dict[str, str]],
) -> None:
    root, state, env = migration_checkout
    tool = newer_tool_checkout(root)
    # An older release has no config-comparison mode; use the new tool's helper,
    # while keeping that release's own Compose model and pinned revision.
    helper = root / "backend/app/tools/legacy_issuer_deployment.py"
    helper.write_text(
        helper.read_text().replace('elif mode == "config":', 'elif mode == "unavailable":')
    )
    subprocess.run(["git", "-C", str(root), "add", str(helper)], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-qm",
            "older helper without config mode",
        ],
        check=True,
    )
    assert run(migration_checkout, "prepare").returncode == 0
    start = len(calls(root))
    script = str(tool / "scripts/migrate-legacy-issuer.sh")
    result = subprocess.run(
        ["bash", script, "compose", str(state), "exec", "-T", "backend", "python", "--version"],
        env=env,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    commands = calls(root)[start:]
    composed = [args for args in commands if args[0] == "compose"]
    assert composed[-1][-5:] == ["exec", "-T", "backend", "python", "--version"]
    assert all(str(root / "docker/compose.yml") in args for args in composed)
    assert not any(str(tool / "docker/compose.yml") in args for args in composed)
    assert not any(args[0] == "stop" or "up" in args or "build" in args for args in commands)
    result = subprocess.run(
        ["bash", script, "apply", str(state)],
        env=env,
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "Prepared release checkout differs" in result.stderr
    assert not (state / "apply-started").exists()


@pytest.mark.parametrize(
    "drift", ["tool-dirty", "release-dirty", "release-revision", "inputs", "model", "command"]
)
def test_cross_checkout_diagnostics_retain_integrity_gates(
    migration_checkout: tuple[Path, Path, dict[str, str]],
    drift: str,
) -> None:
    root, state, env = migration_checkout
    assert run(migration_checkout, "prepare").returncode == 0
    tool = newer_tool_checkout(root)
    action = "ps"
    if drift == "tool-dirty":
        (tool / "untracked").write_text("private-value")
    elif drift == "release-dirty":
        (root / "untracked").write_text("private-value")
    elif drift == "release-revision":
        subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "-c",
                "user.name=Test",
                "-c",
                "user.email=test@example.invalid",
                "commit",
                "--allow-empty",
                "-qm",
                "drift",
            ],
            check=True,
        )
    elif drift == "inputs":
        (state / "preserve.json").write_text("private-value")
    elif drift == "model":
        data = json.loads((root.parent / "candidate.json").read_text())
        data["services"]["backend"]["environment"]["NEW_SETTING"] = "private-value"
        (root.parent / "candidate.json").write_text(json.dumps(data))
    else:
        action = "up"
    start = len(calls(root))
    result = subprocess.run(
        ["bash", str(tool / "scripts/migrate-legacy-issuer.sh"), "compose", str(state), action],
        env=env,
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "private-value" not in result.stdout + result.stderr
    assert not any(args[0] == "compose" and action in args for args in calls(root)[start:])
    assert not (state / "apply-started").exists()
