"""Batch-cached issuer indications with explicitly unknown quote date/timezone."""

from __future__ import annotations

import re
from datetime import UTC, datetime, time
from decimal import Decimal

from app.core.config.jpmorgan import JPMorganSettings
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
from app.providers.jpmorgan.products import SOURCE_MODE
from app.providers.jpmorgan.stream import StreamItem, fetch_batch


def parse_item(
    item: StreamItem, request: WarrantQuoteRequest, identity: IssuerPriceIdentity
) -> WarrantQuoteSnapshot:
    fields = item.fields
    prices = {}
    volumes = {}
    for side in ("bid", "ask"):
        raw, size = fields[side], fields[side + "size"]
        if raw is not None and raw != "" and not re.fullmatch(r"\d{1,12}(?:\.\d{1,12})?", raw):
            raise ValueError("JPMORGAN_INVALID_PRICE")
        if size is not None and size != "" and not re.fullmatch(r"\d{1,12}", size):
            raise ValueError("JPMORGAN_INVALID_VOLUME")
        prices[side] = Decimal(raw) if raw is not None and raw != "" and Decimal(raw) > 0 else None
        volumes[side] = int(size) if size is not None and size != "" else None
    raw_time = fields["quotetime"] or None
    if raw_time is not None:
        if not re.fullmatch(r"\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?", raw_time):
            raise ValueError("JPMORGAN_UNRECOGNIZED_QUOTE_TIME")
        try:
            time.fromisoformat(raw_time)
        except ValueError:
            raise ValueError("JPMORGAN_INVALID_QUOTE_TIME") from None
    if prices["bid"] and prices["ask"] and prices["bid"] > prices["ask"]:
        raise ValueError("JPMORGAN_CROSSED_PRICES")
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
        quote_time_basis="DATE_AND_TIMEZONE_UNKNOWN",
        bid_volume=volumes["bid"],
        ask_volume=volumes["ask"],
    )


class JPMorganWarrantQuoteAdapter:
    def __init__(
        self,
        *,
        database: DatabaseManager,
        settings: JPMorganSettings,
        fetcher: BatchFetcher[StreamItem] = fetch_batch,
    ) -> None:
        self._database, self._settings, self._fetcher = database, settings, fetcher
        self._batches = IssuerBatches(database, MarketDataProvider.JPMORGAN, settings, fetcher)

    def invalidate_routes(self) -> None:
        self._batches.invalidate_routes()

    async def get_warrant_listing_quote(
        self, request: WarrantQuoteRequest
    ) -> MarketDataResult[WarrantQuoteSnapshot]:
        if not self._settings.enabled:
            raise MarketDataConfigurationError("JPMORGAN_DISABLED")
        async with self._database.session_context() as session:
            identity = await read_quote_identity(session, request, MarketDataProvider.JPMORGAN)
        if identity is None:
            raise MarketDataNotFoundError("JPMORGAN_VERIFIED_MAPPING_REQUIRED")
        try:
            item, error, hit = await self._batches.get(request.workspace_id, identity)
        except ValueError as exc:
            raise MarketDataInvalidResponseError(str(exc)) from None
        if error or item is None:
            raise MarketDataInvalidResponseError(error or "JPMORGAN_SNAPSHOT_MISSING")
        try:
            quote = parse_item(item, request, identity)
        except ValueError as exc:
            raise MarketDataInvalidResponseError(str(exc)) from None
        return MarketDataResult(
            data=quote,
            provider=MarketDataProvider.JPMORGAN,
            capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
            correlation_id=request.correlation_id,
            retrieved_at=item.received_at,
            cache_status=CacheStatus.HIT if hit else CacheStatus.MISS,
            quality_status=QualityStatus.VALID,
            warnings=("QUOTE_DATE_AND_TIMEZONE_UNKNOWN", "ISSUER_INDICATION_NOT_EXECUTABLE"),
            retry_count=0,
            provider_call_cost=0,
            reason_code="QUOTE_TIMESTAMP_UNKNOWN_INDICATIVE_ANALYSIS_ONLY",
        )
