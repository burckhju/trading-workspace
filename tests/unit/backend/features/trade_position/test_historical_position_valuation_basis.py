"""Position cost qualification consumes the same immutable currency sources as reports."""

from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from tests.unit.backend.features.trade_position.currency_evidence_fixtures import (
    XETRA,
    document,
    historical,
    listing,
)
from tests.unit.backend.features.trade_position.test_currency_resolution import (
    TRADE,
    confirmed,
    execution,
)

from app.features.trade_position.domain.currency import CurrencyEvidenceReference
from app.features.trade_position.domain.currency_evidence import CurrencyEvidenceLimitExceeded
from app.features.trade_position.service import valuation_basis as module

POSITION = UUID(int=5500)


def owner_snapshot(monkeypatch, facts, *, sources=(), confirmations=()):
    session = object()
    superseded = {fact.supersedes_execution_id for fact in facts}
    records = SimpleNamespace(
        list_for_trade=AsyncMock(return_value=list(facts)),
        list_effective_for_trade=AsyncMock(
            return_value=[fact for fact in facts if fact.id not in superseded]
        ),
    )
    currencies = SimpleNamespace(
        current_for_trade=AsyncMock(
            return_value={confirmation.execution_id: confirmation for confirmation in confirmations}
        )
    )
    evidence = SimpleNamespace(list_for_product=AsyncMock(return_value=tuple(sources)))

    def same_snapshot(repository):
        def create(actual):
            assert actual is session
            return repository

        return create

    for name, repository in (
        ("SqlAlchemyExecutionRecordRepository", records),
        ("SqlAlchemyExecutionCurrencyConfirmationRepository", currencies),
        ("SqlAlchemyCurrencyEvidenceRepository", evidence),
    ):
        monkeypatch.setattr(module, name, same_snapshot(repository))
    return session, records, currencies, evidence


@pytest.mark.asyncio
async def test_historical_eur_buys_qualify_position_basis_and_preserve_typed_source_provenance(
    monkeypatch,
):
    buy, sale = execution(10), execution(11, "SELL")
    source = historical(TRADE)
    before = asdict(source)
    session, records, currencies, evidence = owner_snapshot(
        monkeypatch, (buy, sale), sources=(source,)
    )
    result = await module.read_position_valuation_basis(session, trade=TRADE, position_id=POSITION)
    assert result.currency_status == "KNOWN"
    assert result.cost_basis_currency == "EUR"
    assert result.position.open_quantity == 9
    assert result.position.cost_basis == Decimal("18")
    assert result.position.realized_gross_pnl == Decimal("1")
    assert result.effective_execution_ids == (buy.id, sale.id)
    proof = result.buy_currency_evidence[0]
    assert proof.execution_id == buy.id
    assert proof.source == "HISTORICAL_LISTINGS"
    assert proof.confirmation_ids == ()
    assert proof.evidence_ids == (source.id,)
    assert len(proof.evidence) == 1
    assert isinstance(proof.evidence[0], CurrencyEvidenceReference)
    assert proof.evidence[0].source_reference == source.source_reference
    assert proof.evidence[0].valid_from == source.valid_from
    assert proof.evidence[0].valid_to == source.valid_to
    records.list_for_trade.assert_awaited_once_with(TRADE.id)
    records.list_effective_for_trade.assert_awaited_once_with(TRADE.id)
    currencies.current_for_trade.assert_awaited_once_with(TRADE.workspace_id, TRADE.id)
    evidence.list_for_product.assert_awaited_once_with(TRADE.workspace_id, TRADE.product_id)
    assert asdict(source) == before
    assert buy.currency_confirmation is None


@pytest.mark.asyncio
@pytest.mark.parametrize("today_only", [False, True])
async def test_position_basis_never_qualifies_unproven_past_currency(monkeypatch, today_only):
    facts = (execution(10), execution(11, "SELL"))
    sources = (
        (
            historical(
                TRADE,
                start=datetime(2031, 1, 1, tzinfo=UTC),
                end=datetime(2032, 1, 1, tzinfo=UTC),
            ),
        )
        if today_only
        else ()
    )
    session, *_ = owner_snapshot(monkeypatch, facts, sources=sources)
    result = await module.read_position_valuation_basis(session, trade=TRADE, position_id=POSITION)
    assert result.currency_status == "UNKNOWN"
    assert result.cost_basis_currency is None
    assert result.buy_currency_evidence[0].currency_code is None


@pytest.mark.asyncio
async def test_corrected_buy_own_usd_document_prevents_stale_eur_position_basis(monkeypatch):
    original = execution(10)
    corrected = replace(original, id=UUID(int=20), supersedes_execution_id=original.id)
    sale = execution(11, "SELL")
    receipt = document(TRADE, corrected.id, code="USD")
    session, *_ = owner_snapshot(
        monkeypatch,
        (original, corrected, sale),
        sources=(receipt,),
        confirmations=(confirmed(original),),
    )
    result = await module.read_position_valuation_basis(session, trade=TRADE, position_id=POSITION)
    assert result.currency_status == "KNOWN"
    assert result.cost_basis_currency == "USD"
    assert result.effective_execution_ids == (corrected.id, sale.id)
    assert len(result.buy_currency_evidence) == 1
    proof = result.buy_currency_evidence[0]
    assert proof.execution_id == corrected.id
    assert proof.source == "EXECUTION_DOCUMENT"
    assert proof.evidence_ids == (receipt.id,)
    assert proof.confirmation_ids == ()


@pytest.mark.asyncio
async def test_rebuy_in_different_evidenced_currency_keeps_position_costs_mixed(monkeypatch):
    first, second = execution(10), execution(12)
    session, *_ = owner_snapshot(
        monkeypatch,
        (first, second),
        sources=(historical(TRADE), document(TRADE, second.id, code="USD")),
    )
    result = await module.read_position_valuation_basis(session, trade=TRADE, position_id=POSITION)
    assert result.currency_status == "MIXED"
    assert result.cost_basis_currency is None
    assert [proof.currency_code for proof in result.buy_currency_evidence] == ["EUR", "USD"]


@pytest.mark.asyncio
async def test_position_source_revision_and_revocation_change_basis_without_retired_fallback(
    monkeypatch,
):
    first = historical(TRADE)
    corrected = replace(
        historical(TRADE, 8002, codes=(listing(XETRA, "USD"),)),
        supersedes_evidence_id=first.id,
    )
    revoked = replace(
        corrected,
        id=UUID(int=8003),
        request_id=UUID(int=18003),
        supersedes_evidence_id=corrected.id,
        revoked=True,
    )
    session, _, _, evidence = owner_snapshot(monkeypatch, (execution(10),), sources=(first,))
    original = await module.read_position_valuation_basis(
        session, trade=TRADE, position_id=POSITION
    )
    evidence.list_for_product.return_value = (first, corrected)
    changed = await module.read_position_valuation_basis(session, trade=TRADE, position_id=POSITION)
    evidence.list_for_product.return_value = (first, corrected, revoked)
    withdrawn = await module.read_position_valuation_basis(
        session, trade=TRADE, position_id=POSITION
    )
    assert original.cost_basis_currency == "EUR"
    assert changed.cost_basis_currency == "USD"
    assert withdrawn.cost_basis_currency is None
    assert withdrawn.currency_status == "UNKNOWN"
    assert original.position == changed.position == withdrawn.position
    assert len({original.basis_id, changed.basis_id, withdrawn.basis_id}) == 3


@pytest.mark.asyncio
async def test_position_basis_is_deterministic_for_unchanged_sources_and_source_order(monkeypatch):
    buy = execution(10)
    sources = (historical(TRADE), document(TRADE, buy.id))
    session, _, _, evidence = owner_snapshot(monkeypatch, (buy,), sources=sources)
    first = await module.read_position_valuation_basis(session, trade=TRADE, position_id=POSITION)
    second = await module.read_position_valuation_basis(session, trade=TRADE, position_id=POSITION)
    evidence.list_for_product.return_value = tuple(reversed(sources))
    reordered = await module.read_position_valuation_basis(
        session, trade=TRADE, position_id=POSITION
    )
    assert first == second == reordered


@pytest.mark.asyncio
async def test_no_sources_preserve_exact_main_position_basis_identity(monkeypatch):
    facts = (execution(10), execution(11, "SELL"), execution(12))
    session, *_ = owner_snapshot(monkeypatch, facts, confirmations=(confirmed(facts[0]),))
    result = await module.read_position_valuation_basis(session, trade=TRADE, position_id=POSITION)
    assert result.currency_status == "KNOWN"
    assert result.cost_basis_currency == "EUR"
    # Recorded by running the unchanged reader and its dependencies from Main
    # 1f6ca802df25b2d508338ac837fdfb39ac79eca2 against these exact immutable facts.
    assert result.basis_id == "5e65095a01f39178d77cc43ffd5cd5e66a082dbf797960b664a7a3ba53ceaecf"


@pytest.mark.asyncio
async def test_position_provenance_never_borrows_other_workspace_product_or_trade_sources(
    monkeypatch,
):
    buy = execution(10)
    unrelated = (
        replace(historical(TRADE, 8001), workspace_id=UUID(int=99001)),
        replace(historical(TRADE, 8002), product_id=UUID(int=99002)),
        replace(document(TRADE, buy.id, 9001), trade_id=UUID(int=99003)),
        document(TRADE, UUID(int=99004), 9002),
    )
    session, *_ = owner_snapshot(monkeypatch, (buy,), sources=unrelated)
    result = await module.read_position_valuation_basis(session, trade=TRADE, position_id=POSITION)
    assert result.currency_status == "UNKNOWN"
    assert result.cost_basis_currency is None
    assert result.buy_currency_evidence[0].evidence_ids == ()


@pytest.mark.asyncio
async def test_position_basis_fails_closed_on_incomplete_evidence_read(monkeypatch):
    session, _, _, evidence = owner_snapshot(monkeypatch, (execution(10),))
    evidence.list_for_product.side_effect = CurrencyEvidenceLimitExceeded("complete read refused")
    with pytest.raises(CurrencyEvidenceLimitExceeded):
        await module.read_position_valuation_basis(session, trade=TRADE, position_id=POSITION)


@pytest.mark.asyncio
async def test_malformed_source_revision_never_qualifies_position_cost_currency(monkeypatch):
    buy = execution(10)
    orphan = replace(document(TRADE, buy.id), supersedes_evidence_id=UUID(int=99001))
    session, *_ = owner_snapshot(monkeypatch, (buy,), sources=(orphan,))
    result = await module.read_position_valuation_basis(session, trade=TRADE, position_id=POSITION)
    assert result.currency_status == "UNKNOWN"
    assert result.cost_basis_currency is None
    proof = result.buy_currency_evidence[0]
    assert proof.source == "CONFLICT"
    assert proof.reason == "EVIDENCE_HISTORY_INVALID"
    assert proof.evidence_ids == (orphan.id,)


@pytest.mark.asyncio
async def test_unknown_old_buy_prevents_known_position_basis_from_a_later_historical_source(
    monkeypatch,
):
    first, second = execution(10), execution(12)
    late = historical(TRADE, start=first.executed_at + timedelta(days=1))
    session, *_ = owner_snapshot(monkeypatch, (first, second), sources=(late,))
    result = await module.read_position_valuation_basis(session, trade=TRADE, position_id=POSITION)
    assert result.currency_status == "UNKNOWN"
    assert result.cost_basis_currency is None
    assert [proof.currency_code for proof in result.buy_currency_evidence] == [None, "EUR"]
