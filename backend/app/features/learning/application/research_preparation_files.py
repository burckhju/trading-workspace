"""Private, exclusive local output for research source snapshots on POSIX hosts."""

from __future__ import annotations

import os
from pathlib import Path

from app.features.learning.domain.research_preparation import PreparationError


def _inside_git(path: Path) -> bool:
    for directory in (path, *path.parents):
        marker = directory / ".git"
        if marker.exists() or marker.is_symlink():
            # A regular .git file also marks linked worktrees and submodules.
            return True
        if (
            (directory / "HEAD").is_file()
            and (directory / "objects").is_dir()
            and (directory / "refs").is_dir()
        ):
            return True
    return False


def validate_private_output(output_dir: Path) -> Path:
    """Reject existing paths and repository ancestors, including parent aliases."""
    if os.name != "posix":
        raise PreparationError(
            "PRIVATE_FILESYSTEM_REQUIRED", "Private Ausgabe benötigt einen POSIX-Dateisystemhost."
        )
    if output_dir.exists() or output_dir.is_symlink():
        raise PreparationError("OUTPUT_EXISTS", "Ausgabepfad existiert bereits.")
    absolute = Path(os.path.abspath(output_dir))
    # Resolve only the parent: the final component must be exclusively created.
    parent = absolute.parent.resolve(strict=True)
    resolved = parent / absolute.name
    if _inside_git(absolute.parent) or _inside_git(parent):
        raise PreparationError(
            "OUTPUT_IN_GIT_REPOSITORY", "Private Forschungsdaten gehören außerhalb von Git."
        )
    return resolved


def write_private_outputs(output_dir: Path, files: tuple[tuple[str, bytes], ...]) -> None:
    """Create 0700/0600 outputs without following or overwriting existing entries."""
    resolved = validate_private_output(output_dir)
    try:
        resolved.mkdir(mode=0o700)
    except FileExistsError as exc:
        raise PreparationError(
            "OUTPUT_EXISTS", "Ausgabepfad wurde zwischenzeitlich angelegt."
        ) from exc
    directory_fd = os.open(resolved, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        # Restore owner access even under an unusually restrictive umask.
        os.fchmod(directory_fd, 0o700)
        for filename, content in files:
            descriptor = os.open(
                filename,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
                dir_fd=directory_fd,
            )
            try:
                with os.fdopen(descriptor, "wb") as output:
                    os.fchmod(output.fileno(), 0o600)
                    output.write(content)
                    output.flush()
                    os.fsync(output.fileno())
            except BaseException:
                # A failed completion manifest must not look like a finished bundle.
                os.unlink(filename, dir_fd=directory_fd)
                raise
    finally:
        os.close(directory_fd)
