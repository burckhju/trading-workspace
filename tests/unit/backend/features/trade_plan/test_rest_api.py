from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import UUID

from fastapi.testclient import TestClient

from app.core.config import Environment, Settings
from app.features.trade_plan.api.dependencies import (
    get_trade_plan_query_service,
    get_trade_plan_service,
)
from app.features.trade_plan.domain.enums import (
    EntryType,
    TradeDirection,
    TradePlanOriginType,
    TradePlanStatus,
)
from app.features.trade_plan.domain.models import (
    EntryPlan,
    InvalidationPlan,
    RiskAssumptions,
    Target,
    TradePlan,
    TradePlanVersion,
)
from app.features.trade_plan.service.queries import TradePlanVersionView
from app.main import create_application

WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")
ACTOR_ID = UUID("10000000-0000-4000-8000-000000000001")
PLAN_ID = UUID("20000000-0000-4000-8000-000000000001")
VERSION_ID = UUID("30000000-0000-4000-8000-000000000001")
UNDERLYING_ID = UUID("40000000-0000-4000-8000-000000000001")
CANDIDATE_ID = UUID("50000000-0000-4000-8000-000000000001")
EVALUATION_ID = UUID("60000000-0000-4000-8000-000000000001")
NOW = datetime(2026, 8, 11, 16, 0, tzinfo=UTC)


def settings() -> Settings:
    return Settings(
        _env_file=None,
        environment=Environment.TEST,
        documentation_enabled=True,
        log_level="CRITICAL",
    )


def plan(origin=TradePlanOriginType.MANUAL) -> TradePlan:
    return TradePlan(
        id=PLAN_ID,
        workspace_id=WORKSPACE_ID,
        underlying_id=UNDERLYING_ID,
        origin_type=origin,
        created_at=NOW,
        created_by=ACTOR_ID,
        candidate_id=(CANDIDATE_ID if origin is TradePlanOriginType.CANDIDATE_EVALUATION else None),
        candidate_evaluation_id=(
            EVALUATION_ID if origin is TradePlanOriginType.CANDIDATE_EVALUATION else None
        ),
    )


def version(status=TradePlanStatus.DRAFT, number=1) -> TradePlanVersion:
    return TradePlanVersion(
        id=VERSION_ID,
        trade_plan_id=PLAN_ID,
        version=number,
        direction=TradeDirection.LONG,
        thesis="Breakout continuation",
        entry=EntryPlan(type=EntryType.PRICE, currency="EUR", price=Decimal("100")),
        invalidation=InvalidationPlan(stop_price=Decimal("95")),
        targets=(Target(sequence=1, price=Decimal("110")),),
        risk_assumptions=RiskAssumptions(thesis_risk="Failed breakout"),
        status=status,
        created_at=NOW,
        created_by=ACTOR_ID,
    )


def view(status=TradePlanStatus.DRAFT) -> TradePlanVersionView:
    return TradePlanVersionView(
        plan=plan(),
        version=version(status),
        candidate_evaluation=None,
        approval=None,
        events=(),
    )


def payload() -> dict:
    return {
        "origin_type": "MANUAL",
        "underlying_id": str(UNDERLYING_ID),
        "thesis": "Breakout continuation",
        "entry": {"type": "PRICE", "currency": "EUR", "price": "100"},
        "invalidation": {"stop_price": "95"},
        "targets": [{"sequence": 1, "price": "110"}],
        "risk_assumptions": {"thesis_risk": "Failed breakout"},
    }


def app_with(service, query):
    application = create_application(settings())
    application.dependency_overrides[get_trade_plan_service] = lambda: service
    application.dependency_overrides[get_trade_plan_query_service] = lambda: query
    return application


def test_openapi_exposes_ft007_contracts():
    with TestClient(create_application(settings())) as client:
        document = client.get("/openapi.json").json()
    assert "/api/v1/trade-plans" in document["paths"]
    assert "/api/v1/trade-plans/{trade_plan_id}/versions/{version_id}/approve" in document["paths"]
    assert "CreateTradePlanRequest" in document["components"]["schemas"]
    assert "TradePlanVersionResponse" in document["components"]["schemas"]


def test_create_manual_delegates_actor_correlation_and_returns_read_side():
    service, query = AsyncMock(), AsyncMock()
    service.create_manual.return_value = (plan(), version())
    query.get_version.return_value = view()
    with TestClient(app_with(service, query)) as client:
        response = client.post(
            "/api/v1/trade-plans",
            json=payload(),
            headers={"X-Actor-ID": str(ACTOR_ID), "X-Correlation-ID": "corr-9"},
        )
    assert response.status_code == 201
    assert response.json()["plan"]["id"] == str(PLAN_ID)
    kwargs = service.create_manual.await_args.kwargs
    assert kwargs["workspace_id"] == WORKSPACE_ID
    assert kwargs["underlying_id"] == UNDERLYING_ID
    assert kwargs["actor"] == ACTOR_ID
    assert kwargs["correlation_id"] == "corr-9"
    assert kwargs["entry"].price == Decimal("100")
    query.get_version.assert_awaited_once_with(WORKSPACE_ID, PLAN_ID, VERSION_ID)


def test_create_candidate_does_not_accept_underlying_override():
    service, query = AsyncMock(), AsyncMock()
    body = payload()
    body.update(
        {
            "origin_type": "CANDIDATE_EVALUATION",
            "candidate_id": str(CANDIDATE_ID),
            "candidate_evaluation_id": str(EVALUATION_ID),
        }
    )
    with TestClient(app_with(service, query)) as client:
        response = client.post("/api/v1/trade-plans", json=body)
    assert response.status_code == 422
    assert response.json()["code"] == "REQUEST_VALIDATION_ERROR"
    service.create_from_candidate.assert_not_awaited()


def test_get_plan_returns_latest_version_from_history():
    service, query = AsyncMock(), AsyncMock()
    older = view()
    v2 = TradePlanVersion(
        id=UUID("30000000-0000-4000-8000-000000000002"),
        trade_plan_id=PLAN_ID,
        version=2,
        direction=TradeDirection.LONG,
        thesis="v2",
        entry=older.version.entry,
        invalidation=older.version.invalidation,
        targets=older.version.targets,
        risk_assumptions=older.version.risk_assumptions,
        status=TradePlanStatus.DRAFT,
        created_at=NOW,
        created_by=ACTOR_ID,
        previous_version_id=VERSION_ID,
        change_reason="Update",
    )
    newer = TradePlanVersionView(
        plan=plan(), version=v2, candidate_evaluation=None, approval=None, events=()
    )
    query.list_versions.return_value = (older, newer)
    with TestClient(app_with(service, query)) as client:
        response = client.get(f"/api/v1/trade-plans/{PLAN_ID}")
    assert response.status_code == 200
    assert response.json()["latest_version"]["version"] == 2


def test_amend_delegates_base_version_and_reason():
    service, query = AsyncMock(), AsyncMock()
    amended = TradePlanVersion(
        id=UUID("30000000-0000-4000-8000-000000000002"),
        trade_plan_id=PLAN_ID,
        version=2,
        direction=TradeDirection.LONG,
        thesis="updated",
        entry=version().entry,
        invalidation=version().invalidation,
        targets=version().targets,
        risk_assumptions=version().risk_assumptions,
        status=TradePlanStatus.DRAFT,
        created_at=NOW,
        created_by=ACTOR_ID,
        previous_version_id=VERSION_ID,
        change_reason="Changed thesis",
    )
    service.amend.return_value = amended
    query.get_version.return_value = TradePlanVersionView(
        plan=plan(),
        version=amended,
        candidate_evaluation=None,
        approval=None,
        events=(),
    )
    body = payload()
    body.pop("origin_type")
    body.pop("underlying_id")
    body["change_reason"] = "Changed thesis"
    with TestClient(app_with(service, query)) as client:
        response = client.post(
            f"/api/v1/trade-plans/{PLAN_ID}/versions/{VERSION_ID}/amendments",
            json=body,
            headers={"X-Actor-ID": str(ACTOR_ID)},
        )
    assert response.status_code == 201
    assert service.amend.await_args.kwargs["base_version_id"] == VERSION_ID
    assert service.amend.await_args.kwargs["change_reason"] == "Changed thesis"


def test_approve_delegates_exact_version_and_correlation():
    service, query = AsyncMock(), AsyncMock()
    approved = version(TradePlanStatus.APPROVED)
    service.approve.return_value = approved
    query.get_version.return_value = view(TradePlanStatus.APPROVED)
    with TestClient(app_with(service, query)) as client:
        response = client.post(
            f"/api/v1/trade-plans/{PLAN_ID}/versions/{VERSION_ID}/approve",
            headers={"X-Actor-ID": str(ACTOR_ID), "X-Correlation-ID": "approval-corr"},
        )
    assert response.status_code == 200
    service.approve.assert_awaited_once_with(
        WORKSPACE_ID, PLAN_ID, VERSION_ID, ACTOR_ID, "approval-corr"
    )


def test_service_not_found_maps_to_stable_404_contract():
    service, query = AsyncMock(), AsyncMock()
    query.list_versions.side_effect = ValueError("trade plan not found")
    with TestClient(app_with(service, query)) as client:
        response = client.get(f"/api/v1/trade-plans/{PLAN_ID}")
    assert response.status_code == 404
    assert response.json()["code"] == "TRADE_PLAN_NOT_FOUND"


def test_invalid_domain_content_maps_to_422():
    service, query = AsyncMock(), AsyncMock()
    bad = payload()
    bad["entry"]["price"] = "90"
    bad["invalidation"]["stop_price"] = "95"
    with TestClient(app_with(service, query)) as client:
        response = client.post("/api/v1/trade-plans", json=bad)
    assert response.status_code == 422
    assert response.json()["code"] == "TRADE_PLAN_VALIDATION_ERROR"
