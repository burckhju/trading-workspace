"""HTTP contracts against persisted evidence, without any provider runtime."""

from dataclasses import replace
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from tests.unit.backend.features.market_data.test_retained_quotes import context as context
from tests.unit.backend.features.product import test_valuation_evidence as evidence_tests
from tests.unit.backend.features.product.test_valuation_evidence import (
    facts,
)

from app.core.exceptions import register_exception_handlers
from app.database.dependencies import get_database_session
from app.features.market_data.api.quote_history import router as history_router
from app.features.product.api.valuation_evidence import WORKSPACE_ID
from app.features.product.api.valuation_evidence import router as facts_router
from app.features.product.persistence.models import WarrantModel

prepared = evidence_tests.prepared


@pytest.fixture
def client(prepared):
    c = prepared
    with Session(c.database.engine) as session:
        session.get(WarrantModel, c.warrant).workspace_id = WORKSPACE_ID
        session.commit()
    c.request = replace(c.request, workspace_id=WORKSPACE_ID)
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(facts_router, prefix="/warrants")
    app.include_router(history_router, prefix="/market-data")

    async def session_dep():
        async with c.database.session_context() as session:
            yield session

    app.dependency_overrides[get_database_session] = session_dep
    with TestClient(app) as http:
        yield http, c


def test_get_history_empty_scope_and_query_validation(client):
    http, c = client
    path = f"/market-data/warrants/{c.warrant}/quote-history"
    response = http.get(path)
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == body["segments"] == []
    assert body["time_coverage_percent"] is None
    assert not body["iv_history_available"] and not body["execution_usable"]
    assert http.get(path + "?days=32").status_code == 422
    assert http.get(f"/market-data/warrants/{uuid4()}/quote-history").status_code == 404
    c.provider.get_warrant_listing_quote.assert_not_called()


def test_document_confirmation_conflicts_and_full_unknown_revision(client):
    http, c = client
    path = f"/warrants/{c.warrant}/valuation-evidence"
    assert http.get(path).json()["status"] == "MISSING"
    body = dict(
        terms_id=str(c.terms),
        expected_version=1,
        expected_revision=0,
        facts=facts().model_dump(mode="json"),
    )
    assert http.post(path, json=body).status_code == 422
    body["confirmation"] = "CONFIRM_DOCUMENT_REVIEW"
    actor = uuid4()
    response = http.post(path, json=body, headers={"X-Actor-ID": str(actor)})
    assert response.status_code == 201, response.text
    assert response.json()["current"]["actor_id"] == str(actor)
    assert response.json()["current"]["recorded_at"].endswith("Z")
    assert http.post(path, json=body).status_code == 409
    body["expected_revision"] = 1
    body["facts"]["quanto"] = None
    revised = http.post(path, json=body)
    assert revised.status_code == 201
    assert revised.json()["current"]["facts"]["quanto"] is None
    assert revised.json()["history"][1]["facts"]["quanto"] is False
    body["expected_revision"] = 2
    body["facts"]["reviewed_at"] = "2099-01-01T00:00:00Z"
    assert http.post(path, json=body).status_code == 422
    assert http.get(f"/warrants/{uuid4()}/valuation-evidence").status_code == 404
    c.provider.get_warrant_listing_quote.assert_not_called()


def test_failed_evidence_read_not_returned_as_empty_success(client):
    http, c = client
    with patch(
        "app.features.product.api.valuation_evidence.ValuationEvidenceService.view",
        side_effect=ValueError("invalid evidence"),
    ):
        assert http.get(f"/warrants/{c.warrant}/valuation-evidence").status_code == 422
