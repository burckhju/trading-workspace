"""Batch-cached issuer indications with explicitly unknown quote timezone."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from decimal import Decimal

from app.core.config.morganstanley import MorganStanleySettings
from app.database import DatabaseManager
from app.features.market_data.domain.enums import (
    CacheStatus,
    MarketDataCapability,
    MarketDataProvider,
    QualityStatus,
)
from app.features.market_data.domain.models import WarrantQuoteSnapshot
from app.features.market_data.persistence.quote_identity import read_quote_identity
from app.features.market_data.service.errors import (
    MarketDataConfigurationError,
    MarketDataInvalidResponseError,
    MarketDataNotFoundError,
)
from app.features.market_data.service.types import MarketDataResult, WarrantQuoteRequest
from app.providers.issuer_bindings import BatchFetcher, IssuerBatches, IssuerPriceIdentity
from app.providers.morganstanley.products import SOURCE_MODE, TIME_BASIS
from app.providers.morganstanley.stream import StreamItem, fetch_batch


def parse_item(
    item: StreamItem, request: WarrantQuoteRequest, identity: IssuerPriceIdentity
) -> WarrantQuoteSnapshot:
    fields = item.fields
    prices = {}
    volumes = {}
    for side in ("bid", "ask"):
        raw, size = fields[side], fields[side + "size"]
        if raw is not None and raw != "" and not re.fullmatch(r"\d{1,12}(?:\.\d{1,12})?", raw):
            raise ValueError("MORGAN_STANLEY_INVALID_PRICE")
        if size is not None and size != "" and not re.fullmatch(r"\d{1,12}", size):
            raise ValueError("MORGAN_STANLEY_INVALID_VOLUME")
        prices[side] = Decimal(raw) if raw is not None and raw != "" and Decimal(raw) > 0 else None
        volumes[side] = int(size) if size is not None and size != "" else None
    raw_time = fields["lastquotetimestamp"] or None
    if raw_time is not None:
        if not re.fullmatch(
            r"[0-9]{2}/[0-9]{2}/[0-9]{4} [0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?", raw_time
        ):
            raise ValueError("MORGAN_STANLEY_UNRECOGNIZED_QUOTE_TIME")
        try:
            datetime.strptime(
                raw_time, "%d/%m/%Y %H:%M:%S.%f" if "." in raw_time else "%d/%m/%Y %H:%M:%S"
            )
        except ValueError:
            raise ValueError("MORGAN_STANLEY_INVALID_QUOTE_TIME") from None
    if prices["bid"] and prices["ask"] and prices["bid"] > prices["ask"]:
        raise ValueError("MORGAN_STANLEY_CROSSED_PRICES")
    return WarrantQuoteSnapshot(
        warrant_listing_id=request.warrant_listing_id,
        bid=prices["bid"],
        ask=prices["ask"],
        currency=identity.currency,
        provider_symbol=identity.isin,
        provider_exchange_code="ISSUER",
        isin=identity.isin,
        wkn=identity.wkn,
        observed_at=None,
        assessed_at=datetime.now(UTC),
        source_mode=SOURCE_MODE,
        trading_status="UNKNOWN",
        quote_time_text=raw_time,
        quote_time_basis=TIME_BASIS if raw_time else "TIMESTAMP_MISSING",
        bid_volume=volumes["bid"],
        ask_volume=volumes["ask"],
    )


def quote_warnings(quote: WarrantQuoteSnapshot) -> tuple[str, ...]:
    warnings = [
        "QUOTE_TIMEZONE_UNKNOWN" if quote.quote_time_text else "QUOTE_TIMESTAMP_MISSING",
        "ISSUER_INDICATION_NOT_EXECUTABLE",
    ]
    for side in ("bid", "ask"):
        if getattr(quote, side) is not None and not getattr(quote, side + "_volume"):
            warnings.append(side.upper() + "_WITHOUT_POSITIVE_VOLUME")
    return tuple(warnings)


class MorganStanleyWarrantQuoteAdapter:
    def __init__(
        self,
        *,
        database: DatabaseManager,
        settings: MorganStanleySettings,
        fetcher: BatchFetcher[StreamItem] = fetch_batch,
    ) -> None:
        self._database, self._settings, self._fetcher = database, settings, fetcher
        self._batches = IssuerBatches(
            database, MarketDataProvider.MORGAN_STANLEY, settings, fetcher
        )

    def invalidate_routes(self) -> None:
        self._batches.invalidate_routes()

    async def get_warrant_listing_quote(
        self, request: WarrantQuoteRequest
    ) -> MarketDataResult[WarrantQuoteSnapshot]:
        if not self._settings.enabled:
            raise MarketDataConfigurationError("MORGAN_STANLEY_DISABLED")
        async with self._database.session_context() as session:
            identity = await read_quote_identity(
                session, request, MarketDataProvider.MORGAN_STANLEY
            )
        if identity is None:
            raise MarketDataNotFoundError("MORGAN_STANLEY_VERIFIED_MAPPING_REQUIRED")
        try:
            item, error, hit = await self._batches.get(request.workspace_id, identity)
        except ValueError as exc:
            raise MarketDataInvalidResponseError(str(exc)) from None
        if error or item is None:
            raise MarketDataInvalidResponseError(error or "MORGAN_STANLEY_SNAPSHOT_MISSING")
        try:
            quote = parse_item(item, request, identity)
        except ValueError as exc:
            raise MarketDataInvalidResponseError(str(exc)) from None
        return MarketDataResult(
            data=quote,
            provider=MarketDataProvider.MORGAN_STANLEY,
            capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
            correlation_id=request.correlation_id,
            retrieved_at=item.received_at,
            cache_status=CacheStatus.HIT if hit else CacheStatus.MISS,
            quality_status=QualityStatus.VALID,
            warnings=quote_warnings(quote),
            retry_count=0,
            provider_call_cost=0,
            reason_code=(
                "QUOTE_TIMEZONE_UNKNOWN_INDICATIVE_ANALYSIS_ONLY"
                if quote.quote_time_text
                else "QUOTE_TIMESTAMP_UNKNOWN_INDICATIVE_ANALYSIS_ONLY"
            ),
        )
