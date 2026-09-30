"""Read-only production acceptance: actual dynamic identity, stored quote and source decisions.

Never creates a route, position or quote. The background scheduler performs the
authorized discovery. Missing/failed stages remain visible and produce exit 2.
"""

import argparse
import asyncio
import json
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from time import monotonic
from uuid import UUID, uuid4

import httpx
from sqlalchemy import select, text

from app.core.config import get_settings
from app.database import DatabaseManager
from app.features.market_data.persistence.models import (
    WarrantProviderMappingModel,
    WarrantQuoteObservationModel,
)
from app.features.market_data.persistence.quote_identity import read_quote_identity
from app.features.market_data.service.types import WarrantQuoteRequest
from app.features.product.persistence.models import WarrantListingModel, WarrantModel

TARGETS = ("DE000JZ91459", "DE000MN5Y1X9")
POSITIONS = text("""
SELECT p.id AS position_id, s.selection_status, s.provider, s.selection_reason,
       s.warrant_provider_mapping_id AS mapping_id, s.identity_key, s.mapping_version
FROM positions p
JOIN trades t ON t.id = p.trade_id AND t.product_id = p.product_id
LEFT JOIN position_quote_source_selections s
  ON s.position_id = p.id AND s.workspace_id = t.workspace_id AND s.superseded_at IS NULL
WHERE t.workspace_id = :workspace AND p.product_id = :warrant
  AND t.cancelled_at IS NULL AND p.open_quantity > 0 AND p.closed_at IS NULL
""")


def positive_bid(value: object) -> bool:
    try:
        bid = Decimal(str(value))
        return bid.is_finite() and bid > 0
    except InvalidOperation:
        return False


async def snapshot(database: DatabaseManager, workspace: UUID) -> list[dict[str, object]]:
    items = []
    async with database.session_context() as session:
        await session.execute(text("SET TRANSACTION READ ONLY"))
        for isin in TARGETS:
            item = {
                "isin": isin,
                "identity_verified": False,
                "quote_verified": False,
                "execution_usable": False,
            }
            rows = (
                await session.execute(
                    select(WarrantModel, WarrantProviderMappingModel)
                    .join(WarrantListingModel, WarrantListingModel.warrant_id == WarrantModel.id)
                    .join(
                        WarrantProviderMappingModel,
                        WarrantProviderMappingModel.warrant_listing_id == WarrantListingModel.id,
                    )
                    .where(
                        WarrantModel.workspace_id == workspace,
                        WarrantModel.isin == isin,
                        WarrantListingModel.workspace_id == workspace,
                        WarrantProviderMappingModel.workspace_id == workspace,
                        WarrantProviderMappingModel.identity_evidence.is_not(None),
                    )
                )
            ).all()
            if len(rows) != 1:
                item["status"] = "DYNAMIC_MAPPING_MISSING_OR_AMBIGUOUS"
                items.append(item)
                continue
            warrant, mapping = rows[0]
            request = WarrantQuoteRequest(
                workspace,
                mapping.warrant_listing_id,
                uuid4(),
                datetime.now(UTC),
                expected_currency="EUR",
            )
            identity = await read_quote_identity(session, request, mapping.provider)
            item.update(
                {
                    "identity_verified": identity is not None,
                    "provider": mapping.provider.value,
                    "mapping_id": str(mapping.id),
                    "acquisition_mode": (mapping.identity_evidence or {}).get("acquisition_mode"),
                    "source_url": (mapping.identity_evidence or {}).get("source_url"),
                }
            )
            observed = await session.get(
                WarrantQuoteObservationModel,
                (workspace, mapping.warrant_listing_id, mapping.provider.value),
            )
            if identity and observed and observed.identity_key == identity.key:
                payload = observed.payload
                data = payload.get("data") or {}
                item.update(
                    {
                        "bid": data.get("bid"),
                        "ask": data.get("ask"),
                        "currency": data.get("currency"),
                        "quote_time_text": data.get("quote_time_text"),
                        "quote_time_basis": data.get("quote_time_basis"),
                        "quote_retrieved_at": payload.get("retrieved_at"),
                        "quote_observed_at": data.get("observed_at"),
                    }
                )
                try:
                    retrieved = datetime.fromisoformat(payload["retrieved_at"])
                    created = mapping.created_at
                    # PostgreSQL stores aware timestamps; never infer a missing quote date.
                    item["quote_verified"] = (
                        positive_bid(data.get("bid"))
                        and data.get("currency") == "EUR"
                        and data.get("observed_at") is None
                        and retrieved.utcoffset() is not None
                        and retrieved >= created
                    )
                except (ValueError, TypeError, KeyError):
                    item["quote_verified"] = False
            positions = (
                (await session.execute(POSITIONS, {"workspace": workspace, "warrant": warrant.id}))
                .mappings()
                .all()
            )
            item["open_position_count"] = len(positions)
            item["source_selections"] = [dict(row) for row in positions]
            selected = all(
                row["selection_status"] == "SELECTED"
                and str(row["mapping_id"]) == str(mapping.id)
                and row["provider"] == mapping.provider.value
                and identity is not None
                and row["identity_key"] == identity.key
                and row["mapping_version"] == mapping.version
                for row in positions
            )
            item["selection_verification"] = (
                "NOT_APPLICABLE_NO_OPEN_POSITION"
                if not positions
                else (
                    "DYNAMIC_ROUTE_SELECTED" if selected else "EXISTING_OR_UNRESOLVED_SOURCE_REVIEW"
                )
            )
            item["status"] = (
                "IDENTITY_AND_STORED_QUOTE_VERIFIED"
                if item["identity_verified"] and item["quote_verified"]
                else "AWAITING_IDENTITY_OR_QUOTE"
            )
            items.append(item)
    return items


async def audit(wait_seconds: int) -> tuple[dict[str, object], int]:
    settings = get_settings()
    database = DatabaseManager(settings)
    report = {
        "schema_version": "NEW_ISSUER_ROUTE_ACCEPTANCE_V1",
        "read_only": True,
        "workspace_id": str(settings.market_data.refresh.workspace_id),
        "source_clock_note": "RECEIPT_TIME_IS_NOT_QUOTE_TIME",
    }
    deadline = monotonic() + wait_seconds
    try:
        while True:
            items = await snapshot(database, settings.market_data.refresh.workspace_id)
            ready = all(
                item.get("quote_verified") and item.get("identity_verified") for item in items
            )
            if ready or monotonic() >= deadline:
                break
            await asyncio.sleep(min(5, max(0, deadline - monotonic())))
        async with httpx.AsyncClient(trust_env=False, timeout=10) as client:
            response = await client.get("http://127.0.0.1:8000/api/v1/market-data/refresh/status")
            response.raise_for_status()
            jobs = response.json().get("jobs", [])
        selection_pending = any(
            item.get("selection_verification") == "EXISTING_OR_UNRESOLVED_SOURCE_REVIEW"
            for item in items
        )
        report.update(
            {
                "checked_at": datetime.now(UTC).isoformat(),
                "items": items,
                "jobs": [
                    {
                        key: job.get(key)
                        for key in (
                            "job",
                            "isin",
                            "status",
                            "reason",
                            "checked_at",
                            "next_run_at",
                            "source_selection",
                        )
                    }
                    for job in jobs
                    if job.get("isin") in TARGETS
                ],
                "verification_status": (
                    "NEW_ROUTES_AND_QUOTES_VERIFIED"
                    if ready and not selection_pending
                    else "ACCEPTANCE_INCOMPLETE"
                ),
                "selection_note": (
                    "NO_TEST_POSITION_IS_CREATED; NO_OPEN_POSITION_MEANS_SELECTION_NOT_APPLICABLE"
                ),
            }
        )
        return report, 0 if ready and not selection_pending else 2
    except Exception as exc:
        report.update({"verification_status": "AUDIT_ERROR", "error_type": type(exc).__name__})
        return report, 2
    finally:
        await database.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--wait-seconds", type=int, choices=range(0, 121), default=0, metavar="0..120"
    )
    args = parser.parse_args()
    report, code = asyncio.run(audit(args.wait_seconds))
    print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    raise SystemExit(code)


if __name__ == "__main__":
    main()
