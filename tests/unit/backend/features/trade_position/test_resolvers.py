from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.features.product.service.errors import WarrantNotFound
from app.features.trade_position.service.resolvers import (
    SqlAlchemyWorkspaceSelectionResolver,
    WarrantProductResolver,
)


def _session():
    session = Mock()
    session.scalar = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_workspace_selection_resolver_returns_exact_historical_context() -> None:
    session = _session()
    resolver = SqlAlchemyWorkspaceSelectionResolver(session)

    workspace_id = uuid4()
    run_id = uuid4()
    selection_id = uuid4()
    evaluation_id = uuid4()
    warrant_id = uuid4()
    trade_plan_id = uuid4()
    trade_plan_version_id = uuid4()

    selection = SimpleNamespace(
        id=selection_id,
        run_id=run_id,
        product_evaluation_id=evaluation_id,
    )
    run = SimpleNamespace(
        id=run_id,
        workspace_id=workspace_id,
        trade_plan_id=trade_plan_id,
        trade_plan_version_id=trade_plan_version_id,
    )
    evaluation = SimpleNamespace(
        id=evaluation_id,
        run_id=run_id,
        warrant_id=warrant_id,
    )

    session.scalar.side_effect = [
        selection,
        run,
        evaluation,
    ]

    result = await resolver.resolve(
        workspace_id,
        selection_id,
    )

    assert result.workspace_id == workspace_id
    assert result.product_id == warrant_id
    assert result.trade_plan_id == trade_plan_id
    assert result.trade_plan_version_id == trade_plan_version_id
    assert result.product_selection_id == selection_id
    assert result.product_evaluation_id == evaluation_id


@pytest.mark.asyncio
async def test_workspace_selection_resolver_returns_none_for_unknown_selection() -> None:
    session = _session()
    resolver = SqlAlchemyWorkspaceSelectionResolver(session)
    session.scalar.return_value = None

    result = await resolver.resolve(
        uuid4(),
        uuid4(),
    )

    assert result is None


@pytest.mark.asyncio
async def test_workspace_selection_resolver_rejects_cross_workspace_selection() -> None:
    session = _session()
    resolver = SqlAlchemyWorkspaceSelectionResolver(session)

    requested_workspace = uuid4()
    actual_workspace = uuid4()

    session.scalar.side_effect = [
        SimpleNamespace(
            id=uuid4(),
            run_id=uuid4(),
            product_evaluation_id=uuid4(),
        ),
        SimpleNamespace(
            id=uuid4(),
            workspace_id=actual_workspace,
            trade_plan_id=uuid4(),
            trade_plan_version_id=uuid4(),
        ),
    ]

    result = await resolver.resolve(
        requested_workspace,
        uuid4(),
    )

    assert result is None


class FakeWarrantService:
    def __init__(self) -> None:
        self.get = AsyncMock()


@pytest.mark.asyncio
async def test_product_resolver_returns_existing_warrant_identity() -> None:
    service = FakeWarrantService()
    resolver = WarrantProductResolver(service)

    workspace_id = uuid4()
    warrant_id = uuid4()

    service.get.return_value = SimpleNamespace(
        id=warrant_id,
        workspace_id=workspace_id,
    )

    result = await resolver.resolve(
        workspace_id,
        warrant_id,
    )

    service.get.assert_awaited_once_with(
        workspace_id,
        warrant_id,
    )
    assert result.workspace_id == workspace_id
    assert result.product_id == warrant_id


@pytest.mark.asyncio
async def test_product_resolver_returns_none_for_unknown_warrant() -> None:
    service = FakeWarrantService()
    resolver = WarrantProductResolver(service)

    service.get.side_effect = WarrantNotFound("Warrant does not exist")

    result = await resolver.resolve(
        uuid4(),
        uuid4(),
    )

    assert result is None
