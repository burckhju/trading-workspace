"""Deterministic fail-closed exit decisions for held structured products.

This module deliberately stops at an auditable order proposal. It does not contain
any broker transport and therefore cannot submit, modify, or cancel a live order.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class QuotePurpose(StrEnum):
    MONITORING = "MONITORING"
    DECISION = "DECISION"
    EXECUTABLE = "EXECUTABLE"


class ExitAction(StrEnum):
    HOLD = "HOLD"
    EXIT_FULL = "EXIT_FULL"
    EXIT_PARTIAL = "EXIT_PARTIAL"
    BLOCKED = "BLOCKED"


class ProposedOrderType(StrEnum):
    LIMIT = "LIMIT"


@dataclass(frozen=True, slots=True)
class ExitPolicy:
    name: str = "WARRANT_EXIT"
    version: str = "1.0.0"
    max_quote_age_seconds: int = 30
    max_spread_bps: int = 1_000
    max_slippage_bps: int = 250


@dataclass(frozen=True, slots=True)
class DecisionQuote:
    purpose: QuotePurpose
    bid: Decimal | None
    ask: Decimal | None
    currency: str | None
    observed_at: datetime | None
    age_seconds: int | None
    trading_status: str | None
    source_mode: str | None
    quote_size: int | None
    venue_mic: str | None
    provider: str | None = None
    provider_identity: str | None = None


@dataclass(frozen=True, slots=True)
class ExitDecisionInput:
    trade_id: UUID
    position_id: UUID
    warrant_id: UUID
    provenance_listing_id: UUID
    quote_listing_id: UUID | None
    isin: str
    wkn: str | None
    position_quantity: int | None
    broker_available_quantity: int | None
    expected_currency: str
    quote: DecisionQuote | None
    stop_price: Decimal | None = None
    target_price: Decimal | None = None
    dynamic_stop_price: Decimal | None = None
    requested_partial_quantity: int | None = None
    broker_instrument_identity: str | None = None
    broker: str | None = None
    competing_exit_order: bool = False
    risk_limit_breached: bool = False
    instrument_expired: bool = False
    idempotency_key: str | None = None


@dataclass(frozen=True, slots=True)
class OrderProposal:
    quantity: int
    order_type: ProposedOrderType
    limit_price: Decimal
    venue_mic: str
    idempotency_key: str
    requires_manual_approval: bool = True


@dataclass(frozen=True, slots=True)
class ExitDecision:
    policy_name: str
    policy_version: str
    action: ExitAction
    triggered_rules: tuple[str, ...]
    blocking_gates: tuple[str, ...]
    reasons: tuple[str, ...]
    proposal: OrderProposal | None


def evaluate_exit(
    value: ExitDecisionInput,
    *,
    policy: ExitPolicy | None = None,
) -> ExitDecision:
    """Evaluate one position deterministically and fail closed before proposal creation."""

    effective_policy = policy or ExitPolicy()
    blockers: list[str] = []
    quote = value.quote

    if value.position_quantity is None or value.position_quantity <= 0:
        blockers.append("POSITION_QUANTITY_UNKNOWN")
    if value.broker_available_quantity is None:
        blockers.append("BROKER_POSITION_UNKNOWN")
    elif (
        value.position_quantity is not None
        and value.broker_available_quantity < value.position_quantity
    ):
        blockers.append("BROKER_POSITION_INSUFFICIENT")
    if not value.broker_instrument_identity:
        blockers.append("BROKER_INSTRUMENT_IDENTITY_MISSING")
    if value.competing_exit_order:
        blockers.append("COMPETING_EXIT_ORDER")
    if value.risk_limit_breached:
        blockers.append("RISK_LIMIT_BREACHED")
    if value.instrument_expired:
        blockers.append("INSTRUMENT_EXPIRED")
    if not value.idempotency_key:
        blockers.append("IDEMPOTENCY_IDENTITY_MISSING")

    if quote is None:
        blockers.append("QUOTE_MISSING")
    else:
        if quote.purpose is not QuotePurpose.EXECUTABLE:
            blockers.append("EXECUTABLE_QUOTE_MISSING")
        if quote.bid is None:
            blockers.append("BID_MISSING")
        if quote.quote_size is None:
            blockers.append("QUOTE_SIZE_MISSING")
        elif value.position_quantity is not None and quote.quote_size < value.position_quantity:
            blockers.append("LIQUIDITY_INSUFFICIENT")
        if quote.observed_at is None or quote.age_seconds is None:
            blockers.append("QUOTE_TIMESTAMP_MISSING")
        elif quote.age_seconds < 0 or quote.age_seconds > effective_policy.max_quote_age_seconds:
            blockers.append("QUOTE_STALE")
        if quote.trading_status != "OPEN":
            blockers.append("MARKET_NOT_OPEN")
        if quote.currency != value.expected_currency:
            blockers.append("QUOTE_CURRENCY_MISMATCH")
        if not quote.venue_mic:
            blockers.append("EXECUTION_VENUE_MISSING")
        if quote.bid is not None and quote.ask is not None:
            midpoint = (quote.bid + quote.ask) / Decimal("2")
            if midpoint <= 0:
                blockers.append("SPREAD_INVALID")
            else:
                spread_bps = int(((quote.ask - quote.bid) / midpoint) * Decimal("10000"))
                if spread_bps < 0 or spread_bps > effective_policy.max_spread_bps:
                    blockers.append("SPREAD_LIMIT_EXCEEDED")
        else:
            blockers.append("ASK_MISSING")

    if blockers:
        return ExitDecision(
            policy_name=effective_policy.name,
            policy_version=effective_policy.version,
            action=ExitAction.BLOCKED,
            triggered_rules=(),
            blocking_gates=tuple(dict.fromkeys(blockers)),
            reasons=("FAIL_CLOSED_RISK_OR_DATA_GATE",),
            proposal=None,
        )

    assert quote is not None
    assert quote.bid is not None
    assert quote.venue_mic is not None
    assert value.position_quantity is not None
    assert value.idempotency_key is not None

    triggered: list[str] = []
    if value.stop_price is not None and quote.bid <= value.stop_price:
        triggered.append("STOP_PRICE")
    if value.dynamic_stop_price is not None and quote.bid <= value.dynamic_stop_price:
        triggered.append("DYNAMIC_STOP")
    if value.target_price is not None and quote.bid >= value.target_price:
        triggered.append("TARGET_PRICE")

    if not triggered:
        return ExitDecision(
            policy_name=effective_policy.name,
            policy_version=effective_policy.version,
            action=ExitAction.HOLD,
            triggered_rules=(),
            blocking_gates=(),
            reasons=("NO_EXIT_RULE_TRIGGERED",),
            proposal=None,
        )

    quantity = value.position_quantity
    action = ExitAction.EXIT_FULL
    if value.requested_partial_quantity is not None:
        if value.requested_partial_quantity <= 0 or value.requested_partial_quantity > quantity:
            return ExitDecision(
                policy_name=effective_policy.name,
                policy_version=effective_policy.version,
                action=ExitAction.BLOCKED,
                triggered_rules=tuple(triggered),
                blocking_gates=("PARTIAL_QUANTITY_INVALID",),
                reasons=("FAIL_CLOSED_RISK_OR_DATA_GATE",),
                proposal=None,
            )
        if value.requested_partial_quantity < quantity:
            quantity = value.requested_partial_quantity
            action = ExitAction.EXIT_PARTIAL

    # For an exit, the executable bid is the conservative starting limit. The
    # proposal is manual-approval-only; there is intentionally no market fallback.
    proposal = OrderProposal(
        quantity=quantity,
        order_type=ProposedOrderType.LIMIT,
        limit_price=quote.bid,
        venue_mic=quote.venue_mic,
        idempotency_key=value.idempotency_key,
    )
    return ExitDecision(
        policy_name=effective_policy.name,
        policy_version=effective_policy.version,
        action=action,
        triggered_rules=tuple(triggered),
        blocking_gates=(),
        reasons=("EXIT_RULE_TRIGGERED", "MANUAL_APPROVAL_REQUIRED"),
        proposal=proposal,
    )
