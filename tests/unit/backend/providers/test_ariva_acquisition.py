"""Synthetic acquisition tests: every external request is intercepted."""

import asyncio
import hashlib
import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from pydantic import SecretStr

from app.providers.ariva_mds.evaluation import (
    API_URL,
    MAX_RESPONSE_BYTES,
    TOKEN_URL,
    ArivaCredentials,
    ArivaProbeClient,
    ArivaProbeError,
    CapturedResponse,
    inspect_marketstates,
)

NOW = datetime(2026, 11, 17, 10, tzinfo=UTC)
ISIN = "DE0000000001"
OTHER = "DE0000000002"
TOKEN = "synthetic-access-token-never-real"
CREDENTIALS = ArivaCredentials(
    client_id=SecretStr("synthetic-client-identifier"),
    client_secret=SecretStr("synthetic-client-secret-never-real"),
)


def captured(payload: dict, *, url: str = API_URL + "/marketstates/") -> CapturedResponse:
    raw = json.dumps(payload, separators=(",", ":"))
    return CapturedResponse(url, NOW, hashlib.sha256(raw.encode()).hexdigest(), raw, payload)


def row(**updates: object) -> dict:
    return {
        "instrumentId": ISIN,
        "sourceId": "XSC",
        "marketstateId": f"{ISIN},EUR@XSC",
        "listingVariant": "EUR",
        "currency": "EUR",
        "quality": "REALTIME",
        "bid": {"value": 2, "datetime": NOW.isoformat()},
        "status": {"tradingPhase": "trading", "instrumentStatus": 1},
        **updates,
    }


def inspect(rows: list[dict], *, source: dict | None = None, listings: tuple = ()) -> dict:
    return inspect_marketstates(
        captured({"items": rows}),
        isins=(ISIN,),
        source=captured(source or {"sourceId": "XSC", "operatingMic": "XFRA"}),
        listings=listings,
    )


@pytest.mark.asyncio
async def test_real_documented_requests_keep_originals_and_never_put_credentials_in_urls() -> None:
    requests = []
    original = b'{ "items": [{"instrumentId":"DE0000000001","bid":{"value":0.1200}}] }'

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if str(request.url) == TOKEN_URL:
            assert request.method == "POST"
            assert request.headers["Authorization"].startswith("Basic ")
            assert request.content == b"grant_type=client_credentials"
            return httpx.Response(200, json={"access_token": TOKEN, "token_type": "Bearer"})
        assert request.method == "GET"
        assert request.headers["Authorization"] == f"Bearer {TOKEN}"
        if request.url.path.endswith("/sources/XSC"):
            return httpx.Response(200, json={"sourceId": "XSC", "operatingMic": "XFRA"})
        if request.url.path.endswith("/listings"):
            assert request.url.params["sourceId"] == "XSC"
            return httpx.Response(200, json={"items": []})
        assert request.url.path == "/api/v1/marketstates/"
        assert request.url.params.get_list("marketstateQuery") == [f"{ISIN}@XSC", f"{OTHER}@XSC"]
        assert request.url.params["quality"] == "REALTIME"
        assert "listingVariant" not in request.url.params
        return httpx.Response(200, content=original, headers={"content-type": "application/json"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle), trust_env=False) as http:
        client = ArivaProbeClient(http, CREDENTIALS, clock=lambda: NOW)
        await client.source()
        result = await client.marketstates((ISIN, OTHER))
        await client.listings(ISIN)
    assert len(requests) == 4  # One token, one source, one batch, one scoped listing.
    assert result.raw_text.encode() == original
    assert result.sha256 == hashlib.sha256(original).hexdigest()
    assert result.retrieved_at == NOW
    assert str(result.payload["items"][0]["bid"]["value"]) == "0.1200"
    for request in requests:
        assert "secret" not in str(request.url)
        assert TOKEN not in str(request.url)
        assert request.headers["Accept"] == "application/json"
    assert TOKEN not in repr(client)
    assert "synthetic-client-secret" not in repr(CREDENTIALS)


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [301, 307, 401, 403, 404, 429, 500, 503])
async def test_http_failure_is_not_retried_followed_or_reported_as_closed(status: int) -> None:
    requests = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            status,
            text=f"rejected credentials {TOKEN}",
            headers={"Location": "https://unrelated.invalid/collect", "Retry-After": "1"},
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handle), follow_redirects=True, trust_env=False
    ) as http:
        with pytest.raises(ArivaProbeError, match=f"ARIVA_HTTP_{status}") as caught:
            await ArivaProbeClient(http, CREDENTIALS).source()
    assert caught.value.http_status == status
    assert len(requests) == 1
    assert TOKEN not in str(caught.value)
    assert "CLOSED" not in str(caught.value)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("body", "content_type", "reason"),
    [
        (b'{"a":1,"a":2}', "application/json", "ARIVA_JSON_INVALID"),
        (b'{"a":NaN}', "application/json", "ARIVA_JSON_INVALID"),
        (b'{"a":1e999999999999999999999999}', "application/json", "ARIVA_JSON_INVALID"),
        (b"{", "application/json", "ARIVA_JSON_INVALID"),
        (b"\xff", "application/json", "ARIVA_JSON_INVALID"),
        (b"[]", "application/json", "ARIVA_JSON_OBJECT_REQUIRED"),
        (b"{}", "text/html", "ARIVA_CONTENT_TYPE_INVALID"),
        (b"x" * (MAX_RESPONSE_BYTES + 1), "application/json", "ARIVA_RESPONSE_TOO_LARGE"),
        (b"{}", "application/json", "ARIVA_TOKEN_RESPONSE_INVALID"),
        (b'{"access_token":"a b","token_type":"Bearer"}', "application/json", "ARIVA_TOKEN"),
        (b'{"access_token":"abc","token_type":"Basic"}', "application/json", "ARIVA_TOKEN"),
    ],
)
async def test_untrusted_responses_fail_closed_without_body_leaks(
    body: bytes, content_type: str, reason: str
) -> None:
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(
                200, content=body, headers={"Content-Type": content_type}
            )
        ),
        trust_env=False,
    ) as http:
        with pytest.raises(ArivaProbeError, match=reason):
            await ArivaProbeClient(http, CREDENTIALS).source()


@pytest.mark.asyncio
async def test_transport_exception_and_secret_echo_never_escape_into_original_capture() -> None:
    def failing(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout(f"timeout with {TOKEN}", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(failing), trust_env=False) as http:
        with pytest.raises(ArivaProbeError, match=r"^ARIVA_TRANSPORT_FAILED$"):
            await ArivaProbeClient(http, CREDENTIALS).source()

    def echo(request: httpx.Request) -> httpx.Response:
        if str(request.url) == TOKEN_URL:
            return httpx.Response(200, json={"access_token": TOKEN, "token_type": "bearer"})
        return httpx.Response(200, json={"sourceId": "XSC", "unexpected": TOKEN})

    async with httpx.AsyncClient(transport=httpx.MockTransport(echo), trust_env=False) as http:
        with pytest.raises(ArivaProbeError, match=r"^ARIVA_SECRET_IN_RESPONSE$"):
            await ArivaProbeClient(http, CREDENTIALS).source()


@pytest.mark.asyncio
async def test_invalid_target_and_credentials_fail_before_any_external_call() -> None:
    def forbidden(_request: httpx.Request) -> httpx.Response:
        pytest.fail("No external call is permitted for invalid targets")

    async with httpx.AsyncClient(transport=httpx.MockTransport(forbidden), trust_env=False) as http:
        client = ArivaProbeClient(http, CREDENTIALS)
        for isins in ((), (ISIN, ISIN), ("*",), ("?",), ("../sources",), (ISIN,) * 65):
            with pytest.raises(ArivaProbeError):
                await client.marketstates(isins)
        with pytest.raises(ArivaProbeError, match="ARIVA_ISIN_INVALID"):
            await client.listings("*")
    for secret in ("", "has\nnewline"):
        with pytest.raises(ArivaProbeError, match="ARIVA_CREDENTIALS_INVALID"):
            ArivaCredentials(SecretStr("synthetic-id"), SecretStr(secret))


@pytest.mark.asyncio
@pytest.mark.parametrize("as_key", [False, True])
async def test_json_escaped_token_echo_is_not_saved(as_key: bool) -> None:
    escaped = "".join(f"\\u{ord(character):04x}" for character in TOKEN)
    body = ('{"' + escaped + '":1}' if as_key else '{"nested":["' + escaped + '"]}').encode()
    assert TOKEN.encode() not in body

    def handle(request: httpx.Request) -> httpx.Response:
        if str(request.url) == TOKEN_URL:
            return httpx.Response(200, json={"access_token": TOKEN, "token_type": "Bearer"})
        return httpx.Response(200, content=body, headers={"content-type": "application/json"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle), trust_env=False) as http:
        with pytest.raises(ArivaProbeError, match=r"^ARIVA_SECRET_IN_RESPONSE$"):
            await ArivaProbeClient(http, CREDENTIALS).source()


@pytest.mark.asyncio
async def test_parallel_source_reads_share_only_one_authentication_request() -> None:
    count = 0

    async def handle(request: httpx.Request) -> httpx.Response:
        nonlocal count
        if str(request.url) == TOKEN_URL:
            count += 1
            await asyncio.sleep(0)
            return httpx.Response(200, json={"access_token": TOKEN, "token_type": "Bearer"})
        return httpx.Response(200, json={"sourceId": "XSC"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle), trust_env=False) as http:
        client = ArivaProbeClient(http, CREDENTIALS)
        await asyncio.gather(client.source(), client.source())
    assert count == 1


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [(900, None), (901, "OLDER_THAN_900"), (-1, "TIME_FUTURE")],
)
def test_exact_bid_age_at_capture_has_no_effect_on_missing_status_time(
    seconds: int, expected: str | None
) -> None:
    result = inspect(
        [row(bid={"value": 2, "datetime": (NOW - timedelta(seconds=seconds)).isoformat()})]
    )
    value = result["rows"][0]
    assert value["bid_age_seconds_at_capture"] == seconds
    if expected:
        assert any(expected in reason for reason in value["bid_limitations"])
    else:
        assert value["bid_limitations"] == []
    assert not result["b58_qualified"]
    assert value["status_original_time"] is None


@pytest.mark.parametrize(
    "quote",
    [None, {"value": 2, "date": "2026-11-17"}, {"value": 2, "datetime": "2026-11-17T10:00:00"}],
)
def test_ask_last_http_time_and_date_only_never_replace_original_bid_time(
    quote: dict | None,
) -> None:
    result = inspect(
        [row(bid=quote, ask={"value": 2, "datetime": NOW.isoformat()}, last={"value": 2})]
    )
    assert "ORIGINAL_BID_TIME_MISSING_OR_INVALID" in result["rows"][0]["bid_limitations"]
    assert result["rows"][0]["bid_age_seconds_at_capture"] is None
    assert not result["b58_qualified"]


def test_price_less_status_unknown_time_field_and_conflicting_rows_are_retained() -> None:
    result = inspect(
        [
            row(),
            row(bid=None, status={"secTradingStatus": 7, "datetime": NOW.isoformat()}),
        ]
    )
    assert len(result["rows"]) == 2
    negative = result["rows"][1]
    assert negative["bid"] is None
    assert negative["status_present"]
    assert negative["status_fields"] == ["datetime", "secTradingStatus"]
    assert negative["status_original_time"] is None
    assert result["multiple_rows_requiring_listing_review"] == [ISIN]
    assert not result["b58_qualified"]


def test_source_currency_quality_identity_and_variant_are_not_silently_repaired() -> None:
    result = inspect(
        [row(sourceId="FRA", currency=None, quality="DELAYED", listingVariant=None, status=None)],
        source={"sourceId": "FRA", "operatingMic": "XFRA"},
    )
    assert result["missing_isins"] == [ISIN]
    assert result["delivered_isins"] == []
    assert not result["source_id_matches"]
    reasons = result["rows"][0]["limitations"]
    for expected in (
        "INSTRUMENT_OR_SOURCE_MISMATCH",
        "REALTIME_QUALITY_NOT_DELIVERED",
        "CURRENCY_MISSING_OR_INVALID",
        "LISTING_IDENTITY_REQUIRES_CLARIFICATION",
        "INSTRUMENT_STATUS_NOT_DELIVERED",
    ):
        assert expected in reasons


def test_actual_listing_metadata_is_reported_without_qualifying_provider_or_saved_binding() -> None:
    listing = captured({"items": [row(segmentMic="XFRA", licensedQuality="REALTIME")]})
    result = inspect([row()], listings=(listing,))
    assert result["rows"][0]["listing_segment_mic"] == "XFRA"
    assert (
        "LISTING_METADATA_MISSING_AMBIGUOUS_OR_NOT_REALTIME" not in result["rows"][0]["limitations"]
    )
    assert result["delivered_isins"] == [ISIN]
    assert not result["listing_binding_verified"]
    assert not result["b58_qualified"]


def test_documented_isin_alias_is_preserved_and_compared_without_manual_rebinding() -> None:
    listing = captured({"items": [row(segmentMic="XFRA", licensedQuality="REALTIME")]})
    result = inspect(
        [row(instrumentId=f"ISIN({ISIN})", marketstateId=f"ISIN({ISIN}),EUR@XSC")],
        listings=(listing,),
    )
    assert result["delivered_isins"] == [ISIN]
    assert result["rows"][0]["instrument_id"] == f"ISIN({ISIN})"
    assert result["rows"][0]["listing_segment_mic"] == "XFRA"
    assert "LISTING_IDENTITY_REQUIRES_CLARIFICATION" not in result["rows"][0]["limitations"]
    assert not result["b58_qualified"]


@pytest.mark.parametrize("bad", [{}, {"items": None}, {"items": [1]}, {"items": [{}] * 1025}])
def test_unknown_response_shape_is_not_an_empty_success(bad: dict) -> None:
    with pytest.raises(ArivaProbeError, match="ARIVA_MARKETSTATES_SHAPE_INVALID"):
        inspect_marketstates(captured(bad), isins=(ISIN,), source=captured({}))
    with pytest.raises(ArivaProbeError, match="ARIVA_LISTINGS_SHAPE_INVALID"):
        inspect([row()], listings=(captured(bad),))
