"""Explicit risk evaluation/configuration commands; GET is persisted-input only."""

from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.di import ApplicationContainer, get_container
from app.features.position_monitoring.domain.risk_signals import RiskParameters
from app.features.position_monitoring.service.risk import (
    PositionRiskService,
    RiskConfigurationConflict,
)
from app.features.position_monitoring.service.risk_contracts import (
    PositionRiskView,
    RiskConfiguration,
)

router = APIRouter()
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")
LOCAL_ACTOR_ID = UUID("00000000-0000-4000-8000-000000000002")


class RiskPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    parameters: RiskParameters

    @field_validator("parameters", mode="before")
    @classmethod
    def explicit_parameter_types(cls, value: object) -> object:
        if isinstance(value, dict):
            allowed = {
                "hysteresis_fraction",
                "confirmation_sessions",
                "volatility_high",
                "volatility_reset",
                "maximum_age_days",
            }
            if set(value) - allowed:
                raise ValueError("Unknown risk parameter")
            for key in ("confirmation_sessions", "maximum_age_days"):
                if key in value and type(value[key]) is not int:
                    raise ValueError(f"{key} must be an integer")
        return value


class RiskConfigurationRequest(RiskPreviewRequest):
    enabled: bool = Field(strict=True)
    expected_revision: int = Field(ge=0, strict=True)
    confirmation: Literal["CONFIRM_POSITION_RISK_CONFIGURATION"]


@router.get("/trades/{trade_id}/risk", response_model=PositionRiskView)
async def get_risk(
    trade_id: UUID, container: Annotated[ApplicationContainer, Depends(get_container)]
) -> PositionRiskView:
    async with container.database.session_context() as session:
        view = await PositionRiskService(session).preview(
            workspace_id=WORKSPACE_ID, trade_id=trade_id, now=datetime.now(UTC)
        )
    if view is None:
        raise HTTPException(404, "No open position is available for risk evaluation")
    return view


@router.post("/trades/{trade_id}/risk/preview", response_model=PositionRiskView)
async def preview_risk(
    trade_id: UUID,
    payload: RiskPreviewRequest,
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> PositionRiskView:
    async with container.database.session_context() as session:
        view = await PositionRiskService(session).preview(
            workspace_id=WORKSPACE_ID,
            trade_id=trade_id,
            now=datetime.now(UTC),
            parameters=payload.parameters,
        )
    if view is None:
        raise HTTPException(404, "No open position is available for risk evaluation")
    return view


@router.post("/trades/{trade_id}/risk/evaluations", response_model=PositionRiskView)
async def evaluate_risk(
    trade_id: UUID, container: Annotated[ApplicationContainer, Depends(get_container)]
) -> PositionRiskView:
    async with container.database.session_context() as session:
        view, _ = await PositionRiskService(session).evaluate(
            workspace_id=WORKSPACE_ID, trade_id=trade_id, now=datetime.now(UTC)
        )
    if view is None:
        raise HTTPException(404, "No open position is available for risk evaluation")
    return view


@router.put("/trades/{trade_id}/risk/configuration", response_model=RiskConfiguration)
async def configure_risk(
    trade_id: UUID,
    payload: RiskConfigurationRequest,
    container: Annotated[ApplicationContainer, Depends(get_container)],
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-ID")] = None,
    correlation_id: Annotated[str | None, Header(alias="X-Correlation-ID", max_length=100)] = None,
) -> RiskConfiguration:
    async with container.database.session_context() as session:
        try:
            config = await PositionRiskService(session).configure(
                workspace_id=WORKSPACE_ID,
                trade_id=trade_id,
                now=datetime.now(UTC),
                parameters=payload.parameters,
                enabled=payload.enabled,
                expected_revision=payload.expected_revision,
                actor=actor_id or LOCAL_ACTOR_ID,
                correlation_id=correlation_id,
            )
        except RiskConfigurationConflict as exc:
            raise HTTPException(409, str(exc)) from exc
    if config is None:
        raise HTTPException(404, "No open position is available for risk configuration")
    return config


@router.get("/trades/{trade_id}/risk/history", response_model=tuple[PositionRiskView, ...])
async def risk_history(
    trade_id: UUID, container: Annotated[ApplicationContainer, Depends(get_container)]
) -> tuple[PositionRiskView, ...]:
    async with container.database.session_context() as session:
        views = await PositionRiskService(session).history(
            workspace_id=WORKSPACE_ID, trade_id=trade_id
        )
    if views is None:
        raise HTTPException(404, "No open position is available for risk history")
    return views
