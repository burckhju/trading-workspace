"""Exercise the actual startup entry point with a disposable checkout and fake Docker."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "start-linux.sh"


@pytest.fixture
def checkout(tmp_path: Path) -> tuple[Path, dict[str, str], Path]:
    root = tmp_path / "checkout with spaces"
    (root / "scripts").mkdir(parents=True)
    (root / "docker").mkdir()
    shutil.copy2(SCRIPT, root / "scripts/start-linux.sh")
    (root / "docker/.env").write_text(
        "POSTGRES_PASSWORD=test-only-value\n"
        "TRADING_WORKSPACE_DATABASE_URL=postgresql+asyncpg://user:test-only-value@database/test\n"
    )
    for name in ("compose.yml", "compose.frankfurt.yml", "compose.issuer-monitoring.yml"):
        (root / "docker" / name).write_text("services: {}\n")
    (root / "docker/issuer-renderer").mkdir()
    (root / "docker/issuer-renderer/seccomp_profile.json").write_text("{}\n")
    (root / "docker/.env.example").write_text("POSTGRES_PASSWORD=change-me\n")
    binary = tmp_path / "bin"
    binary.mkdir()
    executable = binary / "docker"
    executable.write_text(
        "#!/usr/bin/env python3\nimport json, os, sys\n"
        'with open(os.environ["TEST_DOCKER_LOG"], "a") as f:\n'
        '    f.write(json.dumps(sys.argv[1:]) + "\\n")\n'
        "args = sys.argv[1:]\n"
        'if args[-3:] == ["ps", "--all", "--quiet"]:\n'
        '    print(os.environ.get("TEST_CONTAINERS", ""))\n'
        'if args[0] == "inspect":\n'
        '    print(os.environ.get("TEST_CONFIG_FILES", ""))\n'
        '    sys.exit(int(os.environ.get("TEST_INSPECT_EXIT", "0")))\n'
        'if args[-4:] == ["--wait", "--wait-timeout", "120", "issuer-renderer"]:\n'
        '    sys.exit(int(os.environ.get("TEST_RENDERER_EXIT", "0")))\n'
        'if "alembic" in args:\n'
        '    sys.exit(int(os.environ.get("TEST_MIGRATION_EXIT", "0")))\n'
    )
    executable.chmod(0o755)
    log = tmp_path / "docker.log"
    env = {**os.environ, "PATH": f"{binary}:{os.environ['PATH']}", "TEST_DOCKER_LOG": str(log)}
    return root, env, log


@pytest.mark.parametrize("with_frankfurt", [False, True])
def test_start_preserves_opt_in_overlay_and_migrates_before_app_start(
    checkout: tuple[Path, dict[str, str], Path], with_frankfurt: bool
) -> None:
    root, env, log = checkout
    original_env = (root / "docker/.env").read_bytes()
    extra = root / "docker/frankfurt.env"
    config = "TRADING_WORKSPACE_MARKET_DATA__FRANKFURT__ENABLED=false\n"
    if with_frankfurt:
        extra.write_text(config)
    result = subprocess.run(
        ["bash", str(root / "scripts/start-linux.sh")], env=env, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    commands = [json.loads(line) for line in log.read_text().splitlines()]
    operational = [args for args in commands if args != ["compose", "version"]]
    assert operational
    overlay = str(root / "docker/compose.frankfurt.yml")
    for args in operational:
        assert (overlay in args) is with_frankfurt
        assert str(root / "docker/.env") in args
    migration = next(i for i, args in enumerate(commands) if "alembic" in args)
    app_start = next(
        i for i, args in enumerate(commands) if args[-4:] == ["up", "-d", "backend", "frontend"]
    )
    assert migration < app_start
    assert (root / "docker/.env").read_bytes() == original_env
    assert "test-only-value" not in result.stdout + result.stderr
    if with_frankfurt:
        assert extra.read_text() == config  # No activation/subscription is inferred.
        assert "compose.frankfurt.yml logs" in result.stdout
    else:
        assert not extra.exists()


def test_explicit_frankfurt_requires_existing_config_without_any_docker_action(
    checkout: tuple[Path, dict[str, str], Path],
) -> None:
    root, env, log = checkout
    result = subprocess.run(
        ["bash", str(root / "scripts/start-linux.sh"), "--frankfurt"],
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "frankfurt.env is missing" in result.stderr
    assert not log.exists()
    assert not (root / "docker/frankfurt.env").exists()


@pytest.mark.parametrize("argument,code", [("--help", 0), ("--unknown", 2)])
def test_argument_validation_never_starts_containers(
    checkout: tuple[Path, dict[str, str], Path], argument: str, code: int
) -> None:
    root, env, log = checkout
    result = subprocess.run(
        ["bash", str(root / "scripts/start-linux.sh"), argument],
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == code
    assert not log.exists()


def _run(
    checkout: tuple[Path, dict[str, str], Path], *args: str
) -> subprocess.CompletedProcess[str]:
    root, env, _ = checkout
    return subprocess.run(
        ["bash", str(root / "scripts/start-linux.sh"), *args],
        cwd=root.parent,
        env=env,
        capture_output=True,
        text=True,
    )


def _commands(log: Path) -> list[list[str]]:
    return [json.loads(line) for line in log.read_text().splitlines()]


def _assert_no_mutation(commands: list[list[str]]) -> None:
    assert all(not {"build", "up", "run", "down"}.intersection(args) for args in commands)


def test_existing_issuer_overlay_cannot_be_silently_dropped(
    checkout: tuple[Path, dict[str, str], Path],
) -> None:
    root, env, log = checkout
    env["TEST_CONTAINERS"] = "existing-backend"
    env["TEST_CONFIG_FILES"] = (
        f"{root}/docker/compose.yml,{root}/docker/compose.issuer-monitoring.yml"
    )
    result = _run(checkout)
    assert result.returncode == 2
    assert "omits or reorders" in result.stderr
    _assert_no_mutation(_commands(log))
    assert not (root / "docker/stuttgart-data").exists()


def test_issuer_start_builds_and_checks_renderer_before_migration_and_app(
    checkout: tuple[Path, dict[str, str], Path],
) -> None:
    root, env, log = checkout
    env["TEST_CONTAINERS"] = "existing-backend\nstopped-frontend"
    extra = root / "docker/exchange extra.yml"
    extra.write_text("services: {}\n")
    (root / "docker/frankfurt.env").write_text("FRANKFURT_UNCHANGED=true\n")
    original_env = (root / "docker/.env").read_bytes()
    chain = [
        root / "docker/compose.yml",
        root / "docker/compose.frankfurt.yml",
        extra,
        root / "docker/compose.issuer-monitoring.yml",
    ]
    env["TEST_CONFIG_FILES"] = ",".join(map(str, chain))
    result = _run(checkout, "--issuer-monitoring", "--overlay", "docker/exchange extra.yml")
    assert result.returncode == 0, result.stderr
    commands = _commands(log)
    for args in commands:
        if args[0] == "compose" and args != ["compose", "version"]:
            assert [args[i + 1] for i, value in enumerate(args) if value == "-f"] == list(
                map(str, chain)
            )
    assert sum(args[0] == "inspect" for args in commands) == 2
    build = next(i for i, args in enumerate(commands) if "build" in args)
    assert commands[build][-3:] == ["backend", "frontend", "issuer-renderer"]
    health = next(i for i, args in enumerate(commands) if "--wait-timeout" in args)
    assert commands[health][-7:] == [
        "up",
        "-d",
        "--no-deps",
        "--wait",
        "--wait-timeout",
        "120",
        "issuer-renderer",
    ]
    migration = next(i for i, args in enumerate(commands) if "alembic" in args)
    assert "--no-deps" in commands[migration]
    app = next(
        i
        for i, args in enumerate(commands)
        if args[-2:] == ["backend", "frontend"] and "up" in args
    )
    assert build < health < migration < app
    assert (root / "docker/.env").read_bytes() == original_env
    assert "test-only-value" not in result.stdout + result.stderr
    # Printed diagnostic command must be runnable from a different working directory.
    hint = next(
        line.removeprefix("Status:    ")
        for line in result.stdout.splitlines()
        if line.startswith("Status:")
    )
    subprocess.run(["bash", "-c", hint], env=env, cwd=root.parent, check=True)
    assert _commands(log)[-1][-1] == "ps"
    assert str(extra) in _commands(log)[-1]


@pytest.mark.parametrize("failure", ["TEST_RENDERER_EXIT", "TEST_MIGRATION_EXIT"])
def test_issuer_start_failure_never_recreates_backend(
    checkout: tuple[Path, dict[str, str], Path], failure: str
) -> None:
    _, env, log = checkout
    env[failure] = "1"
    result = _run(checkout, "--issuer-monitoring")
    assert result.returncode != 0
    commands = _commands(log)
    assert not any("up" in args and "backend" in args for args in commands)
    if failure == "TEST_RENDERER_EXIT":
        assert not any("alembic" in args for args in commands)
    assert not any("down" in args for args in commands)


@pytest.mark.parametrize("label", ["", "<no value>", "reordered", "omitted"])
def test_unreadable_or_incomplete_existing_chain_fails_closed(
    checkout: tuple[Path, dict[str, str], Path], label: str
) -> None:
    root, env, log = checkout
    env["TEST_CONTAINERS"] = "stopped-backend"
    extra = root / "docker/extra.yml"
    extra.write_text("services: {}\n")
    env["TEST_CONFIG_FILES"] = {
        "reordered": f"{extra},{root}/docker/compose.yml",
        "omitted": f"{root}/docker/compose.yml,{root}/docker/old-package.yml",
    }.get(label, label)
    result = _run(checkout, "--overlay", str(extra))
    assert result.returncode == 2
    _assert_no_mutation(_commands(log))


def test_inspect_failure_stops_before_build(checkout: tuple[Path, dict[str, str], Path]) -> None:
    _, env, log = checkout
    env.update(TEST_CONTAINERS="existing-backend", TEST_INSPECT_EXIT="1")
    assert _run(checkout).returncode != 0
    _assert_no_mutation(_commands(log))


def test_check_validates_without_creating_cache_or_changing_env(
    checkout: tuple[Path, dict[str, str], Path],
) -> None:
    root, _, log = checkout
    before = (root / "docker/.env").read_bytes()
    result = _run(checkout, "--issuer-monitoring", "--check")
    assert result.returncode == 0, result.stderr
    _assert_no_mutation(_commands(log))
    assert not (root / "docker/stuttgart-data").exists()
    assert (root / "docker/.env").read_bytes() == before


def test_check_does_not_create_missing_environment(
    checkout: tuple[Path, dict[str, str], Path],
) -> None:
    root, _, log = checkout
    (root / "docker/.env").unlink()
    assert _run(checkout, "--check").returncode == 2
    assert not (root / "docker/.env").exists()
    _assert_no_mutation(_commands(log))


@pytest.mark.parametrize("args", [("--overlay",), ("--overlay", "absent.yml")])
def test_invalid_overlay_stops_before_docker(
    checkout: tuple[Path, dict[str, str], Path], args: tuple[str, ...]
) -> None:
    _, _, log = checkout
    assert _run(checkout, *args).returncode == 2
    assert not log.exists()
