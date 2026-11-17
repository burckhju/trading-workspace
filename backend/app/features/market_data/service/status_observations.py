"""Write original status independently; read exact points without refresh or writes."""

import hashlib
import json
from datetime import UTC, datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import TypeAdapter
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.market_data.domain.enums import MarketDataCapability, MarketDataProvider
from app.features.market_data.domain.models import WarrantQuoteSnapshot
from app.features.market_data.domain.original_market_status_evidence import (
    OriginalMarketStatusEvidence,
    _utc,
)
from app.features.market_data.domain.status_observations import (
    MarketStatusObservation,
    StatusEvidenceRead,
    StatusRouteBinding,
    StatusSourceHistory,
    resolve_status_observations,
)
from app.features.market_data.persistence.models import WarrantMarketStatusObservationModel
from app.features.market_data.persistence.quote_identity import QuoteIdentity
from app.features.market_data.service.types import MarketDataResult, WarrantQuoteRequest

_ORIGINAL = TypeAdapter(OriginalMarketStatusEvidence)
_ROW = WarrantMarketStatusObservationModel


async def capture_market_status(
    session: AsyncSession,
    *,
    request: WarrantQuoteRequest,
    warrant_id: UUID,
    provider: MarketDataProvider,
    identity: QuoteIdentity,
    result: MarketDataResult[WarrantQuoteSnapshot | None] | None,
    error: str | None,
    captured_at: datetime,
) -> None:
    """Append under the caller's listing lock; never use price suitability.

    Failures are delivery gaps. Original status needs its own exact route and
    clocks but does not require a price, VALID price quality, or the five-minute
    sample slot. Retained/cached-after-error payloads cannot become new facts.
    """
    _utc(captured_at, "captured_at")
    quote = result.data if result is not None else None
    original = quote.original_market_status if quote is not None else None
    reason = error
    if reason is None and (quote is None or original is None):
        reason = "ORIGINAL_MARKET_STATUS_NOT_DELIVERED"
    if reason is None and quote is not None and result is not None:
        if quote.retained or quote.refresh_error:
            reason = "RETAINED_MARKET_STATUS_IS_NOT_NEW_OBSERVATION"
        elif (
            result.provider != provider
            or result.capability != MarketDataCapability.WARRANT_LISTING_QUOTE
            or quote.warrant_listing_id != request.warrant_listing_id
            or quote.provider_symbol != identity.isin
            or quote.provider_exchange_code != identity.exchange
            or quote.venue_mic != identity.mic
            or quote.currency != identity.currency
            or (quote.isin is not None and quote.isin != identity.isin)
            or (quote.wkn is not None and identity.wkn is not None and quote.wkn != identity.wkn)
            or (original is not None and original.isin != identity.isin)
            or (original is not None and original.venue_mic != identity.mic)
        ):
            reason = "ORIGINAL_MARKET_STATUS_ROUTE_MISMATCH"
        elif result.retrieved_at > captured_at or (
            original is not None and original.generated_at > result.retrieved_at
        ):
            reason = "ORIGINAL_MARKET_STATUS_TIME_INCONSISTENT"
    if reason is not None:
        original = None
    payload = _ORIGINAL.dump_python(original, mode="json") if original is not None else None
    retrieved_at = (
        result.retrieved_at if result is not None and result.retrieved_at <= captured_at else None
    )
    binding = {
        "workspace_id": str(request.workspace_id),
        "warrant_id": str(warrant_id),
        "warrant_listing_id": str(request.warrant_listing_id),
        "provider": provider.value,
        "identity_key": identity.key,
        "isin": identity.isin,
        "venue_mic": identity.mic,
    }
    content = {
        "version": "market-status-observation-v1",
        "route": binding,
        "original": payload,
        "reason": reason,
        # A status event deduplicates across new requests and retrieval clocks.
        # A failed attempt belongs to the attempted request, never a source time.
        "attempt_id": str(request.correlation_id) if original is None else None,
    }
    fingerprint = hashlib.sha256(
        json.dumps(content, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    record_id = uuid5(NAMESPACE_URL, f"market-status-observation-v1:{fingerprint}")
    if await session.get(_ROW, record_id) is not None:
        return
    session.add(
        _ROW(
            id=record_id,
            workspace_id=request.workspace_id,
            warrant_id=warrant_id,
            warrant_listing_id=request.warrant_listing_id,
            provider=provider.value,
            identity_key=identity.key,
            isin=identity.isin,
            venue_mic=identity.mic,
            fingerprint=fingerprint,
            kind="STATUS" if original is not None else "GAP",
            observed_at=original.observed_at if original is not None else None,
            retrieved_at=retrieved_at,
            captured_at=captured_at,
            source_contract=original.source_contract if original is not None else None,
            source_reference=original.source_reference if original is not None else None,
            original=payload,
            reason=reason,
        )
    )


def _as_utc(value: datetime | None) -> datetime | None:
    # SQLite round-trips timezone-aware columns as naive; persisted instants are
    # UTC by contract. PostgreSQL returns the timezone-aware value unchanged.
    return value.replace(tzinfo=UTC) if value is not None and value.tzinfo is None else value


def _observation(row: WarrantMarketStatusObservationModel) -> MarketStatusObservation:
    captured_at = _as_utc(row.captured_at)
    assert captured_at is not None
    original = _ORIGINAL.validate_python(row.original) if row.original is not None else None
    if (
        row.kind != ("STATUS" if original is not None else "GAP")
        or (original is None and row.observed_at is not None)
        or (
            original is not None
            and (
                original.observed_at != _as_utc(row.observed_at)
                or original.source_contract != row.source_contract
                or original.source_reference != row.source_reference
            )
        )
    ):
        raise ValueError("ORIGINAL_MARKET_STATUS_STORED_BINDING_INVALID")
    return MarketStatusObservation(
        id=row.id,
        fingerprint=row.fingerprint,
        route=StatusRouteBinding(
            row.workspace_id,
            row.warrant_id,
            row.warrant_listing_id,
            row.provider,
            row.identity_key,
            row.isin,
            row.venue_mic,
        ),
        captured_at=captured_at,
        retrieved_at=_as_utc(row.retrieved_at),
        original=original,
        reason=row.reason,
    )


class MarketStatusReader:
    """Caller owns one consistent transaction; no provider I/O, flush or commit."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def read(
        self,
        *,
        route: StatusRouteBinding,
        event_at: datetime,
        known_at: datetime,
        source_contract: str | None = None,
        source_reference: str | None = None,
    ) -> StatusEvidenceRead:
        _utc(event_at, "event_at")
        _utc(known_at, "known_at")
        if event_at > known_at:
            raise ValueError("STATUS_EVENT_AFTER_KNOWN_AT")
        with self._session.no_autoflush:
            scope = (
                _ROW.workspace_id == route.workspace_id,
                _ROW.warrant_id == route.warrant_id,
                _ROW.warrant_listing_id == route.warrant_listing_id,
                _ROW.provider == route.provider,
                _ROW.identity_key == route.identity_key,
                _ROW.isin == route.isin,
                _ROW.venue_mic == route.venue_mic,
                _ROW.captured_at <= known_at,
            )
            source_scope = (
                *scope,
                *(() if source_contract is None else (_ROW.source_contract == source_contract,)),
                *(() if source_reference is None else (_ROW.source_reference == source_reference,)),
            )
            latest_point = select(func.max(_ROW.observed_at)).where(*source_scope).scalar_subquery()
            latest_capture = select(func.max(_ROW.captured_at)).where(*scope).scalar_subquery()
            latest_gap = (
                select(func.max(_ROW.captured_at))
                .where(*scope, _ROW.kind == "GAP")
                .scalar_subquery()
            )
            # Fetch only relevant time slices, including all conflicts at each
            # slice. Never scan or truncate the full retained event history.
            rows = (
                await self._session.scalars(
                    select(_ROW).where(
                        *scope,
                        or_(
                            _ROW.observed_at == event_at,
                            _ROW.observed_at == latest_point,
                            _ROW.captured_at == latest_capture,
                            _ROW.captured_at == latest_gap,
                        ),
                    )
                )
            ).all()
            route_fields = (
                _ROW.provider,
                _ROW.identity_key,
                _ROW.isin,
                _ROW.venue_mic,
                _ROW.source_contract,
                _ROW.source_reference,
            )
            streams = (
                (
                    await self._session.execute(
                        select(
                            *route_fields,
                            func.min(_ROW.captured_at).label("first_captured_at"),
                            func.max(_ROW.captured_at).label("last_captured_at"),
                        )
                        .where(
                            _ROW.workspace_id == route.workspace_id,
                            _ROW.warrant_id == route.warrant_id,
                            _ROW.warrant_listing_id == route.warrant_listing_id,
                            _ROW.captured_at <= known_at,
                        )
                        .group_by(*route_fields)
                        .order_by(*route_fields)
                    )
                )
                .mappings()
                .all()
            )
            history = []
            for stream in streams:
                first, last = _as_utc(stream["first_captured_at"]), _as_utc(
                    stream["last_captured_at"]
                )
                assert first is not None and last is not None
                history.append(
                    StatusSourceHistory(
                        StatusRouteBinding(
                            route.workspace_id,
                            route.warrant_id,
                            route.warrant_listing_id,
                            stream["provider"],
                            stream["identity_key"],
                            stream["isin"],
                            stream["venue_mic"],
                        ),
                        stream["source_contract"],
                        stream["source_reference"],
                        first,
                        last,
                    )
                )
            return resolve_status_observations(
                tuple(_observation(row) for row in rows),
                route=route,
                event_at=event_at,
                known_at=known_at,
                source_contract=source_contract,
                source_reference=source_reference,
                other_route_keys=tuple(
                    sorted({item.route.identity_key for item in history} - {route.identity_key})
                ),
                source_history=tuple(history),
            )
