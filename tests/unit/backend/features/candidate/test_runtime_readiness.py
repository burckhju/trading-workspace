from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.features.candidate.service.runtime_readiness import (
    RuntimeAwareCandidateLiveWorkflowService,
)


@pytest.mark.asyncio
async def test_runtime_step_is_complete_for_active_executable_candidate_model() -> None:
    service = RuntimeAwareCandidateLiveWorkflowService(Mock())
    version_id = uuid4()
    service._resolve_runtime = AsyncMock(
        return_value=SimpleNamespace(
            model_key="TOP_DOWN_CANDIDATE",
            model_version=3,
            model_version_id=version_id,
            definition={
                "schema": "TOP_DOWN_CANDIDATE/1.0",
                "direction": "LONG",
                "market_context_allowed": ["FAVORABLE", "CAUTIOUS"],
            },
        )
    )

    step = await service._runtime_step(uuid4())

    assert step.status == "COMPLETE"
    assert step.resource_id == version_id
    assert "version 3" in step.detail


@pytest.mark.asyncio
async def test_runtime_step_is_complete_for_active_executable_candidate_model_v2() -> None:
    service = RuntimeAwareCandidateLiveWorkflowService(Mock())
    version_id = uuid4()
    service._resolve_runtime = AsyncMock(
        return_value=SimpleNamespace(
            model_key="TOP_DOWN_CANDIDATE",
            model_version=4,
            model_version_id=version_id,
            definition={
                "schema": "TOP_DOWN_CANDIDATE/2.0",
                "direction": "LONG",
                "market_context_allowed": ["FAVORABLE"],
            },
        )
    )

    step = await service._runtime_step(uuid4())

    assert step.status == "COMPLETE"
    assert step.resource_id == version_id
    assert "version 4" in step.detail


@pytest.mark.asyncio
async def test_runtime_step_blocks_when_no_active_candidate_model_exists() -> None:
    service = RuntimeAwareCandidateLiveWorkflowService(Mock())
    service._resolve_runtime = AsyncMock(return_value=None)

    step = await service._runtime_step(uuid4())

    assert step.status == "BLOCKED"
    assert step.action == "ACTIVATE_CANDIDATE_MODEL"
    assert "No active TOP_DOWN_CANDIDATE" in step.detail


@pytest.mark.asyncio
async def test_runtime_step_blocks_incompatible_active_definition() -> None:
    service = RuntimeAwareCandidateLiveWorkflowService(Mock())
    version_id = uuid4()
    service._resolve_runtime = AsyncMock(
        return_value=SimpleNamespace(
            model_key="TOP_DOWN_CANDIDATE",
            model_version=4,
            model_version_id=version_id,
            definition={
                "schema": "TOP_DOWN_CANDIDATE/1.0",
                "direction": "LONG",
                "market_context_allowed": ["FAVORABLE", "CAUTIOUS"],
                "min_relative_strength": 0.7,
            },
        )
    )

    step = await service._runtime_step(uuid4())

    assert step.status == "BLOCKED"
    assert step.action == "ACTIVATE_COMPATIBLE_CANDIDATE_MODEL"
    assert step.resource_id == version_id
    assert "unsupported Candidate definition keys" in step.detail


@pytest.mark.asyncio
async def test_runtime_step_blocks_invalid_v2_definition() -> None:
    service = RuntimeAwareCandidateLiveWorkflowService(Mock())
    version_id = uuid4()
    service._resolve_runtime = AsyncMock(
        return_value=SimpleNamespace(
            model_key="TOP_DOWN_CANDIDATE",
            model_version=5,
            model_version_id=version_id,
            definition={
                "schema": "TOP_DOWN_CANDIDATE/2.0",
                "direction": "LONG",
                "market_context_allowed": ["CAUTIOUS"],
            },
        )
    )

    step = await service._runtime_step(uuid4())

    assert step.status == "BLOCKED"
    assert step.resource_id == version_id
    assert "TOP_DOWN_CANDIDATE/2.0" in step.detail
