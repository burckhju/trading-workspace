"""Persistence models for multi-file external-observation import jobs."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKeyConstraint, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ExternalObservationImportJobModel(Base):
    __tablename__ = "external_observation_import_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('OPEN','PROCESSING','REVIEW_REQUIRED','READY','COMPLETED')",
            name="ck_external_observation_import_jobs_status_valid",
        ),
        CheckConstraint(
            "updated_at >= created_at",
            name="ck_external_observation_import_jobs_updated_not_before_created",
        ),
        ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="RESTRICT",
            name="fk_external_observation_import_jobs_workspace",
        ),
        Index(
            "ix_external_observation_import_jobs_workspace_created",
            "workspace_id",
            "created_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ExternalObservationImportFileModel(Base):
    __tablename__ = "external_observation_import_files"
    __table_args__ = (
        CheckConstraint(
            "length(trim(original_filename)) > 0",
            name="ck_external_observation_import_files_filename_nonblank",
        ),
        CheckConstraint(
            "length(content_hash) = 64",
            name="ck_external_observation_import_files_hash_length",
        ),
        CheckConstraint(
            "file_size_bytes > 0",
            name="ck_external_observation_import_files_size_positive",
        ),
        CheckConstraint(
            "status IN ('QUEUED','PARSED','REVIEW_REQUIRED','DUPLICATE','FAILED','COMPLETED')",
            name="ck_external_observation_import_files_status_valid",
        ),
        CheckConstraint(
            "(status='DUPLICATE') = (duplicate_of_file_id IS NOT NULL)",
            name="ck_external_observation_import_files_duplicate_consistent",
        ),
        CheckConstraint(
            "(status='FAILED') = (failure_code IS NOT NULL)",
            name="ck_external_observation_import_files_failure_consistent",
        ),
        CheckConstraint(
            "updated_at >= created_at",
            name="ck_external_observation_import_files_updated_not_before_created",
        ),
        ForeignKeyConstraint(
            ["job_id"],
            ["external_observation_import_jobs.id"],
            ondelete="RESTRICT",
            name="fk_external_observation_import_files_job",
        ),
        ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="RESTRICT",
            name="fk_external_observation_import_files_workspace",
        ),
        ForeignKeyConstraint(
            ["import_batch_id"],
            ["external_observation_import_batches.id"],
            ondelete="RESTRICT",
            name="fk_external_observation_import_files_batch",
        ),
        ForeignKeyConstraint(
            ["duplicate_of_file_id"],
            ["external_observation_import_files.id"],
            ondelete="RESTRICT",
            name="fk_external_observation_import_files_duplicate",
        ),
        Index(
            "ix_external_observation_import_files_job_status",
            "job_id",
            "status",
        ),
        Index(
            "ix_external_observation_import_files_workspace_hash",
            "workspace_id",
            "content_hash",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    job_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    workspace_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    import_batch_id: Mapped[UUID | None] = mapped_column(Uuid(), nullable=True)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    duplicate_of_file_id: Mapped[UUID | None] = mapped_column(Uuid(), nullable=True)
    failure_code: Mapped[str | None] = mapped_column(String(96), nullable=True)
    failure_detail: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
