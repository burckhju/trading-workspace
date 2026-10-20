"""Explicit journal commands; no automatic Evidence, Lesson or model changes."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, replace
from datetime import datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.features.learning.application.ft011_materialization_service import Ft011HandoffReader
from app.features.learning.application.ports import Clock, IdFactory, TradeReader
from app.features.learning.domain import (
    IdempotencyRecord,
    IdempotencyStatus,
    JournalVersionStatus,
    TradeJournal,
    TradeJournalVersion,
)
from app.features.learning.persistence.unit_of_work import LearningTradeLinkUnitOfWork
from app.features.post_trade.application.handoff_service import Ft012Handoff
from app.features.post_trade.domain import ExitReviewCurrentness


class JournalError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class JournalOperation(StrEnum):
    CREATE_DRAFT = "CREATE_DRAFT"
    SAVE_DRAFT = "SAVE_DRAFT"
    REBIND_SOURCE = "REBIND_SOURCE"
    FINALIZE = "FINALIZE"
    MATERIALIZE = "MATERIALIZE"


class ReviewInspector(Protocol):
    async def inspect_version_currentness(
        self, *, workspace_id: UUID, version_id: UUID
    ) -> ExitReviewCurrentness | None: ...


@dataclass(frozen=True)
class JournalCommand:
    operation: JournalOperation
    version_id: UUID | None = None
    expected_latest_version_id: UUID | None = None
    expected_edit_revision: int | None = None
    expected_exit_review_version_id: UUID | None = None
    what_went_well: str | None = None
    would_do_differently: str | None = None
    additional_notes: str | None = None


@dataclass(frozen=True)
class JournalReceipt:
    result_id: UUID
    result_type: str
    replayed: bool


@dataclass(frozen=True)
class JournalVersionView:
    version: TradeJournalVersion
    is_latest: bool
    source_currentness: str
    source_checked_at: datetime
    learning_evidence_id: UUID | None


@dataclass(frozen=True)
class JournalHistory:
    trade_id: UUID
    journal_id: UUID | None
    handoff: Ft012Handoff
    versions: tuple[JournalVersionView, ...]


class JournalService:
    def __init__(
        self,
        *,
        uow: LearningTradeLinkUnitOfWork,
        trade_reader: TradeReader,
        handoff_reader: Ft011HandoffReader,
        inspector: ReviewInspector,
        clock: Clock,
        id_factory: IdFactory,
    ) -> None:
        self._uow = uow
        self._trade_reader = trade_reader
        self._handoff = handoff_reader
        self._inspector = inspector
        self._clock = clock
        self._ids = id_factory

    async def history(self, *, workspace_id: UUID, trade_id: UUID) -> JournalHistory:
        journal = await self._uow.journals.get(workspace_id, trade_id)
        versions = await self._uow.journals.versions(journal.id) if journal else ()
        handoff = await self._handoff.get(workspace_id=workspace_id, trade_id=trade_id)
        if handoff.ready:
            state = await self._source_state(workspace_id, handoff.exit_review_version_id)
            if state != "CURRENT":
                handoff = replace(handoff, ready=False, reason=f"EXIT_REVIEW_{state}")
        items = []
        for index, version in enumerate(versions):
            currentness = await self._source_state(
                workspace_id, version.source_exit_review_version_id
            )
            items.append(
                JournalVersionView(
                    version,
                    index == 0,
                    currentness,
                    self._clock.now(),
                    await self._uow.journals.evidence_id(version.id),
                )
            )
        return JournalHistory(trade_id, journal.id if journal else None, handoff, tuple(items))

    async def version(self, *, workspace_id: UUID, version_id: UUID) -> JournalHistory:
        journal = await self._uow.journals.origin(workspace_id, version_id)
        if journal is None:
            raise JournalError("JOURNAL_NOT_FOUND", "Journal version not found")
        history = await self.history(workspace_id=workspace_id, trade_id=journal.trade_id)
        return replace(
            history,
            versions=tuple(item for item in history.versions if item.version.id == version_id),
        )

    async def execute(
        self,
        *,
        workspace_id: UUID,
        trade_id: UUID,
        actor_id: UUID,
        idempotency_key: str,
        command: JournalCommand,
    ) -> JournalReceipt:
        if not idempotency_key.strip() or len(idempotency_key) > 240:
            raise JournalError("JOURNAL_INVALID_REQUEST", "Idempotency-Key is required (max 240)")
        payload = {
            "workspace": str(workspace_id),
            "trade": str(trade_id),
            "actor": str(actor_id),
            **asdict(command),
        }
        fingerprint = hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode()
        ).hexdigest()
        command_type = f"JOURNAL_{command.operation.value}"
        async with self._uow:
            # The existing trade repository locks the aggregate. Execution corrections
            # and simultaneous journal commands cannot overwrite the same saved draft.
            trade = await self._trade_reader.get(workspace_id=workspace_id, trade_id=trade_id)
            if trade is None:
                raise JournalError("JOURNAL_NOT_FOUND", "Trade missing or cancelled")
            existing = await self._uow.idempotency_records.get(
                workspace_id, command_type, idempotency_key
            )
            if existing:
                if existing.request_fingerprint != fingerprint:
                    raise JournalError("IDEMPOTENCY_KEY_REUSED", "Key belongs to another request")
                if existing.status is not IdempotencyStatus.SUCCEEDED:
                    raise JournalError("JOURNAL_CONFLICT", "Command has not succeeded")
                if existing.result_id is None or existing.result_type is None:
                    raise RuntimeError("Journal receipt is incomplete")
                return JournalReceipt(existing.result_id, existing.result_type, True)
            try:
                result_id, result_type = await self._apply(
                    workspace_id, trade_id, actor_id, command
                )
                record = IdempotencyRecord(
                    id=self._ids.new_uuid(),
                    workspace_id=workspace_id,
                    command_type=command_type,
                    idempotency_key=idempotency_key,
                    request_fingerprint=fingerprint,
                    status=IdempotencyStatus.IN_PROGRESS,
                    created_at=self._clock.now(),
                )
                await self._uow.idempotency_records.add(record)
                await self._uow.flush()
                await self._uow.idempotency_records.mark_succeeded(
                    record_id=record.id,
                    result_type=result_type,
                    result_id=result_id,
                    completed_at=self._clock.now(),
                )
                await self._uow.commit()
            except IntegrityError as exc:
                await self._uow.rollback()
                raise JournalError(
                    "JOURNAL_CONFLICT", "Concurrent or invalid journal change"
                ) from exc
        return JournalReceipt(result_id, result_type, False)

    async def _source_state(self, workspace_id: UUID, version_id: UUID | None) -> str:
        if version_id is None:
            return "UNKNOWN"
        state = await self._inspector.inspect_version_currentness(
            workspace_id=workspace_id, version_id=version_id
        )
        return state.value if state else "UNKNOWN"

    async def _require_source(
        self, workspace_id: UUID, trade_id: UUID, expected_id: UUID | None
    ) -> UUID:
        handoff = await self._handoff.get(workspace_id=workspace_id, trade_id=trade_id)
        if not handoff.ready:
            raise JournalError("JOURNAL_SOURCE_NOT_READY", handoff.reason)
        if expected_id is None or expected_id != handoff.exit_review_version_id:
            raise JournalError("SOURCE_VERSION_MISMATCH", "Reload and confirm the exact review")
        if await self._source_state(workspace_id, expected_id) != "CURRENT":
            raise JournalError("JOURNAL_SOURCE_NOT_READY", "Review inputs changed or are unknown")
        return expected_id

    async def _apply(
        self, workspace_id: UUID, trade_id: UUID, actor_id: UUID, command: JournalCommand
    ) -> tuple[UUID, str]:
        repo = self._uow.journals
        journal = await repo.get(workspace_id, trade_id)
        versions = await repo.versions(journal.id) if journal else ()
        latest = versions[0] if versions else None
        now = self._clock.now()
        if command.operation is JournalOperation.CREATE_DRAFT:
            if (latest.id if latest else None) != command.expected_latest_version_id or (
                latest and latest.status is JournalVersionStatus.DRAFT
            ):
                raise JournalError("JOURNAL_CONFLICT", "Latest journal changed or draft exists")
            source_id = await self._require_source(
                workspace_id, trade_id, command.expected_exit_review_version_id
            )
            if journal is None:
                journal = TradeJournal(self._ids.new_uuid(), workspace_id, trade_id, now, actor_id)
                await repo.add(journal)
                await self._uow.flush()
            draft = TradeJournalVersion(
                id=self._ids.new_uuid(),
                trade_journal_id=journal.id,
                version=latest.version + 1 if latest else 1,
                status=JournalVersionStatus.DRAFT,
                what_went_well=latest.what_went_well if latest else None,
                would_do_differently=latest.would_do_differently if latest else None,
                additional_notes=latest.additional_notes if latest else None,
                created_at=now,
                created_by=actor_id,
                updated_at=now,
                updated_by=actor_id,
                supersedes_version_id=latest.id if latest else None,
                source_exit_review_version_id=source_id,
            )
            await repo.add_version(draft)
            return draft.id, "TRADE_JOURNAL_VERSION"
        version = next((v for v in versions if v.id == command.version_id), None)
        if version is None:
            raise JournalError("JOURNAL_NOT_FOUND", "Journal version not found for this trade")
        if command.operation is JournalOperation.MATERIALIZE:
            if version.status is not JournalVersionStatus.FINALIZED:
                raise JournalError("JOURNAL_CONFLICT", "Only finalized journals are evidence")
            evidence_id = await repo.evidence_id(version.id)
            if evidence_id is None:
                evidence_id = self._ids.new_uuid()
                await repo.add_evidence(workspace_id, version.id, evidence_id, now)
            return evidence_id, "LEARNING_EVIDENCE"
        if (
            version.status is not JournalVersionStatus.DRAFT
            or version.edit_revision != command.expected_edit_revision
        ):
            raise JournalError("JOURNAL_CONFLICT", "Saved draft changed; reload before editing")
        if command.operation is JournalOperation.SAVE_DRAFT:
            updated = version.replace_draft_content(
                what_went_well=command.what_went_well,
                would_do_differently=command.would_do_differently,
                additional_notes=command.additional_notes,
                updated_at=now,
                updated_by=actor_id,
            )
        else:
            source_id = await self._require_source(
                workspace_id, trade_id, command.expected_exit_review_version_id
            )
            if command.operation is JournalOperation.FINALIZE:
                if source_id != version.source_exit_review_version_id:
                    raise JournalError(
                        "SOURCE_VERSION_MISMATCH", "Rebind the draft source explicitly"
                    )
                updated = version.finalize(finalized_at=now, finalized_by=actor_id)
            elif command.operation is JournalOperation.REBIND_SOURCE:
                updated = replace(
                    version,
                    source_exit_review_version_id=source_id,
                    edit_revision=version.edit_revision + 1,
                    updated_at=now,
                    updated_by=actor_id,
                )
            else:
                raise JournalError("JOURNAL_INVALID_REQUEST", "Unknown operation")
        if not await repo.replace_draft(updated, version.edit_revision):
            raise JournalError("JOURNAL_CONFLICT", "Concurrent draft change")
        return version.id, "TRADE_JOURNAL_VERSION"
