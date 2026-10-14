"""Application contracts only: these fakes do not prove PostgreSQL atomicity."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.features.learning.application.ft011_materialization_service import (
    COMMAND_TYPE,
    Ft011MaterializationError,
    Ft011MaterializationErrorCode,
    MaterializeFt011LearningEvidenceService,
    request_fingerprint,
)
from app.features.learning.domain import (
    FT011Evidence,
    IdempotencyRecord,
    IdempotencyStatus,
    LearningEvidence,
)

NOW = datetime(2026, 10, 14, 6, 0, tzinfo=UTC)
WORKSPACE = UUID(int=101)
TRADE = UUID(int=102)
OBSERVATION = UUID(int=103)
REVIEW = UUID(int=104)
VERSION = UUID(int=105)
NEXT_VERSION = UUID(int=106)


@dataclass(frozen=True)
class HandoffFixture:
    ready: bool = True
    reason: str = "READY"
    post_trade_observation_id: UUID | None = OBSERVATION
    exit_review_id: UUID | None = REVIEW
    exit_review_version_id: UUID | None = VERSION


@dataclass(frozen=True)
class ProjectionFixture:
    evidence: LearningEvidence
    source: FT011Evidence


class IdempotencyFixture:
    def __init__(self) -> None:
        self.records: dict[tuple[UUID, str, str], IdempotencyRecord] = {}

    async def get(self, workspace_id: UUID, command_type: str, key: str):
        return self.records.get((workspace_id, command_type, key))

    async def add(self, record: IdempotencyRecord) -> None:
        self.records[(record.workspace_id, record.command_type, record.idempotency_key)] = record

    async def mark_succeeded(self, *, record_id, result_type, result_id, completed_at):
        for key, record in tuple(self.records.items()):
            if record.id == record_id:
                self.records[key] = replace(
                    record,
                    status=IdempotencyStatus.SUCCEEDED,
                    result_type=result_type,
                    result_id=result_id,
                    completed_at=completed_at,
                )
                return
        raise AssertionError("record missing")


class UowFixture:
    def __init__(self) -> None:
        self.idempotency_records = IdempotencyFixture()
        self.flushes = 0
        self.commits = 0
        self.rollbacks = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        if exc_type is not None:
            await self.rollback()

    async def flush(self):
        self.flushes += 1

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        # Records are in-memory. No claim of transaction rollback semantics.
        self.rollbacks += 1


class RepositoryFixture:
    def __init__(self) -> None:
        self.evidence: dict[UUID, LearningEvidence] = {}
        self.sources: dict[UUID, FT011Evidence] = {}
        self.conflict = False

    async def get_by_source(self, *, workspace_id, exit_review_version_id):
        for source in self.sources.values():
            evidence = self.evidence[source.learning_evidence_id]
            if (
                evidence.workspace_id == workspace_id
                and source.exit_review_version_id == exit_review_version_id
            ):
                return ProjectionFixture(evidence, source)
        return None

    async def get_by_evidence_id(self, *, workspace_id, evidence_id):
        evidence = self.evidence.get(evidence_id)
        if evidence is not None and evidence.workspace_id == workspace_id:
            return ProjectionFixture(evidence, self.sources[evidence_id])
        return None

    async def add_evidence(self, evidence):
        self.evidence[evidence.id] = evidence

    async def add_source(self, source):
        if self.conflict:
            raise IntegrityError("synthetic unit conflict", {}, Exception("synthetic"))
        self.sources[source.learning_evidence_id] = source


class ReaderFixture:
    def __init__(self):
        self.handoff = HandoffFixture()
        self.calls = 0

    async def get(self, *, workspace_id, trade_id):
        assert workspace_id == WORKSPACE
        assert trade_id == TRADE
        self.calls += 1
        return self.handoff


class ClockFixture:
    def now(self):
        return NOW


class IdFixture:
    def new_uuid(self):
        return uuid4()


@pytest.fixture
def subject():
    uow = UowFixture()
    repository = RepositoryFixture()
    reader = ReaderFixture()
    service = MaterializeFt011LearningEvidenceService(
        uow=uow,
        repository=repository,
        handoff_reader=reader,
        clock=ClockFixture(),
        id_factory=IdFixture(),
    )
    return service, uow, repository, reader


def command(key="confirmed-v1", version=VERSION):
    return {
        "workspace_id": WORKSPACE,
        "trade_id": TRADE,
        "idempotency_key": key,
        "expected_exit_review_version_id": version,
    }


def test_legacy_fingerprint_is_byte_compatible():
    payload = {"workspace_id": str(WORKSPACE), "trade_id": str(TRADE)}
    expected = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    assert request_fingerprint(workspace_id=WORKSPACE, trade_id=TRADE) == expected
    assert (
        request_fingerprint(
            workspace_id=WORKSPACE, trade_id=TRADE, expected_exit_review_version_id=None
        )
        == expected
    )


def test_fingerprint_includes_exact_review_version():
    legacy = request_fingerprint(workspace_id=WORKSPACE, trade_id=TRADE)
    v1 = request_fingerprint(
        workspace_id=WORKSPACE, trade_id=TRADE, expected_exit_review_version_id=VERSION
    )
    v2 = request_fingerprint(
        workspace_id=WORKSPACE, trade_id=TRADE, expected_exit_review_version_id=NEXT_VERSION
    )
    assert len({legacy, v1, v2}) == 3
    assert v1 == request_fingerprint(
        workspace_id=WORKSPACE, trade_id=TRADE, expected_exit_review_version_id=VERSION
    )


async def test_pin_materializes_complete_provenance(subject):
    service, uow, repository, reader = subject
    result = await service.execute(**command())
    source = repository.sources[result.learning_evidence_id]
    assert result.created and not result.replayed
    assert result.exit_review_version_id == VERSION
    assert source == FT011Evidence(
        result.learning_evidence_id, TRADE, OBSERVATION, REVIEW, VERSION
    )
    assert uow.commits == 1
    assert reader.calls == 1


async def test_wrong_version_rejected_before_any_writes(subject):
    service, uow, repository, _ = subject
    with pytest.raises(Ft011MaterializationError) as caught:
        await service.execute(**command(version=NEXT_VERSION))
    assert caught.value.code is Ft011MaterializationErrorCode.SOURCE_VERSION_MISMATCH
    assert repository.evidence == {}
    assert repository.sources == {}
    assert uow.idempotency_records.records == {}
    assert uow.flushes == uow.commits == 0


@pytest.mark.parametrize(
    "reason",
    [
        "POST_TRADE_OBSERVATION_MISSING",
        "POST_TRADE_OBSERVATION_INCOMPLETE",
        "EXIT_REVIEW_MISSING",
        "EXIT_REVIEW_VERSION_MISSING",
        "EXIT_REVIEW_NOT_FINALIZED",
        "EXIT_REVIEW_STALE",
    ],
)
async def test_pin_does_not_override_owner_readiness(subject, reason):
    service, uow, repository, reader = subject
    reader.handoff = replace(reader.handoff, ready=False, reason=reason)
    with pytest.raises(Ft011MaterializationError) as caught:
        await service.execute(**command())
    assert caught.value.code is Ft011MaterializationErrorCode.SOURCE_NOT_READY
    assert caught.value.source_reason == reason
    assert repository.evidence == {}
    assert uow.idempotency_records.records == {}
    assert uow.commits == 0


@pytest.mark.parametrize(
    "field", ["post_trade_observation_id", "exit_review_id", "exit_review_version_id"]
)
async def test_incomplete_ready_provenance_still_fails_closed(subject, field):
    service, uow, repository, reader = subject
    reader.handoff = replace(reader.handoff, **{field: None})
    with pytest.raises(RuntimeError, match="complete provenance"):
        await service.execute(**command())
    assert repository.evidence == {}
    assert uow.idempotency_records.records == {}


async def test_retry_replays_original_after_source_becomes_stale(subject):
    service, uow, repository, reader = subject
    first = await service.execute(**command())
    historical_source = repository.sources[first.learning_evidence_id]
    reader.handoff = replace(reader.handoff, ready=False, reason="EXIT_REVIEW_STALE")
    replay = await service.execute(**command())
    assert replay.learning_evidence_id == first.learning_evidence_id
    assert replay.exit_review_version_id == VERSION
    assert not replay.created and replay.replayed
    assert repository.sources[first.learning_evidence_id] == historical_source
    assert reader.calls == 1  # Replay is historical, not a new CURRENT claim.
    assert uow.commits == 1


async def test_same_key_different_pin_is_not_a_retry(subject):
    service, uow, repository, reader = subject
    await service.execute(**command())
    reader.handoff = replace(reader.handoff, exit_review_version_id=NEXT_VERSION)
    with pytest.raises(Ft011MaterializationError) as caught:
        await service.execute(**command(version=NEXT_VERSION))
    assert caught.value.code is Ft011MaterializationErrorCode.IDEMPOTENCY_KEY_REUSED
    assert reader.calls == 1
    assert len(repository.sources) == uow.commits == 1


async def test_new_key_old_confirmation_cannot_materialize_new_review(subject):
    service, uow, repository, reader = subject
    first = await service.execute(**command())
    reader.handoff = replace(reader.handoff, exit_review_version_id=NEXT_VERSION)
    with pytest.raises(Ft011MaterializationError) as caught:
        await service.execute(**command(key="another-key"))
    assert caught.value.code is Ft011MaterializationErrorCode.SOURCE_VERSION_MISMATCH
    assert set(repository.sources) == {first.learning_evidence_id}
    assert len(uow.idempotency_records.records) == 1


async def test_explicit_new_version_does_not_mutate_previous_evidence(subject):
    service, _, repository, reader = subject
    first = await service.execute(**command())
    old_source = repository.sources[first.learning_evidence_id]
    reader.handoff = replace(reader.handoff, exit_review_version_id=NEXT_VERSION)
    second = await service.execute(**command(key="confirmed-v2", version=NEXT_VERSION))
    assert first.learning_evidence_id != second.learning_evidence_id
    assert second.exit_review_version_id == NEXT_VERSION
    assert len(repository.sources) == 2
    assert repository.sources[first.learning_evidence_id] == old_source
    assert old_source.exit_review_version_id == VERSION


async def test_new_key_same_pin_reuses_semantic_evidence(subject):
    service, uow, repository, _ = subject
    first = await service.execute(**command())
    second = await service.execute(**command(key="other-confirmation"))
    assert second.learning_evidence_id == first.learning_evidence_id
    assert not second.created and not second.replayed
    assert len(repository.sources) == 1
    assert len(uow.idempotency_records.records) == 2


async def test_legacy_completed_request_still_replays(subject):
    service, _, repository, reader = subject
    first = await service.execute(**command(version=None))
    reader.handoff = replace(reader.handoff, ready=False, reason="EXIT_REVIEW_STALE")
    replay = await service.execute(**command(version=None))
    assert replay.learning_evidence_id == first.learning_evidence_id
    assert replay.replayed and not replay.created
    assert len(repository.sources) == reader.calls == 1


async def test_legacy_key_cannot_be_reinterpreted_as_pinned_request(subject):
    service, _, repository, reader = subject
    await service.execute(**command(version=None))
    with pytest.raises(Ft011MaterializationError) as caught:
        await service.execute(**command())
    assert caught.value.code is Ft011MaterializationErrorCode.IDEMPOTENCY_KEY_REUSED
    assert len(repository.sources) == reader.calls == 1


@pytest.mark.parametrize(
    ("state", "code"),
    [
        (IdempotencyStatus.IN_PROGRESS, Ft011MaterializationErrorCode.IDEMPOTENCY_IN_PROGRESS),
        (IdempotencyStatus.FAILED_FINAL, Ft011MaterializationErrorCode.IDEMPOTENCY_FAILED_FINAL),
    ],
)
async def test_terminal_and_in_progress_keys_keep_existing_contract(subject, state, code):
    service, uow, repository, reader = subject
    record = IdempotencyRecord(
        id=uuid4(),
        workspace_id=WORKSPACE,
        command_type=COMMAND_TYPE,
        idempotency_key="confirmed-v1",
        request_fingerprint=request_fingerprint(
            workspace_id=WORKSPACE, trade_id=TRADE, expected_exit_review_version_id=VERSION
        ),
        status=state,
        created_at=NOW,
        error_code="SYNTHETIC_FAILURE" if state is IdempotencyStatus.FAILED_FINAL else None,
        completed_at=NOW if state is IdempotencyStatus.FAILED_FINAL else None,
    )
    await uow.idempotency_records.add(record)
    with pytest.raises(Ft011MaterializationError) as caught:
        await service.execute(**command())
    assert caught.value.code is code
    assert reader.calls == 0
    assert repository.evidence == {}


async def test_integrity_error_translation_is_not_a_postgresql_race_test(subject):
    service, uow, repository, _ = subject
    repository.conflict = True
    with pytest.raises(Ft011MaterializationError) as caught:
        await service.execute(**command())
    assert caught.value.code is Ft011MaterializationErrorCode.MATERIALIZATION_CONFLICT
    assert isinstance(caught.value.__cause__, IntegrityError)
    assert uow.rollbacks >= 1
    assert uow.commits == 0
