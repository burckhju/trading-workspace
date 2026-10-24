#!/usr/bin/env python3
"""Closed-world proof for one identified native performance owner journey."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

CASES = {
    "realized-gross": (
        "realized-gross-report-postgres.spec.ts",
        "bafadc4ef6213b62375d-e7b379ddd7f6cba6769e",
        "real PostgreSQL: purchase currency once, inherited sales, sources and correction",
    ),
    "closed-trades": (
        "closed-trades-report-postgres.spec.ts",
        "2dd5a78c1f224eb1b623-d0bfb041223e2b8fca72",
        "real PostgreSQL: full-close cohort, lifetime result, gaps and current correction",
    ),
}


def verify_report(report: dict, qualification: str) -> dict:
    """Reject skips, repeats, retries, swapped tests and global setup errors."""
    if qualification not in CASES:
        raise ValueError("Unknown performance qualification")
    filename, identifier, title = CASES[qualification]
    config = report.get("config", {})
    projects = config.get("projects", [])
    if config.get("workers") != 1 or len(projects) != 1:
        raise ValueError("Exactly one worker and one Chromium project are required")
    project = projects[0]
    if (
        project.get("name") != "chromium"
        or project.get("retries") != 0
        or project.get("repeatEach") != 1
        or config.get("shard") is not None
    ):
        raise ValueError("No retry, repetition or shard may weaken the identified journey")
    stats = report.get("stats", {})
    if tuple(stats.get(key) for key in ("expected", "unexpected", "skipped", "flaky")) != (
        1,
        0,
        0,
        0,
    ) or report.get("errors"):
        raise ValueError("The complete report must have exactly one pass and no errors or skips")
    specs = []

    def collect(suites: list[dict]) -> None:
        for suite in suites:
            specs.extend(suite.get("specs", []))
            collect(suite.get("suites", []))

    collect(report.get("suites", []))
    if len(specs) != 1:
        raise ValueError("Exactly the expected spec must execute")
    spec = specs[0]
    if (spec.get("file"), spec.get("id"), spec.get("title")) != (
        filename,
        identifier,
        title,
    ) or not spec.get("ok"):
        raise ValueError("The executed test identity differs from the pinned native journey")
    tests = spec.get("tests", [])
    if len(tests) != 1:
        raise ValueError("Exactly one native test result is required")
    test = tests[0]
    if (
        test.get("projectName") != "chromium"
        or test.get("status") != "expected"
        or test.get("expectedStatus") != "passed"
        or any(
            item.get("type") in {"skip", "fixme", "fail"} for item in test.get("annotations", [])
        )
    ):
        raise ValueError("A skipped, expected-failing or substituted test is not a pass")
    results = test.get("results", [])
    if (
        len(results) != 1
        or results[0].get("status") != "passed"
        or results[0].get("retry") != 0
        or results[0].get("errors")
        or results[0].get("error")
    ):
        raise ValueError("Exactly one successful attempt with retry zero is required")
    return {
        "qualification": qualification,
        "file": filename,
        "test_id": identifier,
        "title": title,
        "project": "chromium",
        "passed": 1,
        "skipped": 0,
        "flaky": 0,
        "retry": 0,
        "attempts": 1,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("qualification", choices=tuple(CASES))
    args = parser.parse_args()
    print(
        json.dumps(verify_report(json.loads(args.report.read_text()), args.qualification), indent=2)
    )
