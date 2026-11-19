"""0060 schema/shape verification only in explicitly disposable synthetic SQLite."""

import importlib
from datetime import UTC, datetime
from decimal import Decimal
from io import StringIO
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.exc import IntegrityError

from app.features.position_monitoring.persistence.product_deadline_review import (
    ProductDeadlineAssessmentModel,
    ProductDeadlineEpisodeModel,
)
from app.features.product.persistence.deadline_choice import ProductDeadlineExitChoiceModel

migration = importlib.import_module("migrations.versions.20261118_0060_product_deadline_review")
NOW = datetime(2026, 11, 18, tzinfo=UTC)
TABLES = (
    "product_deadline_assessments",
    "product_deadline_episodes",
    "product_deadline_exit_choices",
)


@pytest.fixture
def database(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/synthetic_product_deadline_0060.db")
    metadata = sa.MetaData()
    sa.Table(
        "alerts",
        metadata,
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("alert_type", sa.String(40), nullable=False),
        sa.Column("observed_value", sa.Numeric(24, 10)),
        sa.Column("threshold_value", sa.Numeric(24, 10)),
        sa.CheckConstraint(
            f"alert_type IN ({migration.OLD_ALERT_TYPES})", name="ck_alerts_alert_type_valid"
        ),
        sa.CheckConstraint(
            f"(alert_type IN ({migration.OLD_NONNUMERIC_TYPES}) "
            "AND observed_value IS NULL AND threshold_value IS NULL) OR "
            f"(alert_type NOT IN ({migration.OLD_NONNUMERIC_TYPES}) "
            "AND observed_value IS NOT NULL AND threshold_value IS NOT NULL)",
            name="ck_alerts_alert_value_shape",
        ),
    )
    metadata.create_all(engine)
    with engine.begin() as connection, Operations.context(MigrationContext.configure(connection)):
        alerts = metadata.tables["alerts"]
        connection.execute(
            alerts.insert().values(
                id=uuid4(), alert_type="STOP_REACHED", observed_value=1, threshold_value=2
            )
        )
        connection.execute(
            alerts.insert().values(
                id=uuid4(),
                alert_type="POSITION_REVIEW_DUE",
                observed_value=None,
                threshold_value=None,
            )
        )
        yield connection
    engine.dispose()


def table(connection, name):
    # UUIDs reflect as CHAR(32) in SQLite. Restore their bind processors without
    # importing the full application's unrelated foreign-key model graph.
    uuid_columns = [
        sa.Column(column["name"], sa.Uuid(), primary_key=column["name"] == "id")
        for column in sa.inspect(connection).get_columns(name)
        if isinstance(column["type"], sa.CHAR) and column["type"].length == 32
    ]
    return sa.Table(
        name,
        sa.MetaData(),
        *uuid_columns,
        autoload_with=connection,
        resolve_fks=False,
    )


def scope():
    return dict(
        id=uuid4(),
        workspace_id=uuid4(),
        trade_id=uuid4(),
        position_id=uuid4(),
        rule_version="product-deadline-review-v1",
    )


def assessment(**changes):
    return (
        dict(
            **scope(),
            previous_assessment_id=None,
            input_fingerprint="a" * 64,
            owner_basis_id="b" * 64,
            outcome="UNAVAILABLE",
            evaluated_at=NOW,
            recorded_at=NOW,
            inputs={},
            result={},
        )
        | changes
    )


def episode(**changes):
    return (
        dict(
            **scope(),
            kind="DEADLINE_REVIEW",
            event_key="e" * 64,
            episode_number=1,
            opening_assessment_id=uuid4(),
            closing_assessment_id=None,
            alert_id=uuid4(),
            opened_at=NOW,
            closed_at=None,
            close_reason=None,
        )
        | changes
    )


def choice(**changes):
    return (
        dict(
            id=uuid4(),
            workspace_id=uuid4(),
            warrant_id=uuid4(),
            previous_revision_id=None,
            revision_number=1,
            terms_id=uuid4(),
            listing_id=uuid4(),
            listing_version=1,
            trading_venue_id=uuid4(),
            venue_mic="XSTU",
            venue_version=1,
            quotation_currency_code="EUR",
            recorded_at=NOW,
            recorded_by=uuid4(),
        )
        | changes
    )


def test_schema_matches_owners_and_preserves_existing_alerts(database):
    assert migration.down_revision == "20261118_0059"
    before = list(database.execute(sa.text("SELECT * FROM alerts ORDER BY alert_type")))
    migration.upgrade()
    for model in (
        ProductDeadlineAssessmentModel,
        ProductDeadlineEpisodeModel,
        ProductDeadlineExitChoiceModel,
    ):
        stored = {row["name"]: row for row in sa.inspect(database).get_columns(model.__tablename__)}
        assert set(stored) == set(model.__table__.columns.keys())
        for column in model.__table__.columns:
            assert stored[column.name]["nullable"] is column.nullable
            if isinstance(column.type, sa.String):
                assert stored[column.name]["type"].length == column.type.length
        assert {index.name for index in model.__table__.indexes} <= {
            index["name"] for index in sa.inspect(database).get_indexes(model.__tablename__)
        }
    assert list(database.execute(sa.text("SELECT * FROM alerts ORDER BY alert_type"))) == before
    migration.downgrade()
    assert set(sa.inspect(database).get_table_names()) == {"alerts"}
    assert list(database.execute(sa.text("SELECT * FROM alerts ORDER BY alert_type"))) == before


@pytest.mark.parametrize(
    "observed,threshold,valid",
    [(None, None, True), (1, None, False), (None, 1, False), (0, 0, False)],
)
def test_deadline_alert_has_no_manufactured_numeric_prices(database, observed, threshold, valid):
    migration.upgrade()
    statement = (
        table(database, "alerts")
        .insert()
        .values(
            id=uuid4(),
            alert_type="PRODUCT_DEADLINE_REVIEW",
            observed_value=observed,
            threshold_value=threshold,
        )
    )
    if valid:
        database.execute(statement)
    else:
        with pytest.raises(IntegrityError, match="alert_value_shape"):
            database.execute(statement)


@pytest.mark.parametrize(
    "outcome",
    [
        "BEFORE_WARNING",
        "WARNING_DUE",
        "EXIT_SESSION_STARTED",
        "CALENDAR_SESSION_ENDED",
        "WARNING_DAY_REACHED",
        "DEADLINE_DAY_REACHED",
        "DEADLINE_DAY_PASSED",
        "UNAVAILABLE",
        "CLOSED",
    ],
)
def test_all_time_precisions_are_accepted_without_price_input(database, outcome):
    migration.upgrade()
    database.execute(table(database, TABLES[0]).insert().values(**assessment(outcome=outcome)))


@pytest.mark.parametrize(
    "kind,key,valid",
    [
        ("DEADLINE_REVIEW", "e" * 64, True),
        ("DEADLINE_REVIEW", None, False),
        ("DATA_UNAVAILABLE", None, True),
        ("DATA_UNAVAILABLE", "e" * 64, False),
    ],
)
def test_episode_keys_distinguish_deadline_events_from_data_gaps(database, kind, key, valid):
    migration.upgrade()
    statement = table(database, TABLES[1]).insert().values(**episode(kind=kind, event_key=key))
    if valid:
        database.execute(statement)
    else:
        with pytest.raises(IntegrityError, match="product_deadline_event_shape"):
            database.execute(statement)


@pytest.mark.parametrize(
    "invalid",
    [{"listing_version": None}, {"venue_mic": None}, {"venue_version": 0}, {"listing_id": None}],
)
def test_choice_never_contains_half_a_listing_binding(database, invalid):
    migration.upgrade()
    with pytest.raises(IntegrityError, match="product_deadline_exit_choice_shape"):
        database.execute(table(database, TABLES[2]).insert().values(**choice(**invalid)))


@pytest.mark.parametrize("kind", [*TABLES, "alert"])
def test_downgrade_refuses_every_new_kind_of_recorded_history(database, kind):
    migration.upgrade()
    if kind == "alert":
        database.execute(
            table(database, "alerts")
            .insert()
            .values(
                id=uuid4(),
                alert_type="PRODUCT_DEADLINE_REVIEW",
                observed_value=None,
                threshold_value=None,
            )
        )
    else:
        values = {TABLES[0]: assessment, TABLES[1]: episode, TABLES[2]: choice}[kind]()
        database.execute(table(database, kind).insert().values(**values))
    with pytest.raises(RuntimeError, match="destructive downgrade refused"):
        migration.downgrade()
    assert set(TABLES) <= set(sa.inspect(database).get_table_names())


def test_downgrade_restores_numeric_and_nonnumeric_alert_contract(database):
    migration.upgrade()
    migration.downgrade()
    alerts = table(database, "alerts")
    with pytest.raises(IntegrityError, match="alert_type_valid"):
        database.execute(
            alerts.insert().values(
                id=uuid4(),
                alert_type="PRODUCT_DEADLINE_REVIEW",
                observed_value=1,
                threshold_value=2,
            )
        )
    with pytest.raises(IntegrityError, match="alert_value_shape"):
        database.execute(alerts.insert().values(id=uuid4(), alert_type="STOP_REACHED"))
    database.execute(
        alerts.insert().values(
            id=uuid4(),
            alert_type="STOP_REACHED",
            observed_value=Decimal("1.20"),
            threshold_value=Decimal("1.10"),
        )
    )


def test_postgresql_ddl_keeps_immutable_scope_guards_and_native_alert_alter():
    output = StringIO()
    context = MigrationContext.configure(
        dialect_name="postgresql", opts={"as_sql": True, "output_buffer": output}
    )
    with Operations.context(context):
        migration.upgrade()
    sql = output.getvalue()
    assert "ALTER TABLE alerts" in sql and "_alembic_tmp_alerts" not in sql
    for suffix, name in zip(("assessment", "episode", "exit_choice"), TABLES, strict=True):
        assert f"BEFORE TRUNCATE ON {name}" in sql
        assert f"FOR EACH STATEMENT EXECUTE FUNCTION guard_product_deadline_{suffix}()" in sql
    assert (
        "WARNING_DAY_REACHED" in sql
        and "DEADLINE_DAY_REACHED" in sql
        and "DEADLINE_DAY_PASSED" in sql
    )
