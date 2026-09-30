"""Read scheduler evidence only: no quote fetch, cycle trigger or state writes."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from time import monotonic
from typing import Any

import httpx

from app.tools.audit_issuer_monitoring import TARGETS


def positive(value: object) -> bool:
    try:
        number = Decimal(str(value))
        return number.is_finite() and number > 0
    except InvalidOperation:
        return False


def summarize(monitoring: dict[str, Any], refresh: dict[str, Any]) -> dict[str, Any]:
    checks = monitoring.get("last_rule_checks", [])
    issuer_checks = [row for row in checks if row.get("isin") in TARGETS]
    jobs = refresh.get("jobs", [])
    issuer_jobs = [
        row for row in jobs if row.get("lane") == "ISSUER_QUOTES" and row.get("isin") in TARGETS
    ]
    successful = sorted(
        {
            row["isin"]
            for row in issuer_jobs
            if row.get("status") == "AVAILABLE"
            and any(
                q.get("provider") == TARGETS[row["isin"]]
                and positive(q.get("bid"))
                and q.get("retrieved_at")
                and not q.get("retained")
                and not q.get("refresh_error")
                for q in row.get("quotes", [])
            )
        }
    )
    fields = (
        "isin",
        "job",
        "lane",
        "status",
        "reason",
        "duration_seconds",
        "checked_at",
        "next_run_at",
    )
    failures = [
        row for row in checks if row.get("status") in {"ERROR", "STALE", "MISSING", "BLOCKED"}
    ]
    compact_jobs = [{key: row.get(key) for key in fields} for row in issuer_jobs]
    slow_checks = sorted(
        checks, key=lambda row: float(row.get("price_request_seconds") or 0), reverse=True
    )[:10]
    complete = bool(monitoring.get("last_cycle_completed_at") and not monitoring.get("last_error"))
    return {
        "schema_version": "MONITORING_PERFORMANCE_AUDIT_V1",
        "checked_at": datetime.now(UTC).isoformat(),
        "read_only": True,
        "may_refresh_quotes": False,
        "monitoring": {
            key: monitoring.get(key)
            for key in (
                "enabled",
                "running",
                "cycle_running",
                "parallel_positions",
                "interval_seconds",
                "last_cycle_started_at",
                "last_cycle_completed_at",
                "last_cycle_duration_seconds",
                "next_run_at",
                "last_error",
                "last_result",
            )
        },
        "quote_refresh": {
            key: refresh.get(key)
            for key in (
                "enabled",
                "leader",
                "last_error",
                "scheduling_mode",
                "lanes",
                "pending_jobs",
                "overdue_jobs",
            )
        },
        "summary": {
            "completed_cycle_available": complete,
            "rule_status_counts": dict(Counter(row.get("status") for row in checks)),
            "issuer_rule_status_counts": dict(Counter(row.get("status") for row in issuer_checks)),
            "issuer_positions_in_last_cycle": len({row["position_id"] for row in issuer_checks}),
            "issuer_refresh_jobs": len(issuer_jobs),
            "issuer_refresh_checked": sum(row.get("checked_at") is not None for row in issuer_jobs),
            "issuer_refresh_success_count": len(successful),
        },
        "issuer_refresh_success_isins": successful,
        "issuer_refresh_jobs": compact_jobs,
        "rule_issues": failures,
        "slow_price_requests": [
            {
                key: row.get(key)
                for key in (
                    "isin",
                    "position_id",
                    "rule_key",
                    "provider",
                    "status",
                    "reason",
                    "price_request_seconds",
                    "evaluation_seconds",
                    "refresh_error",
                    "error_type",
                    "error_code",
                    "sqlstate",
                )
            }
            for row in slow_checks
        ],
        "slow_refresh_jobs": [
            {key: row.get(key) for key in fields}
            for row in sorted(jobs, key=lambda row: row.get("duration_seconds") or 0, reverse=True)[
                :10
            ]
        ],
    }


async def audit(wait_seconds: int) -> dict[str, Any]:
    deadline = monotonic() + wait_seconds
    async with httpx.AsyncClient(
        base_url="http://127.0.0.1:8000", timeout=10, trust_env=False, follow_redirects=False
    ) as client:
        while True:
            results = []
            for path in (
                "/api/v1/position-monitoring/runtime/status",
                "/api/v1/market-data/refresh/status",
            ):
                response = await client.get(path)
                response.raise_for_status()
                results.append(response.json())
            report = summarize(*results)
            summary = report["summary"]
            if (
                results[0].get("running")
                and results[1].get("enabled")
                and results[1].get("leader")
                and results[1].get("last_scan_at")
                and summary["completed_cycle_available"]
                and summary["issuer_refresh_checked"] == summary["issuer_refresh_jobs"]
            ):
                report["wait_completed"] = True
                return report
            if monotonic() >= deadline or not results[0].get("enabled"):
                report["wait_completed"] = False
                return report
            print(
                "Warte auf Hintergrundzyklus und Emittenten-Refresh ...",
                file=sys.stderr,
                flush=True,
            )
            await asyncio.sleep(min(10, max(0, deadline - monotonic())))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wait-seconds", type=int, default=0)
    args = parser.parse_args()
    if not 0 <= args.wait_seconds <= 600:
        parser.error("--wait-seconds must be between 0 and 600")
    try:
        result = asyncio.run(audit(args.wait_seconds))
    except (httpx.HTTPError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "read_only": True,
                    "status": "AUDIT_REQUEST_FAILED",
                    "error_type": type(exc).__name__,
                }
            )
        )
        raise SystemExit(1) from None
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
