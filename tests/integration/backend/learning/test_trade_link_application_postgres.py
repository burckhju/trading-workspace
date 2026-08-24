from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.learning.application.read_adapters import (
    SqlAlchemyProductReader,
    SqlAlchemyTradeReader,
)
from app.features.learning.application.trade_link_service import (
    ExternalObservationTradeLinkService,
)
from app.features.learning.persistence.unit_of_work import (
    SqlAlchemyLearningTradeLinkUnitOfWork,
)
from app.features.trade_position.domain.enums import TradeOrigin

NOW = datetime(2026, 8, 23, tzinfo=UTC)


class FixedClock:
    def now(self) -> datetime:
        return NOW


class QueueIds:
    def __init__(self, *values: UUID) -> None:
        self._values = list(values)

    def new_uuid(self) -> UUID:
        return self._values.pop(0)


async def _seed_parents(
    session: AsyncSession,
) -> tuple[UUID, UUID, UUID, UUID]:
    workspace_id = uuid4()
    issuer_id = uuid4()
    underlying_id = uuid4()
    product_id = uuid4()

    await session.execute(
        text("""
            insert into workspaces (id, name, created_at)
            values (:id, :name, :created_at)
            """),
        {
            "id": workspace_id,
            "name": f"ws-{workspace_id}",
            "created_at": NOW,
        },
    )
    await session.execute(
        text("""
            insert into issuers (
                id, legal_name, display_name, country_code, lei,
                is_active, version, created_at, updated_at
            )
            values (
                :id, :legal_name, :display_name, null, null,
                true, 1, :created_at, :updated_at
            )
            """),
        {
            "id": issuer_id,
            "legal_name": f"Issuer {issuer_id}",
            "display_name": "Test Issuer",
            "created_at": NOW,
            "updated_at": NOW,
        },
    )
    await session.execute(
        text("""
            insert into underlyings (
                id, workspace_id, type, name, isin, wkn,
                lifecycle_status, quality_status, version,
                created_at, updated_at, data_origin
            )
            values (
                :id, :workspace_id, 'STOCK', :name, null, null,
                'ACTIVE', 'VERIFIED', 1,
                :created_at, :updated_at, 'MANUAL'
            )
            """),
        {
            "id": underlying_id,
            "workspace_id": workspace_id,
            "name": f"Underlying {underlying_id}",
            "created_at": NOW,
            "updated_at": NOW,
        },
    )
    await session.execute(
        text("""
            insert into warrants (
                id, workspace_id, issuer_id, underlying_id,
                product_family, display_name, isin, wkn,
                lifecycle_status, version, created_at, updated_at
            )
            values (
                :id, :workspace_id, :issuer_id, :underlying_id,
                'WARRANT', :display_name, null, null,
                'ACTIVE', 1, :created_at, :updated_at
            )
            """),
        {
            "id": product_id,
            "workspace_id": workspace_id,
            "issuer_id": issuer_id,
            "underlying_id": underlying_id,
            "display_name": f"Warrant {product_id}",
            "created_at": NOW,
            "updated_at": NOW,
        },
    )
    return workspace_id, issuer_id, underlying_id, product_id


async def _seed_external_trade(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    product_id: UUID,
) -> UUID:
    trade_id = uuid4()
    await session.execute(
        text("""
            insert into trades (
                id, workspace_id, product_id, origin,
                created_at, created_by,
                trade_plan_id, trade_plan_version_id,
                product_selection_id, product_evaluation_id
            )
            values (
                :id, :workspace_id, :product_id, 'EXTERNAL',
                :created_at, :created_by,
                null, null, null, null
            )
            """),
        {
            "id": trade_id,
            "workspace_id": workspace_id,
            "product_id": product_id,
            "created_at": NOW,
            "created_by": uuid4(),
        },
    )
    return trade_id


async def _seed_observation(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    underlying_id: UUID,
    product_id: UUID | None,
) -> tuple[UUID, UUID]:
    observation_id = uuid4()
    version_id = uuid4()

    await session.execute(
        text("""
            insert into external_observations (
                id, workspace_id, current_version_id,
                created_at, created_by
            )
            values (
                :id, :workspace_id, :version_id,
                :created_at, :created_by
            )
            """),
        {
            "id": observation_id,
            "workspace_id": workspace_id,
            "version_id": version_id,
            "created_at": NOW,
            "created_by": uuid4(),
        },
    )
    await session.execute(
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
                :id, :observation_id, 1,
                :underlying_id, :product_id,
                'MANUAL', 'application-pg', null,
                :observed_at, :recorded_at, null,
                'MANUAL', null, null,
                null, :created_at, :created_by
            )
            """),
        {
            "id": version_id,
            "observation_id": observation_id,
            "underlying_id": underlying_id,
            "product_id": product_id,
            "observed_at": NOW,
            "recorded_at": NOW,
            "created_at": NOW,
            "created_by": uuid4(),
        },
    )
    await session.flush()
    return observation_id, version_id


@pytest.mark.asyncio
async def test_sqlalchemy_trade_and_product_readers(
    learning_session: AsyncSession,
) -> None:
    workspace_id, _, underlying_id, product_id = await _seed_parents(learning_session)
    trade_id = await _seed_external_trade(
        learning_session,
        workspace_id=workspace_id,
        product_id=product_id,
    )
    await learning_session.flush()

    trade = await SqlAlchemyTradeReader(learning_session).get(
        workspace_id=workspace_id,
        trade_id=trade_id,
    )
    product = await SqlAlchemyProductReader(learning_session).get(
        workspace_id=workspace_id,
        product_id=product_id,
    )

    assert trade is not None
    assert trade.origin is TradeOrigin.EXTERNAL
    assert trade.product_id == product_id
    assert product is not None
    assert product.underlying_id == underlying_id


@pytest.mark.asyncio
async def test_create_trade_link_persists_root_and_v1_atomically(
    learning_session: AsyncSession,
) -> None:
    workspace_id, _, underlying_id, product_id = await _seed_parents(learning_session)
    trade_id = await _seed_external_trade(
        learning_session,
        workspace_id=workspace_id,
        product_id=product_id,
    )
    observation_id, observation_version_id = await _seed_observation(
        learning_session,
        workspace_id=workspace_id,
        underlying_id=underlying_id,
        product_id=product_id,
    )

    link_id = uuid4()
    link_version_id = uuid4()
    service = ExternalObservationTradeLinkService(
        uow=SqlAlchemyLearningTradeLinkUnitOfWork(learning_session),
        trade_reader=SqlAlchemyTradeReader(learning_session),
        product_reader=SqlAlchemyProductReader(learning_session),
        clock=FixedClock(),
        id_factory=QueueIds(link_id, link_version_id),
    )

    result = await service.create(
        workspace_id=workspace_id,
        external_observation_id=observation_id,
        trade_id=trade_id,
        actor_id=uuid4(),
    )

    row = (
        await learning_session.execute(
            text("""
                select l.current_version_id,
                       v.external_observation_version_id,
                       v.trade_id,
                       v.status,
                       v.change_reason
                from external_observation_trade_links l
                join external_observation_trade_link_versions v
                  on v.id = l.current_version_id
                where l.id = :link_id
                """),
            {"link_id": link_id},
        )
    ).one()

    assert result.id == link_version_id
    assert row.current_version_id == link_version_id
    assert row.external_observation_version_id == observation_version_id
    assert row.trade_id == trade_id
    assert row.status == "ACTIVE"
    assert row.change_reason == "INITIAL_LINK"
