"""SQLAlchemy persistence models for FT-012 build slice 01."""

# ruff: noqa: E501

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class TradeJournalModel(Base):
    __tablename__ = "trade_journals"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="RESTRICT",
            name="fk_trade_journals_workspace",
        ),
        ForeignKeyConstraint(
            ["trade_id"], ["trades.id"], ondelete="RESTRICT", name="fk_trade_journals_trade"
        ),
        UniqueConstraint("trade_id", name="uq_trade_journals_trade"),
        Index("ix_trade_journals_workspace_created", "workspace_id", "created_at"),
    )
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    trade_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[UUID] = mapped_column(Uuid(), nullable=False)


class TradeJournalVersionModel(Base):
    __tablename__ = "trade_journal_versions"
    __table_args__ = (
        CheckConstraint("version >= 1", name="ck_trade_journal_versions_version_positive"),
        CheckConstraint(
            "status IN ('DRAFT','FINALIZED')", name="ck_trade_journal_versions_status_valid"
        ),
        CheckConstraint(
            "((status='DRAFT' AND finalized_at IS NULL AND finalized_by IS NULL) OR "
            "(status='FINALIZED' AND finalized_at IS NOT NULL AND finalized_by IS NOT NULL AND finalized_at >= created_at))",
            name="ck_trade_journal_versions_lifecycle_consistent",
        ),
        CheckConstraint(
            "updated_at >= created_at", name="ck_trade_journal_versions_updated_not_before_created"
        ),
        CheckConstraint(
            "supersedes_version_id IS NULL OR supersedes_version_id <> id",
            name="ck_trade_journal_versions_not_self_superseding",
        ),
        ForeignKeyConstraint(
            ["trade_journal_id"],
            ["trade_journals.id"],
            ondelete="RESTRICT",
            name="fk_trade_journal_versions_journal",
        ),
        ForeignKeyConstraint(
            ["supersedes_version_id"],
            ["trade_journal_versions.id"],
            ondelete="RESTRICT",
            name="fk_trade_journal_versions_supersedes",
        ),
        UniqueConstraint(
            "trade_journal_id", "version", name="uq_trade_journal_versions_journal_version"
        ),
        UniqueConstraint("supersedes_version_id", name="uq_trade_journal_versions_supersedes"),
        Index("ix_trade_journal_versions_journal_version", "trade_journal_id", "version"),
        Index(
            "uq_trade_journal_versions_open_draft",
            "trade_journal_id",
            unique=True,
            postgresql_where=text("status = 'DRAFT'"),
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    trade_journal_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    version: Mapped[int] = mapped_column(Integer(), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    what_went_well: Mapped[str | None] = mapped_column(Text(), nullable=True)
    would_do_differently: Mapped[str | None] = mapped_column(Text(), nullable=True)
    additional_notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_by: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finalized_by: Mapped[UUID | None] = mapped_column(Uuid(), nullable=True)
    supersedes_version_id: Mapped[UUID | None] = mapped_column(Uuid(), nullable=True)


class LessonModel(Base):
    __tablename__ = "lessons"
    __table_args__ = (
        CheckConstraint("length(trim(title)) > 0", name="ck_lessons_title_nonblank"),
        CheckConstraint(
            "current_state IN ('CURRENT','REVIEW_RECOMMENDED','RETIRED')",
            name="ck_lessons_state_valid",
        ),
        CheckConstraint("updated_at >= created_at", name="ck_lessons_updated_not_before_created"),
        ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="RESTRICT", name="fk_lessons_workspace"
        ),
        Index("ix_lessons_workspace_state_updated", "workspace_id", "current_state", "updated_at"),
    )
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    current_version_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    current_state: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_by: Mapped[UUID] = mapped_column(Uuid(), nullable=False)


class LessonVersionModel(Base):
    __tablename__ = "lesson_versions"
    __table_args__ = (
        CheckConstraint("version >= 1", name="ck_lesson_versions_version_positive"),
        CheckConstraint(
            "length(trim(main_category)) > 0", name="ck_lesson_versions_main_category_nonblank"
        ),
        CheckConstraint("length(trim(content)) > 0", name="ck_lesson_versions_content_nonblank"),
        CheckConstraint(
            "supersedes_version_id IS NULL OR supersedes_version_id <> id",
            name="ck_lesson_versions_not_self_superseding",
        ),
        ForeignKeyConstraint(
            ["lesson_id"], ["lessons.id"], ondelete="RESTRICT", name="fk_lesson_versions_lesson"
        ),
        ForeignKeyConstraint(
            ["supersedes_version_id"],
            ["lesson_versions.id"],
            ondelete="RESTRICT",
            name="fk_lesson_versions_supersedes",
        ),
        UniqueConstraint("lesson_id", "version", name="uq_lesson_versions_lesson_version"),
        UniqueConstraint("supersedes_version_id", name="uq_lesson_versions_supersedes"),
        UniqueConstraint("lesson_id", "id", name="uq_lesson_versions_lesson_id"),
        Index("ix_lesson_versions_lesson_version", "lesson_id", "version"),
    )
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    lesson_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    version: Mapped[int] = mapped_column(Integer(), nullable=False)
    main_category: Mapped[str] = mapped_column(String(64), nullable=False)
    content: Mapped[str] = mapped_column(Text(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    supersedes_version_id: Mapped[UUID | None] = mapped_column(Uuid(), nullable=True)


class LessonEvidenceLinkModel(Base):
    __tablename__ = "lesson_evidence_links"
    __table_args__ = (
        CheckConstraint(
            "relation IN ('SUPPORTS','CONTRADICTS','CONTEXTUAL')",
            name="ck_lesson_evidence_links_relation_valid",
        ),
        UniqueConstraint(
            "lesson_version_id",
            "learning_evidence_id",
            name="uq_lesson_evidence_links_version_evidence",
        ),
        UniqueConstraint(
            "id",
            "lesson_version_id",
            name="uq_lesson_evidence_links_id_version",
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    lesson_version_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    learning_evidence_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    relation: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[UUID] = mapped_column(Uuid(), nullable=False)


class IdempotencyRecordModel(Base):
    __tablename__ = "ft012_idempotency_records"
    __table_args__ = (
        CheckConstraint(
            "status IN ('IN_PROGRESS','SUCCEEDED','FAILED_FINAL')",
            name="ck_ft012_idempotency_records_status_valid",
        ),
        CheckConstraint(
            "((status='IN_PROGRESS' AND result_type IS NULL AND result_id IS NULL AND error_code IS NULL AND completed_at IS NULL) OR "
            "(status='SUCCEEDED' AND result_type IS NOT NULL AND result_id IS NOT NULL AND error_code IS NULL AND completed_at IS NOT NULL) OR "
            "(status='FAILED_FINAL' AND result_type IS NULL AND result_id IS NULL AND error_code IS NOT NULL AND completed_at IS NOT NULL))",
            name="ck_ft012_idempotency_records_lifecycle_consistent",
        ),
        UniqueConstraint(
            "workspace_id",
            "command_type",
            "idempotency_key",
            name="uq_ft012_idempotency_records_key",
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    command_type: Mapped[str] = mapped_column(String(96), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(240), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    result_type: Mapped[str | None] = mapped_column(String(96), nullable=True)
    result_id: Mapped[UUID | None] = mapped_column(Uuid(), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(96), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# Deferred same-aggregate current-version FK for Lesson.
Base.metadata.tables["lessons"].append_constraint(
    ForeignKeyConstraint(
        ["id", "current_version_id"],
        ["lesson_versions.lesson_id", "lesson_versions.id"],
        name="fk_lessons_current_version_same_lesson",
        deferrable=True,
        initially="DEFERRED",
        ondelete="RESTRICT",
    )
)


class ExternalObservationImportBatchModel(Base):
    __tablename__ = "external_observation_import_batches"
    __table_args__ = (
        CheckConstraint(
            "length(trim(original_filename)) > 0",
            name="ck_external_observation_import_batches_filename_nonblank",
        ),
        CheckConstraint(
            "length(content_hash) = 64", name="ck_external_observation_import_batches_hash_length"
        ),
        CheckConstraint(
            "file_size_bytes > 0", name="ck_external_observation_import_batches_file_size_positive"
        ),
        ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="RESTRICT",
            name="fk_external_observation_import_batches_workspace",
        ),
        Index(
            "ix_external_observation_import_batches_workspace_imported",
            "workspace_id",
            "imported_at",
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    imported_by: Mapped[UUID] = mapped_column(Uuid(), nullable=False)


class ExternalObservationImportRowModel(Base):
    __tablename__ = "external_observation_import_rows"
    __table_args__ = (
        CheckConstraint(
            "source_row_number >= 1", name="ck_external_observation_import_rows_row_number_positive"
        ),
        CheckConstraint(
            "validation_status IN ('VALID','UNRESOLVED','INVALID')",
            name="ck_external_observation_import_rows_validation_status_valid",
        ),
        CheckConstraint(
            "disposition IN ('PENDING','ACCEPTED','DISCARDED')",
            name="ck_external_observation_import_rows_disposition_valid",
        ),
        CheckConstraint(
            "updated_at >= created_at",
            name="ck_external_observation_import_rows_updated_not_before_created",
        ),
        ForeignKeyConstraint(
            ["batch_id"],
            ["external_observation_import_batches.id"],
            ondelete="RESTRICT",
            name="fk_external_observation_import_rows_batch",
        ),
        ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="RESTRICT",
            name="fk_external_observation_import_rows_workspace",
        ),
        ForeignKeyConstraint(
            ["resolved_underlying_id"],
            ["underlyings.id"],
            ondelete="RESTRICT",
            name="fk_external_observation_import_rows_underlying",
        ),
        ForeignKeyConstraint(
            ["resolved_product_id"],
            ["warrants.id"],
            ondelete="RESTRICT",
            name="fk_external_observation_import_rows_product",
        ),
        UniqueConstraint(
            "batch_id", "source_row_number", name="uq_external_observation_import_rows_batch_row"
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    batch_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    workspace_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    source_row_number: Mapped[int] = mapped_column(Integer(), nullable=False)
    raw_payload: Mapped[dict[str, object]] = mapped_column(JSONB(), nullable=False)
    validation_status: Mapped[str] = mapped_column(String(16), nullable=False)
    disposition: Mapped[str] = mapped_column(String(16), nullable=False)
    resolved_underlying_id: Mapped[UUID | None] = mapped_column(Uuid(), nullable=True)
    resolved_product_id: Mapped[UUID | None] = mapped_column(Uuid(), nullable=True)
    target_external_observation_id: Mapped[UUID | None] = mapped_column(Uuid(), nullable=True)
    accepted_external_observation_version_id: Mapped[UUID | None] = mapped_column(
        Uuid(), nullable=True
    )
    disposed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    disposed_by: Mapped[UUID | None] = mapped_column(Uuid(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ExternalObservationModel(Base):
    __tablename__ = "external_observations"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="RESTRICT",
            name="fk_external_observations_workspace",
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    current_version_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[UUID] = mapped_column(Uuid(), nullable=False)


class ExternalObservationVersionModel(Base):
    __tablename__ = "external_observation_versions"
    __table_args__ = (
        CheckConstraint("version >= 1", name="ck_external_observation_versions_version_positive"),
        CheckConstraint(
            "length(trim(source_name)) > 0",
            name="ck_external_observation_versions_source_name_nonblank",
        ),
        CheckConstraint(
            "recording_method IN ('FILE_IMPORT','MANUAL')",
            name="ck_external_observation_versions_recording_method_valid",
        ),
        CheckConstraint(
            "supersedes_version_id IS NULL OR supersedes_version_id <> id",
            name="ck_external_observation_versions_not_self_superseding",
        ),
        ForeignKeyConstraint(
            ["external_observation_id"],
            ["external_observations.id"],
            ondelete="RESTRICT",
            name="fk_external_observation_versions_observation",
        ),
        ForeignKeyConstraint(
            ["underlying_id"],
            ["underlyings.id"],
            ondelete="RESTRICT",
            name="fk_external_observation_versions_underlying",
        ),
        ForeignKeyConstraint(
            ["product_id"],
            ["warrants.id"],
            ondelete="RESTRICT",
            name="fk_external_observation_versions_product",
        ),
        ForeignKeyConstraint(
            ["import_row_id"],
            ["external_observation_import_rows.id"],
            ondelete="RESTRICT",
            name="fk_external_observation_versions_import_row",
        ),
        UniqueConstraint(
            "external_observation_id",
            "version",
            name="uq_external_observation_versions_observation_version",
        ),
        UniqueConstraint(
            "id", "external_observation_id", name="uq_external_observation_versions_id_observation"
        ),
        UniqueConstraint("import_row_id", name="uq_external_observation_versions_import_row"),
    )
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    external_observation_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    version: Mapped[int] = mapped_column(Integer(), nullable=False)
    underlying_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    product_id: Mapped[UUID | None] = mapped_column(Uuid(), nullable=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    external_reference: Mapped[str | None] = mapped_column(String(512), nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    imported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    recording_method: Mapped[str] = mapped_column(String(16), nullable=False)
    import_row_id: Mapped[UUID | None] = mapped_column(Uuid(), nullable=True)
    source_metadata: Mapped[dict[str, object] | None] = mapped_column(JSONB(), nullable=True)
    supersedes_version_id: Mapped[UUID | None] = mapped_column(Uuid(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[UUID] = mapped_column(Uuid(), nullable=False)


class ExternalObservationImportRowIssueModel(Base):
    __tablename__ = "external_observation_import_row_issues"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('ERROR','WARNING')",
            name="ck_external_observation_import_row_issues_severity_valid",
        ),
        ForeignKeyConstraint(
            ["import_row_id"],
            ["external_observation_import_rows.id"],
            ondelete="RESTRICT",
            name="fk_external_observation_import_row_issues_row",
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    import_row_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    code: Mapped[str] = mapped_column(String(96), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    field: Mapped[str | None] = mapped_column(String(96), nullable=True)
    message: Mapped[str] = mapped_column(Text(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ExternalObservationJournalModel(Base):
    __tablename__ = "external_observation_journals"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="RESTRICT",
            name="fk_external_observation_journals_workspace",
        ),
        ForeignKeyConstraint(
            ["external_observation_id"],
            ["external_observations.id"],
            ondelete="RESTRICT",
            name="fk_external_observation_journals_observation",
        ),
        UniqueConstraint(
            "external_observation_id", name="uq_external_observation_journals_observation"
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    external_observation_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[UUID] = mapped_column(Uuid(), nullable=False)


class ExternalObservationJournalVersionModel(Base):
    __tablename__ = "external_observation_journal_versions"
    __table_args__ = (
        CheckConstraint(
            "version >= 1", name="ck_external_observation_journal_versions_version_positive"
        ),
        CheckConstraint(
            "status IN ('DRAFT','FINALIZED')",
            name="ck_external_observation_journal_versions_status_valid",
        ),
        ForeignKeyConstraint(
            ["external_observation_journal_id"],
            ["external_observation_journals.id"],
            ondelete="RESTRICT",
            name="fk_external_observation_journal_versions_journal",
        ),
        ForeignKeyConstraint(
            ["external_observation_version_id"],
            ["external_observation_versions.id"],
            ondelete="RESTRICT",
            name="fk_external_observation_journal_versions_source",
        ),
        UniqueConstraint(
            "external_observation_journal_id",
            "version",
            name="uq_external_observation_journal_versions_journal_version",
        ),
        UniqueConstraint(
            "id",
            "external_observation_journal_id",
            name="uq_external_observation_journal_versions_id_journal",
        ),
        Index(
            "uq_external_observation_journal_versions_open_draft",
            "external_observation_journal_id",
            unique=True,
            postgresql_where=text("status = 'DRAFT'"),
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    external_observation_journal_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    version: Mapped[int] = mapped_column(Integer(), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    external_observation_version_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    what_stands_out: Mapped[str | None] = mapped_column(Text(), nullable=True)
    relevance_to_own_process: Mapped[str | None] = mapped_column(Text(), nullable=True)
    additional_notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_by: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finalized_by: Mapped[UUID | None] = mapped_column(Uuid(), nullable=True)
    supersedes_version_id: Mapped[UUID | None] = mapped_column(Uuid(), nullable=True)


class LearningEvidenceModel(Base):
    __tablename__ = "learning_evidence"
    __table_args__ = (
        CheckConstraint(
            "evidence_type IN ('FT011','TRADE_JOURNAL_VERSION','EXTERNAL_OBSERVATION','EXTERNAL_OBSERVATION_JOURNAL_VERSION')",
            name="evidence_type_valid",
        ),
        ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="RESTRICT",
            name="fk_learning_evidence_workspace",
        ),
        Index("ix_learning_evidence_workspace_created", "workspace_id", "created_at"),
    )
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(48), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FT011EvidenceModel(Base):
    __tablename__ = "ft011_evidence"
    __table_args__ = (
        ForeignKeyConstraint(
            ["learning_evidence_id"],
            ["learning_evidence.id"],
            ondelete="RESTRICT",
            name="fk_ft011_evidence_anchor",
        ),
        ForeignKeyConstraint(
            ["trade_id"], ["trades.id"], ondelete="RESTRICT", name="fk_ft011_evidence_trade"
        ),
        ForeignKeyConstraint(
            ["post_trade_observation_id"],
            ["post_trade_observations.id"],
            ondelete="RESTRICT",
            name="fk_ft011_evidence_observation",
        ),
        ForeignKeyConstraint(
            ["exit_review_id"],
            ["exit_reviews.id"],
            ondelete="RESTRICT",
            name="fk_ft011_evidence_exit_review",
        ),
        ForeignKeyConstraint(
            ["exit_review_version_id"],
            ["exit_review_versions.id"],
            ondelete="RESTRICT",
            name="fk_ft011_evidence_exit_review_version",
        ),
        UniqueConstraint("exit_review_version_id", name="uq_ft011_evidence_exit_review_version"),
    )
    learning_evidence_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    trade_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    post_trade_observation_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    exit_review_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    exit_review_version_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)


class TradeJournalVersionEvidenceModel(Base):
    __tablename__ = "trade_journal_version_evidence"
    __table_args__ = (
        ForeignKeyConstraint(
            ["learning_evidence_id"],
            ["learning_evidence.id"],
            ondelete="RESTRICT",
            name="fk_trade_journal_version_evidence_anchor",
        ),
        ForeignKeyConstraint(
            ["trade_journal_version_id"],
            ["trade_journal_versions.id"],
            ondelete="RESTRICT",
            name="fk_trade_journal_version_evidence_source",
        ),
        UniqueConstraint(
            "trade_journal_version_id", name="uq_trade_journal_version_evidence_source"
        ),
    )
    learning_evidence_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    trade_journal_version_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)


class ExternalObservationEvidenceModel(Base):
    __tablename__ = "external_observation_evidence"
    __table_args__ = (
        ForeignKeyConstraint(
            ["learning_evidence_id"],
            ["learning_evidence.id"],
            ondelete="RESTRICT",
            name="fk_external_observation_evidence_anchor",
        ),
        ForeignKeyConstraint(
            ["external_observation_version_id"],
            ["external_observation_versions.id"],
            ondelete="RESTRICT",
            name="fk_external_observation_evidence_source",
        ),
        UniqueConstraint(
            "external_observation_version_id", name="uq_external_observation_evidence_source"
        ),
    )
    learning_evidence_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    external_observation_version_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)


class ExternalObservationJournalVersionEvidenceModel(Base):
    __tablename__ = "external_observation_journal_version_evidence"
    __table_args__ = (
        ForeignKeyConstraint(
            ["learning_evidence_id"],
            ["learning_evidence.id"],
            ondelete="RESTRICT",
            name="fk_ext_obs_journal_version_evidence_anchor",
        ),
        ForeignKeyConstraint(
            ["external_observation_journal_version_id"],
            ["external_observation_journal_versions.id"],
            ondelete="RESTRICT",
            name="fk_ext_obs_journal_version_evidence_source",
        ),
        UniqueConstraint(
            "external_observation_journal_version_id",
            name="uq_ext_obs_journal_version_evidence_source",
        ),
    )
    learning_evidence_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    external_observation_journal_version_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)


class LessonStateTransitionRecordModel(Base):
    __tablename__ = "lesson_state_transitions"
    __table_args__ = (
        CheckConstraint(
            "from_state IS NULL OR from_state IN ('CURRENT','REVIEW_RECOMMENDED','RETIRED')",
            name="from_state_valid",
        ),
        CheckConstraint(
            "to_state IN ('CURRENT','REVIEW_RECOMMENDED','RETIRED')",
            name="to_state_valid",
        ),
        CheckConstraint(
            "from_state IS NULL OR from_state <> to_state",
            name="state_changes",
        ),
        CheckConstraint(
            "length(trim(reason)) > 0",
            name="reason_nonblank",
        ),
        ForeignKeyConstraint(
            ["lesson_id"],
            ["lessons.id"],
            ondelete="RESTRICT",
            name="fk_lesson_state_transitions_lesson",
        ),
        ForeignKeyConstraint(
            ["related_lesson_version_id"],
            ["lesson_versions.id"],
            ondelete="RESTRICT",
            name="fk_lesson_state_transitions_version",
        ),
        Index(
            "ix_lesson_state_transitions_lesson_occurred",
            "lesson_id",
            "occurred_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    lesson_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    from_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_state: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    related_lesson_version_id: Mapped[UUID | None] = mapped_column(
        Uuid(),
        nullable=True,
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    actor: Mapped[UUID] = mapped_column(Uuid(), nullable=False)


class LessonReviewSignalRecordModel(Base):
    __tablename__ = "lesson_review_signals"
    __table_args__ = (
        CheckConstraint("status IN ('OPEN','RESOLVED')", name="status_valid"),
        CheckConstraint(
            "resolution IS NULL OR resolution IN "
            "('UNCHANGED_CONFIRMED','NEW_VERSION_CREATED','LESSON_RETIRED')",
            name="resolution_valid",
        ),
        CheckConstraint(
            "(status='OPEN' AND resolved_at IS NULL AND resolved_by IS NULL "
            "AND resolution IS NULL AND resulting_lesson_version_id IS NULL) OR "
            "(status='RESOLVED' AND resolved_at IS NOT NULL "
            "AND resolved_by IS NOT NULL AND resolution IS NOT NULL "
            "AND (resolution <> 'NEW_VERSION_CREATED' "
            "OR resulting_lesson_version_id IS NOT NULL))",
            name="lifecycle_consistent",
        ),
        ForeignKeyConstraint(
            ["lesson_id"],
            ["lessons.id"],
            ondelete="RESTRICT",
            name="fk_lesson_review_signals_lesson",
        ),
        ForeignKeyConstraint(
            ["lesson_version_id"],
            ["lesson_versions.id"],
            ondelete="RESTRICT",
            name="fk_lesson_review_signals_version",
        ),
        ForeignKeyConstraint(
            ["resulting_lesson_version_id"],
            ["lesson_versions.id"],
            ondelete="RESTRICT",
            name="fk_lesson_review_signals_resulting_version",
        ),
        UniqueConstraint("id", "lesson_version_id", name="uq_lesson_review_signals_id_version"),
        Index(
            "uq_lesson_review_signals_open",
            "lesson_id",
            unique=True,
            postgresql_where=text("status = 'OPEN'"),
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    lesson_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    lesson_version_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    raised_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    opened_by: Mapped[UUID | None] = mapped_column(Uuid(), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[UUID | None] = mapped_column(Uuid(), nullable=True)
    resolution: Mapped[str | None] = mapped_column(String(32), nullable=True)
    resulting_lesson_version_id: Mapped[UUID | None] = mapped_column(Uuid(), nullable=True)


class LessonReviewSignalEvidenceRecordModel(Base):
    __tablename__ = "lesson_review_signal_evidence"
    __table_args__ = (
        ForeignKeyConstraint(
            ["lesson_review_signal_id", "lesson_version_id"],
            ["lesson_review_signals.id", "lesson_review_signals.lesson_version_id"],
            ondelete="RESTRICT",
            name="fk_lesson_review_signal_evidence_signal",
        ),
        ForeignKeyConstraint(
            ["lesson_evidence_link_id", "lesson_version_id"],
            ["lesson_evidence_links.id", "lesson_evidence_links.lesson_version_id"],
            ondelete="RESTRICT",
            name="fk_lesson_review_signal_evidence_link",
        ),
    )
    lesson_review_signal_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    lesson_evidence_link_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    lesson_version_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)


class LessonSuggestionRecordModel(Base):
    __tablename__ = "lesson_suggestions"
    __table_args__ = (
        CheckConstraint("status IN ('SUGGESTED','REJECTED','CONFIRMED')", name="status_valid"),
        CheckConstraint(
            "length(trim(suggested_statement)) > 0", name="suggested_statement_nonblank"
        ),
        CheckConstraint(
            "(status='SUGGESTED' AND decided_at IS NULL AND decided_by IS NULL AND resulting_lesson_id IS NULL) OR "
            "(status='REJECTED' AND decided_at IS NOT NULL AND decided_by IS NOT NULL AND resulting_lesson_id IS NULL) OR "
            "(status='CONFIRMED' AND decided_at IS NOT NULL AND decided_by IS NOT NULL AND resulting_lesson_id IS NOT NULL)",
            name="lifecycle_consistent",
        ),
        ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="RESTRICT",
            name="fk_lesson_suggestions_workspace",
        ),
        ForeignKeyConstraint(
            ["resulting_lesson_id"],
            ["lessons.id"],
            ondelete="RESTRICT",
            name="fk_lesson_suggestions_resulting_lesson",
        ),
        Index("ix_lesson_suggestions_workspace_status", "workspace_id", "status"),
    )
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    suggested_statement: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_main_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resulting_lesson_id: Mapped[UUID | None] = mapped_column(Uuid(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_by: Mapped[UUID | None] = mapped_column(Uuid(), nullable=True)


class LessonTagRecordModel(Base):
    __tablename__ = "lesson_tags"
    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="name_nonblank"),
        CheckConstraint("length(trim(normalized_name)) > 0", name="normalized_name_nonblank"),
        ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="RESTRICT",
            name="fk_lesson_tags_workspace",
        ),
        UniqueConstraint(
            "workspace_id", "normalized_name", name="uq_lesson_tags_workspace_normalized_name"
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[UUID] = mapped_column(Uuid(), nullable=False)


class LessonTagAssignmentRecordModel(Base):
    __tablename__ = "lesson_tag_assignments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["lesson_id"],
            ["lessons.id"],
            ondelete="RESTRICT",
            name="fk_lesson_tag_assignments_lesson",
        ),
        ForeignKeyConstraint(
            ["lesson_tag_id"],
            ["lesson_tags.id"],
            ondelete="RESTRICT",
            name="fk_lesson_tag_assignments_tag",
        ),
    )
    lesson_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    lesson_tag_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    assigned_by: Mapped[UUID] = mapped_column(Uuid(), nullable=False)


class ExternalObservationTradeLinkRecordModel(Base):
    __tablename__ = "external_observation_trade_links"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="RESTRICT",
            name="fk_external_observation_trade_links_workspace",
        ),
        ForeignKeyConstraint(
            ["external_observation_id"],
            ["external_observations.id"],
            ondelete="RESTRICT",
            name="fk_external_observation_trade_links_observation",
        ),
        ForeignKeyConstraint(
            ["current_version_id", "id"],
            [
                "external_observation_trade_link_versions.id",
                "external_observation_trade_link_versions.external_observation_trade_link_id",
            ],
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
            name="fk_ext_obs_trade_links_current_version_same_link",
        ),
        Index(
            "ix_ext_obs_trade_links_observation",
            "external_observation_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    external_observation_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    current_version_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[UUID] = mapped_column(Uuid(), nullable=False)


class ExternalObservationTradeLinkVersionRecordModel(Base):
    __tablename__ = "external_observation_trade_link_versions"
    __table_args__ = (
        CheckConstraint("version >= 1", name="version_positive"),
        CheckConstraint(
            "status IN ('ACTIVE','RETRACTED')",
            name="status_valid",
        ),
        CheckConstraint(
            "change_reason IN ("
            "'INITIAL_LINK',"
            "'TARGET_CORRECTED',"
            "'LINK_RETRACTED',"
            "'LINK_REACTIVATED',"
            "'LINK_REACTIVATED_WITH_TARGET_CORRECTION',"
            "'SOURCE_REVALIDATED'"
            ")",
            name="change_reason_valid",
        ),
        CheckConstraint(
            "(version = 1 AND status = 'ACTIVE' "
            "AND change_reason = 'INITIAL_LINK' "
            "AND supersedes_version_id IS NULL) OR "
            "(version > 1 AND supersedes_version_id IS NOT NULL "
            "AND change_reason <> 'INITIAL_LINK')",
            name="initial_version_consistent",
        ),
        ForeignKeyConstraint(
            ["external_observation_trade_link_id"],
            ["external_observation_trade_links.id"],
            ondelete="RESTRICT",
            name="fk_ext_obs_trade_link_versions_link",
        ),
        ForeignKeyConstraint(
            ["external_observation_version_id"],
            ["external_observation_versions.id"],
            ondelete="RESTRICT",
            name="fk_ext_obs_trade_link_versions_source",
        ),
        ForeignKeyConstraint(
            ["trade_id"],
            ["trades.id"],
            ondelete="RESTRICT",
            name="fk_ext_obs_trade_link_versions_trade",
        ),
        ForeignKeyConstraint(
            ["supersedes_version_id", "external_observation_trade_link_id"],
            [
                "external_observation_trade_link_versions.id",
                "external_observation_trade_link_versions.external_observation_trade_link_id",
            ],
            ondelete="RESTRICT",
            name="fk_ext_obs_trade_link_versions_supersedes_same_link",
        ),
        UniqueConstraint(
            "external_observation_trade_link_id",
            "version",
            name="uq_ext_obs_trade_link_versions_link_version",
        ),
        UniqueConstraint(
            "id",
            "external_observation_trade_link_id",
            name="uq_ext_obs_trade_link_versions_id_link",
        ),
        Index(
            "ix_ext_obs_trade_link_versions_trade",
            "trade_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    external_observation_trade_link_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    external_observation_version_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    trade_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    supersedes_version_id: Mapped[UUID | None] = mapped_column(Uuid(), nullable=True)
    change_reason: Mapped[str] = mapped_column(String(64), nullable=False)
    change_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
