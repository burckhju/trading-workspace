"""Controlled FT-011 -> FT-012 LearningEvidence materialization command."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.features.learning.domain import (
    FT011Evidence,
    IdempotencyRecord,
    IdempotencyStatus,
    LearningEvidence,
    LearningEvidenceType,
)
from app.features.learning.persistence.ft011_materialization_repository import (
    Ft011MaterializationRepository,
)
from app.features.learning.persistence.repositories import LearningEvidenceProjection
from app.features.learning.persistence.unit_of_work import LearningTradeLinkUnitOfWork
from app.features.post_trade.application.handoff_service import Ft012Handoff

COMMAND_TYPE = "MATERIALIZE_FT011_LEARNING_EVIDENCE"
RESULT_TYPE = "LEARNING_EVIDENCE"


class Ft011MaterializationErrorCode(StrEnum):
    SOURCE_NOT_READY = "SOURCE_NOT_READY"
    IDEMPOTENCY_KEY_REUSED = "IDEMPOTENCY_KEY_REUSED"
    IDEMPOTENCY_IN_PROGRESS = "IDEMPOTENCY_IN_PROGRESS"
    IDEMPOTENCY_FAILED_FINAL = "IDEMPOTENCY_FAILED_FINAL"
    MATERIALIZATION_CONFLICT = "MATERIALIZATION_CONFLICT"


class Ft011MaterializationError(Exception):
    def __init__(
        self,
        code: Ft011MaterializationErrorCode,
        message: str,
        *,
        source_reason: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.source_reason = source_reason


class Ft011HandoffReader(Protocol):
    async def get(
        self,
        *,
        workspace_id: UUID,
        trade_id: UUID,
    ) -> Ft012Handoff: ...


class Clock(Protocol):
    def now(self) -> datetime: ...


class IdFactory(Protocol):
    def new_uuid(self) -> UUID: ...


@dataclass(frozen=True, slots=True)
class MaterializeFt011LearningEvidenceResult:
    learning_evidence_id: UUID
    exit_review_version_id: UUID
    created: bool
    replayed: bool


def request_fingerprint(*, workspace_id: UUID, trade_id: UUID) -> str:
    payload = {
        "workspace_id": str(workspace_id),
        "trade_id": str(trade_id),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class MaterializeFt011LearningEvidenceService:
    """Materialize one qualified FT-011 handoff into FT-012-owned immutable evidence."""

    def __init__(
        self,
        *,
        uow: LearningTradeLinkUnitOfWork,
        repository: Ft011MaterializationRepository,
        handoff_reader: Ft011HandoffReader,
        clock: Clock,
        id_factory: IdFactory,
    ) -> None:
        self._uow = uow
        self._repository = repository
        self._handoff_reader = handoff_reader
        self._clock = clock
        self._id_factory = id_factory

    async def execute(
        self,
        *,
        workspace_id: UUID,
        trade_id: UUID,
        idempotency_key: str,
    ) -> MaterializeFt011LearningEvidenceResult:
        fingerprint = request_fingerprint(workspace_id=workspace_id, trade_id=trade_id)

        async with self._uow:
            existing_request = await self._uow.idempotency_records.get(
                workspace_id,
                COMMAND_TYPE,
                idempotency_key,
            )
            if existing_request is not None:
                return await self._resolve_existing_request(
                    workspace_id=workspace_id,
                    fingerprint=fingerprint,
                    record=existing_request,
                )

            handoff = await self._handoff_reader.get(
                workspace_id=workspace_id,
                trade_id=trade_id,
            )
            if not handoff.ready:
                raise Ft011MaterializationError(
                    Ft011MaterializationErrorCode.SOURCE_NOT_READY,
                    f"FT-011 source is not ready for FT-012: {handoff.reason}",
                    source_reason=handoff.reason,
                )
            if (
                handoff.post_trade_observation_id is None
                or handoff.exit_review_id is None
                or handoff.exit_review_version_id is None
            ):
                raise RuntimeError("READY FT-011 handoff requires complete provenance")

            existing_source = await self._repository.get_by_source(
                workspace_id=workspace_id,
                exit_review_version_id=handoff.exit_review_version_id,
            )

            record = IdempotencyRecord(
                id=self._id_factory.new_uuid(),
                workspace_id=workspace_id,
                command_type=COMMAND_TYPE,
                idempotency_key=idempotency_key,
                request_fingerprint=fingerprint,
                status=IdempotencyStatus.IN_PROGRESS,
                created_at=self._clock.now(),
            )

            try:
                await self._uow.idempotency_records.add(record)
                await self._uow.flush()

                if existing_source is not None:
                    await self._mark_succeeded(record.id, existing_source.evidence.id)
                    return self._result(existing_source, created=False, replayed=False)

                created_at = self._clock.now()
                evidence = LearningEvidence(
                    id=self._id_factory.new_uuid(),
                    workspace_id=workspace_id,
                    evidence_type=LearningEvidenceType.FT011,
                    created_at=created_at,
                )
                await self._repository.add_evidence(evidence)
                # Parent must exist before the provenance child is flushed on PostgreSQL.
                await self._uow.flush()

                source = FT011Evidence(
                    learning_evidence_id=evidence.id,
                    trade_id=trade_id,
                    post_trade_observation_id=handoff.post_trade_observation_id,
                    exit_review_id=handoff.exit_review_id,
                    exit_review_version_id=handoff.exit_review_version_id,
                )
                await self._repository.add_source(source)
                # Force the semantic uniqueness constraint before recording SUCCESS.
                await self._uow.flush()

                await self._mark_succeeded(record.id, evidence.id)
                return MaterializeFt011LearningEvidenceResult(
                    learning_evidence_id=evidence.id,
                    exit_review_version_id=source.exit_review_version_id,
                    created=True,
                    replayed=False,
                )
            except IntegrityError as exc:
                await self._uow.rollback()
                raise Ft011MaterializationError(
                    Ft011MaterializationErrorCode.MATERIALIZATION_CONFLICT,
                    "concurrent or conflicting FT-011 materialization",
                ) from exc

    async def _resolve_existing_request(
        self,
        *,
        workspace_id: UUID,
        fingerprint: str,
        record: IdempotencyRecord,
    ) -> MaterializeFt011LearningEvidenceResult:
        if record.request_fingerprint != fingerprint:
            raise Ft011MaterializationError(
                Ft011MaterializationErrorCode.IDEMPOTENCY_KEY_REUSED,
                "idempotency key was already used for another request",
            )
        if record.status is IdempotencyStatus.IN_PROGRESS:
            raise Ft011MaterializationError(
                Ft011MaterializationErrorCode.IDEMPOTENCY_IN_PROGRESS,
                "idempotent command is already in progress",
            )
        if record.status is IdempotencyStatus.FAILED_FINAL:
            raise Ft011MaterializationError(
                Ft011MaterializationErrorCode.IDEMPOTENCY_FAILED_FINAL,
                record.error_code or "idempotent command failed finally",
            )
        if record.result_id is None:
            raise RuntimeError("succeeded idempotency record has no result")

        projection = await self._repository.get_by_evidence_id(
            workspace_id=workspace_id,
            evidence_id=record.result_id,
        )
        if projection is None:
            raise RuntimeError("idempotency result LearningEvidence is missing")
        return self._result(projection, created=False, replayed=True)

    async def _mark_succeeded(self, record_id: UUID, evidence_id: UUID) -> None:
        await self._uow.idempotency_records.mark_succeeded(
            record_id=record_id,
            result_type=RESULT_TYPE,
            result_id=evidence_id,
            completed_at=self._clock.now(),
        )
        await self._uow.flush()

    @staticmethod
    def _result(
        projection: LearningEvidenceProjection,
        *,
        created: bool,
        replayed: bool,
    ) -> MaterializeFt011LearningEvidenceResult:
        if not isinstance(projection.source, FT011Evidence):
            raise RuntimeError("FT-011 materialization resolved non-FT011 evidence")
        return MaterializeFt011LearningEvidenceResult(
            learning_evidence_id=projection.evidence.id,
            exit_review_version_id=projection.source.exit_review_version_id,
            created=created,
            replayed=replayed,
        )
