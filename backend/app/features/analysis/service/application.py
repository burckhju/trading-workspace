"""Application orchestration for FT-006 market analysis."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.analysis.domain.calculator import MODEL_ID, MODEL_VERSION, calculate
from app.features.analysis.domain.enums import (
    AnalysisQualityStatus,
    AnalysisStatus,
    PriceField,
)
from app.features.analysis.domain.errors import (
    AnalysisConflict,
    AnalysisDataUnavailable,
    AnalysisExecutionFailed,
    AnalysisNotFound,
)
from app.features.analysis.domain.lifecycle import (
    ensure_retryable,
    ensure_supersedeable,
    validate_transition,
)
from app.features.analysis.domain.models import (
    AnalysisParameters,
    SnapshotRow,
    calculate_input_hash,
)
from app.features.analysis.persistence.models import (
    MarketAnalysisCriterionModel,
    MarketAnalysisEventModel,
    MarketAnalysisModel,
    MarketAnalysisRunModel,
    MarketAnalysisSnapshotRowModel,
)
from app.features.analysis.persistence.repositories import (
    AnalysisOverviewFilter,
    AnalysisOverviewRow,
    SqlAlchemyAnalysisMarketDataReader,
    SqlAlchemyAnalysisReferenceReader,
    SqlAlchemyAnalysisRepository,
)


class MarketAnalysisService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = SqlAlchemyAnalysisRepository(session)
        self._references = SqlAlchemyAnalysisReferenceReader(session)
        self._market_data = SqlAlchemyAnalysisMarketDataReader(session)

    async def create(
        self,
        workspace_id: UUID,
        underlying_id: UUID,
        listing_id: UUID,
        actor: str,
    ) -> MarketAnalysisModel:
        if not await self._references.validate_reference(workspace_id, underlying_id, listing_id):
            raise AnalysisDataUnavailable("underlying/listing reference is invalid")
        now = datetime.now(UTC)
        model = MarketAnalysisModel(
            id=uuid4(),
            workspace_id=workspace_id,
            underlying_id=underlying_id,
            listing_id=listing_id,
            created_at=now,
            created_by=actor,
        )
        await self._repo.add_analysis(model)
        await self._repo.add_event(
            MarketAnalysisEventModel(
                id=uuid4(),
                analysis_id=model.id,
                run_id=None,
                version=None,
                event_type="CREATED",
                from_status=None,
                to_status=AnalysisStatus.DRAFT.value,
                source_version=None,
                replacement_version=None,
                reason=None,
                correlation_id=None,
                occurred_at=now,
            )
        )
        await self._session.commit()
        return model

    async def run(
        self,
        workspace_id: UUID,
        analysis_id: UUID,
        start_date: date,
        end_date: date,
        parameters: AnalysisParameters,
        correlation_id: str | None,
    ) -> MarketAnalysisRunModel:
        analysis = await self._require_analysis(workspace_id, analysis_id)
        prices = await self._market_data.list_daily_prices(
            workspace_id, analysis.listing_id, start_date, end_date
        )
        if not prices:
            raise AnalysisDataUnavailable("no persisted market data in requested range")
        rows = tuple(
            SnapshotRow(
                p.trading_date,
                p.open,
                p.high,
                p.low,
                p.close,
                p.adjusted_close,
                p.volume,
                p.currency,
                p.provider.value,
                p.provider_symbol,
                p.quality_status.value,
                p.warnings,
            )
            for p in prices
        )
        return await self._execute_snapshot(
            analysis_id=analysis_id,
            parameters=parameters,
            rows=rows,
            correlation_id=correlation_id,
            source_version=None,
        )

    async def retry(
        self,
        workspace_id: UUID,
        analysis_id: UUID,
        version: int,
        correlation_id: str | None,
        reason: str | None,
    ) -> MarketAnalysisRunModel:
        await self._require_analysis(workspace_id, analysis_id)
        source = await self._require_run(analysis_id, version)
        source_status = AnalysisStatus(source.status)
        ensure_retryable(source_status)
        if await self._repo.get_supersede_event(analysis_id, version) is not None:
            raise AnalysisConflict("analysis run is already superseded")
        snapshot = await self._repo.list_snapshot(source.id)
        if not snapshot:
            raise AnalysisDataUnavailable("retry requires a persisted source snapshot")
        rows = tuple(self._snapshot_to_domain(item) for item in snapshot)
        parameters = self._parameters_from_dict(source.parameters)
        if source.model_id != MODEL_ID or source.model_version != MODEL_VERSION:
            raise AnalysisConflict(
                f"analysis model {source.model_id} {source.model_version} "
                "is not available for retry"
            )
        replacement = await self._execute_snapshot(
            analysis_id=analysis_id,
            parameters=parameters,
            rows=rows,
            correlation_id=correlation_id,
            source_version=version,
            model_id=source.model_id,
            model_version=source.model_version,
        )
        await self._append_superseded_event(
            analysis_id=analysis_id,
            source=source,
            replacement=replacement,
            correlation_id=correlation_id,
            reason=reason or f"Replaced by retry version {replacement.version}",
        )
        await self._session.commit()
        return replacement

    async def supersede(
        self,
        workspace_id: UUID,
        analysis_id: UUID,
        version: int,
        replacement_version: int,
        correlation_id: str | None,
        reason: str | None,
    ) -> MarketAnalysisEventModel:
        await self._require_analysis(workspace_id, analysis_id)
        if replacement_version <= version:
            raise AnalysisConflict("replacement version must be newer than source version")
        source = await self._require_run(analysis_id, version)
        replacement = await self._require_run(analysis_id, replacement_version)
        replacement_status = AnalysisStatus(replacement.status)
        if replacement_status not in {
            AnalysisStatus.COMPLETED,
            AnalysisStatus.COMPLETED_WITH_WARNINGS,
            AnalysisStatus.NOT_EVALUABLE,
        }:
            raise AnalysisConflict(
                f"analysis version with status {replacement_status.value} cannot be a replacement"
            )
        if await self._repo.get_supersede_event(analysis_id, version) is not None:
            raise AnalysisConflict("analysis run is already superseded")
        event = await self._append_superseded_event(
            analysis_id=analysis_id,
            source=source,
            replacement=replacement,
            correlation_id=correlation_id,
            reason=reason,
        )
        await self._session.commit()
        return event

    async def verify_reproducibility(
        self, workspace_id: UUID, analysis_id: UUID, version: int
    ) -> dict[str, bool]:
        await self._require_analysis(workspace_id, analysis_id)
        run = await self._require_run(analysis_id, version)
        snapshot = await self._repo.list_snapshot(run.id)
        if not snapshot:
            raise AnalysisDataUnavailable(
                "reproducibility verification requires a persisted snapshot"
            )
        rows = tuple(self._snapshot_to_domain(item) for item in snapshot)
        parameters = self._parameters_from_dict(run.parameters)
        model_available = run.model_id == MODEL_ID and run.model_version == MODEL_VERSION
        hash_matches = (
            calculate_input_hash(run.model_id, run.model_version, parameters, rows)
            == run.input_hash
        )
        if not model_available:
            return {
                "verified": False,
                "model_available": False,
                "input_hash_matches": hash_matches,
                "metrics_match": False,
                "criteria_match": False,
                "quality_status_match": False,
                "notes_match": False,
            }
        computation = calculate(parameters, rows)
        quality = computation.quality_status
        notes = list(computation.notes)
        stale = (
            run.analysis_time.date() - rows[-1].trading_date
        ).days > parameters.maximum_data_age_days
        if stale:
            notes.append("Latest market data exceeds maximum_data_age_days")
            if quality is AnalysisQualityStatus.GOOD:
                quality = AnalysisQualityStatus.LIMITED
        stored_criteria = await self._repo.list_criteria(run.id)
        expected_criteria = tuple(
            (item.code, item.classification.value, item.value, item.explanation)
            for item in computation.criteria
        )
        actual_criteria = tuple(
            (item.code, item.classification, item.value, item.explanation)
            for item in stored_criteria
        )
        checks = {
            "model_available": True,
            "input_hash_matches": hash_matches,
            "metrics_match": computation.metrics == run.metrics,
            "criteria_match": expected_criteria == actual_criteria,
            "quality_status_match": quality.value == run.quality_status,
            "notes_match": notes == run.notes,
        }
        return {"verified": all(checks.values()), **checks}

    async def events(
        self, workspace_id: UUID, analysis_id: UUID
    ) -> tuple[MarketAnalysisEventModel, ...]:
        await self._require_analysis(workspace_id, analysis_id)
        return await self._repo.list_events(analysis_id)

    async def get(
        self, workspace_id: UUID, analysis_id: UUID
    ) -> tuple[MarketAnalysisModel, tuple[MarketAnalysisRunModel, ...]]:
        analysis = await self._require_analysis(workspace_id, analysis_id)
        return analysis, await self._repo.list_runs(analysis_id)

    async def list(self, workspace_id: UUID) -> tuple[MarketAnalysisModel, ...]:
        return await self._repo.list_analyses(workspace_id)

    async def overview(
        self,
        workspace_id: UUID,
        offset: int,
        limit: int,
        filters: AnalysisOverviewFilter,
    ) -> tuple[tuple[AnalysisOverviewRow, ...], int]:
        return (
            await self._repo.list_analysis_overview(workspace_id, offset, limit, filters),
            await self._repo.count_analysis_overview(workspace_id, filters),
        )

    async def details(
        self,
        workspace_id: UUID,
        analysis_id: UUID,
        version: int,
        include_snapshot: bool = True,
    ) -> tuple[
        MarketAnalysisModel,
        MarketAnalysisRunModel,
        tuple[MarketAnalysisCriterionModel, ...],
        tuple[MarketAnalysisSnapshotRowModel, ...],
    ]:
        analysis = await self._require_analysis(workspace_id, analysis_id)
        run = await self._require_run(analysis_id, version)
        snapshot = await self._repo.list_snapshot(run.id) if include_snapshot else ()
        return analysis, run, await self._repo.list_criteria(run.id), snapshot

    async def snapshot(
        self,
        workspace_id: UUID,
        analysis_id: UUID,
        version: int,
        offset: int,
        limit: int,
    ) -> tuple[tuple[MarketAnalysisSnapshotRowModel, ...], int]:
        await self._require_analysis(workspace_id, analysis_id)
        run = await self._require_run(analysis_id, version)
        return await self._repo.list_snapshot(
            run.id, offset, limit
        ), await self._repo.count_snapshot(run.id)

    async def _execute_snapshot(
        self,
        *,
        analysis_id: UUID,
        parameters: AnalysisParameters,
        rows: tuple[SnapshotRow, ...],
        correlation_id: str | None,
        source_version: int | None,
        model_id: str = MODEL_ID,
        model_version: str = MODEL_VERSION,
    ) -> MarketAnalysisRunModel:
        latest = await self._repo.get_latest_run(analysis_id)
        if latest is not None and AnalysisStatus(latest.status) is AnalysisStatus.RUNNING:
            raise AnalysisConflict("another analysis execution is already running")
        version = await self._repo.next_version(analysis_id)
        now = datetime.now(UTC)
        validate_transition(AnalysisStatus.DRAFT, AnalysisStatus.RUNNING)
        run = MarketAnalysisRunModel(
            id=uuid4(),
            analysis_id=analysis_id,
            version=version,
            status=AnalysisStatus.RUNNING.value,
            quality_status=AnalysisQualityStatus.INSUFFICIENT.value,
            model_id=model_id,
            model_version=model_version,
            parameters=parameters.as_dict(),
            metrics={},
            notes=[],
            data_sources=sorted({row.provider for row in rows}),
            input_hash=calculate_input_hash(model_id, model_version, parameters, rows),
            observation_count=len(rows),
            analysis_time=now,
            correlation_id=correlation_id,
            error_message=None,
        )
        await self._repo.add_run(run)
        await self._repo.add_snapshot_rows(
            [
                MarketAnalysisSnapshotRowModel(
                    id=uuid4(),
                    run_id=run.id,
                    trading_date=row.trading_date,
                    open=row.open,
                    high=row.high,
                    low=row.low,
                    close=row.close,
                    adjusted_close=row.adjusted_close,
                    volume=row.volume,
                    currency=row.currency,
                    provider=row.provider,
                    provider_symbol=row.provider_symbol,
                    quality_status=row.quality_status,
                    warnings=list(row.warnings),
                )
                for row in rows
            ]
        )
        await self._repo.add_event(
            self._event(
                analysis_id=analysis_id,
                run_id=run.id,
                version=version,
                event_type="STARTED",
                from_status=AnalysisStatus.DRAFT,
                to_status=AnalysisStatus.RUNNING,
                correlation_id=correlation_id,
                source_version=source_version,
            )
        )
        # Persist RUNNING and the exact input snapshot before computation.
        # Only RUNNING rows may mutate.
        await self._session.commit()

        try:
            computation = calculate(parameters, rows)
            stale = (
                run.analysis_time.date() - rows[-1].trading_date
            ).days > parameters.maximum_data_age_days
            notes = list(computation.notes)
            quality = computation.quality_status
            if stale:
                notes.append("Latest market data exceeds maximum_data_age_days")
                if quality is AnalysisQualityStatus.GOOD:
                    quality = AnalysisQualityStatus.LIMITED
            target = (
                AnalysisStatus.NOT_EVALUABLE
                if quality is AnalysisQualityStatus.INSUFFICIENT
                else (
                    AnalysisStatus.COMPLETED_WITH_WARNINGS
                    if notes or quality is AnalysisQualityStatus.LIMITED
                    else AnalysisStatus.COMPLETED
                )
            )
            validate_transition(AnalysisStatus.RUNNING, target)
            run.status = target.value
            run.quality_status = quality.value
            run.metrics = computation.metrics
            run.notes = notes
            await self._repo.add_criteria(
                [
                    MarketAnalysisCriterionModel(
                        id=uuid4(),
                        run_id=run.id,
                        code=item.code,
                        classification=item.classification.value,
                        value=item.value,
                        explanation=item.explanation,
                    )
                    for item in computation.criteria
                ]
            )
            await self._repo.add_event(
                self._event(
                    analysis_id=analysis_id,
                    run_id=run.id,
                    version=version,
                    event_type="FINISHED",
                    from_status=AnalysisStatus.RUNNING,
                    to_status=target,
                    correlation_id=correlation_id,
                    source_version=source_version,
                )
            )
            await self._session.commit()
            return run
        except Exception as exc:
            validate_transition(AnalysisStatus.RUNNING, AnalysisStatus.FAILED)
            run.status = AnalysisStatus.FAILED.value
            run.error_message = str(exc)
            await self._repo.add_event(
                self._event(
                    analysis_id=analysis_id,
                    run_id=run.id,
                    version=version,
                    event_type="FAILED",
                    from_status=AnalysisStatus.RUNNING,
                    to_status=AnalysisStatus.FAILED,
                    correlation_id=correlation_id,
                    source_version=source_version,
                    reason=str(exc),
                )
            )
            await self._session.commit()
            raise AnalysisExecutionFailed(f"analysis execution failed: {exc}") from exc

    async def _append_superseded_event(
        self,
        *,
        analysis_id: UUID,
        source: MarketAnalysisRunModel,
        replacement: MarketAnalysisRunModel,
        correlation_id: str | None,
        reason: str | None,
    ) -> MarketAnalysisEventModel:
        source_status = AnalysisStatus(source.status)
        ensure_supersedeable(source_status)
        validate_transition(source_status, AnalysisStatus.SUPERSEDED)
        event = self._event(
            analysis_id=analysis_id,
            run_id=source.id,
            version=source.version,
            event_type="SUPERSEDED",
            from_status=source_status,
            to_status=AnalysisStatus.SUPERSEDED,
            correlation_id=correlation_id,
            source_version=source.version,
            replacement_version=replacement.version,
            reason=reason,
        )
        await self._repo.add_event(event)
        return event

    async def _require_analysis(self, workspace_id: UUID, analysis_id: UUID) -> MarketAnalysisModel:
        analysis = await self._repo.get_analysis(workspace_id, analysis_id)
        if analysis is None:
            raise AnalysisNotFound("analysis not found")
        return analysis

    async def _require_run(self, analysis_id: UUID, version: int) -> MarketAnalysisRunModel:
        run = await self._repo.get_run(analysis_id, version)
        if run is None:
            raise AnalysisNotFound("analysis version not found")
        return run

    @staticmethod
    def _parameters_from_dict(value: dict[str, Any]) -> AnalysisParameters:
        return AnalysisParameters(
            price_field=PriceField(value["price_field"]),
            short_window=int(value["short_window"]),
            medium_window=int(value["medium_window"]),
            long_window=int(value["long_window"]),
            momentum_windows=tuple(int(item) for item in value["momentum_windows"]),
            volatility_window=int(value["volatility_window"]),
            range_window=int(value["range_window"]),
            minimum_required_observations=int(value["minimum_required_observations"]),
            maximum_data_age_days=int(value["maximum_data_age_days"]),
            annualization_factor=Decimal(str(value["annualization_factor"])),
            rounding_scale=int(value["rounding_scale"]),
        )

    @staticmethod
    def _snapshot_to_domain(item: MarketAnalysisSnapshotRowModel) -> SnapshotRow:
        return SnapshotRow(
            trading_date=item.trading_date,
            open=item.open,
            high=item.high,
            low=item.low,
            close=item.close,
            adjusted_close=item.adjusted_close,
            volume=item.volume,
            currency=item.currency,
            provider=item.provider,
            provider_symbol=item.provider_symbol,
            quality_status=item.quality_status,
            warnings=tuple(item.warnings),
        )

    @staticmethod
    def _event(
        *,
        analysis_id: UUID,
        run_id: UUID | None,
        version: int | None,
        event_type: str,
        from_status: AnalysisStatus | None,
        to_status: AnalysisStatus,
        correlation_id: str | None,
        source_version: int | None = None,
        replacement_version: int | None = None,
        reason: str | None = None,
    ) -> MarketAnalysisEventModel:
        return MarketAnalysisEventModel(
            id=uuid4(),
            analysis_id=analysis_id,
            run_id=run_id,
            version=version,
            event_type=event_type,
            from_status=None if from_status is None else from_status.value,
            to_status=to_status.value,
            source_version=source_version,
            replacement_version=replacement_version,
            reason=reason,
            correlation_id=correlation_id,
            occurred_at=datetime.now(UTC),
        )
