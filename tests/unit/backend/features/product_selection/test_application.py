from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.features.market_data.domain.enums import (
    CacheStatus,
    MarketDataCapability,
    MarketDataProvider,
    QualityStatus,
)
from app.features.market_data.domain.models import WarrantQuoteSnapshot
from app.features.market_data.service.types import MarketDataResult
from app.features.product.domain.models import (
    OptionDirection,
    Warrant,
    WarrantLifecycle,
    WarrantListing,
    WarrantTermsVersion,
)
from app.features.product_selection.domain.enums import (
    CriterionOutcome,
    EligibilityStatus,
    MetricOrigin,
)
from app.features.product_selection.domain.models import ModelReference
from app.features.product_selection.service.application import (
    ProductSelectionModels,
    ProductSelectionService,
)
from app.features.product_selection.service.universe import DirectionEligibilityRule
from app.features.trade_plan.domain.enums import (
    EntryType,
    TradeDirection,
    TradePlanOriginType,
    TradePlanStatus,
)
from app.features.trade_plan.domain.models import (
    EntryPlan,
    InvalidationPlan,
    RiskAssumptions,
    Target,
    TradePlan,
    TradePlanVersion,
)

NOW = datetime(2026, 8, 16, 8, 15, tzinfo=UTC)
WORKSPACE = uuid4()
UNDERLYING = uuid4()
PLAN_ID = uuid4()
VERSION_ID = uuid4()
ACTOR = uuid4()
MODEL = ModelReference("FT008", "1.0.0")
MODELS = ProductSelectionModels(MODEL, MODEL, MODEL)


def _plan() -> TradePlan:
    return TradePlan(
        id=PLAN_ID,
        workspace_id=WORKSPACE,
        underlying_id=UNDERLYING,
        origin_type=TradePlanOriginType.MANUAL,
        created_at=NOW - timedelta(days=1),
        created_by=ACTOR,
    )


def _version(status: TradePlanStatus = TradePlanStatus.APPROVED) -> TradePlanVersion:
    return TradePlanVersion(
        id=VERSION_ID,
        trade_plan_id=PLAN_ID,
        version=1,
        direction=TradeDirection.LONG,
        thesis="Test",
        entry=EntryPlan(type=EntryType.PRICE, currency="EUR", price=Decimal("100")),
        invalidation=InvalidationPlan(stop_price=Decimal("95")),
        targets=(Target(sequence=1, price=Decimal("110")),),
        risk_assumptions=RiskAssumptions(thesis_risk="test risk"),
        status=status,
        created_at=NOW - timedelta(days=1),
        created_by=ACTOR,
    )


def _reference_data():
    warrant = Warrant(
        id=uuid4(),
        workspace_id=WORKSPACE,
        issuer_id=uuid4(),
        underlying_id=UNDERLYING,
        display_name="Test Call",
        isin=None,
        wkn=None,
        lifecycle_status=WarrantLifecycle.ACTIVE,
        version=1,
        created_at=NOW - timedelta(days=30),
        updated_at=NOW - timedelta(days=30),
    )
    terms = WarrantTermsVersion(
        id=uuid4(),
        warrant_id=warrant.id,
        version_no=1,
        effective_from=NOW - timedelta(days=30),
        effective_to=None,
        option_direction=OptionDirection.CALL,
        strike=Decimal("100"),
        maturity_date=date(2027, 1, 15),
        ratio=Decimal("0.1"),
        created_at=NOW - timedelta(days=30),
    )
    listing = WarrantListing(
        id=uuid4(),
        workspace_id=WORKSPACE,
        warrant_id=warrant.id,
        trading_venue_id=uuid4(),
        symbol="TEST",
        quotation_currency_code="EUR",
        lifecycle_status=WarrantLifecycle.ACTIVE,
        version=1,
        created_at=NOW - timedelta(days=30),
        updated_at=NOW - timedelta(days=30),
    )
    return warrant, terms, listing


def _service(plan=None, version=None, refs=None, market_data=None):
    trade_plans = AsyncMock()
    products = AsyncMock()
    trade_plans.get_plan.return_value = plan if plan is not None else _plan()
    trade_plans.get_version.return_value = version if version is not None else _version()
    warrant, terms, listing = refs if refs is not None else _reference_data()
    products.warrants_for_underlying.return_value = (warrant,)
    products.terms_for_warrants.return_value = (terms,)
    products.listings_for_warrants.return_value = (listing,)
    return (
        ProductSelectionService(
            trade_plans=trade_plans, products=products, market_data=market_data
        ),
        trade_plans,
        products,
    )


@pytest.mark.asyncio
async def test_start_run_uses_exact_approved_trade_plan_and_underlying() -> None:
    service, trade_plans, products = _service()

    result = await service.start_run(
        workspace_id=WORKSPACE,
        trade_plan_id=PLAN_ID,
        trade_plan_version_id=VERSION_ID,
        actor=ACTOR,
        models=MODELS,
        evaluated_at=NOW,
    )

    assert result.run.trade_plan_version_id == VERSION_ID
    assert result.run.underlying_id == UNDERLYING
    assert result.run.evaluated_at == NOW
    trade_plans.get_plan.assert_awaited_once_with(WORKSPACE, PLAN_ID)
    trade_plans.get_version.assert_awaited_once_with(PLAN_ID, VERSION_ID)
    products.warrants_for_underlying.assert_awaited_once_with(WORKSPACE, UNDERLYING)


@pytest.mark.asyncio
async def test_start_run_rejects_non_approved_version_before_loading_products() -> None:
    service, _, products = _service(version=_version(TradePlanStatus.READY_FOR_REVIEW))

    with pytest.raises(ValueError, match="APPROVED"):
        await service.start_run(
            workspace_id=WORKSPACE,
            trade_plan_id=PLAN_ID,
            trade_plan_version_id=VERSION_ID,
            actor=ACTOR,
            models=MODELS,
            evaluated_at=NOW,
        )

    products.warrants_for_underlying.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_market_data_contract_keeps_reference_pass_not_evaluable() -> None:
    direction = DirectionEligibilityRule(frozenset({OptionDirection.CALL}), "LONG_CALL_V1")
    service, _, _ = _service()

    result = await service.start_run(
        workspace_id=WORKSPACE,
        trade_plan_id=PLAN_ID,
        trade_plan_version_id=VERSION_ID,
        actor=ACTOR,
        models=ProductSelectionModels(MODEL, MODEL, MODEL, direction),
        evaluated_at=NOW,
    )

    evaluation = result.evaluations[0]
    assert evaluation.eligibility_status is EligibilityStatus.NOT_EVALUABLE
    market = next(
        criterion
        for criterion in evaluation.criteria
        if criterion.criterion_id == "warrant-market-data-contract-available"
    )
    assert market.outcome is CriterionOutcome.NOT_EVALUABLE
    assert any(
        item.name == "market_data_snapshot" and item.value is None for item in evaluation.inputs
    )


@pytest.mark.asyncio
async def test_reference_failure_remains_ineligible_even_with_missing_market_data() -> None:
    warrant, terms, listing = _reference_data()
    inactive = WarrantListing(
        id=listing.id,
        workspace_id=listing.workspace_id,
        warrant_id=listing.warrant_id,
        trading_venue_id=listing.trading_venue_id,
        symbol=listing.symbol,
        quotation_currency_code=listing.quotation_currency_code,
        lifecycle_status=WarrantLifecycle.INACTIVE,
        version=listing.version,
        created_at=listing.created_at,
        updated_at=listing.updated_at,
    )
    direction = DirectionEligibilityRule(frozenset({OptionDirection.CALL}), "LONG_CALL_V1")
    service, _, _ = _service(refs=(warrant, terms, inactive))

    result = await service.start_run(
        workspace_id=WORKSPACE,
        trade_plan_id=PLAN_ID,
        trade_plan_version_id=VERSION_ID,
        actor=ACTOR,
        models=ProductSelectionModels(MODEL, MODEL, MODEL, direction),
        evaluated_at=NOW,
    )

    assert result.evaluations[0].eligibility_status is EligibilityStatus.INELIGIBLE
    assert "Reference is inactive" in result.evaluations[0].reasons


@pytest.mark.asyncio
async def test_universe_omission_is_preserved_in_application_result() -> None:
    warrant, _, _ = _reference_data()
    trade_plans = AsyncMock()
    products = AsyncMock()
    trade_plans.get_plan.return_value = _plan()
    trade_plans.get_version.return_value = _version()
    products.warrants_for_underlying.return_value = (warrant,)
    products.terms_for_warrants.return_value = ()
    products.listings_for_warrants.return_value = ()
    service = ProductSelectionService(trade_plans=trade_plans, products=products)

    result = await service.start_run(
        workspace_id=WORKSPACE,
        trade_plan_id=PLAN_ID,
        trade_plan_version_id=VERSION_ID,
        actor=ACTOR,
        models=MODELS,
        evaluated_at=NOW,
    )

    assert result.evaluations == ()
    assert len(result.universe_omissions) == 1
    assert result.universe_omissions[0].warrant_id == warrant.id


def _quote_result(
    listing_id, *, bid=Decimal("1.00"), ask=Decimal("1.04"), quality=QualityStatus.VALID
):
    return MarketDataResult(
        data=WarrantQuoteSnapshot(
            warrant_listing_id=listing_id,
            bid=bid,
            ask=ask,
            currency="EUR",
            provider_symbol="TEST",
            provider_exchange_code="XETR",
            observed_at=NOW - timedelta(seconds=5),
        ),
        provider=MarketDataProvider.EODHD,
        capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
        correlation_id=uuid4(),
        retrieved_at=NOW,
        cache_status=CacheStatus.MISS,
        quality_status=quality,
        warnings=(),
        retry_count=0,
        provider_call_cost=1,
    )


@pytest.mark.asyncio
async def test_complete_valid_quote_turns_reference_pass_into_eligible_evaluation() -> None:
    warrant, terms, listing = _reference_data()
    market_data = AsyncMock()
    market_data.get_warrant_listing_quote.return_value = _quote_result(listing.id)
    direction = DirectionEligibilityRule(frozenset({OptionDirection.CALL}), "LONG_CALL_V1")
    service, _, _ = _service(refs=(warrant, terms, listing), market_data=market_data)

    result = await service.start_run(
        workspace_id=WORKSPACE,
        trade_plan_id=PLAN_ID,
        trade_plan_version_id=VERSION_ID,
        actor=ACTOR,
        models=ProductSelectionModels(MODEL, MODEL, MODEL, direction),
        evaluated_at=NOW,
    )

    evaluation = result.evaluations[0]
    assert evaluation.eligibility_status is EligibilityStatus.ELIGIBLE
    quote = next(
        item
        for item in evaluation.criteria
        if item.criterion_id == "warrant-market-data-contract-available"
    )
    assert quote.outcome is CriterionOutcome.FULFILLED
    assert (
        next(item for item in evaluation.metrics if item.metric_id == "bid").origin
        is MetricOrigin.PROVIDER
    )
    spread = next(item for item in evaluation.metrics if item.metric_id == "spread_absolute")
    assert spread.value == Decimal("0.04")
    assert spread.origin is MetricOrigin.CALCULATED
    request = market_data.get_warrant_listing_quote.await_args.args[0]
    assert request.warrant_listing_id == listing.id
    assert request.as_of == NOW


@pytest.mark.asyncio
async def test_incomplete_quote_quality_stays_not_evaluable_and_keeps_values_visible() -> None:
    warrant, terms, listing = _reference_data()
    market_data = AsyncMock()
    market_data.get_warrant_listing_quote.return_value = _quote_result(
        listing.id, quality=QualityStatus.INCOMPLETE
    )
    direction = DirectionEligibilityRule(frozenset({OptionDirection.CALL}), "LONG_CALL_V1")
    service, _, _ = _service(refs=(warrant, terms, listing), market_data=market_data)

    result = await service.start_run(
        workspace_id=WORKSPACE,
        trade_plan_id=PLAN_ID,
        trade_plan_version_id=VERSION_ID,
        actor=ACTOR,
        models=ProductSelectionModels(MODEL, MODEL, MODEL, direction),
        evaluated_at=NOW,
    )

    evaluation = result.evaluations[0]
    assert evaluation.eligibility_status is EligibilityStatus.NOT_EVALUABLE
    assert next(item for item in evaluation.metrics if item.metric_id == "bid").value == Decimal(
        "1.00"
    )
    assert not any(item.metric_id == "spread_absolute" for item in evaluation.metrics)
    assert any("quality is INCOMPLETE" in reason for reason in evaluation.reasons)


@pytest.mark.asyncio
async def test_reference_ineligible_skips_warrant_quote_provider() -> None:
    warrant, terms, listing = _reference_data()
    inactive = WarrantListing(
        id=listing.id,
        workspace_id=listing.workspace_id,
        warrant_id=listing.warrant_id,
        trading_venue_id=listing.trading_venue_id,
        symbol=listing.symbol,
        quotation_currency_code=listing.quotation_currency_code,
        lifecycle_status=WarrantLifecycle.INACTIVE,
        version=listing.version,
        created_at=listing.created_at,
        updated_at=listing.updated_at,
    )
    market_data = AsyncMock()
    direction = DirectionEligibilityRule(frozenset({OptionDirection.CALL}), "LONG_CALL_V1")
    service, _, _ = _service(refs=(warrant, terms, inactive), market_data=market_data)

    result = await service.start_run(
        workspace_id=WORKSPACE,
        trade_plan_id=PLAN_ID,
        trade_plan_version_id=VERSION_ID,
        actor=ACTOR,
        models=ProductSelectionModels(MODEL, MODEL, MODEL, direction),
        evaluated_at=NOW,
    )

    assert result.evaluations[0].eligibility_status is EligibilityStatus.INELIGIBLE
    market_data.get_warrant_listing_quote.assert_not_awaited()
    quote = next(
        item
        for item in result.evaluations[0].criteria
        if item.criterion_id == "warrant-market-data-contract-available"
    )
    assert quote.outcome is CriterionOutcome.NOT_APPLICABLE
