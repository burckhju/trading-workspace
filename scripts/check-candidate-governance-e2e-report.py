#!/usr/bin/env python3
"""Pin one native governance journey and bind its complete execution artifact set."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

EXPECTED = {
    (
        "candidate-governance-journey-postgres.spec.ts",
        "candidate governance: exact Lesson source, explicit A-B-A and immutable evaluations",
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
    require(len(found) == len(EXPECTED), "Expected exactly one governance test identity")
    require(
        {(item[0]["file"], item[0]["title"]) for item in found} == EXPECTED,
        "The discovered file/title set differs from the exact governance journey",
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
        == (1, 0, 0, 0),
        "Expected one pass and zero unexpected, skipped or flaky results",
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


def artifact_files(directory):
    """Include every evidence file, including hidden and nested trace resources."""
    require(directory.is_dir() and not directory.is_symlink(), "Invalid artifact directory")
    files = {}
    for path in sorted(directory.rglob("*")):
        require(not path.is_symlink(), "Artifact symlinks are forbidden")
        if path.is_dir() or path == directory / "manifest.json":
            continue
        require(path.is_file(), "Non-file artifact entry")
        content = path.read_bytes()
        files[path.relative_to(directory).as_posix()] = {
            "bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
        }
    require(bool(files), "Empty artifact set")
    return files


def create_artifact_manifest(directory):
    manifest = directory / "manifest.json"
    require(not manifest.exists() and not manifest.is_symlink(), "Manifest already exists")
    manifest.write_text(
        json.dumps({"files": artifact_files(directory)}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def verify_artifact_manifest(directory):
    manifest_path = directory / "manifest.json"
    require(not manifest_path.is_symlink(), "Manifest symlink is forbidden")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    require(set(manifest) == {"files"}, "Unexpected artifact manifest fields")
    actual = artifact_files(directory)
    require(actual == manifest["files"], "Artifact file set, bytes or SHA-256 differ")
    return len(actual)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="mode", required=True)
    for mode in ("discover", "verify"):
        command = commands.add_parser(mode)
        command.add_argument("report", type=Path)
        command.add_argument("manifest", type=Path)
    for mode in ("manifest-create", "manifest-verify"):
        command = commands.add_parser(mode)
        command.add_argument("directory", type=Path)
    args = parser.parse_args()
    if args.mode == "manifest-create":
        create_artifact_manifest(args.directory)
        print("Bound the complete artifact file set, including cleanup, bytes and SHA-256")
        return
    if args.mode == "manifest-verify":
        count = verify_artifact_manifest(args.directory)
        print(f"Verified the entire artifact manifest: {count} files")
        return
    report = json.loads(args.report.read_text(encoding="utf-8"))
    if args.mode == "discover":
        args.manifest.write_text(
            json.dumps(record_discovery(report), indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print("Pinned the exact governance test ID before any stack writes")
    else:
        check_results(report, json.loads(args.manifest.read_text(encoding="utf-8")))
        print(
            "The pinned governance journey passed exactly once; no skips, flaky results or retries"
        )


if __name__ == "__main__":
    main()
