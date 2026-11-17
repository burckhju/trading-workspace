"""Synthetic acquisition proves isolation, exact targets and honest source limits."""

import hashlib
import io
import json
import stat
from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest

from app.features.market.contracts import is_canonical_isin
from app.tools import probe_ariva_b58
from app.tools.probe_ariva_b58 import (
    COVERAGE_PATH,
    MAX_RESPONSE_BYTES,
    ProbeInputError,
    ProbeOptions,
    main,
    run_probe,
)

NOW = datetime(2026, 11, 17, 12, 0, tzinfo=UTC)
FIRST = "DE0007100000"
SECOND = "DE000BASF111"
ENV = {
    "ARIVA_MDS_CLIENT_ID": "SYNTHETIC_ARIVA_CLIENT",
    "ARIVA_MDS_CLIENT_SECRET": "SYNTHETIC_ARIVA_SECRET",
}
TOKEN = "SYNTHETIC_ACCESS_TOKEN"


def coverage(*isins):
    items = []
    for index, isin in enumerate(isins):
        items.append(
            {
                "position_id": str(uuid4()),
                "trade_id": str(uuid4()),
                "warrant_id": str(uuid4()),
                "name": "Synthetic held instrument",
                "isin": isin,
                "wkn": None,
                "selection_id": str(uuid4()),
                "selection_status": "SELECTED",
                "selection_reason": "UNIQUE_VERIFIED_ROUTE",
                "policy_version": "SYNTHETIC_EXISTING_POLICY",
                "selected_at": NOW.isoformat(),
                "selected_provider": "GETTEX_DELAYED" if index else "FRANKFURT_QUOTES",
                "warrant_listing_id": str(uuid4()),
                "mapping_id": str(uuid4()),
                "provider_exchange_code": "MUND" if index else "XSC",
                "mic": "XMUN" if index else "XFRA",
                "currency": "EUR",
                "mapping_status": "ACTIVE",
                "mapping_version": 2,
                "identity_valid": True,
                "source_verified": True,
                "source_health": "MISSING_QUOTE",
                "candidate_product_coverage": "NO_VERIFIED_OBSERVATION",
            }
        )
    summary = dict.fromkeys(
        (
            "legacy_unbound",
            "fresh_quote",
            "last_available",
            "retained_after_refresh_error",
            "stale",
            "reference_only",
            "missing_source",
            "source_disabled",
            "mapping_conflict",
            "ambiguous_source",
            "invalid_quote",
        ),
        0,
    )
    summary.update(
        open_positions=len(items),
        bound_positions=len(items),
        source_verified=len(items),
        missing_quote=len(items),
    )
    return {
        "assessed_at": NOW.isoformat(),
        "configured_sources": ["FRANKFURT_QUOTES", "GETTEX_DELAYED"],
        "source_order": ["FRANKFURT_QUOTES", "GETTEX_DELAYED"],
        "summary": summary,
        "items": items,
        "assessment_scope": "STORED_OBSERVATIONS_NOT_LIVE_VALUATION",
        "execution_usable": False,
    }


def json_response(payload):
    return httpx.Response(200, json=payload)


def token_response():
    return json_response({"access_token": TOKEN, "token_type": "Bearer"})


def source_response():
    return json_response({"sourceId": "XSC", "operatingMic": "XFRA", "name": "Synthetic Börse"})


def state(isin, variant="EUR"):
    return {
        "instrumentId": isin,
        "sourceId": "XSC",
        "marketstateId": f"{isin},{variant}@XSC",
        "listingVariant": variant,
        "currency": "EUR",
        "quality": "REALTIME",
        "bid": {"value": 1.25, "datetime": NOW.isoformat()},
        "status": {"tradingPhase": 1},
    }


def listing(isin):
    return {
        "instrumentId": isin,
        "sourceId": "XSC",
        "listingVariant": "EUR",
        "currency": "EUR",
        "segmentMic": "XFRA",
        "licensedQuality": "REALTIME",
    }


def no_provider(_request):
    raise AssertionError("No provider request is permitted in this synthetic case")


async def execute(tmp_path, payload, *, fetch=False, provider=no_provider, environ=None):
    backend_calls = []

    def backend(request):
        backend_calls.append(request)
        assert request.method == "GET" and request.url.path == COVERAGE_PATH
        assert request.headers.get("authorization") == ""
        return json_response(payload)

    async with (
        httpx.AsyncClient(transport=httpx.MockTransport(backend)) as local,
        httpx.AsyncClient(transport=httpx.MockTransport(provider)) as remote,
    ):
        result = await run_probe(
            ProbeOptions(fetch=fetch, output=tmp_path / "private-report.json"),
            backend_http=local,
            provider_http=remote,
            environ={} if environ is None else environ,
            clock=lambda: NOW,
        )
    assert len(backend_calls) == 1
    return result


async def test_plan_reuses_all_bindings_deduplicates_and_does_not_read_credentials(tmp_path):
    class UnreadableEnvironment(dict):
        def get(self, *_args):
            raise AssertionError("Plan mode must not inspect credentials")

    payload = coverage(FIRST, SECOND, FIRST, None)
    path, report, code = await execute(tmp_path, payload, environ=UnreadableEnvironment())

    assert code == 0
    assert report["status"] == "PLAN_PREPARED_NO_PROVIDER_REQUEST"
    assert report["provider_access_attempted"] is False
    assert report["b58_qualified"] is False
    assert report["plan"]["isins"] == sorted([FIRST, SECOND])
    bindings = report["plan"]["positions"]
    assert len(bindings) == 4
    assert bindings[0]["listing_id"] == payload["items"][0]["warrant_listing_id"]
    assert bindings[1]["selected_provider"] == "GETTEX_DELAYED"
    assert bindings[1]["mic"] == "XMUN"
    assert bindings[-1]["target_status"] == "ISIN_MISSING_OR_INVALID"
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert json.loads(path.read_text()) == report
    assert report["snapshot_scope"] == "SEPARATE_REQUEST_CAPTURES_NOT_ONE_ATOMIC_SNAPSHOT"


@pytest.mark.parametrize("environ", [{}, {"ARIVA_MDS_CLIENT_ID": "synthetic"}])
async def test_fetch_without_complete_explicit_credentials_has_zero_external_calls(
    tmp_path, environ
):
    path, report, code = await execute(tmp_path, coverage(FIRST), fetch=True, environ=environ)
    assert code == 2
    assert report["reason"] == "ARIVA_EVALUATION_CREDENTIALS_MISSING"
    assert report["provider_access_attempted"] is False
    assert all(secret not in path.read_text() for secret in ENV.values())


async def test_live_probe_retains_originals_and_listing_context_without_qualifying(
    tmp_path, monkeypatch
):
    def forbidden_database(*_args, **_kwargs):
        raise AssertionError("The acquisition CLI must not create a database connection")

    monkeypatch.setattr("app.database.DatabaseManager.__init__", forbidden_database)
    calls = []
    raw_market = json.dumps(
        {"items": [state(FIRST), state(FIRST, "ALT"), state(SECOND)]},
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode()

    def provider(request):
        calls.append(request)
        assert "client_secret" not in str(request.url)
        if request.url.path.endswith("/token"):
            assert request.method == "POST"
            assert request.headers["authorization"].startswith("Basic ")
            assert request.content == b"grant_type=client_credentials"
            return token_response()
        assert request.method == "GET"
        assert request.headers["authorization"] == f"Bearer {TOKEN}"
        if request.url.path.endswith("/sources/XSC"):
            return source_response()
        if request.url.path.endswith("/marketstates/"):
            assert request.url.params.get_list("marketstateQuery") == [
                f"{isin}@XSC" for isin in sorted([FIRST, SECOND])
            ]
            assert request.url.params["quality"] == "REALTIME"
            return httpx.Response(
                200, content=raw_market, headers={"Content-Type": "application/json"}
            )
        assert request.url.path.endswith("/listings")
        assert request.url.params["sourceId"] == "XSC"
        isin = request.url.path.split("/")[-2]
        return json_response({"items": [listing(isin)]})

    path, report, code = await execute(
        tmp_path, coverage(FIRST, FIRST, SECOND), fetch=True, provider=provider, environ=ENV
    )

    assert code == 2 and report["status"] == "B58_UNQUALIFIED"
    assert report["b58_qualified"] is report["listing_binding_verified"] is False
    assert report["production_activation_changed"] is False
    assert report["application_state_read_only"] is True
    assert report["requested_acquisition_complete"] is True
    assert len(calls) == 5  # One token, one source, one batch, two distinct listing reads.
    assert report["marketstates_original"]["raw_text"].encode() == raw_market
    assert report["marketstates_original"]["sha256"] == hashlib.sha256(raw_market).hexdigest()
    assert len(report["findings"]["rows"]) == 3  # Do not select or discard a variant.
    assert len(report["listing_originals"]) == 2
    assert all(row["status"] == "CAPTURED" for row in report["listing_requests"])
    text = path.read_text()
    assert all(secret not in text for secret in [*ENV.values(), TOKEN])


@pytest.mark.parametrize("status", [401, 403, 429, 503])
async def test_source_access_failure_stops_without_leaking_error_body(tmp_path, status):
    calls = []

    def provider(request):
        calls.append(request)
        if request.url.path.endswith("/token"):
            return token_response()
        return httpx.Response(status, text=ENV["ARIVA_MDS_CLIENT_SECRET"])

    path, report, code = await execute(
        tmp_path, coverage(FIRST, SECOND), fetch=True, provider=provider, environ=ENV
    )
    assert code == 2 and report["status"] == "PROBE_INCOMPLETE"
    assert report["http_status"] == status
    assert len(calls) == 2
    assert "marketstates_original" not in report
    assert all(secret not in path.read_text() for secret in [*ENV.values(), TOKEN])


@pytest.mark.parametrize("status", [403, 429, 503, "transport"])
async def test_listing_source_failure_preserves_prior_evidence_and_marks_unrequested(
    tmp_path, status
):
    listing_calls = []

    def provider(request):
        if request.url.path.endswith("/token"):
            return token_response()
        if request.url.path.endswith("/sources/XSC"):
            return source_response()
        if request.url.path.endswith("/marketstates/"):
            return json_response({"items": [state(FIRST), state(SECOND)]})
        listing_calls.append(request)
        if status == "transport":
            raise httpx.ReadError("PRIVATE_PROVIDER_ERROR", request=request)
        return httpx.Response(status, text="PRIVATE_PROVIDER_ERROR")

    path, report, code = await execute(
        tmp_path, coverage(FIRST, SECOND), fetch=True, provider=provider, environ=ENV
    )
    assert code == 2
    assert len(listing_calls) == 1
    assert [row["status"] for row in report["listing_requests"]] == [
        "FAILED",
        "NOT_REQUESTED_AFTER_SOURCE_FAILURE",
    ]
    assert "marketstates_original" in report
    assert report["requested_acquisition_complete"] is False
    assert "PRIVATE_PROVIDER_ERROR" not in path.read_text()


async def test_one_missing_listing_does_not_hide_another_delivered_instrument(tmp_path):
    listing_calls = []

    def provider(request):
        if request.url.path.endswith("/token"):
            return token_response()
        if request.url.path.endswith("/sources/XSC"):
            return source_response()
        if request.url.path.endswith("/marketstates/"):
            return json_response({"items": [state(FIRST), state(SECOND)]})
        listing_calls.append(request)
        if len(listing_calls) == 1:
            return httpx.Response(404, text="NO_LISTING")
        return json_response({"items": [listing(SECOND)]})

    _, report, code = await execute(
        tmp_path, coverage(FIRST, SECOND), fetch=True, provider=provider, environ=ENV
    )
    assert code == 2
    assert len(listing_calls) == 2
    assert [row["status"] for row in report["listing_requests"]] == ["FAILED", "CAPTURED"]
    assert report["listing_originals"][0]["isin"] == SECOND
    assert report["requested_acquisition_complete"] is False


async def test_missing_marketstate_is_not_guessed_or_probed_for_listing(tmp_path):
    calls = []

    def provider(request):
        calls.append(request)
        if request.url.path.endswith("/token"):
            return token_response()
        if request.url.path.endswith("/sources/XSC"):
            return source_response()
        if request.url.path.endswith("/marketstates/"):
            return json_response({"items": [state(FIRST)]})
        assert request.url.path.endswith(f"/{FIRST}/listings")
        return httpx.Response(404, text="NO_LISTING")

    _, report, code = await execute(
        tmp_path, coverage(FIRST, SECOND), fetch=True, provider=provider, environ=ENV
    )
    assert code == 2
    assert len(calls) == 4
    assert report["findings"]["missing_isins"] == [SECOND]
    assert report["listing_requests"][1]["status"] == "NOT_REQUESTED_NO_MATCHING_MARKETSTATE"


@pytest.mark.parametrize(
    "url",
    [
        "https://mds.ariva-services.de",
        "http://example.test",
        "http://127.0.0.1.example.test",
        "http://user:PRIVATE@127.0.0.1:8000",
        "http://127.0.0.1:8000?token=PRIVATE",
        "http://127.0.0.1:8000/refresh/run",
        "http://127.0.0.1:8000#PRIVATE",
        "http://127.0.0.1:0",
    ],
)
async def test_non_loopback_or_credential_bearing_backend_url_rejected_before_io(tmp_path, url):
    async with httpx.AsyncClient(transport=httpx.MockTransport(no_provider)) as http:
        with pytest.raises(ProbeInputError, match=r"^LOCAL_API_URL_INVALID$"):
            await run_probe(
                ProbeOptions(api_url=url, output=tmp_path / "never-created.json"),
                backend_http=http,
                provider_http=http,
            )
    assert not (tmp_path / "never-created.json").exists()


@pytest.mark.parametrize("link", [False, True])
async def test_existing_report_or_symlink_never_overwritten_and_never_starts_requests(
    tmp_path, link
):
    original = tmp_path / "original.json"
    original.write_text("UNCHANGED_SYNTHETIC_REPORT")
    destination = tmp_path / "output.json" if link else original
    if link:
        destination.symlink_to(original)
    async with httpx.AsyncClient(transport=httpx.MockTransport(no_provider)) as http:
        with pytest.raises(ProbeInputError, match=r"^REPORT_ALREADY_EXISTS$"):
            await run_probe(
                ProbeOptions(fetch=True, output=destination), backend_http=http, provider_http=http
            )
    assert original.read_text() == "UNCHANGED_SYNTHETIC_REPORT"


async def test_default_private_report_uses_temporary_directory(tmp_path, monkeypatch):
    monkeypatch.setattr("app.tools.probe_ariva_b58.tempfile.tempdir", str(tmp_path))
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _request: json_response(coverage(FIRST)))
    ) as http:
        path, _, code = await run_probe(
            ProbeOptions(), backend_http=http, environ={}, clock=lambda: NOW
        )
    assert code == 0
    assert path.parent == tmp_path
    assert path.name.startswith("trading-workspace-ariva-b58-20261117T120000Z-")
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


@pytest.mark.parametrize(
    "body", [b'{"wrong":true}', b"x" * (MAX_RESPONSE_BYTES + 1)], ids=["invalid", "oversized"]
)
async def test_invalid_or_oversized_local_coverage_never_reaches_provider(tmp_path, body):
    async with (
        httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda _request: httpx.Response(
                    200, content=body, headers={"Content-Type": "application/json"}
                )
            )
        ) as local,
        httpx.AsyncClient(transport=httpx.MockTransport(no_provider)) as remote,
    ):
        _, report, code = await run_probe(
            ProbeOptions(fetch=True, output=tmp_path / "private.json"),
            backend_http=local,
            provider_http=remote,
            environ=ENV,
        )
    assert code == 2
    assert report["provider_access_attempted"] is False
    assert report["reason"] in {
        "LOCAL_COVERAGE_PAYLOAD_INVALID",
        "LOCAL_COVERAGE_RESPONSE_TOO_LARGE",
    }


async def test_more_than_64_distinct_isins_is_not_silently_truncated(tmp_path):
    isins = []
    for index in range(65):
        prefix = f"DE{index:09d}"
        isins.append(next(prefix + str(d) for d in range(10) if is_canonical_isin(prefix + str(d))))
    _, report, code = await execute(tmp_path, coverage(*isins), fetch=True, environ=ENV)
    assert code == 2
    assert report["reason"] == "ARIVA_TARGET_LIMIT_EXCEEDED_NO_PARTIAL_FETCH"
    assert report["plan"]["unique_isins"] == 65
    assert report["provider_access_attempted"] is False


def test_cli_rejects_secret_arguments_without_echoing_them(capsys):
    assert main(["--client-secret", "SYNTHETIC_SECRET_DO_NOT_ECHO"]) == 2
    captured = capsys.readouterr()
    assert "SYNTHETIC_SECRET_DO_NOT_ECHO" not in captured.out + captured.err
    assert json.loads(captured.out)["status"] == "PROBE_NOT_STARTED"


def test_report_write_failure_after_requests_does_not_claim_probe_never_started(
    tmp_path, monkeypatch, capsys
):
    calls = []

    class FailingReport(io.StringIO):
        def write(self, _value):
            raise OSError("SYNTHETIC_DISK_FAILURE")

    def provider(request):
        calls.append(request)
        if request.url.path.endswith("/token"):
            return token_response()
        if request.url.path.endswith("/sources/XSC"):
            return source_response()
        if request.url.path.endswith("/marketstates/"):
            return json_response({"items": [state(FIRST)]})
        return json_response({"items": [listing(FIRST)]})

    async def synthetic_run(options):
        async with (
            httpx.AsyncClient(
                transport=httpx.MockTransport(lambda _request: json_response(coverage(FIRST)))
            ) as local,
            httpx.AsyncClient(transport=httpx.MockTransport(provider)) as remote,
        ):
            return await run_probe(
                options, backend_http=local, provider_http=remote, environ=ENV, clock=lambda: NOW
            )

    monkeypatch.setattr(probe_ariva_b58, "run_probe", synthetic_run)
    monkeypatch.setattr(
        probe_ariva_b58,
        "_reserve_report",
        lambda _path, _now: (tmp_path / "synthetic-unwritable.json", FailingReport()),
    )
    assert main(["--fetch"]) == 2
    output = json.loads(capsys.readouterr().out)
    # Real code reached all mocked acquisition requests before the I/O error.
    assert len(calls) == 4
    assert output["status"] == "REPORT_OR_IO_FAILED"
    assert output["provider_access_attempted"] == "UNKNOWN"
    assert output["b58_qualified"] is False
