"""Bulk-upload REST API for external historical observations."""

from __future__ import annotations

from collections import Counter
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.features.learning.api.bulk_import_dependencies import get_bulk_import_service
from app.features.learning.application.bulk_import_service import (
    BulkImportError,
    ExternalObservationBulkImportService,
)

router = APIRouter(prefix="/api/v1/learning/bulk-imports", tags=["learning"])

WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")
LOCAL_ACTOR_ID = UUID("00000000-0000-4000-8000-000000000002")


class BulkImportFileResponse(BaseModel):
    id: UUID
    filename: str
    status: str
    duplicate_of_file_id: UUID | None
    failure_code: str | None
    failure_detail: str | None


class BulkImportResponse(BaseModel):
    job_id: UUID
    status: str
    files_total: int
    files_by_status: dict[str, int]
    files: list[BulkImportFileResponse]


class ReviewRowResponse(BaseModel):
    id: UUID
    batch_id: UUID
    validation_status: str
    underlying_id: UUID | None
    product_id: UUID | None
    payload: dict[str, Any]


def _bad_request(error: BulkImportError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


@router.post("/hebeltrader", response_model=BulkImportResponse, status_code=status.HTTP_201_CREATED)
async def upload_hebeltrader_files(
    files: Annotated[list[UploadFile], File(description="Hebeltrader PDF issues")],
    service: Annotated[ExternalObservationBulkImportService, Depends(get_bulk_import_service)],
) -> BulkImportResponse:
    if not files:
        raise HTTPException(status_code=400, detail="at least one PDF is required")

    job = await service.create_job(WORKSPACE_ID, LOCAL_ACTOR_ID)
    results: list[BulkImportFileResponse] = []
    try:
        for upload in files:
            content = await upload.read()
            model = await service.ingest_pdf(
                job_id=job.id,
                workspace_id=WORKSPACE_ID,
                actor_id=LOCAL_ACTOR_ID,
                filename=upload.filename or "unnamed.pdf",
                content_type=upload.content_type,
                content=content,
            )
            results.append(
                BulkImportFileResponse(
                    id=model.id,
                    filename=model.original_filename,
                    status=model.status,
                    duplicate_of_file_id=model.duplicate_of_file_id,
                    failure_code=model.failure_code,
                    failure_detail=model.failure_detail,
                )
            )
    except BulkImportError as error:
        raise _bad_request(error) from error
    finally:
        for upload in files:
            await upload.close()

    current_job = await service.get_job(WORKSPACE_ID, job.id)
    counts = Counter(item.status for item in results)
    return BulkImportResponse(
        job_id=job.id,
        status=current_job.status,
        files_total=len(results),
        files_by_status=dict(counts),
        files=results,
    )


@router.get("/{job_id}", response_model=BulkImportResponse)
async def get_bulk_import(
    job_id: UUID,
    service: Annotated[ExternalObservationBulkImportService, Depends(get_bulk_import_service)],
) -> BulkImportResponse:
    try:
        job = await service.get_job(WORKSPACE_ID, job_id)
        files = await service.list_files(WORKSPACE_ID, job_id)
    except BulkImportError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    counts = Counter(item.status for item in files)
    return BulkImportResponse(
        job_id=job.id,
        status=job.status,
        files_total=len(files),
        files_by_status=dict(counts),
        files=[
            BulkImportFileResponse(
                id=item.id,
                filename=item.original_filename,
                status=item.status,
                duplicate_of_file_id=item.duplicate_of_file_id,
                failure_code=item.failure_code,
                failure_detail=item.failure_detail,
            )
            for item in files
        ],
    )


@router.get("/{job_id}/review", response_model=list[ReviewRowResponse])
async def list_bulk_import_review_rows(
    job_id: UUID,
    service: Annotated[ExternalObservationBulkImportService, Depends(get_bulk_import_service)],
) -> list[ReviewRowResponse]:
    try:
        rows = await service.list_review_rows(WORKSPACE_ID, job_id)
    except BulkImportError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    return [
        ReviewRowResponse(
            id=row.id,
            batch_id=row.batch_id,
            validation_status=row.validation_status,
            underlying_id=row.resolved_underlying_id,
            product_id=row.resolved_product_id,
            payload=row.raw_payload,
        )
        for row in rows
    ]
