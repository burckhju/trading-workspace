from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
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
from app.features.product_selection.domain.enums import EligibilityStatus
from app.features.product_selection.domain.models import ModelReference, ProductSelection
from app.features.product_selection.service.application import (
    ProductSelectionModels,
    ProductSelectionService,
)
from app.features.product_selection.service.persistence import ProductSelectionPersistenceService
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


class SelectionUow:
    def __init__(self) -> None:
        self.runs = SimpleNamespace(add=AsyncMock())
        self.evaluations = SimpleNamespace(add=AsyncMock())
        self.omissions = SimpleNamespace(add_all=AsyncMock())
        self.selections = SimpleNamespace(add=AsyncMock())
        self.flush = AsyncMock()
        self.commit = AsyncMock()
        self.rollback = AsyncMock()

    async def __aenter__(self) -> SelectionUow:
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        if exc_type is not None:
            await self.rollback()


@pytest.mark.asyncio
async def test_approved_trade_plan_handoff_pins_run_and_explicit_selection_provenance() -> None:
    now = datetime(2026, 8, 27, 10, 15, tzinfo=UTC)
    workspace_id = uuid4()
    underlying_id = uuid4()
    candidate_id = uuid4()
    candidate_evaluation_id = uuid4()
    actor = uuid4()
    plan_id = uuid4()
    version_id = uuid4()

    plan = TradePlan(
        id=plan_id,
        workspace_id=workspace_id,
        underlying_id=underlying_id,
        origin_type=TradePlanOriginType.CANDIDATE_EVALUATION,
        created_at=now - timedelta(days=1),
        created_by=actor,
        candidate_id=candidate_id,
        candidate_evaluation_id=candidate_evaluation_id,
    )
    version = TradePlanVersion(
        id=version_id,
        trade_plan_id=plan_id,
        version=1,
        direction=TradeDirection.LONG,
        thesis="Approved continuation setup",
        entry=EntryPlan(type=EntryType.PRICE, currency="EUR", price=Decimal("100")),
        invalidation=InvalidationPlan(stop_price=Decimal("95")),
        targets=(Target(sequence=1, price=Decimal("112")),),
        risk_assumptions=RiskAssumptions(thesis_risk="Setup invalidation"),
        status=TradePlanStatus.APPROVED,
        created_at=now - timedelta(hours=12),
        created_by=actor,
    )

    warrant = Warrant(
        id=uuid4(),
        workspace_id=workspace_id,
        issuer_id=uuid4(),
        underlying_id=underlying_id,
        display_name="Golden Path Call",
        isin=None,
        wkn=None,
        lifecycle_status=WarrantLifecycle.ACTIVE,
        version=1,
        created_at=now - timedelta(days=30),
        updated_at=now - timedelta(days=30),
    )
    terms = WarrantTermsVersion(
        id=uuid4(),
        warrant_id=warrant.id,
        version_no=1,
        effective_from=now - timedelta(days=30),
        effective_to=None,
        option_direction=OptionDirection.CALL,
        strike=Decimal("100"),
        maturity_date=date(2027, 1, 15),
        ratio=Decimal("0.1"),
        created_at=now - timedelta(days=30),
    )
    listing = WarrantListing(
        id=uuid4(),
        workspace_id=workspace_id,
        warrant_id=warrant.id,
        trading_venue_id=uuid4(),
        symbol="GOLD",
        quotation_currency_code="EUR",
        lifecycle_status=WarrantLifecycle.ACTIVE,
        version=1,
        created_at=now - timedelta(days=30),
        updated_at=now - timedelta(days=30),
    )

    trade_plans = AsyncMock()
    trade_plans.get_plan.return_value = plan
    trade_plans.get_version.return_value = version
    products = AsyncMock()
    products.warrants_for_underlying.return_value = (warrant,)
    products.terms_for_warrants.return_value = (terms,)
    products.listings_for_warrants.return_value = (listing,)
    market_data = AsyncMock()
    market_data.get_warrant_listing_quote.return_value = MarketDataResult(
        data=WarrantQuoteSnapshot(
            warrant_listing_id=listing.id,
            bid=Decimal("1.00"),
            ask=Decimal("1.04"),
            currency="EUR",
            provider_symbol="GOLD",
            provider_exchange_code="XETR",
            observed_at=now - timedelta(seconds=5),
        ),
        provider=MarketDataProvider.EODHD,
        capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
        correlation_id=uuid4(),
        retrieved_at=now,
        cache_status=CacheStatus.MISS,
        quality_status=QualityStatus.VALID,
        warnings=(),
        retry_count=0,
        provider_call_cost=1,
    )

    model = ModelReference("FT008", "1.0.0")
    service = ProductSelectionService(
        trade_plans=trade_plans,
        products=products,
        market_data=market_data,
    )
    result = await service.start_run(
        workspace_id=workspace_id,
        trade_plan_id=plan_id,
        trade_plan_version_id=version_id,
        actor=actor,
        models=ProductSelectionModels(
            universe=model,
            eligibility=model,
            evaluation=model,
            direction_rule=DirectionEligibilityRule(
                frozenset({OptionDirection.CALL}), "LONG_CALL_V1"
            ),
        ),
        evaluated_at=now,
    )

    assert result.run.workspace_id == workspace_id
    assert result.run.trade_plan_id == plan_id
    assert result.run.trade_plan_version_id == version_id
    assert result.run.trade_plan_version_status is TradePlanStatus.APPROVED
    assert result.run.underlying_id == underlying_id
    assert len(result.evaluations) == 1
    evaluation = result.evaluations[0]
    assert evaluation.eligibility_status is EligibilityStatus.ELIGIBLE
    assert evaluation.run_id == result.run.id

    selection = ProductSelection.from_user_decision(
        id=uuid4(),
        run=result.run,
        evaluation=evaluation,
        selected_at=now + timedelta(minutes=1),
        selected_by=actor,
        rationale="Best eligible product for the approved plan",
    )

    uow = SelectionUow()
    persistence = ProductSelectionPersistenceService(uow)
    await persistence.persist_run(result)
    await persistence.persist_selection(selection)

    trade_plans.get_plan.assert_awaited_once_with(workspace_id, plan_id)
    trade_plans.get_version.assert_awaited_once_with(plan_id, version_id)
    products.warrants_for_underlying.assert_awaited_once_with(workspace_id, underlying_id)
    uow.runs.add.assert_awaited_once_with(result.run)
    uow.evaluations.add.assert_awaited_once_with(evaluation)
    uow.selections.add.assert_awaited_once_with(selection)
    assert uow.commit.await_count == 2

    # The downstream decision remains pinned to the exact immutable FT-007 and FT-008
    # snapshots chosen at handoff time; no later TradePlanVersion or re-run can retarget it.
    later_trade_plan_version_id = uuid4()
    later_product_selection_run_id = uuid4()
    assert result.run.trade_plan_version_id == version_id
    assert result.run.trade_plan_version_id != later_trade_plan_version_id
    assert selection.run_id == result.run.id
    assert selection.run_id != later_product_selection_run_id
    assert selection.product_evaluation_id == evaluation.id
