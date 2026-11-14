"""Explicit evidence commands and a separate, database-only snapshot reader."""

import hashlib
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass, field, replace
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.exceptions import ApplicationError
from app.features.learning.application.hebeltrader_source_reader import (
    HebeltraderSourceEvidence,
    HebeltraderSourceReader,
)
from app.features.product.domain.models import OptionDirection
from app.features.product.service.application import WarrantService
from app.features.trade_position.domain.enums import ExecutionSide
from app.features.trade_position.domain.hebeltrader_evidence import (
    HebeltraderEvidenceDeclaration,
    HebeltraderEvidenceRevision,
)
from app.features.trade_position.domain.price_binding import PriceBasis
from app.features.trade_position.persistence.hebeltrader_evidence import (
    SqlAlchemyHebeltraderEvidenceRepository,
)
from app.features.trade_position.persistence.models import ExecutionRecordModel
from app.features.trade_position.persistence.repositories import (
    SqlAlchemyPositionRepository,
    SqlAlchemyReadOnlyTradeRepository,
    SqlAlchemyTradeRepository,
)
from app.features.trade_position.service.hebeltrader_coverage import (
    HebeltraderCoverage,
    build_hebeltrader_coverage,
    resolve_execution_reference,
)
from app.features.trade_position.service.valuation_basis import (
    PositionExecutionBasis,
    read_position_execution_basis,
)

MAX_EXECUTION_FACTS = 2000
MAX_EVIDENCE_REVISIONS = 200


def evidence_error(code: str, message: str, status: int = 422) -> ApplicationError:
    return ApplicationError(code=code, message=message, status_code=status)


def current_revision(
    history: tuple[HebeltraderEvidenceRevision, ...],
) -> HebeltraderEvidenceRevision | None:
    superseded = {revision.supersedes_evidence_id for revision in history}
    current = [revision for revision in history if revision.id not in superseded]
    if len(current) > 1 or (history and not current):
        raise evidence_error("BASELINE_EVIDENCE_CONFLICT", "Belegstand ist nicht eindeutig.", 409)
    return current[0] if current else None


async def _context(
    session: AsyncSession, *, workspace_id: UUID, trade_id: UUID, position_id: UUID, lock: bool
) -> tuple[PositionExecutionBasis, UUID]:
    trade_reader = (
        SqlAlchemyTradeRepository(session) if lock else SqlAlchemyReadOnlyTradeRepository(session)
    )
    trade = await trade_reader.get(workspace_id, trade_id)
    position = await SqlAlchemyPositionRepository(session).get_for_trade(workspace_id, trade_id)
    if trade is None or position is None or position.id != position_id:
        raise evidence_error(
            "BASELINE_POSITION_NOT_FOUND",
            "Position gehört nicht zu diesem Trade und Workspace.",
            404,
        )
    # Bounded snapshots never silently truncate a source stream or denominator.
    ids = (
        await session.scalars(
            select(ExecutionRecordModel.id)
            .where(ExecutionRecordModel.trade_id == trade_id)
            .limit(MAX_EXECUTION_FACTS + 1)
        )
    ).all()
    if len(ids) > MAX_EXECUTION_FACTS:
        raise evidence_error(
            "BASELINE_EVIDENCE_LIMIT",
            "Ausführungshistorie überschreitet die vollständige Lesegrenze.",
            422,
        )
    warrant = await WarrantService(session).get(workspace_id, trade.product_id)
    basis = await read_position_execution_basis(session, trade=trade, position_id=position_id)
    return basis, warrant.underlying_id


async def _source(
    session: AsyncSession,
    *,
    basis: PositionExecutionBasis,
    underlying_id: UUID,
    source_version_id: UUID | None,
    reuse_trade_link: bool,
) -> HebeltraderSourceEvidence | None:
    reader = HebeltraderSourceReader(session)
    pin = source_version_id
    if pin is None and reuse_trade_link:
        pin = await reader.find_trade_source(
            workspace_id=basis.trade.workspace_id, trade_id=basis.trade.id
        )
    if pin is None:
        return None
    return await reader.read(
        workspace_id=basis.trade.workspace_id,
        source_version_id=pin,
        product_id=basis.trade.product_id,
        underlying_id=underlying_id,
    )


def validate_references(
    declaration: HebeltraderEvidenceDeclaration,
    basis: PositionExecutionBasis,
    underlying_id: UUID,
    source: HebeltraderSourceEvidence | None,
) -> None:
    groups = (
        (
            declaration.entry_order.execution_ids if declaration.entry_order else (),
            ExecutionSide.BUY,
        ),
        (tuple(item.execution_id for item in declaration.underlying_trades), ExecutionSide.BUY),
        (tuple(item.execution_id for item in declaration.z1_sales), ExecutionSide.SELL),
    )
    for references, side in groups:
        resolved: set[UUID] = set()
        for reference in references:
            fact, _, problem = resolve_execution_reference(basis, reference, side)
            if problem or fact is None:
                raise evidence_error(
                    "BASELINE_EXECUTION_MISMATCH", problem or "Ausführungsbezug fehlt."
                )
            if fact.id in resolved:
                raise evidence_error(
                    "BASELINE_EXECUTION_DUPLICATE",
                    "Mehrere Belege bezeichnen dieselbe effektive Ausführung.",
                )
            resolved.add(fact.id)
    if declaration.entry_order is not None:
        first_buy = next(
            (fact for fact in basis.effective_executions if fact.side is ExecutionSide.BUY), None
        )
        entry_ids = {
            fact.id
            for reference in declaration.entry_order.execution_ids
            if (fact := resolve_execution_reference(basis, reference, ExecutionSide.BUY)[0])
            is not None
        }
        if first_buy is None or first_buy.id not in entry_ids:
            raise evidence_error(
                "BASELINE_ENTRY_ORDER_MISMATCH",
                "Die ursprüngliche Einstiegsgruppe muss den ersten effektiven Kauf enthalten.",
            )
    if declaration.source_version_id is not None and (source is None or not source.suitable):
        raise evidence_error(
            "BASELINE_SOURCE_UNSUITABLE",
            "Die angegebene Version ist keine passende bestätigte historische Hebeltrader-Quelle.",
        )
    for observation in declaration.underlying_trades:
        if (
            observation.binding.basis is not PriceBasis.UNDERLYING
            or observation.binding.instrument_id != underlying_id
        ):
            raise evidence_error(
                "BASELINE_PRICE_BINDING_MISMATCH",
                "Basiswertpreis und Produktpreis oder Instrumentidentitäten "
                "dürfen nicht vertauscht werden.",
            )
        if source and source.source and observation.binding != source.source.underlying.binding:
            raise evidence_error(
                "BASELINE_PRICE_BINDING_MISMATCH",
                "Preisachse oder Währung passt nicht zur historischen Quelle.",
            )
        if (
            declaration.scale_review_status == "UNCHANGED_VERIFIED"
            and observation.scale_reference != declaration.source_scale_reference
        ):
            raise evidence_error(
                "BASELINE_SCALE_MISMATCH",
                "Unterschiedliche Preismaßstäbe sind nicht als "
                "unverändert vergleichbar bestätigbar.",
            )


class HebeltraderEvidenceService:
    """Append references only; existing trade lock serializes evidence/corrections."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = SqlAlchemyHebeltraderEvidenceRepository(session)

    async def record(
        self,
        *,
        workspace_id: UUID,
        trade_id: UUID,
        position_id: UUID,
        declaration: HebeltraderEvidenceDeclaration,
        actor: UUID,
        request_id: UUID,
        supersedes_evidence_id: UUID | None,
    ) -> HebeltraderEvidenceRevision:
        fingerprint = hashlib.sha256(
            json.dumps(
                {
                    "trade_id": str(trade_id),
                    "position_id": str(position_id),
                    "declaration": asdict(declaration),
                    "supersedes": str(supersedes_evidence_id),
                },
                sort_keys=True,
                default=str,
            ).encode()
        ).hexdigest()
        try:
            basis, underlying_id = await _context(
                self._session,
                workspace_id=workspace_id,
                trade_id=trade_id,
                position_id=position_id,
                lock=True,
            )
            replay = await self._repository.find_request(workspace_id, request_id)
            if replay is not None:
                if replay.request_fingerprint != fingerprint:
                    raise evidence_error(
                        "BASELINE_EVIDENCE_REQUEST_CONFLICT",
                        "Vorgangskennung gehört zu einer anderen Belegbestätigung.",
                        409,
                    )
                return replay
            if basis.trade.cancelled_at is not None:
                raise evidence_error(
                    "TRADE_CANCELLED",
                    "Stornierter Trade kann keine neue Belegzuordnung erhalten.",
                    409,
                )
            history = await self._repository.history(workspace_id, trade_id, position_id)
            current = current_revision(history)
            if supersedes_evidence_id != (current.id if current else None):
                raise evidence_error(
                    "BASELINE_EVIDENCE_CONFLICT",
                    "Belegstand hat sich geändert. Aktuellen Stand laden.",
                    409,
                )
            if len(history) >= MAX_EVIDENCE_REVISIONS:
                raise evidence_error(
                    "BASELINE_EVIDENCE_LIMIT",
                    "Die Belegkette erreicht die vollständige Lesegrenze.",
                )
            source = await _source(
                self._session,
                basis=basis,
                underlying_id=underlying_id,
                source_version_id=declaration.source_version_id,
                reuse_trade_link=current is None,
            )
            if declaration.source_version_id is None and source and source.suitable:
                # Reuse an existing explicit historical pin once; subsequent reads
                # and revisions never follow a changing recommendation or link.
                declaration = replace(declaration, source_version_id=source.source_version_id)
            validate_references(declaration, basis, underlying_id, source)
            revision = HebeltraderEvidenceRevision(
                id=uuid4(),
                workspace_id=workspace_id,
                trade_id=trade_id,
                position_id=position_id,
                product_id=basis.trade.product_id,
                underlying_id=underlying_id,
                declaration=declaration,
                recorded_at=datetime.now(UTC),
                recorded_by=actor,
                request_id=request_id,
                request_fingerprint=fingerprint,
                supersedes_evidence_id=supersedes_evidence_id,
            )
            await self._repository.add(revision)
            await self._session.commit()
            return revision
        except IntegrityError as error:
            await self._session.rollback()
            raise evidence_error(
                "BASELINE_EVIDENCE_CONFLICT",
                "Belegzuordnung wurde zwischenzeitlich geändert "
                "oder widerspricht dem Ownervertrag.",
                409,
            ) from error
        except Exception:
            await self._session.rollback()
            raise


@dataclass(frozen=True, slots=True)
class HebeltraderEvidenceHistory:
    trade_id: UUID
    position_id: UUID
    current_revision_id: UUID | None
    history: tuple[HebeltraderEvidenceRevision, ...]
    read_started_at: datetime
    read_completed_at: datetime


@dataclass(frozen=True, slots=True)
class HebeltraderScaleBasis:
    """The reviewed F207-4 scope, never a qualification of later market bars.

    ``UNCHANGED_VERIFIED`` relates the pinned publisher marks to the declared
    purchase observations. A monitoring consumer must separately establish the
    scale of each new market observation before comparing it with those marks.
    """

    review_status: Literal["UNVERIFIED", "UNCHANGED_VERIFIED", "ADJUSTMENT_REQUIRED"]
    source_scale_reference: str | None
    review_reference: str | None
    scope: Literal["SOURCE_AND_PURCHASE_EVIDENCE_ONLY"] = field(
        default="SOURCE_AND_PURCHASE_EVIDENCE_ONLY", init=False
    )
    market_observations_verified: Literal[False] = field(default=False, init=False)


@dataclass(frozen=True, slots=True)
class HebeltraderMonitoringBasis:
    """Immutable references and owner projections from the caller's session."""

    coverage: HebeltraderCoverage
    execution_basis: PositionExecutionBasis
    evidence_revision: HebeltraderEvidenceRevision | None
    source_evidence: HebeltraderSourceEvidence | None
    scale: HebeltraderScaleBasis
    option_direction: OptionDirection | None
    option_terms_version_ids: tuple[UUID, ...]
    option_direction_reason: str | None


@dataclass(frozen=True, slots=True)
class _HebeltraderEvidenceSnapshot:
    coverage: HebeltraderCoverage
    execution_basis: PositionExecutionBasis
    evidence_revision: HebeltraderEvidenceRevision | None
    source_evidence: HebeltraderSourceEvidence | None


async def _read_evidence_snapshot(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    trade_id: UUID,
    position_id: UUID,
    started_at: datetime,
    lock: bool,
) -> _HebeltraderEvidenceSnapshot:
    """Share fact selection with the existing F207-4 coverage read."""
    basis, underlying_id = await _context(
        session,
        workspace_id=workspace_id,
        trade_id=trade_id,
        position_id=position_id,
        lock=lock,
    )
    history = await SqlAlchemyHebeltraderEvidenceRepository(session).history(
        workspace_id, trade_id, position_id
    )
    if len(history) > MAX_EVIDENCE_REVISIONS:
        raise evidence_error(
            "BASELINE_EVIDENCE_LIMIT",
            "Belegkette überschreitet die vollständige Lesegrenze.",
        )
    current = current_revision(history)
    source = await _source(
        session,
        basis=basis,
        underlying_id=underlying_id,
        source_version_id=current.declaration.source_version_id if current else None,
        reuse_trade_link=current is None,
    )
    return _HebeltraderEvidenceSnapshot(
        coverage=build_hebeltrader_coverage(
            basis=basis,
            underlying_id=underlying_id,
            revision=current,
            source_evidence=source,
            read_started_at=started_at,
            read_completed_at=datetime.now(UTC),
        ),
        execution_basis=basis,
        evidence_revision=current,
        source_evidence=source,
    )


async def read_hebeltrader_monitoring_basis(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    trade_id: UUID,
    position_id: UUID,
    lock: bool = False,
) -> HebeltraderMonitoringBasis:
    """Read existing execution/source owners within the caller's transaction.

    The caller supplies the snapshot and owns its lifetime. ``lock=True`` uses
    the existing trade lock for a subsequent explicit monitoring command. This
    read neither flushes pending changes nor starts, commits or rolls back a
    transaction. It cannot contact a provider, activate rules or issue notices.

    Product direction is qualified against the existing terms history. A later
    different direction must not silently redefine historical target semantics;
    missing or conflicting terms therefore leave it explicitly unknown.
    """
    started = datetime.now(UTC)
    with session.no_autoflush:
        snapshot = await _read_evidence_snapshot(
            session,
            workspace_id=workspace_id,
            trade_id=trade_id,
            position_id=position_id,
            started_at=started,
            lock=lock,
        )
        current = snapshot.evidence_revision
        basis = snapshot.execution_basis
        if current is not None and (
            current.workspace_id,
            current.trade_id,
            current.position_id,
            current.product_id,
            current.underlying_id,
        ) != (
            workspace_id,
            trade_id,
            position_id,
            basis.trade.product_id,
            snapshot.coverage.underlying_id,
        ):
            raise evidence_error(
                "BASELINE_EVIDENCE_CONFLICT", "Belegrevision gehört nicht zur Positionsbasis.", 409
            )
        terms = await WarrantService(session).terms_history(workspace_id, basis.trade.product_id)
        if any(term.warrant_id != basis.trade.product_id for term in terms):
            raise evidence_error(
                "BASELINE_PRODUCT_MISMATCH", "Produktbedingungen gehören nicht zur Position.", 409
            )
        directions = {term.option_direction for term in terms}
        direction = next(iter(directions)) if len(directions) == 1 else None
        direction_reason = (
            "PRODUCT_TERMS_MISSING"
            if not terms
            else "PRODUCT_DIRECTION_CONFLICT" if direction is None else None
        )
        declaration = current.declaration if current else HebeltraderEvidenceDeclaration()
        return HebeltraderMonitoringBasis(
            coverage=replace(snapshot.coverage, read_completed_at=datetime.now(UTC)),
            execution_basis=basis,
            evidence_revision=current,
            source_evidence=snapshot.source_evidence,
            scale=HebeltraderScaleBasis(
                review_status=declaration.scale_review_status,
                source_scale_reference=declaration.source_scale_reference,
                review_reference=declaration.scale_review_reference,
            ),
            option_direction=direction,
            option_terms_version_ids=tuple(term.id for term in terms),
            option_direction_reason=direction_reason,
        )


class HebeltraderEvidenceReader:
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
                # Even a successful read rolls its snapshot back. No command/UoW,
                # provider, policy activation, scheduler or delivery is reachable.
                await session.rollback()

    async def read(
        self, workspace_id: UUID, trade_id: UUID, position_id: UUID
    ) -> HebeltraderCoverage:
        started = datetime.now(UTC)
        async with self._snapshot() as session:
            return (
                await _read_evidence_snapshot(
                    session,
                    workspace_id=workspace_id,
                    trade_id=trade_id,
                    position_id=position_id,
                    started_at=started,
                    lock=False,
                )
            ).coverage

    async def history(
        self, workspace_id: UUID, trade_id: UUID, position_id: UUID
    ) -> HebeltraderEvidenceHistory:
        started = datetime.now(UTC)
        async with self._snapshot() as session:
            await _context(
                session,
                workspace_id=workspace_id,
                trade_id=trade_id,
                position_id=position_id,
                lock=False,
            )
            history = await SqlAlchemyHebeltraderEvidenceRepository(session).history(
                workspace_id, trade_id, position_id
            )
            if len(history) > MAX_EVIDENCE_REVISIONS:
                raise evidence_error(
                    "BASELINE_EVIDENCE_LIMIT",
                    "Belegkette überschreitet die vollständige Lesegrenze.",
                )
            current = current_revision(history)
            return HebeltraderEvidenceHistory(
                trade_id,
                position_id,
                current.id if current else None,
                history,
                started,
                datetime.now(UTC),
            )
