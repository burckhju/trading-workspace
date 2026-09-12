import httpx
import pytest

from app.providers.frankfurt_quotes.client import FrankfurtSnapshotClient
from app.providers.frankfurt_quotes.schema import FrankfurtSourceError
from tests.unit.backend.providers.frankfurt_quotes.test_client import settings
from tests.unit.backend.providers.frankfurt_quotes.test_schema import NOW, payload


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error,reason",
    [
        (httpx.ReadTimeout("secret upstream details"), "FRANKFURT_TRANSPORT_TIMEOUT"),
        (httpx.ConnectError("secret upstream details"), "FRANKFURT_TRANSPORT_ERROR"),
    ],
)
async def test_transport_exception_is_redacted(error, reason):
    def handler(request):
        raise error

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = FrankfurtSnapshotClient(settings(), client=http)
        with pytest.raises(FrankfurtSourceError, match=f"^{reason}$"):
            await client.load()
        assert client.last_error == reason


@pytest.mark.asyncio
async def test_declared_delay_must_match_configured_entitlement():
    data = payload()
    data["delay_seconds"] = 900
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=data))
    ) as http:
        with pytest.raises(FrankfurtSourceError, match="FEED_DELAY_MISMATCH"):
            await FrankfurtSnapshotClient(settings(), client=http).load()
        client = FrankfurtSnapshotClient(
            settings(feed_delay_seconds=900), client=http, clock=lambda: NOW
        )
        assert (await client.load())[0].delay_seconds == 900


@pytest.mark.asyncio
async def test_failure_does_not_resurrect_previous_success():
    elapsed = [0.0]
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=payload()) if len(calls) == 1 else httpx.Response(503)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = FrankfurtSnapshotClient(
            settings(), client=http, timer=lambda: elapsed[0], clock=lambda: NOW
        )
        await client.load()
        elapsed[0] = 16.0
        with pytest.raises(FrankfurtSourceError, match="HTTP_503"):
            await client.load()
        elapsed[0] = 17.0
        with pytest.raises(FrankfurtSourceError, match="HTTP_503"):
            await client.load()
        assert len(calls) == 2
        assert client.last_success_at == NOW
