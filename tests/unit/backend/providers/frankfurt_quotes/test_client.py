import asyncio
import json
from datetime import timedelta

import httpx
import pytest
from pydantic import ValidationError

from app.core.config.frankfurt import FrankfurtQuoteSettings, FrankfurtSourceMode
from app.providers.frankfurt_quotes.client import FrankfurtSnapshotClient
from app.providers.frankfurt_quotes.schema import FrankfurtSourceError, assess_snapshot
from tests.unit.backend.providers.frankfurt_quotes.test_schema import NOW, payload


def settings(**overrides):
    values = dict(
        enabled=True,
        usage_approved=True,
        contract_verified=True,
        source_name="test-vendor",
        snapshot_url="https://vendor.example/quotes",
        allowed_host="vendor.example",
    )
    values.update(overrides)
    return FrankfurtQuoteSettings(**values)


@pytest.mark.asyncio
async def test_single_flight_bulk_cache_and_actual_age_reassessment():
    calls = []
    moment = [NOW]

    async def handler(request):
        calls.append(request)
        await asyncio.sleep(0)
        return httpx.Response(200, json=payload())

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = FrankfurtSnapshotClient(settings(), client=http, clock=lambda: moment[0])
        results = await asyncio.gather(*(client.load() for _ in range(20)))
        assert len(calls) == 1
        assert sum(not result[2] for result in results) == 1
        moment[0] = NOW + timedelta(seconds=901)
        snapshot, retrieved_at, hit = await client.load()
        assert hit and retrieved_at == NOW
        observation = assess_snapshot(
            snapshot,
            isin="DE000VH2LU21",
            wkn="VH2LU2",
            currency="EUR",
            now=moment[0],
            retrieved_at=retrieved_at,
        )
        assert observation.status == "STALE"


@pytest.mark.asyncio
@pytest.mark.parametrize("code", [301, 401, 403, 404, 429, 500])
async def test_http_failures_redacted_and_backed_off(code):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            code, headers={"location": "https://other.example/secret"}, text="SECRET"
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), follow_redirects=True
    ) as http:
        client = FrankfurtSnapshotClient(settings(bearer_token="HIDDEN"), client=http)
        for _ in range(2):
            with pytest.raises(FrankfurtSourceError, match=f"^FRANKFURT_HTTP_{code}$"):
                await client.load()
        assert len(calls) == 1
        assert "HIDDEN" not in client.last_error
        assert "SECRET" not in client.last_error


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body,mime,reason",
    [
        (b"<html>not a feed</html>", "text/html", "CONTENT_TYPE_INVALID"),
        (b"{broken", "application/json", "SCHEMA_INVALID"),
        (b'{"source":"one","source":"two"}', "application/json", "SCHEMA_INVALID"),
        (b'{"x":NaN}', "application/json", "SCHEMA_INVALID"),
        (b"x" * 1025, "application/json", "PAYLOAD_TOO_LARGE"),
    ],
)
async def test_bad_payload(body, mime, reason):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, content=body, headers={"content-type": mime})
        )
    ) as http:
        client = FrankfurtSnapshotClient(settings(max_response_bytes=1024), client=http)
        with pytest.raises(FrankfurtSourceError, match=f"FRANKFURT_{reason}"):
            await client.load()


@pytest.mark.asyncio
async def test_local_file_and_source_identity(tmp_path):
    path = tmp_path / "quotes.json"
    path.write_text(json.dumps(payload()), encoding="utf-8")
    config = settings(source_mode=FrankfurtSourceMode.LOCAL_FILE, local_file=str(path))
    client = FrankfurtSnapshotClient(config, clock=lambda: NOW)
    assert (await client.load())[0].source == "test-vendor"
    config = config.model_copy(update={"source_name": "other"})
    with pytest.raises(FrankfurtSourceError, match="SOURCE_MISMATCH"):
        await FrankfurtSnapshotClient(config).load()


@pytest.mark.asyncio
async def test_missing_file(tmp_path):
    config = settings(source_mode="local_file", local_file=str(tmp_path / "missing.json"))
    with pytest.raises(FrankfurtSourceError, match="LOCAL_FILE_UNAVAILABLE"):
        await FrankfurtSnapshotClient(config).load()


@pytest.mark.asyncio
async def test_disabled_never_reads():
    with pytest.raises(FrankfurtSourceError, match="DISABLED"):
        await FrankfurtSnapshotClient(FrankfurtQuoteSettings()).load()


@pytest.mark.parametrize(
    "url",
    [
        "http://vendor.example/quotes",
        "https://user:secret@vendor.example/quotes",
        "https://vendor.example/quotes?token=secret",
        "https://vendor.example/quotes#fragment",
    ],
)
def test_unsafe_endpoint_configuration(url):
    with pytest.raises(ValidationError):
        settings(snapshot_url=url)


@pytest.mark.parametrize(
    "patch,reason",
    [
        ({"usage_approved": False}, "USAGE_NOT_APPROVED"),
        ({"contract_verified": False}, "CONTRACT_NOT_VERIFIED"),
        ({"source_name": None}, "SOURCE_NAME_MISSING"),
        ({"snapshot_url": None}, "ENDPOINT_MISSING"),
        ({"allowed_host": "other.example"}, "HOST_NOT_APPROVED"),
        ({"source_mode": "local_file", "local_file": None}, "LOCAL_FILE_MISSING"),
    ],
)
def test_explicit_readiness(patch, reason):
    assert settings(**patch).readiness_reason == f"FRANKFURT_{reason}"


def test_maximum_age_setting():
    with pytest.raises(ValidationError):
        settings(max_quote_age_seconds=901)
