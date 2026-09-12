"""Bounded snapshot transport with process-local single-flight and error backoff."""

import asyncio
import json
import re
from collections import OrderedDict
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from time import monotonic
from typing import Any, NoReturn

import httpx

from app.core.config.frankfurt import FrankfurtQuoteSettings, FrankfurtSourceMode
from app.providers.frankfurt_quotes.public import (
    PUBLIC_EXCHANGE_CODE,
    PUBLIC_URL,
    FrankfurtPublicPrice,
)
from app.providers.frankfurt_quotes.schema import FrankfurtSnapshot, FrankfurtSourceError

# Only temporary transport failures permit explicitly disclosed historical reuse.
# Authentication, identity, schema and empty-response errors remain fail-closed.
TRANSIENT_ERRORS = frozenset(
    {
        "FRANKFURT_TRANSPORT_TIMEOUT",
        "FRANKFURT_TRANSPORT_ERROR",
        "FRANKFURT_HTTP_408",
        "FRANKFURT_HTTP_429",
        "FRANKFURT_HTTP_500",
        "FRANKFURT_HTTP_502",
        "FRANKFURT_HTTP_503",
        "FRANKFURT_HTTP_504",
    }
)


def utc_now() -> datetime:
    return datetime.now(UTC)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON member")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError("Non-finite JSON number")


class FrankfurtSnapshotClient:
    def __init__(
        self,
        settings: FrankfurtQuoteSettings,
        *,
        client: httpx.AsyncClient | None = None,
        clock: Callable[[], datetime] = utc_now,
        timer: Callable[[], float] = monotonic,
    ) -> None:
        self.settings = settings
        self._client = client
        self._clock = clock
        self._timer = timer
        self._lock = asyncio.Lock()
        self._cached: OrderedDict[
            str, tuple[FrankfurtSnapshot | FrankfurtPublicPrice, datetime, float]
        ] = OrderedDict()
        self._next_fetch = 0.0
        self.last_error: str | None = None
        self.last_success_at: datetime | None = None

    async def load(self) -> tuple[FrankfurtSnapshot, datetime, bool]:
        if self.settings.source_mode is FrankfurtSourceMode.PUBLIC_WEBSITE:
            raise FrankfurtSourceError("FRANKFURT_ISIN_REQUIRED")
        value, retrieved_at, hit = await self._load()
        assert isinstance(value, FrankfurtSnapshot)
        return value, retrieved_at, hit

    async def load_public(self, isin: str) -> tuple[FrankfurtPublicPrice, datetime, bool]:
        if self.settings.source_mode is not FrankfurtSourceMode.PUBLIC_WEBSITE:
            raise FrankfurtSourceError("FRANKFURT_PUBLIC_MODE_REQUIRED")
        if re.fullmatch(r"[A-Z]{2}[A-Z0-9]{9}[0-9]", isin) is None:
            raise FrankfurtSourceError("FRANKFURT_ISIN_INVALID")
        value, retrieved_at, hit = await self._load(isin)
        assert isinstance(value, FrankfurtPublicPrice)
        return value, retrieved_at, hit

    async def _load(
        self, isin: str | None = None
    ) -> tuple[FrankfurtSnapshot | FrankfurtPublicPrice, datetime, bool]:
        reason = self.settings.readiness_reason
        if reason != "CONFIGURED_NOT_PROBED":
            raise FrankfurtSourceError(reason)
        async with self._lock:
            key = isin or "snapshot"
            if self._timer() < self._next_fetch:
                if self.last_error is not None:
                    raise FrankfurtSourceError(self.last_error)
                cached = self._cached.get(key)
                if cached is not None and self._timer() < cached[2]:
                    return cached[0], cached[1], True
                # One process-wide request budget, not one budget per holding.
                raise FrankfurtSourceError("FRANKFURT_REQUEST_THROTTLED")
            try:
                async with asyncio.timeout(self.settings.timeout_seconds):
                    raw = await self._read(isin)
                payload = json.loads(
                    raw,
                    parse_float=Decimal,
                    parse_constant=_reject_constant,
                    object_pairs_hook=_unique_object,
                )
                value: FrankfurtSnapshot | FrankfurtPublicPrice
                if isin is not None:
                    if payload == {}:
                        raise FrankfurtSourceError("FRANKFURT_PUBLIC_EMPTY_RESPONSE")
                    value = FrankfurtPublicPrice.model_validate(payload)
                    if value.isin != isin:
                        raise FrankfurtSourceError("FRANKFURT_ISIN_MISMATCH")
                else:
                    value = FrankfurtSnapshot.model_validate(payload)
                    if value.source != self.settings.source_name:
                        raise FrankfurtSourceError("FRANKFURT_SOURCE_MISMATCH")
                    if value.delay_seconds != self.settings.feed_delay_seconds:
                        raise FrankfurtSourceError("FRANKFURT_FEED_DELAY_MISMATCH")
            except ValueError:
                self._fail("FRANKFURT_SCHEMA_INVALID")
            except TimeoutError:
                self._fail("FRANKFURT_TRANSPORT_TIMEOUT")
            except FrankfurtSourceError as exc:
                self._fail(str(exc))
            retrieved_at = self._clock()
            self.last_success_at = retrieved_at
            self.last_error = None
            self._next_fetch = self._timer() + self.settings.refresh_interval_seconds
            self._cached[key] = (value, retrieved_at, self._next_fetch)
            self._cached.move_to_end(key)
            if len(self._cached) > 256:
                self._cached.popitem(last=False)
            return value, retrieved_at, False

    def _fail(self, reason: str) -> NoReturn:
        if reason not in TRANSIENT_ERRORS:
            self._cached.clear()
        self.last_error = reason
        self._next_fetch = self._timer() + max(60, self.settings.refresh_interval_seconds)
        raise FrankfurtSourceError(reason) from None

    def cached_after_error(
        self, reason: str, isin: str | None = None
    ) -> tuple[FrankfurtSnapshot | FrankfurtPublicPrice, datetime] | None:
        """Historical evidence only; strict load/setup/probe still report the failure.

        The adapter must reassess identity/price/time and disclose this error.
        Retrieval time and the request budget are never changed by this read.
        """
        if self.settings.readiness_reason != "CONFIGURED_NOT_PROBED":
            return None
        if reason not in TRANSIENT_ERRORS and reason != "FRANKFURT_REQUEST_THROTTLED":
            return None
        if self.last_error is not None and self.last_error not in TRANSIENT_ERRORS:
            return None
        cached = self._cached.get(isin or "snapshot")
        return (cached[0], cached[1]) if cached is not None else None

    async def _read(self, isin: str | None = None) -> bytes:
        if self.settings.source_mode is FrankfurtSourceMode.LOCAL_FILE:
            return await asyncio.to_thread(self._read_file)
        if self._client is not None:
            return await self._read_http(self._client, isin)
        async with httpx.AsyncClient(
            timeout=self.settings.timeout_seconds, follow_redirects=False, trust_env=False
        ) as client:
            return await self._read_http(client, isin)

    def _read_file(self) -> bytes:
        assert self.settings.local_file is not None
        try:
            with Path(self.settings.local_file).open("rb") as handle:
                raw = handle.read(self.settings.max_response_bytes + 1)
        except OSError:
            raise FrankfurtSourceError("FRANKFURT_LOCAL_FILE_UNAVAILABLE") from None
        if len(raw) > self.settings.max_response_bytes:
            raise FrankfurtSourceError("FRANKFURT_PAYLOAD_TOO_LARGE")
        return raw

    async def _read_http(self, client: httpx.AsyncClient, isin: str | None = None) -> bytes:
        headers = {"Accept": "application/json"}
        if isin is not None:
            url = httpx.URL(PUBLIC_URL, params={"isin": isin, "mic": PUBLIC_EXCHANGE_CODE})
        else:
            assert self.settings.snapshot_url is not None
            url = httpx.URL(self.settings.snapshot_url)
        if isin is None and self.settings.bearer_token is not None:
            headers["Authorization"] = f"Bearer {self.settings.bearer_token.get_secret_value()}"
        try:
            async with client.stream(
                "GET",
                url,
                headers=headers,
                follow_redirects=False,
                timeout=self.settings.timeout_seconds,
            ) as response:
                if response.status_code != 200:
                    raise FrankfurtSourceError(f"FRANKFURT_HTTP_{response.status_code}")
                mime = response.headers.get("content-type", "").split(";")[0].strip().lower()
                if mime != "application/json":
                    raise FrankfurtSourceError("FRANKFURT_CONTENT_TYPE_INVALID")
                raw = bytearray()
                async for chunk in response.aiter_bytes():
                    if len(raw) + len(chunk) > self.settings.max_response_bytes:
                        raise FrankfurtSourceError("FRANKFURT_PAYLOAD_TOO_LARGE")
                    raw.extend(chunk)
                return bytes(raw)
        except httpx.TimeoutException:
            raise FrankfurtSourceError("FRANKFURT_TRANSPORT_TIMEOUT") from None
        except httpx.HTTPError:
            raise FrankfurtSourceError("FRANKFURT_TRANSPORT_ERROR") from None
