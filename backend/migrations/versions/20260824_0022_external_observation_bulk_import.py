"""External observation bulk import jobs.

Revision ID: 20260824_0022
Revises: 20260824_0021
"""

import sqlalchemy as sa
from alembic import op

revision = "20260824_0022"
down_revision = "20260824_0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "external_observation_import_jobs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('OPEN','PROCESSING','REVIEW_REQUIRED','READY','COMPLETED')",
            name="ck_external_observation_import_jobs_status_valid",
        ),
        sa.CheckConstraint(
            "updated_at >= created_at",
            name="ck_external_observation_import_jobs_updated_not_before_created",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="RESTRICT",
            name="fk_external_observation_import_jobs_workspace",
        ),
    )
    op.create_index(
        "ix_external_observation_import_jobs_workspace_created",
        "external_observation_import_jobs",
        ["workspace_id", "created_at"],
    )

    op.create_table(
        "external_observation_import_files",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("import_batch_id", sa.Uuid(), nullable=True),
        sa.Column("original_filename", sa.String(512), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("content_type", sa.String(255), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("duplicate_of_file_id", sa.Uuid(), nullable=True),
        sa.Column("failure_code", sa.String(96), nullable=True),
        sa.Column("failure_detail", sa.String(1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("length(trim(original_filename)) > 0", name="ck_external_observation_import_files_filename_nonblank"),
        sa.CheckConstraint("length(content_hash) = 64", name="ck_external_observation_import_files_hash_length"),
        sa.CheckConstraint("file_size_bytes > 0", name="ck_external_observation_import_files_size_positive"),
        sa.CheckConstraint("status IN ('QUEUED','PARSED','REVIEW_REQUIRED','DUPLICATE','FAILED','COMPLETED')", name="ck_external_observation_import_files_status_valid"),
        sa.CheckConstraint("(status='DUPLICATE') = (duplicate_of_file_id IS NOT NULL)", name="ck_external_observation_import_files_duplicate_consistent"),
        sa.CheckConstraint("(status='FAILED') = (failure_code IS NOT NULL)", name="ck_external_observation_import_files_failure_consistent"),
        sa.CheckConstraint("updated_at >= created_at", name="ck_external_observation_import_files_updated_not_before_created"),
        sa.ForeignKeyConstraint(["job_id"], ["external_observation_import_jobs.id"], ondelete="RESTRICT", name="fk_external_observation_import_files_job"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="RESTRICT", name="fk_external_observation_import_files_workspace"),
        sa.ForeignKeyConstraint(["import_batch_id"], ["external_observation_import_batches.id"], ondelete="RESTRICT", name="fk_external_observation_import_files_batch"),
        sa.ForeignKeyConstraint(["duplicate_of_file_id"], ["external_observation_import_files.id"], ondelete="RESTRICT", name="fk_external_observation_import_files_duplicate"),
    )
    op.create_index("ix_external_observation_import_files_job_status", "external_observation_import_files", ["job_id", "status"])
    op.create_index("ix_external_observation_import_files_workspace_hash", "external_observation_import_files", ["workspace_id", "content_hash"])


def downgrade() -> None:
    op.drop_index("ix_external_observation_import_files_workspace_hash", table_name="external_observation_import_files")
    op.drop_index("ix_external_observation_import_files_job_status", table_name="external_observation_import_files")
    op.drop_table("external_observation_import_files")
    op.drop_index("ix_external_observation_import_jobs_workspace_created", table_name="external_observation_import_jobs")
    op.drop_table("external_observation_import_jobs")
