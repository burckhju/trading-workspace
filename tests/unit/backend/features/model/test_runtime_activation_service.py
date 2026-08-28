from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.features.model.service.runtime_activation_service import RuntimeActivationService


@pytest.mark.asyncio
async def test_rejects_non_approved_version() -> None:
    workspace_id = uuid4()
    model_id = uuid4()
    version_id = uuid4()
    session = SimpleNamespace(
        scalar=AsyncMock(
            side_effect=[
                SimpleNamespace(id=model_id),
                SimpleNamespace(id=version_id, model_id=model_id, status="DRAFT"),
            ]
        )
    )

    with pytest.raises(ValueError, match="only APPROVED model version can be activated"):
        await RuntimeActivationService(session).activate(
            workspace_id=workspace_id,
            model_id=model_id,
            model_version_id=version_id,
            actor=uuid4(),
            correlation_id=None,
        )


@pytest.mark.asyncio
async def test_rejects_noop_activation_when_version_is_already_active() -> None:
    workspace_id = uuid4()
    model_id = uuid4()
    version_id = uuid4()
    activation = SimpleNamespace(model_version_id=version_id)
    version = SimpleNamespace(id=version_id, model_id=model_id, status="APPROVED")
    session = SimpleNamespace(
        scalar=AsyncMock(
            side_effect=[
                SimpleNamespace(id=model_id),
                version,
                SimpleNamespace(id=model_id),
                activation,
                version,
            ]
        )
    )

    with pytest.raises(ValueError, match="model version is already active"):
        await RuntimeActivationService(session).activate(
            workspace_id=workspace_id,
            model_id=model_id,
            model_version_id=version_id,
            actor=uuid4(),
            correlation_id=None,
        )


@pytest.mark.asyncio
async def test_activates_approved_version_and_commits_audit_record() -> None:
    workspace_id = uuid4()
    model_id = uuid4()
    version_id = uuid4()
    version = SimpleNamespace(id=version_id, model_id=model_id, status="APPROVED")
    session = SimpleNamespace(
        scalar=AsyncMock(
            side_effect=[
                SimpleNamespace(id=model_id),
                version,
                SimpleNamespace(id=model_id),
                None,
            ]
        ),
        add=Mock(),
        commit=AsyncMock(),
        rollback=AsyncMock(),
    )

    activation, returned_version = await RuntimeActivationService(session).activate(
        workspace_id=workspace_id,
        model_id=model_id,
        model_version_id=version_id,
        actor=uuid4(),
        correlation_id="corr-1",
    )

    assert activation.workspace_id == workspace_id
    assert activation.model_id == model_id
    assert activation.model_version_id == version_id
    assert activation.correlation_id == "corr-1"
    assert returned_version is version
    session.add.assert_called_once()
    session.commit.assert_awaited_once()
