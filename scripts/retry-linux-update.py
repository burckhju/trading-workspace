#!/usr/bin/env python3
"""Close a proven pre-apply failure and retry or replace via the unchanged launcher.

Run this support file outside the application checkout. It restores only the old
source commit, archives the failed pending record, then executes the installed
launcher. The launcher owns all building, backups, migrations and publication.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import runpy
import stat
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any, NoReturn

SUPPORT_PATH = "scripts/enable-eodhd-linux.py"
SUPPORT_SHA256 = "b650c0bf46397c721a382380b2d2061f6261f943e523f1951c4a5c20733ce90a"
PINS = {
    SUPPORT_PATH: SUPPORT_SHA256,
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
UNCHANGED_FILES = (
    *PINS,
    "docker/compose.yml",
    "docker/compose.issuer-monitoring.yml",
    "docker/issuer-renderer/seccomp_profile.json",
)
PHASE_MARKERS = (
    "prepared",
    "apply-started",
    "backups-verified",
    "migration-started",
    "deployed",
)
ORIGINS = (
    "https://github.com/burckhju/trading-workspace",
    "https://github.com/burckhju/trading-workspace.git",
)


class RecoveryError(ValueError):
    """A public diagnostic containing no private input or subprocess output."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RecoveryError(message)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _support(app: Path) -> SimpleNamespace:
    path = app / SUPPORT_PATH
    require(
        path.is_file() and path.resolve() == path and digest(path.read_bytes()) == SUPPORT_SHA256,
        "The qualified support helper is unavailable or changed.",
    )
    return SimpleNamespace(**runpy.run_path(str(path), run_name="checked_recovery_support"))


@contextmanager
def _lock(control: Path) -> Iterator[int]:
    descriptor = os.open(control / "update.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(descriptor)
        require(
            stat.S_ISREG(info.st_mode)
            and info.st_uid == os.getuid()
            and stat.S_IMODE(info.st_mode) == 0o600,
            "Operation lock ownership, permissions or type differ.",
        )
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RecoveryError("Another managed operation is running.") from None
        yield descriptor
    finally:
        os.close(descriptor)


def _git(support: SimpleNamespace, app: Path, log: Path, *args: str) -> bytes:
    return support.run_command(["git", "-C", str(app), *args], operation_log=log)


def _phase_is_unused(state: Path) -> None:
    require(
        not any(os.path.lexists(state / name) for name in PHASE_MARKERS),
        "Preparation completed or apply may have started; automatic retry is refused.",
    )


def _release_checks(
    support: SimpleNamespace,
    app: Path,
    log: Path,
    old_revision: str,
    tag: str,
    target_revision: str,
) -> str:
    head = _git(support, app, log, "rev-parse", "HEAD").decode().strip()
    require(
        head in (old_revision, target_revision),
        "Checkout is outside the failed transition.",
    )
    require(
        not _git(support, app, log, "status", "--porcelain", "--untracked-files=all").strip(),
        "Application checkout is not clean.",
    )
    require(
        _git(support, app, log, "remote", "get-url", "origin").decode().strip() in ORIGINS,
        "Unexpected application origin.",
    )
    require(
        _git(support, app, log, "rev-parse", "refs/tags/" + tag + "^{commit}").decode().strip()
        == target_revision,
        "The requested release tag does not identify the approved target.",
    )
    require(
        _git(support, app, log, "show", target_revision + ":VERSION").decode().strip() == tag[1:],
        "Target VERSION and requested release tag differ.",
    )
    try:
        _git(
            support,
            app,
            log,
            "merge-base",
            "--is-ancestor",
            old_revision,
            target_revision,
        )
    except support.ActivationError:
        raise RecoveryError("The source-to-target ancestry could not be verified.") from None
    for relative in UNCHANGED_FILES:
        before = _git(support, app, log, "show", old_revision + ":" + relative)
        after = _git(support, app, log, "show", target_revision + ":" + relative)
        path = app / relative
        require(
            before == after
            and path.is_file()
            and path.resolve() == path
            and path.read_bytes() == after,
            "Source and target deployment contracts differ.",
        )
        if relative in PINS:
            require(digest(after) == PINS[relative], "Deployment tooling is not qualified.")
    return head


def _old_runtime(
    support: SimpleNamespace, app: Path, old: Path, log: Path, legacy: dict[str, Any]
) -> list[dict[str, Any]]:
    candidate = support.parse_json(support._read_private(old / "candidate.json"))
    rendered = support.parse_json(support._compose(app, old, log, "config", "--format", "json"))
    support._legacy_call(legacy, "verify_configuration", candidate, rendered)
    items = support._inspect(log)
    support._legacy_call(legacy, "validate_candidate", items, candidate)
    support._check_images_and_chain(items, app, old, candidate, legacy, log)
    return items


def _replacement_checks(
    support: SimpleNamespace,
    app: Path,
    log: Path,
    old_revision: str,
    failed_revision: str,
    tag: str,
    revision: str,
) -> str:
    """Verify a separately published replacement before closing the failed attempt."""
    reference = "refs/tags/" + tag
    published: dict[str, str] = {}
    for line in (
        _git(support, app, log, "ls-remote", "--exit-code", "origin", reference, reference + "^{}")
        .decode()
        .splitlines()
    ):
        fields = line.split()
        require(
            len(fields) == 2
            and re.fullmatch(r"[0-9a-f]{40}", fields[0]) is not None
            and fields[1] in (reference, reference + "^{}")
            and fields[1] not in published,
            "The published replacement tag could not be verified.",
        )
        published[fields[1]] = fields[0]
    require(
        reference in published
        and published.get(reference + "^{}", published[reference]) == revision,
        "The published replacement tag does not identify the approved replacement.",
    )
    local_tags = (
        _git(support, app, log, "for-each-ref", "--format=%(objectname) %(refname)", reference)
        .decode()
        .splitlines()
    )
    require(
        not local_tags or local_tags == [published[reference] + " " + reference],
        "An existing local replacement tag differs from the published release.",
    )
    # Never replace a conflicting local tag. The original launcher repeats this
    # same non-forced fetch and exact commit check before starting its new run.
    _git(support, app, log, "fetch", "origin", reference + ":" + reference)
    require(
        _git(support, app, log, "rev-parse", reference).decode().strip() == published[reference]
        and _git(support, app, log, "rev-parse", reference + "^{commit}").decode().strip()
        == revision,
        "The local replacement tag differs from the published release.",
    )
    require(
        _git(support, app, log, "show", revision + ":VERSION").decode().strip() == tag[1:],
        "Replacement VERSION and release tag differ.",
    )
    try:
        _git(support, app, log, "merge-base", "--is-ancestor", failed_revision, revision)
    except support.ActivationError:
        raise RecoveryError("The failed-to-replacement ancestry could not be verified.") from None
    for relative in UNCHANGED_FILES:
        require(
            _git(support, app, log, "show", old_revision + ":" + relative)
            == _git(support, app, log, "show", revision + ":" + relative),
            "The replacement deployment contract differs from the installed and failed releases.",
        )
    return published[reference]


def _checkout(
    support: SimpleNamespace, app: Path, revision: str, log: Path, lock_descriptor: int
) -> None:
    # Keep the same flock alive even if this Python parent is interrupted first.
    result = subprocess.run(
        ["git", "-C", str(app), "checkout", "--detach", revision],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        pass_fds=(lock_descriptor,),
        check=False,
    )
    support._append_log(
        log, b"\ncheckout stdout:\n" + result.stdout + b"\nstderr:\n" + result.stderr
    )
    require(
        result.returncode == 0,
        "Source return failed; retain the pending operation and log.",
    )


def close_failed_prepare(
    base: Path,
    tag: str,
    target_revision: str,
    *,
    replacement: tuple[str, str] | None = None,
) -> Path:
    """Return the verified launcher after restoring sources and closing only pending."""
    require(
        re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", tag) is not None,
        "Invalid release tag.",
    )
    require(
        re.fullmatch(r"[0-9a-f]{40}", target_revision) is not None,
        "Invalid target revision.",
    )
    if replacement is not None:
        replacement_tag, replacement_revision = replacement
        require(
            re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", replacement_tag) is not None
            and replacement_tag != tag,
            "Invalid or unchanged replacement release tag.",
        )
        require(
            re.fullmatch(r"[0-9a-f]{40}", replacement_revision) is not None
            and replacement_revision != target_revision,
            "Invalid or unchanged replacement revision.",
        )
    require(
        base.is_absolute() and base.resolve() == base,
        "Base path must be absolute and direct.",
    )
    app = base / "trading-workspace-app"
    require(
        app.is_dir() and app.resolve() == app and app not in Path(__file__).resolve().parents,
        "Run the support file outside the direct application checkout.",
    )
    support = _support(app)
    try:
        return _close_bound_operation(support, base, tag, target_revision, replacement=replacement)
    except support.ActivationError as error:
        raise RecoveryError(str(error)) from None


def _close_bound_operation(
    support: SimpleNamespace,
    base: Path,
    tag: str,
    target_revision: str,
    *,
    replacement: tuple[str, str] | None = None,
) -> Path:
    app, control = support._layout(base)
    recovery_sha256 = digest(Path(__file__).resolve().read_bytes())
    with _lock(control) as lock_descriptor:
        support._private_directory(control / "runs")
        require(
            not os.path.lexists(control / "current-state.new"),
            "An unfinished state-pointer publication requires separate review.",
        )
        pending_bytes = support._read_private(control / "pending")
        operation = Path(support._line(control / "pending"))
        require(operation.parent == control / "runs", "Unexpected pending operation target.")
        support._private_directory(operation)
        failed = operation / "deployment"
        support._private_directory(failed)
        _phase_is_unused(failed)
        archive = operation / "aborted-before-apply"
        require(
            not os.path.lexists(archive) and not os.path.lexists(operation / "completed"),
            "The pending operation was already closed.",
        )
        old = support._current(control)
        require(
            all(support._read_private(old / name) == b"" for name in ("prepared", "deployed")),
            "Current deployment completion markers differ.",
        )
        old_pointer = support._read_private(control / "current-state")
        old_activation = support._previous_activation(old)
        old_seal = support._read_private(old / "inputs.sha256")
        old_revision = support._line(old / "revision")
        require(
            re.fullmatch(r"[0-9a-f]{40}", old_revision) is not None
            and old_revision != target_revision
            and support._line(old / "release-root") == str(app)
            and support._line(operation / "previous-state") == str(old)
            and support._line(operation / "previous-root") == str(app)
            and support._line(operation / "previous-revision") == old_revision
            and support._line(operation / "target-revision") == target_revision
            and support._line(failed / "release-root") == str(app)
            and support._line(failed / "revision") == target_revision,
            "The failed operation does not bind the current deployment and requested target.",
        )
        configuration = operation / "configuration"
        support._private_directory(configuration)
        support._private_directory(configuration / "docker")
        environment = support._read_private(old / "environment.env")
        require(
            support._read_private(configuration / "docker/.env") == environment
            and support._read_private(failed / "environment.env") == environment,
            "Failed preparation configuration differs from the sealed deployment.",
        )
        descriptor, log_name = tempfile.mkstemp(prefix="retry-", suffix=".log", dir=operation)
        os.close(descriptor)
        log = Path(log_name)
        head = _release_checks(support, app, log, old_revision, tag, target_revision)
        replacement_tag_object = None
        if replacement is not None:
            replacement_tag_object = _replacement_checks(
                support, app, log, old_revision, target_revision, *replacement
            )
        require(
            support._read_private(configuration / "docker/compose.yml")
            == _git(support, app, log, "show", old_revision + ":docker/compose.yml"),
            "The failed operation's source Compose contract differs.",
        )
        launcher, launcher_hash = support._launcher(app)
        require(
            launcher.resolve() == launcher
            and launcher_hash == PINS["scripts/trading-workspace.sh"],
            "The installed launcher is not the qualified unchanged launcher.",
        )
        legacy = support._legacy(app)
        before = _old_runtime(support, app, old, log, legacy)
        baseline = support.parse_json(support._read_private(failed / "baseline.json"))
        support._legacy_call(legacy, "verify_identity", baseline, before)
        if head != old_revision:
            _checkout(support, app, old_revision, log, lock_descriptor)
        after, _, checked_revision, _ = support._validate_old(
            app, old, log, legacy, activation_state=old_activation
        )
        support._legacy_call(legacy, "verify_identity", before, after)
        support._legacy_call(legacy, "verify_identity", baseline, after)
        require(checked_revision == old_revision, "The restored source revision differs.")
        require(
            support._read_private(control / "pending") == pending_bytes
            and support._read_private(control / "current-state") == old_pointer
            and support._read_private(old / "inputs.sha256") == old_seal
            and support._launcher(app) == (launcher, launcher_hash)
            and not os.path.lexists(control / "current-state.new")
            and not os.path.lexists(archive)
            and digest(Path(__file__).resolve().read_bytes()) == recovery_sha256,
            "Operation ownership or sealed state changed during recovery.",
        )
        _phase_is_unused(failed)
        record: dict[str, Any] = {
            "schema": 1,
            "operation": "close-failed-prepare",
            "old_revision": old_revision,
            "target_revision": target_revision,
            "target_tag": tag,
            "source_before": head,
            "pending_sha256": digest(pending_bytes),
            "old_pointer_sha256": digest(old_pointer),
            "old_seal_sha256": digest(old_seal),
            "support_sha256": SUPPORT_SHA256,
            "recovery_sha256": recovery_sha256,
        }
        if replacement is not None:
            record.update(
                replacement_tag=replacement[0],
                replacement_revision=replacement[1],
                replacement_tag_object=replacement_tag_object,
            )
        support._write_private(
            log.with_suffix(".json"),
            (json.dumps(record, sort_keys=True) + "\n").encode(),
            exclusive=True,
        )
        support._sync_directory(operation)
        os.replace(control / "pending", archive)
        support._sync_directory(operation)
        support._sync_directory(control)
    return launcher


def retry(base: Path, tag: str, target_revision: str) -> NoReturn:
    launcher = close_failed_prepare(base, tag, target_revision)
    os.environ["TRADING_WORKSPACE_BASE"] = str(base)
    print(
        "Failed preparation closed; the existing deployment is unchanged. "
        "Retrying through the verified installed launcher.",
        flush=True,
    )
    os.execv(str(launcher), [str(launcher), "update", tag, target_revision])


def replace_release(
    base: Path, failed_tag: str, failed_revision: str, new_tag: str, new_revision: str
) -> NoReturn:
    launcher = close_failed_prepare(
        base, failed_tag, failed_revision, replacement=(new_tag, new_revision)
    )
    os.environ["TRADING_WORKSPACE_BASE"] = str(base)
    print(
        "Failed preparation closed; the existing deployment is unchanged. "
        "Installing the verified replacement through the unchanged launcher.",
        flush=True,
    )
    os.execv(str(launcher), [str(launcher), "update", new_tag, new_revision])


class _SafeParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise RecoveryError("Invalid arguments; use --help. No argument values printed.")


def main(argv: list[str] | None = None) -> int:
    parser = _SafeParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    for action in ("retry", "replace"):
        command = commands.add_parser(action)
        command.add_argument("tag", metavar="FAILED_TAG" if action == "replace" else "tag")
        command.add_argument(
            "revision", metavar="FAILED_SHA" if action == "replace" else "revision"
        )
        if action == "replace":
            command.add_argument("new_tag", metavar="NEW_TAG")
            command.add_argument("new_revision", metavar="NEW_SHA")
        command.add_argument(
            "--base",
            type=Path,
            default=Path(os.environ.get("TRADING_WORKSPACE_BASE", str(Path.home() / "Boerse"))),
        )
    try:
        args = parser.parse_args(argv)
        require(os.getuid() != 0, "Run as the existing deployment owner, not root/sudo.")
        if args.action == "replace":
            replace_release(
                args.base.expanduser(), args.tag, args.revision, args.new_tag, args.new_revision
            )
        else:
            retry(args.base.expanduser(), args.tag, args.revision)
    except RecoveryError as error:
        print("Update retry stopped: " + str(error), file=sys.stderr)
    except KeyboardInterrupt:
        print(
            "Update retry interrupted. Retain all private records. "
            "If pending was archived, use the unchanged launcher.",
            file=sys.stderr,
        )
        return 130
    except Exception:
        print(
            "Update retry stopped. Inspect private retry diagnostics; no private values printed. "
            "Keep all state and phase markers. "
            "If pending was archived, use the unchanged launcher.",
            file=sys.stderr,
        )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
