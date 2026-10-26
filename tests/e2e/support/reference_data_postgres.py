"""Optional read-only SQL evidence for an identified native UI5 disposable stack.

The normal smoke test proves the browser/API/readback path without Python access.
This additional reader verifies exact persisted assignment provenance locally.
It never creates or changes data and does not define a production endpoint.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
from urllib.parse import urlsplit
from uuid import UUID

import asyncpg


async def inspect(underlying: UUID, assignment: UUID) -> None:
    database_url = os.environ.get("TRADING_WORKSPACE_TEST_DATABASE_URL", "")
    parsed = urlsplit(database_url)
    run_id = os.environ.get("REFERENCE_DATA_E2E_RUN_ID", "")
    if (
        parsed.scheme != "postgresql+asyncpg"
        or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
        or parsed.path != "/trading_workspace_test"
        or parsed.query
        or parsed.fragment
        or not re.fullmatch(r"[a-f0-9]{32}", run_id)
    ):
        raise SystemExit("An identified loopback UI5 test database is required")
    connection = await asyncpg.connect(
        database_url.replace("postgresql+asyncpg:", "postgresql:", 1)
    )
    try:
        async with connection.transaction(readonly=True):
            marker = await connection.fetchval(
                "SELECT shobj_description(oid, 'pg_database') FROM pg_database "
                "WHERE datname = current_database()"
            )
            if marker != f"UI5 synthetic only {run_id}":
                raise SystemExit("Refusing an unidentified database")
            row = await connection.fetchrow(
                "SELECT a.id AS assignment_id, a.underlying_id, a.sector_id, "
                "a.valid_from, a.valid_to, a.source, a.source_reference, a.quality_status, "
                "u.name, s.code, current_setting('server_version') AS postgres_version, "
                "(SELECT count(*) FROM underlying_sector_assignments all_rows "
                "WHERE all_rows.underlying_id = u.id) AS count "
                "FROM underlying_sector_assignments a "
                "JOIN underlyings u ON u.id = a.underlying_id "
                "JOIN sectors s ON s.id = a.sector_id "
                "WHERE a.id = $1 AND a.underlying_id = $2 "
                "AND a.workspace_id = '00000000-0000-4000-8000-000000000001'",
                assignment,
                underlying,
            )
            if (
                row is None
                or not row["name"].startswith("TEST ONLY UI5 ")
                or not row["code"].startswith("UI5-")
            ):
                raise SystemExit("Synthetic UI5 assignment identity did not match")
            print(json.dumps(dict(row), default=str, sort_keys=True))
    finally:
        await connection.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--underlying", required=True, type=UUID)
    parser.add_argument("--assignment", required=True, type=UUID)
    args = parser.parse_args()
    asyncio.run(inspect(args.underlying, args.assignment))
