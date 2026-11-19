"""Real Git and the original launcher, with Docker isolated behind disposable fixtures."""

from __future__ import annotations

import copy
import fcntl
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from app.tools import legacy_issuer_deployment as migration
from tests.unit.backend import test_linux_launcher as launcher_tests
from tests.unit.backend.test_linux_launcher import (
    DOCKER,
    GIT,
    HELPER,
    SUPPORT,
    Installation,
    command,
)
from tests.unit.backend.tools.test_legacy_issuer_deployment import deployment_fixture

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts/retry-linux-update.py"
launcher_installation = launcher_tests.installation


def load_tool() -> ModuleType:
    spec = importlib.util.spec_from_file_location("_linux_update_recovery_tests", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


tool = load_tool()

DOCKER_READS = SUPPORT + r"""
args = sys.argv[1:]
data = json.loads(model.read_text())
items = json.loads((work / 'inspection.json').read_text())
if args[0] == 'inspect' and args[1] != '--format':
    log('docker', args)
    print(json.dumps(items))
elif args[:2] == ['image', 'inspect']:
    log('docker', args)
    reference = args[2]
    matches = [item for item in items
        if reference == item['Image'] or reference == 'trading-workspace-' +
        item['Config']['Labels']['com.docker.compose.service'] + ':migration-' + data['rev']]
    assert len(matches) == 1, args
    print(json.dumps([{'Id':matches[0]['Image'], 'Config':{'Labels':{
        'org.opencontainers.image.revision':data['rev']}}}]))
elif args[0] == 'compose':
    log('docker', args)
    assert args[-3:] == ['config', '--format', 'json'], args
    state = Path(args[args.index('--env-file') + 1]).parent
    print((state / 'candidate.json').read_text())
else:
    exec(ORIGINAL_DOCKER)
"""


def private(path: Path, value: bytes | str) -> None:
    path.write_bytes(value.encode() if isinstance(value, str) else value)
    path.chmod(0o600)


def snapshot(path: Path) -> dict[str, bytes]:
    return {
        str(item.relative_to(path)): item.read_bytes() for item in path.rglob("*") if item.is_file()
    }


@dataclass
class FailedUpdate:
    installation: Installation
    old_revision: str
    target_revision: str
    tag: str
    operation: Path
    failed: Path

    @property
    def app(self) -> Path:
        return self.installation.app

    @property
    def old(self) -> Path:
        return self.installation.state

    @property
    def control(self) -> Path:
        return self.installation.control

    @property
    def base(self) -> Path:
        return self.app.parent

    def close(self, *, tag: str | None = None, revision: str | None = None) -> Path:
        return tool.close_failed_prepare(
            self.base, tag or self.tag, revision or self.target_revision
        )

    def items(self) -> list[dict[str, Any]]:
        return json.loads((self.installation.work / "inspection.json").read_text())

    def change_items(self, items: list[dict[str, Any]]) -> None:
        (self.installation.work / "inspection.json").write_text(json.dumps(items))


@pytest.fixture
def failed_update(
    launcher_installation: Installation, monkeypatch: pytest.MonkeyPatch
) -> FailedUpdate:
    installation = launcher_installation
    app, old, control = installation.app, installation.state, installation.control
    for name in tool.UNCHANGED_FILES:
        destination = app / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, destination)
    (app / "VERSION").write_text("1.5.49\n")
    command(GIT, "add", ".", cwd=app)
    command(GIT, "commit", "-m", "Synthetic qualified old release", cwd=app)
    old_revision = command(GIT, "rev-parse", "HEAD", cwd=app)
    command(GIT, "tag", "v1.5.49", cwd=app)
    command(GIT, "push", str(installation.work / "releases.git"), "HEAD", cwd=app)
    target_revision = installation.release("v1.5.50")
    command(
        GIT,
        "fetch",
        str(installation.work / "releases.git"),
        "refs/tags/v1.5.50:refs/tags/v1.5.50",
        cwd=app,
    )
    command(GIT, "checkout", "--detach", target_revision, cwd=app)
    installation.change_runtime(rev=old_revision)
    items, candidate = deployment_fixture()
    review_environment = {
        "TRADING_WORKSPACE_POSITION_MONITORING__REVIEW_SCOPE": "INDICATIVE_ENTRY_V1",
        "TRADING_WORKSPACE_POSITION_MONITORING__ENABLED": "true",
        "TRADING_WORKSPACE_POSITION_MONITORING__REVIEW_NOTIFICATIONS_ENABLED": "false",
    }
    candidate["services"]["backend"]["environment"].update(review_environment)
    backend_environment = migration.environment(items[0]) | review_environment
    items[0]["Config"]["Env"] = [f"{key}={value}" for key, value in backend_environment.items()]
    private(
        old / "environment.env",
        (old / "environment.env").read_bytes()
        + "".join(f"{key}={value}\n" for key, value in review_environment.items()).encode(),
    )
    chain = ",".join(
        str(path)
        for path in (
            app / "docker/compose.yml",
            app / "docker/compose.issuer-monitoring.yml",
            old / "preserve.json",
        )
    )
    for item in items:
        service = item["Config"]["Labels"]["com.docker.compose.service"]
        item["State"]["Health"] = {"Status": "healthy"}
        if service == "database":
            item["Id"] = "database-unchanged"
        else:
            item["Image"] = f"sha256:{service}-{old_revision}"
            item["Config"]["Labels"]["com.docker.compose.project.config_files"] = chain
            candidate["services"][service][
                "image"
            ] = f"trading-workspace-{service}:migration-{old_revision}"
            private(old / (service + ".image"), item["Image"] + "\n")
    earlier = copy.deepcopy(items)
    for item in earlier:
        item["Id"] = "earlier-" + item["Id"]
        item["Image"] = "sha256:earlier-release"
    private(old / "baseline.json", json.dumps(earlier))
    private(old / "candidate.json", json.dumps(candidate))
    private(
        old / "preserve.json",
        json.dumps(migration.make_overlay(items, candidate, old_revision)),
    )
    private(old / "helper-image", f"sha256:backend-{old_revision}\n")
    private(old / "revision", old_revision + "\n")
    # The real PC has an activated V1 generation, including additional sealed inputs.
    private(old / "activation-tool.py", b"synthetic prior activation tool\n")
    private(
        old / "transition.json",
        json.dumps(
            {
                "schema": 1,
                "operation": "activate-indicative-monitoring",
                "old_activation": False,
                "tool_sha256": tool.digest((old / "activation-tool.py").read_bytes()),
            }
        ),
    )
    support = tool._support(app)
    names = support.LEGACY_INPUTS | support.ADDITIONAL_INPUTS
    private(
        old / "inputs.sha256",
        "".join(
            tool.digest((old / name).read_bytes()) + "  " + name + "\n" for name in sorted(names)
        ),
    )
    for path in (control, *control.rglob("*")):
        path.chmod(0o700 if path.is_dir() else 0o600)
    (installation.work / "inspection.json").write_text(json.dumps(items))
    operation = control / "runs/failed-update"
    operation.mkdir(mode=0o700)
    failed = operation / "deployment"
    failed.mkdir(mode=0o700)
    configuration = operation / "configuration"
    configuration.mkdir(mode=0o700)
    (configuration / "docker").mkdir(mode=0o700)
    private(configuration / "docker/.env", (old / "environment.env").read_bytes())
    private(configuration / "docker/compose.yml", (app / "docker/compose.yml").read_bytes())
    for name, value in {
        "previous-state": str(old),
        "previous-root": str(app),
        "previous-revision": old_revision,
        "target-revision": target_revision,
    }.items():
        private(operation / name, value + "\n")
    private(failed / "baseline.json", json.dumps(items))
    private(failed / "environment.env", (old / "environment.env").read_bytes())
    private(failed / "revision", target_revision + "\n")
    private(failed / "release-root", str(app) + "\n")
    private(failed / "operation.log", "ReadTimeoutError: files.pythonhosted.org\n")
    private(control / "pending", str(operation) + "\n")
    binaries = installation.work / "bin"
    (binaries / "docker").write_text(
        "#!/usr/bin/env python3\nORIGINAL_DOCKER = " + repr(DOCKER) + "\n" + DOCKER_READS
    )
    # An execv of the original #!/usr/bin/env bash launcher must reach real Bash;
    # only its migration-helper subprocess remains simulated in this unit fixture.
    (binaries / "bash").write_text(
        "#!/usr/bin/env python3\nimport os,sys\n"
        "if not sys.argv[1].endswith('/scripts/migrate-legacy-issuer.sh'):\n"
        "    os.execv('/bin/bash', ['/bin/bash', *sys.argv[1:]])\n" + HELPER
    )
    assert installation.run("install").returncode == 0
    for name, value in installation.env.items():
        monkeypatch.setenv(name, value)
    return FailedUpdate(installation, old_revision, target_revision, "v1.5.50", operation, failed)


def assert_unmodified_runtime(fixture: FailedUpdate, before: bytes) -> None:
    assert (fixture.installation.work / "runtime.json").read_bytes() == before
    for call in fixture.installation.calls():
        assert call[:2] not in (["docker", "stop"], ["docker", "start"])
        assert call[0] != "helper"


def test_close_preserves_activated_state_and_uses_failed_not_old_baseline(
    failed_update: FailedUpdate,
) -> None:
    fixture = failed_update
    old, failed = snapshot(fixture.old), snapshot(fixture.failed)
    pointer = (fixture.control / "current-state").read_bytes()
    pending = (fixture.control / "pending").read_bytes()
    runtime = (fixture.installation.work / "runtime.json").read_bytes()
    assert json.loads(old["baseline.json"]) != fixture.items()
    backend = json.loads(old["candidate.json"])["services"]["backend"]["environment"]
    assert backend["TRADING_WORKSPACE_POSITION_MONITORING__REVIEW_SCOPE"] == "INDICATIVE_ENTRY_V1"
    assert backend["TRADING_WORKSPACE_POSITION_MONITORING__ENABLED"] == "true"
    assert (
        migration.environment(fixture.items()[0])[
            "TRADING_WORKSPACE_POSITION_MONITORING__REVIEW_SCOPE"
        ]
        == "INDICATIVE_ENTRY_V1"
    )
    launcher = fixture.close()
    assert launcher.read_bytes() == (ROOT / "scripts/trading-workspace.sh").read_bytes()
    assert command(GIT, "rev-parse", "HEAD", cwd=fixture.app) == fixture.old_revision
    assert snapshot(fixture.old) == old
    assert snapshot(fixture.failed) == failed
    assert (fixture.control / "current-state").read_bytes() == pointer
    assert not (fixture.control / "pending").exists()
    assert (fixture.operation / "aborted-before-apply").read_bytes() == pending
    evidence = json.loads(next(fixture.operation.glob("retry-*.json")).read_text())
    assert evidence["recovery_sha256"] == tool.digest(SCRIPT.read_bytes())
    assert evidence["source_before"] == fixture.target_revision
    assert_unmodified_runtime(fixture, runtime)


class HandedOff(Exception):
    def __init__(self, result: subprocess.CompletedProcess[str]):
        self.result = result


@pytest.mark.parametrize("build_fails", [False, True])
def test_retry_hands_off_unlocked_to_original_launcher_success_or_new_build_failure(
    failed_update: FailedUpdate,
    monkeypatch: pytest.MonkeyPatch,
    build_fails: bool,
) -> None:
    fixture = failed_update
    old, failed = snapshot(fixture.old), snapshot(fixture.failed)
    runtime = (fixture.installation.work / "runtime.json").read_bytes()
    if build_fails:
        (fixture.installation.work / "fail-prepare").touch()

    def execute(path: str, args: list[str]) -> None:
        assert args == [path, "update", fixture.tag, fixture.target_revision]
        assert Path(path).read_bytes() == (ROOT / "scripts/trading-workspace.sh").read_bytes()
        assert os.environ["TRADING_WORKSPACE_BASE"] == str(fixture.base)
        assert_unmodified_runtime(fixture, runtime)
        with (fixture.control / "update.lock").open("r+") as descriptor:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        raise HandedOff(subprocess.run(args, capture_output=True, text=True, timeout=20))

    monkeypatch.setattr(tool.os, "execv", execute)
    with pytest.raises(HandedOff) as handed:
        tool.retry(fixture.base, fixture.tag, fixture.target_revision)
    result = handed.value.result
    assert "never-print-this" not in result.stdout + result.stderr
    assert (result.returncode != 0) is build_fails, result.stdout + result.stderr
    assert snapshot(fixture.old) == old
    assert snapshot(fixture.failed) == failed
    assert (fixture.operation / "aborted-before-apply").is_file()
    assert command(GIT, "rev-parse", "HEAD", cwd=fixture.app) == fixture.target_revision
    current = Path((fixture.control / "current-state").read_text().strip())
    if build_fails:
        assert current == fixture.old
        assert (fixture.installation.work / "runtime.json").read_bytes() == runtime
        pending = Path((fixture.control / "pending").read_text().strip())
        assert pending != fixture.operation
        assert "Synthetic prepare failure" in (pending / "deployment/operation.log").read_text()
        assert not (pending / "deployment/apply-started").exists()
    else:
        assert current != fixture.old and (current / "deployed").is_file()
        assert not (fixture.control / "pending").exists()
        assert (current / "revision").read_text().strip() == fixture.target_revision
        assert (current / "environment.env").read_bytes() == old["environment.env"]
        assert (current / "database-container").read_bytes() == old["database-container"]
        assert (current.parent / "completed").is_file()


@pytest.mark.parametrize(
    "marker", ["prepared", "apply-started", "backups-verified", "migration-started", "deployed"]
)
@pytest.mark.parametrize("dangling_link", [False, True])
def test_every_phase_marker_blocks_even_as_a_dangling_link(
    failed_update: FailedUpdate,
    marker: str,
    dangling_link: bool,
) -> None:
    fixture = failed_update
    path = fixture.failed / marker
    if dangling_link:
        path.symlink_to(fixture.failed / "missing")
    else:
        private(path, b"")
    pending = (fixture.control / "pending").read_bytes()
    with pytest.raises(tool.RecoveryError, match="apply may have started"):
        fixture.close()
    assert command(GIT, "rev-parse", "HEAD", cwd=fixture.app) == fixture.target_revision
    assert (fixture.control / "pending").read_bytes() == pending
    assert not list(fixture.operation.glob("retry-*"))


@pytest.mark.parametrize("marker", ["prepared", "deployed"])
def test_old_success_marker_cannot_be_a_symlink_to_an_existing_file(
    failed_update: FailedUpdate,
    marker: str,
) -> None:
    path = failed_update.old / marker
    path.unlink()
    path.symlink_to(failed_update.old / "revision")
    with pytest.raises(tool.RecoveryError, match="file type"):
        failed_update.close()
    assert (failed_update.control / "pending").exists()


@pytest.mark.parametrize(
    "problem",
    [
        "seal",
        "activation_seal",
        "dirty",
        "origin",
        "sha",
        "tag",
        "tag_version",
        "previous_revision",
        "failed_environment",
        "failed_compose",
        "failed_baseline",
        "runtime_image",
        "runtime_id",
        "database_id",
        "unhealthy",
        "compose_chain",
        "pending_symlink",
        "environment_symlink",
        "private_directory_symlink",
        "pointer_publication",
    ],
)
def test_mismatch_refuses_source_change_and_keeps_original_pending(
    failed_update: FailedUpdate,
    problem: str,
) -> None:
    fixture = failed_update
    kwargs: dict[str, str] = {}
    if problem == "seal":
        private(fixture.old / "environment.env", "SECRET=changed\n")
    elif problem == "activation_seal":
        private(fixture.old / "activation-tool.py", "changed activation\n")
    elif problem == "dirty":
        (fixture.app / "untracked-user-data").write_text("local work")
    elif problem == "origin":
        command(
            GIT,
            "remote",
            "set-url",
            "origin",
            "https://example.invalid/private",
            cwd=fixture.app,
        )
    elif problem == "sha":
        kwargs["revision"] = "f" * 40
    elif problem == "tag":
        kwargs["tag"] = "v1.5.49"
    elif problem == "tag_version":
        command(GIT, "tag", "v1.5.51", fixture.target_revision, cwd=fixture.app)
        kwargs["tag"] = "v1.5.51"
    elif problem == "previous_revision":
        private(fixture.operation / "previous-revision", "f" * 40 + "\n")
    elif problem == "failed_environment":
        private(fixture.failed / "environment.env", "SECRET=changed\n")
    elif problem == "failed_compose":
        private(fixture.operation / "configuration/docker/compose.yml", "services: {}\n")
    elif problem == "failed_baseline":
        baseline = fixture.items()
        baseline[0]["Id"] = "different-before-failed-build"
        private(fixture.failed / "baseline.json", json.dumps(baseline))
    elif problem in {
        "runtime_image",
        "runtime_id",
        "database_id",
        "unhealthy",
        "compose_chain",
    }:
        items = fixture.items()
        if problem == "runtime_image":
            items[0]["Image"] = "sha256:other"
        elif problem == "runtime_id":
            items[0]["Id"] = "unexpected-replacement"
        elif problem == "database_id":
            items[2]["Id"] = "recreated-database"
        elif problem == "unhealthy":
            items[0]["State"]["Health"]["Status"] = "unhealthy"
        else:
            items[0]["Config"]["Labels"]["com.docker.compose.project.config_files"] = "other"
        fixture.change_items(items)
    elif problem == "pending_symlink":
        pending = fixture.control / "pending"
        saved = fixture.control / "saved-pending"
        pending.rename(saved)
        pending.symlink_to(saved)
    elif problem == "environment_symlink":
        path = fixture.failed / "environment.env"
        path.unlink()
        path.symlink_to(fixture.old / "environment.env")
    elif problem == "private_directory_symlink":
        path = fixture.operation / "configuration"
        saved = fixture.operation / "saved-configuration"
        path.rename(saved)
        path.symlink_to(saved, target_is_directory=True)
    else:
        (fixture.control / "current-state.new").symlink_to(fixture.control / "missing")
    pending = (fixture.control / "pending").read_bytes()
    runtime = (fixture.installation.work / "runtime.json").read_bytes()
    with pytest.raises(tool.RecoveryError):
        fixture.close(**kwargs)
    assert command(GIT, "rev-parse", "HEAD", cwd=fixture.app) == fixture.target_revision
    assert (fixture.control / "pending").read_bytes() == pending
    assert_unmodified_runtime(fixture, runtime)


def test_shared_lock_blocks_without_closing_the_failed_operation(
    failed_update: FailedUpdate,
) -> None:
    fixture = failed_update
    with (fixture.control / "update.lock").open("w") as lock:
        (fixture.control / "update.lock").chmod(0o600)
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(tool.RecoveryError, match="Another managed operation"):
            fixture.close()
    assert (fixture.control / "pending").exists()
    assert command(GIT, "rev-parse", "HEAD", cwd=fixture.app) == fixture.target_revision


def test_interrupted_source_return_can_be_rechecked_and_closed(
    failed_update: FailedUpdate,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = failed_update
    checkout = tool._checkout
    runtime = (fixture.installation.work / "runtime.json").read_bytes()
    pending = (fixture.control / "pending").read_bytes()

    def interrupted(*args: Any) -> None:
        checkout(*args)
        raise KeyboardInterrupt

    monkeypatch.setattr(tool, "_checkout", interrupted)
    with pytest.raises(KeyboardInterrupt):
        fixture.close()
    assert command(GIT, "rev-parse", "HEAD", cwd=fixture.app) == fixture.old_revision
    assert (fixture.control / "pending").read_bytes() == pending
    assert not (fixture.operation / "aborted-before-apply").exists()
    # A second call does not need checkout again and must repeat all runtime guards.
    fixture.close()
    assert (fixture.operation / "aborted-before-apply").read_bytes() == pending
    assert_unmodified_runtime(fixture, runtime)


def test_checkout_inherits_the_live_operation_lock(
    failed_update: FailedUpdate,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actual_run = subprocess.run
    inherited: list[int] = []

    def checked_run(args: list[str], **kwargs: Any) -> Any:
        if "checkout" in args:
            descriptors = kwargs.get("pass_fds")
            assert descriptors and len(descriptors) == 1
            inherited.extend(descriptors)
            assert (
                os.fstat(descriptors[0]).st_ino
                == (failed_update.control / "update.lock").stat().st_ino
            )
            with (
                (failed_update.control / "update.lock").open("r+") as contender,
                pytest.raises(BlockingIOError),
            ):
                fcntl.flock(contender, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return actual_run(args, **kwargs)

    monkeypatch.setattr(tool.subprocess, "run", checked_run)
    failed_update.close()
    assert len(inherited) == 1


def test_runtime_change_after_source_return_keeps_pending(
    failed_update: FailedUpdate,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checkout = tool._checkout

    def changed(*args: Any) -> None:
        checkout(*args)
        items = failed_update.items()
        items[0]["Id"] = "concurrently-replaced"
        failed_update.change_items(items)

    monkeypatch.setattr(tool, "_checkout", changed)
    with pytest.raises(tool.RecoveryError, match="validator rejected"):
        failed_update.close()
    assert (failed_update.control / "pending").exists()
    assert not (failed_update.operation / "aborted-before-apply").exists()


@pytest.mark.parametrize("problem", ["compose", "validator", "divergent_history"])
def test_clean_target_contract_or_history_drift_is_rejected(
    failed_update: FailedUpdate,
    problem: str,
) -> None:
    fixture = failed_update
    if problem == "divergent_history":
        tree = command(GIT, "rev-parse", fixture.target_revision + "^{tree}", cwd=fixture.app)
        parent = command(GIT, "rev-parse", fixture.old_revision + "^", cwd=fixture.app)
        target = command(
            GIT,
            "commit-tree",
            tree,
            "-p",
            parent,
            "-m",
            "Divergent synthetic release",
            cwd=fixture.app,
        )
    else:
        relative = (
            "docker/compose.yml"
            if problem == "compose"
            else "backend/app/tools/legacy_issuer_deployment.py"
        )
        path = fixture.app / relative
        path.write_bytes(path.read_bytes() + b"\n# Unqualified contract change\n")
        command(GIT, "commit", "-am", "Changed synthetic deployment contract", cwd=fixture.app)
        target = command(GIT, "rev-parse", "HEAD", cwd=fixture.app)
    command(GIT, "tag", "-f", fixture.tag, target, cwd=fixture.app)
    command(GIT, "checkout", "--detach", target, cwd=fixture.app)
    assert command(GIT, "status", "--porcelain", cwd=fixture.app) == ""
    support = tool._support(fixture.app)
    # Exercise the independent release guard with real Git even on a host whose
    # writable temporary parent is itself a Git checkout. No layout guard is bypassed.
    with pytest.raises(tool.RecoveryError, match=r"contracts differ|ancestry"):
        tool._release_checks(
            support,
            fixture.app,
            fixture.operation / "release-check.log",
            fixture.old_revision,
            fixture.tag,
            target,
        )
    assert (fixture.control / "pending").exists()
    assert command(GIT, "rev-parse", "HEAD", cwd=fixture.app) == target


def test_support_contract_matches_independently_qualified_hashes() -> None:
    expected = {
        "scripts/enable-eodhd-linux.py": (
            "b650c0bf46397c721a382380b2d2061f6261f943e523f1951c4a5c20733ce90a"
        ),
        "scripts/trading-workspace.sh": (
            "6d95aec84f6d91df2283b302c379da91eae1d309a59a13eead920ee9afeb36cb"
        ),
        "scripts/migrate-legacy-issuer.sh": (
            "98e654752c7da85828d7367d19e3f145c43960634dfc831be17778caae7756d9"
        ),
        "backend/app/tools/legacy_issuer_deployment.py": (
            "a9a158d631359fa26554983589c942a9f5ee973de30ec56b4cb6fad8337ffb55"
        ),
    }
    assert expected == tool.PINS
    for relative, checksum in expected.items():
        assert tool.digest((ROOT / relative).read_bytes()) == checksum


@pytest.mark.parametrize("changed", [False, True])
def test_support_loader_rejects_links_and_unknown_bytes(tmp_path: Path, changed: bool) -> None:
    app = tmp_path / "application"
    path = app / "scripts/enable-eodhd-linux.py"
    path.parent.mkdir(parents=True)
    if changed:
        path.write_bytes((ROOT / "scripts/enable-eodhd-linux.py").read_bytes() + b"\n# changed\n")
    else:
        path.symlink_to(ROOT / "scripts/enable-eodhd-linux.py")
    with pytest.raises(tool.RecoveryError, match="support helper"):
        tool._support(app)


def test_cli_rejects_root_and_never_prints_unrecognized_private_arguments(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(tool.os, "getuid", lambda: 0)
    assert tool.main(["retry", "v1.5.50", "a" * 40]) == 2
    assert "not root/sudo" in capsys.readouterr().err
    secret = "PRIVATE-ARGUMENT-MUST-NOT-APPEAR"
    assert tool.main(["retry", "v1.5.50", "a" * 40, "--" + secret]) == 2
    assert secret not in capsys.readouterr().err
