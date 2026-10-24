#!/usr/bin/env python3
"""Pin the two existing learning journeys before execution; reject incomplete reports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

EXPECTED = {
    (
        "post-trade-journal-postgres.spec.ts",
        "real PostgreSQL: captured full exit, review, journal, lesson and stale correction",
    ),
    (
        "post-trade-evidence-history-postgres.spec.ts",
        "real PostgreSQL: FT011 history survives correction and opens the exact Lesson version",
    ),
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def entries(report):
    found = []

    def collect(suites):
        for suite in suites:
            for spec in suite.get("specs", []):
                for test in spec["tests"]:
                    identity = {
                        "file": spec["file"],
                        "title": spec["title"],
                        "id": spec["id"],
                        "project": test["projectName"],
                    }
                    found.append((identity, spec, test))
            collect(suite.get("suites", []))

    collect(report["suites"])
    require(not report.get("errors"), "Global Playwright errors are not allowed")
    require(len(found) == len(EXPECTED), "Expected exactly two learning test identities")
    require(
        {(item[0]["file"], item[0]["title"]) for item in found} == EXPECTED,
        "The discovered file/title set differs from the two approved existing journeys",
    )
    ids = [item[0]["id"] for item in found]
    require(all(isinstance(value, str) and value for value in ids), "Missing test ID")
    require(len(set(ids)) == len(EXPECTED), "Duplicate test IDs")
    for identity, _, test in found:
        require(identity["project"] == "chromium", "Unexpected browser project")
        require(test.get("expectedStatus") == "passed", "Skipped/expected-failure test")
        require(test.get("repeatEachIndex", 0) == 0, "Unexpected test repetition")
    return found


def identities(report):
    return sorted((item[0] for item in entries(report)), key=lambda value: value["file"])


def record_discovery(report):
    for _, _, test in entries(report):
        require(test.get("results", []) == [], "Discovery must precede execution")
    return {"expected_tests": identities(report), "attempts_per_test": 1}


def check_results(report, manifest):
    require(manifest.get("attempts_per_test") == 1, "Exactly one attempt is required")
    require(
        identities(report) == manifest.get("expected_tests"), "Test IDs changed after discovery"
    )
    stats = report["stats"]
    require(
        tuple(stats.get(key) for key in ("expected", "unexpected", "skipped", "flaky"))
        == (2, 0, 0, 0),
        "Expected two passes and zero unexpected, skipped or flaky results",
    )
    for _, spec, test in entries(report):
        require(spec.get("ok") is True, "Unsuccessful spec")
        require(test.get("status") == "expected", "Unsuccessful test")
        results = test.get("results", [])
        require(len(results) == 1, "Each journey must execute exactly once")
        result = results[0]
        require(result.get("status") == "passed", "Journey did not pass")
        require(result.get("retry") == 0, "Browser retry is forbidden")
        require(not result.get("error") and not result.get("errors"), "Attempt contains errors")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("discover", "verify"))
    parser.add_argument("report", type=Path)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    if args.mode == "discover":
        args.manifest.write_text(
            json.dumps(record_discovery(report), indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print("Pinned both existing learning test IDs before any stack writes")
    else:
        check_results(report, json.loads(args.manifest.read_text(encoding="utf-8")))
        print(
            "Both pinned learning journeys passed exactly once; no skips, flaky results or retries"
        )


if __name__ == "__main__":
    main()
