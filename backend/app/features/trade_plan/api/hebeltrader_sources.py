"""Source-first Hebeltrader review; never ask the user to invent model inputs."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal, DecimalException
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_database_session
from app.features.learning.persistence.models import (
    ExternalObservationModel,
    ExternalObservationVersionModel,
)
from app.features.trade_plan.api.hebeltrader_router import (
    PreviewRequest,
    PreviewResponse,
    QuoteRequest,
    StrictRequest,
    preview,
)
from app.features.trade_plan.domain.hebeltrader import Levels, diagnose_bands

router = APIRouter(prefix="/api/v1/trade-plans/strategies/hebeltrader", tags=["hebeltrader"])
# Same local workspace boundary as the existing TradePlan routes.
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")


class SourceAxis(BaseModel):
    currency: str | None
    values: dict[str, str | None]
    reward_risk: str | None = None
    band_deviation: str | None = None
    issues: list[str]


class SourceSnapshot(BaseModel):
    version_id: UUID
    underlying_id: UUID
    label: str
    issue_date: date | None
    filename: str | None
    content_hash: str | None
    stock: SourceAxis
    warrant: SourceAxis
    source_issues: list[str]
    scope: Literal["PUBLISHED_SNAPSHOT_NOT_LIVE"] = "PUBLISHED_SNAPSHOT_NOT_LIVE"


class SourceList(BaseModel):
    items: list[SourceSnapshot]
    has_more: bool
    next_offset: int | None


def _text(payload: dict[str, object], key: str) -> str | None:
    value = payload.get(key)
    return value.strip() if isinstance(value, str) and value.strip() else None


def _price(payload: dict[str, object], key: str, factor: Decimal) -> str | None:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, str | int | float | Decimal):
        return None
    try:
        result = Decimal(str(value)) * factor
    except DecimalException:
        return None
    if not result.is_finite() or not 0 < result <= Decimal("1e12"):
        return None
    return str(result)


def source_axis(payload: dict[str, object], *, stock: bool) -> SourceAxis:
    prefix = "underlying" if stock else "derivative"
    currency = _text(payload, f"{prefix}_currency")
    factor = Decimal("0.01") if currency == "GBp" else Decimal("1")
    issues = []
    if currency == "GBp":
        currency = "GBP"
        issues.append("GBp wurde nachvollziehbar durch 100 in GBP umgerechnet.")
    if (
        currency is None
        or len(currency) != 3
        or not currency.isascii()
        or not currency.isalpha()
        or not currency.isupper()
    ):
        currency = None
        issues.append("Währung fehlt oder ist nicht eindeutig; keine aktuelle Einstiegsprüfung.")
    fields = {
        "entry": "underlying_price" if stock else "derivative_indicated_price",
        "stop": f"{prefix}_stop_1",
        "target1": f"{prefix}_target_1",
        "target2": f"{prefix}_target_2",
    }
    if stock:
        fields.update(gd200="gd200", gd50="gd50")
    values = {name: _price(payload, field, factor) for name, field in fields.items()}
    for name, value in values.items():
        if value is None:
            issues.append(f"Quellenwert {name} fehlt oder ist ungültig; wird nicht geschätzt.")
    axis = SourceAxis(currency=currency, values=values, issues=issues)
    if all(values[key] is not None for key in ("entry", "stop", "target1", "target2")):
        try:
            levels = Levels(
                **{
                    key: Decimal(values[key] or "0")
                    for key in ("entry", "stop", "target1", "target2")
                }
            )
        except ValueError:
            axis.issues.append(
                "Widersprüchliche Marken: erforderlich ist Stopp < Einstieg < T1 < T2."
            )
        else:
            axis.reward_risk = str(levels.reward_risk)
            if stock and values.get("gd200") is not None:
                diagnostic = diagnose_bands(levels, Decimal(values["gd200"] or "0"))
                axis.band_deviation = str(diagnostic.relative_deviation)
                if diagnostic.status == "REVIEW":
                    axis.issues.append("Zielstaffelung weicht um mehr als 2 % vom GD200-Modell ab.")
    return axis


def source_snapshot(version: ExternalObservationVersionModel) -> SourceSnapshot:
    payload = version.source_metadata or {}
    issues = []
    try:
        issue_date = date.fromisoformat(_text(payload, "issue_date") or "")
    except ValueError:
        issue_date = None
        issues.append("Ausgabedatum fehlt oder ist ungültig.")
    if issue_date is not None and issue_date > datetime.now(UTC).date():
        issues.append("Ausgabedatum liegt in der Zukunft; keine aktuelle Einstiegsprüfung.")
    source_file = payload.get("source_file")
    filename = None
    content_hash = None
    if isinstance(source_file, dict):
        filename = _text(source_file, "filename")
        content_hash = _text(source_file, "content_hash")
    if filename is None or content_hash is None:
        issues.append("Dateinachweis fehlt; keine aktuelle Einstiegsprüfung.")
    if payload.get("validation_issues"):
        issues.append("Der Import enthält Quellenwarnungen; vor einer Nutzung prüfen.")
    name = _text(payload, "underlying_name") or "Basiswert"
    reference = version.external_reference or "ohne Ausgabenummer"
    return SourceSnapshot(
        version_id=version.id,
        underlying_id=version.underlying_id,
        label=f"{name} · Hebeltrader {reference}",
        issue_date=issue_date,
        filename=filename,
        content_hash=content_hash,
        stock=source_axis(payload, stock=True),
        warrant=source_axis(payload, stock=False),
        source_issues=issues,
    )


class SourceReader:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def versions(
        self, underlying_id: UUID, *, version_id: UUID | None = None, offset: int = 0
    ) -> list[ExternalObservationVersionModel]:
        query = (
            select(ExternalObservationVersionModel)
            .join(
                ExternalObservationModel,
                (
                    ExternalObservationModel.id
                    == ExternalObservationVersionModel.external_observation_id
                )
                & (
                    ExternalObservationModel.current_version_id
                    == ExternalObservationVersionModel.id
                ),
            )
            .where(
                ExternalObservationModel.workspace_id == WORKSPACE_ID,
                ExternalObservationVersionModel.underlying_id == underlying_id,
                ExternalObservationVersionModel.source_name == "HEBELTRADER",
                ExternalObservationVersionModel.recording_method == "FILE_IMPORT",
            )
            .order_by(
                ExternalObservationVersionModel.observed_at.desc(),
                ExternalObservationVersionModel.id,
            )
        )
        if version_id is not None:
            query = query.where(ExternalObservationVersionModel.id == version_id)
        result = await self.session.scalars(query.offset(offset).limit(51))
        return list(result)


def get_source_reader(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> SourceReader:
    return SourceReader(session)


@router.get("/sources", response_model=SourceList)
async def sources(
    underlying_id: UUID,
    reader: Annotated[SourceReader, Depends(get_source_reader)],
    offset: Annotated[int, Query(ge=0)] = 0,
) -> SourceList:
    versions = await reader.versions(underlying_id, offset=offset)
    return SourceList(
        items=[source_snapshot(version) for version in versions[:50]],
        has_more=len(versions) > 50,
        next_offset=offset + 50 if len(versions) > 50 else None,
    )


class SourcePreviewRequest(StrictRequest):
    underlying_id: UUID
    source_version_id: UUID
    quote: QuoteRequest | None = None
    fundamental_ok: bool = False
    target_history: Literal["UNKNOWN", "NOT_REACHED", "TARGET1_REACHED", "TARGET2_REACHED"] = (
        "UNKNOWN"
    )


class SourcePreviewResponse(BaseModel):
    source: SourceSnapshot
    current_preview: PreviewResponse | None = None
    missing_data: list[str]
    execution_enabled: Literal[False] = False


@router.post("/source-preview", response_model=SourcePreviewResponse)
async def source_preview(
    request: SourcePreviewRequest,
    reader: Annotated[SourceReader, Depends(get_source_reader)],
) -> SourcePreviewResponse:
    versions = await reader.versions(request.underlying_id, version_id=request.source_version_id)
    if not versions:
        raise HTTPException(status_code=404, detail="Importierte Empfehlung nicht verfügbar.")
    source = source_snapshot(versions[0])
    missing = list(source.source_issues)
    values = source.stock.values
    if source.stock.reward_risk is None or source.stock.currency is None:
        missing.append("Eindeutige Aktienmarken und Währung fehlen.")
    if source.issue_date is None or values.get("gd200") is None:
        missing.append("Ausgabedatum oder GD200 fehlen in der Quelle.")
    if request.quote is None:
        missing.append("Kein aktueller Geld-/Briefkurs: nur Quellenszenario, keine Einstiegsfreigabe.")
    elif request.quote.currency != source.stock.currency:
        raise HTTPException(status_code=422, detail="Kurswährung passt nicht zur Empfehlung.")
    if request.target_history == "UNKNOWN":
        missing.append("Zielhistorie nicht belegt; frühere Zielerreichung wird nicht ausgeschlossen.")
    if missing:
        return SourcePreviewResponse(source=source, missing_data=missing)
    # These values come from the selected immutable source, never from invented defaults.
    current = preview(
        PreviewRequest.model_validate(
            {
                "as_of": datetime.now(UTC),
                "analysis_date": source.issue_date,
                "source_ref": f"ExternalObservationVersion:{source.version_id}; {source.filename}",
                "quote": request.quote,
                "gd200": values["gd200"],
                "gd50": values.get("gd50"),
                "published_levels": {
                    key: values[key] for key in ("entry", "stop", "target1", "target2")
                },
                "fundamental_ok": request.fundamental_ok,
                "target1_seen": request.target_history in ("TARGET1_REACHED", "TARGET2_REACHED"),
                "target2_seen": request.target_history == "TARGET2_REACHED",
            }
        )
    )
    return SourcePreviewResponse(source=source, current_preview=current, missing_data=[])
