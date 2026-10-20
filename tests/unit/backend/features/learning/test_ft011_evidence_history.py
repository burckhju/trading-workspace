"""Historical inventory is a separate read contract, not a readiness boolean."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from test_trade_link_api import _make_app

from app.features.learning.api.materialization_dependencies import (
    get_ft011_evidence_history_service,
)
from app.features.learning.application.ft011_evidence_history_service import (
    Ft011EvidenceHistoryService,
)
from app.features.learning.domain import (
    FT011Evidence,
    LearningEvidence,
    LearningEvidenceType,
    LessonEvidenceRelation,
)
from app.features.learning.persistence.lesson_evidence_read_repository import (
    HistoricalLessonEvidenceReference,
)
from app.features.learning.persistence.repositories import LearningEvidenceProjection
from app.features.post_trade.application.exit_review_service import Ft011SourceInspection


@pytest.mark.parametrize("state", ["CURRENT", "STALE", "UNKNOWN"])
async def test_inventory_retains_ids_time_stored_state_and_historical_relations(state):
    ws, trade, eid, version, successor = (uuid4() for _ in range(5))
    made = datetime(2026, 9, 1, tzinfo=UTC)
    checked = datetime(2026, 10, 16, tzinfo=UTC)
    source = FT011Evidence(eid, trade, uuid4(), uuid4(), version)
    evidence = LearningEvidence(eid, ws, LearningEvidenceType.FT011, made)
    links = tuple(
        HistoricalLessonEvidenceReference(
            uuid4(), uuid4(), "Explicit interpretation", uuid4(), 1, rel, False
        )
        for rel in LessonEvidenceRelation
    )
    repo = SimpleNamespace(
        list_for_trade=AsyncMock(return_value=(LearningEvidenceProjection(evidence, source),))
    )
    inspector = SimpleNamespace(
        inspect_materialized_source=AsyncMock(
            return_value=Ft011SourceInspection(1, "FINALIZED", "CURRENT", state, successor)
        )
    )
    lessons = SimpleNamespace(list_version_references_for_evidence=AsyncMock(return_value=links))
    service = Ft011EvidenceHistoryService(
        repository=repo,
        inspector=inspector,
        lessons=lessons,
        clock=SimpleNamespace(now=lambda: checked),
    )
    first = await service.get(workspace_id=ws, trade_id=trade)
    assert first == await service.get(workspace_id=ws, trade_id=trade)
    item = first[0]
    assert item.learning_evidence_id == eid and item.exit_review_version_id == version
    assert item.materialized_at == made and item.checked_at == checked
    assert item.stored_review_currentness == "CURRENT" and item.source_currentness == state
    assert item.superseded_by_version_id == successor
    assert item.lesson_links == links and all(
        not link.is_current_version for link in item.lesson_links
    )
    assert {link.relation for link in item.lesson_links} == set(LessonEvidenceRelation)
    repo.list_for_trade.assert_called_with(workspace_id=ws, trade_id=trade)
    inspector.inspect_materialized_source.assert_called_with(
        workspace_id=ws,
        trade_id=trade,
        observation_id=source.post_trade_observation_id,
        review_id=source.exit_review_id,
        version_id=version,
    )


async def test_empty_history_does_not_inspect_any_source():
    inspector = SimpleNamespace(inspect_materialized_source=AsyncMock())
    service = Ft011EvidenceHistoryService(
        repository=SimpleNamespace(list_for_trade=AsyncMock(return_value=())),
        inspector=inspector,
        lessons=SimpleNamespace(),
        clock=SimpleNamespace(),
    )
    assert await service.get(workspace_id=uuid4(), trade_id=uuid4()) == ()
    inspector.inspect_materialized_source.assert_not_awaited()


def test_history_api_is_registered_and_uses_existing_workspace():
    service = SimpleNamespace(get=AsyncMock(return_value=()))
    app = _make_app()
    app.dependency_overrides[get_ft011_evidence_history_service] = lambda: service
    trade = uuid4()
    with TestClient(app) as client:
        response = client.get(f"/api/v1/learning/trades/{trade}/ft011-evidence/history")
    assert response.status_code == 200 and response.json() == []
    assert service.get.call_args.kwargs["trade_id"] == trade
    assert (
        str(service.get.call_args.kwargs["workspace_id"]) == "00000000-0000-4000-8000-000000000001"
    )


def test_history_wire_keeps_concrete_versions_and_relation_without_ready_field():
    from app.features.learning.application.ft011_evidence_history_service import (
        Ft011EvidenceHistoryItem,
    )

    eid, trade, version, lesson_version, link = (uuid4() for _ in range(5))
    now = datetime(2026, 10, 16, tzinfo=UTC)
    item = Ft011EvidenceHistoryItem(
        eid,
        "FT011",
        now,
        trade,
        uuid4(),
        uuid4(),
        version,
        1,
        "FINALIZED",
        "CURRENT",
        "STALE",
        None,
        now,
        (
            HistoricalLessonEvidenceReference(
                link, uuid4(), "Title", lesson_version, 1, LessonEvidenceRelation.CONTRADICTS, False
            ),
        ),
    )
    app = _make_app()
    app.dependency_overrides[get_ft011_evidence_history_service] = lambda: SimpleNamespace(
        get=AsyncMock(return_value=(item,))
    )
    with TestClient(app) as client:
        response = client.get(f"/api/v1/learning/trades/{trade}/ft011-evidence/history")
    assert response.status_code == 200, response.text
    value = response.json()[0]
    assert value["learning_evidence_id"] == str(eid)
    assert value["exit_review_version_id"] == str(version)
    assert value["source_currentness"] == "STALE"
    assert value["stored_review_currentness"] == "CURRENT"
    assert "ready" not in value
    saved_link = value["lesson_links"][0]
    assert saved_link["relation"] == "CONTRADICTS"
    assert saved_link["lesson_version_id"] == str(lesson_version)
    assert saved_link["link_id"] == str(link)
    assert saved_link["is_current_version"] is False
