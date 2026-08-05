import ast
from pathlib import Path

PATH = Path(__file__).resolve().parents[5] / "backend/migrations/versions/20260805_0002_market_data_persistence.py"


def test_market_data_migration_has_expected_revision_chain_and_tables() -> None:
    text = PATH.read_text(encoding="utf-8")
    tree = ast.parse(text)
    assignments: dict[str, str | None] = {}
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id in {"revision", "down_revision"} and node.value is not None:
                assignments[node.target.id] = ast.literal_eval(node.value)
    assert assignments == {
        "revision": "20260805_0002",
        "down_revision": "20260803_0001",
    }
    assert "provider_instrument_mappings" in text
    assert "daily_prices" in text
    assert "uq_daily_prices_listing_date_type" in text
