"""Read and fingerprint only this run's independently marked disposable journal DB."""

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

WORKSPACE = "00000000-0000-4000-8000-000000000001"
REVISION = "20261028_0048"


def verify_global_issuer_audits(rows, run_id):
    """Only the two journeys' own CREATED issuer audits may be workspace-global."""
    if len(rows) > 2:
        raise RuntimeError("Unexpected number of global issuer audits")
    evidence = []
    issuer_ids = set()
    for row in rows:
        if (
            row["workspace_id"],
            row["aggregate_type"],
            row["actor_type"],
            row["actor_id"],
            row["actor_display_name"],
            row["data_origin"],
            row["change_type"],
            row["version_before"],
            row["version_after"],
        ) != (
            None,
            "ISSUER",
            "SYSTEM_USER",
            f"journal-evidence:{run_id}",
            "Synthetic journal CI",
            "MANUAL",
            "CREATED",
            None,
            1,
        ):
            raise RuntimeError("Unexpected global or foreign-workspace audit owner")
        issuer = row["issuer"]
        if not issuer or str(row["aggregate_id"]) != issuer["id"]:
            raise RuntimeError("Global issuer audit lacks its actual issuer")
        suffix = issuer["legal_name"].removeprefix(f"Journal CI {run_id} ")
        if (
            issuer["legal_name"] == suffix
            or not re.fullmatch(r"[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}", suffix)
            or UUID(suffix).version != 4
            or issuer["display_name"] != "Synthetic journal CI"
            or issuer["country_code"] is not None
            or issuer["lei"] is not None
            or issuer["is_active"] is not True
            or issuer["version"] != 1
            or row["audit_timestamp_matches"] is not True
        ):
            raise RuntimeError("Global issuer audit is not this run's unchanged synthetic issuer")
        expected_changes = {
            key: {"old": None, "new": issuer[key]}
            for key in (
                "legal_name",
                "display_name",
                "country_code",
                "lei",
                "is_active",
            )
        }
        if row["field_changes"] != expected_changes:
            raise RuntimeError("Global issuer audit content differs from its owner entity")
        if len(row["warrant_ids"]) != 1 or issuer["id"] in issuer_ids:
            raise RuntimeError("Global issuer audit lacks its unique own-workspace warrant")
        issuer_ids.add(issuer["id"])
        evidence.append(
            {
                "audit_id": str(row["id"]),
                "issuer_id": issuer["id"],
                "warrant_id": str(row["warrant_ids"][0]),
                "actor_id": row["actor_id"],
                "legal_name": issuer["legal_name"],
            }
        )
    return evidence


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
            global_issuer_audits = []
            for table in tables:
                quoted = '"' + table.replace('"', '""') + '"'
                if table == "audit_events":
                    # The issuer owner deliberately writes global audits. Inspect their
                    # actual entities and references; no blanket nullable-column exception.
                    audits = (
                        (
                            await connection.execute(
                                text(
                                    "SELECT a.*, row_to_json(i) AS issuer, "
                                    "(i.created_at = a.occurred_at AND "
                                    "i.updated_at = a.occurred_at) AS audit_timestamp_matches, "
                                    "ARRAY(SELECT w.id FROM warrants w WHERE w.issuer_id = i.id "
                                    "AND w.workspace_id = :workspace) AS warrant_ids "
                                    "FROM audit_events a LEFT JOIN issuers i "
                                    "ON i.id = a.aggregate_id "
                                    "WHERE a.workspace_id IS DISTINCT FROM :workspace ORDER BY a.id"
                                ),
                                {"workspace": UUID(WORKSPACE)},
                            )
                        )
                        .mappings()
                        .all()
                    )
                    global_issuer_audits = verify_global_issuer_audits(audits, run_id)
                elif table in scoped:
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
                "global_issuer_audits": global_issuer_audits,
                "fingerprint": hashlib.sha256(
                    json.dumps(contents, sort_keys=True).encode()
                ).hexdigest(),
                "tables": contents,
            }
    finally:
        await engine.dispose()


if __name__ == "__main__":
    print(json.dumps(asyncio.run(verify()), sort_keys=True))
