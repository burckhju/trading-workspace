"""Read-only position-level quote-source coverage and health projection."""

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, Protocol
from uuid import UUID

from app.features.market_data.persistence.position_quote_coverage import (
    PositionQuoteCoverageRecord,
)
from app.features.market_data.service.quote_coverage import (
    ProductCoverage,
    QuoteCoverageService,
    RouteCoverage,
)
from app.features.position_monitoring.service.quote_freshness import (
    QuoteFreshness,
    TradingSessionFreshnessPolicy,
)


class PositionQuoteSourceHealth(StrEnum):
    LEGACY_UNBOUND = "LEGACY_UNBOUND"
    NO_VERIFIED_QUOTE_SOURCE = "NO_VERIFIED_QUOTE_SOURCE"
    AMBIGUOUS_SOURCE = "AMBIGUOUS_SOURCE"
    MAPPING_CONFLICT = "MAPPING_CONFLICT"
    SOURCE_DISABLED = "SOURCE_DISABLED"
    MISSING_QUOTE = "MISSING_QUOTE"
    INVALID_QUOTE = "INVALID_QUOTE"
    FRESH_QUOTE = "FRESH_QUOTE"
    LAST_AVAILABLE = "LAST_AVAILABLE"
    RETAINED_AFTER_REFRESH_ERROR = "RETAINED_AFTER_REFRESH_ERROR"
    STALE = "STALE"
    REFERENCE_ONLY = "REFERENCE_ONLY"


class PositionCoverageReader(Protocol):
    async def open_positions(
        self, workspace_id: UUID
    ) -> tuple[PositionQuoteCoverageRecord, ...]: ...


@dataclass(frozen=True)
class PositionQuoteCoverage:
    position_id: UUID
    trade_id: UUID
    warrant_id: UUID
    name: str
    isin: str | None
    wkn: str | None
    selection_id: UUID | None
    selection_status: str | None
    selection_reason: str | None
    policy_version: str | None
    selected_at: datetime | None
    selected_provider: str | None
    warrant_listing_id: UUID | None
    mapping_id: UUID | None
    provider_exchange_code: str | None
    mic: str | None
    currency: str | None
    mapping_status: str | None
    mapping_version: int | None
    identity_valid: bool
    source_verified: bool
    source_health: PositionQuoteSourceHealth
    candidate_product_coverage: str | None
    quote_status: str | None = None
    quote_type: str | None = None
    bid: Decimal | None = None
    ask: Decimal | None = None
    reference_price: Decimal | None = None
    observed_at: datetime | None = None
    retrieved_at: datetime | None = None
    age_seconds: int | None = None
    max_quote_age_seconds: int | None = None
    refresh_error: str | None = None
    trading_status: str | None = None
    monitoring_usable: bool = False
    execution_usable: bool = False


@dataclass(frozen=True)
class PositionQuoteCoverageSummary:
    open_positions: int
    bound_positions: int
    legacy_unbound: int
    source_verified: int
    fresh_quote: int
    last_available: int
    retained_after_refresh_error: int
    stale: int
    reference_only: int
    missing_quote: int
    missing_source: int
    source_disabled: int
    mapping_conflict: int
    ambiguous_source: int
    invalid_quote: int


@dataclass(frozen=True)
class PositionQuoteCoverageReport:
    assessed_at: datetime
    configured_sources: tuple[str, ...]
    source_order: tuple[str, ...]
    summary: PositionQuoteCoverageSummary
    items: tuple[PositionQuoteCoverage, ...]
    assessment_scope: str = "STORED_OBSERVATIONS_NOT_LIVE_VALUATION"
    execution_usable: bool = False


class PositionQuoteCoverageService:
    def __init__(
        self,
        reader: PositionCoverageReader,
        product_coverage: QuoteCoverageService,
        freshness_policy: TradingSessionFreshnessPolicy | None = None,
    ) -> None:
        self.reader = reader
        self.product_coverage = product_coverage
        self.freshness_policy = freshness_policy or TradingSessionFreshnessPolicy()

    async def report(
        self,
        workspace_id: UUID,
        scheduler: dict[str, Any],
        *,
        as_of: datetime | None = None,
    ) -> PositionQuoteCoverageReport:
        now = as_of or datetime.now(UTC)
        if now.tzinfo is None:
            raise ValueError("COVERAGE_AS_OF_MUST_BE_AWARE")
        positions = await self.reader.open_positions(workspace_id)
        products = await self.product_coverage.report(workspace_id, scheduler, as_of=now)
        products_by_id = {item.warrant_id: item for item in products.items}
        items = tuple(
            self._position(row, products_by_id.get(row.warrant_id), now) for row in positions
        )
        return PositionQuoteCoverageReport(
            assessed_at=now,
            configured_sources=products.configured_sources,
            source_order=products.source_order,
            summary=self._summary(items),
            items=items,
        )

    def _position(
        self,
        row: PositionQuoteCoverageRecord,
        product: ProductCoverage | None,
        now: datetime,
    ) -> PositionQuoteCoverage:
        if row.selection_status is None:
            return self._result(
                row,
                product,
                identity_valid=False,
                source_verified=False,
                health=PositionQuoteSourceHealth.LEGACY_UNBOUND,
            )
        if row.selection_status == "NO_VERIFIED_QUOTE_SOURCE":
            return self._result(
                row,
                product,
                identity_valid=False,
                source_verified=False,
                health=PositionQuoteSourceHealth.NO_VERIFIED_QUOTE_SOURCE,
            )
        if row.selection_status == "AMBIGUOUS_SOURCE":
            return self._result(
                row,
                product,
                identity_valid=False,
                source_verified=False,
                health=PositionQuoteSourceHealth.AMBIGUOUS_SOURCE,
            )

        identity_valid = (
            row.persisted_identity_key is not None
            and row.persisted_identity_key == row.current_identity_key
            and row.persisted_mapping_version is not None
            and row.persisted_mapping_version == row.current_mapping_version
            and row.current_mapping_status == "ACTIVE"
        )
        if not identity_valid:
            return self._result(
                row,
                product,
                identity_valid=False,
                source_verified=False,
                health=PositionQuoteSourceHealth.MAPPING_CONFLICT,
            )

        route = self._selected_route(row, product)
        if route is None or route.route_reason != "ROUTE_IDENTITY_VERIFIED":
            return self._result(
                row,
                product,
                identity_valid=True,
                source_verified=True,
                health=PositionQuoteSourceHealth.MAPPING_CONFLICT,
            )
        if not route.configured:
            return self._result(
                row,
                product,
                identity_valid=True,
                source_verified=True,
                health=PositionQuoteSourceHealth.SOURCE_DISABLED,
                route=route,
            )

        health = self._quote_health(route, now)
        quote_present = route.bid is not None or route.reference_price is not None
        monitoring_usable = (
            quote_present
            and route.observed_at is not None
            and health
            in {
                PositionQuoteSourceHealth.FRESH_QUOTE,
                PositionQuoteSourceHealth.LAST_AVAILABLE,
                PositionQuoteSourceHealth.RETAINED_AFTER_REFRESH_ERROR,
                PositionQuoteSourceHealth.STALE,
                PositionQuoteSourceHealth.REFERENCE_ONLY,
            }
        )
        return self._result(
            row,
            product,
            identity_valid=True,
            source_verified=True,
            health=health,
            route=route,
            monitoring_usable=monitoring_usable,
        )

    @staticmethod
    def _result(
        row: PositionQuoteCoverageRecord,
        product: ProductCoverage | None,
        *,
        identity_valid: bool,
        source_verified: bool,
        health: PositionQuoteSourceHealth,
        route: RouteCoverage | None = None,
        monitoring_usable: bool = False,
    ) -> PositionQuoteCoverage:
        return PositionQuoteCoverage(
            position_id=row.position_id,
            trade_id=row.trade_id,
            warrant_id=row.warrant_id,
            name=row.name,
            isin=row.isin,
            wkn=row.wkn,
            selection_id=row.selection_id,
            selection_status=row.selection_status,
            selection_reason=row.selection_reason,
            policy_version=row.policy_version,
            selected_at=row.selected_at,
            selected_provider=row.provider,
            warrant_listing_id=row.listing_id,
            mapping_id=row.mapping_id,
            provider_exchange_code=row.provider_exchange_code,
            mic=row.mic,
            currency=row.currency,
            mapping_status=row.current_mapping_status,
            mapping_version=row.current_mapping_version,
            identity_valid=identity_valid,
            source_verified=source_verified,
            source_health=health,
            candidate_product_coverage=product.coverage if product is not None else None,
            quote_status=route.observation_status if route is not None else None,
            quote_type=(
                "BID"
                if route is not None and route.bid is not None
                else route.reference_price_type if route is not None else None
            ),
            bid=route.bid if route is not None else None,
            ask=route.ask if route is not None else None,
            reference_price=route.reference_price if route is not None else None,
            observed_at=route.observed_at if route is not None else None,
            retrieved_at=route.retrieved_at if route is not None else None,
            age_seconds=route.age_seconds if route is not None else None,
            max_quote_age_seconds=(route.max_quote_age_seconds if route is not None else None),
            refresh_error=route.refresh_error if route is not None else None,
            trading_status=route.trading_status if route is not None else None,
            monitoring_usable=monitoring_usable,
            execution_usable=False,
        )

    @staticmethod
    def _selected_route(
        row: PositionQuoteCoverageRecord, product: ProductCoverage | None
    ) -> RouteCoverage | None:
        if product is None:
            return None
        routes = [
            route
            for route in product.routes
            if route.provider == row.provider
            and route.listing_id == row.listing_id
            and route.mapping_id == row.mapping_id
        ]
        return routes[0] if len(routes) == 1 else None

    def _quote_health(self, route: RouteCoverage, now: datetime) -> PositionQuoteSourceHealth:
        if route.observation_status in {"IDENTITY_CHANGED", "INVALID_STORED_OBSERVATION"}:
            return PositionQuoteSourceHealth.INVALID_QUOTE
        if route.observation_status in {"NO_VERIFIED_OBSERVATION", "ROUTE_UNAVAILABLE"}:
            return PositionQuoteSourceHealth.MISSING_QUOTE
        if route.refresh_error:
            return PositionQuoteSourceHealth.RETAINED_AFTER_REFRESH_ERROR
        if route.observation_status == "REFERENCE_ONLY":
            return PositionQuoteSourceHealth.REFERENCE_ONLY
        if route.observed_at is None:
            return PositionQuoteSourceHealth.MISSING_QUOTE

        freshness = self.freshness_policy.classify(
            observed_at=route.observed_at,
            retrieved_at=now,
            max_age_seconds=route.max_quote_age_seconds or 3600,
            trading_status=route.trading_status,
        )
        if freshness is QuoteFreshness.FRESH:
            return PositionQuoteSourceHealth.FRESH_QUOTE
        if freshness is QuoteFreshness.LAST_AVAILABLE:
            return PositionQuoteSourceHealth.LAST_AVAILABLE
        return PositionQuoteSourceHealth.STALE

    @staticmethod
    def _summary(
        items: tuple[PositionQuoteCoverage, ...],
    ) -> PositionQuoteCoverageSummary:
        def count(*health: PositionQuoteSourceHealth) -> int:
            return sum(item.source_health in health for item in items)

        return PositionQuoteCoverageSummary(
            open_positions=len(items),
            bound_positions=sum(item.selection_status == "SELECTED" for item in items),
            legacy_unbound=count(PositionQuoteSourceHealth.LEGACY_UNBOUND),
            source_verified=sum(item.source_verified for item in items),
            fresh_quote=count(PositionQuoteSourceHealth.FRESH_QUOTE),
            last_available=count(PositionQuoteSourceHealth.LAST_AVAILABLE),
            retained_after_refresh_error=count(
                PositionQuoteSourceHealth.RETAINED_AFTER_REFRESH_ERROR
            ),
            stale=count(PositionQuoteSourceHealth.STALE),
            reference_only=count(PositionQuoteSourceHealth.REFERENCE_ONLY),
            missing_quote=count(PositionQuoteSourceHealth.MISSING_QUOTE),
            missing_source=count(
                PositionQuoteSourceHealth.LEGACY_UNBOUND,
                PositionQuoteSourceHealth.NO_VERIFIED_QUOTE_SOURCE,
                PositionQuoteSourceHealth.AMBIGUOUS_SOURCE,
            ),
            source_disabled=count(PositionQuoteSourceHealth.SOURCE_DISABLED),
            mapping_conflict=count(PositionQuoteSourceHealth.MAPPING_CONFLICT),
            ambiguous_source=count(PositionQuoteSourceHealth.AMBIGUOUS_SOURCE),
            invalid_quote=count(PositionQuoteSourceHealth.INVALID_QUOTE),
        )
