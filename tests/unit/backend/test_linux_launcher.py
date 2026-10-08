"""Run the real launcher with disposable Git, sealed state and simulated Docker.

The migration helper is simulated here; the deployment CI also exercises the
launcher against the real helper, PostgreSQL, renderer and application containers.
"""

import fcntl
import hashlib
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts/trading-workspace.sh"
GIT = shutil.which("git") or "git"


def command(*args: str, cwd: Path | None = None) -> str:
    return subprocess.check_output(args, cwd=cwd, text=True, stderr=subprocess.DEVNULL).strip()


SUPPORT = r"""
import hashlib, json, os, subprocess, sys
from pathlib import Path
work = Path(os.environ['TW_TEST_DIR'])
model = work / 'runtime.json'
real_git = os.environ['TW_TEST_GIT']
def git(root, *args):
    return subprocess.check_output([real_git, '-C', str(root), *args], text=True).strip()
def populate(state, root, rev, env):
    state.mkdir(mode=0o700, parents=True, exist_ok=True)
    (state / 'release-root').write_text(str(root) + '\n')
    (state / 'revision').write_text(rev + '\n')
    (state / 'environment.env').write_bytes(env)
    (state / 'preserve.json').write_text('{}\n')
    for service in ['backend', 'frontend', 'issuer-renderer']:
        (state / (service + '.image')).write_text('sha256:' + service + '-' + rev + '\n')
    (state / 'database-container').write_text('database-unchanged\n')
    files = ['revision', 'release-root', 'environment.env', 'preserve.json', 'backend.image',
             'frontend.image', 'issuer-renderer.image', 'database-container']
    (state / 'inputs.sha256').write_text(''.join(
        hashlib.sha256((state / p).read_bytes()).hexdigest() + '  ' + p + '\n' for p in files))
    (state / 'prepared').touch()
def activate(state):
    root = (state / 'release-root').read_text().strip()
    rev = (state / 'revision').read_text().strip()
    services = ['database', 'issuer-renderer', 'backend', 'frontend']
    model.write_text(json.dumps({'root':root, 'state':str(state), 'rev':rev,
        'health': {s:'running healthy' for s in services}}))
    (state / 'deployed').touch()
def log(kind, args):
    with (work / 'calls.jsonl').open('a') as out:
        out.write(json.dumps([kind, *args]) + '\n')
"""

DOCKER = SUPPORT + r"""
args = sys.argv[1:]
log('docker', args)
data = json.loads(model.read_text())
if args == ['info']:
    sys.exit(1 if (work / 'daemon-off').exists() else 0)
elif args[0] == 'ps':
    print('\n'.join(data['health']))
elif args[:2] == ['inspect', '--format']:
    service = args[-1][len('trading-workspace-'):-2]
    template = args[2]
    if 'config_files' in template:
        root, state = data['root'], data['state']
        chain_key = 'database_chain' if service == 'database' else 'chain'
        print(data.get(chain_key, root + '/docker/compose.yml,' + root +
              '/docker/compose.issuer-monitoring.yml,' + state + '/preserve.json'))
    elif 'compose.service' in template: print(service)
    elif template == '{{.Image}}': print(data.get('image', 'sha256:' + service + '-' + data['rev']))
    elif template == '{{.Id}}': print(data.get('database_id', 'database-unchanged'))
    elif '.State.Status' in template: print(data['health'][service])
    else: raise AssertionError(args)
elif args[0] in ['start', 'stop']:
    names = args[1:] if args[0] == 'start' else args[3:]
    for name in names:
        service = name[len('trading-workspace-'):-2]
        data['health'][service] = 'running healthy' if args[0] == 'start' else 'exited unhealthy'
    model.write_text(json.dumps(data))
elif args[0] == 'exec':
    assert args[1] == 'trading-workspace-backend-1'
    assert '/health/ready' in args[-1]
    sys.exit(1 if (work / 'readiness-fails').exists() else 0)
elif args[0] == 'logs': print('Synthetic local backend log')
else: raise AssertionError(args)
"""

HELPER = SUPPORT + r"""
script, mode, *args = sys.argv[1:]
assert script.endswith('/scripts/migrate-legacy-issuer.sh'), sys.argv
root = Path(script).parent.parent
log('helper', [mode, *args])
if mode == 'compose':
    state = Path(args[0])
    assert git(root, 'status', '--porcelain', '--untracked-files=all') == ''
    assert git(root, 'rev-parse', 'HEAD') == (state / 'revision').read_text().strip()
    subprocess.run(['sha256sum', '--check', '--status', 'inputs.sha256'], cwd=state, check=True)
    if (work / 'config-drift').exists(): sys.exit(2)
    print('Synthetic preserved Compose status')
elif mode == 'prepare':
    config, state = map(Path, args)
    runtime = json.loads(model.read_text())
    old = Path(runtime['state'])
    assert (config / 'docker/.env').read_bytes() == (old / 'environment.env').read_bytes()
    previous_compose = git(root, 'show', runtime['rev'] + ':docker/compose.yml')
    assert (config / 'docker/compose.yml').read_text().strip() == previous_compose
    if (work / 'fail-prepare').exists():
        state.mkdir(mode=0o700)
        (state / 'operation.log').write_text('Synthetic prepare failure')
        sys.exit(23)
    populate(state, root, git(root, 'rev-parse', 'HEAD'), (config / 'docker/.env').read_bytes())
elif mode == 'apply':
    state = Path(args[0])
    assert (state / 'prepared').exists()
    activate(state)
else: raise AssertionError(mode)
"""


@dataclass
class Installation:
    work: Path
    app: Path
    control: Path
    state: Path
    launcher: Path
    revision: str
    env: dict[str, str]

    def run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["/bin/bash", str(self.launcher), *args],
            env=self.env,
            capture_output=True,
            text=True,
            timeout=20,
        )

    def calls(self) -> list[list[str]]:
        path = self.work / "calls.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def change_runtime(self, **changes: object) -> None:
        path = self.work / "runtime.json"
        data = json.loads(path.read_text())
        data.update(changes)
        path.write_text(json.dumps(data))

    def release(self, version: str) -> str:
        remote = self.work / "releases.git"
        worktree = self.work / "release-source"
        command(GIT, "clone", "--shared", str(remote), str(worktree))
        command(GIT, "config", "user.name", "Fixture", cwd=worktree)
        command(GIT, "config", "user.email", "fixture@example.invalid", cwd=worktree)
        (worktree / "VERSION").write_text(version.removeprefix("v") + "\n")
        command(GIT, "commit", "-am", "Synthetic release", cwd=worktree)
        command(GIT, "tag", version, cwd=worktree)
        command(GIT, "push", "origin", version, cwd=worktree)
        return command(GIT, "rev-parse", "HEAD", cwd=worktree)


@pytest.fixture
def installation(tmp_path: Path) -> Installation:
    base = tmp_path / "Boerse with spaces"
    app = base / "trading-workspace-app"
    app.mkdir(parents=True)
    for name in (
        "scripts/migrate-legacy-issuer.sh",
        "backend/app/tools/legacy_issuer_deployment.py",
        "docker/compose.yml",
        "docker/compose.issuer-monitoring.yml",
        "VERSION",
    ):
        destination = app / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, destination)
    command(GIT, "init", str(app))
    command(GIT, "config", "user.name", "Fixture", cwd=app)
    command(GIT, "config", "user.email", "fixture@example.invalid", cwd=app)
    command(GIT, "add", ".", cwd=app)
    command(GIT, "commit", "-m", "Synthetic installed release", cwd=app)
    revision = command(GIT, "rev-parse", "HEAD", cwd=app)
    command(GIT, "tag", "v1.5.2", cwd=app)
    command(GIT, "clone", "--bare", str(app), str(tmp_path / "releases.git"))
    command(
        GIT, "remote", "add", "origin", "https://github.com/burckhju/trading-workspace.git", cwd=app
    )
    control = base / "trading-workspace-state"
    control.mkdir(mode=0o700)
    state = control / "runs/initial/deployment"
    env = {**os.environ, "TW_TEST_DIR": str(tmp_path), "TW_TEST_GIT": GIT}
    setup = tmp_path / "setup.py"
    setup.write_text(
        SUPPORT + "\npopulate(Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], "
        "b'PRIVATE_FIXTURE=never-print-this\\n')\nactivate(Path(sys.argv[1]))\n"
    )
    subprocess.run(["python3", str(setup), str(state), str(app), revision], env=env, check=True)
    (control / "current-state").write_text(str(state) + "\n")
    binaries = tmp_path / "bin"
    binaries.mkdir()
    scripts = {
        "docker": "#!/usr/bin/env python3\n" + DOCKER,
        "bash": "#!/usr/bin/env python3\n" + HELPER,
        "id": '#!/bin/sh\nprintf "1000\\n"\n',
        "git": "#!/usr/bin/env python3\n" + SUPPORT + "\nargs = sys.argv[1:]\n"
        "if 'fetch' in args:\n    args[args.index('fetch') + 1] = str(work / 'releases.git')\n"
        "os.execv(real_git, [real_git, *args])\n",
    }
    for name, content in scripts.items():
        path = binaries / name
        path.write_text(content)
        path.chmod(0o700)
    launcher = tmp_path / "trading-workspace.sh"
    shutil.copyfile(SCRIPT, launcher)
    env.update(
        PATH=f"{binaries}:{os.environ['PATH']}",
        TRADING_WORKSPACE_BASE=str(base),
        TRADING_WORKSPACE_BIN_DIR=str(tmp_path / "user bin $literal%"),
        XDG_DATA_HOME=str(tmp_path / "user data"),
        DISPLAY="",
        WAYLAND_DISPLAY="",
    )
    return Installation(tmp_path, app, control, state, launcher, revision, env)


def assert_success(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 0, result.stdout + result.stderr
    assert "never-print-this" not in result.stdout + result.stderr


def assert_no_mutation(installation: Installation) -> None:
    for args in installation.calls():
        assert args[:2] not in (["docker", "start"], ["docker", "stop"])
        assert args[:2] not in (["helper", "prepare"], ["helper", "apply"])


def test_running_start_and_status_keep_images_containers_and_private_state(
    installation: Installation,
) -> None:
    installation.change_runtime(database_chain="/old/installation/compose.yml,/old/overlay.yml")
    before = {path.name: path.read_bytes() for path in installation.state.iterdir()}
    assert_success(installation.run())
    assert_success(installation.run("status"))
    assert_no_mutation(installation)
    assert {path.name: path.read_bytes() for path in installation.state.iterdir()} == before
    assert len(list((installation.control / "runs").iterdir())) == 1


def test_stop_and_start_reuse_existing_containers_in_dependency_order(
    installation: Installation,
) -> None:
    assert_success(installation.run("stop"))
    stopped = installation.run("status")
    assert stopped.returncode != 0
    assert_success(installation.run("start"))
    calls = installation.calls()
    assert [a[2] for a in calls if a[:2] == ["docker", "start"]] == [
        f"trading-workspace-{service}-1"
        for service in ("database", "issuer-renderer", "backend", "frontend")
    ]
    assert not any(a[:2] in (["helper", "prepare"], ["helper", "apply"]) for a in calls)
    assert not any(set(a).intersection({"build", "up", "down", "rm", "volume"}) for a in calls)


@pytest.mark.parametrize(
    "problem",
    [
        "chain",
        "image",
        "database_id",
        "missing",
        "pending",
        "seal",
        "dirty",
        "daemon-off",
        "config-drift",
    ],
)
def test_preflight_blocks_mutations_on_mismatch(installation: Installation, problem: str) -> None:
    if problem in {"chain", "image", "database_id"}:
        installation.change_runtime(**{problem: "unexpected"})
    elif problem == "missing":
        installation.change_runtime(health={"backend": "running healthy"})
    elif problem == "pending":
        (installation.control / "pending").write_text("unfinished")
    elif problem == "seal":
        (installation.state / "environment.env").write_text("changed")
    elif problem == "dirty":
        (installation.app / "VERSION").write_text("changed")
    else:
        (installation.work / problem).touch()
    assert installation.run("start").returncode != 0
    assert_no_mutation(installation)


def test_parallel_control_cannot_start_or_stop(installation: Installation) -> None:
    with (installation.control / "update.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = installation.run("stop")
    assert result.returncode != 0
    assert "läuft bereits" in result.stderr
    assert_no_mutation(installation)


def test_unhealthy_renderer_stops_before_backend_start(installation: Installation) -> None:
    installation.change_runtime(
        health={
            "database": "running healthy",
            "issuer-renderer": "running unhealthy",
            "backend": "exited unhealthy",
            "frontend": "exited unhealthy",
        }
    )
    assert installation.run("start").returncode != 0
    assert_no_mutation(installation)


def test_readiness_failure_is_not_reported_as_ready(installation: Installation) -> None:
    (installation.work / "readiness-fails").touch()
    result = installation.run("start")
    assert result.returncode != 0
    assert "Trading Workspace ist bereit" not in result.stdout


def test_install_is_repeatable_and_leaves_application_clean(installation: Installation) -> None:
    assert_success(installation.run("install"))
    assert_success(installation.run("install"))
    target = Path(installation.env["TRADING_WORKSPACE_BIN_DIR"]) / "trading-workspace"
    assert target.read_bytes() == SCRIPT.read_bytes()
    assert target.stat().st_mode & 0o777 == 0o700
    menu = Path(installation.env["XDG_DATA_HOME"]) / "applications/trading-workspace.desktop"
    text = menu.read_text()
    assert "Terminal=true" in text and "Actions=Status;Stop;" in text
    assert r"\\$literal%%" in text
    assert " start --desktop" in text
    assert command(GIT, "status", "--porcelain", cwd=installation.app) == ""
    assert installation.calls() == []


def test_logs_read_existing_backend_only(installation: Installation) -> None:
    assert_success(installation.run("logs"))
    assert installation.calls()[-1] == [
        "docker",
        "logs",
        "--tail",
        "100",
        "trading-workspace-backend-1",
    ]
    assert_no_mutation(installation)


@pytest.mark.parametrize(
    "args", [("update",), ("update", "main", "x"), ("start", "--build"), ("unknown",)]
)
def test_bad_arguments_do_not_touch_docker(
    installation: Installation, args: tuple[str, ...]
) -> None:
    assert installation.run(*args).returncode != 0
    assert installation.calls() == []


def test_same_release_update_is_noop_and_mismatched_tag_is_rejected(
    installation: Installation,
) -> None:
    assert_success(installation.run("update", "v1.5.2", installation.revision))
    assert installation.run("update", "v1.5.2", "0" * 40).returncode != 0
    assert_no_mutation(installation)
    assert not (installation.control / "pending").exists()


def test_update_keeps_fixed_folder_and_old_source_and_configuration(
    installation: Installation,
) -> None:
    target = installation.release("v1.5.3")
    original_env = (installation.state / "environment.env").read_bytes()
    assert_success(installation.run("update", "v1.5.3", target))
    assert command(GIT, "rev-parse", "HEAD", cwd=installation.app) == target
    new_state = Path((installation.control / "current-state").read_text().strip())
    assert new_state != installation.state
    assert (new_state / "environment.env").read_bytes() == original_env
    assert (installation.state / "environment.env").read_bytes() == original_env
    assert (new_state.parent / "source-before.tar").stat().st_size > 0
    assert not (installation.control / "pending").exists()
    assert not (installation.app.parent / "trading-workspace-v1.5.3").exists()


def test_failed_update_keeps_current_pointer_and_blocks_retry(installation: Installation) -> None:
    target = installation.release("v1.5.3")
    (installation.work / "fail-prepare").touch()
    assert installation.run("update", "v1.5.3", target).returncode != 0
    assert (installation.control / "pending").exists()
    assert Path((installation.control / "current-state").read_text().strip()) == installation.state
    runtime = json.loads((installation.work / "runtime.json").read_text())
    assert runtime["rev"] == installation.revision
    count = len(installation.calls())
    assert installation.run("start").returncode != 0
    assert len(installation.calls()) == count


def test_launcher_does_not_change_the_pinned_migration_helpers() -> None:
    content = SCRIPT.read_text()
    for name in (
        "scripts/migrate-legacy-issuer.sh",
        "backend/app/tools/legacy_issuer_deployment.py",
    ):
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() in content
