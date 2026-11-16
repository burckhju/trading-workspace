"""One original product period must cover every owner contribution and the BID."""

from copy import deepcopy
from dataclasses import asdict, replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest
from tests.unit.backend.features.position_monitoring import test_hebeltrader_original_bid as bids
from tests.unit.backend.features.trade_position import test_hebeltrader_coverage as executions

from app.core.exceptions import ApplicationError
from app.features.position_monitoring.domain.hebeltrader_original_bid import assess_original_bid
from app.features.position_monitoring.domain.hebeltrader_product_price_scale import (
    PurchaseScaleInput,
    assess_product_price_scale,
)
from app.features.position_monitoring.service.hebeltrader_product_price_scale import (
    product_scale_assessment,
)
from app.features.product.domain.price_scale_evidence import (
    ProductPriceScaleBinding,
    ProductPriceScaleCurrent,
    ProductPriceScaleManifest,
    ProductPriceScaleSource,
)
from app.features.trade_position.domain.currency import (
    CurrencyEvidenceReference,
    ExecutionCurrencyConfirmation,
    ExecutionCurrencySource,
)
from app.features.trade_position.domain.enums import ExecutionSide

case = executions.case
NOW = bids.NOW


def scale_evidence(*, missing=False):
    binding = ProductPriceScaleBinding(
        executions.TRADE.product_id,
        bids.ISIN,
        UUID(int=9300),
        executions.UNDERLYING_ID,
        UUID(int=9301),
    )
    manifest = ProductPriceScaleManifest(
        scale_id="synthetic-original-warrant-unit",
        source_version="synthetic-document-v1",
        binding=binding,
        axis="WARRANT",
        currency="EUR",
        unit="CURRENCY_PER_WARRANT",
        valid_from=executions.BUY_TIME - timedelta(days=1),
        valid_until=NOW + timedelta(days=1),
        status="UNCHANGED_ORIGINAL",
        source_publisher="Synthetic product source",
        source_reference="https://example.invalid/synthetic-original-product",
        source_document_sha256="a" * 64,
        source_published_on=executions.BUY_TIME.date(),
    )
    source = ProductPriceScaleSource(
        manifest_sha256="b" * 64,
        document_sha256="a" * 64,
        document_filename="synthetic-product-original.txt",
        document_media_type="text/plain",
        publisher=manifest.source_publisher,
        reference=manifest.source_reference,
        published_at=None,
        published_on=manifest.source_published_on,
        retrieved_at=NOW - timedelta(days=2),
        reviewed_at=NOW - timedelta(days=1),
        review_reference="Synthetic exact unit/period original-document review",
        recorded_by=executions.TRADE.created_by,
    )
    return ProductPriceScaleCurrent(
        workspace_id=executions.TRADE.workspace_id,
        warrant_id=executions.TRADE.product_id,
        known_at=NOW,
        revision_id=None if missing else UUID(int=9302),
        supersedes_revision_id=None,
        revision_number=None if missing else 1,
        manifest=None if missing else manifest,
        binding=None if missing else binding,
        source=None if missing else source,
        recorded_at=None if missing else NOW - timedelta(hours=1),
        read_at=NOW,
        status="MISSING" if missing else "AVAILABLE",
        reasons=("PRODUCT_PRICE_SCALE_EVIDENCE_MISSING",) if missing else (),
        fingerprint="c" * 64,
    )


def purchase(**changes):
    return replace(
        PurchaseScaleInput(
            execution_id=UUID(int=20),
            supersedes_execution_id=None,
            original_quantity=100,
            remaining_quantity=Decimal(60),
            price_per_unit=Decimal("2"),
            executed_at=executions.BUY_TIME,
            executed_on=None,
            execution_timezone=None,
            recorded_at=NOW - timedelta(days=2),
            currency_code="EUR",
        ),
        **changes,
    )


def evaluate(*, evidence=None, purchases=None, **changes):
    return assess_product_price_scale(
        **dict(
            evidence=evidence or scale_evidence(),
            execution_basis_id="d" * 64,
            purchases=(purchase(),) if purchases is None else purchases,
            bid_at=NOW - timedelta(seconds=60),
            bid_currency="EUR",
            bid_isin=bids.ISIN,
            bid_available=True,
            applicable=True,
        )
        | changes
    )


def compose(basis, *, evidence=None, **changes):
    saved = bids.saved_example()
    return product_scale_assessment(
        **dict(
            evidence=evidence or scale_evidence(),
            basis=basis,
            underlying_id=executions.UNDERLYING_ID,
            saved=saved,
            bid=assess_original_bid(saved, evaluated_at=NOW, applicable=True),
            now=NOW,
            applicable=True,
        )
        | changes
    )


def test_partial_sale_and_rebuy_use_exact_owner_weights_and_do_not_reproject_costs(case):
    basis = case[0]
    before = deepcopy(asdict(basis))
    result = compose(basis)
    assert result.status == "DOCUMENTED"
    assert result.bid_status == "COVERED"
    assert [row.remaining_quantity for row in result.purchases] == [
        Decimal(24),
        Decimal(36),
        Decimal(20),
    ]
    assert [row.original_quantity for row in result.purchases] == [40, 60, 20]
    assert result.execution_basis_id == basis.valuation_basis.basis_id
    assert result.adjustment_applied is False
    assert basis.valuation_basis.position.average_entry_price == Decimal("2.725")
    assert basis.valuation_basis.position.cost_basis == Decimal("218")
    assert asdict(basis) == before
    assert result.evidence.verification == "MANUAL_DOCUMENT_REVIEW_NOT_INDEPENDENT_VERIFICATION"


def test_one_uncovered_fill_is_not_removed_from_denominator_or_contributions(case):
    evidence = scale_evidence()
    evidence = replace(
        evidence,
        manifest=replace(evidence.manifest, valid_from=executions.BUY_TIME + timedelta(minutes=1)),
    )
    result = compose(case[0], evidence=evidence)
    assert result.status == "MISSING"
    assert [row.status for row in result.purchases] == ["MISSING", "COVERED", "COVERED"]
    assert result.purchases[0].remaining_quantity == Decimal(24)
    assert "PRODUCT_SCALE_BUY_OUTSIDE_DOCUMENTED_PERIOD" in result.reasons


def test_later_buy_outside_original_document_never_extends_its_validity(case):
    evidence = scale_evidence()
    evidence = replace(
        evidence,
        manifest=replace(evidence.manifest, valid_until=executions.BUY_TIME + timedelta(days=2)),
    )
    result = compose(case[0], evidence=evidence)
    assert [row.status for row in result.purchases] == ["COVERED", "COVERED", "MISSING"]
    assert result.bid_status == "MISSING"
    assert result.status == "MISSING"


@pytest.mark.parametrize("changed_time", [False, True])
def test_correction_rebinds_exact_effective_buy_and_preserves_original_facts(case, changed_time):
    old = case[0]
    first = old.effective_executions[0]
    corrected = replace(
        first,
        id=UUID(int=9400),
        supersedes_execution_id=first.id,
        price_per_unit=Decimal("3"),
        executed_at=first.executed_at - (timedelta(days=2) if changed_time else timedelta(0)),
    )
    basis = executions.execution_basis([*old.history, corrected])
    result = compose(basis)
    assert result.status == ("MISSING" if changed_time else "DOCUMENTED")
    assert result.execution_basis_id != old.valuation_basis.basis_id
    corrected_row = next(row for row in result.purchases if row.execution_id == corrected.id)
    assert corrected_row.supersedes_execution_id == first.id
    assert corrected_row.price_per_unit == Decimal("3")
    assert first.id not in {row.execution_id for row in result.purchases}
    assert first in basis.history
    assert old.history[0] == first


@pytest.mark.parametrize("day", [date(2026, 3, 29), date(2026, 10, 25)])
def test_date_only_covers_entire_real_local_day_including_dst(day):
    zone = ZoneInfo("Europe/Berlin")
    start = datetime(day.year, day.month, day.day, tzinfo=zone)
    end = datetime.combine(day + timedelta(days=1), datetime.min.time(), zone)
    evidence = scale_evidence()
    evidence = replace(
        evidence,
        manifest=replace(evidence.manifest, valid_from=start, valid_until=NOW + timedelta(days=1)),
    )
    item = purchase(executed_at=start, executed_on=day, execution_timezone="Europe/Berlin")
    result = evaluate(evidence=evidence, purchases=(item,))
    row = result.purchases[0]
    assert row.status == "COVERED"
    assert row.executed_at is None
    assert row.possible_from == start.astimezone(UTC)
    assert row.possible_until == end.astimezone(UTC)
    assert (row.possible_until - row.possible_from).total_seconds() in {23 * 3600, 25 * 3600}
    after_midnight = replace(
        evidence,
        manifest=replace(
            evidence.manifest, valid_from=start.astimezone(UTC) + timedelta(seconds=1)
        ),
    )
    assert evaluate(evidence=after_midnight, purchases=(item,)).purchases[0].status == "MISSING"


def test_date_only_end_boundary_must_cover_whole_day_without_inventing_execution_time():
    day = date(2026, 8, 3)
    item = purchase(
        executed_at=datetime(2026, 8, 3, tzinfo=UTC), executed_on=day, execution_timezone="UTC"
    )
    evidence = scale_evidence()
    evidence = replace(
        evidence,
        manifest=replace(
            evidence.manifest,
            valid_from=item.executed_at,
            valid_until=item.executed_at + timedelta(hours=23),
        ),
    )
    result = evaluate(evidence=evidence, purchases=(item,))
    assert result.purchases[0].status == "MISSING"
    assert result.purchases[0].executed_at is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("executed_at", datetime(2026, 8, 3)),
        ("execution_timezone", "Europe/Berlin"),
        ("executed_on", date(2026, 8, 3)),
    ],
)
def test_unknown_or_inconsistent_time_does_not_supply_a_usable_purchase(field, value):
    result = evaluate(purchases=(purchase(**{field: value}),))
    assert result.status == "UNSUITABLE"
    assert result.purchases[0].reasons == ("PRODUCT_SCALE_BUY_TIME_UNSUITABLE",)


@pytest.mark.parametrize("zone", ["not/a/zone", "Pacific/Apia"])
def test_invalid_zone_or_skipped_date_is_not_assumed_to_be_a_regular_day(zone):
    day = date(2011, 12, 30)
    item = purchase(
        executed_at=datetime(2011, 12, 30, tzinfo=UTC), executed_on=day, execution_timezone=zone
    )
    result = evaluate(purchases=(item,))
    assert result.status == "UNSUITABLE"


@pytest.mark.parametrize("offset,expected", [(0, "COVERED"), (-1, "MISSING")])
def test_time_precise_purchase_lower_bound_is_inclusive(offset, expected):
    evidence = scale_evidence()
    item = purchase(executed_at=evidence.manifest.valid_from + timedelta(microseconds=offset))
    assert evaluate(purchases=(item,)).purchases[0].status == expected


@pytest.mark.parametrize("offset,expected", [(-1, "COVERED"), (0, "MISSING")])
def test_bid_upper_bound_is_exclusive(offset, expected):
    evidence = scale_evidence()
    result = evaluate(bid_at=evidence.manifest.valid_until + timedelta(microseconds=offset))
    assert result.bid_status == expected


@pytest.mark.parametrize("currency,status", [(None, "MISSING"), ("USD", "UNSUITABLE")])
def test_buy_currency_requires_actual_owner_fact(currency, status):
    result = evaluate(purchases=(purchase(currency_code=currency),))
    assert result.status == status
    assert result.bid_status == "COVERED"


@pytest.mark.parametrize("changes", [dict(bid_currency="USD"), dict(bid_isin="DE0000000001")])
def test_same_price_different_currency_or_product_is_not_comparable(changes):
    result = evaluate(**changes)
    assert result.status == "UNSUITABLE"
    assert result.bid_reasons == ("PRODUCT_SCALE_BID_BINDING_MISMATCH",)


@pytest.mark.parametrize("changes", [dict(bid_available=False), dict(bid_at=None)])
def test_missing_original_bid_never_uses_receipt_or_ask_time(changes):
    result = evaluate(**changes)
    assert result.status == "MISSING"
    assert result.bid_reasons == ("PRODUCT_SCALE_QUALIFIED_BID_MISSING",)


@pytest.mark.parametrize(
    "status,reason",
    [
        ("WITHDRAWN", "PRODUCT_PRICE_SCALE_WITHDRAWN"),
        ("ADJUSTMENT_REQUIRED", "PRODUCT_PRICE_SCALE_ADJUSTMENT_REQUIRED"),
    ],
)
def test_withdrawn_or_adjusted_original_is_retained_and_never_normalized(status, reason):
    evidence = scale_evidence()
    evidence = replace(
        evidence,
        status="UNSUITABLE",
        reasons=(reason,),
        manifest=replace(evidence.manifest, status=status),
    )
    result = evaluate(evidence=evidence)
    assert result.status == "UNSUITABLE"
    assert result.evidence is evidence
    assert result.adjustment_applied is False
    assert result.purchases[0].remaining_quantity == Decimal(60)
    assert result.purchases[0].price_per_unit == Decimal("2")


def test_underlying_source_qualification_or_same_terms_without_product_proof_does_not_suffice(case):
    assert case[1].declaration.scale_review_status == "UNCHANGED_VERIFIED"
    assert compose(case[0], evidence=scale_evidence(missing=True)).status == "MISSING"


def test_closed_or_cancelled_keeps_source_and_original_facts_but_no_current_claim(case):
    result = compose(case[0], applicable=False)
    assert result.status == "NOT_APPLICABLE"
    assert result.bid_status == "NOT_APPLICABLE"
    assert all(row.status == "NOT_APPLICABLE" for row in result.purchases)
    assert result.evidence.manifest is not None


def test_no_remaining_buy_is_not_silently_a_documented_open_position():
    assert evaluate(purchases=()).status == "MISSING"
    assert evaluate(purchases=(purchase(remaining_quantity=Decimal(0)),)).status == "MISSING"


@pytest.mark.parametrize("quantity", [Decimal(-1), Decimal(101), Decimal("NaN")])
def test_invalid_owner_contribution_is_integrity_error(quantity):
    with pytest.raises(ValueError, match="contributions"):
        evaluate(purchases=(purchase(remaining_quantity=quantity),))


@pytest.mark.parametrize(
    "field", ["workspace_id", "warrant_id", "known_at", "read_at", "recorded_at"]
)
def test_owner_scope_or_snapshot_mismatch_is_not_missing_evidence(case, field):
    value = UUID(int=99999) if field.endswith("_id") else NOW + timedelta(seconds=1)
    if field == "read_at":
        value = NOW - timedelta(seconds=1)
    with pytest.raises(ApplicationError) as error:
        compose(case[0], evidence=replace(scale_evidence(), **{field: value}))
    assert error.value.code == "HEBELTRADER_ORIGINAL_BID_READ_INCONSISTENT"


def test_changed_old_underlying_binding_remains_readable_as_unsuitable(case):
    evidence = scale_evidence()
    binding = replace(evidence.binding, underlying_id=UUID(int=999))
    evidence = replace(
        evidence,
        status="UNSUITABLE",
        reasons=("PRODUCT_PRICE_SCALE_BINDING_CHANGED",),
        binding=binding,
        manifest=replace(evidence.manifest, binding=binding),
    )
    result = compose(case[0], evidence=evidence)
    assert result.status == "UNSUITABLE"
    assert result.evidence.binding == binding
    with pytest.raises(ApplicationError):
        compose(case[0], evidence=replace(evidence, status="AVAILABLE", reasons=()))


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_buy",
        "duplicate_contribution",
        "wrong_quantity",
        "currency_missing",
        "wrong_execution_scope",
        "wrong_effective_ids",
    ],
)
def test_inconsistent_economic_owner_is_not_repaired_by_scale_consumer(case, mutation):
    basis = case[0]
    if mutation == "missing_buy":
        basis = replace(basis, buy_contributions=basis.buy_contributions[1:])
    elif mutation == "duplicate_contribution":
        basis = replace(
            basis, buy_contributions=(*basis.buy_contributions, basis.buy_contributions[0])
        )
    elif mutation == "wrong_quantity":
        basis = replace(
            basis,
            buy_contributions=(
                replace(basis.buy_contributions[0], original_quantity=999),
                *basis.buy_contributions[1:],
            ),
        )
    elif mutation == "currency_missing":
        basis = replace(
            basis,
            valuation_basis=replace(
                basis.valuation_basis,
                buy_currency_evidence=basis.valuation_basis.buy_currency_evidence[1:],
            ),
        )
    elif mutation == "wrong_execution_scope":
        basis = replace(
            basis,
            effective_executions=(
                replace(basis.effective_executions[0], product_id=UUID(int=999)),
                *basis.effective_executions[1:],
            ),
        )
    else:
        basis = replace(
            basis, valuation_basis=replace(basis.valuation_basis, effective_execution_ids=())
        )
    with pytest.raises(ApplicationError):
        compose(basis)


def test_actual_full_sale_uses_zero_owner_contributions_instead_of_fabricated_buy_weight(case):
    basis = case[0]
    sale = executions.fact(9450, quantity=80, side=ExecutionSide.SELL, after=timedelta(days=3))
    closed = executions.execution_basis([*basis.history, sale])
    result = compose(closed, applicable=False)
    assert all(row.remaining_quantity == 0 for row in result.purchases)
    assert result.status == "NOT_APPLICABLE"


@pytest.mark.parametrize("kind", ["execution", "confirmation", "resolved_source"])
@pytest.mark.parametrize("after_read", [False, True])
def test_later_recording_cannot_enter_an_earlier_common_knowledge_basis(case, kind, after_read):
    basis = case[0]
    instant = NOW + (timedelta(microseconds=1) if after_read else timedelta(0))
    fact = basis.history[0]
    if kind == "execution":
        fact = replace(fact, recorded_at=instant)
    elif kind == "confirmation":
        fact = replace(
            fact,
            currency_confirmation=ExecutionCurrencyConfirmation(
                UUID(int=9500),
                basis.trade.workspace_id,
                basis.trade.id,
                fact.id,
                "EUR",
                ExecutionCurrencySource.USER_CONFIRMED,
                None,
                instant,
                basis.trade.created_by,
                None,
                UUID(int=9501),
                "e" * 64,
            ),
        )
    else:
        reference = CurrencyEvidenceReference(
            UUID(int=9502),
            "EXECUTION_DOCUMENT",
            "Synthetic original currency review",
            instant,
            None,
            None,
            "f" * 64,
        )
        fact = replace(
            fact, currency_resolution=replace(fact.currency_resolution, evidence=(reference,))
        )
    changed = replace(basis, history=(fact, *basis.history[1:]))
    if after_read:
        with pytest.raises(ApplicationError) as error:
            compose(changed)
        assert error.value.code == "HEBELTRADER_ORIGINAL_BID_READ_INCONSISTENT"
    else:
        assert compose(changed).status == "DOCUMENTED"
