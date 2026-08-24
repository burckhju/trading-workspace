from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.learning.domain import IdempotencyRecord, IdempotencyStatus
from app.features.learning.persistence.repositories import (
    SqlAlchemyIdempotencyRecordRepository,
)

NOW = datetime(2026, 8, 23, tzinfo=UTC)


@pytest.mark.asyncio
async def test_idempotency_add_get_and_mark_succeeded(
    learning_session: AsyncSession,
) -> None:
    repo = SqlAlchemyIdempotencyRecordRepository(learning_session)
    record = IdempotencyRecord(
        id=uuid4(),
        workspace_id=uuid4(),
        command_type="EXECUTE_AS_TRADE",
        idempotency_key="idem-1",
        request_fingerprint="a" * 64,
        status=IdempotencyStatus.IN_PROGRESS,
        created_at=NOW,
    )
    await repo.add(record)
    await learning_session.flush()

    loaded = await repo.get(record.workspace_id, record.command_type, record.idempotency_key)
    assert loaded == record

    result_id = uuid4()
    await repo.mark_succeeded(
        record_id=record.id,
        result_type="TRADE",
        result_id=result_id,
        completed_at=NOW,
    )
    await learning_session.flush()

    loaded = await repo.get(record.workspace_id, record.command_type, record.idempotency_key)
    assert loaded is not None
    assert loaded.status is IdempotencyStatus.SUCCEEDED
    assert loaded.result_id == result_id


@pytest.mark.asyncio
async def test_idempotency_mark_failed_final(
    learning_session: AsyncSession,
) -> None:
    repo = SqlAlchemyIdempotencyRecordRepository(learning_session)
    record = IdempotencyRecord(
        id=uuid4(),
        workspace_id=uuid4(),
        command_type="EXECUTE_AS_TRADE",
        idempotency_key="idem-2",
        request_fingerprint="b" * 64,
        status=IdempotencyStatus.IN_PROGRESS,
        created_at=NOW,
    )
    await repo.add(record)
    await learning_session.flush()
    await repo.mark_failed_final(
        record_id=record.id,
        completed_at=NOW,
        error_code="TRADE_CREATE_FAILED",
    )
    await learning_session.flush()

    loaded = await repo.get(record.workspace_id, record.command_type, record.idempotency_key)
    assert loaded is not None
    assert loaded.status is IdempotencyStatus.FAILED_FINAL
    assert loaded.error_code == "TRADE_CREATE_FAILED"


@pytest.mark.asyncio
async def test_idempotency_unique_command_key_per_workspace(
    learning_session: AsyncSession,
) -> None:
    repo = SqlAlchemyIdempotencyRecordRepository(learning_session)
    workspace_id = uuid4()
    first = IdempotencyRecord(
        id=uuid4(),
        workspace_id=workspace_id,
        command_type="EXECUTE_AS_TRADE",
        idempotency_key="same-key",
        request_fingerprint="c" * 64,
        status=IdempotencyStatus.IN_PROGRESS,
        created_at=NOW,
    )
    second = IdempotencyRecord(
        id=uuid4(),
        workspace_id=workspace_id,
        command_type="EXECUTE_AS_TRADE",
        idempotency_key="same-key",
        request_fingerprint="d" * 64,
        status=IdempotencyStatus.IN_PROGRESS,
        created_at=NOW,
    )
    await repo.add(first)
    await learning_session.flush()
    await repo.add(second)
    with pytest.raises(IntegrityError):
        await learning_session.flush()
