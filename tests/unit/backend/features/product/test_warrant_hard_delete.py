from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from sqlalchemy.exc import IntegrityError

from app.features.product.service.errors import (
    WarrantConcurrentModification,
    WarrantDeleteBlocked,
    WarrantNotFound,
)
from app.features.product.service.hard_delete import WarrantHardDeleteService

WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")
WARRANT_ID = UUID("60000000-0000-4000-8000-000000000001")


class WarrantStub:
    def __init__(self, version: int) -> None:
        self.version = version


@pytest.mark.asyncio
async def test_delete_rejects_missing_warrant_without_mutation() -> None:
    session = AsyncMock()
    session.scalar.return_value = None
    service = WarrantHardDeleteService(session)

    with pytest.raises(WarrantNotFound):
        await service.delete(WORKSPACE_ID, WARRANT_ID, 1)

    session.execute.assert_not_awaited()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_rejects_stale_version_without_mutation() -> None:
    session = AsyncMock()
    session.scalar.return_value = WarrantStub(version=3)
    service = WarrantHardDeleteService(session)

    with pytest.raises(WarrantConcurrentModification):
        await service.delete(WORKSPACE_ID, WARRANT_ID, 2)

    session.execute.assert_not_awaited()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_removes_owned_records_and_commits_atomically() -> None:
    session = AsyncMock()
    session.scalar.return_value = WarrantStub(version=4)
    service = WarrantHardDeleteService(session)

    await service.delete(WORKSPACE_ID, WARRANT_ID, 4)

    assert session.execute.await_count == 3
    session.commit.assert_awaited_once_with()
    session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_rolls_back_when_external_history_restricts_owned_records() -> None:
    session = AsyncMock()
    session.scalar.return_value = WarrantStub(version=4)
    session.execute.side_effect = IntegrityError("DELETE", {}, Exception("foreign key restrict"))
    service = WarrantHardDeleteService(session)

    with pytest.raises(WarrantDeleteBlocked):
        await service.delete(WORKSPACE_ID, WARRANT_ID, 4)

    session.rollback.assert_awaited_once_with()
    session.commit.assert_not_awaited()
