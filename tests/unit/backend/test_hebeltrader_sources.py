"""No speculative user inputs; source axes and current-entry gating stay separate."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql

from app.features.learning.persistence.models import ExternalObservationVersionModel
from app.features.trade_plan.api.hebeltrader_sources import (
    WORKSPACE_ID,
    SourceReader,
    get_source_reader,
    router,
    source_axis,
    source_snapshot,
)

UNDERLYING = UUID("00000000-0000-4000-8000-000000000010")
SOURCE = UUID("00000000-0000-4000-8000-000000000011")


def payload():
    return {
        "underlying_name": "Beispielaktie",
        "issue_date": datetime.now(UTC).date().isoformat(),
        "underlying_currency": "USD",
        "underlying_price": "100",
        "underlying_stop_1": "90",
        "underlying_target_1": "120",
        "underlying_target_2": "145",
        "gd200": "95",
        "gd50": "98",
        "derivative_currency": "EUR",
        "derivative_indicated_price": "0.16",
        "derivative_stop_1": "0.07",
        "derivative_target_1": "0.71",
        "derivative_target_2": "2.12",
        "source_file": {"filename": "example.pdf", "content_hash": "a" * 64},
        "validation_issues": [],
    }


def version(data=None):
    return ExternalObservationVersionModel(
        id=SOURCE,
        underlying_id=UNDERLYING,
        external_reference="1/2026",
        source_metadata=payload() if data is None else data,
    )


@pytest.fixture
def api():
    reader = SimpleNamespace(versions=AsyncMock(return_value=[version()]))
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_source_reader] = lambda: reader
    with TestClient(app) as client:
        yield client, reader


def source_body(**changes):
    return {"underlying_id": str(UNDERLYING), "source_version_id": str(SOURCE), **changes}


def quote(**changes):
    return {
        "bid": "100",
        "ask": "101",
        "observed_at": datetime.now(UTC).isoformat(),
        "currency": "USD",
        "source": "Displayed exchange quote",
        **changes,
    }


def test_snapshot_preserves_source_and_separates_price_axes():
    result = source_snapshot(version())
    assert result.filename == "example.pdf"
    assert result.content_hash == "a" * 64
    assert result.stock.currency == "USD"
    assert result.warrant.currency == "EUR"
    assert result.stock.reward_risk == "3.25"
    assert result.stock.band_deviation == "0"
    assert result.stock.values["entry"] == "100"
    assert result.scope == "PUBLISHED_SNAPSHOT_NOT_LIVE"
    assert not result.source_issues
    assert float(result.warrant.reward_risk) == pytest.approx(13.9444444)


@pytest.mark.parametrize("value", [None, "", "NaN", "sNaN", "Infinity", "-1", "0", True, {}, "bad"])
def test_missing_or_invalid_source_never_receives_a_default(value):
    data = payload()
    data["underlying_stop_1"] = value
    result = source_axis(data, stock=True)
    assert result.values["stop"] is None
    assert result.reward_risk is None
    assert result.issues


def test_missing_gd_does_not_suppress_observable_crv():
    data = payload()
    del data["gd200"]
    result = source_axis(data, stock=True)
    assert result.reward_risk == "3.25"
    assert result.band_deviation is None
    assert result.values["gd200"] is None


def test_contradictory_levels_are_displayed_but_not_repaired():
    data = payload()
    data["underlying_stop_1"] = "170"
    result = source_axis(data, stock=True)
    assert result.values["stop"] == "170"
    assert result.reward_risk is None
    assert any("Widersprüchliche" in issue for issue in result.issues)


@pytest.mark.parametrize("currency", [None, "usd", "U1D", "EURO", "", "€"])
def test_unknown_currency_is_not_assumed_to_be_eur(currency):
    data = payload()
    data["underlying_currency"] = currency
    assert source_axis(data, stock=True).currency is None


def test_minor_units_are_converted_consistently_and_explained():
    data = payload()
    data["underlying_currency"] = "GBp"
    result = source_axis(data, stock=True)
    assert result.currency == "GBP"
    assert result.values["entry"] == "1.00"
    assert result.values["gd200"] == "0.95"
    assert result.reward_risk == "3.25"
    assert any("durch 100" in issue for issue in result.issues)
    assert data["underlying_price"] == "100"


def test_inconsistent_band_reports_review_not_synthetic_targets():
    data = payload()
    data["underlying_target_2"] = "200"
    result = source_axis(data, stock=True)
    assert result.values["target2"] == "200"
    assert any("Zielstaffelung" in issue for issue in result.issues)


def test_metadata_warnings_do_not_disclose_or_require_full_pdf_text():
    data = payload()
    data.update(issue_date="bad", source_file={}, validation_issues=[{"code": "TEST"}])
    data["raw_text"] = "PRIVATE ARTICLE TEXT"
    result = source_snapshot(version(data))
    assert len(result.source_issues) == 3
    assert result.issue_date is None
    assert "PRIVATE ARTICLE TEXT" not in result.model_dump_json()


def test_sources_need_only_underlying_identity(api):
    client, reader = api
    response = client.get(
        "/api/v1/trade-plans/strategies/hebeltrader/sources",
        params={"underlying_id": str(UNDERLYING)},
    )
    assert response.status_code == 200
    assert response.json()["items"][0]["stock"]["reward_risk"] == "3.25"
    assert response.json()["has_more"] is False
    reader.versions.assert_awaited_once_with(UNDERLYING, offset=0)


def test_sources_pagination_is_explicit(api):
    client, reader = api
    reader.versions.return_value = [version()] * 51
    data = client.get(
        "/api/v1/trade-plans/strategies/hebeltrader/sources",
        params={"underlying_id": str(UNDERLYING), "offset": 50},
    ).json()
    assert len(data["items"]) == 50
    assert data["next_offset"] == 100
    assert data["has_more"] is True


def test_source_only_review_requires_no_market_or_model_inputs(api):
    client, _ = api
    response = client.post(
        "/api/v1/trade-plans/strategies/hebeltrader/source-preview", json=source_body()
    )
    assert response.status_code == 200
    data = response.json()
    assert data["source"]["stock"]["reward_risk"] == "3.25"
    assert data["current_preview"] is None
    assert data["execution_enabled"] is False
    assert any("Kein aktueller" in message for message in data["missing_data"])


def test_unknown_history_is_not_silently_treated_as_no_target_hit(api):
    client, _ = api
    data = client.post(
        "/api/v1/trade-plans/strategies/hebeltrader/source-preview",
        json=source_body(quote=quote(), fundamental_ok=True),
    ).json()
    assert data["current_preview"] is None
    assert any("Zielhistorie" in message for message in data["missing_data"])


def test_current_review_uses_only_selected_source_levels(api):
    client, _ = api
    response = client.post(
        "/api/v1/trade-plans/strategies/hebeltrader/source-preview",
        json=source_body(quote=quote(), fundamental_ok=True, target_history="NOT_REACHED"),
    )
    assert response.status_code == 200
    data = response.json()["current_preview"]
    assert data["mode"] == "PUBLISHED_LEVELS_REVIEW"
    assert data["assessment"]["eligible"] is True
    assert data["trade_plan_content"]["entry"]["price"] == "101"
    assert data["trade_plan_content"]["invalidation"]["stop_price"] == "90"
    assert str(SOURCE) in data["trade_plan_content"]["thesis"]


def test_older_source_cannot_be_made_current_by_a_fresh_quote(api):
    client, reader = api
    data = payload()
    data["issue_date"] = "2020-01-01"
    reader.versions.return_value = [version(data)]
    response = client.post(
        "/api/v1/trade-plans/strategies/hebeltrader/source-preview",
        json=source_body(quote=quote(), fundamental_ok=True, target_history="NOT_REACHED"),
    ).json()
    assert response["current_preview"]["trade_plan_content"] is None
    assert "ANALYSIS_OLDER_THAN_7_DAYS" in response["current_preview"]["assessment"]["reasons"]


@pytest.mark.parametrize("key", ["band_width", "buffer_fraction", "gd200", "tick", "as_of"])
def test_source_path_rejects_fabricated_model_and_source_overrides(api, key):
    client, _ = api
    response = client.post(
        "/api/v1/trade-plans/strategies/hebeltrader/source-preview",
        json=source_body(**{key: "123"}),
    )
    assert response.status_code == 422


def test_foreign_or_unavailable_source_is_not_read(api):
    client, reader = api
    reader.versions.return_value = []
    response = client.post(
        "/api/v1/trade-plans/strategies/hebeltrader/source-preview", json=source_body()
    )
    assert response.status_code == 404
    reader.versions.assert_awaited_once_with(UNDERLYING, version_id=SOURCE)


def test_wrong_currency_rejected(api):
    client, _ = api
    response = client.post(
        "/api/v1/trade-plans/strategies/hebeltrader/source-preview",
        json=source_body(quote=quote(currency="EUR")),
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_reader_scopes_workspace_underlying_source_and_current_version():
    session = MagicMock()
    session.scalars = AsyncMock(return_value=[])
    reader = SourceReader(session)
    assert await reader.versions(UNDERLYING, version_id=SOURCE) == []
    query = session.scalars.call_args.args[0]
    compiled = str(
        query.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})
    )
    for expected in (
        str(WORKSPACE_ID), str(UNDERLYING), str(SOURCE), "HEBELTRADER", "FILE_IMPORT"
    ):
        assert expected in compiled
    assert "current_version_id" in compiled
    assert "LIMIT 51" in compiled
    session.commit.assert_not_called()
