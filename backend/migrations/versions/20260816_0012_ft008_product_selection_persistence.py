"""FT-008 product selection persistence.

Revision ID: 20260816_0012
Revises: 20260815_0011
"""
from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

revision: str = "20260816_0012"
down_revision: str | None = "20260815_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "product_selection_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("trade_plan_id", sa.Uuid(), nullable=False),
        sa.Column("trade_plan_version_id", sa.Uuid(), nullable=False),
        sa.Column("trade_plan_version_status", sa.String(length=32), nullable=False),
        sa.Column("underlying_id", sa.Uuid(), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("universe_model_id", sa.String(length=100), nullable=False),
        sa.Column("universe_model_version", sa.String(length=64), nullable=False),
        sa.Column("eligibility_model_id", sa.String(length=100), nullable=False),
        sa.Column("eligibility_model_version", sa.String(length=64), nullable=False),
        sa.Column("evaluation_model_id", sa.String(length=100), nullable=False),
        sa.Column("evaluation_model_version", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.CheckConstraint("trade_plan_version_status = 'APPROVED'", name="ck_product_selection_runs_approved_trade_plan_version"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["trade_plan_id"], ["trade_plans.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["trade_plan_version_id"], ["trade_plan_versions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["underlying_id"], ["underlyings.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_product_selection_runs_workspace_plan_version", "product_selection_runs", ["workspace_id", "trade_plan_version_id"])
    op.create_index("ix_product_selection_runs_underlying_evaluated", "product_selection_runs", ["underlying_id", "evaluated_at"])

    op.create_table(
        "product_evaluations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("warrant_id", sa.Uuid(), nullable=False),
        sa.Column("warrant_terms_version_id", sa.Uuid(), nullable=False),
        sa.Column("warrant_listing_id", sa.Uuid(), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("eligibility_model_id", sa.String(length=100), nullable=False),
        sa.Column("eligibility_model_version", sa.String(length=64), nullable=False),
        sa.Column("evaluation_model_id", sa.String(length=100), nullable=False),
        sa.Column("evaluation_model_version", sa.String(length=64), nullable=False),
        sa.Column("eligibility_status", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["product_selection_runs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["warrant_id"], ["warrants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["warrant_terms_version_id"], ["warrant_terms_versions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["warrant_listing_id"], ["warrant_listings.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "warrant_terms_version_id", "warrant_listing_id", name="uq_product_evaluations_run_terms_listing"),
        sa.UniqueConstraint("id", "run_id", name="uq_product_evaluations_id_run"),
    )
    op.create_index("ix_product_evaluations_run_status", "product_evaluations", ["run_id", "eligibility_status"])

    op.create_table(
        "product_evaluation_inputs",
        sa.Column("id", sa.Uuid(), nullable=False), sa.Column("product_evaluation_id", sa.Uuid(), nullable=False), sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False), sa.Column("value", sa.Text(), nullable=True), sa.Column("availability", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=200), nullable=False), sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True), sa.Column("quality", sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(["product_evaluation_id"], ["product_evaluations.id"], ondelete="RESTRICT"), sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_evaluation_id", "sequence", name="uq_product_evaluation_inputs_evaluation_sequence"),
    )
    op.create_table(
        "product_evaluation_criteria",
        sa.Column("id", sa.Uuid(), nullable=False), sa.Column("product_evaluation_id", sa.Uuid(), nullable=False), sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("criterion_id", sa.String(length=120), nullable=False), sa.Column("outcome", sa.String(length=32), nullable=False), sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("actual_value", sa.Text(), nullable=True), sa.Column("expected_value", sa.Text(), nullable=True), sa.Column("data_availability", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["product_evaluation_id"], ["product_evaluations.id"], ondelete="RESTRICT"), sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_evaluation_id", "sequence", name="uq_product_evaluation_criteria_evaluation_sequence"),
    )
    op.create_table(
        "product_evaluation_metrics",
        sa.Column("id", sa.Uuid(), nullable=False), sa.Column("product_evaluation_id", sa.Uuid(), nullable=False), sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("metric_id", sa.String(length=120), nullable=False), sa.Column("value", sa.Numeric(30, 12), nullable=True), sa.Column("unit", sa.String(length=40), nullable=True),
        sa.Column("origin", sa.String(length=32), nullable=False), sa.Column("source", sa.String(length=200), nullable=False), sa.Column("formula_or_rule", sa.Text(), nullable=True),
        sa.Column("data_availability", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["product_evaluation_id"], ["product_evaluations.id"], ondelete="RESTRICT"), sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_evaluation_id", "sequence", name="uq_product_evaluation_metrics_evaluation_sequence"),
    )
    op.create_table(
        "product_evaluation_reasons",
        sa.Column("id", sa.Uuid(), nullable=False), sa.Column("product_evaluation_id", sa.Uuid(), nullable=False), sa.Column("sequence", sa.Integer(), nullable=False), sa.Column("reason", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["product_evaluation_id"], ["product_evaluations.id"], ondelete="RESTRICT"), sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_evaluation_id", "sequence", name="uq_product_evaluation_reasons_evaluation_sequence"),
    )
    op.create_table(
        "product_universe_omissions",
        sa.Column("id", sa.Uuid(), nullable=False), sa.Column("run_id", sa.Uuid(), nullable=False), sa.Column("warrant_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.String(length=64), nullable=False), sa.Column("explanation", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["product_selection_runs.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["warrant_id"], ["warrants.id"], ondelete="RESTRICT"), sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "warrant_id", "reason", name="uq_product_universe_omissions_run_warrant_reason"),
    )
    op.create_table(
        "product_selections",
        sa.Column("id", sa.Uuid(), nullable=False), sa.Column("run_id", sa.Uuid(), nullable=False), sa.Column("product_evaluation_id", sa.Uuid(), nullable=False),
        sa.Column("selected_at", sa.DateTime(timezone=True), nullable=False), sa.Column("selected_by", sa.Uuid(), nullable=False), sa.Column("rationale", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["product_selection_runs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_evaluation_id", "run_id"], ["product_evaluations.id", "product_evaluations.run_id"], ondelete="RESTRICT", name="fk_product_selections_evaluation_same_run"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("run_id", name="uq_product_selections_run"),
    )


def downgrade() -> None:
    op.drop_table("product_selections")
    op.drop_table("product_universe_omissions")
    op.drop_table("product_evaluation_reasons")
    op.drop_table("product_evaluation_metrics")
    op.drop_table("product_evaluation_criteria")
    op.drop_table("product_evaluation_inputs")
    op.drop_index("ix_product_evaluations_run_status", table_name="product_evaluations")
    op.drop_table("product_evaluations")
    op.drop_index("ix_product_selection_runs_underlying_evaluated", table_name="product_selection_runs")
    op.drop_index("ix_product_selection_runs_workspace_plan_version", table_name="product_selection_runs")
    op.drop_table("product_selection_runs")
