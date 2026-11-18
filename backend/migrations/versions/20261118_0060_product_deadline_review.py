"""Durable product-date reviews and explicit exit choices; no activation or orders.

Revision ID: 20261118_0060
Revises: 20261118_0059
"""

import sqlalchemy as sa
from alembic import op

revision = "20261118_0060"
down_revision = "20261118_0059"
branch_labels = None
depends_on = None

OLD_ALERT_TYPES = (
    "'STOP_REACHED', 'TARGET_REACHED', 'RISK_TREND_CHANGED', 'RISK_VOLATILITY_HIGH', "
    "'HEBELTRADER_B04_LOSS', 'INDICATIVE_ENTRY_LOSS', "
    "'POSITION_REVIEW_DUE', 'POSITION_DATA_UNAVAILABLE'"
)
OLD_NONNUMERIC_TYPES = "'POSITION_REVIEW_DUE', 'POSITION_DATA_UNAVAILABLE'"
DEADLINE_TYPE = "'PRODUCT_DEADLINE_REVIEW'"
OUTCOMES = (
    "'BEFORE_WARNING','WARNING_DUE','EXIT_SESSION_STARTED','CALENDAR_SESSION_ENDED',"
    "'WARNING_DAY_REACHED','DEADLINE_DAY_REACHED','DEADLINE_DAY_PASSED','UNAVAILABLE','CLOSED'"
)
DUE_OUTCOMES = (
    "'WARNING_DUE','EXIT_SESSION_STARTED','CALENDAR_SESSION_ENDED',"
    "'WARNING_DAY_REACHED','DEADLINE_DAY_REACHED','DEADLINE_DAY_PASSED'"
)


def _alert_constraints(*, include_deadlines: bool) -> None:
    types = f"{OLD_ALERT_TYPES}, {DEADLINE_TYPE}" if include_deadlines else OLD_ALERT_TYPES
    nonnumeric = (
        f"{OLD_NONNUMERIC_TYPES}, {DEADLINE_TYPE}" if include_deadlines else OLD_NONNUMERIC_TYPES
    )
    # Native ALTER on PostgreSQL; SQLite's batch copy only supports disposable
    # migration verification. Existing price-axis constraints are preserved.
    with op.batch_alter_table("alerts") as batch:
        batch.drop_constraint(op.f("ck_alerts_alert_type_valid"), type_="check")
        batch.drop_constraint(op.f("ck_alerts_alert_value_shape"), type_="check")
        batch.create_check_constraint(
            op.f("ck_alerts_alert_type_valid"), f"alert_type IN ({types})"
        )
        batch.create_check_constraint(
            op.f("ck_alerts_alert_value_shape"),
            f"(alert_type IN ({nonnumeric}) "
            "AND observed_value IS NULL AND threshold_value IS NULL) OR "
            f"(alert_type NOT IN ({nonnumeric}) "
            "AND observed_value IS NOT NULL AND threshold_value IS NOT NULL)",
        )


def _scope_columns() -> list[sa.Column]:  # type: ignore[type-arg]
    return [
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("workspaces.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "trade_id",
            sa.Uuid(),
            sa.ForeignKey("trades.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "position_id",
            sa.Uuid(),
            sa.ForeignKey("positions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("rule_version", sa.String(64), nullable=False),
    ]


def upgrade() -> None:
    _alert_constraints(include_deadlines=True)
    op.create_table(
        "product_deadline_assessments",
        *_scope_columns(),
        sa.Column(
            "previous_assessment_id",
            sa.Uuid(),
            sa.ForeignKey("product_deadline_assessments.id", ondelete="RESTRICT"),
        ),
        sa.Column("input_fingerprint", sa.String(64), nullable=False),
        sa.Column("owner_basis_id", sa.String(64), nullable=False),
        sa.Column("outcome", sa.String(32), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("inputs", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.UniqueConstraint("previous_assessment_id", name="uq_product_deadline_successor"),
        sa.CheckConstraint(f"outcome IN ({OUTCOMES})", name="product_deadline_outcome"),
    )
    op.create_index(
        "uq_product_deadline_root",
        "product_deadline_assessments",
        ["workspace_id", "position_id", "rule_version"],
        unique=True,
        postgresql_where=sa.text("previous_assessment_id IS NULL"),
        sqlite_where=sa.text("previous_assessment_id IS NULL"),
    )
    op.create_index(
        "ix_product_deadline_history",
        "product_deadline_assessments",
        ["workspace_id", "position_id", "recorded_at"],
    )
    op.create_table(
        "product_deadline_episodes",
        *_scope_columns(),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("event_key", sa.String(64)),
        sa.Column("episode_number", sa.Integer(), nullable=False),
        sa.Column(
            "opening_assessment_id",
            sa.Uuid(),
            sa.ForeignKey("product_deadline_assessments.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "closing_assessment_id",
            sa.Uuid(),
            sa.ForeignKey("product_deadline_assessments.id", ondelete="RESTRICT"),
        ),
        sa.Column(
            "alert_id", sa.Uuid(), sa.ForeignKey("alerts.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.Column("close_reason", sa.String(100)),
        sa.UniqueConstraint(
            "opening_assessment_id", "kind", name="uq_product_deadline_episode_opening"
        ),
        sa.UniqueConstraint("alert_id", name="uq_product_deadline_episode_alert"),
        sa.UniqueConstraint(
            "workspace_id",
            "position_id",
            "rule_version",
            "kind",
            "event_key",
            name="uq_product_deadline_event",
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "position_id",
            "rule_version",
            "kind",
            "episode_number",
            name="uq_product_deadline_episode_number",
        ),
        sa.CheckConstraint("episode_number > 0", name="product_deadline_episode_positive"),
        sa.CheckConstraint(
            "kind IN ('DEADLINE_REVIEW','DATA_UNAVAILABLE')", name="product_deadline_kind"
        ),
        sa.CheckConstraint(
            "(kind = 'DEADLINE_REVIEW' AND event_key IS NOT NULL) OR "
            "(kind = 'DATA_UNAVAILABLE' AND event_key IS NULL)",
            name="product_deadline_event_shape",
        ),
    )
    op.create_index(
        "uq_product_deadline_active",
        "product_deadline_episodes",
        ["workspace_id", "position_id", "rule_version", "kind"],
        unique=True,
        postgresql_where=sa.text("closed_at IS NULL"),
        sqlite_where=sa.text("closed_at IS NULL"),
    )
    op.create_table(
        "product_deadline_exit_choices",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("workspaces.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "warrant_id",
            sa.Uuid(),
            sa.ForeignKey("warrants.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "previous_revision_id",
            sa.Uuid(),
            sa.ForeignKey("product_deadline_exit_choices.id", ondelete="RESTRICT"),
        ),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column(
            "terms_id",
            sa.Uuid(),
            sa.ForeignKey("warrant_terms_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "listing_id", sa.Uuid(), sa.ForeignKey("warrant_listings.id", ondelete="RESTRICT")
        ),
        sa.Column("listing_version", sa.Integer()),
        sa.Column(
            "trading_venue_id", sa.Uuid(), sa.ForeignKey("trading_venues.id", ondelete="RESTRICT")
        ),
        sa.Column("venue_mic", sa.String(4)),
        sa.Column("venue_version", sa.Integer()),
        sa.Column("quotation_currency_code", sa.String(3)),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_by", sa.Uuid(), nullable=False),
        sa.CheckConstraint("revision_number > 0", name="product_deadline_exit_choice_positive"),
        sa.CheckConstraint(
            "(listing_id IS NULL AND listing_version IS NULL AND trading_venue_id IS NULL "
            "AND venue_mic IS NULL AND venue_version IS NULL AND quotation_currency_code IS NULL) "
            "OR (listing_id IS NOT NULL AND listing_version IS NOT NULL AND listing_version > 0 "
            "AND trading_venue_id IS NOT NULL AND venue_mic IS NOT NULL "
            "AND venue_version IS NOT NULL AND venue_version > 0 "
            "AND quotation_currency_code IS NOT NULL)",
            name="product_deadline_exit_choice_shape",
        ),
    )
    op.create_index(
        "uq_product_deadline_exit_choice_root",
        "product_deadline_exit_choices",
        ["workspace_id", "warrant_id"],
        unique=True,
        postgresql_where=sa.text("previous_revision_id IS NULL"),
        sqlite_where=sa.text("previous_revision_id IS NULL"),
    )
    op.create_index(
        "uq_product_deadline_exit_choice_number",
        "product_deadline_exit_choices",
        ["workspace_id", "warrant_id", "revision_number"],
        unique=True,
    )
    op.create_index(
        "uq_product_deadline_exit_choice_successor",
        "product_deadline_exit_choices",
        ["previous_revision_id"],
        unique=True,
    )
    if op.get_bind().dialect.name == "postgresql":
        _guards()


def _guards() -> None:
    op.execute("""
    CREATE FUNCTION guard_product_deadline_assessment() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP <> 'INSERT' THEN
        RAISE EXCEPTION 'Product deadline assessments are append-only' USING ERRCODE='23514';
      END IF;
      IF NOT EXISTS (SELECT 1 FROM trades t JOIN positions p ON p.trade_id=t.id
          WHERE t.id=NEW.trade_id AND t.workspace_id=NEW.workspace_id AND p.id=NEW.position_id)
        OR (NEW.previous_assessment_id IS NOT NULL AND NOT EXISTS (
          SELECT 1 FROM product_deadline_assessments a WHERE a.id=NEW.previous_assessment_id
          AND a.workspace_id=NEW.workspace_id AND a.trade_id=NEW.trade_id
          AND a.position_id=NEW.position_id AND a.rule_version=NEW.rule_version)) THEN
        RAISE EXCEPTION 'Product deadline assessment scope mismatch' USING ERRCODE='23514';
      END IF;
      RETURN NEW;
    END $$
    """)
    op.execute(f"""
    CREATE FUNCTION guard_product_deadline_episode() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP IN ('DELETE','TRUNCATE') OR (TG_OP='UPDATE' AND (
          OLD.closed_at IS NOT NULL OR NEW.closed_at IS NULL OR
          (to_jsonb(NEW)-'closed_at'-'closing_assessment_id'-'close_reason') IS DISTINCT FROM
          (to_jsonb(OLD)-'closed_at'-'closing_assessment_id'-'close_reason'))) THEN
        RAISE EXCEPTION 'Product deadline episode history is immutable' USING ERRCODE='23514';
      END IF;
      IF NOT EXISTS (SELECT 1 FROM product_deadline_assessments a JOIN alerts l ON l.id=NEW.alert_id
          WHERE a.id=NEW.opening_assessment_id AND a.workspace_id=NEW.workspace_id
          AND a.trade_id=NEW.trade_id AND a.position_id=NEW.position_id
          AND a.rule_version=NEW.rule_version AND l.trade_id=NEW.trade_id
          AND l.position_id=NEW.position_id
          AND ((NEW.kind='DEADLINE_REVIEW' AND a.outcome IN ({DUE_OUTCOMES})
                AND a.result->>'reminder_due'='true'
                AND NEW.event_key=a.result->>'deadline_event_key'
                AND l.alert_type='PRODUCT_DEADLINE_REVIEW')
            OR (NEW.kind='DATA_UNAVAILABLE' AND a.outcome='UNAVAILABLE'
                AND l.alert_type='POSITION_DATA_UNAVAILABLE'))) THEN
        RAISE EXCEPTION 'Product deadline episode scope mismatch' USING ERRCODE='23514';
      END IF;
      IF NEW.closed_at IS NOT NULL AND (NEW.closed_at < NEW.opened_at OR NEW.close_reason IS NULL
          OR NOT EXISTS (SELECT 1 FROM product_deadline_assessments a
          WHERE a.id=NEW.closing_assessment_id AND a.workspace_id=NEW.workspace_id
          AND a.trade_id=NEW.trade_id AND a.position_id=NEW.position_id
          AND a.rule_version=NEW.rule_version
          AND (a.outcome='CLOSED'
            OR (NEW.kind='DATA_UNAVAILABLE' AND a.outcome<>'UNAVAILABLE')
            OR (NEW.kind='DEADLINE_REVIEW' AND a.outcome<>'UNAVAILABLE'
              AND (a.result->>'reminder_due'='false'
                OR (a.result->>'reminder_due'='true'
                  AND NEW.event_key IS DISTINCT FROM a.result->>'deadline_event_key')))))) THEN
        RAISE EXCEPTION 'Product deadline close requires recorded resolution' USING ERRCODE='23514';
      END IF;
      RETURN NEW;
    END $$
    """)
    op.execute("""
    CREATE FUNCTION guard_product_deadline_exit_choice() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP <> 'INSERT' THEN
        RAISE EXCEPTION 'Product exit choices are append-only' USING ERRCODE='23514';
      END IF;
      IF NOT EXISTS (SELECT 1 FROM warrants w JOIN warrant_terms_versions t ON t.warrant_id=w.id
          WHERE w.id=NEW.warrant_id AND w.workspace_id=NEW.workspace_id AND t.id=NEW.terms_id
          AND t.effective_to IS NULL AND t.created_at<=NEW.recorded_at
          AND t.effective_from<=NEW.recorded_at)
        OR (NEW.previous_revision_id IS NULL AND (NEW.revision_number<>1 OR NEW.listing_id IS NULL))
        OR (NEW.previous_revision_id IS NOT NULL AND NOT EXISTS (
          SELECT 1 FROM product_deadline_exit_choices c WHERE c.id=NEW.previous_revision_id
          AND c.workspace_id=NEW.workspace_id AND c.warrant_id=NEW.warrant_id
          AND NEW.revision_number=c.revision_number+1 AND NEW.recorded_at>=c.recorded_at))
        OR (NEW.listing_id IS NOT NULL AND NOT EXISTS (
          SELECT 1 FROM warrant_listings l JOIN trading_venues v ON v.id=l.trading_venue_id
          JOIN warrants w ON w.id=l.warrant_id JOIN currencies c ON c.code=l.quotation_currency_code
          WHERE l.id=NEW.listing_id AND l.workspace_id=NEW.workspace_id
          AND l.warrant_id=NEW.warrant_id AND l.version=NEW.listing_version
          AND v.id=NEW.trading_venue_id AND v.mic=NEW.venue_mic AND v.version=NEW.venue_version
          AND l.quotation_currency_code=NEW.quotation_currency_code
          AND w.lifecycle_status='ACTIVE' AND l.lifecycle_status='ACTIVE'
          AND v.is_active AND c.is_active)) THEN
        RAISE EXCEPTION 'Product exit choice scope or predecessor mismatch' USING ERRCODE='23514';
      END IF;
      RETURN NEW;
    END $$
    """)
    for suffix, table in (
        ("assessment", "product_deadline_assessments"),
        ("episode", "product_deadline_episodes"),
        ("exit_choice", "product_deadline_exit_choices"),
    ):
        op.execute(
            f"CREATE TRIGGER tw_product_deadline_{suffix}_guard "
            f"BEFORE INSERT OR UPDATE OR DELETE ON {table} "
            f"FOR EACH ROW EXECUTE FUNCTION guard_product_deadline_{suffix}()"
        )
        op.execute(
            f"CREATE TRIGGER tw_product_deadline_{suffix}_no_truncate BEFORE TRUNCATE ON {table} "
            f"FOR EACH STATEMENT EXECUTE FUNCTION guard_product_deadline_{suffix}()"
        )


def downgrade() -> None:
    bind = op.get_bind()
    for table in (
        "product_deadline_assessments",
        "product_deadline_episodes",
        "product_deadline_exit_choices",
    ):
        if bind.execute(sa.text(f"SELECT EXISTS (SELECT 1 FROM {table})")).scalar():
            raise RuntimeError("Product deadline history exists; destructive downgrade refused")
    if bind.execute(
        sa.text("SELECT EXISTS (SELECT 1 FROM alerts WHERE alert_type='PRODUCT_DEADLINE_REVIEW')")
    ).scalar():
        raise RuntimeError("Product deadline alerts exist; destructive downgrade refused")
    if bind.dialect.name == "postgresql":
        for suffix in ("episode", "assessment", "exit_choice"):
            op.execute(f"DROP FUNCTION guard_product_deadline_{suffix}() CASCADE")
    op.drop_table("product_deadline_episodes")
    op.drop_table("product_deadline_assessments")
    op.drop_table("product_deadline_exit_choices")
    _alert_constraints(include_deadlines=False)
