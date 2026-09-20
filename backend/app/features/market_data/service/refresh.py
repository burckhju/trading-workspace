"""Catalog-driven refresh using existing quote providers, mappings and daily imports."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from enum import StrEnum
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
from app.providers.frankfurt_quotes.schema import FrankfurtSourceError
from app.providers.vontobel_markets.configure import configure_warrant as configure_vontobel
from app.providers.vontobel_markets.issuer import supports_issuer_probe

if TYPE_CHECKING:
    from app.core.di import ApplicationContainer

logger = logging.getLogger(__name__)


class RefreshLane(StrEnum):
    WARRANTS = "WARRANTS"
    WARRANT_DISCOVERY = "WARRANT_DISCOVERY"
    UNDERLYINGS = "UNDERLYINGS"


type ScheduledJob = tuple[str, RefreshInstrument, int, Callable[[], Awaitable[dict[str, Any]]]]


def _job_lane(key: str) -> RefreshLane:
    if key.startswith(("FRANKFURT_MAPPING:", "VONTOBEL_MAPPING:")):
        return RefreshLane.WARRANT_DISCOVERY
    if key.startswith(("EODHD_MAPPING:", "UNDERLYING_EOD:")):
        return RefreshLane.UNDERLYINGS
    return RefreshLane.WARRANTS


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
        self._next_underlying_request = 0.0
        self._lane_tasks: dict[RefreshLane, asyncio.Task[None]] = {}
        self._current_jobs: dict[RefreshLane, str | None] = dict.fromkeys(RefreshLane)
        self._lane_errors: dict[RefreshLane, str | None] = dict.fromkeys(RefreshLane)
        self.last_scan_at: datetime | None = None
        self.last_error: str | None = None
        self.leader = False
        self.wake = asyncio.Event()
        self._resolver = build_warrant_quote_resolver(container)

    @property
    def running(self) -> bool:
        return self._lock.locked() or any(not task.done() for task in self._lane_tasks.values())

    @property
    def current_job(self) -> str | None:
        # Compatibility with clients displaying one job. The complete status is
        # in lanes/current_jobs, since multiple lanes may be active at the same time.
        return next((job for job in self._current_jobs.values() if job is not None), None)

    def _schedule_counts(self, keys: Iterable[str], now: float) -> dict[str, int | float]:
        # Pending is a first-check counter. Completed jobs can still be due or
        # overdue; exclude work already in flight from the waiting backlog.
        waiting = [key for key in keys if key not in self._current_jobs.values()]
        overdue = [now - self._due[key] for key in waiting if self._due.get(key, now) < now]
        return {
            "due_jobs": sum(self._due.get(key, now) <= now for key in waiting),
            "overdue_jobs": len(overdue),
            "max_overdue_seconds": max(overdue, default=0.0),
            "deferred_jobs": sum(self.jobs[key]["status"] == "DEFERRED" for key in waiting),
        }

    def status(self) -> dict[str, Any]:
        now = self.timer()
        return {
            "enabled": self.settings.enabled,
            "running": self.running,
            "leader": self.leader,
            "workspace_id": self.workspace_id,
            "settings": self.settings.model_dump(mode="json"),
            "last_scan_at": self.last_scan_at,
            "last_error": self.last_error
            or next((error for error in self._lane_errors.values() if error is not None), None),
            "single_instance_only": True,
            "quote_storage": "DATABASE_LAST_SUCCESS_WITH_ORIGINAL_TIMESTAMPS",
            "underlying_price_type": "COMPLETED_EOD",
            "current_job": self.current_job,
            "current_jobs": dict(self._current_jobs),
            "scheduling_mode": "INDEPENDENT_WARRANT_QUOTE_DISCOVERY_UNDERLYING_LANES",
            "lanes": {
                lane.value: {
                    "running": lane in self._lane_tasks and not self._lane_tasks[lane].done(),
                    "current_job": self._current_jobs[lane],
                    "last_error": self._lane_errors[lane],
                    "pending_jobs": sum(
                        job["status"] == "PENDING"
                        for key, job in self.jobs.items()
                        if _job_lane(key) == lane
                    ),
                    **self._schedule_counts(
                        (key for key in self.jobs if _job_lane(key) == lane), now
                    ),
                }
                for lane in RefreshLane
            },
            "pending_jobs": sum(job["status"] == "PENDING" for job in self.jobs.values()),
            **self._schedule_counts(self.jobs, now),
            "jobs": list(self.jobs.values()),
        }

    async def run_once(self, *, wait_for_completion: bool = True) -> None:
        """Refresh the catalog and dispatch each idle lane without duplicating workers.

        The leader calls with wait_for_completion=False so the next catalog scan,
        lock heartbeat and a completed lane never wait for the other lane's batch.
        Awaiting all lanes remains useful for explicit one-shot runs and tests.
        """
        if not self.settings.enabled:
            await self.stop()
            return
        if self._lock.locked():
            return
        async with self._lock:
            try:
                warrants, underlyings = await read_catalog(
                    self.container.database, self.workspace_id
                )
                self.last_scan_at = datetime.now(UTC)
                self.last_error = None
                schedule: list[ScheduledJob] = []
                # Refresh all active master data, including products without a position.
                for item in warrants:
                    if self.settings.auto_configure:
                        if (
                            self.container.frankfurt is not None
                            and self.container.frankfurt.settings.source_mode
                            is FrankfurtSourceMode.PUBLIC_WEBSITE
                        ):
                            key = f"FRANKFURT_MAPPING:{item.id}"
                            schedule.append(
                                (
                                    key,
                                    item,
                                    self.settings.discovery_interval_seconds,
                                    partial(self._configure_frankfurt, item),
                                )
                            )
                        if self.container.vontobel is not None and supports_issuer_probe(
                            item.issuer
                        ):
                            key = f"VONTOBEL_MAPPING:{item.id}"
                            schedule.append(
                                (
                                    key,
                                    item,
                                    self.settings.discovery_interval_seconds,
                                    partial(self._configure_vontobel, item),
                                )
                            )
                    key = f"WARRANT_QUOTES:{item.id}"
                    schedule.append(
                        (
                            key,
                            item,
                            self.settings.warrants_interval_seconds,
                            partial(self._warrant, item),
                        )
                    )
                for item in underlyings:
                    if self.settings.auto_configure and item.listing_id is not None:
                        key = f"EODHD_MAPPING:{item.id}:{item.listing_id}"
                        schedule.append(
                            (
                                key,
                                item,
                                self.settings.discovery_interval_seconds,
                                partial(self._configure_underlying, item),
                            )
                        )
                    key = f"UNDERLYING_EOD:{item.id}:{item.listing_id}"
                    schedule.append(
                        (
                            key,
                            item,
                            self.settings.underlyings_interval_seconds,
                            partial(self._underlying, item),
                        )
                    )
                schedule.sort(key=lambda job: not job[1].held)
                self.jobs = {
                    key: {
                        "job": key,
                        "instrument_id": item.id,
                        "listing_id": item.listing_id,
                        "name": item.name,
                        "isin": item.isin,
                        "status": "PENDING",
                        "reason": "AWAITING_FIRST_REFRESH",
                        "checked_at": None,
                        "last_success_at": None,
                        "next_run_at": None,
                        **self.jobs.get(key, {}),
                        "held": item.held,
                        "lane": _job_lane(key).value,
                    }
                    for key, item, _interval, _operation in schedule
                }
                self._due = {key: value for key, value in self._due.items() if key in self.jobs}
                for lane in RefreshLane:
                    previous = self._lane_tasks.get(lane)
                    if previous is not None and not previous.done():
                        continue
                    lane_schedule = [job for job in schedule if _job_lane(job[0]) == lane]
                    if lane_schedule:
                        self._lane_tasks[lane] = asyncio.create_task(
                            self._run_lane(lane, lane_schedule),
                            name=f"market-data-{lane.value.lower()}",
                        )
                if wait_for_completion:
                    await asyncio.gather(*self._lane_tasks.values())
            except asyncio.CancelledError:
                await self.stop()
                raise
            except Exception as exc:
                await self.stop()
                self.last_error = type(exc).__name__
                logger.exception("market_data_catalog_refresh_failed")

    async def _run_lane(self, lane: RefreshLane, schedule: list[ScheduledJob]) -> None:
        self._lane_errors[lane] = None
        try:
            for key, item, interval, operation in schedule:
                # A later catalog scan can remove queued inactive instruments.
                if key in self.jobs:
                    await self._job(key, item, interval, operation, catalog_job=True)
            if lane is RefreshLane.WARRANT_DISCOVERY:
                await self._retry_quotes_after_discovery(schedule)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self._lane_errors[lane] = type(exc).__name__
            logger.exception("market_data_lane_failed", extra={"lane": lane.value})

    async def _retry_quotes_after_discovery(
        self, schedule: list[ScheduledJob]
    ) -> None:
        """Retry quotes that missed a route before same-cycle discovery succeeded."""

        quote_task = self._lane_tasks.get(RefreshLane.WARRANTS)
        current_task = asyncio.current_task()
        if quote_task is not None and quote_task is not current_task and not quote_task.done():
            await quote_task

        latest_discovery_success: dict[Any, tuple[RefreshInstrument, datetime]] = {}
        for key, item, _interval, _operation in schedule:
            job = self.jobs.get(key)
            checked_at = None if job is None else job.get("checked_at")
            if job is None or job.get("status") != "AVAILABLE" or checked_at is None:
                continue
            previous = latest_discovery_success.get(item.id)
            if previous is None or checked_at > previous[1]:
                latest_discovery_success[item.id] = (item, checked_at)

        for item, discovery_checked_at in latest_discovery_success.values():
            quote_key = f"WARRANT_QUOTES:{item.id}"
            quote_job = self.jobs.get(quote_key)
            if (
                quote_job is None
                or quote_job.get("status") != "MISSING"
                or quote_job.get("reason") != "NO_USABLE_WARRANT_QUOTE"
            ):
                continue

            quote_checked_at = quote_job.get("checked_at")
            if quote_checked_at is None or quote_checked_at >= discovery_checked_at:
                continue

            self._due.pop(quote_key, None)
            await self._job(
                quote_key,
                item,
                self.settings.warrants_interval_seconds,
                partial(self._warrant, item),
                catalog_job=True,
            )

    async def stop(self) -> None:
        """Cancel and join all workers before the runner releases its leader lock."""
        tasks = tuple(self._lane_tasks.values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self._lane_tasks.clear()

    async def _job(
        self,
        key: str,
        item: RefreshInstrument,
        interval: int,
        operation: Callable[[], Awaitable[dict[str, Any]]],
        *,
        catalog_job: bool = False,
    ) -> None:
        if self.timer() < self._due.get(key, 0):
            return
        previous = self.jobs.get(key, {})
        retry_delay: float = interval
        lane = _job_lane(key)
        self._current_jobs[lane] = key
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
            details = {
                "reason": (
                    str(exc)
                    if isinstance(exc, (ValueError, FrankfurtSourceError))
                    else type(exc).__name__
                )
            }
            status = "ERROR"
            success_at = previous.get("last_success_at")
            if isinstance(exc, FrankfurtSourceError) and str(exc) == "FRANKFURT_REQUEST_THROTTLED":
                # A competing API request may consume the slot after _pace().
                # No provider request failed: retry after the shared cooldown,
                # rather than waiting the full (normally hourly) discovery interval.
                retry_delay = max(
                    1.0,
                    self.settings.request_spacing_seconds,
                    self._next_request - self.timer(),
                    (
                        self.container.frankfurt.snapshots.request_delay_seconds()
                        if self.container.frankfurt is not None
                        else 0.0
                    ),
                )
                status = "DEFERRED"
                details["retry_after_seconds"] = retry_delay
        finally:
            self._current_jobs[lane] = None
        if catalog_job and key not in self.jobs:
            return
        completed = datetime.now(UTC)
        self._due[key] = self.timer() + retry_delay
        self.jobs[key] = {
            "job": key,
            "instrument_id": item.id,
            "listing_id": item.listing_id,
            "name": item.name,
            "isin": item.isin,
            "held": self.jobs.get(key, {}).get("held", item.held),
            "lane": lane.value,
            "status": status,
            "checked_at": completed,
            "last_success_at": success_at,
            "next_run_at": completed + timedelta(seconds=retry_delay),
            **details,
        }

    async def _pace(self) -> None:
        delay = self._next_request - self.timer()
        if self.container.frankfurt is not None:
            delay = max(delay, self.container.frankfurt.snapshots.request_delay_seconds())
        if delay > 0:
            await asyncio.sleep(delay)
        spacing = self.settings.request_spacing_seconds
        if self.container.frankfurt is not None:
            spacing = max(spacing, self.container.frankfurt.settings.refresh_interval_seconds)
        self._next_request = self.timer() + spacing

    async def _pace_underlying(self) -> None:
        # Licensed EODHD work is independent of the public Frankfurt cooldown.
        # Adapter-internal requests still share EODHD's limiter, quota and retries.
        delay = self._next_underlying_request - self.timer()
        if delay > 0:
            await asyncio.sleep(delay)
        self._next_underlying_request = self.timer() + self.settings.request_spacing_seconds

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
        await self._pace_underlying()
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
        await self._pace_underlying()
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
