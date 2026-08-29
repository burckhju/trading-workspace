from datetime import UTC, datetime
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


@pytest.mark.asyncio
async def test_resolves_active_approved_model_by_stable_key() -> None:
    workspace_id = uuid4()
    model_id = uuid4()
    version_id = uuid4()
    activation_id = uuid4()
    actor_id = uuid4()
    activated_at = datetime(2026, 8, 29, 8, 30, tzinfo=UTC)
    model = SimpleNamespace(id=model_id, model_key="TOP_DOWN_CANDIDATE")
    activation = SimpleNamespace(
        id=activation_id,
        model_version_id=version_id,
        activated_at=activated_at,
        activated_by=actor_id,
        correlation_id="candidate-runtime",
    )
    version = SimpleNamespace(
        id=version_id,
        model_id=model_id,
        version=2,
        status="APPROVED",
        definition={"min_relative_strength": 1.2},
    )
    session = SimpleNamespace(scalar=AsyncMock(side_effect=[model, activation, version]))

    resolved = await RuntimeActivationService(session).resolve_by_key(
        workspace_id=workspace_id,
        model_key="TOP_DOWN_CANDIDATE",
    )

    assert resolved is not None
    assert resolved.model_id == model_id
    assert resolved.model_key == "TOP_DOWN_CANDIDATE"
    assert resolved.model_version_id == version_id
    assert resolved.model_version == 2
    assert resolved.definition == {"min_relative_strength": 1.2}
    assert resolved.activation_id == activation_id
    assert resolved.activated_at == activated_at
    assert resolved.activated_by == actor_id
    assert resolved.correlation_id == "candidate-runtime"


@pytest.mark.asyncio
async def test_resolve_by_key_returns_none_when_model_has_no_activation() -> None:
    model = SimpleNamespace(id=uuid4(), model_key="TOP_DOWN_CANDIDATE")
    session = SimpleNamespace(scalar=AsyncMock(side_effect=[model, None]))

    resolved = await RuntimeActivationService(session).resolve_by_key(
        workspace_id=uuid4(),
        model_key="TOP_DOWN_CANDIDATE",
    )

    assert resolved is None


@pytest.mark.asyncio
async def test_resolve_by_key_rejects_missing_model() -> None:
    session = SimpleNamespace(scalar=AsyncMock(return_value=None))

    with pytest.raises(ValueError, match="governed model not found"):
        await RuntimeActivationService(session).resolve_by_key(
            workspace_id=uuid4(),
            model_key="TOP_DOWN_CANDIDATE",
        )


@pytest.mark.asyncio
async def test_resolve_by_key_rejects_inconsistent_non_approved_activation() -> None:
    model_id = uuid4()
    version_id = uuid4()
    model = SimpleNamespace(id=model_id, model_key="TOP_DOWN_CANDIDATE")
    activation = SimpleNamespace(model_version_id=version_id)
    version = SimpleNamespace(
        id=version_id,
        model_id=model_id,
        version=2,
        status="DRAFT",
        definition={"min_relative_strength": 1.2},
    )
    session = SimpleNamespace(scalar=AsyncMock(side_effect=[model, activation, version]))

    with pytest.raises(ValueError, match="active model version is not APPROVED"):
        await RuntimeActivationService(session).resolve_by_key(
            workspace_id=uuid4(),
            model_key="TOP_DOWN_CANDIDATE",
        )


@pytest.mark.asyncio
async def test_resolve_by_key_rejects_blank_key() -> None:
    session = SimpleNamespace(scalar=AsyncMock())

    with pytest.raises(ValueError, match="model_key is required"):
        await RuntimeActivationService(session).resolve_by_key(
            workspace_id=uuid4(),
            model_key="   ",
        )

    session.scalar.assert_not_awaited()
