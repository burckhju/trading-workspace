"""Read-only check of deployed source-selection code, configuration and open positions."""

import argparse
import asyncio
import hashlib
import importlib.util
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import text

from app.core.config import get_settings
from app.database import DatabaseManager
from app.features.market_data.domain.issuer_indications import ISSUER_INDICATIONS
from app.features.market_data.service.position_quote_source import AUTO_SELECTION_POLICY

QUERY = text("""
SELECT p.id AS position_id, t.id AS trade_id, w.isin,
       s.id AS selection_id, s.selection_status, s.selection_reason,
       s.provider, s.policy_version, s.evidence, s.selected_at
FROM positions p
JOIN trades t ON t.id = p.trade_id AND t.product_id = p.product_id
JOIN warrants w ON w.id = p.product_id AND w.workspace_id = t.workspace_id
LEFT JOIN position_quote_source_selections s
  ON s.position_id = p.id AND s.workspace_id = t.workspace_id AND s.superseded_at IS NULL
WHERE t.workspace_id = :workspace_id AND t.cancelled_at IS NULL
  AND p.open_quantity > 0 AND p.closed_at IS NULL
ORDER BY w.isin, p.id
""")


def check_hashes(expected: dict[str, str]) -> list[dict[str, object]]:
    result = []
    for name, digest in expected.items():
        spec = importlib.util.find_spec(name.removesuffix(".py").replace("/", "."))
        path = Path(spec.origin) if spec and spec.origin else None
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if path and path.is_file() else None
        result.append({"module": name, "matches_package": actual == digest})
    return result


async def audit(
    expected_hashes: dict[str, str], expected_enabled: bool
) -> tuple[dict[str, Any], int]:
    settings = get_settings()
    refresh = settings.market_data.refresh
    database = DatabaseManager(settings)
    report: dict[str, Any] = {
        "schema_version": "POSITION_SOURCE_SELECTION_AUDIT_V1",
        "checked_at": datetime.now(UTC).isoformat(),
        "read_only": True,
        "policy": AUTO_SELECTION_POLICY,
        "workspace_id": str(refresh.workspace_id),
        "runtime_files": check_hashes(expected_hashes),
    }
    try:
        async with database.session_context() as session:
            rows = (
                (await session.execute(QUERY, {"workspace_id": refresh.workspace_id}))
                .mappings()
                .all()
            )
        async with httpx.AsyncClient(trust_env=False, timeout=15) as client:
            response = await client.get("http://127.0.0.1:8000/api/v1/market-data/refresh/status")
            response.raise_for_status()
            runtime = response.json()
        status_counts: Counter[str] = Counter()
        provider_counts: Counter[str] = Counter()
        positions: Counter[str] = Counter()
        unresolved = []
        incompatible = []
        automatic_count = 0
        for row in rows:
            positions[str(row["position_id"])] += 1
            status_counts[row["selection_status"] or "UNBOUND"] += 1
            if row["provider"]:
                provider_counts[row["provider"]] += 1
            evidence = row["evidence"] or {}
            if evidence.get("selection_algorithm") == AUTO_SELECTION_POLICY:
                automatic_count += 1
            item = {
                key: row[key]
                for key in (
                    "position_id",
                    "trade_id",
                    "isin",
                    "selection_status",
                    "selection_reason",
                    "provider",
                    "policy_version",
                )
            }
            if row["selection_status"] != "SELECTED":
                unresolved.append(item)
            contract = ISSUER_INDICATIONS.get(row["provider"])
            if (
                contract
                and row["selection_status"] == "SELECTED"
                and row["policy_version"] != contract[2]
            ):
                incompatible.append(item)
        jobs = [
            {key: job.get(key) for key in ("job", "isin", "checked_at", "source_selection")}
            for job in runtime.get("jobs", [])
            if job.get("source_selection") is not None
        ]
        actual_enabled = runtime.get("settings", {}).get("auto_select_position_sources")
        checks = {
            "runtime_files_verified": bool(expected_hashes)
            and all(item["matches_package"] for item in report["runtime_files"]),
            "expected_selection_setting": actual_enabled is expected_enabled,
            "background_refresh_enabled": runtime.get("enabled") is True,
            "workspace_matches": str(runtime.get("workspace_id")) == str(refresh.workspace_id),
            "active_decisions_unique": all(count == 1 for count in positions.values()),
        }
        report.update(
            {
                "checks": checks,
                "auto_select_position_sources": actual_enabled,
                "refresh_leader": runtime.get("leader"),
                "summary": {
                    "open_positions": len(positions),
                    "statuses": dict(status_counts),
                    "selected_providers": dict(provider_counts),
                    "decisions_using_new_algorithm": automatic_count,
                    "issuer_policy_mismatch_count": len(incompatible),
                    "jobs_with_reconciliation_result": len(jobs),
                },
                "unresolved_positions": unresolved,
                "issuer_policy_mismatches": incompatible,
                "selection_jobs": jobs,
                "verification_status": (
                    "RUNTIME_VERIFIED" if all(checks.values()) else "RUNTIME_CHECK_FAILED"
                ),
                "coverage_note": "VERIFIED_MAPPINGS_ONLY_NO_NEW_ISSUER_ISIN_DISCOVERY",
            }
        )
        return report, 0 if all(checks.values()) else 2
    except Exception as exc:
        # Do not print response bodies, connection URLs or credentials.
        report.update({"verification_status": "AUDIT_FAILED", "error_type": type(exc).__name__})
        return report, 2
    finally:
        await database.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-hashes", required=True)
    parser.add_argument("--expected-enabled", choices=("true", "false"), default="true")
    args = parser.parse_args()
    result, code = asyncio.run(
        audit(json.loads(args.runtime_hashes), args.expected_enabled == "true")
    )
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    raise SystemExit(code)


if __name__ == "__main__":
    main()
