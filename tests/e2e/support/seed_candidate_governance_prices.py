"""Marked past prices only, after the independent Candidate journey target guard.

The browser creates every business object through its existing HTTP owner. This
fixture creates no analysis, evidence, hypothesis, proposal, approval, activation
or evaluation. Retrieved/created timestamps are now, never historical knowledge.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from candidate_governance_database_guard import verify
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

WORKSPACE = UUID("00000000-0000-4000-8000-000000000001")


def completed_days(today: date, count: int) -> list[date]:
    day = today - timedelta(days=1)
    result = []
    while len(result) < count:
        if day.weekday() < 5:
            result.append(day)
        day -= timedelta(days=1)
    return list(reversed(result))


async def seed(mode: str, identifiers: list[UUID]) -> dict[str, object]:
    state = await verify()
    if mode == "learning" and len(identifiers) == 2:
        trade_id, listing_id = identifiers
        listings = [listing_id]
        day = date(2026, 8, 19)
        days = []
        while len(days) < 20:
            if day.weekday() < 5:
                days.append(day)
            day += timedelta(days=1)
    elif (mode == "analyses" and len(identifiers) == 3 and len(set(identifiers)) == 3) or (
        mode == "warning" and len(identifiers) == 1
    ):
        listings = []
        days = completed_days(datetime.now(UTC).date(), 200)
    else:
        raise ValueError("Expected learning trade/listing, three analysis IDs or one warning ID")
    now = datetime.now(UTC)
    if any(day >= now.date() for day in days):
        raise ValueError("Future or unfinished synthetic observation days are prohibited")
    engine = create_async_engine(
        os.environ["TRADING_WORKSPACE_TEST_DATABASE_URL"], poolclass=NullPool
    )
    try:
        async with engine.begin() as connection:
            identity = await connection.scalar(text("SELECT current_database()"))
            marker = await connection.scalar(
                text(
                    "SELECT shobj_description(oid, 'pg_database') FROM pg_database "
                    "WHERE datname=current_database()"
                )
            )
            if identity != state["database"] or marker != (
                f"synthetic candidate-governance browser {state['run_id']}"
            ):
                raise RuntimeError("Fixture target changed after the independent guard")
            rows = []
            price_sources = []
            owners = []
            if mode != "learning":
                for index, analysis_id in enumerate(identifiers):
                    analysis = (
                        (
                            await connection.execute(
                                text(
                                    "SELECT a.id AS analysis_id, a.underlying_id, a.listing_id, "
                                    "a.created_by, i.id AS instrument_id, i.kind, "
                                    "i.market_reference_id, r.code AS reference_code, "
                                    "r.name AS reference_name, r.role AS reference_role, "
                                    "r.reference_type, "
                                    "r.active AS reference_active FROM market_analyses a "
                                    "JOIN market_data_instruments i "
                                    "ON i.id=a.market_data_instrument_id "
                                    "LEFT JOIN market_references r ON r.id=i.market_reference_id "
                                    "AND r.workspace_id=:workspace "
                                    "WHERE a.id=:analysis AND a.workspace_id=:workspace "
                                    "AND i.workspace_id=:workspace"
                                ),
                                {"analysis": analysis_id, "workspace": WORKSPACE},
                            )
                        )
                        .mappings()
                        .one()
                    )
                    if analysis["created_by"] != f"candidate-governance:{state['run_id']}":
                        raise RuntimeError("Only this run's API-created analysis is allowed")
                    reference_owner = mode == "analyses" and index < 2
                    if reference_owner:
                        if (
                            analysis["kind"] != "MARKET_REFERENCE"
                            or analysis["listing_id"] is not None
                            or analysis["underlying_id"] is not None
                            or not analysis["reference_active"]
                        ):
                            raise RuntimeError("Market/sector prices require real reference owners")
                        if index == 0:
                            if (
                                analysis["reference_code"],
                                analysis["reference_role"],
                                analysis["reference_type"],
                            ) != (
                                "DAX",
                                "BROAD_MARKET",
                                "INDEX",
                            ):
                                raise RuntimeError(
                                    "Expected the explicit bootstrapped DAX reference"
                                )
                        elif (
                            analysis["reference_role"] != "SECTOR_REFERENCE"
                            or analysis["reference_type"] != "SECTOR_INDEX"
                            or not analysis["reference_name"].startswith(
                                f"Candidate Governance CI {state['run_id']} "
                            )
                        ):
                            raise RuntimeError("Expected this run's synthetic sector reference")
                    elif analysis["kind"] != "LISTING" or analysis["listing_id"] is None:
                        raise RuntimeError("Underlying prices require a real listing owner")
                    owners.append(analysis)
                listings = [item["listing_id"] for item in owners if item["listing_id"]]
            else:
                owners = [
                    {"listing_id": listings[0], "analysis_id": None, "market_reference_id": None}
                ]
            for index, analysis in enumerate(owners):
                listing = analysis["listing_id"]
                if listing is None:
                    role = ("MARKET", "SECTOR")[index]
                    owner = {"instrument_id": analysis["instrument_id"]}
                    symbol = f"SYNTHETIC-CG-{role}-{str(analysis['analysis_id'])[:8]}"
                    mapping = {
                        "id": None,
                        "provider_symbol": symbol,
                        "status": None,
                    }
                else:
                    owner, mapping = await listing_source(connection, listing, mode, state)
                    if mode != "learning" and owner["instrument_id"] != analysis["instrument_id"]:
                        raise RuntimeError("Analysis and listing instrument identities must agree")
                price_sources.append(
                    {
                        "analysis_id": (
                            str(analysis["analysis_id"]) if analysis["analysis_id"] else None
                        ),
                        "listing_id": str(listing) if listing else None,
                        "market_reference_id": (
                            str(analysis["market_reference_id"])
                            if analysis["market_reference_id"]
                            else None
                        ),
                        "instrument_id": str(owner["instrument_id"]),
                        "mapping_id": str(mapping["id"]) if mapping["id"] else None,
                        "provider_symbol": mapping["provider_symbol"],
                        "mapping_status": mapping["status"],
                        "provider_verification": False,
                    }
                )
                count = await connection.scalar(
                    text(
                        "SELECT count(*) FROM daily_prices "
                        "WHERE market_data_instrument_id=:instrument"
                    ),
                    {"instrument": owner["instrument_id"]},
                )
                if count != 0:
                    raise RuntimeError("Never replace or append to existing price history")
                if mode == "learning":
                    relation = await connection.scalar(
                        text(
                            "SELECT count(*) FROM post_trade_observations "
                            "WHERE trade_id=:trade AND underlying_listing_id=:listing "
                            "AND workspace_id=:workspace AND status='ACTIVE'"
                        ),
                        {"trade": trade_id, "listing": listing, "workspace": WORKSPACE},
                    )
                    if relation != 1:
                        raise RuntimeError("An actual owner-created observation is required")
                for offset, day in enumerate(days):
                    if mode == "learning":
                        price = Decimal("102")
                    else:
                        slope = (Decimal("0.5"), Decimal(1), Decimal(2))[index]
                        price = Decimal(100) + slope * offset
                        if mode == "analyses" and index == 0 and offset == 199:
                            price = Decimal(190)
                    warning = ""
                    if mode == "learning":
                        warning = "synthetic candidate governance qualification; no provider"
                    elif mode == "warning" and offset == 199:
                        warning = "Synthetic qualification: source warning must remain visible"
                    rows.append(
                        dict(
                            id=uuid4(),
                            workspace=WORKSPACE,
                            listing=listing,
                            instrument=owner["instrument_id"],
                            day=day,
                            price=price,
                            high=price + 1,
                            low=price - 1,
                            now=now,
                            symbol=mapping["provider_symbol"],
                            warning=warning,
                        )
                    )
            await connection.execute(
                text(
                    "INSERT INTO daily_prices "
                    "(id,workspace_id,listing_id,market_data_instrument_id,trading_date,"
                    "open,high,low,close,adjusted_close,currency,provider,provider_symbol,"
                    "retrieved_at,source_updated_at,quality_status,warnings,price_type,"
                    "created_at,updated_at) VALUES "
                    "(:id,:workspace,:listing,:instrument,:day,:price,:high,:low,:price,:price,"
                    "'EUR','EODHD',:symbol,:now,NULL,'VALID',:warning,'EOD',:now,:now)"
                ),
                rows,
            )
        return {
            "mode": mode,
            "row_count": len(rows),
            "listing_ids": [str(v) for v in listings],
            "sources": price_sources,
            "start_date": days[0].isoformat(),
            "end_date": days[-1].isoformat(),
            "retrieved_at": now.isoformat(),
            "price_quality": "VALID",
            "warning_rows": sum(bool(row["warning"]) for row in rows),
            "source_updated_at": None,
            "synthetic": True,
            "calendar_scope": (
                f"{len(days)} completed weekdays, not certified exchange-calendar coverage"
            ),
        }
    finally:
        await engine.dispose()


async def listing_source(connection, listing, mode, state):
    """Retain the original exact owner/mapping guard for listing-owned fixture rows."""
    owner = (
        (
            await connection.execute(
                text(
                    "SELECT l.currency_code, i.id AS instrument_id, u.name "
                    "FROM listings l JOIN underlyings u ON u.id=l.underlying_id "
                    "JOIN market_data_instruments i ON i.listing_id=l.id "
                    "WHERE l.id=:listing AND l.workspace_id=:workspace "
                    "AND u.workspace_id=:workspace AND i.workspace_id=:workspace"
                ),
                {"listing": listing, "workspace": WORKSPACE},
            )
        )
        .mappings()
        .one()
    )
    if owner["currency_code"] != "EUR" or not owner["name"].startswith(
        f"Candidate Governance CI {state['run_id']} "
    ):
        raise RuntimeError("Only this run's API-created synthetic listing is allowed")
    mapping = (
        (
            await connection.execute(
                text(
                    "SELECT id, provider_symbol, status FROM provider_instrument_mappings "
                    "WHERE listing_id=:listing AND market_data_instrument_id=:instrument "
                    "AND workspace_id=:workspace AND provider='EODHD'"
                ),
                {"listing": listing, "instrument": owner["instrument_id"], "workspace": WORKSPACE},
            )
        )
        .mappings()
        .one()
    )
    expected_status = "DISABLED" if mode == "learning" else "ACTIVE"
    if mapping["status"] != expected_status or not mapping["provider_symbol"].startswith(
        "SYNTHETIC-CG-"
    ):
        raise RuntimeError("The exact synthetic administrative mapping is required")
    return owner, mapping


if __name__ == "__main__":
    print(json.dumps(asyncio.run(seed(sys.argv[1], [UUID(v) for v in sys.argv[2:]]))))
