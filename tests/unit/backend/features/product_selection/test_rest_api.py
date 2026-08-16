from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import UUID

from fastapi.testclient import TestClient

from app.core.config import Environment, Settings
from app.features.product_selection.api.dependencies import (
    get_product_selection_command_service,
    get_product_selection_persistence_service,
    get_product_selection_query_service,
    get_product_selection_service,
)
from app.features.product_selection.domain.enums import (
    CriterionOutcome,
    DataAvailability,
    EligibilityStatus,
)
from app.features.product_selection.domain.models import (
    CriterionResult,
    EvaluationInput,
    ModelReference,
    ProductEvaluation,
    ProductSelection,
    ProductSelectionRun,
)
from app.features.product_selection.service.application import ProductSelectionRunResult
from app.features.product_selection.service.queries import ProductSelectionRunView
from app.features.trade_plan.domain.enums import TradePlanStatus
from app.main import create_application

WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")
ACTOR_ID = UUID("10000000-0000-4000-8000-000000000001")
PLAN_ID = UUID("20000000-0000-4000-8000-000000000001")
VERSION_ID = UUID("30000000-0000-4000-8000-000000000001")
RUN_ID = UUID("40000000-0000-4000-8000-000000000001")
UNDERLYING_ID = UUID("50000000-0000-4000-8000-000000000001")
WARRANT_ID = UUID("60000000-0000-4000-8000-000000000001")
TERMS_ID = UUID("70000000-0000-4000-8000-000000000001")
LISTING_ID = UUID("80000000-0000-4000-8000-000000000001")
EVALUATION_ID = UUID("90000000-0000-4000-8000-000000000001")
NOW = datetime(2026, 8, 16, 8, 0, tzinfo=UTC)
MODEL = ModelReference("model", "1.0.0")


def settings() -> Settings:
    return Settings(
        _env_file=None,
        environment=Environment.TEST,
        documentation_enabled=True,
        log_level="CRITICAL",
    )


def run() -> ProductSelectionRun:
    return ProductSelectionRun(
        id=RUN_ID,
        workspace_id=WORKSPACE_ID,
        trade_plan_id=PLAN_ID,
        trade_plan_version_id=VERSION_ID,
        trade_plan_version_status=TradePlanStatus.APPROVED,
        underlying_id=UNDERLYING_ID,
        evaluated_at=NOW,
        universe_model=MODEL,
        eligibility_model=MODEL,
        evaluation_model=MODEL,
        created_at=NOW,
        created_by=ACTOR_ID,
    )


def evaluation() -> ProductEvaluation:
    explanation = "Warrant listing market data is not available"
    return ProductEvaluation(
        id=EVALUATION_ID,
        run_id=RUN_ID,
        warrant_id=WARRANT_ID,
        warrant_terms_version_id=TERMS_ID,
        warrant_listing_id=LISTING_ID,
        evaluated_at=NOW,
        eligibility_model=MODEL,
        evaluation_model=MODEL,
        inputs=(
            EvaluationInput(
                name="market_data_snapshot",
                value=None,
                availability=DataAvailability.MISSING,
                source="market-data-boundary",
            ),
        ),
        criteria=(
            CriterionResult(
                criterion_id="market-data",
                outcome=CriterionOutcome.NOT_EVALUABLE,
                explanation=explanation,
                data_availability=DataAvailability.MISSING,
            ),
        ),
        metrics=(),
        eligibility_status=EligibilityStatus.NOT_EVALUABLE,
        reasons=(explanation,),
    )


def app_with(
    service: AsyncMock, persistence: AsyncMock, query: AsyncMock, command: AsyncMock | None = None
):
    app = create_application(settings())
    app.dependency_overrides[get_product_selection_service] = lambda: service
    app.dependency_overrides[get_product_selection_persistence_service] = lambda: persistence
    app.dependency_overrides[get_product_selection_query_service] = lambda: query
    app.dependency_overrides[get_product_selection_command_service] = lambda: command or AsyncMock()
    return app


def test_openapi_exposes_explicit_selection_command() -> None:
    with TestClient(create_application(settings())) as client:
        paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/product-selection-runs" in paths
    assert "/api/v1/product-selection-runs/{run_id}" in paths
    assert "/api/v1/product-selection-runs/{run_id}/evaluations/{evaluation_id}" in paths
    assert "/api/v1/product-selection-runs/{run_id}/selection" in paths


def test_start_run_uses_server_controlled_models_and_persists_before_reading() -> None:
    service, persistence, query = AsyncMock(), AsyncMock(), AsyncMock()
    result = ProductSelectionRunResult(
        run=run(), evaluations=(evaluation(),), universe_omissions=()
    )
    service.start_run.return_value = result
    query.get_run.return_value = ProductSelectionRunView(
        run=run(), evaluations=(evaluation(),), universe_omissions=(), selection=None
    )
    with TestClient(app_with(service, persistence, query)) as client:
        response = client.post(
            "/api/v1/product-selection-runs",
            json={"trade_plan_id": str(PLAN_ID), "trade_plan_version_id": str(VERSION_ID)},
            headers={"X-Actor-ID": str(ACTOR_ID)},
        )
    assert response.status_code == 201
    kwargs = service.start_run.await_args.kwargs
    assert kwargs["workspace_id"] == WORKSPACE_ID
    assert kwargs["actor"] == ACTOR_ID
    assert kwargs["models"].direction_rule is None
    assert kwargs["models"].evaluation.model_id == "ft008-product-evaluation"
    persistence.persist_run.assert_awaited_once_with(result)
    query.get_run.assert_awaited_once_with(WORKSPACE_ID, RUN_ID)
    assert response.json()["evaluations"][0]["eligibility_status"] == "NOT_EVALUABLE"


def test_get_run_surfaces_missing_data_reason() -> None:
    service, persistence, query = AsyncMock(), AsyncMock(), AsyncMock()
    query.get_run.return_value = ProductSelectionRunView(
        run=run(), evaluations=(evaluation(),), universe_omissions=(), selection=None
    )
    with TestClient(app_with(service, persistence, query)) as client:
        response = client.get(f"/api/v1/product-selection-runs/{RUN_ID}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["selection"] is None
    assert payload["evaluations"][0]["criteria"][0]["data_availability"] == "MISSING"
    assert "not available" in payload["evaluations"][0]["reasons"][0]


def test_get_evaluation_is_scoped_to_run() -> None:
    service, persistence, query = AsyncMock(), AsyncMock(), AsyncMock()
    query.get_evaluation.return_value = evaluation()
    with TestClient(app_with(service, persistence, query)) as client:
        response = client.get(
            f"/api/v1/product-selection-runs/{RUN_ID}/evaluations/{EVALUATION_ID}"
        )
    assert response.status_code == 200
    query.get_evaluation.assert_awaited_once_with(WORKSPACE_ID, RUN_ID, EVALUATION_ID)


def test_non_approved_start_maps_to_conflict() -> None:
    service, persistence, query = AsyncMock(), AsyncMock(), AsyncMock()
    service.start_run.side_effect = ValueError(
        "Product Selection requires an APPROVED TradePlanVersion"
    )
    with TestClient(app_with(service, persistence, query)) as client:
        response = client.post(
            "/api/v1/product-selection-runs",
            json={"trade_plan_id": str(PLAN_ID), "trade_plan_version_id": str(VERSION_ID)},
        )
    assert response.status_code == 409
    assert response.json()["code"] == "PRODUCT_SELECTION_CONFLICT"
    persistence.persist_run.assert_not_awaited()


def test_select_endpoint_creates_explicit_user_decision_and_returns_updated_run():
    service, persistence, query, command = AsyncMock(), AsyncMock(), AsyncMock(), AsyncMock()
    selected = ProductSelection(
        id=UUID("a0000000-0000-4000-8000-000000000001"),
        run_id=RUN_ID,
        product_evaluation_id=EVALUATION_ID,
        selected_at=NOW,
        selected_by=ACTOR_ID,
        rationale="explicit choice",
    )
    command.select_product.return_value = selected
    query.get_run.return_value = ProductSelectionRunView(
        run=run(), evaluations=(evaluation(),), universe_omissions=(), selection=selected
    )
    with TestClient(app_with(service, persistence, query, command)) as client:
        response = client.post(
            f"/api/v1/product-selection-runs/{RUN_ID}/selection",
            json={"product_evaluation_id": str(EVALUATION_ID), "rationale": "explicit choice"},
            headers={"X-Actor-ID": str(ACTOR_ID)},
        )
    assert response.status_code == 201
    command.select_product.assert_awaited_once_with(
        workspace_id=WORKSPACE_ID,
        run_id=RUN_ID,
        evaluation_id=EVALUATION_ID,
        actor=ACTOR_ID,
        rationale="explicit choice",
    )
    assert response.json()["selection"]["product_evaluation_id"] == str(EVALUATION_ID)


def test_second_selection_maps_to_conflict():
    service, persistence, query, command = AsyncMock(), AsyncMock(), AsyncMock(), AsyncMock()
    command.select_product.side_effect = ValueError(
        "product selection run already has a user selection"
    )
    with TestClient(app_with(service, persistence, query, command)) as client:
        response = client.post(
            f"/api/v1/product-selection-runs/{RUN_ID}/selection",
            json={"product_evaluation_id": str(EVALUATION_ID)},
        )
    assert response.status_code == 409
    assert response.json()["code"] == "PRODUCT_SELECTION_CONFLICT"


def test_ineligible_selection_is_rejected_by_api():
    service, persistence, query, command = AsyncMock(), AsyncMock(), AsyncMock(), AsyncMock()
    command.select_product.side_effect = ValueError(
        "V1 ProductSelection requires an ELIGIBLE ProductEvaluation"
    )
    with TestClient(app_with(service, persistence, query, command)) as client:
        response = client.post(
            f"/api/v1/product-selection-runs/{RUN_ID}/selection",
            json={"product_evaluation_id": str(EVALUATION_ID)},
        )
    assert response.status_code == 409
