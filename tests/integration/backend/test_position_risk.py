"""Real SQL repositories + controlled owner input contract; no provider or delivery."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from tests.unit.backend.features.position_monitoring.test_risk_signals import LISTING, prices

from app.features.alert.persistence.models import AlertModel
from app.features.market.service.risk_reference import RiskListingReference
from app.features.market_data.domain.models import WarrantQuoteSnapshot
from app.features.market_data.domain.risk_evidence import SavedQuoteEvidence
from app.features.notification.persistence.models import NotificationModel
from app.features.notification.persistence.repositories import SqlAlchemyNotificationRepository
from app.features.notification.service.creation import AlertNotificationService
from app.features.position_monitoring.domain.risk_signals import RiskParameters
from app.features.position_monitoring.persistence.models import (
    MonitoringRuleStateModel,
    PositionRiskConfigurationModel,
    PositionRiskSnapshotModel,
)
from app.features.position_monitoring.persistence.risk_records import RISK_VIEW
from app.features.position_monitoring.service.risk import (
    PositionRiskService,
    RiskConfigurationConflict,
)
from app.features.position_monitoring.service.risk_inputs import RiskInputs
from app.features.product.service.risk_reference import RiskProductReference
from app.features.trade_position.persistence.models import PositionModel, TradeModel
from app.features.trade_position.service.open_position_reader import OpenPositionReference
from app.main import create_application


class AsyncFacade:
    """Exercise the actual statements in SQLite; PostgreSQL locking is tested separately."""

    def __init__(self, session):
        self.sync = session

    async def execute(self, stmt):
        return self.sync.execute(stmt)

    async def scalar(self, stmt):
        return self.sync.scalar(stmt)

    async def scalars(self, stmt):
        return self.sync.scalars(stmt)

    async def get(self, model, key):
        return self.sync.get(model, key)

    def add(self, value):
        self.sync.add(value)

    async def flush(self):
        self.sync.flush()

    async def commit(self):
        self.sync.commit()


class ControlledInputs:
    def __init__(self, ref):
        self.ref = ref
        self.values = list(prices(41))
        # Rising terminal close makes the initial state unambiguously ABOVE.
        self.values[-1] = replace(
            self.values[-1],
            open=Decimal(110),
            high=Decimal(111),
            low=Decimal(109),
            close=Decimal(110),
            adjusted_close=Decimal(110),
        )
        self.product = RiskProductReference(
            ref.warrant_id,
            uuid4(),
            "Synthetic call",
            None,
            None,
            uuid4(),
            "CALL",
            Decimal(".1"),
            Decimal(100),
            "EUR",
            None,
        )
        self.quote = SavedQuoteEvidence("NO_CONFIRMED_SAVED_QUOTE_SOURCE")

    async def read(self, ref, as_of):
        assert ref == self.ref
        return RiskInputs(
            ref,
            self.product,
            RiskListingReference(LISTING, "EUR", "TEST"),
            tuple(self.values),
            self.quote,
        )

    def append(self, value):
        day = self.values[-1].trading_date + timedelta(days=1)
        while day.weekday() >= 5:
            day += timedelta(days=1)
        close = Decimal(value)
        self.values.append(
            replace(
                self.values[-1],
                trading_date=day,
                open=close,
                high=close + 1,
                low=close - 1,
                close=close,
                adjusted_close=close,
                retrieved_at=datetime.combine(day, datetime.min.time(), tzinfo=UTC)
                + timedelta(hours=22),
            )
        )

    def now(self):
        return self.values[-1].retrieved_at + timedelta(hours=3)


@pytest.fixture
def stored():
    create_application()  # Load the complete FK metadata, without connecting to a server.
    engine = create_engine("sqlite://")
    tables = [
        TradeModel,
        PositionModel,
        PositionRiskConfigurationModel,
        PositionRiskSnapshotModel,
        MonitoringRuleStateModel,
        AlertModel,
        NotificationModel,
    ]
    for model in tables:
        model.__table__.create(engine)
    workspace, trade, position, warrant = (uuid4() for _ in range(4))
    ref = OpenPositionReference(workspace, trade, position, warrant)
    with Session(engine, expire_on_commit=False, autoflush=False) as session:
        session.add(
            TradeModel(
                id=trade,
                workspace_id=workspace,
                product_id=warrant,
                origin="EXTERNAL",
                created_at=datetime.now(UTC),
                created_by=uuid4(),
            )
        )
        session.add(
            PositionModel(
                id=position,
                trade_id=trade,
                product_id=warrant,
                open_quantity=10,
                cost_basis=20,
                average_entry_price=2,
                opened_at=datetime.now(UTC),
                last_execution_at=datetime.now(UTC),
                realized_gross_pnl=0,
            )
        )
        session.commit()
        yield AsyncFacade(session), ref, ControlledInputs(ref)
    engine.dispose()


@pytest.mark.asyncio
async def test_preview_configuration_snapshot_alert_replay_recovery_and_versioning(stored):
    session, ref, inputs = stored
    service = PositionRiskService(session, inputs)
    kwargs = dict(workspace_id=ref.workspace_id, trade_id=ref.trade_id)
    preview = await service.preview(**kwargs, now=inputs.now())
    assert preview.configuration.enabled is False and preview.snapshot_id is None
    assert preview.iv.status == "NOT_EVALUABLE" and preview.iv.current_iv_decimal is None
    assert session.sync.scalar(select(func.count()).select_from(PositionRiskSnapshotModel)) == 0
    config = await service.configure(
        **kwargs,
        now=inputs.now(),
        parameters=RiskParameters(),
        enabled=True,
        expected_revision=0,
        actor=uuid4(),
        correlation_id="test",
    )
    assert config.revision == 1
    proposed = await service.preview(
        **kwargs, now=inputs.now(), parameters=RiskParameters(confirmation_sessions=3)
    )
    assert not proposed.configuration.enabled
    assert proposed.configuration.actor is None and proposed.configuration.configured_at is None
    baseline, alerts = await service.evaluate(**kwargs, now=inputs.now())
    assert baseline.assessment.transition == "INITIALIZED" and not alerts
    duplicate, _ = await service.evaluate(**kwargs, now=inputs.now() + timedelta(minutes=1))
    assert duplicate.snapshot_id == baseline.snapshot_id
    inputs.quote = SavedQuoteEvidence("DISPLAY_CONTEXT_CHANGED")
    inputs.values = [
        replace(p, retrieved_at=p.retrieved_at + timedelta(minutes=1)) for p in inputs.values
    ]
    refreshed, _ = await service.evaluate(**kwargs, now=inputs.now())
    # New IV evidence is auditable, but it does not create another confirmation day.
    assert refreshed.snapshot_id != baseline.snapshot_id
    assert refreshed.assessment.state == baseline.assessment.state
    assert refreshed.assessment.trend_triggered is None
    current_preview = await service.preview(**kwargs, now=inputs.now())
    assert current_preview.quote_evidence.reason == "DISPLAY_CONTEXT_CHANGED"
    assert refreshed.quote_evidence.reason == "DISPLAY_CONTEXT_CHANGED"
    for _ in range(2):
        inputs.append(80)
        crossed, alerts = await PositionRiskService(session, inputs).evaluate(
            **kwargs, now=inputs.now()
        )
    assert crossed.assessment.transition == "CROSSED_BELOW"
    trend = next(item for item in alerts if item.alert.alert_type.value == "RISK_TREND_CHANGED")
    assert trend.alert.market_data_observed_at is None
    assert trend.alert.price_context["snapshot_id"] == str(crossed.snapshot_id)
    notification_service = AlertNotificationService(
        notifications=SqlAlchemyNotificationRepository(session), new_id=uuid4, now=inputs.now
    )
    first = await notification_service.create_telegram(alert=trend.alert, symbol="TEST")
    await session.commit()
    _, replay = await PositionRiskService(session, inputs).evaluate(**kwargs, now=inputs.now())
    replay_trend = next(
        item for item in replay if item.alert.alert_type.value == "RISK_TREND_CHANGED"
    )
    second = await notification_service.create_telegram(alert=replay_trend.alert, symbol="TEST")
    assert first.id == second.id and "Messwert" in first.body
    # A document revision changes audit evidence, never a signal session or alert edge.
    alert_count = session.sync.scalar(select(func.count()).select_from(AlertModel))
    inputs.product = replace(
        inputs.product,
        evidence_revision=1,
        evidence_origin="MANUAL_DOCUMENT_REVIEW",
        evidence_document="Synthetic final terms",
        exercise_style="EUROPEAN",
        quanto=False,
        ratio_convention="UNDERLYING_UNITS_PER_WARRANT",
        product_type="VANILLA_WARRANT",
    )
    documented, replay = await service.evaluate(**kwargs, now=inputs.now())
    assert documented.snapshot_id != crossed.snapshot_id
    assert documented.basis_key == crossed.basis_key
    assert documented.assessment.state == crossed.assessment.state
    assert documented.iv.current_iv_decimal is documented.iv.risk_level is None
    assert session.sync.scalar(select(func.count()).select_from(AlertModel)) == alert_count
    documented_trend = next(item for item in replay if item.alert.id == trend.alert.id)
    third = await notification_service.create_telegram(alert=documented_trend.alert, symbol="TEST")
    assert third.id == first.id
    # A data failure creates a new audit record, preserving the active warning.
    original = inputs.values[-1]
    inputs.values[-1] = replace(original, adjusted_close=None)
    gap, _ = await service.evaluate(**kwargs, now=inputs.now())
    assert gap.assessment.state.trend_warning and gap.assessment.trend_triggered is None
    assert session.sync.get(AlertModel, trend.alert.id).status == "OPEN"
    inputs.values[-1] = original
    original_product = inputs.product
    inputs.product = replace(original_product, terms_id=None)
    missing_terms, _ = await service.evaluate(**kwargs, now=inputs.now())
    assert missing_terms.assessment.state.trend_warning
    assert missing_terms.basis_key == crossed.basis_key
    inputs.product = original_product
    for _ in range(2):
        inputs.append(120)
        recovered, _ = await service.evaluate(**kwargs, now=inputs.now())
    assert recovered.assessment.transition == "CROSSED_ABOVE"
    assert session.sync.get(AlertModel, trend.alert.id).status == "RESOLVED"
    # A new confirmed deterioration after recovery is a new alert, not a replay.
    for _ in range(2):
        inputs.append(80)
        _, new_alerts = await service.evaluate(**kwargs, now=inputs.now())
    new_trend = next(
        item for item in new_alerts if item.alert.alert_type.value == "RISK_TREND_CHANGED"
    )
    assert new_trend.alert.id != trend.alert.id
    history = await service.history(**kwargs)
    assert any(
        v.snapshot_id == crossed.snapshot_id and v.assessment.state.trend_warning for v in history
    )
    with pytest.raises(RiskConfigurationConflict):
        await service.configure(
            **kwargs,
            now=inputs.now(),
            parameters=RiskParameters(),
            enabled=False,
            expected_revision=0,
            actor=uuid4(),
            correlation_id=None,
        )
    config = await service.configure(
        **kwargs,
        now=inputs.now(),
        parameters=RiskParameters(),
        enabled=False,
        expected_revision=1,
        actor=uuid4(),
        correlation_id=None,
    )
    fresh, alerts = await service.evaluate(**kwargs, now=inputs.now())
    assert (
        fresh.configuration.revision == 2
        and fresh.assessment.transition == "INITIALIZED"
        and not alerts
    )
    assert session.sync.get(AlertModel, new_trend.alert.id).status == "INVALIDATED"
    assert session.sync.get(AlertModel, trend.alert.id).status == "RESOLVED"
    assert session.sync.get(PositionModel, ref.position_id).open_quantity == 10
    assert (
        await service.preview(workspace_id=uuid4(), trade_id=ref.trade_id, now=inputs.now()) is None
    )


@pytest.mark.asyncio
async def test_disabled_preview_correction_same_day_and_parameter_preview(stored):
    session, ref, inputs = stored
    service = PositionRiskService(session, inputs)
    kwargs = dict(workspace_id=ref.workspace_id, trade_id=ref.trade_id, now=inputs.now())
    first, _ = await service.evaluate(**kwargs)
    inputs.values[-1] = replace(
        inputs.values[-1],
        open=Decimal(80),
        high=Decimal(81),
        low=Decimal(79),
        close=Decimal(80),
        adjusted_close=Decimal(80),
    )
    correction, alerts = await service.evaluate(**kwargs)
    assert correction.snapshot_id != first.snapshot_id and not alerts
    assert correction.assessment.transition == "SAME_OR_OLDER_SESSION"
    preview = await service.preview(**kwargs, parameters=RiskParameters(confirmation_sessions=3))
    assert preview.assessment.transition == "INITIALIZED" and not preview.configuration.enabled
    assert len(await service.history(workspace_id=ref.workspace_id, trade_id=ref.trade_id)) == 2


@pytest.mark.asyncio
async def test_iv_evidence_storage_source_side_age_changes_do_not_add_alerts_or_sessions(stored):
    session, ref, inputs = stored
    service = PositionRiskService(session, inputs)
    kwargs = dict(workspace_id=ref.workspace_id, trade_id=ref.trade_id)
    now = inputs.now()
    await service.configure(
        **kwargs,
        now=now,
        parameters=RiskParameters(),
        enabled=True,
        expected_revision=0,
        actor=uuid4(),
        correlation_id=None,
    )
    quote = WarrantQuoteSnapshot(
        uuid4(), Decimal(2), Decimal("2.2"), "EUR", "SYN", "ISSUER", now, max_quote_age_seconds=60
    )
    inputs.quote = SavedQuoteEvidence("SAVED", quote, "SYN-A", now, "route-a")
    baseline, alerts = await service.evaluate(**kwargs, now=now)
    assert not alerts and baseline.iv.current_iv_decimal is None
    inputs.quote = replace(
        inputs.quote,
        retrieved_at=now + timedelta(seconds=1),
        quote=replace(quote, assessed_at=now + timedelta(seconds=1)),
    )
    same, alerts = await service.evaluate(**kwargs, now=now + timedelta(seconds=1))
    assert same.snapshot_id == baseline.snapshot_id and not alerts
    inputs.quote = replace(inputs.quote, provider="SYN-B", identity_key="route-b")
    changed, alerts = await service.evaluate(**kwargs, now=now + timedelta(seconds=2))
    assert changed.snapshot_id != baseline.snapshot_id and not alerts
    assert changed.assessment.state == baseline.assessment.state
    assert changed.assessment.transition == "SAME_OR_OLDER_SESSION"
    inputs.quote = replace(inputs.quote, quote=replace(quote, ask=None))
    partial, alerts = await service.evaluate(**kwargs, now=now + timedelta(seconds=3))
    assert partial.iv.quote_side == "BID_ONLY" and not alerts
    stale, alerts = await service.evaluate(**kwargs, now=now + timedelta(seconds=61))
    assert stale.snapshot_id != partial.snapshot_id and "QUOTE_STALE" in stale.iv.reasons
    assert not alerts and stale.assessment.state == baseline.assessment.state
    assert session.sync.scalar(select(func.count()).select_from(AlertModel)) == 0
    assert session.sync.scalar(select(func.count()).select_from(NotificationModel)) == 0
    history = await service.history(**kwargs)
    assert len(history) == 4
    assert {v.quote_evidence.provider for v in history} == {"SYN-A", "SYN-B"}
    assert session.sync.get(PositionModel, ref.position_id).open_quantity == 10
    old_payload = RISK_VIEW.dump_python(baseline, mode="json")
    old_payload.pop("iv")
    assert RISK_VIEW.validate_python(old_payload).iv is None  # No invented backfill.


@pytest.mark.asyncio
async def test_risk_http_contract_confirmation_preview_history_and_unknown_position(
    stored, monkeypatch
):
    from contextlib import asynccontextmanager
    from types import SimpleNamespace

    import httpx
    from fastapi import FastAPI

    from app.core.di import get_container
    from app.features.position_monitoring.api import risk as api

    session, ref, inputs = stored

    @asynccontextmanager
    async def scope():
        yield session

    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[get_container] = lambda: SimpleNamespace(
        database=SimpleNamespace(session_context=scope)
    )
    monkeypatch.setattr(api, "WORKSPACE_ID", ref.workspace_id)
    monkeypatch.setattr(api, "PositionRiskService", lambda s: PositionRiskService(s, inputs))

    # Pin the HTTP clock to the controlled source receipt.
    class Clock:
        @staticmethod
        def now(tz):
            return inputs.now()

    monkeypatch.setattr(api, "datetime", Clock)
    base = f"/trades/{ref.trade_id}/risk"
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(base)
        assert response.status_code == 200
        data = response.json()
        assert data["metrics"]["status"] == "AVAILABLE" and data["snapshot_id"] is None
        params = data["configuration"]["parameters"]
        for invalid in (
            {"confirmation_sessions": True},
            {"confirmation_sessions": 1.5},
            {"unexpected_parameter": 1},
        ):
            response = await client.post(
                base + "/preview", json={"parameters": {**params, **invalid}}
            )
            assert response.status_code == 422
        assert (await client.get(base + "/history")).json() == []
        proposed = await client.post(base + "/preview", json={"parameters": params})
        assert proposed.status_code == 200 and proposed.json()["mode"] == "PREVIEW"
        payload = dict(parameters=params, enabled=True, expected_revision=0)
        assert (await client.put(base + "/configuration", json=payload)).status_code == 422
        payload["confirmation"] = "CONFIRM_POSITION_RISK_CONFIGURATION"
        assert (await client.put(base + "/configuration", json=payload)).status_code == 200
        assert (await client.put(base + "/configuration", json=payload)).status_code == 409
        saved = await client.post(base + "/evaluations")
        assert saved.status_code == 200 and saved.json()["snapshot_id"]
        assert len((await client.get(base + "/history")).json()) == 1
        assert (await client.get(f"/trades/{uuid4()}/risk")).status_code == 404
        assert (
            await client.post(
                base + "/preview", json={"parameters": {**params, "volatility_high": "NaN"}}
            )
        ).status_code == 422
