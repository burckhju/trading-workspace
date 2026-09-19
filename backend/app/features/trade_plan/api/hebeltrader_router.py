"""Read-only strategy previews. Existing TradePlan approval/write paths are unchanged."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, replace
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any, Literal, cast
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from app.features.position_monitoring.domain.hebeltrader import (
    SessionCalendar,
    evaluate_management,
)
from app.features.product_selection.domain.hebeltrader_pricing import european_call_scenario
from app.features.trade_plan.api.dtos import TradePlanContentRequest
from app.features.trade_plan.domain.hebeltrader import (
    POLICY_ID,
    ZERO,
    Levels,
    assess_entry,
    build_levels,
    diagnose_bands,
)

Aware = Annotated[datetime, AwareDatetime]
Positive = Annotated[Decimal, Field(gt=0, le=Decimal("1e12"))]
NonNegative = Annotated[Decimal, Field(ge=0, le=Decimal("1e12"))]

router = APIRouter(prefix="/api/v1/trade-plans/strategies/hebeltrader", tags=["hebeltrader"])


def _wire(values: dict[str, Any]) -> dict[str, Any]:
    """Preserve Decimal values as strings on every JSON endpoint."""
    return cast(dict[str, Any], json.loads(json.dumps(values, default=str)))


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class LevelsRequest(StrictRequest):
    entry: Positive
    stop: Positive
    target1: Positive
    target2: Positive

    def domain(self) -> Levels:
        return Levels(**self.model_dump())

    @model_validator(mode="after")
    def validate_order(self) -> LevelsRequest:
        self.domain()
        return self


class QuoteRequest(StrictRequest):
    bid: NonNegative
    ask: Positive
    observed_at: Aware
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    source: str = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def validate_spread(self) -> QuoteRequest:
        if self.bid > self.ask or not self.source.strip():
            raise ValueError("uncrossed quote and non-blank source required")
        return self

    def usable(self, as_of: datetime) -> bool:
        return 0 <= (as_of - self.observed_at).total_seconds() <= 3600


class PreviewRequest(StrictRequest):
    as_of: Aware
    analysis_date: date
    source_ref: str = Field(min_length=1, max_length=500)
    quote: QuoteRequest
    gd200: Positive
    gd50: Positive | None = None
    fundamental_ok: bool = False
    published_levels: LevelsRequest | None = None
    band_width: Positive | None = None
    support_source: Literal["GD200", "GD50", "MANUAL"] = "GD200"
    manual_support: Positive | None = None
    buffer_fraction: Decimal = Field(default=ZERO, ge=0, lt=1)
    tick: Positive = Decimal("0.01")
    target1_seen: bool = False
    target2_seen: bool = False

    @model_validator(mode="after")
    def validate_inputs(self) -> PreviewRequest:
        if not self.source_ref.strip() or self.analysis_date > self.as_of.date():
            raise ValueError("source_ref and analysis_date on/before as_of are required")
        if (self.published_levels is None) == (self.band_width is None):
            raise ValueError("provide exactly one of published_levels or explicit band_width")
        if self.published_levels is None:
            if self.support_source == "GD50" and self.gd50 is None:
                raise ValueError("GD50 support requires gd50")
            if self.support_source == "MANUAL" and self.manual_support is None:
                raise ValueError("MANUAL support requires manual_support")
        return self


class PreviewResponse(BaseModel):
    policy_id: str
    mode: str
    execution_enabled: Literal[False] = False
    input_digest: str
    levels: dict[str, Any]
    assessment: dict[str, Any]
    band_diagnostic: dict[str, Any]
    warnings: list[str]
    trade_plan_content: TradePlanContentRequest | None


@router.post("/preview", response_model=PreviewResponse)
def preview(request: PreviewRequest) -> PreviewResponse:
    try:
        if request.published_levels is not None:
            levels = request.published_levels.domain()
            mode = "PUBLISHED_LEVELS_REVIEW"
        else:
            support = {
                "GD200": request.gd200,
                "GD50": request.gd50,
                "MANUAL": request.manual_support,
            }[request.support_source]
            if support is None or request.band_width is None:
                raise ValueError("explicit support and band_width required")
            levels = build_levels(
                entry=request.quote.ask,
                gd200=request.gd200,
                band_width=request.band_width,
                support=support,
                buffer_fraction=request.buffer_fraction,
                tick=request.tick,
            )
            mode = "RECONSTRUCTED_BANDS"
        assessment = assess_entry(
            levels=levels,
            stock_levels=levels,
            stock_price=request.quote.bid,
            gd200=request.gd200,
            fundamental_ok=request.fundamental_ok,
            bid=request.quote.bid,
            ask=request.quote.ask,
            target1_seen=request.target1_seen,
            target2_seen=request.target2_seen,
        )
        if (request.as_of.date() - request.analysis_date).days > 7:
            assessment = replace(
                assessment,
                eligible=False,
                allocation_fraction=ZERO,
                reasons=(*assessment.reasons, "ANALYSIS_OLDER_THAN_7_DAYS"),
            )
        if not request.quote.usable(request.as_of):
            assessment = replace(
                assessment,
                eligible=False,
                allocation_fraction=ZERO,
                reasons=(*assessment.reasons, "QUOTE_STALE_OR_FUTURE"),
            )
        diagnostic = diagnose_bands(levels, request.gd200)
        snapshot = request.model_dump(mode="json")
        encoded = json.dumps(snapshot, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(encoded.encode()).hexdigest()
        content: TradePlanContentRequest | None = None
        if assessment.eligible:
            target_prices = (
                [levels.target2] if assessment.late_entry else [levels.target1, levels.target2]
            )
            content = TradePlanContentRequest.model_validate(
                {
                    "thesis": f"Hebeltrader-Rekonstruktion; Quelle: {request.source_ref}",
                    "entry": {
                        "type": "PRICE",
                        "currency": request.quote.currency,
                        "price": request.quote.ask,
                    },
                    "invalidation": {
                        "stop_price": assessment.effective_stop,
                        "rationale": "Technische Invalidierung; kein garantierter Ausführungskurs.",
                    },
                    "targets": [
                        {"sequence": i, "price": price} for i, price in enumerate(target_prices, 1)
                    ],
                    "risk_assumptions": {
                        "thesis_risk": (
                            "Rekonstruiertes Szenario; Fundamentaldaten separat prüfen. "
                            "Keine Erfolgswahrscheinlichkeit."
                        ),
                        "max_loss_assumption": (
                            "Stopp ist keine Verlustgarantie; Kosten, Spread und "
                            "Kurslücken beachten."
                        ),
                        "notes": json.dumps(
                            {
                                "policy_id": POLICY_ID,
                                "input_digest": digest,
                                "mode": mode,
                                "inputs": snapshot,
                                "late_entry": assessment.late_entry,
                                "allocation_fraction": str(assessment.allocation_fraction),
                                "management": (
                                    "T1: 50%; Reststopp Einstand. Verlust ab 20 Sitzungen "
                                    "schließen. Nach T1+20 Sitzungen "
                                    "max(bisheriger Stopp, 0.8*T1)."
                                ),
                            },
                            ensure_ascii=False,
                            sort_keys=True,
                        ),
                    },
                }
            )
        warnings = [
            "RECONSTRUCTION_NOT_PUBLISHER_FORMULA",
            "NO_PERFORMANCE_BACKTEST",
            "MAJOR_CURRENCY_UNITS_REQUIRED",
            "CRV_EXCLUDES_COSTS_AND_SLIPPAGE",
        ]
        if diagnostic.status == "REVIEW":
            warnings.append("BAND_DEVIATION_REQUIRES_REVIEW")
        return PreviewResponse(
            policy_id=POLICY_ID,
            mode=mode,
            input_digest=digest,
            levels=asdict(levels),
            assessment=asdict(assessment),
            band_diagnostic=asdict(diagnostic),
            warnings=warnings,
            trade_plan_content=content,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


class CalendarRequest(StrictRequest):
    venue: str = Field(min_length=1, max_length=50)
    source: str = Field(min_length=1, max_length=200)
    time_zone: str = Field(default="Europe/Berlin", min_length=1, max_length=100)
    coverage_start: date
    coverage_end: date
    sessions: list[date] = Field(min_length=1, max_length=10000)

    def domain(self) -> SessionCalendar:
        return SessionCalendar(
            self.venue,
            self.source,
            self.coverage_start,
            self.coverage_end,
            tuple(self.sessions),
            self.time_zone,
        )


class EntryCheckRequest(StrictRequest):
    """Checks an independently supplied warrant/equity plan; never mixes price axes."""

    as_of: Aware
    levels: LevelsRequest
    stock_levels: LevelsRequest
    instrument_kind: Literal["STOCK", "CALL"]
    strike: Positive | None = None
    last_trading_date: date | None = None
    calendar: CalendarRequest | None = None
    levels_currency: str = Field(pattern=r"^[A-Z]{3}$")
    stock_currency: str = Field(pattern=r"^[A-Z]{3}$")
    stock_price: Positive
    gd200: Positive
    fundamental_ok: bool
    quote: QuoteRequest
    target1_seen: bool = False
    target2_seen: bool = False


@router.post("/entry-check")
def entry_check(request: EntryCheckRequest) -> dict[str, Any]:
    try:
        if request.quote.currency != request.levels_currency:
            raise ValueError("quote currency must match levels_currency")
        if request.instrument_kind == "STOCK" and (
            request.stock_currency != request.levels_currency
            or request.stock_levels != request.levels
            or request.stock_price != request.quote.bid
        ):
            raise ValueError("STOCK requires identical price axes, currency and stock bid")
        result = assess_entry(
            levels=request.levels.domain(),
            stock_levels=request.stock_levels.domain(),
            stock_price=request.stock_price,
            gd200=request.gd200,
            fundamental_ok=request.fundamental_ok,
            bid=request.quote.bid,
            ask=request.quote.ask,
            target1_seen=request.target1_seen,
            target2_seen=request.target2_seen,
        )
        if request.instrument_kind == "CALL":
            if (
                request.strike is None
                or request.calendar is None
                or request.last_trading_date is None
            ):
                raise ValueError("CALL requires strike, calendar and verified last_trading_date")
            calendar = request.calendar.domain()
            today = request.as_of.astimezone(ZoneInfo(calendar.time_zone)).date()
            if request.last_trading_date not in calendar.sessions:
                raise ValueError("last_trading_date must be a covered venue session")
            remaining = calendar.count(today, max(today, request.last_trading_date))
            extra = []
            if remaining <= 20:
                extra.append("EXPIRY_BUFFER_NOT_MET")
            if request.strike <= request.stock_levels.entry:
                extra.append("CALL_NOT_OTM_AT_RECOMMENDATION")
            if extra:
                result = replace(
                    result,
                    eligible=False,
                    allocation_fraction=ZERO,
                    reasons=(*result.reasons, *extra),
                )
        if not request.quote.usable(request.as_of):
            result = replace(
                result,
                eligible=False,
                allocation_fraction=ZERO,
                reasons=(*result.reasons, "QUOTE_STALE_OR_FUTURE"),
            )
        return _wire(
            {
                "policy_id": POLICY_ID,
                "execution_enabled": False,
                "scope": "MANUAL_INPUT_CHECK_NOT_PRODUCT_APPROVAL",
                **asdict(result),
            }
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


class ManagementRequest(StrictRequest):
    as_of: Aware
    levels: LevelsRequest
    position_currency: str = Field(pattern=r"^[A-Z]{3}$")
    actual_entry: Positive
    current_stop: Positive
    quote: QuoteRequest | None = None
    entered_on: date
    calendar: CalendarRequest
    remaining_fraction: Decimal = Field(default=Decimal("1"), ge=0, le=1)
    target1_completed_on: date | None = None
    late_entry: bool = False
    last_trading_date: date | None = None
    instrument_kind: Literal["STOCK", "CALL"]


@router.post("/management-preview")
def management_preview(request: ManagementRequest) -> dict[str, Any]:
    try:
        calendar = request.calendar.domain()
        if request.quote and request.quote.currency != request.position_currency:
            raise ValueError("quote currency must match position_currency")
        result = evaluate_management(
            levels=request.levels.domain(),
            actual_entry=request.actual_entry,
            current_stop=request.current_stop,
            bid=request.quote.bid if request.quote else None,
            quote_usable=request.quote.usable(request.as_of) if request.quote else False,
            entered_on=request.entered_on,
            as_of=request.as_of.astimezone(ZoneInfo(calendar.time_zone)).date(),
            calendar=calendar,
            remaining_fraction=request.remaining_fraction,
            target1_completed_on=request.target1_completed_on,
            late_entry=request.late_entry,
            last_trading_date=request.last_trading_date,
            instrument_kind=request.instrument_kind,
        )
        return _wire({"policy_id": POLICY_ID, "execution_enabled": False, **asdict(result)})
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


class CallScenarioRequest(StrictRequest):
    spot: Positive
    strike: Positive
    ratio: Positive
    valuation_date: date
    exercise_date: date
    implied_volatility: Decimal = Field(ge=0, le=5)
    risk_free_rate: Decimal = Field(ge=-1, le=1)
    dividend_yield: Decimal = Field(ge=-1, le=1)
    fx_quote_per_underlying: Positive
    underlying_currency: str = Field(pattern=r"^[A-Z]{3}$")
    warrant_currency: str = Field(pattern=r"^[A-Z]{3}$")
    exercise_style: Literal["EUROPEAN"]
    quanto: Literal[False]


@router.post("/call-scenario")
def call_scenario(request: CallScenarioRequest) -> dict[str, Any]:
    try:
        if (
            request.underlying_currency == request.warrant_currency
            and request.fx_quote_per_underlying != 1
        ):
            raise ValueError("same-currency scenario requires FX = 1")
        value = european_call_scenario(
            **request.model_dump(
                exclude={"exercise_style", "quanto", "underlying_currency", "warrant_currency"}
            )
        )
        return _wire(
            {
                "policy_id": POLICY_ID,
                "model": "BSM_EUROPEAN_CALL_ACT_365",
                "theoretical_value": value,
                "execution_enabled": False,
                "warning": "THEORETICAL_NOT_ISSUER_BID; no spread, credit or discrete dividends",
                "inputs": request.model_dump(mode="json"),
            }
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/rules")
def rules() -> dict[str, Any]:
    return {
        "policy_id": POLICY_ID,
        "profile_effective_from": "2026-08-10",
        "execution_enabled": False,
        "rules": {
            "entry": "Underlying > GD200, fundamental review, underlying stop distance >= 0.02",
            "targets": "T1 = GD200 + explicit B; T2 = GD200 + 2*B",
            "stop": "Explicit support * (1 - explicit buffer), rounded down to tick",
            "crv": "((T1 + T2)/2 - ask)/(ask - stop); late entry uses T2 only",
            "target1": (
                "Review selling 0.5 of original position; breakeven only after confirmed fill"
            ),
            "target2": "Review closing remaining position",
            "loss_timer": "At/after 20 venue sessions, bid < actual entry",
            "post_target1": "After 20 venue sessions: max(current stop, breakeven, 0.8*T1)",
            "expiry": "Review exit with <= 20 sessions to verified last trading date",
            "late_entry": (
                "Half allocation; stop original entry; no fictional first-target proceeds"
            ),
        },
        "implementation_choices": [
            "Explicit B: publisher volatility window/multiplier are unknown",
            "Explicit support choice; buffer defaults to 0, not an inferred publisher percentage",
            "Stops never decrease; this resolves a contradiction in the published text",
            "Quote age <= 3600 seconds; analysis age <= 7 calendar days",
            "No weekday-generated calendars; callers must supply complete venue sessions",
            "Latest profile only; do not silently apply to historical dates before 2026-08-10",
            "CALL entry check requires OTM strike, session calendar and >20 sessions to last trade",
            "Entry check is not product approval; provider/contract verification remains separate",
        ],
    }
