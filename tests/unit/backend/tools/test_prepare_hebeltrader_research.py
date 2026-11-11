from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.tools.prepare_hebeltrader_research import main

REPO = Path(__file__).resolve().parents[4]


def _documented_synthetic_source(tmp_path: Path) -> Path:
    document = (REPO / "docs/features/HEBELTRADER_RESEARCH_PREPARATION.md").read_text()
    example = document.split("```json\n", 1)[1].split("\n```", 1)[0]
    source = tmp_path / "synthetic.json"
    source.write_text(example, encoding="utf-8")
    return source


def _arguments(source: Path, output: Path) -> list[str]:
    return [
        "--input",
        str(source),
        "--out",
        str(output),
        "--cutoff",
        "2026-11-10",
        "--expected-count",
        "1",
    ]


def test_documented_example_runs_without_site_packages_settings_database_or_network(
    tmp_path: Path,
) -> None:
    source = _documented_synthetic_source(tmp_path)
    output = tmp_path / "prepared"
    # -I/-S excludes environment/site packages. The audit hook also rejects operational imports.
    program = """
import sys
import runpy
sys.path.insert(0, sys.argv.pop(1))
def reject_operational(event, args):
    if event.startswith('socket.'):
        raise AssertionError('Network is outside this adapter')
    if event == 'import':
        name = args[0]
        if any(part in name for part in ('settings', 'sqlalchemy', 'persistence', 'httpx')):
            raise AssertionError('Operational dependency: ' + name)
sys.addaudithook(reject_operational)
runpy.run_module('app.tools.prepare_hebeltrader_research', run_name='__main__')
"""
    completed = subprocess.run(
        [
            sys.executable,
            "-B",
            "-I",
            "-S",
            "-c",
            program,
            str(REPO / "backend"),
            *_arguments(source, output),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
        cwd=tmp_path,
        env={},
    )
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["status"] == "PREPARED"
    assert result["case_count"] == 1
    assert result["historical_result_status"] == "NOT_COMPUTED"
    assert (output / "manifest.json").exists()


def test_cli_returns_controlled_rejection_without_output_for_wrong_count(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = _documented_synthetic_source(tmp_path)
    output = tmp_path / "rejected"
    arguments = _arguments(source, output)
    arguments[-1] = "222"
    assert main(arguments) == 2
    result = json.loads(capsys.readouterr().err)
    assert result["code"] == "CASE_COUNT_MISMATCH"
    assert not output.exists()


def test_cli_handles_file_error_and_invalid_cutoff(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "missing.json"
    output = tmp_path / "rejected"
    arguments = _arguments(source, output)
    assert main(arguments) == 2
    assert json.loads(capsys.readouterr().err)["code"] == "FILE_IO_ERROR"
    arguments[5] = "20261110"
    assert main(arguments) == 2
    assert json.loads(capsys.readouterr().err)["code"] == "INVALID_DATE"
    assert not output.exists()


def test_cli_requires_all_four_explicit_arguments() -> None:
    with pytest.raises(SystemExit) as rejected:
        main([])
    assert rejected.value.code == 2
