from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.features.product_selection.service.queries import ProductSelectionQueryService


@pytest.mark.asyncio
async def test_get_run_returns_complete_view():
    service = ProductSelectionQueryService.__new__(ProductSelectionQueryService)
    run = Mock(id=uuid4())
    evaluation = Mock()
    omission = Mock()
    selection = Mock()
    service._runs = Mock(get=AsyncMock(return_value=run))
    service._evaluations = Mock(list_for_run=AsyncMock(return_value=(evaluation,)))
    service._omissions = Mock(list_for_run=AsyncMock(return_value=(omission,)))
    service._selections = Mock(get_for_run=AsyncMock(return_value=selection))

    result = await service.get_run(uuid4(), run.id)

    assert result.run is run
    assert result.evaluations == (evaluation,)
    assert result.universe_omissions == (omission,)
    assert result.selection is selection


@pytest.mark.asyncio
async def test_get_run_rejects_missing_run():
    service = ProductSelectionQueryService.__new__(ProductSelectionQueryService)
    service._runs = Mock(get=AsyncMock(return_value=None))

    with pytest.raises(ValueError, match="product selection run not found"):
        await service.get_run(uuid4(), uuid4())


@pytest.mark.asyncio
async def test_list_for_trade_plan_version_delegates_to_repository():
    service = ProductSelectionQueryService.__new__(ProductSelectionQueryService)
    expected = (Mock(),)
    service._runs = Mock(list_for_trade_plan_version=AsyncMock(return_value=expected))
    workspace_id, version_id = uuid4(), uuid4()

    result = await service.list_for_trade_plan_version(workspace_id, version_id)

    assert result == expected
    service._runs.list_for_trade_plan_version.assert_awaited_once_with(workspace_id, version_id)


@pytest.mark.asyncio
async def test_get_evaluation_returns_scoped_evaluation():
    service = ProductSelectionQueryService.__new__(ProductSelectionQueryService)
    run = Mock(id=uuid4())
    evaluation = Mock()
    service._runs = Mock(get=AsyncMock(return_value=run))
    service._evaluations = Mock(get=AsyncMock(return_value=evaluation))

    result = await service.get_evaluation(uuid4(), run.id, uuid4())

    assert result is evaluation


@pytest.mark.asyncio
async def test_get_evaluation_rejects_missing_run_and_missing_evaluation():
    service = ProductSelectionQueryService.__new__(ProductSelectionQueryService)
    workspace_id, run_id, evaluation_id = uuid4(), uuid4(), uuid4()
    service._runs = Mock(get=AsyncMock(return_value=None))

    with pytest.raises(ValueError, match="product selection run not found"):
        await service.get_evaluation(workspace_id, run_id, evaluation_id)

    run = Mock(id=run_id)
    service._runs = Mock(get=AsyncMock(return_value=run))
    service._evaluations = Mock(get=AsyncMock(return_value=None))

    with pytest.raises(ValueError, match="product evaluation not found for run"):
        await service.get_evaluation(workspace_id, run_id, evaluation_id)
