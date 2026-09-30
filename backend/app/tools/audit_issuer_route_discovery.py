"""Read-only deployment and coverage check; never initiate provider connections."""

import argparse
import asyncio
import json
from collections import Counter
from datetime import UTC, datetime

import httpx
from sqlalchemy import select, text

from app.core.config import get_settings
from app.database import DatabaseManager
from app.features.market_data.domain.enums import MarketDataProvider
from app.features.market_data.persistence.models import WarrantProviderMappingModel
from app.providers.issuer_bindings import read_bindings
from app.tools.audit_position_source_selection import audit as selection_audit


async def audit(
    expected_hashes: dict[str, str], expected_enabled: bool, expected_renderer: bool = False
) -> tuple[dict[str, object], int]:
    # Includes source hashes, uniqueness and policy checks already used by selection V1.
    selection, selection_code = await selection_audit(expected_hashes, True)
    selection["coverage_note"] = "VERIFIED_ROUTES_WITH_ISSUER_DISCOVERY_V1"
    settings = get_settings()
    workspace = settings.market_data.refresh.workspace_id
    database = DatabaseManager(settings)
    report = {
        "schema_version": "ISSUER_ROUTE_DISCOVERY_AUDIT_V1",
        "read_only": True,
        "checked_at": datetime.now(UTC).isoformat(),
        "selection_audit": selection,
    }
    try:
        async with database.session_context() as session:
            revisions = list(
                (await session.execute(text("SELECT version_num FROM alembic_version"))).scalars()
            )
            rows = list(
                await session.scalars(
                    select(WarrantProviderMappingModel).where(
                        WarrantProviderMappingModel.workspace_id == workspace,
                        WarrantProviderMappingModel.identity_evidence.is_not(None),
                    )
                )
            )
        dynamic: Counter[str] = Counter()
        invalid = []
        bindings = {
            provider: await read_bindings(database, workspace, provider)
            for provider in (
                MarketDataProvider.JPMORGAN,
                MarketDataProvider.MORGAN_STANLEY,
            )
        }
        for row in rows:
            if row.identity_evidence is None:
                continue
            dynamic[row.provider.value] += 1
            if bindings.get(row.provider, {}).get(row.provider_symbol) != row.identity_evidence.get(
                "stream_id"
            ):
                invalid.append(
                    {
                        "mapping_id": str(row.id),
                        "isin": row.provider_symbol,
                        "status": row.status.value,
                        "reason": "DYNAMIC_ROUTE_NOT_CURRENTLY_ELIGIBLE",
                    }
                )
        async with httpx.AsyncClient(trust_env=False, timeout=15) as client:
            response = await client.get("http://127.0.0.1:8000/api/v1/market-data/refresh/status")
            response.raise_for_status()
            runtime = response.json()
        jobs = [
            {
                key: job.get(key)
                for key in (
                    "job",
                    "isin",
                    "status",
                    "reason",
                    "checked_at",
                    "next_run_at",
                    "mapping_created",
                    "source_selection",
                    "required_action",
                    "listing_count",
                    "eligible_listing_count",
                )
            }
            for job in runtime.get("jobs", [])
            if job.get("lane") == "ISSUER_DISCOVERY"
        ]
        checks = {
            "source_selection_runtime_verified": selection_code == 0,
            "schema_revision_verified": revisions == ["20260928_0042"],
            "expected_discovery_setting": runtime.get("settings", {}).get(
                "auto_discover_issuer_routes"
            )
            is expected_enabled,
            "refresh_leader": runtime.get("leader") is True,
            "discovery_lane_available": "ISSUER_DISCOVERY" in runtime.get("lanes", {}),
        }
        renderer: dict[str, object] = {
            "configured": settings.market_data.refresh.issuer_renderer_enabled
        }
        checks["expected_renderer_setting"] = renderer["configured"] is expected_renderer
        if renderer["configured"]:
            from app.providers.issuer_rendered import RENDERER_URL

            try:
                async with httpx.AsyncClient(trust_env=False, timeout=5) as client:
                    response = await client.get(RENDERER_URL + "/health")
                    response.raise_for_status()
                    health = response.json()
                renderer.update(
                    {
                        key: health.get(key)
                        for key in (
                            "ready",
                            "version",
                            "chromium_sandbox",
                        )
                    }
                )
                checks["renderer_ready"] = (
                    renderer.get("ready") is True
                    and renderer.get("version") == "ISSUER_RENDERER_V1"
                    and renderer.get("chromium_sandbox") is True
                )
            except (httpx.HTTPError, ValueError):
                checks["renderer_ready"] = False
        report.update(
            {
                "checks": checks,
                "renderer": renderer,
                "dynamic_mappings": dict(dynamic),
                "ineligible_dynamic_routes": invalid,
                "discovery_jobs": jobs,
                "discovery_job_statuses": dict(Counter(job["status"] for job in jobs)),
                "verification_status": (
                    "RUNTIME_VERIFIED" if all(checks.values()) else "RUNTIME_CHECK_FAILED"
                ),
                "coverage_note": "RUNTIME_STATUS_IS_NOT_PROOF_OF_NEW_PRODUCT_PAGE_REACHABILITY",
            }
        )
        return report, 0 if all(checks.values()) else 2
    except Exception as exc:
        report.update({"verification_status": "AUDIT_FAILED", "error_type": type(exc).__name__})
        return report, 2
    finally:
        await database.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-hashes", required=True)
    parser.add_argument("--expected-enabled", choices=("true", "false"), default="true")
    parser.add_argument("--expected-renderer", choices=("true", "false"), default="false")
    args = parser.parse_args()
    result, code = asyncio.run(
        audit(
            json.loads(args.runtime_hashes),
            args.expected_enabled == "true",
            args.expected_renderer == "true",
        )
    )
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    raise SystemExit(code)


if __name__ == "__main__":
    main()
