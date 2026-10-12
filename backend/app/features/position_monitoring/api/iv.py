"""Stateless assumption-only model preview. No position, provider, DB or alert writes."""

from dataclasses import replace
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.features.analysis.domain.vanilla_iv import (
    Scenario,
    ScenarioValue,
    VanillaInputs,
    fraction,
    revalue,
    solve_iv,
)

router = APIRouter()


class IvModelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    basis: Literal["HYPOTHETICAL_ASSUMPTIONS"]
    product_type: Literal["VANILLA_WARRANT"]
    exercise_style: Literal["EUROPEAN"]
    direction: Literal["CALL", "PUT"]
    spot: Decimal
    strike: Decimal
    ratio: Decimal
    remaining_days: Decimal
    iv_percent: Decimal | None = None
    calibration_price: Decimal | None = None
    rate_percent: Decimal
    dividend_yield_percent: Decimal
    currency: str = Field(min_length=3, max_length=3)
    underlying_currency: str = Field(min_length=3, max_length=3)
    strike_currency: str = Field(min_length=3, max_length=3)
    quanto: bool = Field(strict=True)
    dividend_model: Literal["CONTINUOUS_YIELD"]
    ratio_convention: Literal["UNDERLYING_UNITS_PER_WARRANT"]
    scenario: Scenario


@router.post("/risk/iv/model-preview", response_model=ScenarioValue)
async def model_preview(payload: IvModelRequest) -> ScenarioValue:
    try:
        if (payload.iv_percent is None) == (payload.calibration_price is None):
            raise ValueError("CHOOSE_IV_OR_HYPOTHETICAL_PRICE")
        inputs = VanillaInputs(
            payload.product_type,
            payload.exercise_style,
            payload.direction,
            payload.spot,
            payload.strike,
            payload.ratio,
            payload.remaining_days,
            fraction(payload.iv_percent) if payload.iv_percent is not None else Decimal(".2"),
            fraction(payload.rate_percent),
            fraction(payload.dividend_yield_percent),
            payload.currency,
            payload.underlying_currency,
            payload.strike_currency,
            payload.quanto,
            payload.dividend_model,
            payload.ratio_convention,
        )
        if payload.calibration_price is not None:
            inputs = replace(inputs, iv_decimal=solve_iv(inputs, payload.calibration_price))
        result = revalue(inputs, payload.scenario)
        return replace(
            result,
            iv_origin=(
                "HYPOTHETICAL_PRICE_INVERSION"
                if payload.calibration_price is not None
                else "USER_ASSUMPTION"
            ),
        )
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc
