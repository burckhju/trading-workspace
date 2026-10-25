"""Reject incomplete browser evidence and unverified governance qualification targets."""

from __future__ import annotations

import copy
import importlib.util
import os
import subprocess
from pathlib import Path
from uuid import UUID

import pytest

ROOT = Path(__file__).resolve().parents[3]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


REPORT = load("candidate_governance_report", "scripts/check-candidate-governance-e2e-report.py")
DATABASE = load(
    "candidate_governance_database", "tests/e2e/support/candidate_governance_database_guard.py"
)
RUN = "00000000-0000-4000-8000-000000000123"
DB_NAME = "trading_workspace_test_cg_" + UUID(RUN).hex
HOST_URL = f"postgresql+asyncpg://tw_candidate_e2e:synthetic@127.0.0.1:25432/{DB_NAME}"


def report(*, discovery=False):
    filename, title = next(iter(REPORT.EXPECTED))
    return {
        "suites": [
            {
                "suites": [
                    {
                        "specs": [
                            {
                                "file": filename,
                                "title": title,
                                "id": "B-CG-001-stable-playwright-id",
                                "ok": True,
                                "tests": [
                                    {
                                        "projectName": "chromium",
                                        "expectedStatus": "passed",
                                        "status": "expected",
                                        "results": (
                                            []
                                            if discovery
                                            else [{"status": "passed", "retry": 0, "errors": []}]
                                        ),
                                    }
                                ],
                            }
                        ]
                    }
                ]
            }
        ],
        "errors": [],
        "stats": {"expected": 1, "unexpected": 0, "skipped": 0, "flaky": 0},
    }


def test_exact_discovered_governance_journey_passes_once():
    discovery = REPORT.record_discovery(report(discovery=True))
    REPORT.check_results(report(), discovery)


@pytest.mark.parametrize(
    "defect",
    [
        "missing",
        "extra",
        "wrong_file",
        "wrong_title",
        "wrong_project",
        "changed_id",
        "empty_id",
        "global_error",
        "skipped",
        "flaky",
        "expected_failure",
        "failed",
        "retry",
        "second_attempt",
        "no_attempt",
        "attempt_error",
        "stats_lie",
        "repetition",
    ],
)
def test_report_rejects_incomplete_or_retried_journey(defect):
    value = report()
    specs = value["suites"][0]["suites"][0]["specs"]
    spec = specs[0]
    test = spec["tests"][0]
    if defect == "missing":
        specs.clear()
    elif defect == "extra":
        specs.append(copy.deepcopy(spec))
    elif defect == "wrong_file":
        spec["file"] = "post-trade-journal-postgres.spec.ts"
    elif defect == "wrong_title":
        spec["title"] = "An unrelated success"
    elif defect == "wrong_project":
        test["projectName"] = "webkit"
    elif defect == "changed_id":
        spec["id"] = "not-the-discovered-id"
    elif defect == "empty_id":
        spec["id"] = ""
    elif defect == "global_error":
        value["errors"] = [{"message": "worker teardown failed"}]
    elif defect in ("skipped", "flaky"):
        test["status"] = defect
    elif defect == "expected_failure":
        test["expectedStatus"] = "failed"
    elif defect == "failed":
        test["results"][0]["status"] = "failed"
    elif defect == "retry":
        test["results"][0]["retry"] = 1
    elif defect == "second_attempt":
        test["results"].append(copy.deepcopy(test["results"][0]))
    elif defect == "no_attempt":
        test["results"].clear()
    elif defect == "attempt_error":
        test["results"][0]["errors"] = [{"message": "incomplete request"}]
    elif defect == "stats_lie":
        value["stats"]["skipped"] = 1
    elif defect == "repetition":
        test["repeatEachIndex"] = 1
    with pytest.raises(ValueError):
        REPORT.check_results(value, REPORT.record_discovery(report(discovery=True)))


def test_discovery_must_precede_execution():
    with pytest.raises(ValueError, match="precede execution"):
        REPORT.record_discovery(report())


@pytest.fixture
def evidence_directory(tmp_path):
    (tmp_path / "playwright" / ".resources").mkdir(parents=True)
    (tmp_path / "cleanup.json").write_text('{"removed": true}')
    (tmp_path / "results.json").write_text("synthetic report")
    (tmp_path / "playwright" / ".resources" / "desktop.png").write_bytes(b"synthetic image")
    (tmp_path / "playwright" / "manifest.json").write_text("nested trace resource")
    REPORT.create_artifact_manifest(tmp_path)
    return tmp_path


def test_manifest_covers_every_file_including_hidden_nested_artifacts(evidence_directory):
    assert REPORT.verify_artifact_manifest(evidence_directory) == 4


@pytest.mark.parametrize("defect", ["changed", "removed", "added", "hidden", "symlink"])
def test_manifest_rejects_changed_or_incomplete_file_sets(evidence_directory, defect):
    path = evidence_directory / "cleanup.json"
    if defect == "changed":
        path.write_text('{"removed": false}')
    elif defect == "removed":
        path.unlink()
    elif defect == "added":
        (evidence_directory / "unbound.log").write_text("not in manifest")
    elif defect == "hidden":
        (evidence_directory / "playwright" / ".resources" / "desktop.png").unlink()
    elif defect == "symlink":
        path.unlink()
        path.symlink_to("results.json")
    with pytest.raises(ValueError):
        REPORT.verify_artifact_manifest(evidence_directory)


def test_manifest_cannot_be_silently_replaced(evidence_directory):
    with pytest.raises(ValueError, match="already exists"):
        REPORT.create_artifact_manifest(evidence_directory)


@pytest.fixture
def target_environment(monkeypatch):
    values = {
        "CI": "true",
        "GITHUB_ACTIONS": "true",
        "CANDIDATE_GOVERNANCE_E2E_WRITES_ALLOWED": "1",
        "CANDIDATE_GOVERNANCE_E2E_WORKSPACE_ID": DATABASE.WORKSPACE,
        "CANDIDATE_GOVERNANCE_E2E_RUN_ID": RUN,
        "TRADING_WORKSPACE_ENVIRONMENT": "test",
        "TRADING_WORKSPACE_TEST_DATABASE_URL": HOST_URL,
        "TRADING_WORKSPACE_DATABASE_URL": HOST_URL,
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)


def test_database_target_binds_exact_synthetic_run(target_environment):
    run_id, target = DATABASE.configured_target()
    assert run_id == RUN and target.database == DB_NAME


@pytest.mark.parametrize(
    "key,value",
    [
        ("CI", "false"),
        ("GITHUB_ACTIONS", "false"),
        ("CANDIDATE_GOVERNANCE_E2E_WRITES_ALLOWED", "0"),
        ("TRADING_WORKSPACE_ENVIRONMENT", "production"),
        ("CANDIDATE_GOVERNANCE_E2E_WORKSPACE_ID", "00000000-0000-4000-8000-000000000999"),
        ("CANDIDATE_GOVERNANCE_E2E_RUN_ID", "00000000-0000-4000-8000-000000000999"),
        ("TRADING_WORKSPACE_TEST_DATABASE_URL", HOST_URL.replace("127.0.0.1", "remote")),
        ("TRADING_WORKSPACE_TEST_DATABASE_URL", HOST_URL.replace("25432", "5432")),
        ("TRADING_WORKSPACE_TEST_DATABASE_URL", HOST_URL.replace("tw_candidate_e2e", "real_user")),
        ("TRADING_WORKSPACE_TEST_DATABASE_URL", HOST_URL.replace(DB_NAME, "trading_workspace")),
        ("TRADING_WORKSPACE_DATABASE_URL", HOST_URL.replace(DB_NAME, "foreign")),
    ],
)
def test_database_guard_refuses_foreign_target_before_connection(
    target_environment, monkeypatch, key, value
):
    monkeypatch.setenv(key, value)
    with pytest.raises(RuntimeError):
        DATABASE.configured_target()


def test_runner_refuses_non_ci_context_before_any_command(tmp_path):
    result = subprocess.run(
        ["bash", str(ROOT / "scripts/run-candidate-governance-e2e.sh")],
        env={"PATH": os.environ["PATH"], "HOME": str(tmp_path)},
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 1
    assert "requires its disposable GitHub Actions checkout" in result.stderr


def issuer_audit():
    issuer = {
        "id": "00000000-0000-4000-8000-000000000456",
        "legal_name": f"Candidate Governance CI {RUN} 00000000-0000-4000-8000-000000000789",
        "display_name": "Synthetic candidate governance CI",
        "country_code": None,
        "lei": None,
        "is_active": True,
        "version": 1,
    }
    return {
        "id": UUID("00000000-0000-4000-8000-000000000987"),
        "workspace_id": None,
        "aggregate_type": "ISSUER",
        "aggregate_id": UUID(issuer["id"]),
        "actor_type": "SYSTEM_USER",
        "actor_id": f"candidate-governance:{RUN}",
        "actor_display_name": "Synthetic candidate governance CI",
        "data_origin": "MANUAL",
        "change_type": "CREATED",
        "version_before": None,
        "version_after": 1,
        "issuer": issuer,
        "audit_timestamp_matches": True,
        "warrant_ids": [UUID("00000000-0000-4000-8000-000000000654")],
        "field_changes": {
            key: {"old": None, "new": issuer[key]}
            for key in ("legal_name", "display_name", "country_code", "lei", "is_active")
        },
    }


def test_global_audit_exception_is_exactly_one_unchanged_run_owned_issuer():
    row = issuer_audit()
    assert DATABASE.verify_global_issuer_audits([], RUN) == []
    assert DATABASE.verify_global_issuer_audits([row], RUN)[0]["issuer_id"] == str(
        row["aggregate_id"]
    )
    with pytest.raises(RuntimeError, match="number"):
        DATABASE.verify_global_issuer_audits([row, copy.deepcopy(row)], RUN)


@pytest.mark.parametrize(
    "field,value",
    [
        ("workspace_id", UUID(RUN)),
        ("aggregate_type", "CURRENCY"),
        ("actor_type", "PROVIDER"),
        ("actor_id", "journal-evidence:" + RUN),
        ("actor_display_name", "Real user"),
        ("data_origin", "EXTERNAL"),
        ("change_type", "UPDATED"),
        ("version_before", 1),
        ("version_after", 2),
        ("aggregate_id", UUID(RUN)),
        ("audit_timestamp_matches", False),
        ("warrant_ids", []),
        ("warrant_ids", [UUID(RUN), UUID(RUN)]),
        ("field_changes", {}),
    ],
)
def test_global_audit_refuses_foreign_or_changed_owner(field, value):
    row = issuer_audit()
    row[field] = value
    with pytest.raises(RuntimeError):
        DATABASE.verify_global_issuer_audits([row], RUN)


@pytest.mark.parametrize(
    "field,value",
    [
        ("legal_name", "Unrelated issuer"),
        ("legal_name", f"Candidate Governance CI {RUN} invalid-suffix"),
        ("display_name", "Real issuer"),
        ("country_code", "DE"),
        ("lei", "FOREIGN_REFERENCE"),
        ("is_active", False),
        ("version", 2),
    ],
)
def test_global_audit_refuses_foreign_or_changed_entity(field, value):
    row = issuer_audit()
    row["issuer"][field] = value
    with pytest.raises(RuntimeError):
        DATABASE.verify_global_issuer_audits([row], RUN)
