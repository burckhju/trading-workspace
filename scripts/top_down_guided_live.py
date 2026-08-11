#!/usr/bin/env python3
"""Inspect one candidate's live top-down prerequisites and optionally evaluate it.

This script never configures mappings or imports data automatically. It reports
one explicit next action at a time so operator decisions remain auditable.
"""

from __future__ import annotations

import argparse
import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def request_json(url: str, *, method: str = "GET", body: bytes | None = None):
    req = Request(
        url, data=body, method=method, headers={"Content-Type": "application/json"}
    )
    try:
        with urlopen(
            req
        ) as response:  # noqa: S310 - operator-provided local service URL
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8")
        raise SystemExit(f"HTTP {exc.code}: {detail}") from exc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("candidate_id")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--evaluate",
        action="store_true",
        help="Run automatic evaluation only when readiness is complete",
    )
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    workflow = request_json(
        f"{base}/api/v1/candidates/{args.candidate_id}/live-workflow"
    )
    print(json.dumps(workflow, indent=2))
    if not workflow["ready"]:
        print(f"NEXT_ACTION={workflow.get('next_action') or 'NONE'}")
        return 2
    print("READY_FOR_AUTO_EVALUATION")
    if not args.evaluate:
        return 0

    evaluation = request_json(
        f"{base}/api/v1/candidates/{args.candidate_id}/evaluations/auto",
        method="POST",
        body=b"{}",
    )
    print(json.dumps(evaluation, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
