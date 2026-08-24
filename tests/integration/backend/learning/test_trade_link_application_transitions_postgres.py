from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from test_trade_link_application_postgres import (
    FixedClock,
    QueueIds,
    _seed_external_trade,
    _seed_observation,
    _seed_parents,
)

from app.features.learning.application.read_adapters import (
    SqlAlchemyProductReader,
    SqlAlchemyTradeReader,
)
from app.features.learning.application.trade_link_service import (
    ExternalObservationTradeLinkService,
    TradeLinkErrorCode,
    TradeLinkServiceError,
)
from app.features.learning.domain import (
    TradeLinkChangeReason,
    TradeLinkStatus,
)
from app.features.learning.persistence.unit_of_work import (
    SqlAlchemyLearningTradeLinkUnitOfWork,
)

NOW = datetime(2026, 8, 23, tzinfo=UTC)


def _service(
    session: AsyncSession,
    *ids: UUID,
) -> ExternalObservationTradeLinkService:
    return ExternalObservationTradeLinkService(
        uow=SqlAlchemyLearningTradeLinkUnitOfWork(session),
        trade_reader=SqlAlchemyTradeReader(session),
        product_reader=SqlAlchemyProductReader(session),
        clock=FixedClock(),
        id_factory=QueueIds(*ids),
    )


async def _create_initial_link(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    observation_id: UUID,
    trade_id: UUID,
) -> tuple[UUID, UUID]:
    link_id = uuid4()
    version_id = uuid4()
    result = await _service(session, link_id, version_id).create(
        workspace_id=workspace_id,
        external_observation_id=observation_id,
        trade_id=trade_id,
        actor_id=uuid4(),
    )
    assert result.id == version_id
    return link_id, version_id


@pytest.mark.asyncio
async def test_correct_target_creates_active_next_version(
    learning_session: AsyncSession,
) -> None:
    workspace_id, _, underlying_id, product_id = await _seed_parents(learning_session)
    trade_a = await _seed_external_trade(
        learning_session,
        workspace_id=workspace_id,
        product_id=product_id,
    )
    trade_b = await _seed_external_trade(
        learning_session,
        workspace_id=workspace_id,
        product_id=product_id,
    )
    observation_id, current_source_id = await _seed_observation(
        learning_session,
        workspace_id=workspace_id,
        underlying_id=underlying_id,
        product_id=product_id,
    )
    link_id, v1_id = await _create_initial_link(
        learning_session,
        workspace_id=workspace_id,
        observation_id=observation_id,
        trade_id=trade_a,
    )

    v2_id = uuid4()
    result = await _service(learning_session, v2_id).correct_target(
        workspace_id=workspace_id,
        trade_link_id=link_id,
        trade_id=trade_b,
        actor_id=uuid4(),
        change_note="target corrected",
    )

    assert result.id == v2_id
    assert result.version == 2
    assert result.status is TradeLinkStatus.ACTIVE
    assert result.change_reason is TradeLinkChangeReason.TARGET_CORRECTED
    assert result.trade_id == trade_b
    assert result.external_observation_version_id == current_source_id
    assert result.supersedes_version_id == v1_id

    row = (
        await learning_session.execute(
            text("""
                select current_version_id
                from external_observation_trade_links
                where id = :link_id
                """),
            {"link_id": link_id},
        )
    ).one()
    assert row.current_version_id == v2_id


@pytest.mark.asyncio
async def test_retract_preserves_trade_and_source(
    learning_session: AsyncSession,
) -> None:
    workspace_id, _, underlying_id, product_id = await _seed_parents(learning_session)
    trade_id = await _seed_external_trade(
        learning_session,
        workspace_id=workspace_id,
        product_id=product_id,
    )
    observation_id, source_id = await _seed_observation(
        learning_session,
        workspace_id=workspace_id,
        underlying_id=underlying_id,
        product_id=product_id,
    )
    link_id, v1_id = await _create_initial_link(
        learning_session,
        workspace_id=workspace_id,
        observation_id=observation_id,
        trade_id=trade_id,
    )

    v2_id = uuid4()
    result = await _service(learning_session, v2_id).retract(
        workspace_id=workspace_id,
        trade_link_id=link_id,
        actor_id=uuid4(),
        change_note="retracted",
    )

    assert result.version == 2
    assert result.status is TradeLinkStatus.RETRACTED
    assert result.change_reason is TradeLinkChangeReason.LINK_RETRACTED
    assert result.trade_id == trade_id
    assert result.external_observation_version_id == source_id
    assert result.supersedes_version_id == v1_id


@pytest.mark.asyncio
async def test_reactivate_same_target_uses_current_source(
    learning_session: AsyncSession,
) -> None:
    workspace_id, _, underlying_id, product_id = await _seed_parents(learning_session)
    trade_id = await _seed_external_trade(
        learning_session,
        workspace_id=workspace_id,
        product_id=product_id,
    )
    observation_id, old_source_id = await _seed_observation(
        learning_session,
        workspace_id=workspace_id,
        underlying_id=underlying_id,
        product_id=product_id,
    )
    link_id, _ = await _create_initial_link(
        learning_session,
        workspace_id=workspace_id,
        observation_id=observation_id,
        trade_id=trade_id,
    )

    retract_id = uuid4()
    await _service(learning_session, retract_id).retract(
        workspace_id=workspace_id,
        trade_link_id=link_id,
        actor_id=uuid4(),
    )

    current_source_id = uuid4()
    await learning_session.execute(
        text("""
            insert into external_observation_versions (
                id, external_observation_id, version,
                underlying_id, product_id,
                source_type, source_name, external_reference,
                observed_at, recorded_at, imported_at,
                recording_method, import_row_id, source_metadata,
                supersedes_version_id, created_at, created_by
            )
            values (
                :id, :observation_id, 2,
                :underlying_id, :product_id,
                'MANUAL', 'application-pg-v2', null,
                :observed_at, :recorded_at, null,
                'MANUAL', null, null,
                :supersedes, :created_at, :created_by
            )
            """),
        {
            "id": current_source_id,
            "observation_id": observation_id,
            "underlying_id": underlying_id,
            "product_id": product_id,
            "observed_at": NOW,
            "recorded_at": NOW,
            "supersedes": old_source_id,
            "created_at": NOW,
            "created_by": uuid4(),
        },
    )
    await learning_session.execute(
        text("""
            update external_observations
            set current_version_id = :current_source_id
            where id = :observation_id
            """),
        {
            "current_source_id": current_source_id,
            "observation_id": observation_id,
        },
    )
    await learning_session.flush()

    reactivate_id = uuid4()
    result = await _service(learning_session, reactivate_id).reactivate(
        workspace_id=workspace_id,
        trade_link_id=link_id,
        actor_id=uuid4(),
    )

    assert result.version == 3
    assert result.status is TradeLinkStatus.ACTIVE
    assert result.change_reason is TradeLinkChangeReason.LINK_REACTIVATED
    assert result.trade_id == trade_id
    assert result.external_observation_version_id == current_source_id
    assert result.supersedes_version_id == retract_id


@pytest.mark.asyncio
async def test_reactivate_changed_target_uses_target_correction_reason(
    learning_session: AsyncSession,
) -> None:
    workspace_id, _, underlying_id, product_id = await _seed_parents(learning_session)
    trade_a = await _seed_external_trade(
        learning_session,
        workspace_id=workspace_id,
        product_id=product_id,
    )
    trade_b = await _seed_external_trade(
        learning_session,
        workspace_id=workspace_id,
        product_id=product_id,
    )
    observation_id, _ = await _seed_observation(
        learning_session,
        workspace_id=workspace_id,
        underlying_id=underlying_id,
        product_id=product_id,
    )
    link_id, _ = await _create_initial_link(
        learning_session,
        workspace_id=workspace_id,
        observation_id=observation_id,
        trade_id=trade_a,
    )

    await _service(learning_session, uuid4()).retract(
        workspace_id=workspace_id,
        trade_link_id=link_id,
        actor_id=uuid4(),
    )

    result = await _service(learning_session, uuid4()).reactivate(
        workspace_id=workspace_id,
        trade_link_id=link_id,
        actor_id=uuid4(),
        trade_id=trade_b,
    )

    assert result.status is TradeLinkStatus.ACTIVE
    assert result.change_reason is TradeLinkChangeReason.LINK_REACTIVATED_WITH_TARGET_CORRECTION
    assert result.trade_id == trade_b


@pytest.mark.asyncio
async def test_revalidate_source_moves_active_link_to_current_source(
    learning_session: AsyncSession,
) -> None:
    workspace_id, _, underlying_id, product_id = await _seed_parents(learning_session)
    trade_id = await _seed_external_trade(
        learning_session,
        workspace_id=workspace_id,
        product_id=product_id,
    )
    observation_id, old_source_id = await _seed_observation(
        learning_session,
        workspace_id=workspace_id,
        underlying_id=underlying_id,
        product_id=product_id,
    )
    link_id, v1_id = await _create_initial_link(
        learning_session,
        workspace_id=workspace_id,
        observation_id=observation_id,
        trade_id=trade_id,
    )

    current_source_id = uuid4()
    await learning_session.execute(
        text("""
            insert into external_observation_versions (
                id, external_observation_id, version,
                underlying_id, product_id,
                source_type, source_name, external_reference,
                observed_at, recorded_at, imported_at,
                recording_method, import_row_id, source_metadata,
                supersedes_version_id, created_at, created_by
            )
            values (
                :id, :observation_id, 2,
                :underlying_id, :product_id,
                'MANUAL', 'application-pg-v2', null,
                :observed_at, :recorded_at, null,
                'MANUAL', null, null,
                :supersedes, :created_at, :created_by
            )
            """),
        {
            "id": current_source_id,
            "observation_id": observation_id,
            "underlying_id": underlying_id,
            "product_id": product_id,
            "observed_at": NOW,
            "recorded_at": NOW,
            "supersedes": old_source_id,
            "created_at": NOW,
            "created_by": uuid4(),
        },
    )
    await learning_session.execute(
        text("""
            update external_observations
            set current_version_id = :current_source_id
            where id = :observation_id
            """),
        {
            "current_source_id": current_source_id,
            "observation_id": observation_id,
        },
    )
    await learning_session.flush()

    v2_id = uuid4()
    result = await _service(learning_session, v2_id).revalidate_source(
        workspace_id=workspace_id,
        trade_link_id=link_id,
        actor_id=uuid4(),
        change_note="source revalidated",
    )

    assert result.id == v2_id
    assert result.version == 2
    assert result.status is TradeLinkStatus.ACTIVE
    assert result.change_reason is TradeLinkChangeReason.SOURCE_REVALIDATED
    assert result.trade_id == trade_id
    assert result.external_observation_version_id == current_source_id
    assert result.supersedes_version_id == v1_id


@pytest.mark.asyncio
async def test_revalidate_source_rejects_incompatible_current_source(
    learning_session: AsyncSession,
) -> None:
    workspace_id, _, underlying_id, product_id = await _seed_parents(learning_session)
    trade_id = await _seed_external_trade(
        learning_session,
        workspace_id=workspace_id,
        product_id=product_id,
    )
    observation_id, old_source_id = await _seed_observation(
        learning_session,
        workspace_id=workspace_id,
        underlying_id=underlying_id,
        product_id=product_id,
    )
    link_id, _ = await _create_initial_link(
        learning_session,
        workspace_id=workspace_id,
        observation_id=observation_id,
        trade_id=trade_id,
    )

    incompatible_underlying_id = uuid4()
    await learning_session.execute(
        text("""
            insert into underlyings (
                id,
                workspace_id,
                type,
                name,
                isin,
                wkn,
                lifecycle_status,
                quality_status,
                version,
                created_at,
                updated_at,
                data_origin
            )
            values (
                :id,
                :workspace_id,
                'STOCK',
                :name,
                null,
                null,
                'ACTIVE',
                'VERIFIED',
                1,
                :created_at,
                :updated_at,
                'MANUAL'
            )
            """),
        {
            "id": incompatible_underlying_id,
            "workspace_id": workspace_id,
            "name": f"Incompatible Underlying {incompatible_underlying_id}",
            "created_at": NOW,
            "updated_at": NOW,
        },
    )

    current_source_id = uuid4()
    await learning_session.execute(
        text("""
            insert into external_observation_versions (
                id, external_observation_id, version,
                underlying_id, product_id,
                source_type, source_name, external_reference,
                observed_at, recorded_at, imported_at,
                recording_method, import_row_id, source_metadata,
                supersedes_version_id, created_at, created_by
            )
            values (
                :id, :observation_id, 2,
                :underlying_id, :product_id,
                'MANUAL', 'application-pg-v2', null,
                :observed_at, :recorded_at, null,
                'MANUAL', null, null,
                :supersedes, :created_at, :created_by
            )
            """),
        {
            "id": current_source_id,
            "observation_id": observation_id,
            "underlying_id": incompatible_underlying_id,
            "product_id": None,
            "observed_at": NOW,
            "recorded_at": NOW,
            "supersedes": old_source_id,
            "created_at": NOW,
            "created_by": uuid4(),
        },
    )
    await learning_session.execute(
        text("""
            update external_observations
            set current_version_id = :current_source_id
            where id = :observation_id
            """),
        {
            "current_source_id": current_source_id,
            "observation_id": observation_id,
        },
    )
    await learning_session.flush()

    with pytest.raises(TradeLinkServiceError) as exc:
        await _service(learning_session, uuid4()).revalidate_source(
            workspace_id=workspace_id,
            trade_link_id=link_id,
            actor_id=uuid4(),
        )
    assert exc.value.code is TradeLinkErrorCode.TRADE_LINK_SOURCE_INCOMPATIBLE
