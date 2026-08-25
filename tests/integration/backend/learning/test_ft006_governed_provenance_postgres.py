from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.analysis.domain.governed_provenance import governed_baseline_definition
from app.features.analysis.persistence.models import MarketAnalysisModel, MarketAnalysisRunModel
from app.features.model.service.application import ModelGovernanceService


async def test_approved_ft006_baseline_is_persisted_as_run_provenance(
    learning_session: AsyncSession,
) -> None:
    workspace_id = uuid4()
    venue_id = uuid4()
    underlying_id = uuid4()
    listing_id = uuid4()
    analysis_id = uuid4()
    actor = uuid4()
    now = datetime.now(UTC)

    await learning_session.execute(
        text("insert into workspaces (id, name, created_at) values (:id, :name, :created_at)"),
        {"id": workspace_id, "name": "FT-006 provenance test", "created_at": now},
    )
    await learning_session.execute(
        text(
            """
            insert into trading_venues (
                id, mic, name, country_code, timezone, is_active,
                reference_version, version, created_at, updated_at
            ) values (
                :id, 'XETR', 'Xetra', 'DE', 'Europe/Berlin', true,
                'test', 1, :created_at, :updated_at
            )
            """
        ),
        {"id": venue_id, "created_at": now, "updated_at": now},
    )
    await learning_session.execute(
        text(
            """
            insert into currencies (
                code, name, minor_unit, is_active, reference_version, created_at, updated_at
            ) values ('EUR', 'Euro', 2, true, 'test', :created_at, :updated_at)
            on conflict (code) do nothing
            """
        ),
        {"created_at": now, "updated_at": now},
    )
    await learning_session.execute(
        text(
            """
            insert into underlyings (
                id, workspace_id, type, name, isin, wkn, lifecycle_status,
                quality_status, version, created_at, updated_at, data_origin
            ) values (
                :id, :workspace_id, 'STOCK', 'FT006 Test Underlying', null, null, 'ACTIVE',
                'VERIFIED', 1, :created_at, :updated_at, 'MANUAL'
            )
            """
        ),
        {
            "id": underlying_id,
            "workspace_id": workspace_id,
            "created_at": now,
            "updated_at": now,
        },
    )
    await learning_session.execute(
        text(
            """
            insert into listings (
                id, workspace_id, underlying_id, trading_venue_id, ticker, currency_code,
                lifecycle_status, is_primary, version, created_at, updated_at, data_origin
            ) values (
                :id, :workspace_id, :underlying_id, :venue_id, 'FT06', 'EUR',
                'ACTIVE', true, 1, :created_at, :updated_at, 'MANUAL'
            )
            """
        ),
        {
            "id": listing_id,
            "workspace_id": workspace_id,
            "underlying_id": underlying_id,
            "venue_id": venue_id,
            "created_at": now,
            "updated_at": now,
        },
    )

    analysis = MarketAnalysisModel(
        id=analysis_id,
        workspace_id=workspace_id,
        underlying_id=underlying_id,
        listing_id=listing_id,
        created_at=now,
        created_by="integration-test",
    )
    learning_session.add(analysis)
    await learning_session.flush()

    governance = ModelGovernanceService(learning_session)
    model, baseline = await governance.create_model(
        workspace_id=workspace_id,
        model_key="EOD_TREND_MOMENTUM",
        name="EOD Trend Momentum",
        purpose="Governed provenance anchor for the released FT-006 runtime",
        initial_definition=governed_baseline_definition(),
        actor=actor,
    )
    await governance.approve_initial_version(
        workspace_id=workspace_id,
        model_id=model.id,
        version_id=baseline.id,
        actor=actor,
        correlation_id="ft006-provenance-integration-test",
    )

    run = MarketAnalysisRunModel(
        id=uuid4(),
        analysis_id=analysis_id,
        version=1,
        status="COMPLETED",
        quality_status="COMPLETE",
        model_id="EOD_TREND_MOMENTUM",
        model_version="1.0.0",
        parameters={},
        metrics={},
        notes=[],
        data_sources=[],
        input_hash="0" * 64,
        observation_count=200,
        analysis_time=now,
        correlation_id="ft006-provenance-integration-test",
        error_message=None,
    )
    learning_session.add(run)
    await learning_session.flush()

    assert run.governed_model_version_id == baseline.id
