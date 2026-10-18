"""Verify and fingerprint only the explicitly marked disposable report E2E DB."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool


async def verify() -> dict[str, object]:
    if os.environ.get("REPORT_E2E_WRITES_ALLOWED") != "1":
        raise RuntimeError("Explicit disposable report E2E authorization is required")
    if os.environ.get("TRADING_WORKSPACE_ENVIRONMENT") != "test":
        raise RuntimeError("Only the test environment is allowed")
    run_id = str(UUID(os.environ["REPORT_E2E_RUN_ID"]))
    configured = os.environ["TRADING_WORKSPACE_TEST_DATABASE_URL"]
    url = make_url(configured)
    if not re.fullmatch(r"tw_realized_report_e2e_[0-9a-f]{32}", url.database or ""):
        raise RuntimeError("Only a newly named disposable report database is allowed")
    if url.host != "127.0.0.1" or url.port != 35432:
        raise RuntimeError("This qualification uses only the identified loopback test cluster")
    app_url = make_url(os.environ["TRADING_WORKSPACE_DATABASE_URL"])
    if app_url != url:
        raise RuntimeError("Application and qualification database targets differ")
    engine = create_async_engine(url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SET TRANSACTION READ ONLY"))
            marker = await connection.scalar(
                text(
                    "SELECT shobj_description(oid, 'pg_database') FROM pg_database "
                    "WHERE datname = current_database()"
                )
            )
            if marker != f"synthetic realized-gross browser {run_id}":
                raise RuntimeError("Disposable database marker does not match this run")
            version = await connection.scalar(text("SELECT version()"))
            revision = await connection.scalar(text("SELECT version_num FROM alembic_version"))
            tables = (
                await connection.scalars(
                    text("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY 1")
                )
            ).all()
            contents: dict[str, dict[str, object]] = {}
            for table in tables:
                quoted = '"' + table.replace('"', '""') + '"'
                row = (
                    await connection.execute(
                        text(
                            "SELECT count(*) AS count, md5(coalesce(string_agg("
                            "row_to_json(t)::text, E'\\n' ORDER BY row_to_json(t)::text), '')) "
                            f"AS hash FROM {quoted} AS t"
                        )
                    )
                ).one()
                contents[table] = {"count": row._mapping["count"], "hash": row._mapping["hash"]}
            fingerprint = hashlib.sha256(json.dumps(contents, sort_keys=True).encode()).hexdigest()
            return {
                "database": url.database,
                "run_id": run_id,
                "postgresql": version,
                "schema_revision": revision,
                "fingerprint": fingerprint,
                "tables": contents,
            }
    finally:
        await engine.dispose()


if __name__ == "__main__":
    print(json.dumps(asyncio.run(verify()), sort_keys=True))
