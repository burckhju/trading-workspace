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
    elif mode == "analyses" and len(identifiers) == 3 and len(set(identifiers)) == 3:
        listings = identifiers
        days = completed_days(datetime.now(UTC).date(), 200)
    else:
        raise ValueError("Expected learning trade/listing or three distinct analysis listings")
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
            for index, listing in enumerate(listings):
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
                            {
                                "listing": listing,
                                "instrument": owner["instrument_id"],
                                "workspace": WORKSPACE,
                            },
                        )
                    )
                    .mappings()
                    .one()
                )
                expected_status = "DISABLED" if mode == "learning" else "ACTIVE"
                if mapping["status"] != expected_status or not mapping[
                    "provider_symbol"
                ].startswith("SYNTHETIC-CG-"):
                    raise RuntimeError("The exact synthetic administrative mapping is required")
                price_sources.append(
                    {
                        "listing_id": str(listing),
                        "instrument_id": str(owner["instrument_id"]),
                        "mapping_id": str(mapping["id"]),
                        "provider_symbol": mapping["provider_symbol"],
                        "mapping_status": mapping["status"],
                        "provider_verification": False,
                    }
                )
                count = await connection.scalar(
                    text("SELECT count(*) FROM daily_prices WHERE listing_id=:listing"),
                    {"listing": listing},
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
                        if index == 0 and offset == 199:
                            price = Decimal(190)
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
                    "'EUR','EODHD',:symbol,:now,NULL,'VALID',"
                    "'synthetic candidate governance qualification; no provider','EOD',:now,:now)"
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
            "source_updated_at": None,
            "synthetic": True,
        }
    finally:
        await engine.dispose()


if __name__ == "__main__":
    print(json.dumps(asyncio.run(seed(sys.argv[1], [UUID(v) for v in sys.argv[2:]]))))
