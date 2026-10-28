"""Execution-owner read basis for monetary qualification of an open position.

The caller supplies one read-only snapshot transaction. Arithmetic and currency
reuse remain owned by the existing projector and resolver; this service only
binds their outputs to the same effective facts and immutable evidence.
"""

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Literal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.trade_position.domain.currency import (
    RESOLVER_VERSION,
    CurrencyEvidenceReference,
    CurrencyResolutionSource,
    ExecutionCurrencyResolution,
)
from app.features.trade_position.domain.currency_resolution import resolve_execution_currencies
from app.features.trade_position.domain.enums import ExecutionSide
from app.features.trade_position.domain.models import Position, Trade
from app.features.trade_position.domain.projector import PositionProjector
from app.features.trade_position.persistence.currency_evidence import (
    SqlAlchemyCurrencyEvidenceRepository,
)
from app.features.trade_position.persistence.currency_repository import (
    SqlAlchemyExecutionCurrencyConfirmationRepository,
)
from app.features.trade_position.persistence.repositories import SqlAlchemyExecutionRecordRepository

POSITION_VALUATION_DEFINITION = "position-unrealized-gross-v1"


@dataclass(frozen=True, slots=True)
class BuyCurrencyEvidence:
    execution_id: UUID
    currency_code: str | None
    source: CurrencyResolutionSource
    source_execution_ids: tuple[UUID, ...]
    confirmation_ids: tuple[UUID, ...]
    evidence_ids: tuple[UUID, ...] = ()
    evidence: tuple[CurrencyEvidenceReference, ...] = ()
    reason: str | None = None
    resolver_version: str = RESOLVER_VERSION


@dataclass(frozen=True, slots=True)
class PositionValuationBasis:
    definition_version: str
    basis_id: str
    position: Position
    cost_basis_currency: str | None
    currency_status: Literal["KNOWN", "UNKNOWN", "MIXED"]
    effective_execution_ids: tuple[UUID, ...]
    buy_currency_evidence: tuple[BuyCurrencyEvidence, ...]


def _buy_evidence(
    execution_id: UUID, resolution: ExecutionCurrencyResolution
) -> BuyCurrencyEvidence:
    # asdict recursively converts the references into dictionaries. Keep the
    # immutable typed references intact for the dataclass-backed API schemas.
    return BuyCurrencyEvidence(
        execution_id=execution_id,
        currency_code=resolution.currency_code,
        source=resolution.source,
        source_execution_ids=resolution.source_execution_ids,
        confirmation_ids=resolution.confirmation_ids,
        evidence_ids=resolution.evidence_ids,
        evidence=resolution.evidence,
        reason=resolution.reason,
        resolver_version=resolution.resolver_version,
    )


def _legacy_currency_material(
    resolution: ExecutionCurrencyResolution | BuyCurrencyEvidence,
) -> dict[str, object]:
    return {
        "currency_code": resolution.currency_code,
        "source": resolution.source,
        "source_execution_ids": resolution.source_execution_ids,
        "confirmation_ids": resolution.confirmation_ids,
    }


async def read_position_valuation_basis(
    session: AsyncSession, *, trade: Trade, position_id: UUID
) -> PositionValuationBasis:
    executions = SqlAlchemyExecutionRecordRepository(session)
    history = await executions.list_for_trade(trade.id)
    effective = await executions.list_effective_for_trade(trade.id)
    confirmations = await SqlAlchemyExecutionCurrencyConfirmationRepository(
        session
    ).current_for_trade(trade.workspace_id, trade.id)
    history_ids = {fact.id for fact in history}
    source_history = await SqlAlchemyCurrencyEvidenceRepository(session).list_for_product(
        trade.workspace_id, trade.product_id
    )
    evidence = tuple(
        sorted(
            (
                item
                for item in source_history
                if item.workspace_id == trade.workspace_id
                and item.product_id == trade.product_id
                and (
                    item.kind == "HISTORICAL_LISTINGS"
                    or (item.trade_id == trade.id and item.execution_id in history_ids)
                )
            ),
            key=lambda item: item.id,
        )
    )
    trace = PositionProjector.project_with_trace(id=position_id, trade=trade, executions=effective)
    resolutions = resolve_execution_currencies(
        trade=trade, executions=history, current=confirmations, evidence=evidence
    )
    buys = tuple(
        _buy_evidence(fact.id, resolutions[fact.id])
        for fact in trace.ordered_executions
        if fact.side is ExecutionSide.BUY
    )
    codes = {buy.currency_code for buy in buys if buy.currency_code is not None}
    status: Literal["KNOWN", "UNKNOWN", "MIXED"]
    if len(codes) > 1 or any(buy.source == "MIXED" for buy in buys):
        status = "MIXED"
    elif not buys or any(buy.currency_code is None for buy in buys):
        status = "UNKNOWN"
    else:
        status = "KNOWN"
    # Audit identities and economic facts both participate. No read clock enters
    # the hash: the same materialized owner facts retain the same basis identity.
    material = {
        "definition_version": POSITION_VALUATION_DEFINITION,
        "trade": asdict(trade),
        "position": asdict(trace.position),
        "history": [
            (
                asdict(fact)
                if evidence
                else asdict(fact)
                | {"currency_resolution": _legacy_currency_material(fact.currency_resolution)}
            )
            for fact in history
        ],
        "effective_execution_ids": [str(fact.id) for fact in trace.ordered_executions],
        "confirmations": [asdict(confirmations[key]) for key in sorted(confirmations)],
        # Preserve the original basis identity when no reviewed sources exist.
        "buy_currency_evidence": [
            {
                "execution_id": buy.execution_id,
                **_legacy_currency_material(buy),
            }
            for buy in buys
        ],
    }
    if evidence:
        material.update(
            resolver_version=RESOLVER_VERSION,
            currency_evidence=[asdict(item) for item in evidence],
            buy_currency_evidence=[asdict(buy) for buy in buys],
        )
    return PositionValuationBasis(
        definition_version=POSITION_VALUATION_DEFINITION,
        basis_id=hashlib.sha256(
            json.dumps(material, sort_keys=True, default=str, separators=(",", ":")).encode()
        ).hexdigest(),
        position=trace.position,
        cost_basis_currency=next(iter(codes)) if status == "KNOWN" else None,
        currency_status=status,
        effective_execution_ids=tuple(fact.id for fact in trace.ordered_executions),
        buy_currency_evidence=buys,
    )
