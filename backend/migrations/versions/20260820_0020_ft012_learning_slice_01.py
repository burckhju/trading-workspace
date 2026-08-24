"""FT-012 learning build slice 01.

Revision ID: 20260820_0020
Revises: 20260818_0019
"""

# ruff: noqa: E501

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260820_0020"
down_revision = "20260818_0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "trade_journals",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("trade_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="RESTRICT",
            name="fk_trade_journals_workspace",
        ),
        sa.ForeignKeyConstraint(
            ["trade_id"], ["trades.id"], ondelete="RESTRICT", name="fk_trade_journals_trade"
        ),
        sa.UniqueConstraint("trade_id", name="uq_trade_journals_trade"),
    )
    op.create_index(
        "ix_trade_journals_workspace_created", "trade_journals", ["workspace_id", "created_at"]
    )

    op.create_table(
        "trade_journal_versions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("trade_journal_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("what_went_well", sa.Text(), nullable=True),
        sa.Column("would_do_differently", sa.Text(), nullable=True),
        sa.Column("additional_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_by", sa.Uuid(), nullable=False),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finalized_by", sa.Uuid(), nullable=True),
        sa.Column("supersedes_version_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint("version >= 1", name="ck_trade_journal_versions_version_positive"),
        sa.CheckConstraint(
            "status IN ('DRAFT','FINALIZED')", name="ck_trade_journal_versions_status_valid"
        ),
        sa.CheckConstraint(
            "updated_at >= created_at", name="ck_trade_journal_versions_updated_not_before_created"
        ),
        sa.CheckConstraint(
            "supersedes_version_id IS NULL OR supersedes_version_id <> id",
            name="ck_trade_journal_versions_not_self_superseding",
        ),
        sa.CheckConstraint(
            "((status='DRAFT' AND finalized_at IS NULL AND finalized_by IS NULL) OR (status='FINALIZED' AND finalized_at IS NOT NULL AND finalized_by IS NOT NULL AND finalized_at >= created_at))",
            name="ck_trade_journal_versions_lifecycle_consistent",
        ),
        sa.ForeignKeyConstraint(
            ["trade_journal_id"],
            ["trade_journals.id"],
            ondelete="RESTRICT",
            name="fk_trade_journal_versions_journal",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_version_id"],
            ["trade_journal_versions.id"],
            ondelete="RESTRICT",
            name="fk_trade_journal_versions_supersedes",
        ),
        sa.UniqueConstraint(
            "trade_journal_id", "version", name="uq_trade_journal_versions_journal_version"
        ),
        sa.UniqueConstraint("supersedes_version_id", name="uq_trade_journal_versions_supersedes"),
    )
    op.create_index(
        "ix_trade_journal_versions_journal_version",
        "trade_journal_versions",
        ["trade_journal_id", "version"],
    )
    op.create_index(
        "uq_trade_journal_versions_open_draft",
        "trade_journal_versions",
        ["trade_journal_id"],
        unique=True,
        postgresql_where=sa.text("status = 'DRAFT'"),
    )

    op.create_table(
        "lessons",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("current_version_id", sa.Uuid(), nullable=False),
        sa.Column("current_state", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_by", sa.Uuid(), nullable=False),
        sa.CheckConstraint("length(trim(title)) > 0", name="ck_lessons_title_nonblank"),
        sa.CheckConstraint(
            "current_state IN ('CURRENT','REVIEW_RECOMMENDED','RETIRED')",
            name="ck_lessons_state_valid",
        ),
        sa.CheckConstraint(
            "updated_at >= created_at", name="ck_lessons_updated_not_before_created"
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="RESTRICT", name="fk_lessons_workspace"
        ),
    )
    op.create_index(
        "ix_lessons_workspace_state_updated",
        "lessons",
        ["workspace_id", "current_state", "updated_at"],
    )

    op.create_table(
        "lesson_versions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("lesson_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("main_category", sa.String(64), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("supersedes_version_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint("version >= 1", name="ck_lesson_versions_version_positive"),
        sa.CheckConstraint(
            "length(trim(main_category)) > 0", name="ck_lesson_versions_main_category_nonblank"
        ),
        sa.CheckConstraint("length(trim(content)) > 0", name="ck_lesson_versions_content_nonblank"),
        sa.CheckConstraint(
            "supersedes_version_id IS NULL OR supersedes_version_id <> id",
            name="ck_lesson_versions_not_self_superseding",
        ),
        sa.ForeignKeyConstraint(
            ["lesson_id"], ["lessons.id"], ondelete="RESTRICT", name="fk_lesson_versions_lesson"
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_version_id"],
            ["lesson_versions.id"],
            ondelete="RESTRICT",
            name="fk_lesson_versions_supersedes",
        ),
        sa.UniqueConstraint("lesson_id", "version", name="uq_lesson_versions_lesson_version"),
        sa.UniqueConstraint("supersedes_version_id", name="uq_lesson_versions_supersedes"),
        sa.UniqueConstraint("lesson_id", "id", name="uq_lesson_versions_lesson_id"),
    )
    op.create_index(
        "ix_lesson_versions_lesson_version", "lesson_versions", ["lesson_id", "version"]
    )

    op.create_foreign_key(
        "fk_lessons_current_version_same_lesson",
        "lessons",
        "lesson_versions",
        ["id", "current_version_id"],
        ["lesson_id", "id"],
        ondelete="RESTRICT",
        deferrable=True,
        initially="DEFERRED",
    )

    op.create_table(
        "lesson_evidence_links",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("lesson_version_id", sa.Uuid(), nullable=False),
        sa.Column("learning_evidence_id", sa.Uuid(), nullable=False),
        sa.Column("relation", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "relation IN ('SUPPORTS','CONTRADICTS','CONTEXTUAL')",
            name="ck_lesson_evidence_links_relation_valid",
        ),
        sa.UniqueConstraint(
            "lesson_version_id",
            "learning_evidence_id",
            name="uq_lesson_evidence_links_version_evidence",
        ),
        sa.UniqueConstraint(
            "id",
            "lesson_version_id",
            name="uq_lesson_evidence_links_id_version",
        ),
    )

    op.create_table(
        "ft012_idempotency_records",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("command_type", sa.String(96), nullable=False),
        sa.Column("idempotency_key", sa.String(240), nullable=False),
        sa.Column("request_fingerprint", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("result_type", sa.String(96), nullable=True),
        sa.Column("result_id", sa.Uuid(), nullable=True),
        sa.Column("error_code", sa.String(96), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('IN_PROGRESS','SUCCEEDED','FAILED_FINAL')",
            name="ck_ft012_idempotency_records_status_valid",
        ),
        sa.CheckConstraint(
            "((status='IN_PROGRESS' AND result_type IS NULL AND result_id IS NULL AND error_code IS NULL AND completed_at IS NULL) OR (status='SUCCEEDED' AND result_type IS NOT NULL AND result_id IS NOT NULL AND error_code IS NULL AND completed_at IS NOT NULL) OR (status='FAILED_FINAL' AND result_type IS NULL AND result_id IS NULL AND error_code IS NOT NULL AND completed_at IS NOT NULL))",
            name="ck_ft012_idempotency_records_lifecycle_consistent",
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "command_type",
            "idempotency_key",
            name="uq_ft012_idempotency_records_key",
        ),
    )

    op.create_table(
        "external_observation_import_batches",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("original_filename", sa.String(512), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("content_type", sa.String(255), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("imported_by", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "length(trim(original_filename)) > 0",
            name="ck_external_observation_import_batches_filename_nonblank",
        ),
        sa.CheckConstraint(
            "length(content_hash) = 64", name="ck_external_observation_import_batches_hash_length"
        ),
        sa.CheckConstraint(
            "file_size_bytes > 0", name="ck_external_observation_import_batches_file_size_positive"
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="RESTRICT",
            name="fk_external_observation_import_batches_workspace",
        ),
    )
    op.create_index(
        "ix_external_observation_import_batches_workspace_imported",
        "external_observation_import_batches",
        ["workspace_id", "imported_at"],
    )

    op.create_table(
        "external_observation_import_rows",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("source_row_number", sa.Integer(), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False),
        sa.Column("validation_status", sa.String(16), nullable=False),
        sa.Column("disposition", sa.String(16), nullable=False),
        sa.Column("resolved_underlying_id", sa.Uuid(), nullable=True),
        sa.Column("resolved_product_id", sa.Uuid(), nullable=True),
        sa.Column("target_external_observation_id", sa.Uuid(), nullable=True),
        sa.Column("accepted_external_observation_version_id", sa.Uuid(), nullable=True),
        sa.Column("disposed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("disposed_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "source_row_number >= 1", name="ck_external_observation_import_rows_row_number_positive"
        ),
        sa.CheckConstraint(
            "validation_status IN ('VALID','UNRESOLVED','INVALID')",
            name="ck_external_observation_import_rows_validation_status_valid",
        ),
        sa.CheckConstraint(
            "disposition IN ('PENDING','ACCEPTED','DISCARDED')",
            name="ck_external_observation_import_rows_disposition_valid",
        ),
        sa.CheckConstraint(
            "updated_at >= created_at",
            name="ck_external_observation_import_rows_updated_not_before_created",
        ),
        sa.CheckConstraint(
            "((disposition='PENDING' AND disposed_at IS NULL AND disposed_by IS NULL "
            "AND accepted_external_observation_version_id IS NULL) OR "
            "(disposition='ACCEPTED' AND disposed_at IS NOT NULL AND disposed_by IS NOT NULL "
            "AND accepted_external_observation_version_id IS NOT NULL) OR "
            "(disposition='DISCARDED' AND disposed_at IS NOT NULL AND disposed_by IS NOT NULL "
            "AND accepted_external_observation_version_id IS NULL))",
            name="ck_external_observation_import_rows_lifecycle_consistent",
        ),
        sa.ForeignKeyConstraint(
            ["batch_id"],
            ["external_observation_import_batches.id"],
            ondelete="RESTRICT",
            name="fk_external_observation_import_rows_batch",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="RESTRICT",
            name="fk_external_observation_import_rows_workspace",
        ),
        sa.ForeignKeyConstraint(
            ["resolved_underlying_id"],
            ["underlyings.id"],
            ondelete="RESTRICT",
            name="fk_external_observation_import_rows_underlying",
        ),
        sa.ForeignKeyConstraint(
            ["resolved_product_id"],
            ["warrants.id"],
            ondelete="RESTRICT",
            name="fk_external_observation_import_rows_product",
        ),
        sa.UniqueConstraint(
            "batch_id", "source_row_number", name="uq_external_observation_import_rows_batch_row"
        ),
    )
    op.create_index(
        "ix_external_observation_import_rows_batch_status",
        "external_observation_import_rows",
        ["batch_id", "validation_status", "disposition"],
    )

    op.create_table(
        "external_observations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("current_version_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="RESTRICT",
            name="fk_external_observations_workspace",
        ),
    )
    op.create_index(
        "ix_external_observations_workspace_created",
        "external_observations",
        ["workspace_id", "created_at"],
    )

    op.create_table(
        "external_observation_versions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("external_observation_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("underlying_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=True),
        sa.Column("source_type", sa.String(64), nullable=False),
        sa.Column("source_name", sa.String(255), nullable=False),
        sa.Column("external_reference", sa.String(512), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("recording_method", sa.String(16), nullable=False),
        sa.Column("import_row_id", sa.Uuid(), nullable=True),
        sa.Column("source_metadata", postgresql.JSONB(), nullable=True),
        sa.Column("supersedes_version_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "version >= 1", name="ck_external_observation_versions_version_positive"
        ),
        sa.CheckConstraint(
            "length(trim(source_name)) > 0",
            name="ck_external_observation_versions_source_name_nonblank",
        ),
        sa.CheckConstraint(
            "recording_method IN ('FILE_IMPORT','MANUAL')",
            name="ck_external_observation_versions_recording_method_valid",
        ),
        sa.CheckConstraint(
            "((recording_method='FILE_IMPORT' AND imported_at IS NOT NULL AND import_row_id IS NOT NULL) OR "
            "(recording_method='MANUAL' AND imported_at IS NULL AND import_row_id IS NULL))",
            name="ck_external_observation_versions_recording_provenance_consistent",
        ),
        sa.CheckConstraint(
            "supersedes_version_id IS NULL OR supersedes_version_id <> id",
            name="ck_external_observation_versions_not_self_superseding",
        ),
        sa.ForeignKeyConstraint(
            ["external_observation_id"],
            ["external_observations.id"],
            ondelete="RESTRICT",
            name="fk_external_observation_versions_observation",
        ),
        sa.ForeignKeyConstraint(
            ["underlying_id"],
            ["underlyings.id"],
            ondelete="RESTRICT",
            name="fk_external_observation_versions_underlying",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["warrants.id"],
            ondelete="RESTRICT",
            name="fk_external_observation_versions_product",
        ),
        sa.ForeignKeyConstraint(
            ["import_row_id"],
            ["external_observation_import_rows.id"],
            ondelete="RESTRICT",
            name="fk_external_observation_versions_import_row",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_version_id", "external_observation_id"],
            [
                "external_observation_versions.id",
                "external_observation_versions.external_observation_id",
            ],
            ondelete="RESTRICT",
            name="fk_external_observation_versions_supersedes_same_observation",
        ),
        sa.UniqueConstraint(
            "external_observation_id",
            "version",
            name="uq_external_observation_versions_observation_version",
        ),
        sa.UniqueConstraint(
            "id", "external_observation_id", name="uq_external_observation_versions_id_observation"
        ),
        sa.UniqueConstraint("import_row_id", name="uq_external_observation_versions_import_row"),
    )
    op.create_index(
        "ix_external_observation_versions_observation_version",
        "external_observation_versions",
        ["external_observation_id", "version"],
    )
    op.create_index(
        "ix_external_observation_versions_underlying_observed",
        "external_observation_versions",
        ["underlying_id", "observed_at"],
    )
    op.create_index(
        "ix_external_observation_versions_product_observed",
        "external_observation_versions",
        ["product_id", "observed_at"],
    )

    op.create_foreign_key(
        "fk_external_observations_current_version_same_observation",
        "external_observations",
        "external_observation_versions",
        ["current_version_id", "id"],
        ["id", "external_observation_id"],
        ondelete="RESTRICT",
        deferrable=True,
        initially="DEFERRED",
    )
    op.create_foreign_key(
        "fk_external_observation_import_rows_target_observation",
        "external_observation_import_rows",
        "external_observations",
        ["target_external_observation_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_external_observation_import_rows_accepted_version",
        "external_observation_import_rows",
        "external_observation_versions",
        ["accepted_external_observation_version_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.create_table(
        "external_observation_import_row_issues",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("import_row_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(96), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("field", sa.String(96), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "severity IN ('ERROR','WARNING')",
            name="ck_external_observation_import_row_issues_severity_valid",
        ),
        sa.CheckConstraint(
            "length(trim(code)) > 0", name="ck_external_observation_import_row_issues_code_nonblank"
        ),
        sa.CheckConstraint(
            "length(trim(message)) > 0",
            name="ck_external_observation_import_row_issues_message_nonblank",
        ),
        sa.ForeignKeyConstraint(
            ["import_row_id"],
            ["external_observation_import_rows.id"],
            ondelete="RESTRICT",
            name="fk_external_observation_import_row_issues_row",
        ),
    )
    op.create_index(
        "ix_external_observation_import_row_issues_row_created",
        "external_observation_import_row_issues",
        ["import_row_id", "created_at"],
    )

    op.create_table(
        "external_observation_journals",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("external_observation_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="RESTRICT",
            name="fk_external_observation_journals_workspace",
        ),
        sa.ForeignKeyConstraint(
            ["external_observation_id"],
            ["external_observations.id"],
            ondelete="RESTRICT",
            name="fk_external_observation_journals_observation",
        ),
        sa.UniqueConstraint(
            "external_observation_id", name="uq_external_observation_journals_observation"
        ),
    )

    op.create_table(
        "external_observation_journal_versions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("external_observation_journal_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("external_observation_version_id", sa.Uuid(), nullable=False),
        sa.Column("what_stands_out", sa.Text(), nullable=True),
        sa.Column("relevance_to_own_process", sa.Text(), nullable=True),
        sa.Column("additional_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_by", sa.Uuid(), nullable=False),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finalized_by", sa.Uuid(), nullable=True),
        sa.Column("supersedes_version_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint(
            "version >= 1", name="ck_external_observation_journal_versions_version_positive"
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT','FINALIZED')",
            name="ck_external_observation_journal_versions_status_valid",
        ),
        sa.CheckConstraint(
            "updated_at >= created_at",
            name="ck_external_observation_journal_versions_updated_not_before_created",
        ),
        sa.CheckConstraint(
            "((status='DRAFT' AND finalized_at IS NULL AND finalized_by IS NULL) OR "
            "(status='FINALIZED' AND finalized_at IS NOT NULL AND finalized_by IS NOT NULL AND finalized_at >= created_at))",
            name="ck_external_observation_journal_versions_lifecycle_consistent",
        ),
        sa.CheckConstraint(
            "supersedes_version_id IS NULL OR supersedes_version_id <> id",
            name="ck_external_observation_journal_versions_not_self_superseding",
        ),
        sa.ForeignKeyConstraint(
            ["external_observation_journal_id"],
            ["external_observation_journals.id"],
            ondelete="RESTRICT",
            name="fk_external_observation_journal_versions_journal",
        ),
        sa.ForeignKeyConstraint(
            ["external_observation_version_id"],
            ["external_observation_versions.id"],
            ondelete="RESTRICT",
            name="fk_external_observation_journal_versions_source",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_version_id", "external_observation_journal_id"],
            [
                "external_observation_journal_versions.id",
                "external_observation_journal_versions.external_observation_journal_id",
            ],
            ondelete="RESTRICT",
            name="fk_ext_obs_journal_versions_supersedes_same_journal",
        ),
        sa.UniqueConstraint(
            "external_observation_journal_id",
            "version",
            name="uq_external_observation_journal_versions_journal_version",
        ),
        sa.UniqueConstraint(
            "id",
            "external_observation_journal_id",
            name="uq_external_observation_journal_versions_id_journal",
        ),
    )
    op.create_index(
        "ix_external_observation_journal_versions_journal_version",
        "external_observation_journal_versions",
        ["external_observation_journal_id", "version"],
    )
    op.create_index(
        "uq_external_observation_journal_versions_open_draft",
        "external_observation_journal_versions",
        ["external_observation_journal_id"],
        unique=True,
        postgresql_where=sa.text("status = 'DRAFT'"),
    )

    op.create_table(
        "learning_evidence",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_type", sa.String(48), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "evidence_type IN ('FT011','TRADE_JOURNAL_VERSION','EXTERNAL_OBSERVATION','EXTERNAL_OBSERVATION_JOURNAL_VERSION')",
            name="evidence_type_valid",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="RESTRICT",
            name="fk_learning_evidence_workspace",
        ),
    )
    op.create_index(
        "ix_learning_evidence_workspace_created",
        "learning_evidence",
        ["workspace_id", "created_at"],
    )

    op.create_table(
        "ft011_evidence",
        sa.Column("learning_evidence_id", sa.Uuid(), primary_key=True),
        sa.Column("trade_id", sa.Uuid(), nullable=False),
        sa.Column("post_trade_observation_id", sa.Uuid(), nullable=False),
        sa.Column("exit_review_id", sa.Uuid(), nullable=False),
        sa.Column("exit_review_version_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["learning_evidence_id"],
            ["learning_evidence.id"],
            ondelete="RESTRICT",
            name="fk_ft011_evidence_anchor",
        ),
        sa.ForeignKeyConstraint(
            ["trade_id"], ["trades.id"], ondelete="RESTRICT", name="fk_ft011_evidence_trade"
        ),
        sa.ForeignKeyConstraint(
            ["post_trade_observation_id"],
            ["post_trade_observations.id"],
            ondelete="RESTRICT",
            name="fk_ft011_evidence_observation",
        ),
        sa.ForeignKeyConstraint(
            ["exit_review_id"],
            ["exit_reviews.id"],
            ondelete="RESTRICT",
            name="fk_ft011_evidence_exit_review",
        ),
        sa.ForeignKeyConstraint(
            ["exit_review_version_id"],
            ["exit_review_versions.id"],
            ondelete="RESTRICT",
            name="fk_ft011_evidence_exit_review_version",
        ),
        sa.UniqueConstraint("exit_review_version_id", name="uq_ft011_evidence_exit_review_version"),
    )

    op.create_table(
        "trade_journal_version_evidence",
        sa.Column("learning_evidence_id", sa.Uuid(), primary_key=True),
        sa.Column("trade_journal_version_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["learning_evidence_id"],
            ["learning_evidence.id"],
            ondelete="RESTRICT",
            name="fk_trade_journal_version_evidence_anchor",
        ),
        sa.ForeignKeyConstraint(
            ["trade_journal_version_id"],
            ["trade_journal_versions.id"],
            ondelete="RESTRICT",
            name="fk_trade_journal_version_evidence_source",
        ),
        sa.UniqueConstraint(
            "trade_journal_version_id", name="uq_trade_journal_version_evidence_source"
        ),
    )

    op.create_table(
        "external_observation_evidence",
        sa.Column("learning_evidence_id", sa.Uuid(), primary_key=True),
        sa.Column("external_observation_version_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["learning_evidence_id"],
            ["learning_evidence.id"],
            ondelete="RESTRICT",
            name="fk_external_observation_evidence_anchor",
        ),
        sa.ForeignKeyConstraint(
            ["external_observation_version_id"],
            ["external_observation_versions.id"],
            ondelete="RESTRICT",
            name="fk_external_observation_evidence_source",
        ),
        sa.UniqueConstraint(
            "external_observation_version_id", name="uq_external_observation_evidence_source"
        ),
    )

    op.create_table(
        "external_observation_journal_version_evidence",
        sa.Column("learning_evidence_id", sa.Uuid(), primary_key=True),
        sa.Column("external_observation_journal_version_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["learning_evidence_id"],
            ["learning_evidence.id"],
            ondelete="RESTRICT",
            name="fk_ext_obs_journal_version_evidence_anchor",
        ),
        sa.ForeignKeyConstraint(
            ["external_observation_journal_version_id"],
            ["external_observation_journal_versions.id"],
            ondelete="RESTRICT",
            name="fk_ext_obs_journal_version_evidence_source",
        ),
        sa.UniqueConstraint(
            "external_observation_journal_version_id",
            name="uq_ext_obs_journal_version_evidence_source",
        ),
    )

    op.create_table(
        "lesson_state_transitions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("lesson_id", sa.Uuid(), nullable=False),
        sa.Column("from_state", sa.String(32), nullable=True),
        sa.Column("to_state", sa.String(32), nullable=False),
        sa.Column("reason", sa.String(255), nullable=False),
        sa.Column("related_lesson_version_id", sa.Uuid(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "from_state IS NULL OR from_state IN ('CURRENT','REVIEW_RECOMMENDED','RETIRED')",
            name="from_state_valid",
        ),
        sa.CheckConstraint(
            "to_state IN ('CURRENT','REVIEW_RECOMMENDED','RETIRED')",
            name="to_state_valid",
        ),
        sa.CheckConstraint(
            "from_state IS NULL OR from_state <> to_state",
            name="state_changes",
        ),
        sa.CheckConstraint(
            "length(trim(reason)) > 0",
            name="reason_nonblank",
        ),
        sa.ForeignKeyConstraint(
            ["lesson_id"],
            ["lessons.id"],
            ondelete="RESTRICT",
            name="fk_lesson_state_transitions_lesson",
        ),
        sa.ForeignKeyConstraint(
            ["related_lesson_version_id"],
            ["lesson_versions.id"],
            ondelete="RESTRICT",
            name="fk_lesson_state_transitions_version",
        ),
    )
    op.create_index(
        "ix_lesson_state_transitions_lesson_occurred",
        "lesson_state_transitions",
        ["lesson_id", "occurred_at"],
    )

    op.create_table(
        "lesson_review_signals",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("lesson_id", sa.Uuid(), nullable=False),
        sa.Column("lesson_version_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("raised_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.Uuid(), nullable=True),
        sa.Column("resolution", sa.String(32), nullable=True),
        sa.Column("resulting_lesson_version_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint("status IN ('OPEN','RESOLVED')", name="status_valid"),
        sa.CheckConstraint(
            "resolution IS NULL OR resolution IN ('UNCHANGED_CONFIRMED','NEW_VERSION_CREATED','LESSON_RETIRED')",
            name="resolution_valid",
        ),
        sa.CheckConstraint(
            "(status='OPEN' AND resolved_at IS NULL AND resolved_by IS NULL AND resolution IS NULL AND resulting_lesson_version_id IS NULL) OR (status='RESOLVED' AND resolved_at IS NOT NULL AND resolved_by IS NOT NULL AND resolution IS NOT NULL AND (resolution <> 'NEW_VERSION_CREATED' OR resulting_lesson_version_id IS NOT NULL))",
            name="lifecycle_consistent",
        ),
        sa.ForeignKeyConstraint(
            ["lesson_id"],
            ["lessons.id"],
            ondelete="RESTRICT",
            name="fk_lesson_review_signals_lesson",
        ),
        sa.ForeignKeyConstraint(
            ["lesson_version_id"],
            ["lesson_versions.id"],
            ondelete="RESTRICT",
            name="fk_lesson_review_signals_version",
        ),
        sa.ForeignKeyConstraint(
            ["resulting_lesson_version_id"],
            ["lesson_versions.id"],
            ondelete="RESTRICT",
            name="fk_lesson_review_signals_resulting_version",
        ),
        sa.UniqueConstraint("id", "lesson_version_id", name="uq_lesson_review_signals_id_version"),
    )
    op.create_index(
        "uq_lesson_review_signals_open",
        "lesson_review_signals",
        ["lesson_id"],
        unique=True,
        postgresql_where=sa.text("status = 'OPEN'"),
    )

    op.create_table(
        "lesson_review_signal_evidence",
        sa.Column("lesson_review_signal_id", sa.Uuid(), primary_key=True),
        sa.Column("lesson_evidence_link_id", sa.Uuid(), primary_key=True),
        sa.Column("lesson_version_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["lesson_review_signal_id", "lesson_version_id"],
            ["lesson_review_signals.id", "lesson_review_signals.lesson_version_id"],
            ondelete="RESTRICT",
            name="fk_lesson_review_signal_evidence_signal",
        ),
        sa.ForeignKeyConstraint(
            ["lesson_evidence_link_id", "lesson_version_id"],
            ["lesson_evidence_links.id", "lesson_evidence_links.lesson_version_id"],
            ondelete="RESTRICT",
            name="fk_lesson_review_signal_evidence_link",
        ),
    )

    op.create_table(
        "lesson_suggestions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("suggested_statement", sa.Text(), nullable=False),
        sa.Column("suggested_main_category", sa.String(64), nullable=True),
        sa.Column("resulting_lesson_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decided_by", sa.Uuid(), nullable=True),
        sa.CheckConstraint("status IN ('SUGGESTED','REJECTED','CONFIRMED')", name="status_valid"),
        sa.CheckConstraint(
            "length(trim(suggested_statement)) > 0", name="suggested_statement_nonblank"
        ),
        sa.CheckConstraint(
            "(status='SUGGESTED' AND decided_at IS NULL AND decided_by IS NULL AND resulting_lesson_id IS NULL) OR (status='REJECTED' AND decided_at IS NOT NULL AND decided_by IS NOT NULL AND resulting_lesson_id IS NULL) OR (status='CONFIRMED' AND decided_at IS NOT NULL AND decided_by IS NOT NULL AND resulting_lesson_id IS NOT NULL)",
            name="lifecycle_consistent",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="RESTRICT",
            name="fk_lesson_suggestions_workspace",
        ),
        sa.ForeignKeyConstraint(
            ["resulting_lesson_id"],
            ["lessons.id"],
            ondelete="RESTRICT",
            name="fk_lesson_suggestions_resulting_lesson",
        ),
    )
    op.create_index(
        "ix_lesson_suggestions_workspace_status", "lesson_suggestions", ["workspace_id", "status"]
    )

    op.create_table(
        "lesson_tags",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("normalized_name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.CheckConstraint("length(trim(name)) > 0", name="name_nonblank"),
        sa.CheckConstraint("length(trim(normalized_name)) > 0", name="normalized_name_nonblank"),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="RESTRICT",
            name="fk_lesson_tags_workspace",
        ),
        sa.UniqueConstraint(
            "workspace_id", "normalized_name", name="uq_lesson_tags_workspace_normalized_name"
        ),
    )

    op.create_table(
        "lesson_tag_assignments",
        sa.Column("lesson_id", sa.Uuid(), primary_key=True),
        sa.Column("lesson_tag_id", sa.Uuid(), primary_key=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("assigned_by", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["lesson_id"],
            ["lessons.id"],
            ondelete="RESTRICT",
            name="fk_lesson_tag_assignments_lesson",
        ),
        sa.ForeignKeyConstraint(
            ["lesson_tag_id"],
            ["lesson_tags.id"],
            ondelete="RESTRICT",
            name="fk_lesson_tag_assignments_tag",
        ),
    )

    op.create_table(
        "external_observation_trade_links",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("external_observation_id", sa.Uuid(), nullable=False),
        sa.Column("current_version_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="RESTRICT",
            name="fk_external_observation_trade_links_workspace",
        ),
        sa.ForeignKeyConstraint(
            ["external_observation_id"],
            ["external_observations.id"],
            ondelete="RESTRICT",
            name="fk_external_observation_trade_links_observation",
        ),
    )
    op.create_index(
        "ix_ext_obs_trade_links_observation",
        "external_observation_trade_links",
        ["external_observation_id"],
    )

    op.create_table(
        "external_observation_trade_link_versions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("external_observation_trade_link_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("external_observation_version_id", sa.Uuid(), nullable=False),
        sa.Column("trade_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("supersedes_version_id", sa.Uuid(), nullable=True),
        sa.Column("change_reason", sa.String(64), nullable=False),
        sa.Column("change_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.CheckConstraint("version >= 1", name="version_positive"),
        sa.CheckConstraint("status IN ('ACTIVE','RETRACTED')", name="status_valid"),
        sa.CheckConstraint(
            "change_reason IN ("
            "'INITIAL_LINK','TARGET_CORRECTED','LINK_RETRACTED',"
            "'LINK_REACTIVATED','LINK_REACTIVATED_WITH_TARGET_CORRECTION',"
            "'SOURCE_REVALIDATED')",
            name="change_reason_valid",
        ),
        sa.CheckConstraint(
            "(version = 1 AND status = 'ACTIVE' "
            "AND change_reason = 'INITIAL_LINK' "
            "AND supersedes_version_id IS NULL) OR "
            "(version > 1 AND supersedes_version_id IS NOT NULL "
            "AND change_reason <> 'INITIAL_LINK')",
            name="initial_version_consistent",
        ),
        sa.ForeignKeyConstraint(
            ["external_observation_trade_link_id"],
            ["external_observation_trade_links.id"],
            ondelete="RESTRICT",
            name="fk_ext_obs_trade_link_versions_link",
        ),
        sa.ForeignKeyConstraint(
            ["external_observation_version_id"],
            ["external_observation_versions.id"],
            ondelete="RESTRICT",
            name="fk_ext_obs_trade_link_versions_source",
        ),
        sa.ForeignKeyConstraint(
            ["trade_id"],
            ["trades.id"],
            ondelete="RESTRICT",
            name="fk_ext_obs_trade_link_versions_trade",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_version_id", "external_observation_trade_link_id"],
            [
                "external_observation_trade_link_versions.id",
                "external_observation_trade_link_versions.external_observation_trade_link_id",
            ],
            ondelete="RESTRICT",
            name="fk_ext_obs_trade_link_versions_supersedes_same_link",
        ),
        sa.UniqueConstraint(
            "external_observation_trade_link_id",
            "version",
            name="uq_ext_obs_trade_link_versions_link_version",
        ),
        sa.UniqueConstraint(
            "id",
            "external_observation_trade_link_id",
            name="uq_ext_obs_trade_link_versions_id_link",
        ),
    )
    op.create_index(
        "ix_ext_obs_trade_link_versions_trade",
        "external_observation_trade_link_versions",
        ["trade_id"],
    )

    op.create_foreign_key(
        "fk_ext_obs_trade_links_current_version_same_link",
        "external_observation_trade_links",
        "external_observation_trade_link_versions",
        ["current_version_id", "id"],
        ["id", "external_observation_trade_link_id"],
        ondelete="RESTRICT",
        deferrable=True,
        initially="DEFERRED",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_ext_obs_trade_links_current_version_same_link",
        "external_observation_trade_links",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_ext_obs_trade_link_versions_trade",
        table_name="external_observation_trade_link_versions",
    )
    op.drop_table("external_observation_trade_link_versions")
    op.drop_index(
        "ix_ext_obs_trade_links_observation",
        table_name="external_observation_trade_links",
    )
    op.drop_table("external_observation_trade_links")

    op.drop_table("lesson_tag_assignments")
    op.drop_table("lesson_tags")
    op.drop_index("ix_lesson_suggestions_workspace_status", table_name="lesson_suggestions")
    op.drop_table("lesson_suggestions")
    op.drop_table("lesson_review_signal_evidence")
    op.drop_index("uq_lesson_review_signals_open", table_name="lesson_review_signals")
    op.drop_table("lesson_review_signals")

    op.drop_index(
        "ix_lesson_state_transitions_lesson_occurred",
        table_name="lesson_state_transitions",
    )
    op.drop_table("lesson_state_transitions")

    op.drop_table("external_observation_journal_version_evidence")
    op.drop_table("external_observation_evidence")
    op.drop_table("trade_journal_version_evidence")
    op.drop_table("ft011_evidence")
    op.drop_index(
        "ix_learning_evidence_workspace_created",
        table_name="learning_evidence",
    )
    op.drop_table("learning_evidence")

    op.drop_index(
        "uq_external_observation_journal_versions_open_draft",
        table_name="external_observation_journal_versions",
    )
    op.drop_index(
        "ix_external_observation_journal_versions_journal_version",
        table_name="external_observation_journal_versions",
    )
    op.drop_table("external_observation_journal_versions")
    op.drop_table("external_observation_journals")
    op.drop_index(
        "ix_external_observation_import_row_issues_row_created",
        table_name="external_observation_import_row_issues",
    )
    op.drop_table("external_observation_import_row_issues")
    op.drop_constraint(
        "fk_external_observation_import_rows_accepted_version",
        "external_observation_import_rows",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_external_observation_import_rows_target_observation",
        "external_observation_import_rows",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_external_observations_current_version_same_observation",
        "external_observations",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_external_observation_versions_product_observed",
        table_name="external_observation_versions",
    )
    op.drop_index(
        "ix_external_observation_versions_underlying_observed",
        table_name="external_observation_versions",
    )
    op.drop_index(
        "ix_external_observation_versions_observation_version",
        table_name="external_observation_versions",
    )
    op.drop_table("external_observation_versions")
    op.drop_index("ix_external_observations_workspace_created", table_name="external_observations")
    op.drop_table("external_observations")
    op.drop_index(
        "ix_external_observation_import_rows_batch_status",
        table_name="external_observation_import_rows",
    )
    op.drop_table("external_observation_import_rows")
    op.drop_index(
        "ix_external_observation_import_batches_workspace_imported",
        table_name="external_observation_import_batches",
    )
    op.drop_table("external_observation_import_batches")
    op.drop_table("ft012_idempotency_records")
    op.drop_table("lesson_evidence_links")
    op.drop_constraint("fk_lessons_current_version_same_lesson", "lessons", type_="foreignkey")
    op.drop_index("ix_lesson_versions_lesson_version", table_name="lesson_versions")
    op.drop_table("lesson_versions")
    op.drop_index("ix_lessons_workspace_state_updated", table_name="lessons")
    op.drop_table("lessons")
    op.drop_index("uq_trade_journal_versions_open_draft", table_name="trade_journal_versions")
    op.drop_index("ix_trade_journal_versions_journal_version", table_name="trade_journal_versions")
    op.drop_table("trade_journal_versions")
    op.drop_index("ix_trade_journals_workspace_created", table_name="trade_journals")
    op.drop_table("trade_journals")
