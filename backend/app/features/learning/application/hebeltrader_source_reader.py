"""Narrow read of a confirmed historical Hebeltrader PDF version.

The import owner keeps the originals. This reader exposes only structured marks
and provenance, never article content, and never substitutes the latest issue.
Original source units are not evidence of a verified split adjustment.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.learning.domain.enums import ExternalObservationRecordingMethod
from app.features.learning.persistence.bulk_import_models import (
    ExternalObservationImportFileModel,
)
from app.features.learning.persistence.models import (
    ExternalObservationImportBatchModel,
    ExternalObservationImportRowModel,
    ExternalObservationModel,
    ExternalObservationTradeLinkRecordModel,
    ExternalObservationTradeLinkVersionRecordModel,
    ExternalObservationVersionModel,
)
from app.features.learning.persistence.repositories import (
    SqlAlchemyExternalObservationRepository,
    SqlAlchemyExternalObservationVersionRepository,
)
from app.features.trade_position.domain.price_binding import PriceBasis, PriceBinding


@dataclass(frozen=True, slots=True)
class SourcePriceMarks:
    binding: PriceBinding
    reference_price: Decimal
    target_1: Decimal
    target_2: Decimal
    stop_1: Decimal
    stop_2: Decimal
    scale: Literal["SOURCE_ORIGINAL"] = "SOURCE_ORIGINAL"


@dataclass(frozen=True, slots=True)
class ConfirmedHebeltraderSource:
    source_version_id: UUID
    observation_id: UUID
    version: int
    supersedes_version_id: UUID | None
    currentness: Literal["CURRENT_SOURCE", "SOURCE_SUPERSEDED"]
    product_id: UUID
    underlying_id: UUID
    underlying: SourcePriceMarks
    product: SourcePriceMarks
    issue_date: date
    # observed_at preserves the import's original metadata, which represents the
    # issue date at midnight. It is not a verified intraday publication instant.
    observed_at: datetime
    recorded_at: datetime
    imported_at: datetime
    source_name: str
    external_reference: str | None
    import_row_id: UUID
    batch_id: UUID
    file_id: UUID
    filename: str
    content_hash: str
    accepted_at: datetime
    accepted_by: UUID
    time_precision: Literal["DATE_ONLY"] = "DATE_ONLY"


@dataclass(frozen=True, slots=True)
class HebeltraderSourceEvidence:
    source_version_id: UUID
    source: ConfirmedHebeltraderSource | None
    reasons: tuple[str, ...] = ()

    @property
    def suitable(self) -> bool:
        return self.source is not None and not self.reasons


def _positive(payload: dict[str, object], key: str) -> Decimal:
    value = payload.get(key)
    if not isinstance(value, (str, int, Decimal)) or isinstance(value, bool):
        raise ValueError(key)
    result = Decimal(value)
    if not result.is_finite() or result <= 0:
        raise ValueError(key)
    return result


def _marks(
    payload: dict[str, object], *, prefix: str, basis: PriceBasis, instrument_id: UUID
) -> SourcePriceMarks:
    currency = payload.get(f"{prefix}_currency")
    if not isinstance(currency, str):
        raise ValueError("currency")
    return SourcePriceMarks(
        binding=PriceBinding(basis, instrument_id, currency),
        reference_price=_positive(
            payload,
            ("underlying_price" if prefix == "underlying" else "derivative_indicated_price"),
        ),
        target_1=_positive(payload, f"{prefix}_target_1"),
        target_2=_positive(payload, f"{prefix}_target_2"),
        stop_1=_positive(payload, f"{prefix}_stop_1"),
        stop_2=_positive(payload, f"{prefix}_stop_2"),
    )


class HebeltraderSourceReader:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def read(
        self,
        *,
        workspace_id: UUID,
        source_version_id: UUID,
        product_id: UUID,
        underlying_id: UUID,
    ) -> HebeltraderSourceEvidence:
        def unavailable(reason: str) -> HebeltraderSourceEvidence:
            return HebeltraderSourceEvidence(source_version_id, None, (reason,))

        # The existing version repository reads exact IDs; its workspace guard
        # belongs to the observation root and must be checked before projection.
        try:
            source = await SqlAlchemyExternalObservationVersionRepository(self._session).get(
                source_version_id
            )
        except ValueError:
            # A structurally invalid historical import is not a valid source.
            # Database/read failures still propagate as unavailable, never missing.
            return unavailable("NOT_CONFIRMED_PDF")
        if source is None:
            return unavailable("NOT_FOUND")
        observation = await SqlAlchemyExternalObservationRepository(self._session).get(
            workspace_id, source.external_observation_id
        )
        if observation is None:
            return unavailable("NOT_FOUND")
        if (source.product_id, source.underlying_id) != (product_id, underlying_id):
            return unavailable("IDENTITY_MISMATCH")
        if (
            source.recording_method is not ExternalObservationRecordingMethod.FILE_IMPORT
            or source.source_name != "HEBELTRADER"
            or source.source_type != "NEWSLETTER_RECOMMENDATION"
            or source.import_row_id is None
            or source.imported_at is None
        ):
            return unavailable("NOT_CONFIRMED_PDF")

        row = await self._session.scalar(
            select(ExternalObservationImportRowModel).where(
                ExternalObservationImportRowModel.id == source.import_row_id,
                ExternalObservationImportRowModel.workspace_id == workspace_id,
            )
        )
        if (
            row is None
            or row.disposition != "ACCEPTED"
            or row.validation_status != "VALID"
            or row.accepted_external_observation_version_id != source_version_id
            or row.disposed_at is None
            or row.disposed_by is None
        ):
            return unavailable("NOT_CONFIRMED_PDF")
        if (row.resolved_product_id, row.resolved_underlying_id) != (
            product_id,
            underlying_id,
        ):
            return unavailable("IDENTITY_MISMATCH")
        batch = await self._session.scalar(
            select(ExternalObservationImportBatchModel).where(
                ExternalObservationImportBatchModel.id == row.batch_id,
                ExternalObservationImportBatchModel.workspace_id == workspace_id,
            )
        )
        payload = source.source_metadata
        if not isinstance(payload, dict):
            return unavailable("PROVENANCE_MISMATCH")
        provenance = payload.get("source_file")
        if not isinstance(provenance, dict):
            return unavailable("PROVENANCE_MISMATCH")
        try:
            file_id = UUID(str(provenance.get("file_id")))
        except (ValueError, AttributeError):
            return unavailable("PROVENANCE_MISMATCH")
        file = await self._session.scalar(
            select(ExternalObservationImportFileModel).where(
                ExternalObservationImportFileModel.id == file_id,
                ExternalObservationImportFileModel.workspace_id == workspace_id,
            )
        )
        if (
            batch is None
            or file is None
            or file.import_batch_id != row.batch_id
            or file.status != "COMPLETED"
            or provenance.get("batch_id") != str(batch.id)
            or provenance.get("filename") != batch.original_filename
            or file.original_filename != batch.original_filename
            or provenance.get("content_hash") != batch.content_hash
            or file.content_hash != batch.content_hash
            or re.fullmatch(r"[0-9a-fA-F]{64}", batch.content_hash) is None
            or {key: value for key, value in payload.items() if key != "source_file"}
            != row.raw_payload
        ):
            return unavailable("PROVENANCE_MISMATCH")
        try:
            issue = payload.get("issue_date")
            if not isinstance(issue, str) or re.fullmatch(r"\d{4}-\d{2}-\d{2}", issue) is None:
                raise ValueError("issue date")
            issue_date = date.fromisoformat(issue)
            underlying = _marks(
                payload,
                prefix="underlying",
                basis=PriceBasis.UNDERLYING,
                instrument_id=underlying_id,
            )
            product = _marks(
                payload,
                prefix="derivative",
                basis=PriceBasis.WARRANT,
                instrument_id=product_id,
            )
        except (ValueError, InvalidOperation):
            return unavailable("INVALID_MARKS")
        return HebeltraderSourceEvidence(
            source_version_id,
            ConfirmedHebeltraderSource(
                source_version_id=source_version_id,
                observation_id=observation.id,
                version=source.version,
                supersedes_version_id=source.supersedes_version_id,
                currentness=(
                    "CURRENT_SOURCE"
                    if observation.current_version_id == source_version_id
                    else "SOURCE_SUPERSEDED"
                ),
                product_id=product_id,
                underlying_id=underlying_id,
                underlying=underlying,
                product=product,
                issue_date=issue_date,
                observed_at=source.observed_at,
                recorded_at=source.recorded_at,
                imported_at=source.imported_at,
                source_name=source.source_name,
                external_reference=source.external_reference,
                import_row_id=row.id,
                batch_id=batch.id,
                file_id=file.id,
                filename=batch.original_filename,
                content_hash=batch.content_hash,
                accepted_at=row.disposed_at,
                accepted_by=row.disposed_by,
            ),
        )

    async def find_trade_source(self, *, workspace_id: UUID, trade_id: UUID) -> UUID | None:
        """Reuse an unchanged initial TradeLink pin, never a refreshed source.

        Several distinct historical pins require clarification. This method does
        not choose a recommendation by date, underlying or product similarity.
        An amended link requires an explicit evidence declaration even when its
        current target still matches. The caller first resolves the trade through
        its execution owner. No persisted evidence revision uses this fallback.
        """
        link = ExternalObservationTradeLinkRecordModel
        version = ExternalObservationTradeLinkVersionRecordModel
        source = ExternalObservationVersionModel
        observation = ExternalObservationModel
        versions = (
            await self._session.scalars(
                select(version)
                .join(
                    link,
                    (link.current_version_id == version.id)
                    & (link.id == version.external_observation_trade_link_id),
                )
                .join(source, source.id == version.external_observation_version_id)
                .join(observation, observation.id == source.external_observation_id)
                .where(
                    link.workspace_id == workspace_id,
                    observation.workspace_id == workspace_id,
                    link.external_observation_id == observation.id,
                    version.trade_id == trade_id,
                    version.status == "ACTIVE",
                    source.source_name == "HEBELTRADER",
                    source.source_type == "NEWSLETTER_RECOMMENDATION",
                )
            )
        ).all()
        if any(value.version != 1 or value.change_reason != "INITIAL_LINK" for value in versions):
            return None
        ids = {value.external_observation_version_id for value in versions}
        return next(iter(ids)) if len(ids) == 1 else None
