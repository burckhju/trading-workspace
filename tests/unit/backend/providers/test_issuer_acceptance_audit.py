"""Acceptance reports cannot promote partial evidence or stale source bindings."""

from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.features.market_data.domain.enums import MarketDataProvider
from app.tools import audit_new_issuer_routes as module


@pytest.mark.parametrize(
    "fault",
    [None, "missing_mapping", "bid_missing", "wrong_identity", "old_selection", "no_position"],
)
async def test_acceptance_requires_identity_quote_and_exact_selection(monkeypatch, fault):
    now = datetime.now(UTC)
    workspace, warrant_id, mapping_id = uuid4(), uuid4(), uuid4()
    identity = SimpleNamespace(key="verified-key")
    mapping = SimpleNamespace(
        id=mapping_id,
        warrant_listing_id=uuid4(),
        version=1,
        provider=MarketDataProvider.JPMORGAN,
        created_at=now - timedelta(seconds=1),
        identity_evidence={"acquisition_mode": "RENDERED_DOM"},
    )
    quote = SimpleNamespace(
        identity_key="wrong" if fault == "wrong_identity" else identity.key,
        payload={
            "retrieved_at": now.isoformat(),
            "data": {
                "bid": None if fault == "bid_missing" else "0.0250",
                "ask": None,
                "currency": "EUR",
                "observed_at": None,
                "quote_time_text": "14:00:00",
                "quote_time_basis": "DATE_AND_TIMEZONE_UNKNOWN",
            },
        },
    )
    binding = {
        "selection_status": "SELECTED",
        "provider": "JPMORGAN",
        "mapping_id": mapping_id,
        "identity_key": identity.key,
        "mapping_version": 0 if fault == "old_selection" else 1,
    }
    statements = []

    async def execute(statement, params=None):
        statements.append(str(statement))
        if str(statement) == "SET TRANSACTION READ ONLY":
            return None
        if params is not None:
            assert params == {"workspace": workspace, "warrant": warrant_id}
            return SimpleNamespace(
                mappings=lambda: SimpleNamespace(
                    all=lambda: [] if fault == "no_position" else [binding]
                )
            )
        return SimpleNamespace(
            all=lambda: (
                [] if fault == "missing_mapping" else [(SimpleNamespace(id=warrant_id), mapping)]
            )
        )

    session = SimpleNamespace(execute=execute, get=AsyncMock(return_value=quote))

    @asynccontextmanager
    async def session_context():
        yield session

    monkeypatch.setattr(module, "TARGETS", ("DE000JZ91459",))
    monkeypatch.setattr(module, "read_quote_identity", AsyncMock(return_value=identity))
    result = (await module.snapshot(SimpleNamespace(session_context=session_context), workspace))[0]
    assert statements[0] == "SET TRANSACTION READ ONLY"
    assert all(s.lstrip().startswith("SELECT") for s in statements[1:])
    assert result["quote_verified"] is (
        fault not in {"missing_mapping", "bid_missing", "wrong_identity"}
    )
    assert result["execution_usable"] is False
    if fault == "old_selection":
        assert result["selection_verification"] == "EXISTING_OR_UNRESOLVED_SOURCE_REVIEW"
    if fault == "no_position":
        assert result["selection_verification"] == "NOT_APPLICABLE_NO_OPEN_POSITION"
    if fault is None:
        assert result["selection_verification"] == "DYNAMIC_ROUTE_SELECTED"
        assert result["quote_observed_at"] is None
