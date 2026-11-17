"""Bounded original-data acquisition against the documented ARIVA MDS API.

This is an evaluation transport, not a B58 source qualification or quote adapter.
The public 0.6.25 schema does not document an original timestamp for Status.
See docs/reviews/B58_ARIVA_ACQUISITION_2026-11-17.md for the actual source proof.
"""

import asyncio
import base64
import hashlib
import json
import re
from collections import Counter
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal, DecimalException
from typing import Any
from urllib.parse import quote_plus

import httpx
from pydantic import SecretStr

API_URL = "https://mds.ariva-services.de/api/v1"
TOKEN_URL = "https://auth.ariva-services.de/auth/realms/mds/protocol/openid-connect/token"
SOURCE_ID = "XSC"  # ARIVA source code, deliberately not an ISO MIC.
MAX_ISINS = 64
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
ISIN_PATTERN = re.compile(r"[A-Z]{2}[A-Z0-9]{9}[0-9]\Z")
ORIGINAL_TIME_PATTERN = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})\Z"
)


class ArivaProbeError(ValueError):
    """Only a fixed reason code/status escapes the transport; no secret-bearing body."""

    def __init__(self, reason: str, *, http_status: int | None = None) -> None:
        super().__init__(reason)
        self.http_status = http_status


@dataclass(frozen=True)
class ArivaCredentials:
    client_id: SecretStr
    client_secret: SecretStr

    def __post_init__(self) -> None:
        for value in (self.client_id, self.client_secret):
            text = value.get_secret_value()
            if not text or any(ord(character) < 32 for character in text):
                raise ArivaProbeError("ARIVA_CREDENTIALS_INVALID")


@dataclass(frozen=True)
class CapturedResponse:
    url: str
    retrieved_at: datetime
    sha256: str
    raw_text: str = field(repr=False)
    payload: dict[str, Any] = field(repr=False)


def _now() -> datetime:
    return datetime.now(UTC)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate member")
        result[key] = value
    return result


def _reject_constant(_value: str) -> None:
    raise ValueError("non-finite number")


def _json_object(raw: bytes) -> tuple[str, dict[str, Any]]:
    try:
        original = raw.decode("utf-8")
        payload = json.loads(
            original,
            parse_float=Decimal,
            parse_constant=_reject_constant,
            object_pairs_hook=_unique_object,
        )
    except (UnicodeError, ValueError, RecursionError, DecimalException):
        raise ArivaProbeError("ARIVA_JSON_INVALID") from None
    if not isinstance(payload, dict):
        raise ArivaProbeError("ARIVA_JSON_OBJECT_REQUIRED")
    return original, payload


def _contains_secret(payload: dict[str, Any], secrets: tuple[str, ...]) -> bool:
    pending: list[Any] = [payload]
    while pending:
        value = pending.pop()
        if isinstance(value, str) and any(secret in value for secret in secrets):
            return True
        if isinstance(value, dict):
            pending.extend(value.keys())
            pending.extend(value.values())
        elif isinstance(value, list):
            pending.extend(value)
    return False


class ArivaProbeClient:
    """One client-credentials exchange, bounded GETs, no retries or source fallback.

    Callers create a dedicated AsyncClient with trust_env=False. Each request
    forbids redirects and overrides any default Authorization header explicitly.
    A transport failure has no market-status meaning.
    """

    def __init__(
        self,
        http: httpx.AsyncClient,
        credentials: ArivaCredentials,
        *,
        clock: Callable[[], datetime] = _now,
    ) -> None:
        self._http = http
        self._credentials = credentials
        self._clock = clock
        self._token: SecretStr | None = None
        self._authentication_lock = asyncio.Lock()

    async def source(self) -> CapturedResponse:
        return await self._get("/sources/XSC")

    async def listings(self, isin: str) -> CapturedResponse:
        if ISIN_PATTERN.fullmatch(isin) is None:
            raise ArivaProbeError("ARIVA_ISIN_INVALID")
        return await self._get(f"/instruments/{isin}/listings", params=[("sourceId", SOURCE_ID)])

    async def marketstates(self, isins: tuple[str, ...]) -> CapturedResponse:
        if not isins or len(isins) > MAX_ISINS or len(set(isins)) != len(isins):
            raise ArivaProbeError("ARIVA_TARGET_COUNT_INVALID")
        if any(ISIN_PATTERN.fullmatch(isin) is None for isin in isins):
            raise ArivaProbeError("ARIVA_ISIN_INVALID")
        # Omitted listing variant returns all variants at this exact source.
        # Never infer a variant from EUR, choose a random source, or accept the
        # default 'best licensed' quality, which can be delayed.
        params = [("marketstateQuery", f"{isin}@{SOURCE_ID}") for isin in isins]
        params.append(("quality", "REALTIME"))
        return await self._get("/marketstates/", params=params)

    async def _authenticate(self) -> str:
        async with self._authentication_lock:
            if self._token is None:
                auth = httpx.BasicAuth(
                    quote_plus(self._credentials.client_id.get_secret_value()),
                    quote_plus(self._credentials.client_secret.get_secret_value()),
                )
                raw, _url = await self._request(
                    "POST",
                    TOKEN_URL,
                    auth=auth,
                    data={"grant_type": "client_credentials"},
                )
                _original, payload = _json_object(raw)
                token, kind = payload.get("access_token"), payload.get("token_type")
                if (
                    not isinstance(token, str)
                    or not token
                    or len(token) > 65536
                    or any(character.isspace() or ord(character) < 32 for character in token)
                    or not isinstance(kind, str)
                    or kind.casefold() != "bearer"
                ):
                    raise ArivaProbeError("ARIVA_TOKEN_RESPONSE_INVALID")
                self._token = SecretStr(token)
            return self._token.get_secret_value()

    async def _get(
        self, path: str, *, params: list[tuple[str, str]] | None = None
    ) -> CapturedResponse:
        token = await self._authenticate()
        raw, url = await self._request(
            "GET", API_URL + path, params=params, authorization=f"Bearer {token}"
        )
        # Do not persist an unexpected server echo of credentials or a token.
        secrets = (
            token,
            self._credentials.client_id.get_secret_value(),
            self._credentials.client_secret.get_secret_value(),
            base64.b64encode(
                (
                    quote_plus(self._credentials.client_id.get_secret_value())
                    + ":"
                    + quote_plus(self._credentials.client_secret.get_secret_value())
                ).encode("ascii")
            ).decode("ascii"),
        )
        if any(secret.encode("utf-8") in raw for secret in secrets):
            raise ArivaProbeError("ARIVA_SECRET_IN_RESPONSE")
        original, payload = _json_object(raw)
        if _contains_secret(payload, secrets):
            raise ArivaProbeError("ARIVA_SECRET_IN_RESPONSE")
        captured_at = self._clock()
        if captured_at.utcoffset() is None:
            raise ArivaProbeError("ARIVA_CAPTURE_CLOCK_INVALID")
        return CapturedResponse(
            url=url,
            retrieved_at=captured_at,
            sha256=hashlib.sha256(raw).hexdigest(),
            raw_text=original,
            payload=payload,
        )

    async def _request(
        self,
        method: str,
        url: str,
        *,
        params: list[tuple[str, str]] | None = None,
        auth: httpx.BasicAuth | None = None,
        data: dict[str, str] | None = None,
        authorization: str = "",
    ) -> tuple[bytes, str]:
        try:
            async with asyncio.timeout(30):
                async with self._http.stream(
                    method,
                    url,
                    params=httpx.QueryParams(tuple(params)) if params is not None else None,
                    auth=auth,
                    data=data,
                    headers={"Accept": "application/json", "Authorization": authorization},
                    follow_redirects=False,
                    timeout=10,
                ) as response:
                    if response.status_code != 200:
                        # Do not retain error bodies, cookies, token URLs with
                        # server-added arguments, or uncontracted retry values.
                        raise ArivaProbeError(
                            f"ARIVA_HTTP_{response.status_code}",
                            http_status=response.status_code,
                        )
                    content_type = response.headers.get("Content-Type", "").split(";")[0]
                    if content_type.strip().lower() != "application/json":
                        raise ArivaProbeError("ARIVA_CONTENT_TYPE_INVALID")
                    body = bytearray()
                    async for chunk in response.aiter_bytes(chunk_size=65536):
                        body.extend(chunk)
                        if len(body) > MAX_RESPONSE_BYTES:
                            raise ArivaProbeError("ARIVA_RESPONSE_TOO_LARGE")
                    return bytes(body), str(response.request.url)
        except (httpx.HTTPError, TimeoutError):
            raise ArivaProbeError("ARIVA_TRANSPORT_FAILED") from None


def _bid_fields(row: dict[str, Any], captured_at: datetime) -> dict[str, Any]:
    bid = row.get("bid")
    value = bid.get("value") if isinstance(bid, dict) else None
    original_time = bid.get("datetime") if isinstance(bid, dict) else None
    reasons: list[str] = []
    price = value if isinstance(value, (int, Decimal)) and not isinstance(value, bool) else None
    if price is None or not Decimal(price).is_finite() or price <= 0:
        price = None
        reasons.append("ORIGINAL_BID_VALUE_MISSING_OR_INVALID")
    observed_at: datetime | None = None
    if isinstance(original_time, str) and ORIGINAL_TIME_PATTERN.fullmatch(original_time):
        with suppress(ValueError):
            observed_at = datetime.fromisoformat(original_time)
    if observed_at is None:
        reasons.append("ORIGINAL_BID_TIME_MISSING_OR_INVALID")
    age = (captured_at - observed_at).total_seconds() if observed_at is not None else None
    if age is not None:
        if age < 0:
            reasons.append("ORIGINAL_BID_TIME_FUTURE")
        elif age > 900:
            reasons.append("ORIGINAL_BID_OLDER_THAN_900_SECONDS")
    indicative = bid.get("isIndicative", False) if isinstance(bid, dict) else None
    if indicative is not False:
        reasons.append("BID_INDICATIVE_OR_FLAG_INVALID")
    return {
        "bid": str(price) if price is not None else None,
        "bid_original_time_text": original_time if isinstance(original_time, str) else None,
        "bid_age_seconds_at_capture": age,
        "bid_is_indicative": indicative,
        "bid_limitations": reasons,
    }


def _instrument_isin(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value[5:-1] if value.startswith("ISIN(") and value.endswith(")") else value


def inspect_marketstates(
    response: CapturedResponse,
    *,
    isins: tuple[str, ...],
    source: CapturedResponse,
    listings: tuple[CapturedResponse, ...] = (),
) -> dict[str, Any]:
    """Describe delivered facts without granting a route or interpreting status codes.

    The return value deliberately cannot become a positive B58 result, even if
    an undocumented 'status.datetime' happens to appear in a future response.
    Listing MIC, original-time semantics, negative-event coverage and recovery
    require the separate supplier qualification; a snapshot cannot prove them.
    """
    items = response.payload.get("items")
    if not isinstance(items, list) or len(items) > MAX_ISINS * 16:
        raise ArivaProbeError("ARIVA_MARKETSTATES_SHAPE_INVALID")
    if not all(isinstance(row, dict) for row in items):
        raise ArivaProbeError("ARIVA_MARKETSTATES_SHAPE_INVALID")
    listing_rows: list[dict[str, Any]] = []
    for listing_response in listings:
        candidates = listing_response.payload.get("items")
        if not isinstance(candidates, list) or len(candidates) > MAX_ISINS * 16:
            raise ArivaProbeError("ARIVA_LISTINGS_SHAPE_INVALID")
        if not all(isinstance(candidate, dict) for candidate in candidates):
            raise ArivaProbeError("ARIVA_LISTINGS_SHAPE_INVALID")
        listing_rows.extend(candidates)
    rows: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    for item in items:
        instrument = item.get("instrumentId")
        isin = _instrument_isin(instrument)
        limits = ["STATUS_ORIGINAL_TIME_AND_SEMANTICS_UNDOCUMENTED"]
        if isin not in isins or item.get("sourceId") != SOURCE_ID:
            limits.append("INSTRUMENT_OR_SOURCE_MISMATCH")
        else:
            counts[isin] += 1
        if item.get("quality") != "REALTIME":
            limits.append("REALTIME_QUALITY_NOT_DELIVERED")
        if not isinstance(item.get("currency"), str) or not re.fullmatch(
            r"[A-Z]{3}", item["currency"]
        ):
            limits.append("CURRENCY_MISSING_OR_INVALID")
        variant, marketstate_id = item.get("listingVariant"), item.get("marketstateId")
        expected_ids = (f"{isin},{variant}@{SOURCE_ID}", f"ISIN({isin}),{variant}@{SOURCE_ID}")
        if not isinstance(variant, str) or not variant or marketstate_id not in expected_ids:
            limits.append("LISTING_IDENTITY_REQUIRES_CLARIFICATION")
        status = item.get("status")
        if not isinstance(status, dict) or not status:
            limits.append("INSTRUMENT_STATUS_NOT_DELIVERED")
        matches = [
            candidate
            for candidate in listing_rows
            if candidate.get("marketstateId") in expected_ids
            and _instrument_isin(candidate.get("instrumentId")) == isin
            and candidate.get("sourceId") == SOURCE_ID
            and candidate.get("listingVariant") == variant
            and candidate.get("currency") == item.get("currency")
        ]
        listing = matches[0] if len(matches) == 1 else {}
        segment_mic = listing.get("segmentMic")
        if (
            len(matches) != 1
            or not isinstance(segment_mic, str)
            or re.fullmatch(r"[A-Z0-9]{4}", segment_mic) is None
            or listing.get("licensedQuality") != "REALTIME"
        ):
            limits.append("LISTING_METADATA_MISSING_AMBIGUOUS_OR_NOT_REALTIME")
        bid = _bid_fields(item, response.retrieved_at)
        rows.append(
            {
                "instrument_id": instrument,
                "source_id": item.get("sourceId"),
                "marketstate_id": marketstate_id,
                "listing_variant": variant,
                "currency": item.get("currency"),
                "quality": item.get("quality"),
                "listing_segment_mic": segment_mic,
                "listing_licensed_quality": listing.get("licensedQuality"),
                **bid,
                "status_present": isinstance(status, dict) and bool(status),
                "status_original_time": None,
                "status_temporal_meaning": "UNDOCUMENTED",
                "status_fields": sorted(status) if isinstance(status, dict) else [],
                "limitations": limits,
            }
        )
    operating_mic = source.payload.get("operatingMic")
    source_bound = source.payload.get("sourceId") == SOURCE_ID
    return {
        "b58_qualified": False,
        "result": "B58_UNQUALIFIED",
        "source_id_matches": source_bound,
        "source_operating_mic": operating_mic,
        "source_code_is_not_a_mic": True,
        "listing_binding_verified": False,
        "delivered_isins": sorted(counts),
        "missing_isins": [isin for isin in isins if not counts[isin]],
        "multiple_rows_requiring_listing_review": [isin for isin in isins if counts[isin] > 1],
        "rows": rows,
        "limitations": [
            "STATUS_ORIGINAL_TIME_AND_SEMANTICS_UNDOCUMENTED",
            "BID_ORIGINAL_TIME_SEMANTICS_REQUIRE_SOURCE_PROOF",
            "NEGATIVE_STATUS_AND_RECOVERY_NOT_PROVEN_BY_SNAPSHOT",
            "LISTING_BINDING_AND_USAGE_RIGHTS_REQUIRE_SEPARATE_QUALIFICATION",
        ]
        + ([] if source_bound else ["SOURCE_METADATA_MISMATCH"]),
    }
