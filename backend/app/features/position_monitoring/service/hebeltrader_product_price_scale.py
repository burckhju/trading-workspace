"""Bind the Product read to the exact existing Trade Position projection."""

from datetime import UTC, datetime
from uuid import UUID

from app.features.market_data.domain.risk_evidence import SavedQuoteEvidence
from app.features.position_monitoring.domain.hebeltrader_original_bid import OriginalBidAssessment
from app.features.position_monitoring.domain.hebeltrader_product_price_scale import (
    ProductPriceScaleAssessment,
    PurchaseScaleInput,
    assess_product_price_scale,
)
from app.features.position_monitoring.service.hebeltrader_original_bid_sessions import (
    inconsistent_read,
)
from app.features.product.domain.price_scale_evidence import ProductPriceScaleCurrent
from app.features.trade_position.domain.enums import ExecutionSide
from app.features.trade_position.service.valuation_basis import PositionExecutionBasis


def product_scale_assessment(
    *,
    evidence: ProductPriceScaleCurrent,
    basis: PositionExecutionBasis,
    underlying_id: UUID,
    saved: SavedQuoteEvidence,
    bid: OriginalBidAssessment,
    now: datetime,
    applicable: bool,
) -> ProductPriceScaleAssessment:
    economic = basis.valuation_basis
    trade = basis.trade
    # A concurrent writer may commit between the server clock and the first
    # snapshot SELECT. Never filter/reproject those newer owner facts to invent
    # an earlier basis. The caller can repeat this passive read instead.
    knowledge_clocks = [trade.created_at]
    if trade.cancelled_at is not None:
        knowledge_clocks.append(trade.cancelled_at)
    for fact in basis.history:
        knowledge_clocks.append(fact.recorded_at)
        if fact.currency_confirmation is not None:
            knowledge_clocks.append(fact.currency_confirmation.confirmed_at)
        knowledge_clocks.extend(item.recorded_at for item in fact.currency_resolution.evidence)
    knowledge_clocks.extend(
        item.recorded_at for buy in economic.buy_currency_evidence for item in buy.evidence
    )
    if now.utcoffset() is None or any(
        clock.utcoffset() is None or clock.astimezone(UTC) > now.astimezone(UTC)
        for clock in knowledge_clocks
    ):
        raise inconsistent_read()
    if (
        evidence.workspace_id != trade.workspace_id
        or evidence.warrant_id != trade.product_id
        or evidence.known_at != now
        or evidence.read_at < now
        or (evidence.recorded_at is not None and evidence.recorded_at > now)
        or (
            evidence.binding is not None
            and (
                evidence.binding.warrant_id != trade.product_id
                or (
                    evidence.status == "AVAILABLE"
                    and evidence.binding.underlying_id != underlying_id
                )
            )
        )
    ):
        raise inconsistent_read()
    facts = basis.effective_executions
    if (
        tuple(fact.id for fact in facts) != economic.effective_execution_ids
        or len({fact.id for fact in facts}) != len(facts)
        or any(fact.trade_id != trade.id or fact.product_id != trade.product_id for fact in facts)
    ):
        raise inconsistent_read()
    buys = tuple(fact for fact in facts if fact.side == ExecutionSide.BUY)
    contributions = {item.execution_id: item for item in basis.buy_contributions}
    currencies = {item.execution_id: item for item in economic.buy_currency_evidence}
    if (
        len(contributions) != len(basis.buy_contributions)
        or len(currencies) != len(economic.buy_currency_evidence)
        or set(contributions) != {fact.id for fact in buys}
        or set(currencies) != set(contributions)
        or any(contributions[fact.id].original_quantity != fact.quantity for fact in buys)
    ):
        raise inconsistent_read()
    purchases = tuple(
        PurchaseScaleInput(
            execution_id=fact.id,
            supersedes_execution_id=fact.supersedes_execution_id,
            original_quantity=contributions[fact.id].original_quantity,
            remaining_quantity=contributions[fact.id].remaining_quantity,
            price_per_unit=fact.price_per_unit,
            executed_at=fact.executed_at,
            executed_on=fact.executed_on,
            execution_timezone=fact.execution_timezone,
            recorded_at=fact.recorded_at,
            currency_code=currencies[fact.id].currency_code,
        )
        for fact in buys
    )
    original = saved.quote.original_evidence if saved.quote is not None else None
    return assess_product_price_scale(
        evidence=evidence,
        execution_basis_id=economic.basis_id,
        purchases=purchases,
        bid_at=bid.original_bid_at,
        bid_currency=bid.currency,
        bid_isin=original.isin if original else None,
        bid_available=bid.status == "AVAILABLE",
        applicable=applicable,
    )
