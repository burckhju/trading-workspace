"""Application orchestration for starting an FT-008 ProductSelectionRun."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.market_data.domain.enums import MarketDataCapability, QualityStatus
from app.features.market_data.domain.models import WarrantQuoteSnapshot
from app.features.market_data.service.contracts import WarrantListingQuoteProvider
from app.features.market_data.service.types import MarketDataResult, WarrantQuoteRequest
from app.features.product_selection.domain.enums import (
    CriterionOutcome,
    DataAvailability,
    EligibilityStatus,
    MetricOrigin,
)
from app.features.product_selection.domain.models import (
    CriterionResult,
    EvaluationInput,
    EvaluationMetric,
    ModelReference,
    ProductEvaluation,
    ProductSelectionRun,
)
from app.features.product_selection.service.repositories import (
    ProductSelectionProductRepository,
    ProductSelectionTradePlanRepository,
    SqlAlchemyProductSelectionProductRepository,
    SqlAlchemyProductSelectionTradePlanRepository,
)
from app.features.product_selection.service.universe import (
    DirectionEligibilityRule,
    ProductUniverse,
    ProductUniverseMember,
    UniverseOmission,
    construct_product_universe,
    evaluate_reference_eligibility,
)
from app.features.trade_plan.domain.enums import TradePlanStatus


@dataclass(frozen=True, slots=True)
class ProductSelectionModels:
    universe: ModelReference
    eligibility: ModelReference
    evaluation: ModelReference
    direction_rule: DirectionEligibilityRule | None = None


@dataclass(frozen=True, slots=True)
class ProductSelectionRunResult:
    run: ProductSelectionRun
    evaluations: tuple[ProductEvaluation, ...]
    universe_omissions: tuple[UniverseOmission, ...]


class ProductSelectionService:
    """Build a reproducible reference-data evaluation run without persisting it yet."""

    def __init__(
        self,
        session: AsyncSession | None = None,
        *,
        trade_plans: ProductSelectionTradePlanRepository | None = None,
        products: ProductSelectionProductRepository | None = None,
        market_data: WarrantListingQuoteProvider | None = None,
    ) -> None:
        if trade_plans is None:
            if session is None:
                raise ValueError("session or explicit repositories are required")
            trade_plans = SqlAlchemyProductSelectionTradePlanRepository(session)
        if products is None:
            if session is None:
                raise ValueError("session or explicit repositories are required")
            products = SqlAlchemyProductSelectionProductRepository(session)
        self._trade_plans = trade_plans
        self._products = products
        self._market_data = market_data

    async def start_run(
        self,
        *,
        workspace_id: UUID,
        trade_plan_id: UUID,
        trade_plan_version_id: UUID,
        actor: UUID,
        models: ProductSelectionModels,
        evaluated_at: datetime | None = None,
    ) -> ProductSelectionRunResult:
        plan = await self._trade_plans.get_plan(workspace_id, trade_plan_id)
        if plan is None:
            raise ValueError("trade plan not found in workspace")

        version = await self._trade_plans.get_version(trade_plan_id, trade_plan_version_id)
        if version is None:
            raise ValueError("trade plan version not found for trade plan")
        if version.trade_plan_id != plan.id:
            raise ValueError("trade plan version does not belong to trade plan")
        if version.status is not TradePlanStatus.APPROVED:
            raise ValueError("Product Selection requires an APPROVED TradePlanVersion")

        now = evaluated_at or datetime.now(UTC)
        run = ProductSelectionRun(
            id=uuid4(),
            workspace_id=plan.workspace_id,
            trade_plan_id=plan.id,
            trade_plan_version_id=version.id,
            trade_plan_version_status=version.status,
            underlying_id=plan.underlying_id,
            evaluated_at=now,
            universe_model=models.universe,
            eligibility_model=models.eligibility,
            evaluation_model=models.evaluation,
            created_at=now,
            created_by=actor,
        )

        universe = await self._load_universe(run)
        evaluations = tuple(
            [
                await self._evaluate_member(run=run, member=member, models=models)
                for member in universe.members
            ]
        )
        return ProductSelectionRunResult(
            run=run,
            evaluations=evaluations,
            universe_omissions=universe.omissions,
        )

    async def _load_universe(self, run: ProductSelectionRun) -> ProductUniverse:
        warrants = await self._products.warrants_for_underlying(run.workspace_id, run.underlying_id)
        warrant_ids = tuple(warrant.id for warrant in warrants)
        terms = await self._products.terms_for_warrants(warrant_ids)
        listings = await self._products.listings_for_warrants(run.workspace_id, warrant_ids)
        return construct_product_universe(
            run=run,
            warrants=warrants,
            terms_versions=terms,
            listings=listings,
        )

    async def _evaluate_member(
        self,
        *,
        run: ProductSelectionRun,
        member: ProductUniverseMember,
        models: ProductSelectionModels,
    ) -> ProductEvaluation:
        reference = evaluate_reference_eligibility(
            member=member,
            evaluated_at=run.evaluated_at,
            direction_rule=models.direction_rule,
        )

        if reference.status is EligibilityStatus.INELIGIBLE:
            market_criteria, market_inputs, metrics = self._market_data_not_applicable()
        else:
            market_criteria, market_inputs, metrics = await self._market_data_evaluation(
                run=run, member=member
            )

        criteria = (*reference.criteria, *market_criteria)
        status = self._overall_status(criteria)
        reasons = tuple(
            dict.fromkeys(
                criterion.explanation
                for criterion in criteria
                if criterion.outcome
                in {CriterionOutcome.NOT_FULFILLED, CriterionOutcome.NOT_EVALUABLE}
            )
        )
        inputs = (
            EvaluationInput(
                name="warrant_terms_version_id",
                value=str(member.terms.id),
                availability=DataAvailability.AVAILABLE,
                source="FT-004 WarrantTermsVersion",
                observed_at=run.evaluated_at,
                quality="historically resolved effective version",
            ),
            EvaluationInput(
                name="warrant_listing_id",
                value=str(member.listing.id),
                availability=DataAvailability.AVAILABLE,
                source="FT-004 WarrantListing",
                observed_at=run.evaluated_at,
                quality="concrete listing context",
            ),
            *market_inputs,
        )
        return ProductEvaluation(
            id=uuid4(),
            run_id=run.id,
            warrant_id=member.warrant.id,
            warrant_terms_version_id=member.terms.id,
            warrant_listing_id=member.listing.id,
            evaluated_at=run.evaluated_at,
            eligibility_model=models.eligibility,
            evaluation_model=models.evaluation,
            inputs=inputs,
            criteria=criteria,
            metrics=metrics,
            eligibility_status=status,
            reasons=reasons,
        )

    async def _market_data_evaluation(
        self, *, run: ProductSelectionRun, member: ProductUniverseMember
    ) -> tuple[
        tuple[CriterionResult, ...], tuple[EvaluationInput, ...], tuple[EvaluationMetric, ...]
    ]:
        if self._market_data is None:
            explanation = (
                "Provider-neutral WarrantListing market-data provider is not configured; "
                "quote-dependent V1 evaluation cannot be completed"
            )
            return (
                (
                    CriterionResult(
                        criterion_id="warrant-market-data-contract-available",
                        outcome=CriterionOutcome.NOT_EVALUABLE,
                        explanation=explanation,
                        data_availability=DataAvailability.MISSING,
                    ),
                ),
                (
                    EvaluationInput(
                        name="market_data_snapshot",
                        value=None,
                        availability=DataAvailability.MISSING,
                        source="TC-001 WarrantListing quote boundary",
                        quality="provider not configured",
                    ),
                ),
                (),
            )

        result = await self._market_data.get_warrant_listing_quote(
            WarrantQuoteRequest(
                workspace_id=run.workspace_id,
                warrant_listing_id=member.listing.id,
                correlation_id=run.id,
                as_of=run.evaluated_at,
            )
        )
        if result.capability is not MarketDataCapability.WARRANT_LISTING_QUOTE:
            raise ValueError("Warrant quote provider returned the wrong market-data capability")
        if result.data is None:
            return self._missing_quote(result)
        if result.data.warrant_listing_id != member.listing.id:
            raise ValueError("Warrant quote snapshot belongs to a different WarrantListing")
        return self._evaluate_quote(member=member, result=result)

    @staticmethod
    def _market_data_not_applicable() -> (
        tuple[
            tuple[CriterionResult, ...], tuple[EvaluationInput, ...], tuple[EvaluationMetric, ...]
        ]
    ):
        return (
            (
                CriterionResult(
                    criterion_id="warrant-market-data-contract-available",
                    outcome=CriterionOutcome.NOT_APPLICABLE,
                    explanation="Quote lookup skipped because reference eligibility already failed",
                    data_availability=DataAvailability.NOT_APPLICABLE,
                ),
            ),
            (
                EvaluationInput(
                    name="market_data_snapshot",
                    value=None,
                    availability=DataAvailability.NOT_APPLICABLE,
                    source="TC-001 WarrantListing quote boundary",
                    quality="not requested after reference exclusion",
                ),
            ),
            (),
        )

    @staticmethod
    def _missing_quote(
        result: MarketDataResult[WarrantQuoteSnapshot | None],
    ) -> tuple[
        tuple[CriterionResult, ...], tuple[EvaluationInput, ...], tuple[EvaluationMetric, ...]
    ]:
        explanation = "No WarrantListing quote snapshot was available at the evaluation time"
        return (
            (
                CriterionResult(
                    criterion_id="warrant-market-data-contract-available",
                    outcome=CriterionOutcome.NOT_EVALUABLE,
                    explanation=explanation,
                    data_availability=DataAvailability.MISSING,
                ),
            ),
            (
                EvaluationInput(
                    name="market_data_snapshot",
                    value=None,
                    availability=DataAvailability.MISSING,
                    source=f"TC-001/{result.provider.value}",
                    observed_at=None,
                    quality=ProductSelectionService._quality_text(result),
                ),
            ),
            (),
        )

    @staticmethod
    def _evaluate_quote(
        *,
        member: ProductUniverseMember,
        result: MarketDataResult[WarrantQuoteSnapshot | None],
    ) -> tuple[
        tuple[CriterionResult, ...], tuple[EvaluationInput, ...], tuple[EvaluationMetric, ...]
    ]:
        snapshot = result.data
        assert snapshot is not None
        source = (
            f"{result.provider.value}:{snapshot.provider_symbol}."
            f"{snapshot.provider_exchange_code}"
        )
        quality_text = ProductSelectionService._quality_text(result)
        currency_matches = snapshot.currency == member.listing.quotation_currency_code
        complete = snapshot.bid is not None and snapshot.ask is not None
        quality_valid = result.quality_status is QualityStatus.VALID
        usable = complete and currency_matches and quality_valid

        explanation_parts: list[str] = []
        if not complete:
            explanation_parts.append("bid and ask are not both available")
        if not currency_matches:
            explanation_parts.append(
                f"quote currency {snapshot.currency} does not match listing currency "
                f"{member.listing.quotation_currency_code}"
            )
        if not quality_valid:
            explanation_parts.append(f"market-data quality is {result.quality_status.value}")

        criterion = CriterionResult(
            criterion_id="warrant-market-data-contract-available",
            outcome=CriterionOutcome.FULFILLED if usable else CriterionOutcome.NOT_EVALUABLE,
            explanation=(
                "Complete, currency-consistent WarrantListing quote is available"
                if usable
                else "WarrantListing quote is not sufficient: " + "; ".join(explanation_parts)
            ),
            actual_value=(
                f"bid={snapshot.bid};ask={snapshot.ask};currency={snapshot.currency}"
                if complete
                else None
            ),
            expected_value=(
                "complete bid/ask; "
                f"currency={member.listing.quotation_currency_code}; "
                "quality=VALID"
            ),
            data_availability=(
                DataAvailability.AVAILABLE if usable else DataAvailability.INSUFFICIENT
            ),
        )
        inputs = (
            EvaluationInput(
                name="market_data_snapshot",
                value=(f"{source}@{snapshot.observed_at.isoformat()}"),
                availability=DataAvailability.AVAILABLE,
                source="TC-001 WarrantListing quote boundary",
                observed_at=snapshot.observed_at,
                quality=quality_text,
            ),
            ProductSelectionService._quote_input(
                "bid", snapshot.bid, source, snapshot, quality_text
            ),
            ProductSelectionService._quote_input(
                "ask", snapshot.ask, source, snapshot, quality_text
            ),
        )
        metrics = ProductSelectionService._quote_metrics(
            snapshot, source, quality_valid and currency_matches
        )
        return ((criterion,), inputs, metrics)

    @staticmethod
    def _quote_input(
        name: str,
        value: Decimal | None,
        source: str,
        snapshot: WarrantQuoteSnapshot,
        quality: str,
    ) -> EvaluationInput:
        return EvaluationInput(
            name=f"market_{name}",
            value=str(value) if value is not None else None,
            availability=(
                DataAvailability.AVAILABLE if value is not None else DataAvailability.MISSING
            ),
            source=source,
            observed_at=snapshot.observed_at,
            quality=quality,
        )

    @staticmethod
    def _quote_metrics(
        snapshot: WarrantQuoteSnapshot, source: str, context_valid: bool
    ) -> tuple[EvaluationMetric, ...]:
        bid_availability = (
            DataAvailability.AVAILABLE if snapshot.bid is not None else DataAvailability.MISSING
        )
        ask_availability = (
            DataAvailability.AVAILABLE if snapshot.ask is not None else DataAvailability.MISSING
        )
        metrics: list[EvaluationMetric] = [
            EvaluationMetric(
                metric_id="bid",
                value=snapshot.bid,
                unit=snapshot.currency,
                origin=MetricOrigin.PROVIDER,
                source=source,
                data_availability=bid_availability,
            ),
            EvaluationMetric(
                metric_id="ask",
                value=snapshot.ask,
                unit=snapshot.currency,
                origin=MetricOrigin.PROVIDER,
                source=source,
                data_availability=ask_availability,
            ),
        ]
        if snapshot.bid is not None and snapshot.ask is not None and context_valid:
            spread = snapshot.ask - snapshot.bid
            midpoint = (snapshot.ask + snapshot.bid) / Decimal("2")
            spread_percent = spread / midpoint * Decimal("100")
            metrics.extend(
                [
                    EvaluationMetric(
                        metric_id="spread_absolute",
                        value=spread,
                        unit=snapshot.currency,
                        origin=MetricOrigin.CALCULATED,
                        source="FT-008 transparent quote comparison",
                        formula_or_rule="ask - bid",
                    ),
                    EvaluationMetric(
                        metric_id="spread_percent_mid",
                        value=spread_percent,
                        unit="PERCENT",
                        origin=MetricOrigin.CALCULATED,
                        source="FT-008 transparent quote comparison",
                        formula_or_rule="(ask - bid) / ((ask + bid) / 2) * 100",
                    ),
                ]
            )
        return tuple(metrics)

    @staticmethod
    def _quality_text(result: MarketDataResult[object]) -> str:
        warnings = "; ".join(result.warnings)
        return f"{result.quality_status.value}; retrieved_at={result.retrieved_at.isoformat()}" + (
            f"; warnings={warnings}" if warnings else ""
        )

    @staticmethod
    def _overall_status(criteria: tuple[CriterionResult, ...]) -> EligibilityStatus:
        if any(item.outcome is CriterionOutcome.NOT_FULFILLED for item in criteria):
            return EligibilityStatus.INELIGIBLE
        if any(item.outcome is CriterionOutcome.NOT_EVALUABLE for item in criteria):
            return EligibilityStatus.NOT_EVALUABLE
        return EligibilityStatus.ELIGIBLE
