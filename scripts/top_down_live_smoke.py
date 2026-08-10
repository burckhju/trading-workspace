#!/usr/bin/env python3
"""Run a lightweight live top-down smoke check against a running Trading Workspace API.

The script never knows provider credentials. It first verifies that semantic market
references are ready server-side, then optionally triggers an automatic candidate
evaluation whose sources are resolved entirely by the backend.
"""

from __future__ import annotations

import argparse
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def request_json(url: str, *, method: str = "GET", body: dict[str, object] | None = None):
    payload = None if body is None else json.dumps(body).encode("utf-8")
    request = Request(url, data=payload, method=method)
    if payload is not None:
        request.add_header("Content-Type", "application/json")
    with urlopen(request, timeout=30) as response:  # noqa: S310 - explicit operator-supplied URL
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--candidate-id")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    try:
        readiness = request_json(f"{base}/api/v1/top-down-reference-data/readiness")
        not_ready = [item for item in readiness if not item["ready"]]
        print(json.dumps({"references": readiness}, indent=2))
        if not_ready:
            print("Top-down reference configuration is not ready; no candidate evaluation started.")
            return 2
        if not args.candidate_id:
            print("References are ready. Supply --candidate-id to execute the automatic E2E evaluation.")
            return 0
        evaluation = request_json(
            f"{base}/api/v1/candidates/{args.candidate_id}/evaluations/auto",
            method="POST",
            body={},
        )
        print(json.dumps({"candidate_evaluation": evaluation}, indent=2))
        return 0
    except (HTTPError, URLError, TimeoutError) as error:
        print(f"Smoke test failed: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
