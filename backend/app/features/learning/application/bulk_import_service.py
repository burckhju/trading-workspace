"""Application orchestration for bulk Hebeltrader imports."""

from __future__ import annotations

import hashlib
from dataclasses import asdict
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.learning.application.hebeltrader_parser import (
    HebeltraderParseError,
    HebeltraderRecommendation,
    parse_hebeltrader_pdf,
)
from app.features.learning.persistence.bulk_import_models import (
    ExternalObservationImportFileModel,
    ExternalObservationImportJobModel,
)
from app.features.learning.persistence.models import (
    ExternalObservationImportBatchModel,
    ExternalObservationImportRowModel,
)
from app.features.market.persistence.models import UnderlyingModel
from app.features.product.persistence.models import WarrantModel


class BulkImportError(ValueError):
    """Raised for invalid bulk-import application commands."""


class ExternalObservationBulkImportService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_job(self, workspace_id: UUID, actor_id: UUID) -> ExternalObservationImportJobModel:
        now = datetime.now(UTC)
        job = ExternalObservationImportJobModel(
            id=uuid4(),
            workspace_id=workspace_id,
            status="OPEN",
            created_at=now,
            created_by=actor_id,
            updated_at=now,
        )
        self._session.add(job)
        await self._session.commit()
        return job

    async def get_job(self, workspace_id: UUID, job_id: UUID) -> ExternalObservationImportJobModel:
        job = await self._session.scalar(
            select(ExternalObservationImportJobModel).where(
                ExternalObservationImportJobModel.id == job_id,
                ExternalObservationImportJobModel.workspace_id == workspace_id,
            )
        )
        if job is None:
            raise BulkImportError("import job does not exist in workspace")
        return job

    async def list_files(
        self, workspace_id: UUID, job_id: UUID
    ) -> list[ExternalObservationImportFileModel]:
        await self.get_job(workspace_id, job_id)
        rows = await self._session.scalars(
            select(ExternalObservationImportFileModel)
            .where(
                ExternalObservationImportFileModel.job_id == job_id,
                ExternalObservationImportFileModel.workspace_id == workspace_id,
            )
            .order_by(ExternalObservationImportFileModel.created_at, ExternalObservationImportFileModel.id)
        )
        return list(rows)

    async def list_review_rows(
        self, workspace_id: UUID, job_id: UUID
    ) -> list[ExternalObservationImportRowModel]:
        await self.get_job(workspace_id, job_id)
        rows = await self._session.scalars(
            select(ExternalObservationImportRowModel)
            .join(
                ExternalObservationImportFileModel,
                ExternalObservationImportFileModel.import_batch_id
                == ExternalObservationImportRowModel.batch_id,
            )
            .where(
                ExternalObservationImportFileModel.job_id == job_id,
                ExternalObservationImportRowModel.workspace_id == workspace_id,
                ExternalObservationImportRowModel.disposition == "PENDING",
                ExternalObservationImportRowModel.validation_status.in_(("UNRESOLVED", "INVALID")),
            )
            .order_by(ExternalObservationImportRowModel.created_at, ExternalObservationImportRowModel.id)
        )
        return list(rows)

    async def ingest_pdf(
        self,
        *,
        job_id: UUID,
        workspace_id: UUID,
        actor_id: UUID,
        filename: str,
        content_type: str | None,
        content: bytes,
    ) -> ExternalObservationImportFileModel:
        if not filename.strip():
            raise BulkImportError("filename must not be blank")
        if not content:
            raise BulkImportError("file must not be empty")

        job = await self.get_job(workspace_id, job_id)
        if job.status == "COMPLETED":
            raise BulkImportError("completed import job cannot accept more files")

        now = datetime.now(UTC)
        content_hash = hashlib.sha256(content).hexdigest()
        duplicate = await self._session.scalar(
            select(ExternalObservationImportFileModel)
            .where(
                ExternalObservationImportFileModel.workspace_id == workspace_id,
                ExternalObservationImportFileModel.content_hash == content_hash,
                ExternalObservationImportFileModel.status != "FAILED",
            )
            .order_by(ExternalObservationImportFileModel.created_at)
            .limit(1)
        )
        if duplicate is not None:
            file_model = ExternalObservationImportFileModel(
                id=uuid4(),
                job_id=job_id,
                workspace_id=workspace_id,
                import_batch_id=None,
                original_filename=filename.strip(),
                content_hash=content_hash,
                content_type=content_type,
                file_size_bytes=len(content),
                status="DUPLICATE",
                duplicate_of_file_id=duplicate.id,
                failure_code=None,
                failure_detail=None,
                created_at=now,
                updated_at=now,
            )
            self._session.add(file_model)
            await self._refresh_job_status(job)
            await self._session.commit()
            return file_model

        file_model = ExternalObservationImportFileModel(
            id=uuid4(),
            job_id=job_id,
            workspace_id=workspace_id,
            import_batch_id=None,
            original_filename=filename.strip(),
            content_hash=content_hash,
            content_type=content_type,
            file_size_bytes=len(content),
            status="QUEUED",
            duplicate_of_file_id=None,
            failure_code=None,
            failure_detail=None,
            created_at=now,
            updated_at=now,
        )
        self._session.add(file_model)
        job.status = "PROCESSING"
        job.updated_at = now
        await self._session.flush()

        try:
            recommendation = parse_hebeltrader_pdf(content)
        except HebeltraderParseError as error:
            file_model.status = "FAILED"
            file_model.failure_code = "HEBELTRADER_PARSE_FAILED"
            file_model.failure_detail = str(error)[:1024]
            file_model.updated_at = datetime.now(UTC)
            await self._refresh_job_status(job)
            await self._session.commit()
            return file_model

        batch = ExternalObservationImportBatchModel(
            id=uuid4(),
            workspace_id=workspace_id,
            original_filename=filename.strip(),
            content_hash=content_hash,
            content_type=content_type,
            file_size_bytes=len(content),
            imported_at=datetime.now(UTC),
            imported_by=actor_id,
        )
        self._session.add(batch)
        await self._session.flush()

        row = await self._stage_recommendation(
            workspace_id=workspace_id,
            batch_id=batch.id,
            recommendation=recommendation,
        )
        file_model.import_batch_id = batch.id
        file_model.status = "PARSED" if row.validation_status == "VALID" else "REVIEW_REQUIRED"
        file_model.updated_at = datetime.now(UTC)
        await self._refresh_job_status(job)
        await self._session.commit()
        return file_model

    async def _stage_recommendation(
        self,
        *,
        workspace_id: UUID,
        batch_id: UUID,
        recommendation: HebeltraderRecommendation,
    ) -> ExternalObservationImportRowModel:
        now = datetime.now(UTC)
        issues = [
            {"code": issue.code, "field": issue.field, "message": issue.message}
            for issue in recommendation.validation_issues
        ]

        underlying = await self._session.scalar(
            select(UnderlyingModel).where(
                UnderlyingModel.workspace_id == workspace_id,
                UnderlyingModel.wkn == recommendation.underlying_wkn.upper(),
            )
        )
        if underlying is None:
            issues.append(
                {
                    "code": "UNDERLYING_WKN_NOT_FOUND",
                    "field": "underlying_wkn",
                    "message": "No workspace underlying matches the source WKN",
                }
            )

        warrant = await self._session.scalar(
            select(WarrantModel).where(
                WarrantModel.workspace_id == workspace_id,
                WarrantModel.wkn == recommendation.derivative_wkn.upper(),
            )
        )
        if warrant is None:
            issues.append(
                {
                    "code": "WARRANT_WKN_NOT_FOUND",
                    "field": "derivative_wkn",
                    "message": "No workspace warrant matches the source WKN",
                }
            )
        elif underlying is not None and warrant.underlying_id != underlying.id:
            issues.append(
                {
                    "code": "WARRANT_UNDERLYING_MISMATCH",
                    "field": "derivative_wkn",
                    "message": "Resolved warrant belongs to a different underlying",
                }
            )

        validation_status = "VALID" if not issues else "UNRESOLVED"
        if any(issue["code"] == "WARRANT_UNDERLYING_MISMATCH" for issue in issues):
            validation_status = "INVALID"

        payload = _json_payload(recommendation)
        payload["validation_issues"] = issues

        row = ExternalObservationImportRowModel(
            id=uuid4(),
            batch_id=batch_id,
            workspace_id=workspace_id,
            source_row_number=1,
            raw_payload=payload,
            validation_status=validation_status,
            disposition="PENDING",
            resolved_underlying_id=(underlying.id if underlying is not None else None),
            resolved_product_id=(warrant.id if warrant is not None else None),
            target_external_observation_id=None,
            accepted_external_observation_version_id=None,
            disposed_at=None,
            disposed_by=None,
            created_at=now,
            updated_at=now,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def _refresh_job_status(self, job: ExternalObservationImportJobModel) -> None:
        await self._session.flush()
        statuses = list(
            await self._session.scalars(
                select(ExternalObservationImportFileModel.status).where(
                    ExternalObservationImportFileModel.job_id == job.id
                )
            )
        )
        if not statuses:
            job.status = "OPEN"
        elif any(status == "QUEUED" for status in statuses):
            job.status = "PROCESSING"
        elif any(status in {"REVIEW_REQUIRED", "FAILED"} for status in statuses):
            job.status = "REVIEW_REQUIRED"
        else:
            job.status = "READY"
        job.updated_at = datetime.now(UTC)


def _json_payload(value: HebeltraderRecommendation) -> dict[str, Any]:
    payload = asdict(value)
    payload.pop("raw_text", None)
    payload.pop("validation_issues", None)

    def convert(item: Any) -> Any:
        if isinstance(item, Decimal):
            return str(item)
        if isinstance(item, datetime):
            return item.isoformat()
        if hasattr(item, "isoformat"):
            return item.isoformat()
        if isinstance(item, dict):
            return {key: convert(val) for key, val in item.items()}
        if isinstance(item, (list, tuple)):
            return [convert(val) for val in item]
        return item

    return {key: convert(item) for key, item in payload.items()}
