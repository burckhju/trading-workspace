import importlib
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, insert, inspect, select

from app.features.position_monitoring.persistence.models import (
    PositionRiskConfigurationModel,
    PositionRiskSnapshotModel,
)


@pytest.mark.parametrize("history", [None, "configuration", "snapshot"])
def test_additive_migration_starts_disabled_and_refuses_loss_of_history(history):
    migration = importlib.import_module("migrations.versions.20261004_0044_position_risk")
    engine = create_engine("sqlite://")
    with engine.begin() as connection, Operations.context(MigrationContext.configure(connection)):
        migration.upgrade()
        assert set(inspect(connection).get_table_names()) == {
            "position_risk_configurations",
            "position_risk_snapshots",
        }
        assert connection.execute(select(PositionRiskConfigurationModel)).all() == []
        if history:
            common = dict(id=uuid4(), workspace_id=uuid4(), position_id=uuid4())
            if history == "configuration":
                model = PositionRiskConfigurationModel
                fields = dict(
                    revision=1,
                    enabled=False,
                    policy_version="POSITION_RISK_V1",
                    parameters={},
                    configured_at=datetime.now(UTC),
                    actor=uuid4(),
                )
            else:
                model = PositionRiskSnapshotModel
                fields = dict(
                    configuration_revision=0,
                    input_fingerprint="a" * 64,
                    evaluated_at=datetime.now(UTC),
                    payload={},
                )
            connection.execute(insert(model).values(**common, **fields))
            with pytest.raises(RuntimeError, match="immutable risk history"):
                migration.downgrade()
            assert len(connection.execute(select(model)).all()) == 1
        else:
            migration.downgrade()
            assert inspect(connection).get_table_names() == []
    engine.dispose()
