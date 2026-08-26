from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.analysis.domain.governed_provenance import governed_baseline_definition
from app.features.analysis.domain.models import AnalysisParameters, SnapshotRow
from app.features.analysis.persistence.models import (
    MarketAnalysisEventModel,
    MarketAnalysisRunModel,
)
from app.features.analysis.service.application import MarketAnalysisService
from app.features.model.service.application import ModelGovernanceService


async def test_ft006_service_persists_lifecycle_and_governed_provenance_postgres(
    learning_session: AsyncSession,
) -> None:
    workspace_id = uuid4()
    venue_id = uuid4()
    underlying_id = uuid4()
    listing_id = uuid4()
    actor = uuid4()
    now = datetime.now(UTC)

    await learning_session.execute(
        text("insert into workspaces (id, name, created_at) " "values (:id, :name, :created_at)"),
        {
            "id": workspace_id,
            "name": "FT-006 provenance test",
            "created_at": now,
        },
    )
    await learning_session.execute(
        text("""
            insert into trading_venues (
                id, mic, name, country_code, timezone, is_active,
                reference_version, version, created_at, updated_at
            ) values (
                :id, 'XFT6', 'FT006 Test Venue', 'DE', 'Europe/Berlin', true,
                'test', 1, :created_at, :updated_at
            )
        """),
        {
            "id": venue_id,
            "created_at": now,
            "updated_at": now,
        },
    )
    await learning_session.execute(
        text("""
            insert into currencies (
                code, name, minor_unit, is_active,
                reference_version, created_at, updated_at
            ) values (
                'EUR', 'Euro', 2, true, 'test', :created_at, :updated_at
            )
            on conflict (code) do nothing
        """),
        {
            "created_at": now,
            "updated_at": now,
        },
    )
    await learning_session.execute(
        text("""
            insert into underlyings (
                id, workspace_id, type, name, isin, wkn,
                lifecycle_status, quality_status, version,
                created_at, updated_at, data_origin
            ) values (
                :id, :workspace_id, 'STOCK', 'FT006 Test Underlying',
                null, null, 'ACTIVE', 'VERIFIED', 1,
                :created_at, :updated_at, 'MANUAL'
            )
        """),
        {
            "id": underlying_id,
            "workspace_id": workspace_id,
            "created_at": now,
            "updated_at": now,
        },
    )
    await learning_session.execute(
        text("""
            insert into listings (
                id, workspace_id, underlying_id, trading_venue_id,
                ticker, currency_code, lifecycle_status, is_primary,
                version, created_at, updated_at, data_origin
            ) values (
                :id, :workspace_id, :underlying_id, :venue_id,
                'FT06', 'EUR', 'ACTIVE', true,
                1, :created_at, :updated_at, 'MANUAL'
            )
        """),
        {
            "id": listing_id,
            "workspace_id": workspace_id,
            "underlying_id": underlying_id,
            "venue_id": venue_id,
            "created_at": now,
            "updated_at": now,
        },
    )

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

    service = MarketAnalysisService(learning_session)

    analysis = await service.create(
        workspace_id=workspace_id,
        underlying_id=underlying_id,
        listing_id=listing_id,
        actor="integration-test",
    )

    created_events = (
        await learning_session.scalars(
            select(MarketAnalysisEventModel).where(
                MarketAnalysisEventModel.analysis_id == analysis.id,
                MarketAnalysisEventModel.event_type == "CREATED",
            )
        )
    ).all()

    assert len(created_events) == 1

    rows = tuple(
        SnapshotRow(
            trading_date=date(2025, 1, 1) + timedelta(days=index),
            open=Decimal("100") + index,
            high=Decimal("102") + index,
            low=Decimal("99") + index,
            close=Decimal("101") + index,
            adjusted_close=Decimal("101") + index,
            volume=Decimal("1000"),
            currency="EUR",
            provider="EODHD",
            provider_symbol="FT06.XFT6",
            quality_status="VALID",
            warnings=(),
        )
        for index in range(220)
    )

    run = await service._execute_snapshot(
        analysis_id=analysis.id,
        parameters=AnalysisParameters(),
        rows=rows,
        correlation_id="ft006-provenance-integration-test",
        source_version=None,
    )

    persisted_run = await learning_session.get(
        MarketAnalysisRunModel,
        run.id,
    )
    assert persisted_run is not None
    assert persisted_run.governed_model_version_id == baseline.id

    started_events = (
        await learning_session.scalars(
            select(MarketAnalysisEventModel).where(
                MarketAnalysisEventModel.analysis_id == analysis.id,
                MarketAnalysisEventModel.run_id == run.id,
                MarketAnalysisEventModel.event_type == "STARTED",
            )
        )
    ).all()

    assert len(started_events) == 1
