import asyncio
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from sqlalchemy.dialects import postgresql

from app.features.market.persistence.enums import AggregateType, LifecycleStatus
from app.features.market.persistence.repositories import (
    SqlAlchemyAuditEventRepository,
    SqlAlchemyListingRepository,
    SqlAlchemyUnderlyingRepository,
)


def _sql(statement: object) -> str:
    return str(
        statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})
    )


def test_underlying_search_is_workspace_scoped_and_supports_all_search_fields() -> None:
    workspace_id = uuid4()
    statement = SqlAlchemyUnderlyingRepository._search_statement(
        workspace_id, "SIE", LifecycleStatus.ACTIVE
    )
    sql = _sql(statement)
    assert "underlyings.workspace_id" in sql
    assert "underlyings.lifecycle_status" in sql
    assert "underlyings.name ILIKE '%%SIE%%'" in sql
    assert "underlyings.isin ILIKE '%%SIE%%'" in sql
    assert "underlyings.wkn ILIKE '%%SIE%%'" in sql
    assert "EXISTS" in sql and "listings.ticker" in sql


def test_underlying_repository_does_not_commit() -> None:
    session = Mock()
    session.add = Mock()
    session.flush = AsyncMock()
    model = Mock()
    repository = SqlAlchemyUnderlyingRepository(session)
    asyncio.run(repository.add(model))
    asyncio.run(repository.flush())
    session.add.assert_called_once_with(model)
    session.flush.assert_awaited_once()
    assert not hasattr(repository, "commit")


def test_listing_lookup_is_workspace_scoped() -> None:
    session = Mock()
    session.scalar = AsyncMock(return_value=None)
    repository = SqlAlchemyListingRepository(session)
    asyncio.run(repository.find_by_venue_ticker(uuid4(), uuid4(), "SIE"))
    sql = _sql(session.scalar.await_args.args[0])
    assert "listings.workspace_id" in sql
    assert "listings.trading_venue_id" in sql
    assert "listings.ticker = 'SIE'" in sql


def test_audit_repository_is_append_only_and_scoped() -> None:
    session = Mock()
    scalar_result = Mock()
    scalar_result.all.return_value = []
    session.scalars = AsyncMock(return_value=scalar_result)
    session.add = Mock()
    repository = SqlAlchemyAuditEventRepository(session)
    event = Mock()
    asyncio.run(repository.append(event))
    asyncio.run(
        repository.list_for_aggregate(
            uuid4(), AggregateType.UNDERLYING, uuid4(), offset=0, limit=20
        )
    )
    session.add.assert_called_once_with(event)
    sql = _sql(session.scalars.await_args.args[0])
    assert "audit_events.workspace_id" in sql
    assert "audit_events.aggregate_type" in sql
    assert "audit_events.aggregate_id" in sql
    assert "ORDER BY audit_events.occurred_at DESC" in sql
    assert not hasattr(repository, "delete")
    assert not hasattr(repository, "update")
