from pathlib import Path

from app.core.config.settings import (
    StuttgartDelayedSettings,
    StuttgartDelayedSourceMode,
)
from app.features.position_monitoring.service.source_diagnostics import (
    StuttgartDelayedSourceStatus,
    get_stuttgart_delayed_source_health,
)


def _settings(
    directory: str | None, *, enabled: bool = True
) -> StuttgartDelayedSettings:
    return StuttgartDelayedSettings(
        enabled=enabled,
        source_mode=StuttgartDelayedSourceMode.LOCAL_DIRECTORY,
        local_directory=directory,
    )


def test_source_health_reports_disabled() -> None:
    result = get_stuttgart_delayed_source_health(_settings("/tmp/xstu", enabled=False))

    assert result.status == StuttgartDelayedSourceStatus.DISABLED
    assert result.enabled is False


def test_source_health_reports_missing_directory(tmp_path: Path) -> None:
    result = get_stuttgart_delayed_source_health(_settings(str(tmp_path / "missing")))

    assert result.status == StuttgartDelayedSourceStatus.SOURCE_MISSING
    assert result.file_count == 0


def test_source_health_reports_empty_directory(tmp_path: Path) -> None:
    result = get_stuttgart_delayed_source_health(_settings(str(tmp_path)))

    assert result.status == StuttgartDelayedSourceStatus.SOURCE_MISSING
    assert result.latest_file is None
    assert result.file_count == 0


def test_source_health_selects_newest_verified_payload(tmp_path: Path) -> None:
    (tmp_path / "XSTU-pretrade-20260907T1849.json.gz").write_bytes(b"old")
    (tmp_path / "XSTU-pretrade-20260908T1900.json.gz").write_bytes(b"new")
    (tmp_path / "ignored.txt").write_text("ignore")

    result = get_stuttgart_delayed_source_health(_settings(str(tmp_path)))

    assert result.status == StuttgartDelayedSourceStatus.READY
    assert result.latest_file == "XSTU-pretrade-20260908T1900.json.gz"
    assert result.file_count == 2
    assert result.latest_file_timestamp is not None
    assert result.latest_file_timestamp.isoformat() == "2026-09-08T19:00:00+00:00"
