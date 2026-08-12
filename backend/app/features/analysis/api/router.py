"""Versioned REST API for reproducible market analysis."""

from __future__ import annotations

import csv
from datetime import datetime
from io import StringIO
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response, status

from app.core.exceptions import ApplicationError
from app.features.analysis.api.dependencies import get_market_analysis_service
from app.features.analysis.api.dtos import (
    AnalysisDetailResponse,
    AnalysisEventResponse,
    AnalysisOverviewPageResponse,
    AnalysisOverviewResponse,
    AnalysisRunDetailResponse,
    AnalysisSummaryResponse,
    AnalysisVerificationResponse,
    CreateAnalysisRequest,
    CriterionResponse,
    RetryAnalysisRequest,
    RunAnalysisRequest,
    RunSummaryResponse,
    SnapshotPageResponse,
    SnapshotRowResponse,
    SupersedeAnalysisRequest,
)
from app.features.analysis.api.errors import translate_analysis_error
from app.features.analysis.domain.errors import AnalysisError
from app.features.analysis.persistence.repositories import AnalysisOverviewFilter
from app.features.analysis.service.application import MarketAnalysisService

router = APIRouter(prefix="/api/v1/market-analyses", tags=["market-analyses"])
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")


def _analysis(model: Any) -> AnalysisSummaryResponse:
    return AnalysisSummaryResponse(
        id=model.id,
        underlying_id=model.underlying_id,
        listing_id=model.listing_id,
        created_at=model.created_at,
        created_by=model.created_by,
    )


def _run(model: Any) -> RunSummaryResponse:
    return RunSummaryResponse(
        version=model.version,
        status=model.status,
        quality_status=model.quality_status,
        model_id=model.model_id,
        model_version=model.model_version,
        observation_count=model.observation_count,
        analysis_time=model.analysis_time,
        input_hash=model.input_hash,
    )


def _event(model: Any) -> AnalysisEventResponse:
    return AnalysisEventResponse(
        id=model.id,
        version=model.version,
        event_type=model.event_type,
        from_status=model.from_status,
        to_status=model.to_status,
        source_version=model.source_version,
        replacement_version=model.replacement_version,
        reason=model.reason,
        correlation_id=model.correlation_id,
        occurred_at=model.occurred_at,
    )


def _raise(exc: AnalysisError) -> None:
    raise translate_analysis_error(exc) from exc


def _overview_filters(
    underlying_id: UUID | None,
    status_filter: str | None,
    quality_status: str | None,
    analysis_time_from: datetime | None,
    analysis_time_to: datetime | None,
    sort_by: str,
    sort_direction: str,
) -> AnalysisOverviewFilter:
    return AnalysisOverviewFilter(
        underlying_id=underlying_id,
        status=status_filter,
        quality_status=quality_status,
        analysis_time_from=analysis_time_from,
        analysis_time_to=analysis_time_to,
        sort_by=sort_by,
        sort_direction=sort_direction,
    )


@router.post(
    "", response_model=AnalysisSummaryResponse, status_code=status.HTTP_201_CREATED
)
async def create_analysis(
    request: CreateAnalysisRequest,
    service: Annotated[MarketAnalysisService, Depends(get_market_analysis_service)],
    actor: Annotated[str | None, Header(alias="X-Actor-Name")] = None,
) -> AnalysisSummaryResponse:
    try:
        return _analysis(
            await service.create(
                WORKSPACE_ID,
                request.underlying_id,
                request.listing_id,
                actor or "Trading Workspace User",
            )
        )
    except AnalysisError as exc:
        _raise(exc)
        raise AssertionError("unreachable") from exc


@router.get("", response_model=list[AnalysisSummaryResponse])
async def list_analyses(
    service: Annotated[MarketAnalysisService, Depends(get_market_analysis_service)],
) -> list[AnalysisSummaryResponse]:
    return [_analysis(item) for item in await service.list(WORKSPACE_ID)]


@router.get("/page", response_model=AnalysisOverviewPageResponse)
async def list_analysis_page(
    service: Annotated[MarketAnalysisService, Depends(get_market_analysis_service)],
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    underlying_id: UUID | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    quality_status: str | None = None,
    analysis_time_from: datetime | None = None,
    analysis_time_to: datetime | None = None,
    sort_by: Literal[
        "created_at",
        "underlying_name",
        "latest_analysis_time",
        "latest_status",
        "latest_quality_status",
    ] = "created_at",
    sort_direction: Literal["asc", "desc"] = "desc",
) -> AnalysisOverviewPageResponse:
    filters = _overview_filters(
        underlying_id,
        status_filter,
        quality_status,
        analysis_time_from,
        analysis_time_to,
        sort_by,
        sort_direction,
    )
    rows, total = await service.overview(WORKSPACE_ID, offset, limit, filters)
    return AnalysisOverviewPageResponse(
        items=[
            AnalysisOverviewResponse(
                **_analysis(row.analysis).model_dump(),
                underlying_name=row.underlying_name,
                ticker=row.ticker,
                trading_venue_mic=row.trading_venue_mic,
                trading_venue_name=row.trading_venue_name,
                currency_code=row.currency_code,
                latest_version=row.latest_version,
                latest_status=row.latest_status,
                latest_quality_status=row.latest_quality_status,
                latest_analysis_time=row.latest_analysis_time,
            )
            for row in rows
        ],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/export.csv")
async def export_analysis_overview_csv(
    service: Annotated[MarketAnalysisService, Depends(get_market_analysis_service)],
    underlying_id: UUID | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    quality_status: str | None = None,
    analysis_time_from: datetime | None = None,
    analysis_time_to: datetime | None = None,
    sort_by: Literal[
        "created_at",
        "underlying_name",
        "latest_analysis_time",
        "latest_status",
        "latest_quality_status",
    ] = "created_at",
    sort_direction: Literal["asc", "desc"] = "desc",
) -> Response:
    filters = _overview_filters(
        underlying_id,
        status_filter,
        quality_status,
        analysis_time_from,
        analysis_time_to,
        sort_by,
        sort_direction,
    )
    rows, _ = await service.overview(WORKSPACE_ID, 0, 10000, filters)
    output = StringIO(newline="")
    writer = csv.writer(output, delimiter=";")
    writer.writerow(
        [
            "Analyse-ID",
            "Basiswert",
            "Ticker",
            "MIC",
            "Handelsplatz",
            "Währung",
            "Letzte Version",
            "Status",
            "Qualitätsstatus",
            "Analysezeitpunkt",
            "Erstellt am",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row.analysis.id,
                row.underlying_name,
                row.ticker,
                row.trading_venue_mic,
                row.trading_venue_name,
                row.currency_code,
                row.latest_version or "",
                row.latest_status or "",
                row.latest_quality_status or "",
                (
                    row.latest_analysis_time.isoformat()
                    if row.latest_analysis_time
                    else ""
                ),
                row.analysis.created_at.isoformat(),
            ]
        )
    return Response(
        content="\ufeff" + output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="market-analyses.csv"'},
    )


@router.get("/{analysis_id}", response_model=AnalysisDetailResponse)
async def get_analysis(
    analysis_id: UUID,
    service: Annotated[MarketAnalysisService, Depends(get_market_analysis_service)],
) -> AnalysisDetailResponse:
    try:
        analysis, runs = await service.get(WORKSPACE_ID, analysis_id)
        return AnalysisDetailResponse(
            analysis=_analysis(analysis), runs=[_run(item) for item in runs]
        )
    except AnalysisError as exc:
        _raise(exc)
        raise AssertionError("unreachable") from exc


@router.post(
    "/{analysis_id}/runs",
    response_model=RunSummaryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def run_analysis(
    analysis_id: UUID,
    request: RunAnalysisRequest,
    service: Annotated[MarketAnalysisService, Depends(get_market_analysis_service)],
    correlation_id: Annotated[str | None, Header(alias="X-Correlation-ID")] = None,
) -> RunSummaryResponse:
    if request.end_date < request.start_date:
        raise ApplicationError(
            code="INVALID_DATE_RANGE",
            message="end_date must not precede start_date",
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    try:
        return _run(
            await service.run(
                WORKSPACE_ID,
                analysis_id,
                request.start_date,
                request.end_date,
                request.parameters.to_domain(),
                correlation_id,
            )
        )
    except AnalysisError as exc:
        _raise(exc)
        raise AssertionError("unreachable") from exc


@router.get("/{analysis_id}/runs/{version}", response_model=AnalysisRunDetailResponse)
async def get_run(
    analysis_id: UUID,
    version: int,
    service: Annotated[MarketAnalysisService, Depends(get_market_analysis_service)],
    include_snapshot: bool = Query(default=True),
) -> AnalysisRunDetailResponse:
    try:
        analysis, run, criteria, snapshot = await service.details(
            WORKSPACE_ID, analysis_id, version, include_snapshot
        )
        return AnalysisRunDetailResponse(
            analysis=_analysis(analysis),
            run=_run(run),
            parameters=run.parameters,
            metrics=run.metrics,
            notes=run.notes,
            data_sources=run.data_sources,
            criteria=[
                CriterionResponse(
                    code=item.code,
                    classification=item.classification,
                    value=None if item.value is None else str(item.value),
                    explanation=item.explanation,
                )
                for item in criteria
            ],
            snapshot=[
                SnapshotRowResponse(
                    trading_date=item.trading_date,
                    open=str(item.open),
                    high=str(item.high),
                    low=str(item.low),
                    close=str(item.close),
                    adjusted_close=(
                        None
                        if item.adjusted_close is None
                        else str(item.adjusted_close)
                    ),
                    volume=None if item.volume is None else str(item.volume),
                    currency=item.currency,
                    provider=item.provider,
                    provider_symbol=item.provider_symbol,
                    quality_status=item.quality_status,
                    warnings=item.warnings,
                )
                for item in snapshot
            ],
        )
    except AnalysisError as exc:
        _raise(exc)
        raise AssertionError("unreachable") from exc


@router.get(
    "/{analysis_id}/runs/{version}/snapshot", response_model=SnapshotPageResponse
)
async def get_snapshot(
    analysis_id: UUID,
    version: int,
    service: Annotated[MarketAnalysisService, Depends(get_market_analysis_service)],
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> SnapshotPageResponse:
    try:
        rows, total = await service.snapshot(
            WORKSPACE_ID, analysis_id, version, offset, limit
        )
        return SnapshotPageResponse(
            items=[
                SnapshotRowResponse(
                    trading_date=item.trading_date,
                    open=str(item.open),
                    high=str(item.high),
                    low=str(item.low),
                    close=str(item.close),
                    adjusted_close=(
                        None
                        if item.adjusted_close is None
                        else str(item.adjusted_close)
                    ),
                    volume=None if item.volume is None else str(item.volume),
                    currency=item.currency,
                    provider=item.provider,
                    provider_symbol=item.provider_symbol,
                    quality_status=item.quality_status,
                    warnings=item.warnings,
                )
                for item in rows
            ],
            total=total,
            offset=offset,
            limit=limit,
        )
    except AnalysisError as exc:
        _raise(exc)
        raise AssertionError("unreachable") from exc


@router.post(
    "/{analysis_id}/runs/{version}/retry",
    response_model=RunSummaryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def retry_analysis(
    analysis_id: UUID,
    version: int,
    request: RetryAnalysisRequest,
    service: Annotated[MarketAnalysisService, Depends(get_market_analysis_service)],
    correlation_id: Annotated[str | None, Header(alias="X-Correlation-ID")] = None,
) -> RunSummaryResponse:
    try:
        return _run(
            await service.retry(
                WORKSPACE_ID, analysis_id, version, correlation_id, request.reason
            )
        )
    except AnalysisError as exc:
        _raise(exc)
        raise AssertionError("unreachable") from exc


@router.post(
    "/{analysis_id}/runs/{version}/supersede",
    response_model=AnalysisEventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def supersede_analysis(
    analysis_id: UUID,
    version: int,
    request: SupersedeAnalysisRequest,
    service: Annotated[MarketAnalysisService, Depends(get_market_analysis_service)],
    correlation_id: Annotated[str | None, Header(alias="X-Correlation-ID")] = None,
) -> AnalysisEventResponse:
    try:
        return _event(
            await service.supersede(
                WORKSPACE_ID,
                analysis_id,
                version,
                request.replacement_version,
                correlation_id,
                request.reason,
            )
        )
    except AnalysisError as exc:
        _raise(exc)
        raise AssertionError("unreachable") from exc


@router.get("/{analysis_id}/events", response_model=list[AnalysisEventResponse])
async def list_analysis_events(
    analysis_id: UUID,
    service: Annotated[MarketAnalysisService, Depends(get_market_analysis_service)],
) -> list[AnalysisEventResponse]:
    try:
        return [
            _event(item) for item in await service.events(WORKSPACE_ID, analysis_id)
        ]
    except AnalysisError as exc:
        _raise(exc)
        raise AssertionError("unreachable") from exc


@router.post(
    "/{analysis_id}/runs/{version}/verify", response_model=AnalysisVerificationResponse
)
async def verify_analysis_reproducibility(
    analysis_id: UUID,
    version: int,
    service: Annotated[MarketAnalysisService, Depends(get_market_analysis_service)],
) -> AnalysisVerificationResponse:
    try:
        return AnalysisVerificationResponse(
            **await service.verify_reproducibility(WORKSPACE_ID, analysis_id, version)
        )
    except AnalysisError as exc:
        _raise(exc)
        raise AssertionError("unreachable") from exc
