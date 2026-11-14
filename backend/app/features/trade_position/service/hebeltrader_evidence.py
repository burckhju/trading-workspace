"""Explicit evidence commands and a separate, database-only snapshot reader."""

import hashlib
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.exceptions import ApplicationError
from app.features.learning.application.hebeltrader_source_reader import (
    HebeltraderSourceEvidence,
    HebeltraderSourceReader,
)
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
            basis, underlying_id = await _context(
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
            source = await _source(
                session,
                basis=basis,
                underlying_id=underlying_id,
                source_version_id=current.declaration.source_version_id if current else None,
                reuse_trade_link=current is None,
            )
            return build_hebeltrader_coverage(
                basis=basis,
                underlying_id=underlying_id,
                revision=current,
                source_evidence=source,
                read_started_at=started,
                read_completed_at=datetime.now(UTC),
            )

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
