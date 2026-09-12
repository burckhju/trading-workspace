"""Catalog-driven refresh using existing quote providers, mappings and daily imports."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from functools import partial
from time import monotonic
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import func, select

from app.core.config.frankfurt import FrankfurtSourceMode
from app.features.market.persistence.models import TradingVenueModel
from app.features.market_data.domain.enums import MappingStatus, MarketDataProvider
from app.features.market_data.persistence.models import (
    DailyPriceModel,
    ProviderInstrumentMappingModel,
    WarrantProviderMappingModel,
)
from app.features.market_data.service.refresh_catalog import RefreshInstrument, read_catalog
from app.features.market_data.service.refresh_discovery import discover_underlying
from app.features.market_data.service.types import DailyPriceRequest, WarrantQuoteRequest
from app.features.position_monitoring.service.quote_runtime import build_warrant_quote_resolver
from app.features.product.domain.models import WarrantLifecycle
from app.features.product.persistence.models import WarrantListingModel
from app.providers.frankfurt_quotes.configure import configure_warrant as configure_frankfurt
from app.providers.vontobel_markets.configure import configure_warrant as configure_vontobel

if TYPE_CHECKING:
    from app.core.di import ApplicationContainer

logger = logging.getLogger(__name__)


class MarketDataRefreshRuntime:
    """One process-local job schedule; the runner owns the deployment leader lock."""

    def __init__(
        self, container: ApplicationContainer, *, timer: Callable[[], float] = monotonic
    ) -> None:
        self.container = container
        self.settings = container.settings.market_data.refresh
        self.workspace_id = self.settings.workspace_id
        self.timer = timer
        self.jobs: dict[str, dict[str, Any]] = {}
        self._due: dict[str, float] = {}
        self._lock = asyncio.Lock()
        self._next_request = 0.0
        self.running = False
        self.last_scan_at: datetime | None = None
        self.last_error: str | None = None
        self.leader = False
        self.wake = asyncio.Event()
        self._resolver = build_warrant_quote_resolver(container)

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.settings.enabled,
            "running": self.running,
            "leader": self.leader,
            "workspace_id": self.workspace_id,
            "settings": self.settings.model_dump(mode="json"),
            "last_scan_at": self.last_scan_at,
            "last_error": self.last_error,
            "single_instance_only": True,
            "quote_storage": "PROCESS_CACHE_WITH_ORIGINAL_TIMESTAMPS",
            "underlying_price_type": "COMPLETED_EOD",
            "jobs": list(self.jobs.values()),
        }

    async def run_once(self) -> None:
        if not self.settings.enabled or self._lock.locked():
            return
        async with self._lock:
            self.running = True
            try:
                warrants, underlyings = await read_catalog(
                    self.container.database, self.workspace_id
                )
                self.last_scan_at = datetime.now(UTC)
                self.last_error = None
                live_keys: set[str] = set()
                # Refresh all active master data, including products without a position.
                for item in warrants:
                    if self.settings.auto_configure:
                        if (
                            self.container.frankfurt is not None
                            and self.container.frankfurt.settings.source_mode
                            is FrankfurtSourceMode.PUBLIC_WEBSITE
                        ):
                            key = f"FRANKFURT_MAPPING:{item.id}"
                            live_keys.add(key)
                            await self._job(
                                key,
                                item,
                                self.settings.discovery_interval_seconds,
                                partial(self._configure_frankfurt, item),
                            )
                        if (
                            self.container.vontobel is not None
                            and "vontobel" in (item.issuer or "").lower()
                        ):
                            key = f"VONTOBEL_MAPPING:{item.id}"
                            live_keys.add(key)
                            await self._job(
                                key,
                                item,
                                self.settings.discovery_interval_seconds,
                                partial(self._configure_vontobel, item),
                            )
                    key = f"WARRANT_QUOTES:{item.id}"
                    live_keys.add(key)
                    await self._job(
                        key,
                        item,
                        self.settings.warrants_interval_seconds,
                        partial(self._warrant, item),
                    )
                for item in underlyings:
                    if self.settings.auto_configure and item.listing_id is not None:
                        key = f"EODHD_MAPPING:{item.id}:{item.listing_id}"
                        live_keys.add(key)
                        await self._job(
                            key,
                            item,
                            self.settings.discovery_interval_seconds,
                            partial(self._configure_underlying, item),
                        )
                    key = f"UNDERLYING_EOD:{item.id}:{item.listing_id}"
                    live_keys.add(key)
                    await self._job(
                        key,
                        item,
                        self.settings.underlyings_interval_seconds,
                        partial(self._underlying, item),
                    )
                self.jobs = {key: value for key, value in self.jobs.items() if key in live_keys}
                self._due = {key: value for key, value in self._due.items() if key in live_keys}
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.last_error = type(exc).__name__
                logger.exception("market_data_catalog_refresh_failed")
            finally:
                self.running = False

    async def _job(
        self,
        key: str,
        item: RefreshInstrument,
        interval: int,
        operation: Callable[[], Awaitable[dict[str, Any]]],
    ) -> None:
        if self.timer() < self._due.get(key, 0):
            return
        previous = self.jobs.get(key, {})
        try:
            details = await operation()
            status = details.pop("status", "AVAILABLE")
            success_at = (
                datetime.now(UTC) if status == "AVAILABLE" else previous.get("last_success_at")
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            # Never expose transport URLs or credentials in operational diagnostics.
            details = {"reason": str(exc) if isinstance(exc, ValueError) else type(exc).__name__}
            status = "ERROR"
            success_at = previous.get("last_success_at")
        completed = datetime.now(UTC)
        self._due[key] = self.timer() + interval
        self.jobs[key] = {
            "job": key,
            "instrument_id": item.id,
            "listing_id": item.listing_id,
            "name": item.name,
            "isin": item.isin,
            "status": status,
            "checked_at": completed,
            "last_success_at": success_at,
            "next_run_at": completed + timedelta(seconds=interval),
            **details,
        }

    async def _pace(self) -> None:
        delay = self._next_request - self.timer()
        if delay > 0:
            await asyncio.sleep(delay)
        spacing = self.settings.request_spacing_seconds
        if self.container.frankfurt is not None:
            spacing = max(spacing, self.container.frankfurt.settings.refresh_interval_seconds)
        self._next_request = self.timer() + spacing

    async def _configure_frankfurt(self, item: RefreshInstrument) -> dict[str, Any]:
        assert self.container.frankfurt is not None
        await self._pace()
        async with self.container.database.session_context() as session:
            result = await configure_frankfurt(
                session,
                self.container.frankfurt.snapshots,
                workspace_id=self.workspace_id,
                warrant_id=item.id,
                apply=True,
            )
        return {
            "reason": "FRANKFURT_IDENTITY_VERIFIED",
            "mapping_id": result["mapping_id"],
            "warrant_listing_id": result["warrant_listing_id"],
        }

    async def _configure_vontobel(self, item: RefreshInstrument) -> dict[str, Any]:
        assert self.container.vontobel is not None
        await self._pace()
        async with self.container.database.session_context() as session:
            listing_id = await configure_vontobel(
                session, self.container.vontobel, workspace_id=self.workspace_id, warrant_id=item.id
            )
        return {"reason": "ISSUER_IDENTITY_VERIFIED", "warrant_listing_id": listing_id}

    async def _warrant(self, item: RefreshInstrument) -> dict[str, Any]:
        async with self.container.database.session_context() as session:
            listings = list(
                await session.scalars(
                    select(WarrantListingModel)
                    .join(
                        TradingVenueModel,
                        TradingVenueModel.id == WarrantListingModel.trading_venue_id,
                    )
                    .where(
                        WarrantListingModel.workspace_id == self.workspace_id,
                        WarrantListingModel.warrant_id == item.id,
                        WarrantListingModel.lifecycle_status == WarrantLifecycle.ACTIVE,
                        TradingVenueModel.is_active.is_(True),
                    )
                    .order_by(WarrantListingModel.id)
                )
            )
            mappings = list(
                await session.scalars(
                    select(WarrantProviderMappingModel).where(
                        WarrantProviderMappingModel.workspace_id == self.workspace_id,
                        WarrantProviderMappingModel.warrant_listing_id.in_(
                            [listing.id for listing in listings]
                        ),
                    )
                )
            )
        observations: list[dict[str, Any]] = []
        quotes: list[dict[str, Any]] = []
        for listing in listings:
            await self._pace()
            resolution = await self._resolver.resolve(
                WarrantQuoteRequest(
                    self.workspace_id,
                    listing.id,
                    uuid4(),
                    datetime.now(UTC),
                    expected_currency=listing.quotation_currency_code,
                )
            )
            observations.extend(asdict(attempt) for attempt in resolution.attempts)
            if resolution.result is not None and resolution.result.data is not None:
                quotes.append(
                    {
                        **asdict(resolution.result.data),
                        "provider": resolution.result.provider,
                        "retrieved_at": resolution.result.retrieved_at,
                    }
                )
        available = any(row["status"] == "AVAILABLE" for row in observations)
        return {
            "status": "AVAILABLE" if available else "MISSING",
            "reason": "QUOTE_OBSERVATIONS_AVAILABLE" if available else "NO_USABLE_WARRANT_QUOTE",
            "source_attempts": observations,
            "quotes": quotes,
            "mappings": [
                {"provider": m.provider, "status": m.status, "listing_id": m.warrant_listing_id}
                for m in mappings
            ],
            "active_listing_count": len(listings),
        }

    async def _configure_underlying(self, item: RefreshInstrument) -> dict[str, Any]:
        assert item.listing_id is not None
        await self._pace()
        return await discover_underlying(self.container, self.workspace_id, item.listing_id)

    async def _underlying(self, item: RefreshInstrument) -> dict[str, Any]:
        if self.container.eodhd is None:
            return {"status": "BLOCKED", "reason": "EODHD_DISABLED"}
        if item.listing_id is None:
            return {"status": "BLOCKED", "reason": "ACTIVE_UNDERLYING_LISTING_REQUIRED"}
        async with self.container.database.session_context() as session:
            mapping = await session.scalar(
                select(ProviderInstrumentMappingModel).where(
                    ProviderInstrumentMappingModel.workspace_id == self.workspace_id,
                    ProviderInstrumentMappingModel.listing_id == item.listing_id,
                    ProviderInstrumentMappingModel.provider == MarketDataProvider.EODHD,
                )
            )
            last_day = await session.scalar(
                select(func.max(DailyPriceModel.trading_date)).where(
                    DailyPriceModel.workspace_id == self.workspace_id,
                    DailyPriceModel.listing_id == item.listing_id,
                )
            )
        if (
            mapping is None
            or mapping.status != MappingStatus.ACTIVE
            or mapping.validated_at is None
        ):
            return {"status": "BLOCKED", "reason": "VALIDATED_EODHD_MAPPING_REQUIRED"}
        await self._pace()
        end = datetime.now(UTC).date() - timedelta(days=1)
        start = (
            max(end - timedelta(days=400), last_day - timedelta(days=7))
            if last_day
            else end - timedelta(days=400)
        )
        async with self.container.daily_price_import_service() as service:
            result = await service.import_daily_prices(
                DailyPriceRequest(
                    self.workspace_id,
                    item.listing_id,
                    mapping.id,
                    start,
                    end,
                    uuid4(),
                )
            )
        return {
            "status": "AVAILABLE" if result.processed else "MISSING",
            "reason": "COMPLETED_EOD_IMPORTED" if result.processed else "NO_COMPLETED_EOD_RETURNED",
            "provider": result.provider,
            "provider_identity": mapping.provider_symbol,
            "provider_exchange_code": mapping.provider_exchange_code,
            "retrieved_at": result.retrieved_at,
            "processed": result.processed,
            "price_type": "EOD",
            "execution_usable": False,
        }
