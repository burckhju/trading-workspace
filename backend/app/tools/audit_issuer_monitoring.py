"""Audit confirmed rules and the running schedulers without changing alert/rule state.

Uses the backend's normal quote GETs (which can persist quote observations).
Never creates rules, alerts, notifications, selections, or executions.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from time import monotonic
from typing import Any

import httpx
from sqlalchemy import text

from app.core.config import get_settings
from app.database import DatabaseManager
from app.features.position_monitoring.backend_valuations import BackendProductValuations
from app.features.position_monitoring.domain.evaluator import PositionRuleEvaluator
from app.features.position_monitoring.service.rule_prices import (
    CycleProductValuations,
    rule_price,
)
from app.features.position_monitoring.service.subjects import SqlAlchemyMonitoringSubjectReader
from app.features.trade_position.domain.price_binding import PriceBasis
from app.providers.jpmorgan.products import INSTRUMENTS as JPMORGAN
from app.providers.morganstanley.products import ELIGIBLE_INSTRUMENTS as MORGAN_STANLEY

TARGETS = {
    **dict.fromkeys(JPMORGAN, "JPMORGAN"),
    **dict.fromkeys(MORGAN_STANLEY, "MORGAN_STANLEY"),
}


async def get_json(client: httpx.AsyncClient, path: str) -> dict[str, Any]:
    response = await client.get("/api/v1" + path)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("AUDIT_RESPONSE_INVALID")
    return payload


def summarize_background(monitoring: dict[str, Any], refresh: dict[str, Any]) -> dict[str, Any]:
    jobs = [
        j
        for j in refresh.get("jobs", [])
        if j.get("isin") in TARGETS and j.get("lane") in {"WARRANTS", "ISSUER_QUOTES"}
    ]
    checks = [c for c in monitoring.get("last_rule_checks", []) if c.get("isin") in TARGETS]
    verified_jobs = [
        j
        for j in jobs
        if any(
            q.get("provider") == TARGETS[j["isin"]]
            and q.get("bid") is not None
            and q.get("retrieved_at") is not None
            and not q.get("retained")
            and not q.get("refresh_error")
            for q in j.get("quotes", [])
        )
    ]
    return {
        "monitoring": monitoring,
        "quote_refresh": {
            k: refresh.get(k)
            for k in (
                "enabled",
                "leader",
                "last_scan_at",
                "last_error",
                "settings",
                "lanes",
            )
        },
        "issuer_refresh_jobs": [
            {
                k: j.get(k)
                for k in (
                    "isin",
                    "status",
                    "reason",
                    "checked_at",
                    "last_success_at",
                    "next_run_at",
                )
            }
            for j in jobs
        ],
        "issuer_rule_checks": checks,
        "scheduler_cycle_evidenced": bool(
            monitoring.get("enabled")
            and monitoring.get("running")
            and monitoring.get("last_cycle_completed_at")
            and not monitoring.get("last_error")
        ),
        "quote_refresh_leader_evidenced": bool(
            refresh.get("enabled")
            and refresh.get("leader")
            and refresh.get("last_scan_at")
            and not refresh.get("last_error")
        ),
        # A scan/leader flag does not prove that all target jobs have run successfully.
        "issuer_refresh_success_count": len(verified_jobs),
        "issuer_refresh_verified_isins": sorted({j["isin"] for j in verified_jobs}),
    }


async def audit(wait_seconds: int) -> dict[str, Any]:
    settings = get_settings()
    database = DatabaseManager(settings)
    try:
        async with database.session_context() as session:
            revision = (
                (await session.execute(text("SELECT version_num FROM alembic_version")))
                .scalars()
                .all()
            )
            resolutions = await SqlAlchemyMonitoringSubjectReader(
                session,
                for_rule_evaluation=True,
                workspace_id=settings.market_data.refresh.workspace_id,
            ).list_resolutions()
        by_position = {str(r.position_id): r for r in resolutions}
        async with httpx.AsyncClient(
            base_url="http://127.0.0.1:8000",
            timeout=65,
            trust_env=False,
            follow_redirects=False,
        ) as client:
            remote = BackendProductValuations(client)
            await remote.check_ready()
            coverage = await get_json(client, "/market-data/positions/quote-coverage")
            products = CycleProductValuations(remote)
            items = []
            for row in coverage["items"]:
                if row.get("isin") not in TARGETS:
                    continue
                item = {
                    "isin": row["isin"],
                    "position_id": row["position_id"],
                    "trade_id": row["trade_id"],
                    "rules": [],
                }
                resolution = by_position.get(str(row["position_id"]))
                if resolution is None or resolution.subject is None:
                    item["status"] = str(resolution.issue) if resolution else "SUBJECT_NOT_FOUND"
                    items.append(item)
                    continue
                subject = resolution.subject
                for rule in subject.rules:
                    check: dict[str, Any] = {
                        "rule_key": rule.rule_key,
                        "threshold": str(rule.threshold),
                        **(rule.price_binding.as_dict() if rule.price_binding else {}),
                    }
                    if rule.price_binding and rule.price_binding.basis is PriceBasis.UNDERLYING:
                        check.update(status="UNDERLYING_RULE", reason="SEPARATE_PRICE_BASIS")
                    else:
                        try:
                            result = await rule_price(
                                subject=subject,
                                rule=rule,
                                market_data=None,
                                products=products,
                                now=datetime.now(UTC),
                                checked_at=lambda: datetime.now(UTC),
                                max_age_days=settings.position_monitoring.max_completed_price_age_days,
                            )
                            check.update(status=result.status, reason=result.reason)
                            if result.observation:
                                check.update(result.observation.context or {})
                                evaluation = PositionRuleEvaluator.evaluate(
                                    rule=rule, observation=result.observation
                                )
                                check.update(
                                    observed_value=str(result.observation.value),
                                    would_trigger=evaluation.triggered,
                                )
                        except Exception as exc:
                            check.update(status="ERROR", reason=type(exc).__name__)
                    item["rules"].append(check)
                item["status"] = "RULES_INSPECTED"
                items.append(item)

            deadline = monotonic() + wait_seconds
            while True:
                monitoring = await get_json(client, "/position-monitoring/runtime/status")
                refresh = await get_json(client, "/market-data/refresh/status")
                background = summarize_background(monitoring, refresh)
                if (
                    (
                        background["scheduler_cycle_evidenced"]
                        and background["quote_refresh_leader_evidenced"]
                    )
                    or not monitoring.get("enabled")
                    or not refresh.get("enabled")
                    or monotonic() >= deadline
                ):
                    break
                print(
                    "Warte auf den ersten abgeschlossenen Hintergrundzyklus ...",
                    file=sys.stderr,
                    flush=True,
                )
                await asyncio.sleep(min(5, max(0, deadline - monotonic())))
            checks = [c for item in items for c in item["rules"]]
            return {
                "schema_version": "ISSUER_MONITORING_AUDIT_V1",
                "checked_at": datetime.now(UTC).isoformat(),
                "alembic_revisions": revision,
                "mutates_rule_state": False,
                "sends_notifications": False,
                "may_refresh_quotes": True,
                "summary": {
                    "open_target_positions": len(items),
                    "indicative_rules_checked": sum(
                        c.get("reason") == "ISSUER_INDICATION_CHECKED" for c in checks
                    ),
                    "blocked_rules": sum(c.get("status") == "BLOCKED" for c in checks),
                    "positions_without_rules": sum(i["status"] == "NO_RULES" for i in items),
                    "rule_errors": sum(
                        c.get("status") in {"ERROR", "MISSING", "STALE"} for c in checks
                    ),
                },
                "items": items,
                "background": background,
            }
    finally:
        await database.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wait-seconds", type=int, default=0)
    args = parser.parse_args()
    if not 0 <= args.wait_seconds <= 600:
        parser.error("--wait-seconds must be between 0 and 600")
    try:
        result = asyncio.run(audit(args.wait_seconds))
    except Exception as exc:
        print(
            json.dumps(
                {"schema_version": "ISSUER_MONITORING_AUDIT_V1", "error": type(exc).__name__}
            )
        )
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
