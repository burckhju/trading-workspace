from importlib import util
from pathlib import Path


def _load_migration():
    path = (
        Path(__file__).parents[5]
        / "backend"
        / "migrations"
        / "versions"
        / "20260825_0023_ft013_controlled_model_governance.py"
    )
    spec = util.spec_from_file_location("ft013_migration", path)
    assert spec is not None and spec.loader is not None
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_revision_chain() -> None:
    migration = _load_migration()
    assert migration.revision == "20260825_0023"
    assert migration.down_revision == "20260824_0022"
