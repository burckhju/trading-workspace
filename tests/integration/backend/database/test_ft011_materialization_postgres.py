"""PostgreSQL invariants for FT-011 -> FT-012 materialization."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine


def _test_database_url() -> str:
    url = os.environ.get("TRADING_WORKSPACE_TEST_DATABASE_URL", "")
    if not url:
        pytest.skip("TRADING_WORKSPACE_TEST_DATABASE_URL is not configured")
    if url.split("?", 1)[0].rsplit("/", 1)[-1] != "trading_workspace_test":
        pytest.fail("FT011 materialization test may run only against trading_workspace_test")
    return url


@pytest.mark.asyncio
async def test_materialization_tables_and_request_idempotency_are_database_enforced() -> None:
    engine = create_async_engine(_test_database_url())
    workspace_id = uuid4()
    evidence_id = uuid4()
    record_id = uuid4()
    now = datetime.now(UTC)

    async with engine.connect() as connection:
        transaction = await connection.begin()
        try:
            await connection.execute(
                text(
                    "INSERT INTO workspaces (id, name, created_at) "
                    "VALUES (:id, 'FT011 Materialization PG', :now)"
                ),
                {"id": workspace_id, "now": now},
            )
            await connection.execute(
                text(
                    "INSERT INTO learning_evidence "
                    "(id, workspace_id, evidence_type, created_at) "
                    "VALUES (:id, :workspace_id, 'FT011', :now)"
                ),
                {"id": evidence_id, "workspace_id": workspace_id, "now": now},
            )
            await connection.execute(
                text(
                    "INSERT INTO ft012_idempotency_records "
                    "(id, workspace_id, command_type, idempotency_key, request_fingerprint, "
                    "status, result_type, result_id, error_code, created_at, completed_at) "
                    "VALUES (:id, :workspace_id, 'MATERIALIZE_FT011_LEARNING_EVIDENCE', "
                    "'pg-idempotency', :fingerprint, 'SUCCEEDED', 'LEARNING_EVIDENCE', "
                    ":result_id, NULL, :now, :now)"
                ),
                {
                    "id": record_id,
                    "workspace_id": workspace_id,
                    "fingerprint": "a" * 64,
                    "result_id": evidence_id,
                    "now": now,
                },
            )

            persisted = await connection.execute(
                text(
                    "SELECT evidence_type FROM learning_evidence "
                    "WHERE id = :evidence_id AND workspace_id = :workspace_id"
                ),
                {"evidence_id": evidence_id, "workspace_id": workspace_id},
            )
            assert persisted.scalar_one() == "FT011"

            constraint = await connection.execute(
                text(
                    "SELECT contype FROM pg_constraint "
                    "WHERE conname = 'uq_ft011_evidence_exit_review_version' "
                    "AND conrelid = 'ft011_evidence'::regclass"
                )
            )
            assert constraint.scalar_one() == "u"

            with pytest.raises(IntegrityError):
                async with connection.begin_nested():
                    await connection.execute(
                        text(
                            "INSERT INTO ft012_idempotency_records "
                            "(id, workspace_id, command_type, idempotency_key, "
                            "request_fingerprint, status, result_type, result_id, error_code, "
                            "created_at, completed_at) VALUES "
                            "(:id, :workspace_id, 'MATERIALIZE_FT011_LEARNING_EVIDENCE', "
                            "'pg-idempotency', :fingerprint, 'SUCCEEDED', 'LEARNING_EVIDENCE', "
                            ":result_id, NULL, :now, :now)"
                        ),
                        {
                            "id": uuid4(),
                            "workspace_id": workspace_id,
                            "fingerprint": "a" * 64,
                            "result_id": evidence_id,
                            "now": now,
                        },
                    )
        finally:
            await transaction.rollback()
    await engine.dispose()
