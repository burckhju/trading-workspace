"""Unit tests for database infrastructure."""

from app.core.config import Environment, Settings
from app.database import Base, DatabaseManager, NAMING_CONVENTION


def make_settings() -> Settings:
    return Settings(
        environment=Environment.TEST,
        database_url="postgresql+asyncpg://localhost/trading_workspace_test",
    )


def test_metadata_uses_stable_constraint_naming() -> None:
    assert Base.metadata.naming_convention == NAMING_CONVENTION
    assert NAMING_CONVENTION["pk"] == "pk_%(table_name)s"
    assert NAMING_CONVENTION["fk"].startswith("fk_%(table_name)s")


def test_database_manager_builds_async_postgresql_engine() -> None:
    manager = DatabaseManager(make_settings())

    assert manager.url.drivername == "postgresql+asyncpg"
    assert manager.url.database == "trading_workspace_test"
