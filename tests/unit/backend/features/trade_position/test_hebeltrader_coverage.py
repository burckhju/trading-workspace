"""Synthetic financial/identity examples for the pure F207-4 coverage consumer."""

import hashlib
import json
from dataclasses import asdict, replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from app.features.learning.application.hebeltrader_source_reader import (
    ConfirmedHebeltraderSource,
    HebeltraderSourceEvidence,
    SourcePriceMarks,
)
from app.features.trade_position.domain.enums import ExecutionSide, TradeOrigin
from app.features.trade_position.domain.hebeltrader_evidence import (
    EntryOrderEvidence,
    HebeltraderEvidenceDeclaration,
    HebeltraderEvidenceRevision,
    UnderlyingTradeEvidence,
    Z1SaleEvidence,
)
from app.features.trade_position.domain.models import ExecutionRecord, Trade
from app.features.trade_position.domain.price_binding import PriceBasis, PriceBinding
from app.features.trade_position.domain.projector import PositionProjector
from app.features.trade_position.service.hebeltrader_coverage import (
    build_hebeltrader_coverage,
    resolve_execution_reference,
)
from app.features.trade_position.service.valuation_basis import (
    BuyCurrencyEvidence,
    PositionExecutionBasis,
    PositionValuationBasis,
)

NOW = datetime(2026, 11, 14, 10, tzinfo=UTC)
BUY_TIME = datetime(2026, 8, 3, 12, tzinfo=UTC)
TRADE = Trade(UUID(int=1), UUID(int=2), UUID(int=3), TradeOrigin.EXTERNAL, BUY_TIME, UUID(int=4))
POSITION_ID = UUID(int=5)
UNDERLYING_ID = UUID(int=6)
SOURCE_ID = UUID(int=7)
SCALE = "synthetic-original-scale-2026"


def fact(number, *, quantity, price="2", side=ExecutionSide.BUY, after=timedelta(0)):
    return ExecutionRecord(
        id=UUID(int=number),
        trade_id=TRADE.id,
        product_id=TRADE.product_id,
        quantity=quantity,
        price_per_unit=Decimal(price),
        executed_at=BUY_TIME + after,
        recorded_at=NOW - timedelta(days=2),
        recorded_by=TRADE.created_by,
        side=side,
    )


def execution_basis(history, *, trade=TRADE):
    # Supply the explicit repository result in this fixture. The production
    # consumer neither discovers executions nor projects inventory itself.
    superseded = {item.supersedes_execution_id for item in history}
    effective = [item for item in history if item.id not in superseded]
    trace = PositionProjector.project_with_trace(id=POSITION_ID, trade=trade, executions=effective)
    valuation = PositionValuationBasis(
        definition_version="position-unrealized-gross-v1",
        basis_id=hashlib.sha256(
            json.dumps([asdict(item) for item in history], default=str).encode()
        ).hexdigest(),
        position=trace.position,
        cost_basis_currency="EUR",
        currency_status="KNOWN",
        effective_execution_ids=tuple(item.id for item in trace.ordered_executions),
        buy_currency_evidence=tuple(
            BuyCurrencyEvidence(
                item.id, "EUR", "USER_CONFIRMED", (item.id,), (UUID(int=1000 + item.id.int),)
            )
            for item in trace.ordered_executions
            if item.side is ExecutionSide.BUY
        ),
    )
    return PositionExecutionBasis(
        trade, tuple(history), trace.ordered_executions, trace.buy_contributions, valuation
    )


def source():
    return ConfirmedHebeltraderSource(
        source_version_id=SOURCE_ID,
        observation_id=UUID(int=8),
        version=1,
        supersedes_version_id=None,
        currentness="SOURCE_SUPERSEDED",
        product_id=TRADE.product_id,
        underlying_id=UNDERLYING_ID,
        underlying=SourcePriceMarks(
            PriceBinding(PriceBasis.UNDERLYING, UNDERLYING_ID, "USD"),
            Decimal("100"),
            Decimal("110"),
            Decimal("120"),
            Decimal("90"),
            Decimal("95"),
        ),
        product=SourcePriceMarks(
            PriceBinding(PriceBasis.WARRANT, TRADE.product_id, "EUR"),
            Decimal("2"),
            Decimal("3"),
            Decimal("4"),
            Decimal("1"),
            Decimal("1.5"),
        ),
        issue_date=date(2026, 8, 3),
        observed_at=datetime(2026, 8, 3, tzinfo=UTC),
        recorded_at=NOW - timedelta(days=3),
        imported_at=NOW - timedelta(days=3),
        source_name="HEBELTRADER",
        external_reference="synthetic-issue-1",
        import_row_id=UUID(int=9),
        batch_id=UUID(int=10),
        file_id=UUID(int=11),
        filename="synthetic.pdf",
        content_hash="a" * 64,
        accepted_at=NOW - timedelta(days=3),
        accepted_by=TRADE.created_by,
    )


def observation(execution, price):
    return UnderlyingTradeEvidence(
        execution_id=execution.id,
        source_reference=f"Synthetic original last-trade archive for execution {execution.id}",
        price=Decimal(price),
        binding=PriceBinding(PriceBasis.UNDERLYING, UNDERLYING_ID, "USD"),
        scale_reference=SCALE,
        last_trade_verified=True,
        observed_at=execution.executed_at - timedelta(seconds=5),
    )


def revision(declaration):
    return HebeltraderEvidenceRevision(
        id=UUID(int=12),
        workspace_id=TRADE.workspace_id,
        trade_id=TRADE.id,
        position_id=POSITION_ID,
        product_id=TRADE.product_id,
        underlying_id=UNDERLYING_ID,
        declaration=declaration,
        recorded_at=NOW - timedelta(days=1),
        recorded_by=TRADE.created_by,
        request_id=UUID(int=13),
        request_fingerprint="b" * 64,
    )


@pytest.fixture
def case():
    fills = (
        fact(20, quantity=40),
        fact(21, quantity=60, price="2.5", after=timedelta(minutes=2)),
    )
    sale = fact(22, quantity=40, price="3", side=ExecutionSide.SELL, after=timedelta(days=1))
    rebuy = fact(23, quantity=20, price="4", after=timedelta(days=2))
    declaration = HebeltraderEvidenceDeclaration(
        entry_order=EntryOrderEvidence(
            "Synthetic broker order A: both actual partial fills",
            tuple(item.id for item in fills),
            True,
        ),
        source_version_id=SOURCE_ID,
        underlying_trades=(
            observation(fills[0], "100"),
            observation(fills[1], "110"),
            observation(rebuy, "120"),
        ),
        z1_sales=(Z1SaleEvidence(sale.id, "Synthetic actual SELL expressly attributed to Z1"),),
        z1_sales_reviewed=True,
        source_scale_reference=SCALE,
        scale_review_status="UNCHANGED_VERIFIED",
        scale_review_reference="Synthetic reviewed unadjusted instrument/source units",
    )
    return (
        execution_basis([*fills, sale, rebuy]),
        revision(declaration),
        HebeltraderSourceEvidence(SOURCE_ID, source()),
    )


def project(case, *, clock=NOW):
    basis, evidence, publisher = case
    return build_hebeltrader_coverage(
        basis=basis,
        underlying_id=UNDERLYING_ID,
        revision=evidence,
        source_evidence=publisher,
        read_started_at=clock,
        read_completed_at=clock + timedelta(milliseconds=2),
    )


def item(result, key):
    return next(value for value in result.items if value.key == key)


def with_declaration(case, **changes):
    basis, evidence, publisher = case
    return basis, replace(evidence, declaration=replace(evidence.declaration, **changes)), publisher


def test_original_order_fills_stay_100_while_rebuy_updates_owner_costs_and_underlying(case):
    before = tuple(asdict(value) for value in case)
    result = project(case)
    assert result.coverage_status == "COMPLETE"
    assert result.original_z1_quantity == 100
    assert result.assigned_z1_sold_quantity == 40
    assert result.original_underlying_entry == Decimal("106")
    # Old fills retain 24 + 36 units after the sale; the new buy contributes 20.
    assert result.personal_underlying_entry == Decimal("109.5")
    assert result.valuation_basis.position.open_quantity == 80
    assert result.valuation_basis.position.cost_basis == Decimal("218")
    assert result.valuation_basis.position.average_entry_price == Decimal("2.725")
    assert result.valuation_basis.position.opened_at == BUY_TIME
    assert result.underlying_currency == "USD"
    assert result.valuation_basis.cost_basis_currency == "EUR"
    assert result.source.source_version_id == SOURCE_ID
    assert result.source.currentness == "SOURCE_SUPERSEDED"
    assert result.implementation_status == "F207_4_EVIDENCE_ONLY"
    assert result.operation_status == "NOT_ASSESSED"
    assert tuple(asdict(value) for value in case) == before
    assert project(case, clock=NOW + timedelta(days=4)).basis_id == result.basis_id


def test_missing_first_fill_is_not_removed_from_weighting_denominator(case):
    observations = case[1].declaration.underlying_trades[1:]
    result = project(with_declaration(case, underlying_trades=observations))
    assert result.coverage_status == "INCOMPLETE"
    assert result.personal_underlying_entry is None
    assert result.original_underlying_entry is None
    assert result.original_z1_quantity == 100
    assert item(result, f"underlying_trade:{UUID(int=20)}").status == "MISSING"


def test_missing_later_rebuy_preserves_fully_evidenced_original_group_only(case):
    observations = case[1].declaration.underlying_trades[:2]
    result = project(with_declaration(case, underlying_trades=observations))
    assert result.coverage_status == "INCOMPLETE"
    assert result.personal_underlying_entry is None
    assert result.original_underlying_entry == Decimal("106")
    assert result.original_z1_quantity == 100


@pytest.mark.parametrize("missing", [True, False])
def test_no_order_group_is_inferred_from_proximity_or_all_trade_buys(case, missing):
    group = None if missing else replace(case[1].declaration.entry_order, complete=False)
    result = project(with_declaration(case, entry_order=group))
    assert result.original_z1_quantity is None
    assert item(result, "entry_order").status == "MISSING"
    assert result.personal_underlying_entry == Decimal("109.5")


def test_a_later_order_cannot_be_misrepresented_as_original_entry(case):
    group = EntryOrderEvidence("Synthetic separate later order", (UUID(int=23),), True)
    result = project(with_declaration(case, entry_order=group))
    assert result.original_z1_quantity is None
    assert item(result, "entry_order").status == "CONFLICT"


@pytest.mark.parametrize("seconds", [0, -3600, -86400 * 4])
def test_trade_at_or_before_purchase_and_late_recording_has_no_60_second_cutoff(case, seconds):
    observations = list(case[1].declaration.underlying_trades)
    observations[0] = replace(observations[0], observed_at=BUY_TIME + timedelta(seconds=seconds))
    result = project(with_declaration(case, underlying_trades=tuple(observations)))
    assert item(result, f"underlying_trade:{UUID(int=20)}").status == "PRESENT"
    assert result.personal_underlying_entry == Decimal("109.5")
    assert result.evidence_recorded_at > BUY_TIME + timedelta(days=90)


@pytest.mark.parametrize("invalid", ["future_trade", "unverified_last", "same_day_only"])
def test_unsuitable_historical_trade_never_looks_complete(case, invalid):
    observations = list(case[1].declaration.underlying_trades)
    changes = {
        "future_trade": {"observed_at": BUY_TIME + timedelta(microseconds=1)},
        "unverified_last": {"last_trade_verified": False},
        "same_day_only": {
            "observed_at": None,
            "observed_on": BUY_TIME.date(),
            "observation_timezone": "UTC",
        },
    }
    observations[0] = replace(observations[0], **changes[invalid])
    result = project(with_declaration(case, underlying_trades=tuple(observations)))
    assert result.coverage_status == "INCOMPLETE"
    assert item(result, f"underlying_trade:{UUID(int=20)}").status == "UNSUITABLE"
    assert result.personal_underlying_entry is None


def test_date_only_purchase_never_turns_midnight_anchor_into_real_execution_time(case):
    basis, evidence, publisher = case
    original = basis.history[0]
    dated = replace(
        original,
        executed_at=BUY_TIME.replace(hour=0),
        executed_on=BUY_TIME.date(),
        execution_timezone="UTC",
    )
    basis = execution_basis([dated, *basis.history[1:]])
    observation_now = replace(
        evidence.declaration.underlying_trades[0], observed_at=BUY_TIME - timedelta(hours=1)
    )
    evidence = replace(
        evidence,
        declaration=replace(
            evidence.declaration,
            underlying_trades=(observation_now, *evidence.declaration.underlying_trades[1:]),
        ),
    )
    result = project((basis, evidence, publisher))
    assert result.personal_underlying_entry is None
    assert item(result, f"underlying_trade:{dated.id}").status == "UNSUITABLE"
    link = next(
        link
        for link in result.execution_links
        if link.role == "ENTRY_ORDER" and link.original_execution_id == dated.id
    )
    assert link.event_at is None
    assert link.event_on == "2026-08-03"
    assert link.time_precision == "DATE_ONLY"
    assert link.execution_timezone == "UTC"
    assert link.execution_recorded_at == dated.recorded_at


def test_correction_tracks_effective_fill_without_mutating_original_evidence(case):
    basis, evidence, publisher = case
    original = basis.history[0]
    corrected = replace(
        original, id=UUID(int=30), quantity=50, supersedes_execution_id=original.id, recorded_at=NOW
    )
    changed = execution_basis([*basis.history, corrected])
    result = project((changed, evidence, publisher))
    assert result.original_z1_quantity == 110
    assert result.coverage_status == "COMPLETE"
    link = next(
        link
        for link in result.execution_links
        if link.role == "ENTRY_ORDER" and link.original_execution_id == original.id
    )
    assert link.effective_execution_id == corrected.id
    assert link.correction_chain == (original.id, corrected.id)
    assert evidence.declaration.entry_order.execution_ids == (UUID(int=20), UUID(int=21))
    assert basis.history[0].quantity == 40
    assert project(case).original_z1_quantity == 100


def test_changed_execution_time_requires_exact_replacement_observation_link(case):
    basis, evidence, publisher = case
    original = basis.history[0]
    corrected = replace(
        original,
        id=UUID(int=30),
        executed_at=BUY_TIME - timedelta(minutes=10),
        supersedes_execution_id=original.id,
        recorded_at=NOW,
    )
    changed = execution_basis([*basis.history, corrected])
    stale = project((changed, evidence, publisher))
    assert stale.personal_underlying_entry is None
    assert item(stale, f"underlying_trade:{corrected.id}").status == "UNSUITABLE"
    observed = observation(corrected, "100")
    reviewed = replace(
        evidence,
        id=UUID(int=31),
        supersedes_evidence_id=evidence.id,
        declaration=replace(
            evidence.declaration,
            underlying_trades=(observed, *evidence.declaration.underlying_trades[1:]),
        ),
    )
    current = project((changed, reviewed, publisher))
    assert current.coverage_status == "COMPLETE"
    assert current.personal_underlying_entry == Decimal("109.5")
    assert evidence.declaration.underlying_trades[0].execution_id == original.id


def test_two_ancestral_references_cannot_double_count_one_effective_fill(case):
    basis, evidence, publisher = case
    original = basis.history[0]
    corrected = replace(
        original, id=UUID(int=30), supersedes_execution_id=original.id, recorded_at=NOW
    )
    basis = execution_basis([*basis.history, corrected])
    evidence = replace(
        evidence,
        declaration=replace(
            evidence.declaration,
            entry_order=replace(
                evidence.declaration.entry_order,
                execution_ids=(original.id, corrected.id, UUID(int=21)),
            ),
        ),
    )
    result = project((basis, evidence, publisher))
    assert result.original_z1_quantity is None
    assert item(result, "entry_order").status == "CONFLICT"


@pytest.mark.parametrize(
    "field", ["workspace_id", "trade_id", "position_id", "product_id", "underlying_id"]
)
def test_foreign_evidence_scope_is_never_applied(case, field):
    basis, evidence, publisher = case
    result = project((basis, replace(evidence, **{field: UUID(int=999)}), publisher))
    assert result.coverage_status == "CONFLICTED"
    assert item(result, "scope").status == "CONFLICT"
    assert result.evidence_revision_id is None
    assert result.original_z1_quantity is None
    assert result.personal_underlying_entry is None
    assert result.assigned_z1_sold_quantity is None
    assert result.source is None


@pytest.mark.parametrize("field", ["product_id", "underlying_id", "source_version_id"])
def test_wrong_historical_source_identity_or_version_is_not_valid(case, field):
    basis, evidence, publisher = case
    publisher = replace(publisher, source=replace(publisher.source, **{field: UUID(int=999)}))
    result = project((basis, evidence, publisher))
    assert result.coverage_status == "CONFLICTED"
    assert result.source is None
    assert result.personal_underlying_entry is None
    assert item(result, "publisher_source").status == "UNSUITABLE"


@pytest.mark.parametrize("invalid", ["axis", "instrument", "currency", "scale", "adjustment"])
def test_different_price_axes_currencies_scales_never_compare(case, invalid):
    observations = list(case[1].declaration.underlying_trades)
    first = observations[0]
    changes = {
        "axis": {"binding": PriceBinding(PriceBasis.WARRANT, UNDERLYING_ID, "USD")},
        "instrument": {"binding": PriceBinding(PriceBasis.UNDERLYING, UUID(int=999), "USD")},
        "currency": {"binding": PriceBinding(PriceBasis.UNDERLYING, UNDERLYING_ID, "EUR")},
        "scale": {"scale_reference": "synthetic-different-scale"},
        "adjustment": {},
    }
    observations[0] = replace(first, **changes[invalid])
    declaration_changes = {"underlying_trades": tuple(observations)}
    if invalid == "adjustment":
        declaration_changes["scale_review_status"] = "ADJUSTMENT_REQUIRED"
    result = project(with_declaration(case, **declaration_changes))
    assert result.coverage_status != "COMPLETE"
    assert result.personal_underlying_entry is None
    assert item(result, f"underlying_trade:{UUID(int=20)}").status == "UNSUITABLE"
    assert result.valuation_basis.position.cost_basis == Decimal("218")
    assert result.valuation_basis.position.open_quantity == 80


def test_only_explicit_real_sell_attribution_counts_and_50_percent_creates_nothing(case):
    missing = project(with_declaration(case, z1_sales=(), z1_sales_reviewed=False))
    assert missing.assigned_z1_sold_quantity is None
    reviewed_none = project(with_declaration(case, z1_sales=(), z1_sales_reviewed=True))
    assert reviewed_none.assigned_z1_sold_quantity == 0
    result = project(case)
    assert result.original_z1_quantity == 100
    assert result.assigned_z1_sold_quantity == 40
    assert result.valuation_basis.position.open_quantity == 80
    wrong = project(
        with_declaration(
            case, z1_sales=(Z1SaleEvidence(UUID(int=20), "Synthetic incorrect BUY attribution"),)
        )
    )
    assert wrong.assigned_z1_sold_quantity is None
    assert item(wrong, "z1_sales").status == "CONFLICT"


def test_closed_position_keeps_historical_proofs_without_personal_open_entry(case):
    basis, evidence, publisher = case
    close = fact(30, quantity=80, price="5", side=ExecutionSide.SELL, after=timedelta(days=3))
    result = project((execution_basis([*basis.history, close]), evidence, publisher))
    assert result.coverage_status == "INCOMPLETE"
    assert item(result, "executions").status == "UNSUITABLE"
    assert result.original_z1_quantity == 100
    assert result.assigned_z1_sold_quantity == 40
    assert result.original_underlying_entry == Decimal("106")
    assert result.personal_underlying_entry is None
    assert result.valuation_basis.position.open_quantity == 0


def test_missing_owner_remaining_weights_are_visible_not_complete(case):
    basis, evidence, publisher = case
    result = project((replace(basis, buy_contributions=()), evidence, publisher))
    assert result.personal_underlying_entry is None
    assert result.coverage_status != "COMPLETE"
    assert any(value.status != "PRESENT" for value in result.items)


@pytest.mark.parametrize("side", [ExecutionSide.BUY, ExecutionSide.SELL])
def test_reference_correction_never_crosses_side_or_trade_boundaries(case, side):
    basis, _, _ = case
    reference = UUID(int=20) if side is ExecutionSide.BUY else UUID(int=22)
    original = next(value for value in basis.history if value.id == reference)
    replacement = replace(
        original,
        id=UUID(int=30),
        supersedes_execution_id=reference,
        side=ExecutionSide.SELL if side is ExecutionSide.BUY else ExecutionSide.BUY,
    )
    changed = replace(
        basis,
        history=(*basis.history, replacement),
        effective_executions=(
            *(value for value in basis.effective_executions if value.id != reference),
            replacement,
        ),
    )
    value, chain, problem = resolve_execution_reference(changed, reference, side)
    assert value is None and problem is not None
    assert chain == (reference, replacement.id)
    replacement = replace(replacement, side=side, trade_id=UUID(int=999))
    changed = replace(changed, history=(*basis.history, replacement))
    assert resolve_execution_reference(changed, reference, side)[0] is None


def test_missing_source_never_uses_a_current_recommendation_or_execution_price(case):
    basis, evidence, _ = case
    result = project((basis, evidence, None))
    assert result.coverage_status == "INCOMPLETE"
    assert result.source is None
    assert result.underlying_currency is None
    assert result.personal_underlying_entry is None
    assert result.original_underlying_entry is None
    assert result.valuation_basis.position.average_entry_price == Decimal("2.725")


@pytest.mark.parametrize("price", ["0", "-1", "NaN", "Infinity", "-Infinity"])
def test_original_trade_value_must_be_finite_positive(case, price):
    with pytest.raises(ValueError, match="finite and positive"):
        replace(case[1].declaration.underlying_trades[0], price=Decimal(price))


@pytest.mark.parametrize("kind", ["BID", "ASK", "MID", "CLOSE", "DAILY_HIGH"])
def test_another_price_kind_cannot_be_declared_a_historical_underlying_trade(case, kind):
    with pytest.raises(ValueError, match="original trade"):
        replace(case[1].declaration.underlying_trades[0], price_kind=kind)


@pytest.mark.parametrize("invalid", ["missing", "naive", "both"])
def test_original_timestamp_precision_requires_explicit_unambiguous_input(case, invalid):
    changes = {
        "missing": {"observed_at": None},
        "naive": {"observed_at": BUY_TIME.replace(tzinfo=None)},
        "both": {"observed_on": BUY_TIME.date(), "observation_timezone": "UTC"},
    }
    with pytest.raises(ValueError):
        replace(case[1].declaration.underlying_trades[0], **changes[invalid])
