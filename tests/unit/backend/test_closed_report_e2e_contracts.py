"""An unrelated green spec, skip or retry cannot qualify a native owner journey."""

import copy
import runpy
from pathlib import Path

import pytest

MODULE = runpy.run_path(
    str(Path(__file__).resolve().parents[3] / "scripts/check-performance-e2e-report.py")
)
CASES = MODULE["CASES"]
verify_report = MODULE["verify_report"]


def _passing_report(qualification: str) -> dict:
    filename, identifier, title = CASES[qualification]
    return {
        "config": {
            "workers": 1,
            "shard": None,
            "projects": [{"name": "chromium", "retries": 0, "repeatEach": 1}],
        },
        "stats": {"expected": 1, "unexpected": 0, "skipped": 0, "flaky": 0},
        "errors": [],
        "suites": [
            {
                "suites": [
                    {
                        "specs": [
                            {
                                "file": filename,
                                "id": identifier,
                                "title": title,
                                "ok": True,
                                "tests": [
                                    {
                                        "projectName": "chromium",
                                        "status": "expected",
                                        "expectedStatus": "passed",
                                        "annotations": [],
                                        "results": [{"status": "passed", "retry": 0, "errors": []}],
                                    }
                                ],
                            }
                        ]
                    }
                ]
            }
        ],
    }


@pytest.mark.parametrize("qualification", list(CASES))
def test_exact_identified_native_pass_is_accepted(qualification: str) -> None:
    proof = verify_report(_passing_report(qualification), qualification)
    assert proof["test_id"] == CASES[qualification][1]
    assert proof["attempts"] == 1 and proof["retry"] == 0


@pytest.mark.parametrize(
    "change",
    [
        "skip",
        "flaky",
        "unexpected",
        "global_error",
        "wrong_file",
        "wrong_id",
        "wrong_title",
        "extra_spec",
        "extra_test",
        "extra_attempt",
        "retry",
        "failed",
        "expected_failure",
        "annotation_skip",
        "annotation_fixme",
        "no_result",
        "result_error",
        "workers",
        "project_retries",
        "repeat",
        "shard",
        "wrong_project",
        "missing_count",
    ],
)
def test_incomplete_or_swapped_evidence_is_rejected(change: str) -> None:
    report = _passing_report("closed-trades")
    specs = report["suites"][0]["suites"][0]["specs"]
    spec = specs[0]
    test = spec["tests"][0]
    if change in {"skip", "flaky", "unexpected"}:
        report["stats"]["skipped" if change == "skip" else change] = 1
    elif change == "global_error":
        report["errors"] = [{"message": "setup failed"}]
    elif change in {"wrong_file", "wrong_id", "wrong_title"}:
        spec[change.removeprefix("wrong_")] = "unrelated passing smoke test"
    elif change == "extra_spec":
        specs.append(copy.deepcopy(spec))
    elif change == "extra_test":
        spec["tests"].append(copy.deepcopy(test))
    elif change == "extra_attempt":
        test["results"].append(copy.deepcopy(test["results"][0]))
    elif change == "retry":
        test["results"][0]["retry"] = 1
    elif change == "failed":
        test["results"][0]["status"] = "failed"
    elif change == "expected_failure":
        test["expectedStatus"] = "failed"
    elif change.startswith("annotation_"):
        test["annotations"] = [{"type": change.removeprefix("annotation_")}]
    elif change == "no_result":
        test["results"] = []
    elif change == "result_error":
        test["results"][0]["error"] = {"message": "failed step"}
    elif change == "workers":
        report["config"]["workers"] = 2
    elif change == "project_retries":
        report["config"]["projects"][0]["retries"] = 2
    elif change == "repeat":
        report["config"]["projects"][0]["repeatEach"] = 2
    elif change == "shard":
        report["config"]["shard"] = {"current": 1, "total": 2}
    elif change == "wrong_project":
        test["projectName"] = "firefox"
    elif change == "missing_count":
        del report["stats"]["skipped"]
    with pytest.raises(ValueError):
        verify_report(report, "closed-trades")


def test_the_other_valid_journey_does_not_substitute_for_closed_trades() -> None:
    with pytest.raises(ValueError, match="identity"):
        verify_report(_passing_report("realized-gross"), "closed-trades")
    with pytest.raises(ValueError, match="Unknown"):
        verify_report(_passing_report("closed-trades"), "arbitrary-file")
