"""Read and fingerprint only this run's independently marked disposable journal DB."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

WORKSPACE = "00000000-0000-4000-8000-000000000001"
REVISION = "20261017_0047"


def configured_target():
    if os.environ.get("CI") != "true" or os.environ.get("GITHUB_ACTIONS") != "true":
        raise RuntimeError("Only the dedicated GitHub Actions qualification is allowed")
    if os.environ.get("JOURNAL_E2E_WRITES_ALLOWED") != "1":
        raise RuntimeError("Explicit journal qualification authorization is required")
    if os.environ.get("FT011_E2E_WRITES_ALLOWED") != "1":
        raise RuntimeError("Explicit FT011 qualification authorization is required")
    if os.environ.get("TRADING_WORKSPACE_ENVIRONMENT") != "test":
        raise RuntimeError("Only the test environment is allowed")
    if os.environ.get("JOURNAL_E2E_WORKSPACE_ID") != WORKSPACE:
        raise RuntimeError("Unexpected synthetic workspace")
    run_id = str(UUID(os.environ["JOURNAL_E2E_RUN_ID"]))
    url = make_url(os.environ["TRADING_WORKSPACE_TEST_DATABASE_URL"])
    if url.database != "trading_workspace_test_journal_" + UUID(run_id).hex:
        raise RuntimeError("Database name does not identify this fresh run")
    if (url.drivername, url.host, url.port, url.username) != (
        "postgresql+asyncpg",
        "127.0.0.1",
        25432,
        "tw_journal_e2e",
    ):
        raise RuntimeError("Unexpected database driver, loopback endpoint or synthetic user")
    if make_url(os.environ["TRADING_WORKSPACE_DATABASE_URL"]) != url:
        raise RuntimeError("Application and qualification database targets differ")
    return run_id, url


async def verify():
    run_id, url = configured_target()
    engine = create_async_engine(url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            await connection.execute(
                text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            )
            identity = (
                await connection.execute(
                    text("SELECT current_database(), current_user, inet_server_port()")
                )
            ).one()
            if tuple(identity) != (url.database, url.username, 5432):
                raise RuntimeError("Connected database identity differs from the verified target")
            marker = await connection.scalar(
                text(
                    "SELECT shobj_description(oid, 'pg_database') FROM pg_database "
                    "WHERE datname = current_database()"
                )
            )
            if marker != f"synthetic journal-evidence browser {run_id}":
                raise RuntimeError("Database marker does not match this run")
            version = await connection.scalar(text("SHOW server_version_num"))
            if not 170000 <= int(version) < 180000:
                raise RuntimeError("This qualification requires PostgreSQL 17")
            revisions = (
                await connection.scalars(text("SELECT version_num FROM alembic_version"))
            ).all()
            if revisions != [REVISION]:
                raise RuntimeError("Unexpected or multiple migration heads")
            workspaces = (await connection.scalars(text("SELECT id FROM workspaces"))).all()
            if workspaces != [UUID(WORKSPACE)]:
                raise RuntimeError("Expected exactly the identified synthetic workspace")
            tables = (
                await connection.scalars(
                    text("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY 1")
                )
            ).all()
            scoped = set(
                (
                    await connection.scalars(
                        text(
                            "SELECT table_name FROM information_schema.columns "
                            "WHERE table_schema='public' AND column_name='workspace_id'"
                        )
                    )
                ).all()
            )
            contents = {}
            for table in tables:
                quoted = '"' + table.replace('"', '""') + '"'
                if table in scoped:
                    foreign = await connection.scalar(
                        text(
                            f"SELECT EXISTS (SELECT 1 FROM {quoted} "
                            "WHERE workspace_id IS DISTINCT FROM :workspace)"
                        ),
                        {"workspace": UUID(WORKSPACE)},
                    )
                    if foreign:
                        raise RuntimeError(f"Unexpected workspace data in {table}")
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
            return {
                "database": url.database,
                "run_id": run_id,
                "workspace_id": WORKSPACE,
                "postgresql_version_num": version,
                "schema_revision": REVISION,
                "fingerprint": hashlib.sha256(
                    json.dumps(contents, sort_keys=True).encode()
                ).hexdigest(),
                "tables": contents,
            }
    finally:
        await engine.dispose()


if __name__ == "__main__":
    print(json.dumps(asyncio.run(verify()), sort_keys=True))
