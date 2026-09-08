from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from app.core.config.settings import (
    StuttgartDelayedSettings,
    StuttgartDelayedSourceMode,
)

_XSTU_FILE_NAME = re.compile(r"^XSTU-pretrade-(?P<stamp>\d{8}T\d{4})\.json\.gz$")


class StuttgartDelayedSourceStatus(StrEnum):
    DISABLED = "DISABLED"
    READY = "READY"
    MISCONFIGURED = "MISCONFIGURED"
    SOURCE_MISSING = "SOURCE_MISSING"


@dataclass(frozen=True, slots=True)
class StuttgartDelayedSourceHealth:
    status: StuttgartDelayedSourceStatus
    reason: str
    enabled: bool
    source_mode: StuttgartDelayedSourceMode
    schema_version: str | None
    local_directory: str | None
    latest_file: str | None
    latest_file_timestamp: datetime | None
    file_count: int | None


def _timestamp_from_filename(path: Path) -> datetime | None:
    match = _XSTU_FILE_NAME.fullmatch(path.name)
    if match is None:
        return None
    try:
        parsed = datetime.strptime(match.group("stamp"), "%Y%m%dT%H%M")
    except ValueError:
        return None
    return parsed.replace(tzinfo=UTC)


def get_stuttgart_delayed_source_health(
    settings: StuttgartDelayedSettings,
) -> StuttgartDelayedSourceHealth:
    if not settings.enabled:
        return StuttgartDelayedSourceHealth(
            status=StuttgartDelayedSourceStatus.DISABLED,
            reason="Börse Stuttgart delayed quote source is disabled",
            enabled=False,
            source_mode=settings.source_mode,
            schema_version=settings.schema_version,
            local_directory=settings.local_directory,
            latest_file=None,
            latest_file_timestamp=None,
            file_count=None,
        )

    if not settings.has_verified_schema or not settings.has_source_configuration:
        return StuttgartDelayedSourceHealth(
            status=StuttgartDelayedSourceStatus.MISCONFIGURED,
            reason=(
                "Enabled source requires the verified schema and a complete source "
                "configuration"
            ),
            enabled=True,
            source_mode=settings.source_mode,
            schema_version=settings.schema_version,
            local_directory=settings.local_directory,
            latest_file=None,
            latest_file_timestamp=None,
            file_count=None,
        )

    if settings.source_mode != StuttgartDelayedSourceMode.LOCAL_DIRECTORY:
        return StuttgartDelayedSourceHealth(
            status=StuttgartDelayedSourceStatus.READY,
            reason=f"Configured {settings.source_mode.value} transport is activation-ready",
            enabled=True,
            source_mode=settings.source_mode,
            schema_version=settings.schema_version,
            local_directory=settings.local_directory,
            latest_file=None,
            latest_file_timestamp=None,
            file_count=None,
        )

    assert settings.local_directory is not None
    directory = Path(settings.local_directory)
    if not directory.is_dir():
        return StuttgartDelayedSourceHealth(
            status=StuttgartDelayedSourceStatus.SOURCE_MISSING,
            reason="Configured local_directory is not accessible",
            enabled=True,
            source_mode=settings.source_mode,
            schema_version=settings.schema_version,
            local_directory=settings.local_directory,
            latest_file=None,
            latest_file_timestamp=None,
            file_count=0,
        )

    candidates = sorted(
        (
            path
            for path in directory.glob(settings.local_file_pattern)
            if path.is_file() and _XSTU_FILE_NAME.fullmatch(path.name)
        ),
        key=lambda path: path.name,
    )
    if not candidates:
        return StuttgartDelayedSourceHealth(
            status=StuttgartDelayedSourceStatus.SOURCE_MISSING,
            reason="No verified XSTU delayed payload file is available",
            enabled=True,
            source_mode=settings.source_mode,
            schema_version=settings.schema_version,
            local_directory=settings.local_directory,
            latest_file=None,
            latest_file_timestamp=None,
            file_count=0,
        )

    latest = candidates[-1]
    return StuttgartDelayedSourceHealth(
        status=StuttgartDelayedSourceStatus.READY,
        reason="Newest verified XSTU delayed payload is available",
        enabled=True,
        source_mode=settings.source_mode,
        schema_version=settings.schema_version,
        local_directory=settings.local_directory,
        latest_file=latest.name,
        latest_file_timestamp=_timestamp_from_filename(latest),
        file_count=len(candidates),
    )
