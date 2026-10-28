"""Explicit reviewed-source commands; never update executions or confirmations."""

from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions.types import ApplicationError
from app.features.market.persistence.models import CurrencyModel, TradingVenueModel
from app.features.product.persistence.models import WarrantModel
from app.features.trade_position.domain.currency_evidence import (
    CurrencyEvidence,
    CurrencyEvidenceKind,
    CurrencyEvidenceLimitExceeded,
    CurrencyListingEvidence,
    evidence_fingerprint,
)
from app.features.trade_position.persistence.currency_evidence import (
    SqlAlchemyCurrencyEvidenceRepository,
)
from app.features.trade_position.persistence.models import (
    ExecutionRecordModel,
    TradeModel,
)


def _error(code: str, message: str, status: int = 409) -> ApplicationError:
    return ApplicationError(code=code, message=message, status_code=status)


class CurrencyEvidenceService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = SqlAlchemyCurrencyEvidenceRepository(session)

    async def _product(self, workspace_id: UUID, product_id: UUID, *, lock: bool = False) -> None:
        query = select(WarrantModel.id).where(
            WarrantModel.workspace_id == workspace_id, WarrantModel.id == product_id
        )
        if lock:
            query = query.with_for_update()
        if await self._session.scalar(query) is None:
            raise _error(
                "WARRANT_NOT_FOUND",
                "Produkt wurde in diesem Workspace nicht gefunden.",
                404,
            )

    async def history(self, workspace_id: UUID, product_id: UUID) -> tuple[CurrencyEvidence, ...]:
        await self._product(workspace_id, product_id)
        try:
            return await self._repository.list_for_product(workspace_id, product_id)
        except CurrencyEvidenceLimitExceeded as error:
            raise _error(
                "CURRENCY_EVIDENCE_LIMIT",
                "Der Quellenumfang überschreitet die sichere Lesegrenze.",
                422,
            ) from error

    async def _validate_scope(self, evidence: CurrencyEvidence) -> None:
        if evidence.kind == "EXECUTION_DOCUMENT":
            trade = await self._session.scalar(
                select(TradeModel)
                .where(
                    TradeModel.workspace_id == evidence.workspace_id,
                    TradeModel.id == evidence.trade_id,
                    TradeModel.product_id == evidence.product_id,
                )
                .with_for_update()
            )
            if trade is None:
                raise _error(
                    "EXECUTION_NOT_FOUND",
                    "Trade und Produkt passen nicht zur Quelle.",
                    404,
                )
            if trade.cancelled_at is not None:
                raise _error("TRADE_CANCELLED", "Dieser Trade wurde storniert.")
            execution = await self._session.scalar(
                select(ExecutionRecordModel.id).where(
                    ExecutionRecordModel.id == evidence.execution_id,
                    ExecutionRecordModel.trade_id == evidence.trade_id,
                    ExecutionRecordModel.product_id == evidence.product_id,
                )
            )
            if execution is None:
                raise _error(
                    "EXECUTION_NOT_FOUND",
                    "Die konkrete Buchung wurde nicht gefunden.",
                    404,
                )
        codes = {item.currency_code for item in evidence.listings if item.currency_code is not None}
        if evidence.currency_code is not None:
            codes.add(evidence.currency_code)
        if codes:
            found = set(
                await self._session.scalars(
                    select(CurrencyModel.code).where(CurrencyModel.code.in_(codes))
                )
            )
            if found != codes:
                raise _error(
                    "CURRENCY_NOT_FOUND",
                    "Eine Quellenwährung ist im Währungskatalog nicht bekannt.",
                    422,
                )
        venues = {item.trading_venue_id for item in evidence.listings}
        if evidence.trading_venue_id is not None:
            venues.add(evidence.trading_venue_id)
        if venues:
            found_venues = set(
                await self._session.scalars(
                    select(TradingVenueModel.id).where(TradingVenueModel.id.in_(venues))
                )
            )
            if found_venues != venues:
                raise _error(
                    "TRADING_VENUE_NOT_FOUND",
                    "Ein Quellenhandelsplatz ist nicht bekannt.",
                    422,
                )
        # Historical currencies and venues remain admissible even if inactive today.

    async def _validate_predecessor(self, evidence: CurrencyEvidence) -> None:
        predecessor_id = evidence.supersedes_evidence_id
        if predecessor_id is None:
            if evidence.revoked:
                raise _error(
                    "CURRENCY_EVIDENCE_CONFLICT",
                    "Ein Widerruf benötigt den bisherigen Nachweis.",
                )
            return
        previous = await self._repository.get(evidence.workspace_id, predecessor_id)
        if previous is None or any(
            getattr(previous, field) != getattr(evidence, field)
            for field in (
                "workspace_id",
                "product_id",
                "kind",
                "trade_id",
                "execution_id",
            )
        ):
            raise _error(
                "CURRENCY_EVIDENCE_CONFLICT",
                "Der zu ersetzende Nachweis gehört zu einem anderen Quellenumfang.",
            )
        if previous.recorded_at > evidence.recorded_at or await self._repository.has_successor(
            previous.id
        ):
            raise _error(
                "CURRENCY_EVIDENCE_CONFLICT",
                "Der Nachweis wurde bereits geändert. Bitte den aktuellen Stand laden.",
            )

    async def record(
        self,
        *,
        workspace_id: UUID,
        product_id: UUID,
        actor: UUID,
        kind: CurrencyEvidenceKind,
        source_reference: str,
        request_id: UUID,
        supersedes_evidence_id: UUID | None = None,
        revoked: bool = False,
        trade_id: UUID | None = None,
        execution_id: UUID | None = None,
        currency_code: str | None = None,
        trading_venue_id: UUID | None = None,
        valid_from: datetime | None = None,
        valid_to: datetime | None = None,
        listings: tuple[CurrencyListingEvidence, ...] = (),
        complete_listing_set: bool = False,
        now: datetime | None = None,
    ) -> CurrencyEvidence:
        try:
            evidence = CurrencyEvidence(
                id=uuid4(),
                workspace_id=workspace_id,
                product_id=product_id,
                kind=kind,
                source_reference=source_reference,
                recorded_at=now or datetime.now(UTC),
                recorded_by=actor,
                supersedes_evidence_id=supersedes_evidence_id,
                request_id=request_id,
                request_fingerprint="",
                revoked=revoked,
                trade_id=trade_id,
                execution_id=execution_id,
                currency_code=currency_code,
                trading_venue_id=trading_venue_id,
                valid_from=valid_from,
                valid_to=valid_to,
                listings=listings,
                complete_listing_set=complete_listing_set,
            )
        except ValueError as error:
            raise _error("CURRENCY_EVIDENCE_INVALID", str(error), 422) from error
        evidence = replace(evidence, request_fingerprint=evidence_fingerprint(evidence))
        try:
            # Same per-product boundary for corrections, first insert and direct SQL guards.
            await self._product(workspace_id, product_id, lock=True)
            replay = await self._repository.find_request(workspace_id, request_id)
            if replay is not None:
                if replay.request_fingerprint != evidence.request_fingerprint:
                    raise _error(
                        "CURRENCY_EVIDENCE_REQUEST_CONFLICT",
                        "Diese Vorgangskennung gehört zu einem anderen Quellenstand.",
                    )
                await self._session.rollback()  # Release the read lock without a write.
                return replay
            await self._validate_scope(evidence)
            await self._validate_predecessor(evidence)
            await self._repository.add(evidence)
            await self._session.commit()
            return evidence
        except IntegrityError as error:
            await self._session.rollback()
            constraint = getattr(getattr(error.orig, "__cause__", None), "constraint_name", None)
            if constraint == "uq_currency_evidence_request":
                raise _error(
                    "CURRENCY_EVIDENCE_REQUEST_CONFLICT",
                    "Diese Vorgangskennung wurde bereits verwendet.",
                ) from error
            if constraint == "uq_currency_evidence_successor":
                raise _error(
                    "CURRENCY_EVIDENCE_CONFLICT", "Der Nachweis wurde bereits geändert."
                ) from error
            raise
        except Exception:
            await self._session.rollback()
            raise
