"""FT-013 controlled model governance.

Revision ID: 20260825_0023
Revises: 20260824_0022
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260825_0023"
down_revision = "20260824_0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "governed_models",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("model_key", sa.String(96), nullable=False),
        sa.Column("name", sa.String(240), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.CheckConstraint("length(trim(model_key)) > 0", name="ck_governed_models_key_nonblank"),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_governed_models_name_nonblank"),
        sa.CheckConstraint("length(trim(purpose)) > 0", name="ck_governed_models_purpose_nonblank"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="RESTRICT", name="fk_governed_models_workspace"),
        sa.UniqueConstraint("workspace_id", "model_key", name="uq_governed_models_workspace_key"),
    )
    op.create_table(
        "governed_model_versions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("model_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("definition", postgresql.JSONB(), nullable=False),
        sa.Column("change_summary", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("previous_version_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint("version >= 1", name="ck_governed_model_versions_positive"),
        sa.CheckConstraint("status IN ('DRAFT','APPROVED')", name="ck_governed_model_versions_status_valid"),
        sa.CheckConstraint("previous_version_id IS NULL OR previous_version_id <> id", name="ck_governed_model_versions_not_self_previous"),
        sa.ForeignKeyConstraint(["model_id"], ["governed_models.id"], ondelete="RESTRICT", name="fk_governed_model_versions_model"),
        sa.ForeignKeyConstraint(["previous_version_id"], ["governed_model_versions.id"], ondelete="RESTRICT", name="fk_governed_model_versions_previous"),
        sa.UniqueConstraint("model_id", "version", name="uq_governed_model_versions_model_version"),
        sa.UniqueConstraint("previous_version_id", name="uq_governed_model_versions_previous"),
    )
    op.create_index("ix_governed_model_versions_model_status", "governed_model_versions", ["model_id", "status"])

    op.create_table(
        "model_hypotheses",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("source_lesson_version_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.CheckConstraint("length(trim(title)) > 0", name="ck_model_hypotheses_title_nonblank"),
        sa.CheckConstraint("length(trim(statement)) > 0", name="ck_model_hypotheses_statement_nonblank"),
        sa.CheckConstraint("status IN ('OPEN','PROPOSED','CLOSED')", name="ck_model_hypotheses_status_valid"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="RESTRICT", name="fk_model_hypotheses_workspace"),
        sa.ForeignKeyConstraint(["source_lesson_version_id"], ["lesson_versions.id"], ondelete="RESTRICT", name="fk_model_hypotheses_lesson_version"),
    )
    op.create_index("ix_model_hypotheses_workspace_status", "model_hypotheses", ["workspace_id", "status"])

    op.create_table(
        "model_hypothesis_evidence",
        sa.Column("hypothesis_id", sa.Uuid(), primary_key=True),
        sa.Column("learning_evidence_id", sa.Uuid(), primary_key=True),
        sa.ForeignKeyConstraint(["hypothesis_id"], ["model_hypotheses.id"], ondelete="RESTRICT", name="fk_model_hypothesis_evidence_hypothesis"),
        sa.ForeignKeyConstraint(["learning_evidence_id"], ["learning_evidence.id"], ondelete="RESTRICT", name="fk_model_hypothesis_evidence_evidence"),
    )

    op.create_table(
        "model_change_proposals",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("model_id", sa.Uuid(), nullable=False),
        sa.Column("base_model_version_id", sa.Uuid(), nullable=False),
        sa.Column("hypothesis_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("proposed_definition", postgresql.JSONB(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.CheckConstraint("status IN ('DRAFT','VALIDATED','APPROVED')", name="ck_model_change_proposals_status_valid"),
        sa.CheckConstraint("length(trim(rationale)) > 0", name="ck_model_change_proposals_rationale_nonblank"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="RESTRICT", name="fk_model_change_proposals_workspace"),
        sa.ForeignKeyConstraint(["model_id"], ["governed_models.id"], ondelete="RESTRICT", name="fk_model_change_proposals_model"),
        sa.ForeignKeyConstraint(["base_model_version_id"], ["governed_model_versions.id"], ondelete="RESTRICT", name="fk_model_change_proposals_base_version"),
        sa.ForeignKeyConstraint(["hypothesis_id"], ["model_hypotheses.id"], ondelete="RESTRICT", name="fk_model_change_proposals_hypothesis"),
    )
    op.create_index("ix_model_change_proposals_workspace_status", "model_change_proposals", ["workspace_id", "status"])

    op.create_table(
        "model_validations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("proposal_id", sa.Uuid(), nullable=False),
        sa.Column("method", sa.String(24), nullable=False),
        sa.Column("evidence_cutoff_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("conclusion", sa.String(24), nullable=False),
        sa.Column("metrics", postgresql.JSONB(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.CheckConstraint("method = 'RETROSPECTIVE'", name="ck_model_validations_method_v1"),
        sa.CheckConstraint("conclusion IN ('SUPPORTS','INCONCLUSIVE','CONTRADICTS')", name="ck_model_validations_conclusion_valid"),
        sa.CheckConstraint("evidence_cutoff_at <= created_at", name="ck_model_validations_cutoff_not_after_created"),
        sa.ForeignKeyConstraint(["proposal_id"], ["model_change_proposals.id"], ondelete="RESTRICT", name="fk_model_validations_proposal"),
    )
    op.create_index("ix_model_validations_proposal_created", "model_validations", ["proposal_id", "created_at"])

    op.create_table(
        "model_validation_evidence",
        sa.Column("validation_id", sa.Uuid(), primary_key=True),
        sa.Column("learning_evidence_id", sa.Uuid(), primary_key=True),
        sa.ForeignKeyConstraint(["validation_id"], ["model_validations.id"], ondelete="RESTRICT", name="fk_model_validation_evidence_validation"),
        sa.ForeignKeyConstraint(["learning_evidence_id"], ["learning_evidence.id"], ondelete="RESTRICT", name="fk_model_validation_evidence_evidence"),
    )

    op.create_table(
        "model_approvals",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("proposal_id", sa.Uuid(), nullable=True),
        sa.Column("model_version_id", sa.Uuid(), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_by", sa.Uuid(), nullable=False),
        sa.Column("correlation_id", sa.String(100), nullable=True),
        sa.ForeignKeyConstraint(["proposal_id"], ["model_change_proposals.id"], ondelete="RESTRICT", name="fk_model_approvals_proposal"),
        sa.ForeignKeyConstraint(["model_version_id"], ["governed_model_versions.id"], ondelete="RESTRICT", name="fk_model_approvals_version"),
        sa.UniqueConstraint("proposal_id", name="uq_model_approvals_proposal"),
        sa.UniqueConstraint("model_version_id", name="uq_model_approvals_version"),
    )


def downgrade() -> None:
    op.drop_table("model_approvals")
    op.drop_table("model_validation_evidence")
    op.drop_index("ix_model_validations_proposal_created", table_name="model_validations")
    op.drop_table("model_validations")
    op.drop_index("ix_model_change_proposals_workspace_status", table_name="model_change_proposals")
    op.drop_table("model_change_proposals")
    op.drop_table("model_hypothesis_evidence")
    op.drop_index("ix_model_hypotheses_workspace_status", table_name="model_hypotheses")
    op.drop_table("model_hypotheses")
    op.drop_index("ix_governed_model_versions_model_status", table_name="governed_model_versions")
    op.drop_table("governed_model_versions")
    op.drop_table("governed_models")
