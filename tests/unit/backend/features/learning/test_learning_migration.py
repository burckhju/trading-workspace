from importlib import util
from pathlib import Path


def _load_migration():
    path = (
        Path(__file__).parents[5]
        / "backend"
        / "migrations"
        / "versions"
        / "20260820_0020_ft012_learning_slice_01.py"
    )
    spec = util.spec_from_file_location("ft012_migration", path)
    assert spec is not None and spec.loader is not None
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_revision_chain() -> None:
    migration = _load_migration()
    assert migration.revision == "20260820_0020"
    assert migration.down_revision == "20260818_0019"
