"""Read-only source coverage: stored evidence is not a live valuation or permission."""

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID

from pydantic import TypeAdapter, ValidationError

from app.features.market_data.domain.enums import MarketDataCapability, QualityStatus
from app.features.market_data.domain.models import WarrantQuoteSnapshot
from app.features.market_data.service.types import MarketDataResult
from app.features.position_monitoring.service.quote_sources import quote_priority

_RESULT = TypeAdapter(MarketDataResult[WarrantQuoteSnapshot | None])


@dataclass(frozen=True)
class RouteRecord:
    provider: str
    listing_id: UUID
    mic: str
    currency: str
    mapping_id: UUID | None
    mapping_status: str | None
    provider_identity: str | None
    provider_exchange_code: str | None
    validated_at: datetime | None
    route_reason: str
    identity_key: str | None
    observation_identity_key: str | None
    payload: dict[str, Any] | None


@dataclass(frozen=True)
class ProductRecord:
    warrant_id: UUID
    name: str
    isin: str | None
    wkn: str | None
    issuer: str
    active: bool
    issuer_probe_eligible: bool
    routes: tuple[RouteRecord, ...]


class CoverageReader(Protocol):
    async def held_products(self, workspace_id: UUID) -> tuple[ProductRecord, ...]: ...


@dataclass(frozen=True)
class RouteCoverage:
    provider: str
    listing_id: UUID
    mic: str
    currency: str
    mapping_id: UUID | None
    mapping_status: str | None
    provider_identity: str | None
    provider_exchange_code: str | None
    validated_at: datetime | None
    configured: bool
    route_reason: str
    observation_status: str
    bid: Decimal | None = None
    ask: Decimal | None = None
    reference_price: Decimal | None = None
    reference_price_type: str | None = None
    observed_at: datetime | None = None
    retrieved_at: datetime | None = None
    age_seconds: int | None = None
    max_quote_age_seconds: int | None = None
    feed_delay_seconds: int | None = None
    trading_status: str | None = None
    refresh_error: str | None = None


@dataclass(frozen=True)
class ProductCoverage:
    warrant_id: UUID
    name: str
    isin: str | None
    wkn: str | None
    issuer: str
    issuer_probe_eligible: bool
    coverage: str
    routes: tuple[RouteCoverage, ...]
    refresh_status: str
    refresh_reason: str | None
    checked_at: datetime | None
    next_run_at: datetime | None
    discovery_reasons: tuple[str, ...]


@dataclass(frozen=True)
class CoverageReport:
    assessed_at: datetime
    scheduler_enabled: bool
    scheduler_leader: bool
    source_order: tuple[str, ...]
    configured_sources: tuple[str, ...]
    items: tuple[ProductCoverage, ...]
    assessment_scope: str = "STORED_OBSERVATIONS_NOT_LIVE_VALUATION"
    execution_usable: bool = False


def _code(value: object) -> str | None:
    # Never propagate arbitrary provider bodies, URLs or exceptions.
    import re

    return (
        value if isinstance(value, str) and re.fullmatch(r"[A-Z][A-Z0-9_]{0,120}", value) else None
    )


class QuoteCoverageService:
    def __init__(self, reader: CoverageReader, sources: tuple[tuple[str, bool], ...]) -> None:
        self.reader = reader
        self.sources = sources

    async def report(
        self, workspace_id: UUID, scheduler: dict[str, Any], *, as_of: datetime | None = None
    ) -> CoverageReport:
        now = as_of or datetime.now(UTC)
        if now.tzinfo is None:
            raise ValueError("COVERAGE_AS_OF_MUST_BE_AWARE")
        configured = {name for name, enabled in self.sources if enabled}
        # Runtime diagnostics belong only to their configured workspace.
        same_workspace = str(scheduler.get("workspace_id")) == str(workspace_id)
        jobs = scheduler.get("jobs", []) if same_workspace else []
        indexed = {str(job["job"]): job for job in jobs}
        running = set((scheduler.get("current_jobs") or {}).values()) if same_workspace else set()
        enabled = bool(scheduler.get("enabled")) and same_workspace
        products = await self.reader.held_products(workspace_id)
        items = []
        for product in products:
            key = f"WARRANT_QUOTES:{product.warrant_id}"
            job = indexed.get(key, {})
            attempts = {
                (a.get("source"), str(a.get("warrant_listing_id"))): a
                for a in job.get("source_attempts", [])
            }
            routes = tuple(
                self._route(
                    row,
                    product,
                    row.provider in configured,
                    now,
                    attempts.get((row.provider, str(row.listing_id)), {}),
                )
                for row in product.routes
            )
            statuses = {route.observation_status for route in routes}
            if not product.active:
                coverage = "INACTIVE_PRODUCT"
            elif "BID_WITHIN_AGE_BUDGET" in statuses:
                coverage = "BID_WITHIN_AGE_BUDGET"
            elif "OLDER_BID" in statuses:
                coverage = "HISTORICAL_BID_ONLY"
            elif "REFERENCE_ONLY" in statuses:
                coverage = "REFERENCE_ONLY"
            elif any(
                route.route_reason == "ROUTE_IDENTITY_VERIFIED" and route.configured
                for route in routes
            ):
                coverage = "NO_VERIFIED_QUOTE"
            else:
                coverage = "NO_USABLE_ROUTE"
            discovery = tuple(
                code
                for prefix in ("FRANKFURT_MAPPING", "VONTOBEL_MAPPING")
                if (code := _code(indexed.get(f"{prefix}:{product.warrant_id}", {}).get("reason")))
            )
            status = (
                "DISABLED"
                if not enabled
                else "RUNNING" if key in running else _code(job.get("status")) or "NOT_SCHEDULED"
            )
            items.append(
                ProductCoverage(
                    product.warrant_id,
                    product.name,
                    product.isin,
                    product.wkn,
                    product.issuer,
                    product.issuer_probe_eligible,
                    coverage,
                    routes,
                    status,
                    _code(job.get("reason")),
                    job.get("checked_at"),
                    job.get("next_run_at"),
                    discovery,
                )
            )
        return CoverageReport(
            now,
            enabled,
            bool(scheduler.get("leader")) and same_workspace,
            tuple(name for name, _ in self.sources),
            tuple(name for name, enabled in self.sources if enabled),
            tuple(items),
        )

    @staticmethod
    def _route(
        row: RouteRecord,
        product: ProductRecord,
        configured: bool,
        now: datetime,
        attempt: dict[str, Any],
    ) -> RouteCoverage:
        values: dict[str, Any] = {
            "provider": row.provider,
            "listing_id": row.listing_id,
            "mic": row.mic,
            "currency": row.currency,
            "mapping_id": row.mapping_id,
            "mapping_status": row.mapping_status,
            "provider_identity": row.provider_identity,
            "provider_exchange_code": row.provider_exchange_code,
            "validated_at": row.validated_at,
            "configured": configured,
            "route_reason": row.route_reason,
            "observation_status": "NO_VERIFIED_OBSERVATION",
            "refresh_error": _code(attempt.get("refresh_error"))
            or (_code(attempt.get("reason")) if attempt.get("status") != "AVAILABLE" else None),
        }
        if not configured or not product.active or row.identity_key is None:
            return RouteCoverage(**{**values, "observation_status": "ROUTE_UNAVAILABLE"})
        if row.payload is None:
            return RouteCoverage(**values)
        if row.identity_key != row.observation_identity_key:
            return RouteCoverage(**{**values, "observation_status": "IDENTITY_CHANGED"})
        try:
            result = _RESULT.validate_python(row.payload)
            quote = result.data
            if (
                quote is None
                or result.quality_status != QualityStatus.VALID
                or result.capability != MarketDataCapability.WARRANT_LISTING_QUOTE
                or result.provider.value != row.provider
                or quote.warrant_listing_id != row.listing_id
                or quote.currency != row.currency
                or quote.provider_symbol != product.isin
                or quote.provider_exchange_code != row.provider_exchange_code
                or (quote.isin is not None and quote.isin != product.isin)
                or (quote.wkn is not None and product.wkn is not None and quote.wkn != product.wkn)
                or (quote.venue_mic is not None and quote.venue_mic != row.mic)
                or quote.retained
                or (
                    quote.assessed_at is not None
                    and (quote.assessed_at < result.retrieved_at or quote.assessed_at > now)
                )
                or result.retrieved_at > now
                or (quote.observed_at is not None and quote.observed_at > result.retrieved_at)
                or (quote.bid is None and quote.reference_price is None)
            ):
                raise ValueError("INVALID_STORED_OBSERVATION")
            priority = quote_priority(quote, now)
            status = (
                "BID_WITHIN_AGE_BUDGET"
                if priority == 0
                else "OLDER_BID" if quote.bid is not None else "REFERENCE_ONLY"
            )
            if values["refresh_error"] and status == "BID_WITHIN_AGE_BUDGET":
                status = "OLDER_BID"
            return RouteCoverage(
                **{
                    **values,
                    "observation_status": status,
                    "bid": quote.bid,
                    "ask": quote.ask,
                    "reference_price": quote.reference_price,
                    "reference_price_type": quote.reference_price_type,
                    "observed_at": quote.observed_at,
                    "retrieved_at": result.retrieved_at,
                    "age_seconds": (
                        int((now - quote.observed_at).total_seconds())
                        if quote.observed_at
                        else None
                    ),
                    "max_quote_age_seconds": (
                        min(3600, quote.max_quote_age_seconds)
                        if quote.max_quote_age_seconds is not None
                        else 3600
                    ),
                    "feed_delay_seconds": quote.feed_delay_seconds,
                    "trading_status": quote.trading_status,
                }
            )
        except (ValidationError, ValueError, TypeError):
            return RouteCoverage(**{**values, "observation_status": "INVALID_STORED_OBSERVATION"})
