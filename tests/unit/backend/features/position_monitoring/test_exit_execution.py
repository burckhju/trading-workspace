from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from app.features.position_monitoring.domain.exit_execution import (
    DecisionQuote,
    ExitAction,
    ExitDecisionInput,
    ProposedOrderType,
    QuotePurpose,
    evaluate_exit,
)


def _input(*, quote: DecisionQuote, **overrides) -> ExitDecisionInput:
    values = {
        "trade_id": uuid4(),
        "position_id": uuid4(),
        "warrant_id": uuid4(),
        "provenance_listing_id": uuid4(),
        "quote_listing_id": uuid4(),
        "isin": "DE000VH2LU21",
        "wkn": "VH2LU2",
        "position_quantity": 100,
        "broker_available_quantity": 100,
        "expected_currency": "EUR",
        "quote": quote,
        "stop_price": Decimal("0.25"),
        "broker_instrument_identity": "broker-contract-1",
        "broker": "PAPER",
        "idempotency_key": "trade:position:exit:v1",
    }
    values.update(overrides)
    return ExitDecisionInput(**values)


def _quote(*, purpose: QuotePurpose = QuotePurpose.EXECUTABLE) -> DecisionQuote:
    return DecisionQuote(
        purpose=purpose,
        bid=Decimal("0.24"),
        ask=Decimal("0.25"),
        currency="EUR",
        observed_at=datetime(2026, 9, 12, 7, 0, tzinfo=UTC),
        age_seconds=2,
        trading_status="OPEN",
        source_mode="BROKER_EXECUTABLE",
        quote_size=1000,
        venue_mic="XSTU",
        provider="PAPER",
        provider_identity="contract-1",
    )


def test_issuer_indication_can_never_create_order_proposal() -> None:
    decision = evaluate_exit(_input(quote=_quote(purpose=QuotePurpose.DECISION)))

    assert decision.action is ExitAction.BLOCKED
    assert "EXECUTABLE_QUOTE_MISSING" in decision.blocking_gates
    assert decision.proposal is None


def test_missing_quote_size_blocks_even_when_stop_is_hit() -> None:
    quote = _quote()
    quote = DecisionQuote(
        purpose=quote.purpose,
        bid=quote.bid,
        ask=quote.ask,
        currency=quote.currency,
        observed_at=quote.observed_at,
        age_seconds=quote.age_seconds,
        trading_status=quote.trading_status,
        source_mode=quote.source_mode,
        quote_size=None,
        venue_mic=quote.venue_mic,
    )

    decision = evaluate_exit(_input(quote=quote))

    assert decision.action is ExitAction.BLOCKED
    assert "QUOTE_SIZE_MISSING" in decision.blocking_gates
    assert decision.proposal is None


def test_executable_fresh_quote_proposes_manual_limit_exit_without_market_fallback() -> None:
    decision = evaluate_exit(_input(quote=_quote()))

    assert decision.action is ExitAction.EXIT_FULL
    assert decision.triggered_rules == ("STOP_PRICE",)
    assert decision.blocking_gates == ()
    assert decision.proposal is not None
    assert decision.proposal.order_type is ProposedOrderType.LIMIT
    assert decision.proposal.limit_price == Decimal("0.24")
    assert decision.proposal.requires_manual_approval is True


def test_competing_exit_order_blocks_duplicate_proposal() -> None:
    decision = evaluate_exit(_input(quote=_quote(), competing_exit_order=True))

    assert decision.action is ExitAction.BLOCKED
    assert "COMPETING_EXIT_ORDER" in decision.blocking_gates
    assert decision.proposal is None


def test_no_trigger_holds_without_proposal() -> None:
    decision = evaluate_exit(_input(quote=_quote(), stop_price=Decimal("0.20")))

    assert decision.action is ExitAction.HOLD
    assert decision.triggered_rules == ()
    assert decision.proposal is None
