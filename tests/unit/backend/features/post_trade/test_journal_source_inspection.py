"""Source currentness remains an FT-011 non-writing, exact-version assessment."""

from dataclasses import replace
from types import SimpleNamespace
from uuid import uuid4

import pytest
from tests.unit.backend.features.post_trade.test_exit_review_service import (
    _observation,
    _planning,
    _prices,
    _service,
    _trade,
    _uow,
)

from app.features.post_trade.application.input_fingerprint import (
    build_exit_review_input_fingerprint,
)
from app.features.post_trade.domain import ExitReviewCurrentness, ExitReviewStatus
from app.features.post_trade.domain.observation_metrics import build_observation_evidence


@pytest.mark.parametrize(
    "variant, expected",
    [
        ("current", "CURRENT"),
        ("changed", "STALE"),
        ("superseded", "STALE"),
        ("stored_stale", "STALE"),
        ("missing", None),
        ("draft", None),
        ("foreign", None),
        ("unknown", None),
        ("incomplete", "STALE"),
        ("no_exit", "STALE"),
    ],
)
@pytest.mark.asyncio
async def test_owner_inspects_without_rewriting_review(variant, expected):
    ws, trade_id = uuid4(), uuid4()
    uow = _uow()
    observation = _observation(workspace_id=ws, trade_id=trade_id)
    trade = _trade(workspace_id=ws, trade_id=trade_id)
    planning = _planning()
    prices = _prices(observation.underlying_listing_id)
    evidence = build_observation_evidence(
        prices,
        full_exit_at=trade.full_exit_at,
        target_count=20,
        targets=planning.original_targets,
        stop=planning.original_stop,
    )
    version = SimpleNamespace(
        id=uuid4(),
        exit_review_id=uuid4(),
        status=ExitReviewStatus.FINALIZED,
        currentness=ExitReviewCurrentness.CURRENT,
        input_fingerprint=build_exit_review_input_fingerprint(
            trade=trade, planning=planning, evidence=evidence
        ),
    )
    uow.exit_review_versions.get.return_value = version
    uow.exit_review_versions.get_latest.return_value = version
    uow.exit_reviews.get.return_value = SimpleNamespace(
        id=version.exit_review_id, post_trade_observation_id=observation.id
    )
    uow.observations.get.return_value = observation
    if variant == "changed":
        trade = replace(trade, realized_gross_pnl=trade.realized_gross_pnl + 1)
    if variant == "superseded":
        uow.exit_review_versions.get_latest.return_value = SimpleNamespace(id=uuid4())
    if variant == "stored_stale":
        version.currentness = ExitReviewCurrentness.STALE
    if variant == "missing":
        uow.exit_review_versions.get.return_value = None
    if variant == "draft":
        version.status = ExitReviewStatus.DRAFT
    if variant == "foreign":
        uow.exit_reviews.get.return_value = None
    if variant == "unknown":
        version.input_fingerprint = None
    if variant == "incomplete":
        prices = prices[:19]
    if variant == "no_exit":
        trade = replace(trade, full_exit_at=None, is_fully_closed=False)
    service = _service(uow=uow, trade=trade, planning=planning, prices=prices)
    result = await service.inspect_version_currentness(workspace_id=ws, version_id=version.id)
    assert (result.value if result else None) == expected
    uow.commit.assert_not_awaited()
    uow.exit_review_versions.replace.assert_not_awaited()


@pytest.mark.parametrize("mismatch", [None, "trade", "observation", "review", "version"])
async def test_materialized_source_inspection_validates_exact_graph_without_mutation(mismatch):
    from unittest.mock import AsyncMock

    ws, trade_id, observation_id, review_id, version_id = (uuid4() for _ in range(5))
    uow = _uow()
    observation = SimpleNamespace(id=observation_id, trade_id=trade_id)
    review = SimpleNamespace(id=review_id, post_trade_observation_id=observation_id)
    version = SimpleNamespace(
        id=version_id,
        exit_review_id=review_id,
        version=1,
        status=ExitReviewStatus.FINALIZED,
        currentness=ExitReviewCurrentness.CURRENT,
    )
    uow.observations.get.return_value = observation
    uow.exit_reviews.get.return_value = review
    uow.exit_review_versions.get.return_value = version
    later = uuid4()
    uow.exit_review_versions.get_latest.return_value = SimpleNamespace(id=later)
    if mismatch == "trade":
        observation.trade_id = uuid4()
    if mismatch == "observation":
        review.post_trade_observation_id = uuid4()
    if mismatch == "review":
        version.exit_review_id = uuid4()
    if mismatch == "version":
        uow.exit_review_versions.get.return_value = None
    service = _service(uow=uow, trade=None, planning=None, prices=())
    service.inspect_version_currentness = AsyncMock(return_value=ExitReviewCurrentness.STALE)
    result = await service.inspect_materialized_source(
        workspace_id=ws,
        trade_id=trade_id,
        observation_id=observation_id,
        review_id=review_id,
        version_id=version_id,
    )
    if mismatch:
        assert result.source_currentness == "UNKNOWN" and result.version_number is None
        service.inspect_version_currentness.assert_not_awaited()
    else:
        assert result.stored_currentness == "CURRENT" and result.source_currentness == "STALE"
        assert result.superseded_by_version_id == later and result.version_number == 1
        service.inspect_version_currentness.assert_awaited_once_with(
            workspace_id=ws, version_id=version_id
        )
    uow.commit.assert_not_awaited()
    uow.exit_review_versions.replace.assert_not_awaited()
