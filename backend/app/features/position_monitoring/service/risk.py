"""Qualified risk snapshots and explicitly confirmed, append-only activation."""

import hashlib
from dataclasses import replace
from datetime import datetime
from uuid import UUID, uuid4

from pydantic import TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.alert.service.risk_lifecycle import invalidate_risk_alerts
from app.features.analysis.domain.product_comparison import ProductComparison, compare_product
from app.features.analysis.domain.risk_analytics import RiskMetrics, risk_metrics
from app.features.position_monitoring.domain.quote_quality import qualify_quote
from app.features.position_monitoring.domain.risk_signals import RiskParameters, assess_risk
from app.features.position_monitoring.persistence.models import PositionRiskConfigurationModel
from app.features.position_monitoring.persistence.risk_records import (
    RISK_PARAMETERS,
    RiskRecordRepository,
)
from app.features.position_monitoring.service.cycle import CreatedPositionAlert
from app.features.position_monitoring.service.risk_alerts import RiskAlertService
from app.features.position_monitoring.service.risk_contracts import (
    PositionRiskView,
    RiskConfiguration,
)
from app.features.position_monitoring.service.risk_inputs import (
    PersistedRiskInputReader,
    RiskInputReader,
    RiskInputs,
)
from app.features.trade_position.service.open_position_reader import (
    OpenPositionReader,
    OpenPositionReference,
)

INPUTS = TypeAdapter(RiskInputs)


class RiskConfigurationConflict(ValueError):
    pass


class PositionRiskService:
    def __init__(self, session: AsyncSession, inputs: RiskInputReader | None = None) -> None:
        self._session = session
        self._positions = OpenPositionReader(session)
        self._records = RiskRecordRepository(session)
        self._inputs = inputs or PersistedRiskInputReader(session)

    async def preview(
        self,
        *,
        workspace_id: UUID,
        trade_id: UUID,
        now: datetime,
        parameters: RiskParameters | None = None,
    ) -> PositionRiskView | None:
        position = await self._positions.read(workspace_id=workspace_id, trade_id=trade_id)
        if position is None:
            return None
        config = await self._records.configuration(position.position_id)
        if parameters is not None:
            # A proposed parameter set is never allowed to inherit an active alert state.
            config = replace(config, enabled=False, parameters=parameters)
        return await self._calculate(position, config, now, inherit=parameters is None)

    async def evaluate(
        self, *, workspace_id: UUID, trade_id: UUID, now: datetime
    ) -> tuple[PositionRiskView | None, tuple[CreatedPositionAlert, ...]]:
        position = await self._positions.read(
            workspace_id=workspace_id, trade_id=trade_id, lock=True
        )
        if position is None:
            return None, ()
        config = await self._records.configuration(position.position_id)
        view = await self._calculate(position, config, now)
        existing = await self._records.identical(position.position_id, view.input_fingerprint)
        if existing is not None:
            alerts = await RiskAlertService(self._session).process(view, evaluate=False)
            await self._session.commit()
            return existing, alerts
        view = replace(view, snapshot_id=uuid4(), mode="STORED")
        self._records.add_snapshot(workspace_id, view)
        alerts = await RiskAlertService(self._session).process(view)
        await self._session.commit()
        return view, alerts

    async def configure(
        self,
        *,
        workspace_id: UUID,
        trade_id: UUID,
        now: datetime,
        parameters: RiskParameters,
        enabled: bool,
        expected_revision: int,
        actor: UUID,
        correlation_id: str | None,
    ) -> RiskConfiguration | None:
        position = await self._positions.read(
            workspace_id=workspace_id, trade_id=trade_id, lock=True
        )
        if position is None:
            return None
        old = await self._records.configuration(position.position_id)
        if old.revision != expected_revision:
            raise RiskConfigurationConflict("Configuration changed; reload before confirming")
        config = RiskConfiguration(old.revision + 1, enabled, parameters, now, actor)
        self._session.add(
            PositionRiskConfigurationModel(
                id=uuid4(),
                workspace_id=workspace_id,
                position_id=position.position_id,
                revision=config.revision,
                enabled=enabled,
                policy_version=config.policy_version,
                parameters=RISK_PARAMETERS.dump_python(parameters, mode="json"),
                configured_at=now,
                actor=actor,
                correlation_id=correlation_id,
            )
        )
        await invalidate_risk_alerts(self._session, position_id=position.position_id, now=now)
        await self._session.commit()
        return config

    async def history(
        self, *, workspace_id: UUID, trade_id: UUID
    ) -> tuple[PositionRiskView, ...] | None:
        position = await self._positions.read(workspace_id=workspace_id, trade_id=trade_id)
        return await self._records.history(position.position_id) if position else None

    async def _calculate(
        self,
        position: OpenPositionReference,
        config: RiskConfiguration,
        now: datetime,
        *,
        inherit: bool = True,
    ) -> PositionRiskView:
        inputs = await self._inputs.read(position, now)
        product, listing = inputs.product, inputs.listing
        metrics = risk_metrics(
            inputs.prices, as_of=now, max_age_days=config.parameters.maximum_age_days
        )
        if product is None or listing is None:
            metrics = RiskMetrics("NOT_EVALUABLE", "PRODUCT_TERMS_OR_PRIMARY_LISTING_MISSING")
        elif any(
            p.listing_id != listing.listing_id or p.currency != listing.currency
            for p in inputs.prices
        ):
            metrics = RiskMetrics("NOT_EVALUABLE", "POSITION_SERIES_IDENTITY_MISMATCH")
        basis = hashlib.sha256(
            str(
                (
                    position.warrant_id,
                    product.terms_id if product else None,
                    product.direction if product else None,
                    listing,
                    (
                        (
                            inputs.prices[-1].provider.value,
                            inputs.prices[-1].provider_symbol,
                            inputs.prices[-1].market_data_instrument_id,
                        )
                        if inputs.prices
                        else None
                    ),
                )
            ).encode()
        ).hexdigest()
        last = (
            await self._records.latest(position.position_id, config.revision) if inherit else None
        )
        previous = (
            last.assessment.state
            if last and (last.basis_key == basis or metrics.status != "AVAILABLE")
            else None
        )
        assessment = assess_risk(
            metrics,
            direction=product.direction if product else None,
            parameters=config.parameters,
            previous=previous,
        )
        comparison = compare_product(inputs.synchronized_pairs, as_of=now)
        if not inputs.synchronized_pairs:
            comparison = ProductComparison("NOT_EVALUABLE", inputs.comparison_limits)
        elif (
            product is None
            or listing is None
            or any(
                p.warrant_id != position.warrant_id
                or p.underlying_id != product.underlying_id
                or p.underlying_listing_id != listing.listing_id
                or p.terms_id != product.terms_id
                or p.direction != product.direction
                or p.ratio != product.ratio
                or p.underlying_currency != listing.currency
                for p in inputs.synchronized_pairs
            )
        ):
            comparison = ProductComparison("NOT_EVALUABLE", ("POSITION_PRODUCT_IDENTITY_MISMATCH",))
        quote = inputs.quote
        if product and quote.quote and quote.quote.isin != product.isin:
            quote = replace(quote, quote=None, reason="POSITION_QUOTE_IDENTITY_MISMATCH")
        # Stable input identity excludes evaluation clock/state; repeated polls do not
        # append duplicate snapshots. A new quality failure is nevertheless auditable.
        fingerprint = hashlib.sha256(
            INPUTS.dump_json(inputs)
            + RISK_PARAMETERS.dump_json(config.parameters)
            + str((config.revision, basis, metrics.status, metrics.reason)).encode()
        ).hexdigest()
        return PositionRiskView(
            position.trade_id,
            position.position_id,
            now,
            config,
            product,
            listing,
            metrics,
            assessment,
            qualify_quote(quote, as_of=now),
            comparison,
            fingerprint,
            basis,
            inputs.prices,
            previous_snapshot_id=last.snapshot_id if last else None,
        )
