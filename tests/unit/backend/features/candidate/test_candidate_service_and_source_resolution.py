from datetime import UTC, date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.features.candidate.domain.enums import CandidateStatus
from app.features.candidate.service.application import CandidateService
from app.features.candidate.service.source_resolution import SemanticTopDownSourceResolver
from app.features.market.persistence.top_down_models import UnderlyingSectorAssignmentModel


def _session():
    session = Mock()
    session.scalar = AsyncMock()
    session.scalars = AsyncMock()
    session.execute = AsyncMock()
    session.get = AsyncMock()
    session.add = Mock()
    session.commit = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_candidate_service_create_get_list_status_and_history_paths():
    session = _session()
    service = CandidateService(session)
    repo = Mock()
    repo.underlying_exists = AsyncMock(return_value=True)
    repo.get_by_underlying = AsyncMock(return_value=None)
    repo.commit = AsyncMock()
    repo.add = Mock()
    repo.list = AsyncMock(return_value=(SimpleNamespace(id=uuid4()),))
    repo.get = AsyncMock()
    repo.list_evaluations = AsyncMock(return_value=(SimpleNamespace(version=1),))
    repo.list_criteria = AsyncMock(return_value=(SimpleNamespace(criterion_id="X"),))
    service._repo = repo

    workspace, underlying = uuid4(), uuid4()
    created = await service.create(workspace, underlying, "tester")
    assert created.status == CandidateStatus.IDENTIFIED.value
    assert repo.add.call_count == 2

    repo.get_by_underlying.return_value = created
    assert await service.create(workspace, underlying, "tester") is created
    repo.underlying_exists.return_value = False
    with pytest.raises(ValueError, match="underlying does not exist"):
        await service.create(workspace, uuid4(), "tester")

    assert len(await service.list(workspace)) == 1
    repo.get.return_value = None
    with pytest.raises(ValueError, match="candidate not found"):
        await service.get(workspace, uuid4())

    repo.get.return_value = created
    created.status = CandidateStatus.IDENTIFIED.value
    changed = await service.change_status(workspace, created.id, CandidateStatus.UNDER_REVIEW, "tester", None)
    assert changed.status == CandidateStatus.UNDER_REVIEW.value
    assert repo.commit.await_count >= 2

    with pytest.raises(ValueError, match="rejection reason"):
        created.status = CandidateStatus.UNDER_REVIEW.value
        await service.change_status(workspace, created.id, CandidateStatus.REJECTED, "tester", None)

    created.status = CandidateStatus.WATCHING.value
    same = await service.change_status(workspace, created.id, CandidateStatus.WATCHING, "tester", None)
    assert same is created

    assert (await service.list_evaluations(created.id))[0].version == 1
    assert (await service.list_criteria(uuid4()))[0].criterion_id == "X"


@pytest.mark.asyncio
async def test_source_resolver_validation_and_latest_helpers():
    session = _session()
    resolver = SemanticTopDownSourceResolver(session)
    workspace = uuid4()

    scalar_rows = Mock()
    scalar_rows.all.return_value = []
    session.scalars.return_value = scalar_rows
    with pytest.raises(ValueError, match="no valid sector assignment"):
        await resolver._one_valid(
            UnderlyingSectorAssignmentModel,
            workspace_id=workspace,
            valid_on=date(2026, 8, 10),
            extra=(UnderlyingSectorAssignmentModel.underlying_id == uuid4(),),
            label="sector assignment",
        )

    scalar_rows.all.return_value = [SimpleNamespace(quality_status="GOOD"), SimpleNamespace(quality_status="GOOD")]
    with pytest.raises(ValueError, match="multiple overlapping"):
        await resolver._one_valid(
            UnderlyingSectorAssignmentModel,
            workspace_id=workspace,
            valid_on=date(2026, 8, 10),
            extra=(UnderlyingSectorAssignmentModel.underlying_id == uuid4(),),
            label="sector assignment",
        )

    scalar_rows.all.return_value = [SimpleNamespace(quality_status="INSUFFICIENT")]
    with pytest.raises(ValueError, match="quality is INSUFFICIENT"):
        await resolver._one_valid(
            UnderlyingSectorAssignmentModel,
            workspace_id=workspace,
            valid_on=date(2026, 8, 10),
            extra=(UnderlyingSectorAssignmentModel.underlying_id == uuid4(),),
            label="sector assignment",
        )

    good = SimpleNamespace(quality_status="GOOD")
    scalar_rows.all.return_value = [good]
    assert await resolver._one_valid(
        UnderlyingSectorAssignmentModel,
        workspace_id=workspace,
        valid_on=date(2026, 8, 10),
        extra=(UnderlyingSectorAssignmentModel.underlying_id == uuid4(),),
        label="sector assignment",
    ) is good

    resolver._latest_completed = AsyncMock(return_value=None)
    with pytest.raises(ValueError, match="no completed broad-market"):
        await resolver._latest_completed_for_listing(workspace, uuid4(), datetime.now(UTC), "broad-market")
    with pytest.raises(ValueError, match="no completed underlying"):
        await resolver._latest_completed_for_underlying(workspace, uuid4(), datetime.now(UTC))

    analysis_id = uuid4()
    resolver._latest_completed.return_value = (SimpleNamespace(id=analysis_id), SimpleNamespace(version=3))
    assert (await resolver._latest_completed_for_listing(workspace, uuid4(), datetime.now(UTC), "market")).version == 3
    assert (await resolver._latest_completed_for_underlying(workspace, uuid4(), datetime.now(UTC))).analysis_id == analysis_id


@pytest.mark.asyncio
async def test_source_resolver_listing_helper():
    resolver = SemanticTopDownSourceResolver(_session())
    listing_id = uuid4()
    resolver._one_valid = AsyncMock(return_value=SimpleNamespace(listing_id=listing_id))
    assert await resolver._listing_for_reference(uuid4(), uuid4(), date(2026,8,10), "sector") == listing_id
