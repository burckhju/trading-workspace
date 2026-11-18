"""Offline PostgreSQL generation keeps the new history and foreign scope guards."""

import importlib
from io import StringIO

from alembic.migration import MigrationContext
from alembic.operations import Operations


def test_readiness_ddl_preserves_originals_against_update_delete_and_truncate():
    migration = importlib.import_module("migrations.versions.20261118_0058_review_readiness")
    output = StringIO()
    context = MigrationContext.configure(
        dialect_name="postgresql", opts={"as_sql": True, "output_buffer": output}
    )
    with Operations.context(context):
        migration.upgrade()
    ddl = output.getvalue()
    assert ddl.count("BEFORE UPDATE OR DELETE") == 2
    assert ddl.count("BEFORE TRUNCATE") == 2
    assert "w.workspace_id = NEW.workspace_id AND t.id = NEW.terms_id" in ddl
    assert "NEW.retrieved_at > NEW.recorded_at" in ddl
    assert "guard_product_review_document_scope" in ddl
    assert "ON DELETE RESTRICT" in ddl
    assert "INSERT INTO" not in ddl  # no invented user or historical evidence
