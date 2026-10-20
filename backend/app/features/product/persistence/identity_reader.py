"""Workspace-scoped batch access to current warrant labels, including historical products."""

from collections.abc import Collection
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.product.persistence.models import WarrantModel
from app.features.product.service.identities import WarrantIdentity


async def read_identities(
    session: AsyncSession, *, workspace_id: UUID, warrant_ids: Collection[UUID]
) -> dict[UUID, WarrantIdentity]:
    if not warrant_ids:
        return {}
    rows = (
        await session.execute(
            select(
                WarrantModel.id, WarrantModel.display_name, WarrantModel.isin, WarrantModel.wkn
            ).where(
                WarrantModel.workspace_id == workspace_id, WarrantModel.id.in_(set(warrant_ids))
            )
        )
    ).all()
    return {row.id: WarrantIdentity(row.id, row.display_name, row.isin, row.wkn) for row in rows}
