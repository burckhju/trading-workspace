"""Currency regressions exercise the real valuation and execution-owner rules.

Persistence and the sole quote boundary are synthetic. No confirmation or
execution is manufactured by a valuation read, and no real provider is called.
"""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from tests.unit.backend.features.position_monitoring.test_product_valuation import (
    NOW,
    _context,
    _Database,
    _Provider,
    _quote_result,
    _Session,
    valuation_module,
)

from app.features.position_monitoring.service.product_valuation import (
    ProductPositionValuationService,
)
from app.features.position_monitoring.service.quote_sources import (
    MultiSourceWarrantQuoteResolver,
    NamedWarrantQuoteSource,
)
from app.features.trade_position.domain.currency import (
    ExecutionCurrencyConfirmation,
    ExecutionCurrencySource,
)
from app.features.trade_position.domain.enums import ExecutionSide
from app.features.trade_position.domain.models import ExecutionRecord
from app.features.trade_position.persistence.currency_evidence import (
    SqlAlchemyCurrencyEvidenceRepository,
)
from app.features.trade_position.persistence.currency_repository import (
    SqlAlchemyExecutionCurrencyConfirmationRepository,
)
from app.features.trade_position.persistence.repositories import SqlAlchemyExecutionRecordRepository


def execution(trade, *, quantity=10, price="2.00", offset=0, side="BUY", replaces=None):
    return ExecutionRecord(
        id=uuid4(),
        trade_id=trade.id,
        product_id=trade.product_id,
        side=ExecutionSide(side),
        quantity=quantity,
        price_per_unit=Decimal(price),
        executed_at=NOW - timedelta(days=10) + timedelta(hours=offset),
        recorded_at=NOW - timedelta(days=1) + timedelta(seconds=offset),
        recorded_by=trade.created_by,
        supersedes_execution_id=replaces,
    )


def confirmation(trade, fact, code):
    return ExecutionCurrencyConfirmation(
        id=uuid4(),
        workspace_id=trade.workspace_id,
        trade_id=trade.id,
        execution_id=fact.id,
        currency_code=code,
        source=ExecutionCurrencySource.USER_CONFIRMED,
        confirmed_at=NOW,
        confirmed_by=trade.created_by,
        note=None,
        supersedes_confirmation_id=None,
        request_id=uuid4(),
        request_fingerprint="synthetic",
    )


def service(
    monkeypatch,
    *,
    bound,
    trade,
    position,
    evaluation,
    listing,
    facts,
    codes,
    quote_mode="current",
    bid="2.50",
):
    superseded = {fact.supersedes_execution_id for fact in facts}
    effective = [fact for fact in facts if fact.id not in superseded]
    current = {
        fact.id: confirmation(trade, fact, code)
        for fact, code in zip(facts, codes, strict=True)
        if code is not None
    }
    monkeypatch.setattr(
        SqlAlchemyExecutionRecordRepository, "list_for_trade", AsyncMock(return_value=facts)
    )
    monkeypatch.setattr(
        SqlAlchemyExecutionRecordRepository,
        "list_effective_for_trade",
        AsyncMock(return_value=effective),
    )
    monkeypatch.setattr(
        SqlAlchemyExecutionCurrencyConfirmationRepository,
        "current_for_trade",
        AsyncMock(return_value=current),
    )
    monkeypatch.setattr(
        SqlAlchemyCurrencyEvidenceRepository,
        "list_for_product",
        AsyncMock(return_value=()),
    )
    result = _quote_result(
        listing_id=listing.id, bid=Decimal(bid), ask=Decimal(bid) + Decimal("0.05")
    )
    if quote_mode == "stale":
        result = replace(result, data=replace(result.data, observed_at=NOW - timedelta(hours=2)))
    elif quote_mode == "last_available":
        result = replace(
            result,
            retrieved_at=datetime(2026, 9, 12, 6, 51, 13, tzinfo=UTC),
            data=replace(
                result.data,
                observed_at=datetime(2026, 9, 11, 19, 59, 13, tzinfo=UTC),
                trading_status="CLOSED",
            ),
        )
    elif quote_mode == "indicative":
        result = replace(
            result,
            data=replace(
                result.data,
                bid=None,
                ask=None,
                reference_price=Decimal(bid),
                reference_price_type="LAST_TRADE",
            ),
        )
    provider = _Provider(result)
    fallback = _Provider(result)
    if bound:
        selection = SimpleNamespace(
            id=uuid4(),
            selection_status="SELECTED",
            selection_reason="UNIQUE_VERIFIED_ROUTE",
            policy_version="POSITION_QUOTE_SOURCE_POLICY_V1",
            warrant_listing_id=listing.id,
            warrant_provider_mapping_id=uuid4(),
            provider="EODHD",
            identity_key="bound-identity",
            mapping_version=1,
        )
        monkeypatch.setattr(
            valuation_module,
            "read_quote_identity",
            AsyncMock(return_value=SimpleNamespace(key="bound-identity")),
        )
        scalars = [selection, listing, SimpleNamespace(id=selection.warrant_provider_mapping_id)]
        if evaluation is not None:
            scalars.append(evaluation)
        session = _Session(trade=trade, position=position, scalars=scalars)
        reader = ProductPositionValuationService(
            database=_Database(session),
            quote_resolver=MultiSourceWarrantQuoteResolver(
                (
                    NamedWarrantQuoteSource("EODHD", provider),
                    NamedWarrantQuoteSource("FALLBACK", fallback),
                )
            ),
        )
    else:
        session = _Session(trade=trade, position=position, evaluation=evaluation, listing=listing)
        reader = ProductPositionValuationService(
            database=_Database(session), quote_provider=provider
        )
    return reader, provider, fallback, current


@pytest.mark.asyncio
@pytest.mark.parametrize("bound", [False, True], ids=["evaluation", "bound_source"])
@pytest.mark.parametrize("quote_mode", ["current", "indicative", "stale", "last_available"])
@pytest.mark.parametrize(
    ("codes", "reason"),
    [
        ([None], "COST_BASIS_CURRENCY_UNKNOWN"),
        (["USD"], "COST_BASIS_CURRENCY_MISMATCH"),
        (["EUR", "USD"], "COST_BASIS_CURRENCY_MIXED"),
        ([None, "EUR"], "COST_BASIS_CURRENCY_UNKNOWN"),
    ],
)
async def test_unproven_costs_never_become_monetary_pnl(
    monkeypatch,
    bound,
    quote_mode,
    codes,
    reason,
):
    trade, position, evaluation, listing = _context()
    facts = [
        execution(trade, quantity=10 // len(codes), offset=index) for index in range(len(codes))
    ]
    reader, provider, fallback, current = service(
        monkeypatch,
        bound=bound,
        trade=trade,
        position=position,
        evaluation=evaluation,
        listing=listing,
        facts=facts,
        codes=codes,
        quote_mode=quote_mode,
    )
    value = await reader.for_trade(trade.id)
    assert value is not None
    assert value.analysis_market_value == Decimal("25.00")
    # The original bug returns +5 EUR at exactly this assertion.
    assert value.analysis_unrealized_gross_pnl is None
    assert value.unrealized_gross_pnl is None
    assert value.analysis_unrealized_pnl_usable is False
    assert value.unrealized_pnl_usable is False
    assert value.analysis_unrealized_pnl_reason == reason
    assert value.unrealized_pnl_reason == reason
    assert value.market_value == (
        Decimal("25.00") if quote_mode in {"current", "last_available"} else None
    )
    assert provider.calls == 1 and fallback.calls == 0
    assert len(current) == sum(code is not None for code in codes)


@pytest.mark.asyncio
@pytest.mark.parametrize("bound", [False, True])
@pytest.mark.parametrize(
    ("bid", "expected"), [("2.50", "5.00"), ("1.50", "-5.00"), ("2.00", "0.00")]
)
async def test_evidenced_same_currency_preserves_positive_negative_and_neutral_pnl(
    monkeypatch,
    bound,
    bid,
    expected,
):
    trade, position, evaluation, listing = _context()
    fact = execution(trade)
    reader, provider, _, current = service(
        monkeypatch,
        bound=bound,
        trade=trade,
        position=position,
        evaluation=evaluation,
        listing=listing,
        facts=[fact],
        codes=["EUR"],
        bid=bid,
    )
    value = await reader.for_trade(trade.id)
    assert value.unrealized_gross_pnl == Decimal(expected)
    assert value.analysis_unrealized_gross_pnl == Decimal(expected)
    assert value.unrealized_pnl_usable and value.analysis_unrealized_pnl_usable
    assert value.position_basis.cost_basis_currency == "EUR"
    assert value.position_basis.effective_execution_ids == (fact.id,)
    proof = value.position_basis.buy_currency_evidence[0]
    assert proof.confirmation_ids == (current[fact.id].id,)
    assert provider.calls == 1


@pytest.mark.asyncio
async def test_additional_buy_partial_sale_and_same_side_correction_share_owner_basis(monkeypatch):
    trade, position, evaluation, listing = _context()
    first = execution(trade, quantity=10)
    sale = execution(trade, quantity=4, price="3", offset=1, side="SELL")
    additional = execution(trade, quantity=4, price="4", offset=2)
    corrected = execution(trade, quantity=4, price="3", offset=2, replaces=additional.id)
    reader, _, _, current = service(
        monkeypatch,
        bound=True,
        trade=trade,
        position=position,
        evaluation=evaluation,
        listing=listing,
        facts=[first, sale, additional, corrected],
        codes=["EUR", "USD", None, None],
        bid="3",
    )
    value = await reader.for_trade(trade.id)
    # The authoritative projection is 6*2 + 4*3 = 24, not the old stored test row's 20.
    assert value.market_value == Decimal("30")
    assert value.unrealized_gross_pnl == Decimal("6")
    assert value.position_basis.position.cost_basis == Decimal("24")
    assert value.position_basis.position.open_quantity == 10
    assert value.position_basis.effective_execution_ids == (first.id, sale.id, corrected.id)
    assert value.position_basis.buy_currency_evidence[-1].confirmation_ids == (
        current[first.id].id,
    )
    assert (
        current[sale.id].id not in value.position_basis.buy_currency_evidence[-1].confirmation_ids
    )


@pytest.mark.asyncio
async def test_replaced_buy_uses_its_confirmed_ancestor_without_retaining_old_costs(monkeypatch):
    trade, position, evaluation, listing = _context()
    original = execution(trade, price="7")
    replacement = execution(trade, price="2", replaces=original.id)
    reader, _, _, current = service(
        monkeypatch,
        bound=False,
        trade=trade,
        position=position,
        evaluation=evaluation,
        listing=listing,
        facts=[original, replacement],
        codes=["EUR", None],
    )
    value = await reader.for_trade(trade.id)
    assert value.unrealized_gross_pnl == Decimal("5")
    proof = value.position_basis.buy_currency_evidence[0]
    assert proof.execution_id == replacement.id
    assert proof.source == "REPLACED_EXECUTION"
    assert proof.source_execution_ids == (original.id,)
    assert proof.confirmation_ids == (current[original.id].id,)
