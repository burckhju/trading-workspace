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
    ExternalObservationEvidenceModel,
    ExternalObservationImportBatchModel,
    ExternalObservationImportRowIssueModel,
    ExternalObservationImportRowModel,
    ExternalObservationModel,
    ExternalObservationVersionModel,
    LearningEvidenceModel,
)
from app.features.market.persistence.models import UnderlyingModel
from app.features.product.persistence.models import WarrantModel


class BulkImportError(ValueError):
    """Raised for invalid bulk-import application commands."""


class ExternalObservationBulkImportService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_job(
        self,
        workspace_id: UUID,
        actor_id: UUID,
    ) -> ExternalObservationImportJobModel:
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

    async def get_job(
        self,
        workspace_id: UUID,
        job_id: UUID,
    ) -> ExternalObservationImportJobModel:
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
        self,
        workspace_id: UUID,
        job_id: UUID,
    ) -> list[ExternalObservationImportFileModel]:
        await self.get_job(workspace_id, job_id)
        rows = await self._session.scalars(
            select(ExternalObservationImportFileModel)
            .where(
                ExternalObservationImportFileModel.job_id == job_id,
                ExternalObservationImportFileModel.workspace_id == workspace_id,
            )
            .order_by(
                ExternalObservationImportFileModel.created_at,
                ExternalObservationImportFileModel.id,
            )
        )
        return list(rows)

    async def list_review_rows(
        self,
        workspace_id: UUID,
        job_id: UUID,
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
            .order_by(
                ExternalObservationImportRowModel.created_at,
                ExternalObservationImportRowModel.id,
            )
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
        retry_file = await self._find_failed_retry(
            workspace_id=workspace_id,
            job_id=job_id,
            content_hash=content_hash,
        )
        if retry_file is not None:
            file_model = retry_file
            file_model.original_filename = filename.strip()
            file_model.content_type = content_type
            file_model.file_size_bytes = len(content)
            file_model.status = "QUEUED"
            file_model.failure_code = None
            file_model.failure_detail = None
            file_model.updated_at = now
        else:
            duplicate = await self._find_duplicate(
                workspace_id=workspace_id,
                content_hash=content_hash,
            )
            if duplicate is not None:
                return await self._record_duplicate(
                    job=job,
                    workspace_id=workspace_id,
                    filename=filename,
                    content_type=content_type,
                    content=content,
                    content_hash=content_hash,
                    duplicate=duplicate,
                )
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
        if row.validation_status == "VALID":
            file_model.status = "PARSED"
        else:
            file_model.status = "REVIEW_REQUIRED"
        file_model.updated_at = datetime.now(UTC)
        await self._refresh_job_status(job)
        await self._session.commit()
        return file_model

    async def resolve_review_row(
        self,
        *,
        workspace_id: UUID,
        job_id: UUID,
        row_id: UUID,
        underlying_id: UUID,
        product_id: UUID,
        actor_id: UUID,
    ) -> ExternalObservationImportRowModel:
        job = await self.get_job(workspace_id, job_id)
        if job.status == "COMPLETED":
            raise BulkImportError("completed import job cannot be reviewed")

        row, file_model = await self._get_row_and_file(
            workspace_id,
            job_id,
            row_id,
        )
        if row.disposition != "PENDING":
            raise BulkImportError("only pending import rows can be resolved")

        underlying = await self._session.scalar(
            select(UnderlyingModel).where(
                UnderlyingModel.id == underlying_id,
                UnderlyingModel.workspace_id == workspace_id,
            )
        )
        if underlying is None:
            raise BulkImportError("selected underlying does not exist in workspace")

        warrant = await self._session.scalar(
            select(WarrantModel).where(
                WarrantModel.id == product_id,
                WarrantModel.workspace_id == workspace_id,
            )
        )
        if warrant is None:
            raise BulkImportError("selected warrant does not exist in workspace")
        if warrant.underlying_id != underlying.id:
            raise BulkImportError("selected warrant does not belong to selected underlying")

        now = datetime.now(UTC)
        row.resolved_underlying_id = underlying.id
        row.resolved_product_id = warrant.id
        row.validation_status = "VALID"
        row.updated_at = now
        payload = dict(row.raw_payload)
        payload["review_resolution"] = {
            "resolved_underlying_id": str(underlying.id),
            "resolved_product_id": str(warrant.id),
            "resolved_at": now.isoformat(),
            "resolved_by": str(actor_id),
        }
        row.raw_payload = payload
        file_model.status = "PARSED"
        file_model.updated_at = now
        await self._refresh_job_status(job)
        await self._session.commit()
        return row

    async def discard_review_row(
        self,
        *,
        workspace_id: UUID,
        job_id: UUID,
        row_id: UUID,
        actor_id: UUID,
    ) -> ExternalObservationImportRowModel:
        job = await self.get_job(workspace_id, job_id)
        if job.status == "COMPLETED":
            raise BulkImportError("completed import job cannot be reviewed")

        row, file_model = await self._get_row_and_file(
            workspace_id,
            job_id,
            row_id,
        )
        if row.disposition != "PENDING":
            raise BulkImportError("only pending import rows can be discarded")

        now = datetime.now(UTC)
        row.disposition = "DISCARDED"
        row.disposed_at = now
        row.disposed_by = actor_id
        row.updated_at = now
        file_model.status = "COMPLETED"
        file_model.updated_at = now
        await self._refresh_job_status(job)
        await self._session.commit()
        return row

    async def confirm_job(
        self,
        *,
        workspace_id: UUID,
        job_id: UUID,
        actor_id: UUID,
    ) -> list[UUID]:
        job = await self.get_job(workspace_id, job_id)
        if job.status == "COMPLETED":
            raise BulkImportError("import job is already completed")

        files = await self.list_files(workspace_id, job_id)
        if any(file.status == "FAILED" for file in files):
            raise BulkImportError("failed files must be retried before confirmation")

        review_rows = await self.list_review_rows(workspace_id, job_id)
        if review_rows:
            raise BulkImportError(
                "all review rows must be resolved or discarded before confirmation"
            )

        pending_rows = await self._list_valid_pending_rows(
            workspace_id=workspace_id,
            job_id=job_id,
        )
        now = datetime.now(UTC)
        version_ids: list[UUID] = []
        for row in pending_rows:
            if row.resolved_underlying_id is None or row.resolved_product_id is None:
                raise BulkImportError(
                    "valid Hebeltrader row requires resolved underlying and warrant"
                )
            version_id = await self._accept_row(
                workspace_id=workspace_id,
                job_id=job_id,
                actor_id=actor_id,
                row=row,
                now=now,
            )
            version_ids.append(version_id)

        job.status = "COMPLETED"
        job.updated_at = now
        await self._session.commit()
        return version_ids

    async def _stage_recommendation(
        self,
        *,
        workspace_id: UUID,
        batch_id: UUID,
        recommendation: HebeltraderRecommendation,
    ) -> ExternalObservationImportRowModel:
        now = datetime.now(UTC)
        issues: list[dict[str, str | None]] = [
            {
                "code": issue.code,
                "field": issue.field,
                "message": issue.message,
                "severity": "WARNING",
            }
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
                    "severity": "ERROR",
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
                    "severity": "ERROR",
                }
            )
        elif underlying is not None and warrant.underlying_id != underlying.id:
            issues.append(
                {
                    "code": "WARRANT_UNDERLYING_MISMATCH",
                    "field": "derivative_wkn",
                    "message": "Resolved warrant belongs to a different underlying",
                    "severity": "ERROR",
                }
            )

        validation_status = "VALID" if not issues else "UNRESOLVED"
        mismatch = any(issue["code"] == "WARRANT_UNDERLYING_MISMATCH" for issue in issues)
        if mismatch:
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
        self._persist_issues(row.id, issues, now)
        await self._session.flush()
        return row

    async def _find_failed_retry(
        self,
        *,
        workspace_id: UUID,
        job_id: UUID,
        content_hash: str,
    ) -> ExternalObservationImportFileModel | None:
        return await self._session.scalar(
            select(ExternalObservationImportFileModel)
            .where(
                ExternalObservationImportFileModel.workspace_id == workspace_id,
                ExternalObservationImportFileModel.job_id == job_id,
                ExternalObservationImportFileModel.content_hash == content_hash,
                ExternalObservationImportFileModel.status == "FAILED",
            )
            .order_by(ExternalObservationImportFileModel.created_at)
            .limit(1)
        )

    async def _find_duplicate(
        self,
        *,
        workspace_id: UUID,
        content_hash: str,
    ) -> ExternalObservationImportFileModel | None:
        return await self._session.scalar(
            select(ExternalObservationImportFileModel)
            .where(
                ExternalObservationImportFileModel.workspace_id == workspace_id,
                ExternalObservationImportFileModel.content_hash == content_hash,
                ExternalObservationImportFileModel.status != "FAILED",
            )
            .order_by(ExternalObservationImportFileModel.created_at)
            .limit(1)
        )

    async def _record_duplicate(
        self,
        *,
        job: ExternalObservationImportJobModel,
        workspace_id: UUID,
        filename: str,
        content_type: str | None,
        content: bytes,
        content_hash: str,
        duplicate: ExternalObservationImportFileModel,
    ) -> ExternalObservationImportFileModel:
        now = datetime.now(UTC)
        file_model = ExternalObservationImportFileModel(
            id=uuid4(),
            job_id=job.id,
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

    async def _list_valid_pending_rows(
        self,
        *,
        workspace_id: UUID,
        job_id: UUID,
    ) -> list[ExternalObservationImportRowModel]:
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
                ExternalObservationImportRowModel.validation_status == "VALID",
                ExternalObservationImportRowModel.disposition == "PENDING",
            )
            .order_by(ExternalObservationImportRowModel.created_at)
        )
        return list(rows)

    async def _accept_row(
        self,
        *,
        workspace_id: UUID,
        job_id: UUID,
        actor_id: UUID,
        row: ExternalObservationImportRowModel,
        now: datetime,
    ) -> UUID:
        file_model = await self._session.scalar(
            select(ExternalObservationImportFileModel).where(
                ExternalObservationImportFileModel.job_id == job_id,
                ExternalObservationImportFileModel.import_batch_id == row.batch_id,
            )
        )
        if file_model is None:
            raise BulkImportError("import row has no file provenance")
        if row.resolved_underlying_id is None or row.resolved_product_id is None:
            raise BulkImportError("import row has unresolved identities")

        observation_id = uuid4()
        version_id = uuid4()
        evidence_id = uuid4()
        issue_number = row.raw_payload.get("issue_number")
        issue_date = str(row.raw_payload.get("issue_date", ""))
        issue_year = issue_date[:4] if len(issue_date) >= 4 else "unknown"

        observation = ExternalObservationModel(
            id=observation_id,
            workspace_id=workspace_id,
            current_version_id=version_id,
            created_at=now,
            created_by=actor_id,
        )
        version = ExternalObservationVersionModel(
            id=version_id,
            external_observation_id=observation_id,
            version=1,
            underlying_id=row.resolved_underlying_id,
            product_id=row.resolved_product_id,
            source_type="NEWSLETTER_RECOMMENDATION",
            source_name="HEBELTRADER",
            external_reference=f"{issue_number}/{issue_year}",
            observed_at=_observed_at(row.raw_payload),
            recorded_at=now,
            imported_at=now,
            recording_method="FILE_IMPORT",
            import_row_id=row.id,
            source_metadata={
                **row.raw_payload,
                "source_file": {
                    "file_id": str(file_model.id),
                    "filename": file_model.original_filename,
                    "content_hash": file_model.content_hash,
                    "batch_id": str(row.batch_id),
                },
            },
            supersedes_version_id=None,
            created_at=now,
            created_by=actor_id,
        )
        evidence = LearningEvidenceModel(
            id=evidence_id,
            workspace_id=workspace_id,
            evidence_type="EXTERNAL_OBSERVATION",
            created_at=now,
        )
        evidence_source = ExternalObservationEvidenceModel(
            learning_evidence_id=evidence_id,
            external_observation_version_id=version_id,
        )
        self._session.add_all([observation, version, evidence, evidence_source])

        row.disposition = "ACCEPTED"
        row.accepted_external_observation_version_id = version_id
        row.disposed_at = now
        row.disposed_by = actor_id
        row.updated_at = now
        file_model.status = "COMPLETED"
        file_model.updated_at = now
        return version_id

    def _persist_issues(
        self,
        row_id: UUID,
        issues: list[dict[str, str | None]],
        now: datetime,
    ) -> None:
        for issue in issues:
            self._session.add(
                ExternalObservationImportRowIssueModel(
                    id=uuid4(),
                    import_row_id=row_id,
                    code=str(issue["code"]),
                    severity=str(issue["severity"]),
                    field=issue["field"],
                    message=str(issue["message"]),
                    created_at=now,
                )
            )

    async def _get_row_and_file(
        self,
        workspace_id: UUID,
        job_id: UUID,
        row_id: UUID,
    ) -> tuple[ExternalObservationImportRowModel, ExternalObservationImportFileModel]:
        result = await self._session.execute(
            select(
                ExternalObservationImportRowModel,
                ExternalObservationImportFileModel,
            )
            .join(
                ExternalObservationImportFileModel,
                ExternalObservationImportFileModel.import_batch_id
                == ExternalObservationImportRowModel.batch_id,
            )
            .where(
                ExternalObservationImportRowModel.id == row_id,
                ExternalObservationImportRowModel.workspace_id == workspace_id,
                ExternalObservationImportFileModel.job_id == job_id,
            )
        )
        pair = result.one_or_none()
        if pair is None:
            raise BulkImportError("import row does not exist in job")
        return pair[0], pair[1]

    async def _refresh_job_status(
        self,
        job: ExternalObservationImportJobModel,
    ) -> None:
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
        elif any(file_status == "QUEUED" for file_status in statuses):
            job.status = "PROCESSING"
        elif any(file_status in {"REVIEW_REQUIRED", "FAILED"} for file_status in statuses):
            job.status = "REVIEW_REQUIRED"
        else:
            job.status = "READY"
        job.updated_at = datetime.now(UTC)


def _observed_at(payload: dict[str, Any]) -> datetime:
    issue_date = payload.get("issue_date")
    if not isinstance(issue_date, str):
        raise BulkImportError("import row has no valid issue_date")
    try:
        parsed = datetime.fromisoformat(issue_date)
    except ValueError as error:
        raise BulkImportError("import row has invalid issue_date") from error
    return datetime(parsed.year, parsed.month, parsed.day, tzinfo=UTC)


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
