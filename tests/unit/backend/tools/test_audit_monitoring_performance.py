"""Operational diagnostics cover the current catalogue, including newly found routes."""

from copy import deepcopy

import httpx
import pytest

from app.tools import audit_monitoring_performance as audit

NOW = "2026-10-02T12:00:00+00:00"
ISIN = "SYNTHETIC-NEW-ISSUER"


def evidence():
    monitoring = {
        "enabled": True,
        "running": True,
        "last_cycle_completed_at": NOW,
        "last_rule_checks": [
            {
                "isin": ISIN,
                "instrument_id": "new-instrument",
                "position_id": "new-position",
                "provider": "JPMORGAN",
                "status": "INDICATIVE",
            }
        ],
    }
    refresh = {
        "enabled": True,
        "leader": True,
        "last_scan_at": NOW,
        "jobs": [
            {
                "job": "ISSUER_QUOTES:new-instrument",
                "isin": ISIN,
                "instrument_id": "new-instrument",
                "lane": "ISSUER_QUOTES",
                "status": "AVAILABLE",
                "checked_at": NOW,
                "quotes": [
                    {
                        "provider": "JPMORGAN",
                        "bid": "0.125",
                        "retrieved_at": NOW,
                        "observed_at": None,
                        "quote_time_basis": "DATE_AND_TIMEZONE_UNKNOWN",
                    }
                ],
            }
        ],
    }
    return monitoring, refresh


@pytest.mark.parametrize("provider", ["JPMORGAN", "MORGAN_STANLEY"])
def test_new_issuer_product_is_included_without_a_historical_target_entry(provider):
    monitoring, refresh = evidence()
    monitoring["last_rule_checks"][0]["provider"] = provider
    refresh["jobs"][0]["quotes"][0]["provider"] = provider
    report = audit.summarize(monitoring, refresh)
    assert report["summary"]["issuer_refresh_jobs"] == 1
    assert report["summary"]["issuer_refresh_success_count"] == 1
    assert report["summary"]["issuer_positions_in_last_cycle"] == 1
    assert report["issuer_refresh_success_isins"] == [ISIN]
    assert report["issuer_refresh_unverified_isins"] == []
    assert report["issuer_refresh_jobs"][0]["positive_bid_evidenced"] is True
    assert report["issuer_refresh_jobs"][0]["quotes"][0]["observed_at"] is None


@pytest.mark.asyncio
async def test_unchecked_new_product_prevents_completed_wait_without_provider_requests(monkeypatch):
    monitoring, refresh = evidence()
    refresh["jobs"][0].update(status="PENDING", checked_at=None, quotes=[])
    requests = []

    def respond(request):
        requests.append((request.method, request.url.path))
        return httpx.Response(
            200, json=monitoring if "position-monitoring" in request.url.path else refresh
        )

    client = httpx.AsyncClient(
        base_url="http://127.0.0.1:8000", transport=httpx.MockTransport(respond)
    )
    monkeypatch.setattr(audit.httpx, "AsyncClient", lambda **kwargs: client)
    report = await audit.audit(0)
    assert report["wait_completed"] is False
    assert report["issuer_refresh_unverified_isins"] == [ISIN]
    assert requests == [
        ("GET", "/api/v1/position-monitoring/runtime/status"),
        ("GET", "/api/v1/market-data/refresh/status"),
    ]


def test_failed_rule_is_linked_by_instrument_but_an_explicit_exchange_provider_is_not():
    monitoring, refresh = evidence()
    failed = monitoring["last_rule_checks"][0]
    failed.pop("provider")
    failed.update(status="MISSING", reason="ISSUER_INDICATION_REFRESH_FAILED")
    exchange = dict(failed, position_id="exchange-position", provider="FRANKFURT_QUOTES")
    unrelated = dict(failed, position_id="unrelated", instrument_id="different-instrument")
    monitoring["last_rule_checks"].extend([exchange, unrelated])
    report = audit.summarize(monitoring, refresh)
    assert report["summary"]["issuer_positions_in_last_cycle"] == 1
    assert report["summary"]["issuer_rule_status_counts"] == {"MISSING": 1}


@pytest.mark.parametrize(
    "quote_change",
    [
        {"bid": None},
        {"bid": "0"},
        {"bid": "-1"},
        {"bid": "NaN"},
        {"bid": "Infinity"},
        {"retrieved_at": None},
        {"retained": True},
        {"refresh_error": "SYNTHETIC_REFRESH_FAILURE"},
        {"provider": "FRANKFURT_QUOTES"},
    ],
)
def test_available_job_does_not_prove_a_positive_unretained_issuer_bid(quote_change):
    monitoring, refresh = evidence()
    refresh["jobs"][0]["quotes"][0].update(quote_change)
    original = deepcopy(refresh)
    report = audit.summarize(monitoring, refresh)
    assert report["summary"]["issuer_refresh_success_count"] == 0
    assert report["issuer_refresh_unverified_isins"] == [ISIN]
    assert report["issuer_refresh_jobs"][0]["positive_bid_evidenced"] is False
    assert refresh == original


def test_indicative_refresh_failure_remains_visible_with_its_original_status():
    monitoring, refresh = evidence()
    row = monitoring["last_rule_checks"][0]
    row.update(provider="FRANKFURT_QUOTES", refresh_error="FRANKFURT_REQUEST_THROTTLED")
    report = audit.summarize(monitoring, refresh)
    assert report["rule_issues"] == [row]
    assert report["rule_issues"][0]["status"] == "INDICATIVE"


def test_exchange_and_discovery_jobs_do_not_inflate_issuer_quote_coverage():
    monitoring, refresh = evidence()
    for lane in ("WARRANTS", "ISSUER_DISCOVERY"):
        refresh["jobs"].append(dict(refresh["jobs"][0], lane=lane, isin="OTHER-TEST-PRODUCT"))
    report = audit.summarize(monitoring, refresh)
    assert report["summary"]["issuer_refresh_jobs"] == 1
    assert report["issuer_refresh_success_isins"] == [ISIN]


def test_failed_job_cannot_promote_embedded_quote_evidence():
    monitoring, refresh = evidence()
    refresh["jobs"][0]["status"] = "ERROR"
    report = audit.summarize(monitoring, refresh)
    assert report["summary"]["issuer_refresh_checked"] == 1
    assert report["summary"]["issuer_refresh_success_count"] == 0
    assert report["issuer_refresh_unverified_isins"] == [ISIN]
