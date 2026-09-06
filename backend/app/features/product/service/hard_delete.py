"""Guarded hard-delete support for unreferenced warrants."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.product.persistence.models import (
    WarrantListingModel,
    WarrantModel,
    WarrantTermsVersionModel,
)
from app.features.product.service.errors import (
    WarrantConcurrentModification,
    WarrantDeleteBlocked,
    WarrantNotFound,
)


class WarrantHardDeleteService:
    """Physically remove a warrant only while no external history references it."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def delete(self, workspace_id: UUID, warrant_id: UUID, expected_version: int) -> None:
        warrant = await self._session.scalar(
            select(WarrantModel)
            .where(
                WarrantModel.workspace_id == workspace_id,
                WarrantModel.id == warrant_id,
            )
            .with_for_update()
        )
        if warrant is None:
            raise WarrantNotFound("Warrant does not exist")
        if warrant.version != expected_version:
            raise WarrantConcurrentModification(
                f"Expected version {expected_version}, found {warrant.version}",
                field="version",
            )

        try:
            # Terms and listings are owned by the warrant. External immutable records use
            # RESTRICT foreign keys, so any historical use blocks one of these deletes and
            # the complete transaction is rolled back.
            await self._session.execute(
                delete(WarrantListingModel).where(
                    WarrantListingModel.workspace_id == workspace_id,
                    WarrantListingModel.warrant_id == warrant_id,
                )
            )
            await self._session.execute(
                delete(WarrantTermsVersionModel).where(
                    WarrantTermsVersionModel.warrant_id == warrant_id
                )
            )
            await self._session.execute(
                delete(WarrantModel).where(
                    WarrantModel.workspace_id == workspace_id,
                    WarrantModel.id == warrant_id,
                    WarrantModel.version == expected_version,
                )
            )
            await self._session.commit()
        except IntegrityError as error:
            await self._session.rollback()
            raise WarrantDeleteBlocked(
                "Der Optionsschein wird bereits historisch oder operativ verwendet "
                "und kann nicht gelöscht werden."
            ) from error
        except Exception:
            await self._session.rollback()
            raise
