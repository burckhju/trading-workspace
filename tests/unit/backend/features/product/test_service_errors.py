from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError

from app.features.product.service.application import WarrantService
from app.features.product.service.errors import (
    DuplicateWarrantIsin,
    WarrantConcurrentModification,
)


@pytest.mark.asyncio
async def test_commit_translates_stale_write_into_concurrency_error() -> None:
    session = AsyncMock()
    session.commit.side_effect = StaleDataError("stale")
    service = WarrantService(session)

    with pytest.raises(WarrantConcurrentModification):
        await service._commit()

    session.rollback.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_commit_translates_isin_constraint_race_into_duplicate_error() -> None:
    session = AsyncMock()
    session.commit.side_effect = IntegrityError(
        "insert",
        {},
        Exception("duplicate key violates constraint uq_warrants_workspace_isin"),
    )
    service = WarrantService(session)

    with pytest.raises(DuplicateWarrantIsin):
        await service._commit()

    session.rollback.assert_awaited_once_with()
