from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from test_trade_link_application_postgres import (
    _seed_observation,
    _seed_parents,
)

from app.features.learning.application.execute_as_trade_service import (
    ExecuteExternalObservationAsTradeService,
)
from app.features.learning.application.external_trade_creator import (
    SqlAlchemyExternalTradeCreator,
)
from app.features.learning.application.read_adapters import (
    SqlAlchemyProductReader,
    SqlAlchemyTradeReader,
)
from app.features.learning.application.trade_link_service import (
    ExternalObservationTradeLinkService,
)
from app.features.learning.persistence.unit_of_work import (
    LearningTradeLinkUnitOfWork,
    SqlAlchemyLearningTradeLinkUnitOfWork,
)

NOW = datetime(2026, 8, 23, tzinfo=UTC)


class FixedClock:
    def now(self) -> datetime:
        return NOW


class Ids:
    def new_uuid(self) -> UUID:
        return uuid4()


def _services(session: AsyncSession):
    concrete = SqlAlchemyLearningTradeLinkUnitOfWork(session)
    uow = cast(LearningTradeLinkUnitOfWork, concrete)
    trade_links = ExternalObservationTradeLinkService(
        uow=uow,
        trade_reader=SqlAlchemyTradeReader(session),
        product_reader=SqlAlchemyProductReader(session),
        clock=FixedClock(),
        id_factory=Ids(),
    )
    return ExecuteExternalObservationAsTradeService(
        session=session,
        uow=uow,
        external_trade_creator=SqlAlchemyExternalTradeCreator(session),
        trade_link_service=trade_links,
        clock=FixedClock(),
        id_factory=Ids(),
    )


@pytest.mark.asyncio
async def test_execute_as_trade_creates_trade_link_and_idempotency(
    learning_session: AsyncSession,
) -> None:
    workspace_id, _, underlying_id, product_id = await _seed_parents(learning_session)
    observation_id, _ = await _seed_observation(
        learning_session,
        workspace_id=workspace_id,
        underlying_id=underlying_id,
        product_id=product_id,
    )

    service = _services(learning_session)
    first = await service.execute(
        workspace_id=workspace_id,
        observation_id=observation_id,
        quantity=2,
        price_per_unit=Decimal("11.25"),
        executed_at=NOW,
        actor_id=uuid4(),
        idempotency_key="exec-1",
    )

    trade_count = await learning_session.scalar(
        text("select count(*) from trades where id = :id"),
        {"id": first.trade_id},
    )
    link_count = await learning_session.scalar(
        text(
            """
            select count(*)
            from external_observation_trade_links
            where id = :id
            """
        ),
        {"id": first.trade_link_id},
    )
    idem = (
        await learning_session.execute(
            text(
                """
                select status, result_type, result_id
                from ft012_idempotency_records
                where workspace_id = :workspace_id
                  and command_type = 'EXECUTE_AS_TRADE'
                  and idempotency_key = 'exec-1'
                """
            ),
            {"workspace_id": workspace_id},
        )
    ).one()

    assert first.replayed is False
    assert trade_count == 1
    assert link_count == 1
    assert idem.status == "SUCCEEDED"
    assert idem.result_type == "TRADE"
    assert idem.result_id == first.trade_id

    replay = await service.execute(
        workspace_id=workspace_id,
        observation_id=observation_id,
        quantity=2,
        price_per_unit=Decimal("11.25"),
        executed_at=NOW,
        actor_id=uuid4(),
        idempotency_key="exec-1",
    )

    assert replay.replayed is True
    assert replay.trade_id == first.trade_id
    assert replay.trade_link_id == first.trade_link_id
