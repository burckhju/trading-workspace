from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

import app.features.market.persistence.models
import app.features.product.persistence.models
import app.features.product_selection.persistence.models
import app.features.trade_plan.persistence.models
import app.features.trade_position.persistence.models  # noqa: F401
from app.features.learning.domain import (
    ExternalObservationTradeLinkVersion,
    TradeLinkChangeReason,
    TradeLinkStatus,
)
from app.features.learning.persistence.repositories import (
    PersistenceStateConflictError,
    SqlAlchemyExternalObservationTradeLinkRepository,
    SqlAlchemyExternalObservationTradeLinkVersionRepository,
)


def _now() -> datetime:
    return datetime.now(UTC)


async def _seed_trade_link_graph(
    session: AsyncSession,
) -> tuple[UUID, UUID, UUID, UUID]:
    workspace_id = uuid4()
    observation_id = uuid4()
    observation_version_id = uuid4()
    trade_id = uuid4()
    link_id = uuid4()
    link_version_id = uuid4()
    now = _now()

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
            "created_at": now,
        },
    )

    await session.execute(
        text("""
            insert into issuers (
                id,
                legal_name,
                display_name,
                country_code,
                lei,
                is_active,
                version,
                created_at,
                updated_at
            )
            values (
                :id,
                :legal_name,
                :display_name,
                null,
                null,
                true,
                1,
                :created_at,
                :updated_at
            )
            """),
        {
            "id": issuer_id,
            "legal_name": f"Issuer {issuer_id}",
            "display_name": "Test Issuer",
            "created_at": now,
            "updated_at": now,
        },
    )

    await session.execute(
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
            "id": underlying_id,
            "workspace_id": workspace_id,
            "name": f"Underlying {underlying_id}",
            "created_at": now,
            "updated_at": now,
        },
    )

    await session.execute(
        text("""
            insert into warrants (
                id,
                workspace_id,
                issuer_id,
                underlying_id,
                product_family,
                display_name,
                isin,
                wkn,
                lifecycle_status,
                version,
                created_at,
                updated_at
            )
            values (
                :id,
                :workspace_id,
                :issuer_id,
                :underlying_id,
                'WARRANT',
                :display_name,
                null,
                null,
                'ACTIVE',
                1,
                :created_at,
                :updated_at
            )
            """),
        {
            "id": product_id,
            "workspace_id": workspace_id,
            "issuer_id": issuer_id,
            "underlying_id": underlying_id,
            "display_name": f"Warrant {product_id}",
            "created_at": now,
            "updated_at": now,
        },
    )

    await session.execute(
        text("""
            insert into trades (
                id,
                workspace_id,
                product_id,
                origin,
                created_at,
                created_by,
                trade_plan_id,
                trade_plan_version_id,
                product_selection_id,
                product_evaluation_id
            )
            values (
                :id,
                :workspace_id,
                :product_id,
                'EXTERNAL',
                :created_at,
                :created_by,
                null,
                null,
                null,
                null
            )
            """),
        {
            "id": trade_id,
            "workspace_id": workspace_id,
            "product_id": product_id,
            "created_at": now,
            "created_by": uuid4(),
        },
    )

    await session.execute(
        text("""
            insert into external_observations (
                id, workspace_id, current_version_id,
                created_at, created_by
            )
            values (
                :id, :workspace_id, :current_version_id,
                :created_at, :created_by
            )
            """),
        {
            "id": observation_id,
            "workspace_id": workspace_id,
            "current_version_id": observation_version_id,
            "created_at": now,
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
                'MANUAL', 'repo-test', null,
                :observed_at, :recorded_at, null,
                'MANUAL', null, null,
                null, :created_at, :created_by
            )
            """),
        {
            "id": observation_version_id,
            "observation_id": observation_id,
            "underlying_id": underlying_id,
            "product_id": product_id,
            "observed_at": now,
            "recorded_at": now,
            "created_at": now,
            "created_by": uuid4(),
        },
    )

    await session.execute(
        text("""
            insert into external_observation_trade_links (
                id, workspace_id, external_observation_id,
                current_version_id, created_at, created_by
            )
            values (
                :id, :workspace_id, :observation_id,
                :current_version_id, :created_at, :created_by
            )
            """),
        {
            "id": link_id,
            "workspace_id": workspace_id,
            "observation_id": observation_id,
            "current_version_id": link_version_id,
            "created_at": now,
            "created_by": uuid4(),
        },
    )

    await session.execute(
        text("""
            insert into external_observation_trade_link_versions (
                id, external_observation_trade_link_id, version,
                external_observation_version_id, trade_id,
                status, supersedes_version_id, change_reason,
                change_note, created_at, created_by
            )
            values (
                :id, :link_id, 1,
                :observation_version_id, :trade_id,
                'ACTIVE', null, 'INITIAL_LINK',
                null, :created_at, :created_by
            )
            """),
        {
            "id": link_version_id,
            "link_id": link_id,
            "observation_version_id": observation_version_id,
            "trade_id": trade_id,
            "created_at": now,
            "created_by": uuid4(),
        },
    )

    await session.flush()
    return workspace_id, observation_id, trade_id, link_id


async def test_get_current_and_latest_diverge_after_pointer_stays_old(
    learning_session: AsyncSession,
) -> None:
    workspace_id, _, trade_id, link_id = await _seed_trade_link_graph(learning_session)
    links = SqlAlchemyExternalObservationTradeLinkRepository(learning_session)
    versions = SqlAlchemyExternalObservationTradeLinkVersionRepository(
        learning_session,
        links,
    )

    current = await versions.get_current(link_id)
    assert current is not None

    newer = ExternalObservationTradeLinkVersion(
        id=uuid4(),
        external_observation_trade_link_id=link_id,
        version=2,
        external_observation_version_id=current.external_observation_version_id,
        trade_id=trade_id,
        status=TradeLinkStatus.ACTIVE,
        supersedes_version_id=current.id,
        change_reason=TradeLinkChangeReason.SOURCE_REVALIDATED,
        change_note=None,
        created_at=_now(),
        created_by=uuid4(),
    )
    await versions.add(newer)
    await learning_session.flush()

    assert (await versions.get_current(link_id)).id == current.id
    assert (await versions.get_latest(link_id)).id == newer.id
    assert await versions.next_version_number(workspace_id, link_id) == 3


async def test_advance_current_rejects_stale_expected_pointer(
    learning_session: AsyncSession,
) -> None:
    workspace_id, _, trade_id, link_id = await _seed_trade_link_graph(learning_session)
    links = SqlAlchemyExternalObservationTradeLinkRepository(learning_session)
    versions = SqlAlchemyExternalObservationTradeLinkVersionRepository(
        learning_session,
        links,
    )
    current = await versions.get_current(link_id)
    assert current is not None

    newer = ExternalObservationTradeLinkVersion(
        id=uuid4(),
        external_observation_trade_link_id=link_id,
        version=2,
        external_observation_version_id=current.external_observation_version_id,
        trade_id=trade_id,
        status=TradeLinkStatus.ACTIVE,
        supersedes_version_id=current.id,
        change_reason=TradeLinkChangeReason.SOURCE_REVALIDATED,
        change_note=None,
        created_at=_now(),
        created_by=uuid4(),
    )
    await versions.add(newer)
    await learning_session.flush()

    await links.advance_current(
        link_id=link_id,
        expected_current_version_id=current.id,
        new_current_version_id=newer.id,
    )

    with pytest.raises(PersistenceStateConflictError):
        await links.advance_current(
            link_id=link_id,
            expected_current_version_id=current.id,
            new_current_version_id=uuid4(),
        )

    loaded = await links.get(workspace_id, link_id)
    assert loaded is not None
    assert loaded.current_version_id == newer.id


async def test_exists_current_active_pair_uses_current_pointer_only(
    learning_session: AsyncSession,
) -> None:
    _, observation_id, trade_id, link_id = await _seed_trade_link_graph(learning_session)
    links = SqlAlchemyExternalObservationTradeLinkRepository(learning_session)

    assert await links.exists_current_active_pair(
        external_observation_id=observation_id,
        trade_id=trade_id,
    )
    assert not await links.exists_current_active_pair(
        external_observation_id=observation_id,
        trade_id=trade_id,
        exclude_link_id=link_id,
    )
