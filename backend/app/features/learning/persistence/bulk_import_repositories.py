"""Repositories for multi-file external-observation imports."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.learning.domain.bulk_import import (
    ExternalObservationImportFile,
    ExternalObservationImportFileStatus,
    ExternalObservationImportJob,
    ExternalObservationImportJobStatus,
    ExternalObservationImportJobSummary,
)
from app.features.learning.persistence.bulk_import_models import (
    ExternalObservationImportFileModel,
    ExternalObservationImportJobModel,
)


def _job_from_model(model: ExternalObservationImportJobModel) -> ExternalObservationImportJob:
    return ExternalObservationImportJob(
        id=model.id,
        workspace_id=model.workspace_id,
        status=ExternalObservationImportJobStatus(model.status),
        created_at=model.created_at,
        created_by=model.created_by,
        updated_at=model.updated_at,
    )


def _file_from_model(model: ExternalObservationImportFileModel) -> ExternalObservationImportFile:
    return ExternalObservationImportFile(
        id=model.id,
        job_id=model.job_id,
        workspace_id=model.workspace_id,
        import_batch_id=model.import_batch_id,
        original_filename=model.original_filename,
        content_hash=model.content_hash,
        content_type=model.content_type,
        file_size_bytes=model.file_size_bytes,
        status=ExternalObservationImportFileStatus(model.status),
        duplicate_of_file_id=model.duplicate_of_file_id,
        failure_code=model.failure_code,
        failure_detail=model.failure_detail,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SqlAlchemyExternalObservationImportJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, job: ExternalObservationImportJob) -> None:
        self._session.add(
            ExternalObservationImportJobModel(
                id=job.id,
                workspace_id=job.workspace_id,
                status=job.status.value,
                created_at=job.created_at,
                created_by=job.created_by,
                updated_at=job.updated_at,
            )
        )

    async def get(self, workspace_id: UUID, job_id: UUID) -> ExternalObservationImportJob | None:
        model = await self._session.scalar(
            select(ExternalObservationImportJobModel).where(
                ExternalObservationImportJobModel.workspace_id == workspace_id,
                ExternalObservationImportJobModel.id == job_id,
            )
        )
        return _job_from_model(model) if model is not None else None

    async def set_status(
        self,
        *,
        workspace_id: UUID,
        job_id: UUID,
        status: ExternalObservationImportJobStatus,
        updated_at: datetime,
    ) -> bool:
        model = await self._session.scalar(
            select(ExternalObservationImportJobModel)
            .where(
                ExternalObservationImportJobModel.workspace_id == workspace_id,
                ExternalObservationImportJobModel.id == job_id,
            )
            .with_for_update()
        )
        if model is None:
            return False
        model.status = status.value
        model.updated_at = updated_at
        return True


class SqlAlchemyExternalObservationImportFileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, value: ExternalObservationImportFile) -> None:
        self._session.add(
            ExternalObservationImportFileModel(
                id=value.id,
                job_id=value.job_id,
                workspace_id=value.workspace_id,
                import_batch_id=value.import_batch_id,
                original_filename=value.original_filename,
                content_hash=value.content_hash,
                content_type=value.content_type,
                file_size_bytes=value.file_size_bytes,
                status=value.status.value,
                duplicate_of_file_id=value.duplicate_of_file_id,
                failure_code=value.failure_code,
                failure_detail=value.failure_detail,
                created_at=value.created_at,
                updated_at=value.updated_at,
            )
        )

    async def list_for_job(self, job_id: UUID) -> Sequence[ExternalObservationImportFile]:
        models = (
            await self._session.scalars(
                select(ExternalObservationImportFileModel)
                .where(ExternalObservationImportFileModel.job_id == job_id)
                .order_by(
                    ExternalObservationImportFileModel.created_at,
                    ExternalObservationImportFileModel.id,
                )
            )
        ).all()
        return tuple(_file_from_model(model) for model in models)

    async def find_existing_hash(
        self,
        *,
        workspace_id: UUID,
        content_hash: str,
        exclude_file_id: UUID | None = None,
    ) -> ExternalObservationImportFile | None:
        query = select(ExternalObservationImportFileModel).where(
            ExternalObservationImportFileModel.workspace_id == workspace_id,
            ExternalObservationImportFileModel.content_hash == content_hash,
            ExternalObservationImportFileModel.status
            != ExternalObservationImportFileStatus.FAILED.value,
        )
        if exclude_file_id is not None:
            query = query.where(ExternalObservationImportFileModel.id != exclude_file_id)
        model = await self._session.scalar(
            query.order_by(ExternalObservationImportFileModel.created_at).limit(1)
        )
        return _file_from_model(model) if model is not None else None

    async def summary(self, job_id: UUID) -> ExternalObservationImportJobSummary:
        files = await self.list_for_job(job_id)
        counts = Counter(value.status for value in files)
        return ExternalObservationImportJobSummary(
            files_total=len(files),
            files_queued=counts[ExternalObservationImportFileStatus.QUEUED],
            files_parsed=counts[ExternalObservationImportFileStatus.PARSED],
            files_review_required=counts[ExternalObservationImportFileStatus.REVIEW_REQUIRED],
            files_duplicate=counts[ExternalObservationImportFileStatus.DUPLICATE],
            files_failed=counts[ExternalObservationImportFileStatus.FAILED],
            files_completed=counts[ExternalObservationImportFileStatus.COMPLETED],
        )
