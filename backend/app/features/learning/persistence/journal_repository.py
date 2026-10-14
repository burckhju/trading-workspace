"""FT-012 journal persistence on the existing journal/evidence tables."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict
from datetime import datetime
from typing import Protocol, cast
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.learning.domain import JournalVersionStatus, TradeJournal, TradeJournalVersion
from app.features.learning.persistence.mapping import (
    trade_journal_to_model,
    trade_journal_version_to_model,
)
from app.features.learning.persistence.models import (
    LearningEvidenceModel,
    TradeJournalModel,
    TradeJournalVersionEvidenceModel,
    TradeJournalVersionModel,
)


class JournalRepository(Protocol):
    async def get(self, workspace_id: UUID, trade_id: UUID) -> TradeJournal | None: ...
    async def versions(self, journal_id: UUID) -> Sequence[TradeJournalVersion]: ...
    async def add(self, journal: TradeJournal) -> None: ...
    async def add_version(self, version: TradeJournalVersion) -> None: ...
    async def replace_draft(self, version: TradeJournalVersion, expected_revision: int) -> bool: ...
    async def evidence_id(self, version_id: UUID) -> UUID | None: ...
    async def add_evidence(
        self, workspace_id: UUID, version_id: UUID, evidence_id: UUID, created_at: datetime
    ) -> None: ...
    async def origin(self, workspace_id: UUID, version_id: UUID) -> TradeJournal | None: ...


def _journal(model: TradeJournalModel) -> TradeJournal:
    return TradeJournal(
        model.id, model.workspace_id, model.trade_id, model.created_at, model.created_by
    )


def _version(model: TradeJournalVersionModel) -> TradeJournalVersion:
    return TradeJournalVersion(
        id=model.id,
        trade_journal_id=model.trade_journal_id,
        version=model.version,
        status=JournalVersionStatus(model.status),
        what_went_well=model.what_went_well,
        would_do_differently=model.would_do_differently,
        additional_notes=model.additional_notes,
        created_at=model.created_at,
        created_by=model.created_by,
        updated_at=model.updated_at,
        updated_by=model.updated_by,
        finalized_at=model.finalized_at,
        finalized_by=model.finalized_by,
        supersedes_version_id=model.supersedes_version_id,
        edit_revision=model.edit_revision,
        source_exit_review_version_id=model.source_exit_review_version_id,
    )


class SqlAlchemyJournalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, workspace_id: UUID, trade_id: UUID) -> TradeJournal | None:
        model = await self._session.scalar(
            select(TradeJournalModel)
            .where(
                TradeJournalModel.workspace_id == workspace_id,
                TradeJournalModel.trade_id == trade_id,
            )
            .execution_options(populate_existing=True)
        )
        return _journal(model) if model else None

    async def origin(self, workspace_id: UUID, version_id: UUID) -> TradeJournal | None:
        model = await self._session.scalar(
            select(TradeJournalModel)
            .join(
                TradeJournalVersionModel,
                TradeJournalVersionModel.trade_journal_id == TradeJournalModel.id,
            )
            .where(
                TradeJournalModel.workspace_id == workspace_id,
                TradeJournalVersionModel.id == version_id,
            )
        )
        return _journal(model) if model else None

    async def versions(self, journal_id: UUID) -> Sequence[TradeJournalVersion]:
        models = (
            await self._session.scalars(
                select(TradeJournalVersionModel)
                .where(TradeJournalVersionModel.trade_journal_id == journal_id)
                .order_by(TradeJournalVersionModel.version.desc())
                .execution_options(populate_existing=True)
            )
        ).all()
        return tuple(_version(model) for model in models)

    async def add(self, journal: TradeJournal) -> None:
        self._session.add(trade_journal_to_model(journal))

    async def add_version(self, version: TradeJournalVersion) -> None:
        self._session.add(trade_journal_version_to_model(version))

    async def replace_draft(self, version: TradeJournalVersion, expected_revision: int) -> bool:
        values = asdict(version)
        values.pop("id")
        values["status"] = version.status.value
        result = await self._session.scalar(
            update(TradeJournalVersionModel)
            .where(
                TradeJournalVersionModel.id == version.id,
                TradeJournalVersionModel.status == "DRAFT",
                TradeJournalVersionModel.edit_revision == expected_revision,
            )
            .values(**values)
            .returning(TradeJournalVersionModel.id)
        )
        return result is not None

    async def evidence_id(self, version_id: UUID) -> UUID | None:
        return cast(
            UUID | None,
            await self._session.scalar(
                select(TradeJournalVersionEvidenceModel.learning_evidence_id).where(
                    TradeJournalVersionEvidenceModel.trade_journal_version_id == version_id
                )
            ),
        )

    async def add_evidence(
        self, workspace_id: UUID, version_id: UUID, evidence_id: UUID, created_at: datetime
    ) -> None:
        self._session.add(
            LearningEvidenceModel(
                id=evidence_id,
                workspace_id=workspace_id,
                evidence_type="TRADE_JOURNAL_VERSION",
                created_at=created_at,
            )
        )
        await self._session.flush()
        self._session.add(
            TradeJournalVersionEvidenceModel(
                learning_evidence_id=evidence_id,
                trade_journal_version_id=version_id,
            )
        )
