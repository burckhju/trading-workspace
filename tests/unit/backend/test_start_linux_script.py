"""Exercise the actual startup entry point with a disposable checkout and fake Docker."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "start-linux.sh"


@pytest.fixture
def checkout(tmp_path):
    root = tmp_path / "checkout with spaces"
    (root / "scripts").mkdir(parents=True)
    (root / "docker").mkdir()
    shutil.copy2(SCRIPT, root / "scripts/start-linux.sh")
    (root / "docker/.env").write_text(
        "POSTGRES_PASSWORD=test-only-value\n"
        "TRADING_WORKSPACE_DATABASE_URL=postgresql+asyncpg://user:test-only-value@database/test\n"
    )
    binary = tmp_path / "bin"
    binary.mkdir()
    executable = binary / "docker"
    executable.write_text(
        "#!/usr/bin/env python3\nimport json, os, sys\n"
        'with open(os.environ["TEST_DOCKER_LOG"], "a") as f:\n'
        '    f.write(json.dumps(sys.argv[1:]) + "\\n")\n'
    )
    executable.chmod(0o755)
    log = tmp_path / "docker.log"
    env = {**os.environ, "PATH": f"{binary}:{os.environ['PATH']}", "TEST_DOCKER_LOG": str(log)}
    return root, env, log


@pytest.mark.parametrize("with_frankfurt", [False, True])
def test_start_preserves_opt_in_overlay_and_migrates_before_app_start(checkout, with_frankfurt):
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
        assert "-f docker/compose.frankfurt.yml logs" in result.stdout
    else:
        assert not extra.exists()


def test_explicit_frankfurt_requires_existing_config_without_any_docker_action(checkout):
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
def test_argument_validation_never_starts_containers(checkout, argument, code):
    root, env, log = checkout
    result = subprocess.run(
        ["bash", str(root / "scripts/start-linux.sh"), argument],
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == code
    assert not log.exists()
