"""Explicit, snapshot-based target assessment; no scheduler/provider/alert calls."""

import hashlib
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID, uuid4

from pydantic import TypeAdapter
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.exceptions import ApplicationError
from app.features.market_data.service.hebeltrader_history import (
    HebeltraderHistoryReader,
    HebeltraderPriceHistory,
)
from app.features.position_monitoring.domain.hebeltrader_targets import (
    BASELINE_ID,
    BASELINE_VERSION,
    DEFINITION_VERSION,
    TargetComparisonQualification,
    TargetPositionBasis,
    TargetSourceBasis,
    evaluate_hebeltrader_targets,
)
from app.features.position_monitoring.persistence.hebeltrader_targets import (
    SqlAlchemyHebeltraderTargetRepository,
    TargetAssessmentRecord,
    TargetRequestReceipt,
)
from app.features.position_monitoring.service.hebeltrader_target_contracts import (
    HebeltraderTargetsReport,
    TargetAssessmentCommand,
    TargetInputsView,
)
from app.features.position_monitoring.service.hebeltrader_target_projection import (
    ASSESSMENT_ADAPTER,
    VIEW_ADAPTER,
    assessment_view,
    persisted_view,
    reason_text,
    target_history,
    target_position,
    target_source,
)
from app.features.trade_position.service.hebeltrader_evidence import (
    HebeltraderMonitoringBasis,
    read_hebeltrader_monitoring_basis,
)

QUALIFICATION_ADAPTER = TypeAdapter(TargetComparisonQualification)
HISTORY_ADAPTER = TypeAdapter(HebeltraderPriceHistory)
POSITION_ADAPTER = TypeAdapter(TargetPositionBasis)
SOURCE_ADAPTER = TypeAdapter(TargetSourceBasis)


def target_error(code: str, message: str, status: int = 409) -> ApplicationError:
    return ApplicationError(code=code, message=message, status_code=status)


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode()
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class _Inputs:
    owner: HebeltraderMonitoringBasis
    position: TargetPositionBasis
    source: TargetSourceBasis | None
    history: HebeltraderPriceHistory
    basis_id: str


def _matches(qualification: TargetComparisonQualification | None, inputs: _Inputs) -> bool:
    source, binding = inputs.source, inputs.history.binding
    return (
        qualification is not None
        and bool(qualification.evidence_reference.strip())
        and source is not None
        and binding is not None
        and qualification.history_fingerprint == inputs.history.fingerprint
        and qualification.listing_fingerprint == binding.fingerprint
        and qualification.source_version_id == source.source_version_id
        and qualification.source_scale_reference == source.scale_reference
    )


def _previous_qualification(
    previous: TargetAssessmentRecord | None,
) -> TargetComparisonQualification | None:
    value = previous.inputs.get("qualification") if previous else None
    return QUALIFICATION_ADAPTER.validate_python(value) if value is not None else None


async def _inputs(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    trade_id: UUID,
    position_id: UUID,
    now: datetime,
    lock: bool,
    previous: TargetAssessmentRecord | None,
    owner: HebeltraderMonitoringBasis | None = None,
) -> _Inputs:
    if owner is None:
        owner = await read_hebeltrader_monitoring_basis(
            session,
            workspace_id=workspace_id,
            trade_id=trade_id,
            position_id=position_id,
            lock=lock,
        )
    position = target_position(owner)
    # Preserve the selected historical listing across changing primary metadata.
    # A new primary is discovery only, never an implicit rebind of prior evidence.
    binding = previous.inputs.get("history", {}).get("binding") if previous else None
    listing_id = UUID(binding["listing_id"]) if binding is not None else None
    opened_on = position.opened_on or (
        position.opened_at.astimezone(UTC).date() if position.opened_at else now.date()
    )
    history = await HebeltraderHistoryReader(session).read(
        workspace_id=workspace_id,
        underlying_id=position.underlying_id,
        listing_id=listing_id,
        start_date=min(opened_on - timedelta(days=1), now.date()),
        end_date=now.date(),
        known_at=now,
    )
    basis_id = _fingerprint(
        {
            "definition_version": DEFINITION_VERSION,
            "owner_basis_id": owner.coverage.basis_id,
            "option_direction": owner.option_direction,
            "option_direction_reason": owner.option_direction_reason,
            "option_terms_version_ids": owner.option_terms_version_ids,
            "history_fingerprint": history.fingerprint,
        }
    )
    return _Inputs(owner, position, target_source(owner), history, basis_id)


def _report(
    inputs: _Inputs,
    *,
    latest: TargetAssessmentRecord | None,
    count: int,
    started: datetime,
) -> HebeltraderTargetsReport:
    qualification_reusable = _matches(_previous_qualification(latest), inputs)
    source, history, position = inputs.source, inputs.history, inputs.position
    issues = [reason_text(reason) for reason in history.reasons]
    if source is None:
        issues.append("Eine passende bestätigte historische Hebeltrader-Quellenversion fehlt.")
    if inputs.owner.option_direction_reason:
        issues.append(reason_text(inputs.owner.option_direction_reason))
    if not qualification_reusable:
        issues.append(
            "Die historische Listingbindung und der unveränderte Vergleichsmaßstab dieser "
            "Kursreihe müssen mit einer konkreten Belegreferenz qualifiziert werden. "
            "Die vorhandene Kaufbelegfreigabe deckt diese Tageskurse nicht automatisch ab."
        )
    if any(row.issues for row in history.rows):
        issues.append(
            "Einzelne Kursbelege haben ungeklärte Zeit-, Qualitäts- oder Identitätsprobleme."
        )
    if any(row.scale_status == "ADJUSTMENT_INDICATION_PRESENT" for row in history.rows):
        issues.append(reason_text("ADJUSTMENT_INDICATION_PRESENT"))
    if position.original_z1_quantity is None:
        issues.append("Der ursprüngliche Z1-Mengenbezug ist noch nicht vollständig belegt.")
    if position.personal_underlying_entry is None:
        issues.append("Der persönliche Basiswerteinstand ist noch nicht vollständig belegt.")
    return HebeltraderTargetsReport(
        trade_id=position.trade_id,
        position_id=position.position_id,
        current_basis_id=inputs.basis_id,
        currentness=(
            "NO_ASSESSMENT"
            if latest is None
            else "CURRENT" if latest.basis_id == inputs.basis_id else "CHANGED_INPUTS"
        ),
        position_state=(
            "CANCELLED" if position.cancelled else "CLOSED" if position.closed else "OPEN"
        ),
        read_started_at=started,
        read_completed_at=datetime.now(UTC),
        assessment_count=count,
        inputs=TargetInputsView(
            source_version_id=source.source_version_id if source else None,
            source_scale_reference=source.scale_reference if source else None,
            price_history_fingerprint=history.fingerprint,
            listing_binding_fingerprint=history.binding.fingerprint if history.binding else None,
            qualification_reusable=qualification_reusable,
            available_price_rows=len(history.rows),
            issues=tuple(dict.fromkeys(issues)),
        ),
        latest_assessment=persisted_view(latest) if latest else None,
    )


class HebeltraderTargetReader:
    """GETs have a separate database-enforced read-only transaction boundary."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    @asynccontextmanager
    async def _snapshot(self) -> AsyncIterator[AsyncSession]:
        async with AsyncSession(self._engine, expire_on_commit=False, autoflush=False) as session:
            await session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
            await session.execute(text("SET LOCAL statement_timeout = '10000ms'"))
            try:
                yield session
            finally:
                await session.rollback()

    async def read(
        self, workspace_id: UUID, trade_id: UUID, position_id: UUID
    ) -> HebeltraderTargetsReport:
        started = datetime.now(UTC)
        async with self._snapshot() as session:
            repository = SqlAlchemyHebeltraderTargetRepository(session)
            latest = await repository.latest(workspace_id, trade_id, position_id)
            inputs = await _inputs(
                session,
                workspace_id=workspace_id,
                trade_id=trade_id,
                position_id=position_id,
                now=started,
                lock=False,
                previous=latest,
            )
            count = await repository.count(workspace_id, trade_id, position_id)
            return _report(inputs, latest=latest, count=count, started=started)

    async def assessment(
        self, workspace_id: UUID, trade_id: UUID, position_id: UUID, assessment_id: UUID
    ) -> TargetAssessmentRecord:
        async with self._snapshot() as session:
            # Scope the existing position even for a missing assessment ID.
            await read_hebeltrader_monitoring_basis(
                session, workspace_id=workspace_id, trade_id=trade_id, position_id=position_id
            )
            record = await SqlAlchemyHebeltraderTargetRepository(session).get(
                workspace_id, trade_id, position_id, assessment_id
            )
            if record is None:
                raise target_error(
                    "HEBELTRADER_ASSESSMENT_NOT_FOUND", "Prüfstand nicht gefunden.", 404
                )
            return record


class HebeltraderTargetService:
    """Append one reviewable result and receipt under the existing trade lock."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = SqlAlchemyHebeltraderTargetRepository(session)

    async def assess(
        self,
        *,
        workspace_id: UUID,
        trade_id: UUID,
        command: TargetAssessmentCommand,
        actor: UUID,
        now: datetime | None = None,
    ) -> HebeltraderTargetsReport:
        started = now or datetime.now(UTC)
        if started.utcoffset() is None:
            raise ValueError("Assessment cutoff must be timezone-aware")
        started = started.astimezone(UTC)
        request_fingerprint = _fingerprint(
            {"workspace_id": workspace_id, "trade_id": trade_id, "actor": actor, **asdict(command)}
        )
        try:
            await self._session.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
            await self._session.execute(text("SET LOCAL statement_timeout = '10000ms'"))
            # Acquire the same owner lock used by execution/evidence corrections
            # before selecting the terminal assessment. No monitoring lock order.
            await read_hebeltrader_monitoring_basis(
                self._session,
                workspace_id=workspace_id,
                trade_id=trade_id,
                position_id=command.position_id,
                lock=True,
            )
            # Waiting for the trade lock must finish before the immutable input
            # snapshot begins. An append-only owner revision does not UPDATE the
            # trade row, so a pre-wait REPEATABLE READ snapshot would be stale.
            engine = self._session.bind
            if not isinstance(engine, AsyncEngine):
                raise RuntimeError("Target commands require an engine-backed session")
            snapshot_at = started if now is not None else datetime.now(UTC)
            async with HebeltraderTargetReader(engine)._snapshot() as snapshot:
                snapshot_repository = SqlAlchemyHebeltraderTargetRepository(snapshot)
                latest = await snapshot_repository.latest(
                    workspace_id, trade_id, command.position_id
                )
                inputs = await _inputs(
                    snapshot,
                    workspace_id=workspace_id,
                    trade_id=trade_id,
                    position_id=command.position_id,
                    now=snapshot_at,
                    lock=False,
                    previous=latest,
                )
                count = await snapshot_repository.count(workspace_id, trade_id, command.position_id)
                replay = await snapshot_repository.find_request(workspace_id, command.request_id)
                if replay is not None:
                    if replay.request_fingerprint != request_fingerprint or (
                        replay.trade_id,
                        replay.position_id,
                    ) != (trade_id, command.position_id):
                        raise target_error(
                            "HEBELTRADER_REQUEST_CONFLICT",
                            "Die Vorgangskennung gehört zu einer anderen Belegprüfung.",
                        )
                    await self._session.rollback()
                    return _report(inputs, latest=latest, count=count, started=started)
                if inputs.position.closed or inputs.position.cancelled:
                    raise target_error(
                        "HEBELTRADER_POSITION_CLOSED",
                        "Geschlossene oder stornierte Positionen bleiben historisch lesbar.",
                    )
                if (
                    inputs.basis_id != command.expected_basis_id
                    or command.expected_assessment_id != (latest.id if latest else None)
                ):
                    raise target_error(
                        "HEBELTRADER_BASIS_CONFLICT",
                        "Die Beleggrundlage hat sich geändert. Aktuellen Prüfstand laden.",
                    )
                qualification = command.qualification
                if qualification is not None and not _matches(qualification, inputs):
                    raise target_error(
                        "HEBELTRADER_QUALIFICATION_MISMATCH",
                        "Die Freigabe passt nicht zu Kursreihe, Listing, Quelle und Preismaßstab.",
                        422,
                    )
                if qualification is None:
                    earlier = _previous_qualification(latest)
                    qualification = earlier if _matches(earlier, inputs) else None
                previous_domain = (
                    ASSESSMENT_ADAPTER.validate_python(latest.result["domain"]) if latest else None
                )
                assessment = evaluate_hebeltrader_targets(
                    position=inputs.position,
                    source=inputs.source,
                    history=target_history(inputs.history),
                    qualification=qualification,
                    assessment_id=uuid4(),
                    assessed_at=snapshot_at,
                    previous=previous_domain,
                )
                if (
                    latest is None
                    or latest.basis_id != inputs.basis_id
                    or assessment.input_fingerprint != latest.input_fingerprint
                ):
                    view = assessment_view(
                        assessment,
                        basis_id=inputs.basis_id,
                        source=inputs.source,
                        history=inputs.history,
                        previous=latest,
                        recorded_at=snapshot_at,
                    )
                    latest = TargetAssessmentRecord(
                        id=assessment.assessment_id,
                        workspace_id=workspace_id,
                        trade_id=trade_id,
                        position_id=command.position_id,
                        product_id=inputs.position.product_id,
                        underlying_id=inputs.position.underlying_id,
                        source_version_id=(
                            inputs.source.source_version_id if inputs.source else None
                        ),
                        evidence_revision_id=inputs.position.evidence_revision_id,
                        previous_assessment_id=latest.id if latest else None,
                        definition_version=DEFINITION_VERSION,
                        baseline_id=BASELINE_ID,
                        baseline_version=BASELINE_VERSION,
                        basis_id=inputs.basis_id,
                        input_fingerprint=assessment.input_fingerprint,
                        recorded_at=snapshot_at,
                        recorded_by=actor,
                        inputs={
                            "position": POSITION_ADAPTER.dump_python(inputs.position, mode="json"),
                            "source": (
                                SOURCE_ADAPTER.dump_python(inputs.source, mode="json")
                                if inputs.source
                                else None
                            ),
                            "source_provenance": (
                                json.loads(
                                    json.dumps(asdict(inputs.owner.coverage.source), default=str)
                                )
                                if inputs.owner.coverage.source
                                else None
                            ),
                            "history": HISTORY_ADAPTER.dump_python(inputs.history, mode="json"),
                            "source_evidence": (
                                json.loads(
                                    json.dumps(asdict(inputs.owner.source_evidence), default=str)
                                )
                                if inputs.owner.source_evidence
                                else None
                            ),
                            "qualification": (
                                QUALIFICATION_ADAPTER.dump_python(qualification, mode="json")
                                if qualification
                                else None
                            ),
                            "option_terms_version_ids": [
                                str(value) for value in inputs.owner.option_terms_version_ids
                            ],
                        },
                        result={
                            **cast(dict[str, Any], VIEW_ADAPTER.dump_python(view, mode="json")),
                            "domain": ASSESSMENT_ADAPTER.dump_python(assessment, mode="json"),
                        },
                    )
                    await self._repository.add(latest)
                    count += 1
                await self._repository.receipt(
                    TargetRequestReceipt(
                        id=uuid4(),
                        workspace_id=workspace_id,
                        trade_id=trade_id,
                        position_id=command.position_id,
                        assessment_id=latest.id,
                        request_id=command.request_id,
                        request_fingerprint=request_fingerprint,
                        recorded_at=snapshot_at,
                        recorded_by=actor,
                    )
                )
                report = _report(inputs, latest=latest, count=count, started=started)
                await self._session.commit()
                return report
        except IntegrityError as error:
            await self._session.rollback()
            raise target_error(
                "HEBELTRADER_ASSESSMENT_CONFLICT",
                "Der Prüfstand wurde zwischenzeitlich geändert oder verletzt die Belegzuordnung.",
            ) from error
        except DBAPIError as error:
            await self._session.rollback()
            if getattr(error.orig, "sqlstate", None) in {"40001", "40P01"}:
                raise target_error(
                    "HEBELTRADER_BASIS_CONFLICT",
                    "Die Beleggrundlage wurde gleichzeitig geändert. Aktuellen Prüfstand laden.",
                ) from error
            raise
        except Exception:
            await self._session.rollback()
            raise
