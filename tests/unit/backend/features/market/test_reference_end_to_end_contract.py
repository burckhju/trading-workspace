from dataclasses import dataclass
from datetime import UTC, date, datetime
from types import SimpleNamespace
from uuid import UUID

from fastapi.testclient import TestClient

from app.core.config import Environment, Settings
from app.features.market.api.dependencies import (
    get_market_reference_analysis_service,
    get_reference_market_data_service,
    get_top_down_reference_administration_service,
)
from app.features.market_data.service.reference_market_data import ReferencePriceImportResult
from app.main import create_application

WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")
REFERENCE_ID = UUID("10000000-0000-4000-8000-000000000001")
INSTRUMENT_ID = UUID("20000000-0000-4000-8000-000000000001")
MAPPING_ID = UUID("30000000-0000-4000-8000-000000000001")
ANALYSIS_ID = UUID("40000000-0000-4000-8000-000000000001")
NOW = datetime(2026, 8, 27, 8, 0, tzinfo=UTC)


def settings() -> Settings:
    return Settings(
        _env_file=None,
        environment=Environment.TEST,
        documentation_enabled=True,
        log_level="CRITICAL",
    )


@dataclass
class WorkflowState:
    mapping_created: bool = False
    mapping_active: bool = False
    imported_prices: int = 0
    analysis_created: bool = False
    analysis_completed: bool = False


class FakeReferenceMarketDataService:
    def __init__(self, state: WorkflowState) -> None:
        self.state = state

    def _mapping(self) -> SimpleNamespace:
        return SimpleNamespace(
            id=MAPPING_ID,
            workspace_id=WORKSPACE_ID,
            listing_id=None,
            market_data_instrument_id=INSTRUMENT_ID,
            provider="EODHD",
            provider_symbol="GSPC",
            provider_exchange_code="INDX",
            status="ACTIVE" if self.state.mapping_active else "DISABLED",
            validated_at=NOW if self.state.mapping_active else None,
            validation_message=(
                "Technically validated against EODHD Search API; currency=USD"
                if self.state.mapping_active
                else "Awaiting explicit validation"
            ),
            version=2 if self.state.mapping_active else 1,
        )

    async def upsert_mapping(self, **kwargs: object) -> SimpleNamespace:
        assert kwargs["workspace_id"] == WORKSPACE_ID
        assert kwargs["market_reference_id"] == REFERENCE_ID
        assert kwargs["provider_symbol"] == "GSPC"
        assert kwargs["provider_exchange_code"] == "INDX"
        self.state.mapping_created = True
        self.state.mapping_active = False
        return self._mapping()

    async def validate_mapping(self, **kwargs: object) -> SimpleNamespace:
        assert self.state.mapping_created
        assert kwargs["workspace_id"] == WORKSPACE_ID
        assert kwargs["market_reference_id"] == REFERENCE_ID
        self.state.mapping_active = True
        return self._mapping()

    async def import_daily_prices(self, **kwargs: object) -> ReferencePriceImportResult:
        assert self.state.mapping_active
        assert kwargs["workspace_id"] == WORKSPACE_ID
        assert kwargs["market_reference_id"] == REFERENCE_ID
        start_date = kwargs["start_date"]
        end_date = kwargs["end_date"]
        assert isinstance(start_date, date)
        assert isinstance(end_date, date)
        self.state.imported_prices = 61
        return ReferencePriceImportResult(
            market_reference_id=REFERENCE_ID,
            market_data_instrument_id=INSTRUMENT_ID,
            mapping_id=MAPPING_ID,
            currency="USD",
            start_date=start_date,
            end_date=end_date,
            inserted=61,
            updated=0,
            unchanged=0,
        )


class FakeReferenceAnalysisService:
    def __init__(self, state: WorkflowState) -> None:
        self.state = state

    async def create_for_market_reference(self, **kwargs: object) -> SimpleNamespace:
        assert self.state.imported_prices >= 61
        assert kwargs["workspace_id"] == WORKSPACE_ID
        assert kwargs["market_reference_id"] == REFERENCE_ID
        self.state.analysis_created = True
        return SimpleNamespace(
            id=ANALYSIS_ID,
            market_data_instrument_id=INSTRUMENT_ID,
            created_at=NOW,
            created_by=kwargs["actor"],
        )

    async def run_market_reference(self, **kwargs: object) -> SimpleNamespace:
        assert self.state.analysis_created
        assert kwargs["workspace_id"] == WORKSPACE_ID
        assert kwargs["analysis_id"] == ANALYSIS_ID
        self.state.analysis_completed = True
        return SimpleNamespace(
            version=1,
            status="COMPLETED",
            quality_status="VALID",
            model_id="FT-006",
            model_version="1",
            observation_count=61,
            analysis_time=NOW,
            input_hash="d01g-qualified-input",
        )


class FakeReadinessService:
    def __init__(self, state: WorkflowState) -> None:
        self.state = state

    async def reference_readiness(self, workspace_id: UUID) -> tuple[SimpleNamespace, ...]:
        assert workspace_id == WORKSPACE_ID
        ready = (
            self.state.mapping_active
            and self.state.imported_prices >= 61
            and self.state.analysis_completed
        )
        blockers: list[str] = []
        if not self.state.mapping_active:
            blockers.append("NO_ACTIVE_PROVIDER_MAPPING")
        if self.state.imported_prices < 61:
            blockers.append("INSUFFICIENT_DAILY_PRICE_HISTORY")
        if not self.state.analysis_completed:
            blockers.append("NO_COMPLETED_ANALYSIS")
        return (
            SimpleNamespace(
                reference_id=REFERENCE_ID,
                reference_code="SP500",
                reference_type="INDEX",
                listing_id=None,
                provider_mapping_id=MAPPING_ID if self.state.mapping_created else None,
                provider_mapping_active=self.state.mapping_active,
                daily_price_count=self.state.imported_prices,
                latest_price_date=(date(2026, 8, 26) if self.state.imported_prices else None),
                completed_analysis_id=(ANALYSIS_ID if self.state.analysis_completed else None),
                completed_analysis_version=1 if self.state.analysis_completed else None,
                ready=ready,
                blockers=tuple(blockers),
            ),
        )


def test_market_reference_public_chain_reaches_readiness_without_listing() -> None:
    state = WorkflowState()
    application = create_application(settings())
    application.dependency_overrides[get_reference_market_data_service] = lambda: (
        FakeReferenceMarketDataService(state)
    )
    application.dependency_overrides[get_market_reference_analysis_service] = lambda: (
        FakeReferenceAnalysisService(state)
    )
    application.dependency_overrides[get_top_down_reference_administration_service] = lambda: (
        FakeReadinessService(state)
    )

    with TestClient(application) as client:
        initial = client.get("/api/v1/top-down-reference-data/readiness")
        assert initial.status_code == 200
        assert initial.json()[0]["ready"] is False
        assert initial.json()[0]["listing_id"] is None

        mapping = client.put(
            f"/api/v1/top-down-reference-data/market-references/{REFERENCE_ID}"
            "/provider-mapping/eodhd",
            json={"provider_symbol": "GSPC", "provider_exchange_code": "INDX"},
        )
        assert mapping.status_code == 200
        assert mapping.json()["listing_id"] is None
        assert mapping.json()["status"] == "DISABLED"

        validation = client.post(
            f"/api/v1/top-down-reference-data/market-references/{REFERENCE_ID}"
            "/provider-mapping/eodhd/validate"
        )
        assert validation.status_code == 200
        assert validation.json()["status"] == "ACTIVE"

        imported = client.post(
            f"/api/v1/top-down-reference-data/market-references/{REFERENCE_ID}"
            "/daily-prices/import",
            json={"start_date": "2026-06-01", "end_date": "2026-08-26"},
        )
        assert imported.status_code == 200
        assert imported.json()["inserted"] == 61
        assert imported.json()["market_data_instrument_id"] == str(INSTRUMENT_ID)

        analysis = client.post(
            f"/api/v1/top-down-reference-data/market-references/{REFERENCE_ID}/analyses",
            headers={"X-Actor-Name": "D01-G qualification"},
        )
        assert analysis.status_code == 201
        assert analysis.json()["analysis_id"] == str(ANALYSIS_ID)
        assert analysis.json()["market_data_instrument_id"] == str(INSTRUMENT_ID)

        run = client.post(
            f"/api/v1/top-down-reference-data/market-reference-analyses/{ANALYSIS_ID}/runs",
            json={"start_date": "2026-06-01", "end_date": "2026-08-26"},
        )
        assert run.status_code == 201
        assert run.json()["status"] == "COMPLETED"

        readiness = client.get("/api/v1/top-down-reference-data/readiness")

    assert readiness.status_code == 200
    result = readiness.json()[0]
    assert result["listing_id"] is None
    assert result["provider_mapping_active"] is True
    assert result["daily_price_count"] == 61
    assert result["completed_analysis_id"] == str(ANALYSIS_ID)
    assert result["blockers"] == []
    assert result["ready"] is True
