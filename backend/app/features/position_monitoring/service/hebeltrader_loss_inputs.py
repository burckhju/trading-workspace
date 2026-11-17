"""Compose only B04's owner facts; target qualification is never consulted."""

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ApplicationError
from app.features.market_data.domain.risk_evidence import SavedQuoteEvidence
from app.features.market_data.service.risk_read import RiskMarketDataReader
from app.features.market_data.service.session_evidence import SessionEvidenceReader
from app.features.position_monitoring.domain.hebeltrader_original_bid import assess_original_bid
from app.features.position_monitoring.domain.hebeltrader_sessions import SessionEntry
from app.features.position_monitoring.service.hebeltrader_original_bid_sessions import (
    product_sessions,
    underlying_sessions,
)
from app.features.position_monitoring.service.hebeltrader_product_price_scale import (
    product_scale_assessment,
)
from app.features.product.service.application import WarrantService
from app.features.product.service.price_scale_evidence import ProductPriceScaleEvidenceReader
from app.features.trade_position.domain.enums import ExecutionSide
from app.features.trade_position.persistence.repositories import (
    SqlAlchemyPositionRepository,
    SqlAlchemyReadOnlyTradeRepository,
)
from app.features.trade_position.service.valuation_basis import read_position_execution_basis

JSON_VALUE = TypeAdapter(dict[str, Any])


@dataclass(frozen=True, slots=True)
class LossInputs:
    workspace_id: UUID
    trade_id: UUID
    position_id: UUID
    product_id: UUID
    owner_basis_id: str
    closed: bool
    saved: SavedQuoteEvidence
    material: dict[str, Any]
    problems: tuple[str, ...]


async def read_loss_inputs(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    trade_id: UUID,
    position_id: UUID,
    now: datetime,
) -> LossInputs:
    """Caller owns transaction and trade lock; no writes, provider or F207 target read."""
    trade = await SqlAlchemyReadOnlyTradeRepository(session).get(workspace_id, trade_id)
    position = await SqlAlchemyPositionRepository(session).get_for_trade(workspace_id, trade_id)
    if trade is None or position is None or position.id != position_id:
        raise ApplicationError(
            code="B04_POSITION_NOT_FOUND",
            message="Position gehört nicht zum Workspace/Trade.",
            status_code=404,
        )
    basis = await read_position_execution_basis(session, trade=trade, position_id=position_id)
    economic = basis.valuation_basis
    position = economic.position
    closed = position.is_closed or position.is_cancelled or trade.cancelled_at is not None
    warrant = await WarrantService(session).get(workspace_id, trade.product_id)
    if closed:
        material = JSON_VALUE.dump_python(
            {
                "economic_basis": asdict(economic),
                "effective_execution_ids": [str(fact.id) for fact in basis.effective_executions],
                "entry": None,
                "saved_quote": {"route": None, "provenance": None},
                "bid": {"price": None, "original_bid_at": None},
                "product_scale": None,
                "product_sessions": {"calendar": None},
                "underlying_sessions": {
                    "count": None,
                    "calendar": None,
                    "period": {"fingerprint": None},
                },
                "warrant_name": warrant.display_name,
                "warrant_isin": warrant.isin,
                "warrant_wkn": warrant.wkn,
            },
            mode="json",
        )
        return LossInputs(
            workspace_id,
            trade_id,
            position_id,
            trade.product_id,
            economic.basis_id,
            True,
            SavedQuoteEvidence("POSITION_CLOSED_OR_CANCELLED"),
            material,
            (),
        )
    saved = await RiskMarketDataReader(session).saved_quote(
        workspace_id=workspace_id,
        position_id=position_id,
        expected_warrant_id=trade.product_id,
        as_of=now,
    )
    bid = assess_original_bid(saved, evaluated_at=now, applicable=not closed)
    first = next(
        (fact for fact in basis.effective_executions if fact.side == ExecutionSide.BUY), None
    )
    entry = (
        None
        if first is None
        else SessionEntry(
            execution_id=first.id,
            executed_at=first.executed_at if first.executed_on is None else None,
            executed_on=first.executed_on,
            execution_timezone=first.execution_timezone,
            time_precision="EXACT" if first.executed_on is None else "DATE_ONLY",
        )
    )
    calendars = SessionEvidenceReader(session)
    product = await product_sessions(calendars, route=saved.route, bid=bid, now=now)
    underlying = await underlying_sessions(
        calendars,
        workspace_id=workspace_id,
        underlying_id=warrant.underlying_id,
        entry=entry,
        bid=bid,
        now=now,
    )
    scale = product_scale_assessment(
        evidence=await ProductPriceScaleEvidenceReader(session).current(
            workspace_id=workspace_id,
            warrant_id=trade.product_id,
            known_at=now,
        ),
        basis=basis,
        underlying_id=warrant.underlying_id,
        saved=saved,
        bid=bid,
        now=now,
        applicable=not closed,
    )
    problems: list[str] = list(bid.reasons)
    if economic.currency_status != "KNOWN" or economic.cost_basis_currency is None:
        problems.append("EXECUTION_CURRENCY_UNQUALIFIED")
    elif bid.currency != economic.cost_basis_currency:
        problems.append("EXECUTION_BID_CURRENCY_MISMATCH")
    if scale.status != "DOCUMENTED":
        problems.extend(scale.reasons or ("PRODUCT_PRICE_SCALE_UNQUALIFIED",))
    for match in (product.at_bid, product.at_read):
        if match.status != "IN_DOCUMENTED_INTERVAL":
            problems.extend(match.reasons or ("PRODUCT_SESSION_UNQUALIFIED",))
    count = underlying.count
    if count is None or count.status != "AVAILABLE":
        problems.extend(count.reasons if count else ("UNDERLYING_SESSIONS_UNQUALIFIED",))
    # Persist complete actual inputs for later explanation, never reconstruct a
    # prior evaluation or a supposedly sent message from today's last-success.
    material = JSON_VALUE.dump_python(
        {
            "economic_basis": asdict(economic),
            "effective_execution_ids": [str(fact.id) for fact in basis.effective_executions],
            "entry": asdict(entry) if entry else None,
            "saved_quote": asdict(saved),
            "bid": asdict(bid),
            "product_scale": asdict(scale),
            "product_sessions": asdict(product),
            "underlying_sessions": asdict(underlying),
            "warrant_name": warrant.display_name,
            "warrant_isin": warrant.isin,
            "warrant_wkn": warrant.wkn,
        },
        mode="json",
    )
    return LossInputs(
        workspace_id,
        trade_id,
        position_id,
        trade.product_id,
        economic.basis_id,
        closed,
        saved,
        material,
        tuple(dict.fromkeys(problems)),
    )
