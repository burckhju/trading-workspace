"""Native regression for the candidate-before-CREATED-event persistence boundary.

Only the underlying/workspace are explicit fixtures. Candidate and event must be
created by the real owner, unlike the historical FT-019 evaluation-only fixture.
The inherited learning_session requires the migrated disposable PostgreSQL target.
"""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.candidate.persistence.models import CandidateEventModel, CandidateModel
from app.features.candidate.service.application import CandidateService
from app.features.market.domain.enums import (
    DataOrigin,
    LifecycleStatus,
    QualityStatus,
    UnderlyingType,
)
from app.features.market.persistence.models import UnderlyingModel, WorkspaceModel


async def test_candidate_owner_persists_parent_and_exactly_one_created_event(
    learning_session: AsyncSession,
) -> None:
    workspace_id, underlying_id = uuid4(), uuid4()
    now = datetime.now(UTC)
    learning_session.add(
        WorkspaceModel(id=workspace_id, name="Synthetic candidate creation", created_at=now)
    )
    await learning_session.flush()
    learning_session.add(
        UnderlyingModel(
            id=underlying_id,
            workspace_id=workspace_id,
            type=UnderlyingType.STOCK,
            name="Synthetic candidate parent fixture",
            isin=None,
            wkn=None,
            lifecycle_status=LifecycleStatus.ACTIVE,
            quality_status=QualityStatus.DRAFT,
            version=1,
            created_at=now,
            updated_at=now,
            data_origin=DataOrigin.MANUAL,
        )
    )
    await learning_session.flush()

    service = CandidateService(learning_session)
    created = await service.create(workspace_id, underlying_id, "synthetic-candidate-owner")
    candidate_id = created.id
    learning_session.expire_all()
    stored = (
        await learning_session.scalars(
            select(CandidateModel).where(
                CandidateModel.workspace_id == workspace_id,
                CandidateModel.underlying_id == underlying_id,
            )
        )
    ).one()
    assert stored.id == candidate_id
    assert stored.status == "IDENTIFIED"
    assert stored.created_by == "synthetic-candidate-owner"
    event = (
        await learning_session.scalars(
            select(CandidateEventModel).where(CandidateEventModel.candidate_id == candidate_id)
        )
    ).one()
    assert event.event_type == "CREATED"
    assert event.from_status is None
    assert event.to_status == "IDENTIFIED"
    assert event.actor == stored.created_by
    assert event.occurred_at == stored.created_at

    # The existing deliberate lookup of the same underlying must return the
    # retained candidate without appending another creation event.
    assert (await service.create(workspace_id, underlying_id, "another-actor")).id == candidate_id
    assert (
        await learning_session.scalars(
            select(CandidateEventModel).where(CandidateEventModel.candidate_id == candidate_id)
        )
    ).all() == [event]
