"""Read the reviewed universe; one explicit POST durably authorizes its setup."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.di import ApplicationContainer, get_container
from app.core.identity import RequestIdentity, get_request_identity
from app.features.market.service.chart_watchlist import ChartWatchlistService
from app.features.market.service.chart_watchlist_contracts import (
    ChartWatchlistActivationRequest,
    ChartWatchlistError,
    ChartWatchlistRefresh,
    ChartWatchlistResponse,
)
from app.features.market.service.types import Actor
from app.features.market_data.service.refresh import MarketDataRefreshRuntime

router = APIRouter(prefix="/api/v1/market-charts/watchlist", tags=["market-charts"])
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")


async def get_chart_watchlist_service(
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> AsyncIterator[ChartWatchlistService]:
    async with container.chart_watchlist_service(WORKSPACE_ID) as service:
        yield service


def _with_scheduler(response: ChartWatchlistResponse, request: Request) -> ChartWatchlistResponse:
    runtime: MarketDataRefreshRuntime = request.app.state.market_data_refresh
    status = runtime.status()
    scheduler = {
        key: status.get(key)
        for key in (
            "enabled",
            "running",
            "leader",
            "last_error",
            "underlying_price_type",
            "last_scan_at",
        )
    }
    scheduler["settings"] = {
        "underlyings_interval_seconds": status.get("settings", {}).get(
            "underlyings_interval_seconds"
        )
    }
    scheduler["provider_enabled"] = runtime.container.eodhd is not None
    refresh = {}
    for job in status.get("jobs", []):
        key = str(job.get("job", ""))
        if key.startswith("UNDERLYING_EOD:") and job.get("listing_id") is not None:
            target = f"listing:{job['listing_id']}"
        elif key.startswith("REFERENCE_EOD:") and job.get("market_reference_id") is not None:
            target = f"reference:{job['market_reference_id']}"
        else:
            continue
        refresh[target] = ChartWatchlistRefresh(
            status=job["status"],
            reason=job.get("reason"),
            checked_at=job.get("checked_at"),
            last_success_at=job.get("last_success_at"),
            next_run_at=job.get("next_run_at"),
        )
    return response.model_copy(
        update={
            "scheduler": scheduler,
            "items": tuple(
                item.model_copy(
                    update={"refresh": refresh.get(item.target_key) if item.target_key else None}
                )
                for item in response.items
            ),
        }
    )


@router.get("", response_model=ChartWatchlistResponse)
async def read_chart_watchlist(
    request: Request,
    service: Annotated[ChartWatchlistService, Depends(get_chart_watchlist_service)],
) -> ChartWatchlistResponse:
    return _with_scheduler(await service.read(), request)


@router.post("/activate", response_model=ChartWatchlistResponse)
async def activate_chart_watchlist(
    request: Request,
    body: ChartWatchlistActivationRequest,
    service: Annotated[ChartWatchlistService, Depends(get_chart_watchlist_service)],
    identity: Annotated[RequestIdentity, Depends(get_request_identity)],
) -> ChartWatchlistResponse:
    try:
        response = await service.activate(
            catalog_version=body.catalog_version,
            confirmed=body.confirmed,
            actor=Actor(identity.actor_id, identity.actor_name),
        )
    except ChartWatchlistError as error:
        raise HTTPException(status_code=error.status_code, detail=error.code) from error
    runtime: MarketDataRefreshRuntime = request.app.state.market_data_refresh
    runtime.wake.set()
    return _with_scheduler(response, request)
