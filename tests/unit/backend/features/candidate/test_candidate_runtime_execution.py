from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.features.analysis.domain.enums import (
    AnalysisQualityStatus,
    CriterionClassification,
)
from app.features.analysis.domain.top_down import ContextClassification, TradingDirection
from app.features.candidate.domain.models import AnalysisReference, CandidateEvaluationInput
from app.features.candidate.service.application import CandidateService


def _input(
    market_context: ContextClassification = ContextClassification.FAVORABLE,
) -> CandidateEvaluationInput:
    return CandidateEvaluationInput(
        direction=TradingDirection.LONG,
        market_context=market_context,
        market_quality=AnalysisQualityStatus.GOOD,
        sector_trend=CriterionClassification.POSITIVE,
        sector_relative_strength=CriterionClassification.POSITIVE,
        sector_quality=AnalysisQualityStatus.GOOD,
        underlying_long_trend=CriterionClassification.POSITIVE,
        underlying_medium_trend=CriterionClassification.POSITIVE,
        underlying_short_trend=CriterionClassification.NEUTRAL,
        underlying_relative_strength=CriterionClassification.POSITIVE,
        underlying_quality=AnalysisQualityStatus.GOOD,
    )


def _sources() -> dict[str, AnalysisReference]:
    return {
        role: AnalysisReference(
            analysis_id=uuid4(),
            version=1,
            model_id=f"{role}_ANALYSIS",
            model_version="1.0.0",
        )
        for role in ("MARKET", "SECTOR", "UNDERLYING")
    }


def _service() -> tuple[CandidateService, Mock]:
    session = Mock()
    service = CandidateService(session)
    repo = Mock()
    repo.get = AsyncMock(return_value=SimpleNamespace(id=uuid4()))
    repo.next_evaluation_version = AsyncMock(return_value=1)
    repo.add = Mock()
    repo.add_all = Mock()
    repo.commit = AsyncMock()
    service._repo = repo
    return service, repo


@pytest.mark.asyncio
async def test_candidate_evaluation_executes_active_governed_version() -> None:
    service, repo = _service()
    service._runtime = SimpleNamespace(
        resolve_by_key=AsyncMock(
            return_value=SimpleNamespace(
                model_key="TOP_DOWN_CANDIDATE",
                model_version=7,
                definition={
                    "schema": "TOP_DOWN_CANDIDATE/1.0",
                    "direction": "LONG",
                    "market_context_allowed": ["FAVORABLE", "CAUTIOUS"],
                },
            )
        )
    )
    workspace_id = uuid4()
    candidate_id = uuid4()

    result = await service.evaluate(workspace_id, candidate_id, _input(), _sources())

    assert result.model_id == "TOP_DOWN_CANDIDATE"
    assert result.model_version == "7"
    assert result.qualification == "QUALIFIED"
    service._runtime.resolve_by_key.assert_awaited_once_with(
        workspace_id=workspace_id,
        model_key="TOP_DOWN_CANDIDATE",
    )
    repo.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_activation_switch_changes_candidate_result_and_persisted_provenance() -> None:
    service, repo = _service()
    repo.next_evaluation_version = AsyncMock(side_effect=[1, 2])
    service._runtime = SimpleNamespace(
        resolve_by_key=AsyncMock(
            side_effect=[
                SimpleNamespace(
                    model_key="TOP_DOWN_CANDIDATE",
                    model_version=10,
                    definition={
                        "schema": "TOP_DOWN_CANDIDATE/2.0",
                        "direction": "LONG",
                        "market_context_allowed": ["FAVORABLE", "CAUTIOUS"],
                    },
                ),
                SimpleNamespace(
                    model_key="TOP_DOWN_CANDIDATE",
                    model_version=11,
                    definition={
                        "schema": "TOP_DOWN_CANDIDATE/2.0",
                        "direction": "LONG",
                        "market_context_allowed": ["FAVORABLE"],
                    },
                ),
            ]
        )
    )
    workspace_id = uuid4()
    candidate_id = uuid4()
    value = _input(ContextClassification.CAUTIOUS)
    sources = _sources()

    permissive = await service.evaluate(workspace_id, candidate_id, value, sources)
    strict = await service.evaluate(workspace_id, candidate_id, value, sources)

    assert permissive.version == 1
    assert permissive.model_version == "10"
    assert permissive.qualification == "QUALIFIED"
    assert strict.version == 2
    assert strict.model_version == "11"
    assert strict.qualification == "NOT_QUALIFIED"
    assert permissive.model_version == "10"
    assert service._runtime.resolve_by_key.await_count == 2
    assert repo.commit.await_count == 2


@pytest.mark.asyncio
async def test_candidate_evaluation_fails_closed_without_active_version() -> None:
    service, repo = _service()
    service._runtime = SimpleNamespace(resolve_by_key=AsyncMock(return_value=None))

    with pytest.raises(ValueError, match="no active TOP_DOWN_CANDIDATE model version"):
        await service.evaluate(uuid4(), uuid4(), _input(), _sources())

    repo.add.assert_not_called()
    repo.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_candidate_evaluation_fails_closed_for_incompatible_definition() -> None:
    service, repo = _service()
    service._runtime = SimpleNamespace(
        resolve_by_key=AsyncMock(
            return_value=SimpleNamespace(
                model_key="TOP_DOWN_CANDIDATE",
                model_version=8,
                definition={
                    "schema": "TOP_DOWN_CANDIDATE/1.0",
                    "direction": "LONG",
                    "market_context_allowed": ["FAVORABLE", "CAUTIOUS"],
                    "min_relative_strength": 0.03,
                },
            )
        )
    )

    with pytest.raises(ValueError, match="unsupported Candidate definition keys"):
        await service.evaluate(uuid4(), uuid4(), _input(), _sources())

    repo.add.assert_not_called()
    repo.commit.assert_not_awaited()
