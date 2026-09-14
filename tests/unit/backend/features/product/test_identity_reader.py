"""Public product-name reads are scoped, batched and preserve missing identity."""

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.product.service.application import WarrantService


async def test_identity_reader_empty_batch_does_not_query():
    session = AsyncMock(spec=AsyncSession)
    assert (
        await WarrantService(session).read_identities(workspace_id=uuid4(), warrant_ids=set()) == {}
    )
    session.execute.assert_not_awaited()


async def test_identity_reader_is_scoped_and_uses_one_query_without_lifecycle_filter():
    session = AsyncMock(spec=AsyncSession)
    workspace_id, a, b = uuid4(), uuid4(), uuid4()
    session.execute.return_value = SimpleNamespace(
        all=lambda: [SimpleNamespace(id=a, display_name="SYNTHETIC <A&B>", isin=None, wkn="SYN001")]
    )
    result = await WarrantService(session).read_identities(
        workspace_id=workspace_id, warrant_ids=[a, b, a]
    )
    assert list(result) == [a]  # Unknown / foreign identity is not invented.
    assert result[a].display_name == "SYNTHETIC <A&B>"
    assert result[a].isin is None and result[a].wkn == "SYN001"
    session.execute.assert_awaited_once()
    statement = session.execute.await_args.args[0]
    sql = str(statement)
    assert "warrants.workspace_id =" in sql and "warrants.id IN" in sql
    assert "lifecycle_status" not in sql  # Closed trades may reference expired / inactive products.
    assert workspace_id in statement.compile().params.values()
    session.commit.assert_not_awaited()
    session.flush.assert_not_awaited()
