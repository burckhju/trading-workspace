"""Exercise the real build installer with an isolated, network-free pip process."""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]

FAKE_PIP = r"""
import json
import os
import signal
import sys
from pathlib import Path

log = Path(os.environ["FAKE_PIP_LOG"])
attempt = len(log.read_text().splitlines()) + 1 if log.exists() else 1
args = sys.argv[1:]
requirements = Path(args[args.index("--requirement") + 1])
with log.open("a") as handle:
    handle.write(json.dumps({"args": args, "requirements": requirements.read_text()}) + "\n")
codes = json.loads(os.environ["FAKE_PIP_EXIT_CODES"])
code = codes[min(attempt - 1, len(codes) - 1)]
print(f"pip attempt {attempt} stdout", flush=True)
print(f"pip attempt {attempt} error {code}", file=sys.stderr, flush=True)
if code < 0:
    os.kill(os.getpid(), -code)
sys.exit(code)
"""


@dataclass
class Installer:
    directory: Path
    environment: dict[str, str]
    log: Path

    def run(self, codes: list[int]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(self.directory / "install_dependencies.py")],
            # The installer must locate its requirements independently of the caller's cwd.
            cwd=self.directory.parent,
            env={**self.environment, "FAKE_PIP_EXIT_CODES": json.dumps(codes)},
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

    def assert_attempts(self, expected: int) -> None:
        calls = [json.loads(line) for line in self.log.read_text().splitlines()]
        assert len(calls) == expected
        for call in calls:
            # Every attempt installs the same complete file, without --no-deps,
            # ignored requirements, relaxed TLS, or an unbounded pip upgrade.
            assert call["args"] == [
                "install",
                "--no-cache-dir",
                "--index-url",
                "https://pypi.org/simple",
                "--timeout",
                "120",
                "--retries",
                "5",
                "--requirement",
                str(self.directory / "requirements.txt"),
            ]
            assert call["requirements"] == (ROOT / "backend/requirements.txt").read_text()


@pytest.fixture
def installer(tmp_path: Path) -> Installer:
    directory = tmp_path / "backend with spaces"
    directory.mkdir()
    for name in ("install_dependencies.py", "requirements.txt"):
        shutil.copyfile(ROOT / "backend" / name, directory / name)
    modules = tmp_path / "isolated modules"
    modules.mkdir()
    (modules / "pip.py").write_text(FAKE_PIP)
    log = tmp_path / "pip-calls.jsonl"
    return Installer(
        directory=directory,
        environment={
            **os.environ,
            "PYTHONPATH": str(modules),
            "PYTHONDONTWRITEBYTECODE": "1",
            "FAKE_PIP_LOG": str(log),
        },
        log=log,
    )


def test_success_installs_all_requirements_once(installer: Installer) -> None:
    result = installer.run([0])

    assert result.returncode == 0, result.stderr
    installer.assert_attempts(1)
    assert "pip attempt 1 stdout" in result.stdout
    assert "retrying" not in result.stderr


@pytest.mark.parametrize("codes", [[17, 0], [17, 19, 0]])
def test_temporary_failure_retries_complete_installation(
    installer: Installer, codes: list[int]
) -> None:
    result = installer.run(codes)

    assert result.returncode == 0, result.stderr
    installer.assert_attempts(len(codes))
    assert result.stderr.count("retrying in 2s") == len(codes) - 1
    assert "pip attempt 1 error 17" in result.stderr
    assert f"pip attempt {len(codes)} stdout" in result.stdout


def test_persistent_failure_stops_after_three_attempts_with_last_pip_error(
    installer: Installer,
) -> None:
    result = installer.run([17, 19, 23, 0])

    assert result.returncode == 23
    installer.assert_attempts(3)
    assert result.stderr.count("retrying in 2s") == 2
    assert "pip attempt 3 error 23" in result.stderr
    assert "pip attempt 4" not in result.stdout + result.stderr


def test_terminated_pip_stops_without_retry(installer: Installer) -> None:
    result = installer.run([-signal.SIGTERM, 0])

    assert result.returncode == 128 + signal.SIGTERM
    installer.assert_attempts(1)
    assert "retrying" not in result.stderr
