"""Documented warrant units against owner BUY contributions, never cost arithmetic."""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.features.product.domain.price_scale_evidence import ProductPriceScaleCurrent

type ScaleCoverageStatus = Literal["COVERED", "MISSING", "UNSUITABLE", "NOT_APPLICABLE"]


@dataclass(frozen=True, slots=True)
class PurchaseScaleInput:
    execution_id: UUID
    supersedes_execution_id: UUID | None
    original_quantity: int
    remaining_quantity: Decimal
    price_per_unit: Decimal
    executed_at: datetime
    executed_on: date | None
    execution_timezone: str | None
    recorded_at: datetime
    currency_code: str | None


@dataclass(frozen=True, slots=True)
class PurchaseScaleCoverage:
    execution_id: UUID
    supersedes_execution_id: UUID | None
    original_quantity: int
    remaining_quantity: Decimal
    price_per_unit: Decimal
    executed_at: datetime | None
    executed_on: date | None
    execution_timezone: str | None
    recorded_at: datetime
    currency_code: str | None
    possible_from: datetime | None
    possible_until: datetime | None
    status: ScaleCoverageStatus
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ProductPriceScaleAssessment:
    status: Literal["DOCUMENTED", "MISSING", "UNSUITABLE", "NOT_APPLICABLE"]
    reasons: tuple[str, ...]
    evidence: ProductPriceScaleCurrent
    execution_basis_id: str
    bid_at: datetime | None
    bid_status: ScaleCoverageStatus
    bid_reasons: tuple[str, ...]
    purchases: tuple[PurchaseScaleCoverage, ...]
    adjustment_applied: Literal[False] = False
    definition_version: Literal["hebeltrader-product-price-scale-v1"] = (
        "hebeltrader-product-price-scale-v1"
    )


def _purchase_period(item: PurchaseScaleInput) -> tuple[datetime, datetime | None]:
    """A date is a possible local-day interval, never its internal sorting anchor."""
    if item.executed_at.utcoffset() is None:
        raise ValueError("Execution time must be aware")
    if item.executed_on is None:
        if item.execution_timezone is not None:
            raise ValueError("Execution precision is inconsistent")
        return item.executed_at.astimezone(UTC), None
    if item.execution_timezone is None:
        raise ValueError("A date-only execution needs its original zone")
    zone = ZoneInfo(item.execution_timezone)
    first = datetime.combine(item.executed_on, time.min, zone)
    end = datetime.combine(item.executed_on + timedelta(days=1), time.min, zone)
    start_utc, end_utc = first.astimezone(UTC), end.astimezone(UTC)
    if (
        start_utc != item.executed_at.astimezone(UTC)
        or start_utc.astimezone(zone).replace(tzinfo=None) != first.replace(tzinfo=None)
        or end_utc.astimezone(zone).replace(tzinfo=None) != end.replace(tzinfo=None)
        or end_utc <= start_utc
    ):
        raise ValueError("The complete possible execution day is not unambiguous")
    return start_utc, end_utc


def _coverage(
    item: PurchaseScaleInput,
    evidence: ProductPriceScaleCurrent,
    *,
    applicable: bool,
) -> PurchaseScaleCoverage:
    start, end = None, None
    status: ScaleCoverageStatus
    reasons: tuple[str, ...]
    manifest = evidence.manifest
    if not applicable or item.remaining_quantity == 0:
        status = "NOT_APPLICABLE"
        reasons = (
            "POSITION_CLOSED_OR_CANCELLED" if not applicable else "BUY_NO_REMAINING_CONTRIBUTION",
        )
    elif evidence.status != "AVAILABLE" or manifest is None:
        status = "UNSUITABLE" if evidence.status == "UNSUITABLE" else "MISSING"
        reasons = evidence.reasons
    elif item.currency_code is None:
        status, reasons = "MISSING", ("PRODUCT_SCALE_BUY_CURRENCY_MISSING",)
    elif item.currency_code != manifest.currency:
        status, reasons = "UNSUITABLE", ("PRODUCT_SCALE_BUY_CURRENCY_MISMATCH",)
    else:
        try:
            start, end = _purchase_period(item)
        except (ValueError, OverflowError, ZoneInfoNotFoundError):
            status, reasons = "UNSUITABLE", ("PRODUCT_SCALE_BUY_TIME_UNSUITABLE",)
        else:
            lower, upper = manifest.valid_from.astimezone(UTC), manifest.valid_until.astimezone(UTC)
            covered = lower <= start < upper and (end is None or end <= upper)
            status = "COVERED" if covered else "MISSING"
            reasons = () if covered else ("PRODUCT_SCALE_BUY_OUTSIDE_DOCUMENTED_PERIOD",)
    return PurchaseScaleCoverage(
        execution_id=item.execution_id,
        supersedes_execution_id=item.supersedes_execution_id,
        original_quantity=item.original_quantity,
        remaining_quantity=item.remaining_quantity,
        price_per_unit=item.price_per_unit,
        executed_at=item.executed_at if item.executed_on is None else None,
        executed_on=item.executed_on,
        execution_timezone=item.execution_timezone,
        recorded_at=item.recorded_at,
        currency_code=item.currency_code,
        possible_from=start,
        possible_until=end,
        status=status,
        reasons=reasons,
    )


def assess_product_price_scale(
    *,
    evidence: ProductPriceScaleCurrent,
    execution_basis_id: str,
    purchases: tuple[PurchaseScaleInput, ...],
    bid_at: datetime | None,
    bid_currency: str | None,
    bid_isin: str | None,
    bid_available: bool,
    applicable: bool,
) -> ProductPriceScaleAssessment:
    """Every contributing BUY and the BID must share this one documented period.

    The owner has already qualified identity, terms and the current revision.
    This function does not infer unchanged units from their absence of change.
    A manual original-document review is not independent source verification.
    """
    if any(
        not item.remaining_quantity.is_finite()
        or item.remaining_quantity < 0
        or item.remaining_quantity > item.original_quantity
        for item in purchases
    ) or len({item.execution_id for item in purchases}) != len(purchases):
        raise ValueError("Inconsistent execution-owner BUY contributions")
    manifest = evidence.manifest
    if evidence.status == "AVAILABLE" and (
        manifest is None
        or manifest.status != "UNCHANGED_ORIGINAL"
        or manifest.axis != "WARRANT"
        or manifest.unit != "CURRENCY_PER_WARRANT"
        or evidence.binding != manifest.binding
        or evidence.source is None
        or evidence.revision_id is None
    ):
        raise ValueError("Inconsistent available product price scale owner evidence")
    covered = tuple(_coverage(item, evidence, applicable=applicable) for item in purchases)
    bid_status: ScaleCoverageStatus
    bid_reasons: tuple[str, ...]
    if not applicable:
        bid_status, bid_reasons = "NOT_APPLICABLE", ("POSITION_CLOSED_OR_CANCELLED",)
    elif evidence.status != "AVAILABLE" or manifest is None:
        bid_status = "UNSUITABLE" if evidence.status == "UNSUITABLE" else "MISSING"
        bid_reasons = evidence.reasons
    elif not bid_available or bid_at is None:
        bid_status, bid_reasons = "MISSING", ("PRODUCT_SCALE_QUALIFIED_BID_MISSING",)
    elif bid_currency != manifest.currency or bid_isin != manifest.binding.isin:
        bid_status, bid_reasons = "UNSUITABLE", ("PRODUCT_SCALE_BID_BINDING_MISMATCH",)
    elif bid_at.utcoffset() is None:
        raise ValueError("Original BID clock must be aware")
    elif not (
        manifest.valid_from.astimezone(UTC)
        <= bid_at.astimezone(UTC)
        < manifest.valid_until.astimezone(UTC)
    ):
        bid_status, bid_reasons = "MISSING", ("PRODUCT_SCALE_BID_OUTSIDE_DOCUMENTED_PERIOD",)
    else:
        bid_status, bid_reasons = "COVERED", ()
    reasons = tuple(dict.fromkeys((*bid_reasons, *(r for item in covered for r in item.reasons))))
    if not applicable:
        status: Literal["DOCUMENTED", "MISSING", "UNSUITABLE", "NOT_APPLICABLE"] = "NOT_APPLICABLE"
    elif bid_status == "UNSUITABLE" or any(item.status == "UNSUITABLE" for item in covered):
        status = "UNSUITABLE"
    elif (
        bid_status != "COVERED"
        or not any(item.remaining_quantity > 0 for item in covered)
        or any(item.status not in {"COVERED", "NOT_APPLICABLE"} for item in covered)
    ):
        status = "MISSING"
        if not any(item.remaining_quantity > 0 for item in covered):
            reasons = (*reasons, "PRODUCT_SCALE_CONTRIBUTING_BUYS_MISSING")
    else:
        status = "DOCUMENTED"
        reasons = ()
    return ProductPriceScaleAssessment(
        status=status,
        reasons=reasons,
        evidence=evidence,
        execution_basis_id=execution_basis_id,
        bid_at=bid_at,
        bid_status=bid_status,
        bid_reasons=bid_reasons,
        purchases=covered,
    )
