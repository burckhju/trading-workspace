import json
from dataclasses import asdict, replace
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from tests.unit.backend.features.position_monitoring.test_cli import result
from tests.unit.backend.features.position_monitoring.test_rule_price_binding import (
    NOW,
    RULE,
    SUBJECT,
    valuation,
)

from app.features.position_monitoring import cli
from app.features.position_monitoring.api.dtos import ProductPositionValuationResponse
from app.features.position_monitoring.backend_valuations import (
    BackendProductValuations,
    backend_origin,
)
from app.features.position_monitoring.service.rule_prices import CycleProductValuations, rule_price


def payload(**kwargs):
    return ProductPositionValuationResponse.model_validate(asdict(valuation(**kwargs))).model_dump(
        mode="json"
    )


@pytest.mark.parametrize("kind", ["BID", "LAST_TRADE"])
async def test_backend_payload_keeps_provenance_and_is_shared_by_both_rules(kind):
    calls = []
    data = payload(reference_price_type=kind)

    def handler(request):
        calls.append(request)
        assert request.method == "GET"
        return httpx.Response(200, json=data)

    diagnostics = []
    async with httpx.AsyncClient(
        base_url="http://backend", transport=httpx.MockTransport(handler)
    ) as client:
        reader = CycleProductValuations(BackendProductValuations(client, diagnostics=diagnostics))
        for rule in (RULE, replace(RULE, rule_key="CURRENT_STOP")):
            checked = await rule_price(
                subject=SUBJECT,
                rule=rule,
                products=reader,
                market_data=None,
                now=NOW,
                max_age_days=4,
            )
            assert checked.observation.value == valuation().reference_price
            assert checked.observation.context["price_type"] == kind
            assert (
                checked.observation.context["observed_at"]
                == valuation().quote_observed_at.isoformat()
            )
            assert checked.observation.context["execution_usable"] == "false"
            assert (
                checked.observation.context["warning"] == "OUTDATED_QUOTE_INDICATIVE_ANALYSIS_ONLY"
            )
    assert len(calls) == len(diagnostics) == 1
    assert diagnostics[0]["trade_id"] == str(SUBJECT.trade_id)


@pytest.mark.parametrize(
    ("code", "data", "reason"),
    [
        (503, {"detail": "SECRET"}, "BACKEND_HTTP_503"),
        (302, {}, "BACKEND_HTTP_302"),
        (200, {}, "BACKEND_VALUATION_SCHEMA_INVALID"),
        (200, {"wrong": "schema"}, "BACKEND_VALUATION_SCHEMA_INVALID"),
        (200, payload(trade_id=uuid4()), "BACKEND_TRADE_IDENTITY_MISMATCH"),
    ],
)
async def test_invalid_backend_response_never_becomes_a_price(code, data, reason):
    diagnostics = []
    async with httpx.AsyncClient(
        base_url="http://backend",
        transport=httpx.MockTransport(lambda r: httpx.Response(code, json=data)),
    ) as client:
        with pytest.raises(RuntimeError, match=reason):
            await BackendProductValuations(client, diagnostics=diagnostics).for_trade(
                SUBJECT.trade_id
            )
    assert diagnostics[0]["reason"] == reason
    assert "SECRET" not in json.dumps(diagnostics)


async def test_missing_position_remains_missing():
    async with httpx.AsyncClient(
        base_url="http://backend",
        transport=httpx.MockTransport(lambda r: httpx.Response(404)),
    ) as client:
        assert await BackendProductValuations(client).for_trade(SUBJECT.trade_id) is None


@pytest.mark.parametrize("data", [{"status": "not_ready"}, [], None])
async def test_readiness_failure_prevents_a_cycle(data):
    async with httpx.AsyncClient(
        base_url="http://backend",
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=data)),
    ) as client:
        with pytest.raises(RuntimeError, match="BACKEND_NOT_READY"):
            await BackendProductValuations(client).check_ready()


async def test_transport_failure_has_bounded_diagnostic():
    def handler(request):
        raise httpx.ConnectError("SECRET", request=request)

    diagnostics = []
    async with httpx.AsyncClient(
        base_url="http://backend", transport=httpx.MockTransport(handler)
    ) as client:
        with pytest.raises(RuntimeError, match="BACKEND_NOT_READY"):
            await BackendProductValuations(client).check_ready()
        with pytest.raises(RuntimeError, match="BACKEND_TRANSPORT_ERROR"):
            await BackendProductValuations(client, diagnostics=diagnostics).for_trade(
                SUBJECT.trade_id
            )
    assert "SECRET" not in json.dumps(diagnostics)


@pytest.mark.parametrize(
    "url",
    [
        "ftp://backend",
        "http://user:secret@backend",
        "http://backend/api",
        "http://backend?token=x",
        "http://backend/#x",
        "",
    ],
)
def test_backend_origin_rejects_credentials_and_ambiguous_addresses(url):
    with pytest.raises(ValueError):
        backend_origin(url)


async def test_cli_backend_mode_uses_http_port_and_closes_resources(monkeypatch):
    container = SimpleNamespace(
        database=object(),
        eodhd=None,
        close=AsyncMock(),
    )
    monkeypatch.setattr(
        cli,
        "get_settings",
        lambda: SimpleNamespace(
            notification=SimpleNamespace(telegram=SimpleNamespace(enabled=False))
        ),
    )
    monkeypatch.setattr(cli.ApplicationContainer, "build", lambda s: container)
    monkeypatch.setattr(
        cli, "build_warrant_quote_resolver", lambda c: pytest.fail("isolated provider")
    )
    runtime = SimpleNamespace(run=AsyncMock(return_value=result()))
    selected = []

    def build_runtime(**kwargs):
        selected.append(kwargs["products"])
        return runtime

    monkeypatch.setattr(cli, "build_position_monitoring_runtime", build_runtime)
    client = httpx.AsyncClient(
        base_url="http://backend",
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"status": "ready"})),
    )
    monkeypatch.setattr(cli.httpx, "AsyncClient", lambda **kwargs: client)
    assert await cli.run_once(allow_telegram=False, backend_url="http://backend") == result()
    assert isinstance(selected[0], BackendProductValuations)
    assert client.is_closed
    container.close.assert_awaited_once()
    runtime.run.assert_awaited_once()


def test_cli_detail_output_marks_cache_context_and_exposes_missing_reasons(monkeypatch, capsys):
    async def once(**kwargs):
        kwargs["quote_diagnostics"].append({"reason": "FRANKFURT_REQUEST_THROTTLED"})
        return result()

    monkeypatch.setattr(cli, "run_once", once)
    monkeypatch.setattr(
        "sys.argv", ["monitor", "--backend-url", "http://127.0.0.1:8000", "--include-rule-checks"]
    )
    cli.main()
    output = json.loads(capsys.readouterr().out)
    assert output["quote_context"] == "RUNNING_BACKEND"
    assert output["subject_errors"] == 0
    assert output["product_valuations"][0]["reason"] == "FRANKFURT_REQUEST_THROTTLED"
    assert output["rule_checks"] == []
