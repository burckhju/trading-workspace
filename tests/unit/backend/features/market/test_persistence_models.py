"""Architecture tests for the FT-001 SQLAlchemy persistence mappings."""

from sqlalchemy import CheckConstraint, UniqueConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

from app.database.base import Base
from app.features.market.persistence.models import (
    AuditEventModel,
    CurrencyModel,
    ListingModel,
    TradingVenueModel,
    UnderlyingModel,
    WorkspaceModel,
)


def _foreign_key_ondelete(model: type[Base], column_name: str) -> str | None:
    foreign_key = next(iter(model.__table__.c[column_name].foreign_keys))
    return foreign_key.ondelete


def test_ft001_registers_exactly_the_approved_tables() -> None:
    expected = {
        "workspaces",
        "trading_venues",
        "currencies",
        "underlyings",
        "listings",
        "audit_events",
    }

    assert expected.issubset(Base.metadata.tables)


def test_underlying_mapping_has_approved_constraints_and_optimistic_locking() -> None:
    table = UnderlyingModel.__table__
    index_names = {index.name for index in table.indexes}
    checks = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert _foreign_key_ondelete(UnderlyingModel, "workspace_id") == "RESTRICT"
    assert "uq_underlyings_workspace_isin" in index_names
    assert "uq_underlyings_workspace_wkn" in index_names
    assert "ix_underlyings_workspace_lifecycle_name" in index_names
    assert "ck_underlyings_version_positive" in checks
    assert "ck_underlyings_name_not_blank" in checks
    assert UnderlyingModel.__mapper__.version_id_col is table.c.version
    assert UnderlyingModel.__mapper__.version_id_generator is False


def test_listing_mapping_has_approved_constraints_and_delete_rules() -> None:
    table = ListingModel.__table__
    index_names = {index.name for index in table.indexes}
    unique_names = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert _foreign_key_ondelete(ListingModel, "workspace_id") == "RESTRICT"
    assert _foreign_key_ondelete(ListingModel, "underlying_id") == "CASCADE"
    assert _foreign_key_ondelete(ListingModel, "trading_venue_id") == "RESTRICT"
    assert _foreign_key_ondelete(ListingModel, "currency_code") == "RESTRICT"
    assert "uq_listings_workspace_venue_ticker" in unique_names
    assert "uq_listings_active_primary_underlying" in index_names
    assert "ix_listings_underlying_lifecycle" in index_names
    assert "ix_listings_workspace_ticker" in index_names
    assert ListingModel.__mapper__.version_id_col is table.c.version
    assert ListingModel.__mapper__.version_id_generator is False


def test_reference_models_are_readable_relational_references() -> None:
    assert TradingVenueModel.__table__.c.mic.type.length == 4
    assert CurrencyModel.__table__.c.code.primary_key is True
    assert CurrencyModel.__table__.c.code.type.length == 3
    assert WorkspaceModel.__table__.c.id.primary_key is True


def test_audit_event_keeps_logical_aggregate_reference_without_foreign_key() -> None:
    table = AuditEventModel.__table__
    index_names = {index.name for index in table.indexes}

    assert _foreign_key_ondelete(AuditEventModel, "workspace_id") == "RESTRICT"
    assert not table.c.aggregate_id.foreign_keys
    assert table.c.field_changes.type.__class__.__name__ == "JSONB"
    assert "ix_audit_events_aggregate_chronology" in index_names
    assert "ix_audit_events_workspace_chronology" in index_names


def test_postgresql_ddl_contains_partial_unique_indexes_and_jsonb() -> None:
    dialect = postgresql.dialect()
    audit_ddl = str(CreateTable(AuditEventModel.__table__).compile(dialect=dialect))
    underlying_indexes = {
        index.name: str(CreateIndex(index).compile(dialect=dialect))
        for index in UnderlyingModel.__table__.indexes
    }
    listing_indexes = {
        index.name: str(CreateIndex(index).compile(dialect=dialect))
        for index in ListingModel.__table__.indexes
    }

    assert "JSONB" in audit_ddl
    assert (
        "WHERE isin IS NOT NULL" in underlying_indexes["uq_underlyings_workspace_isin"]
    )
    assert "WHERE wkn IS NOT NULL" in underlying_indexes["uq_underlyings_workspace_wkn"]
    assert (
        "WHERE is_primary = true AND lifecycle_status = 'ACTIVE'"
        in listing_indexes["uq_listings_active_primary_underlying"]
    )
