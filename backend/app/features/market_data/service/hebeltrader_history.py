"""Bounded saved EOD evidence; historical comparison requires explicit qualification.

The existing price owner may replace daily rows. Consumers must preserve these
original values and fingerprints with their decisions. Current listing/venue
metadata is exposed honestly, never relabelled as a verified historical binding.
No provider, price import, rule activation or write belongs to this reader.
"""

import hashlib
import json
from dataclasses import asdict, dataclass, replace
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.market.persistence.models import ListingModel, TradingVenueModel, UnderlyingModel
from app.features.market.service.risk_reference import RiskListingReader
from app.features.market_data.persistence.instruments import MarketDataInstrumentModel
from app.features.market_data.persistence.models import DailyPriceModel

MAX_HISTORY_ROWS = 5000
type HistoryStatus = Literal["AVAILABLE", "MISSING", "BLOCKED", "LIMIT_EXCEEDED"]


@dataclass(frozen=True, slots=True)
class HistoricalListingBinding:
    workspace_id: UUID
    underlying_id: UUID
    listing_id: UUID
    trading_venue_id: UUID
    venue_mic: str
    timezone: str
    currency: str
    listing_version: int
    venue_version: int
    venue_reference_version: str
    listing_recorded_at: datetime
    listing_updated_at: datetime
    venue_recorded_at: datetime
    venue_updated_at: datetime
    fingerprint: str
    provenance: Literal["CURRENT_REFERENCE_NOT_HISTORICALLY_VERIFIED"] = (
        "CURRENT_REFERENCE_NOT_HISTORICALLY_VERIFIED"
    )


@dataclass(frozen=True, slots=True)
class HistoricalDailyEvidence:
    source_row_id: UUID
    workspace_id: UUID
    listing_id: UUID
    market_data_instrument_id: UUID | None
    fingerprint: str
    trading_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    adjusted_close: Decimal | None
    volume: Decimal | None
    currency: str
    provider: str
    provider_symbol: str
    price_type: str
    quality_status: str
    warnings: tuple[str, ...]
    interval_start: datetime | None
    interval_end: datetime | None
    retrieved_at: datetime
    source_updated_at: datetime | None
    recorded_at: datetime
    last_updated_at: datetime
    issues: tuple[str, ...]
    scale_status: Literal[
        "REQUIRES_EXPLICIT_COMPARISON_QUALIFICATION", "ADJUSTMENT_INDICATION_PRESENT"
    ]
    time_precision: Literal["DATE_ONLY"] = "DATE_ONLY"
    interval_basis: Literal["LOCAL_CALENDAR_DAY_NOT_VERIFIED_SESSION"] = (
        "LOCAL_CALENDAR_DAY_NOT_VERIFIED_SESSION"
    )
    price_basis: Literal["UNDERLYING"] = "UNDERLYING"


@dataclass(frozen=True, slots=True)
class HebeltraderPriceHistory:
    workspace_id: UUID
    underlying_id: UUID
    binding: HistoricalListingBinding | None
    rows: tuple[HistoricalDailyEvidence, ...]
    status: HistoryStatus
    reasons: tuple[str, ...]
    fingerprint: str
    start_date: date
    end_date: date
    known_at: datetime
    read_at: datetime
    stored_range_complete: bool
    intervals_complete: bool
    rows_observed: int
    row_limit: int = MAX_HISTORY_ROWS
    calendar_coverage: Literal["NOT_ASSESSED"] = "NOT_ASSESSED"
    qualification_required: Literal["HISTORICAL_BINDING_AND_COMPARISON_SCALE"] = (
        "HISTORICAL_BINDING_AND_COMPARISON_SCALE"
    )


def _utc(value: datetime) -> datetime:
    # These are existing UTC persistence clocks, not inferred market-event times.
    # SQLite round trips used by owner tests omit the stored UTC offset.
    return value.replace(tzinfo=UTC) if value.utcoffset() is None else value.astimezone(UTC)


def _json_value(value: object) -> str:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (UUID, Decimal)):
        return str(value)
    raise TypeError(f"Unsupported evidence value: {type(value).__name__}")


def _fingerprint(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=_json_value)
    return hashlib.sha256(encoded.encode()).hexdigest()


def _binding(listing: ListingModel, venue: TradingVenueModel) -> HistoricalListingBinding:
    value = HistoricalListingBinding(
        workspace_id=listing.workspace_id,
        underlying_id=listing.underlying_id,
        listing_id=listing.id,
        trading_venue_id=venue.id,
        venue_mic=venue.mic,
        timezone=venue.timezone,
        currency=listing.currency_code,
        listing_version=listing.version,
        venue_version=venue.version,
        venue_reference_version=venue.reference_version,
        listing_recorded_at=_utc(listing.created_at),
        listing_updated_at=_utc(listing.updated_at),
        venue_recorded_at=_utc(venue.created_at),
        venue_updated_at=_utc(venue.updated_at),
        fingerprint="",
    )
    return replace(value, fingerprint=_fingerprint(asdict(value)))


def _adjustment_indications(rows: list[DailyPriceModel]) -> set[tuple[str, str, str]]:
    """A source adjustment may be a dividend or another change, not a proven split.

    Any such stored indication requires review of its whole source/currency
    segment. No ratio is interpreted as a factor and no original OHLC is changed.
    Absence of an indication is not a verified comparison scale.
    """
    return {
        (str(row.provider), row.provider_symbol, row.currency)
        for row in rows
        if (
            row.adjusted_close is not None
            and row.adjusted_close.is_finite()
            and row.close.is_finite()
            and row.adjusted_close != row.close
        )
        or any(token in row.warnings.upper() for token in ("SPLIT", "ADJUST", "CORPORATE_ACTION"))
    }


def _comparison_material(row: HistoricalDailyEvidence) -> dict[str, object]:
    material = asdict(row)
    # Re-fetching identical provider facts only renews these technical clocks.
    # Preserve them in the audit DTO without redefining its original evidence.
    material.pop("retrieved_at")
    material.pop("last_updated_at")
    return material


def _row(
    row: DailyPriceModel,
    *,
    zone: ZoneInfo | None,
    known_at: datetime,
    adjustment_indications: set[tuple[str, str, str]],
    valid_instrument_ids: set[UUID],
) -> HistoricalDailyEvidence:
    assert row.listing_id is not None
    issues: list[str] = []
    if row.market_data_instrument_id is not None and (
        row.market_data_instrument_id not in valid_instrument_ids
    ):
        issues.append("MARKET_DATA_INSTRUMENT_SCOPE_MISMATCH")
    interval_start = interval_end = None
    if zone is None:
        issues.append("LISTING_TIMEZONE_UNAVAILABLE")
    else:
        interval_start = datetime.combine(row.trading_date, time.min, zone).astimezone(UTC)
        interval_end = datetime.combine(
            row.trading_date + timedelta(days=1), time.min, zone
        ).astimezone(UTC)
        if interval_end > known_at:
            issues.append("FULL_LOCAL_DAY_NOT_COMPLETED_AT_CUTOFF")
    if str(row.price_type) != "EOD":
        issues.append("PRICE_TYPE_NOT_EOD")
    if str(row.quality_status) != "VALID" or row.warnings != "":
        issues.append("EOD_QUALITY_LIMITED")
    values = (row.open, row.high, row.low, row.close)
    if (
        any(not value.is_finite() or value <= 0 for value in values)
        or not row.low <= row.open <= row.high
        or not row.low <= row.close <= row.high
        or (
            row.adjusted_close is not None
            and (not row.adjusted_close.is_finite() or row.adjusted_close <= 0)
        )
        or (row.volume is not None and (not row.volume.is_finite() or row.volume < 0))
    ):
        issues.append("INVALID_ORIGINAL_VALUES")
    if (
        len(row.currency) != 3
        or not row.currency.isascii()
        or not row.currency.isalpha()
        or row.currency != row.currency.upper()
        or not row.provider_symbol.strip()
    ):
        issues.append("INVALID_ORIGINAL_SOURCE_BINDING")
    retrieved = _utc(row.retrieved_at)
    source_updated = _utc(row.source_updated_at) if row.source_updated_at else None
    recorded = _utc(row.created_at)
    updated = _utc(row.updated_at)
    if any(value > known_at for value in (retrieved, recorded, updated)) or (
        source_updated is not None and source_updated > known_at
    ):
        issues.append("DATA_NOT_KNOWN_AT_CUTOFF")
    if (
        updated < recorded
        or retrieved > updated
        or (source_updated is not None and source_updated > retrieved)
    ):
        issues.append("INVALID_STORED_TIME_ORDER")
    value = HistoricalDailyEvidence(
        source_row_id=row.id,
        workspace_id=row.workspace_id,
        listing_id=row.listing_id,
        market_data_instrument_id=row.market_data_instrument_id,
        fingerprint="",
        trading_date=row.trading_date,
        open=row.open,
        high=row.high,
        low=row.low,
        close=row.close,
        adjusted_close=row.adjusted_close,
        volume=row.volume,
        currency=row.currency,
        provider=str(row.provider),
        provider_symbol=row.provider_symbol,
        price_type=str(row.price_type),
        quality_status=str(row.quality_status),
        # Preserve blank entries in a malformed nonempty warning representation.
        warnings=() if row.warnings == "" else tuple(row.warnings.split("\n")),
        interval_start=interval_start,
        interval_end=interval_end,
        retrieved_at=retrieved,
        source_updated_at=source_updated,
        recorded_at=recorded,
        last_updated_at=updated,
        issues=tuple(issues),
        scale_status=(
            "ADJUSTMENT_INDICATION_PRESENT"
            if (str(row.provider), row.provider_symbol, row.currency) in adjustment_indications
            else "REQUIRES_EXPLICIT_COMPARISON_QUALIFICATION"
        ),
    )
    original = _comparison_material(value)
    for field in ("interval_start", "interval_end", "issues", "scale_status"):
        original.pop(field)
    return replace(value, fingerprint=_fingerprint(original))


class HebeltraderHistoryReader:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def read(
        self,
        *,
        workspace_id: UUID,
        underlying_id: UUID,
        listing_id: UUID | None,
        start_date: date,
        end_date: date,
        known_at: datetime,
    ) -> HebeltraderPriceHistory:
        """Read every stored row in the inclusive range, or reject the oversized range.

        Full local calendar days are conservative date-only envelopes, not
        verified sessions or invented intraday event timestamps. Today's primary
        listing is only a discovery option; no historical recommendation or
        price row is rebound. The caller owns transaction isolation and retains
        each qualified input snapshot with the resulting monitoring decision.
        """
        if known_at.utcoffset() is None or start_date > end_date or end_date == date.max:
            raise ValueError("A valid date range and timezone-aware cutoff are required")
        known_at = known_at.astimezone(UTC)
        read_at = datetime.now(UTC)
        binding = None
        rows: tuple[HistoricalDailyEvidence, ...] = ()
        observed = 0
        status: HistoryStatus = "MISSING"
        reasons: tuple[str, ...] = ()
        stored_range_complete = False

        with self._session.no_autoflush:
            if listing_id is None:
                reference = await RiskListingReader(self._session).read(
                    workspace_id=workspace_id, underlying_id=underlying_id
                )
                listing_id = reference.listing_id if reference else None
            if listing_id is None:
                reasons = ("NO_UNIQUE_ACTIVE_PRIMARY_LISTING",)
            else:
                found = (
                    await self._session.execute(
                        select(ListingModel, TradingVenueModel)
                        .join(
                            TradingVenueModel,
                            TradingVenueModel.id == ListingModel.trading_venue_id,
                        )
                        .join(UnderlyingModel, UnderlyingModel.id == ListingModel.underlying_id)
                        .where(
                            ListingModel.id == listing_id,
                            ListingModel.workspace_id == workspace_id,
                            ListingModel.underlying_id == underlying_id,
                            UnderlyingModel.workspace_id == workspace_id,
                        )
                    )
                ).one_or_none()
                if found is None:
                    reasons = ("LISTING_IDENTITY_NOT_FOUND",)
                else:
                    binding = _binding(found[0], found[1])
                    try:
                        zone: ZoneInfo | None = ZoneInfo(binding.timezone)
                    except (ZoneInfoNotFoundError, ValueError):
                        zone = None
                        reasons = ("LISTING_TIMEZONE_UNAVAILABLE",)
                    if max(binding.listing_updated_at, binding.venue_updated_at) > known_at:
                        reasons += ("CURRENT_REFERENCE_NOT_KNOWN_AT_CUTOFF",)
                    models = list(
                        (
                            await self._session.scalars(
                                select(DailyPriceModel)
                                .where(
                                    DailyPriceModel.workspace_id == workspace_id,
                                    DailyPriceModel.listing_id == listing_id,
                                    DailyPriceModel.trading_date.between(start_date, end_date),
                                )
                                .order_by(DailyPriceModel.trading_date, DailyPriceModel.id)
                                .limit(MAX_HISTORY_ROWS + 1)
                            )
                        ).all()
                    )
                    observed = len(models)
                    if observed > MAX_HISTORY_ROWS:
                        status = "LIMIT_EXCEEDED"
                        reasons += ("HISTORICAL_RANGE_ROW_LIMIT_EXCEEDED",)
                    else:
                        stored_range_complete = True
                        adjustments = _adjustment_indications(models)
                        instrument_ids = {
                            model.market_data_instrument_id
                            for model in models
                            if model.market_data_instrument_id is not None
                        }
                        valid_instrument_ids = (
                            set(
                                (
                                    await self._session.scalars(
                                        select(MarketDataInstrumentModel.id).where(
                                            MarketDataInstrumentModel.id.in_(instrument_ids),
                                            MarketDataInstrumentModel.workspace_id == workspace_id,
                                            MarketDataInstrumentModel.kind == "LISTING",
                                            MarketDataInstrumentModel.listing_id == listing_id,
                                            MarketDataInstrumentModel.market_reference_id.is_(None),
                                            MarketDataInstrumentModel.created_at <= known_at,
                                        )
                                    )
                                ).all()
                            )
                            if instrument_ids
                            else set()
                        )
                        rows = tuple(
                            _row(
                                model,
                                zone=zone,
                                known_at=known_at,
                                adjustment_indications=adjustments,
                                valid_instrument_ids=valid_instrument_ids,
                            )
                            for model in models
                        )
                        status = "BLOCKED" if reasons else "AVAILABLE" if rows else "MISSING"
                        if not rows:
                            reasons += ("NO_STORED_EOD_IN_RANGE",)

        intervals_complete = bool(rows) and all(
            row.interval_end is not None and row.interval_end <= known_at for row in rows
        )
        fingerprint = _fingerprint(
            {
                "contract": "HEBELTRADER_SAVED_EOD_HISTORY_V1",
                "workspace_id": workspace_id,
                "underlying_id": underlying_id,
                "listing_id": listing_id,
                "binding": asdict(binding) if binding else None,
                "rows": tuple(_comparison_material(row) for row in rows),
                "start_date": start_date,
                # Advancing the read window without changing its comparison
                # material must not revoke an existing explicit qualification.
                # The requested end remains in the audit DTO; new rows, issues
                # or completed intervals still change this fingerprint.
                "status": status,
                "reasons": reasons,
                "stored_range_complete": stored_range_complete,
                "intervals_complete": intervals_complete,
                "rows_observed": observed,
                "row_limit": MAX_HISTORY_ROWS,
            }
        )
        return HebeltraderPriceHistory(
            workspace_id,
            underlying_id,
            binding,
            rows,
            status,
            reasons,
            fingerprint,
            start_date,
            end_date,
            known_at,
            read_at,
            stored_range_complete,
            intervals_complete,
            observed,
            row_limit=MAX_HISTORY_ROWS,
        )
