"""Bounded snapshot transport with process-local single-flight and error backoff."""

import asyncio
import json
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from time import monotonic
from typing import Any, NoReturn

import httpx

from app.core.config.frankfurt import FrankfurtQuoteSettings, FrankfurtSourceMode
from app.providers.frankfurt_quotes.schema import FrankfurtSnapshot, FrankfurtSourceError


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
        self._cached: tuple[FrankfurtSnapshot, datetime] | None = None
        self._next_fetch = 0.0
        self.last_error: str | None = None
        self.last_success_at: datetime | None = None

    async def load(self) -> tuple[FrankfurtSnapshot, datetime, bool]:
        reason = self.settings.readiness_reason
        if reason != "CONFIGURED_NOT_PROBED":
            raise FrankfurtSourceError(reason)
        async with self._lock:
            if self._timer() < self._next_fetch:
                if self.last_error is not None:
                    raise FrankfurtSourceError(self.last_error)
                if self._cached is not None:
                    return self._cached[0], self._cached[1], True
            try:
                async with asyncio.timeout(self.settings.timeout_seconds):
                    raw = await self._read()
                payload = json.loads(
                    raw,
                    parse_float=Decimal,
                    parse_constant=_reject_constant,
                    object_pairs_hook=_unique_object,
                )
                snapshot = FrankfurtSnapshot.model_validate(payload)
                if snapshot.source != self.settings.source_name:
                    raise FrankfurtSourceError("FRANKFURT_SOURCE_MISMATCH")
                if snapshot.delay_seconds != self.settings.feed_delay_seconds:
                    raise FrankfurtSourceError("FRANKFURT_FEED_DELAY_MISMATCH")
            except ValueError:
                self._fail("FRANKFURT_SCHEMA_INVALID")
            except TimeoutError:
                self._fail("FRANKFURT_TRANSPORT_TIMEOUT")
            except FrankfurtSourceError as exc:
                self._fail(str(exc))
            retrieved_at = self._clock()
            self._cached = (snapshot, retrieved_at)
            self.last_success_at = retrieved_at
            self.last_error = None
            self._next_fetch = self._timer() + self.settings.refresh_interval_seconds
            return snapshot, retrieved_at, False

    def _fail(self, reason: str) -> NoReturn:
        self._cached = None  # Never silently resurrect an older successful snapshot.
        self.last_error = reason
        self._next_fetch = self._timer() + max(60, self.settings.refresh_interval_seconds)
        raise FrankfurtSourceError(reason) from None

    async def _read(self) -> bytes:
        if self.settings.source_mode is FrankfurtSourceMode.LOCAL_FILE:
            return await asyncio.to_thread(self._read_file)
        if self._client is not None:
            return await self._read_http(self._client)
        async with httpx.AsyncClient(
            timeout=self.settings.timeout_seconds, follow_redirects=False, trust_env=False
        ) as client:
            return await self._read_http(client)

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

    async def _read_http(self, client: httpx.AsyncClient) -> bytes:
        assert self.settings.snapshot_url is not None
        headers = {"Accept": "application/json"}
        if self.settings.bearer_token is not None:
            headers["Authorization"] = f"Bearer {self.settings.bearer_token.get_secret_value()}"
        try:
            async with client.stream(
                "GET",
                self.settings.snapshot_url,
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
