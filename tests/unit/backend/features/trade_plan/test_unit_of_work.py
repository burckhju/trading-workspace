from unittest.mock import AsyncMock, Mock

import pytest

from app.features.trade_plan.service.unit_of_work import SqlAlchemyTradePlanUnitOfWork


def _session():
    session = Mock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_trade_plan_uow_owns_transaction_boundary() -> None:
    session = _session()
    uow = SqlAlchemyTradePlanUnitOfWork(session)

    async with uow as entered:
        assert entered is uow
        await uow.flush()
        await uow.commit()

    session.flush.assert_awaited_once()
    session.commit.assert_awaited_once()
    session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_trade_plan_uow_rolls_back_on_error() -> None:
    session = _session()
    uow = SqlAlchemyTradePlanUnitOfWork(session)

    with pytest.raises(RuntimeError):
        async with uow:
            raise RuntimeError("boom")

    session.rollback.assert_awaited_once()
